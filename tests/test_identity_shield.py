import json
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.identity_shield import assess_applicant_risk, run_student_enrollment_screening


class IdentityShieldTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        SessionLocal = sessionmaker(bind=self.engine)
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    @patch("app.identity_shield.publish_domain_event")
    @patch("app.identity_shield.mirror_document")
    @patch("app.identity_shield.build_subject_identity_graph")
    def test_enrollment_screening_flags_face_mismatch_and_shared_device(
        self,
        build_graph_mock,
        mirror_document_mock,
        publish_domain_event_mock,
    ):
        student = models.Student(
            id=11,
            name="Ankan",
            email="ankan@example.com",
            registration_number="22BCS011",
            parent_email="parent@example.com",
            section="CSE-A",
            department="CSE",
            semester=4,
            profile_face_template_json=json.dumps(
                {
                    "embeddings": [[1.0, 0.0, 0.0]],
                    "signature": [1.0, 0.0, 0.0],
                }
            ),
            enrollment_video_template_json=json.dumps(
                {
                    "embeddings": [[0.0, 1.0, 0.0]],
                    "signature": [0.0, 1.0, 0.0],
                }
            ),
        )
        auth_user = models.AuthUser(
            id=91,
            email="ankan@example.com",
            password_hash="x",
            role=models.UserRole.STUDENT,
            student_id=11,
            is_active=True,
        )
        self.db.add_all([student, auth_user])
        self.db.commit()

        build_graph_mock.return_value = {
            "subject_key": "student:11",
            "summary": {
                "shared_device_count": 2,
                "connected_user_count": 3,
                "connected_student_count": 1,
            },
            "nodes": [],
            "edges": [],
        }

        result = run_student_enrollment_screening(self.db, student_id=11)

        signal_types = {signal.signal_type for signal in result.signals}
        self.assertEqual(result.workflow_key, "enrollment_identity")
        self.assertEqual(result.student_id, 11)
        self.assertIn("profile_enrollment_face_mismatch", signal_types)
        self.assertIn("shared_device_reuse", signal_types)
        self.assertIn(result.risk_level, {models.FraudRiskLevel.HIGH, models.FraudRiskLevel.CRITICAL})
        self.assertTrue(mirror_document_mock.called)
        self.assertTrue(publish_domain_event_mock.called)

    @patch("app.identity_shield.publish_domain_event")
    @patch("app.identity_shield.mirror_document")
    @patch("app.identity_shield.get_mongo_db", return_value=None)
    def test_applicant_risk_assessment_flags_existing_email_and_liveness_failure(
        self,
        _get_mongo_db,
        mirror_document_mock,
        publish_domain_event_mock,
    ):
        existing_user = models.AuthUser(
            id=7,
            email="applicant@example.com",
            password_hash="x",
            role=models.UserRole.STUDENT,
            is_active=True,
        )
        self.db.add(existing_user)
        self.db.commit()

        payload = schemas.ApplicantRiskAssessmentRequest(
            applicant_email="applicant@example.com",
            claimed_role="student",
            registration_number=None,
            document_match_score=0.51,
            face_match_confidence=0.69,
            liveness_passed=False,
            suspicious_flags=["document tamper suspected"],
        )

        result = assess_applicant_risk(self.db, payload)

        signal_types = {signal.signal_type for signal in result.signals}
        self.assertEqual(result.workflow_key, "applicant_identity")
        self.assertEqual(result.applicant_email, "applicant@example.com")
        self.assertIn("existing_account_email", signal_types)
        self.assertIn("document_match_low", signal_types)
        self.assertIn("face_match_low", signal_types)
        self.assertIn("liveness_failed", signal_types)
        self.assertEqual(result.status, models.IdentityVerificationStatus.FLAGGED)
        self.assertTrue(mirror_document_mock.called)
        self.assertTrue(publish_domain_event_mock.called)


if __name__ == "__main__":
    unittest.main()
