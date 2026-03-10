import json
import unittest
from types import SimpleNamespace
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

    @patch("app.identity_shield.publish_domain_event")
    @patch("app.identity_shield.mirror_document")
    @patch("app.identity_shield.store_data_url_object")
    @patch("app.identity_shield.score_uploaded_video_liveness")
    @patch("app.identity_shield.get_mongo_db", return_value=None)
    def test_applicant_risk_assessment_persists_evidence_artifacts(
        self,
        _get_mongo_db,
        score_uploaded_video_liveness_mock,
        store_data_url_object_mock,
        mirror_document_mock,
        publish_domain_event_mock,
    ):
        score_uploaded_video_liveness_mock.return_value = {
            "available": True,
            "liveness_passed": True,
            "score": 0.93,
            "engine": "opencv-dnn",
            "reason": "Automatic liveness score passed.",
            "metrics": {"motion_score": 0.19},
            "sampled_frames": 8,
            "valid_frames": 8,
            "total_video_frames": 41,
        }
        store_data_url_object_mock.side_effect = [
            SimpleNamespace(
                object_key="identity/cases/doc.pdf",
                content_type="application/pdf",
                size_bytes=3210,
                checksum_sha256="d" * 64,
            ),
            SimpleNamespace(
                object_key="identity/cases/video.mp4",
                content_type="video/mp4",
                size_bytes=6543,
                checksum_sha256="e" * 64,
            ),
        ]

        payload = schemas.ApplicantRiskAssessmentRequest(
            applicant_email="evidence@example.com",
            claimed_role="student",
            registration_number="24BCS1001",
            document_match_score=0.84,
            face_match_confidence=0.88,
            evidence_uploads=[
                schemas.IdentityVerificationArtifactUpload(
                    artifact_type="document_evidence",
                    data_url="data:application/pdf;base64,QUJDRA==",
                    verification_state="scored",
                    note="Passport scan",
                    document_match_score=0.84,
                ),
                schemas.IdentityVerificationArtifactUpload(
                    artifact_type="video_verification",
                    data_url="data:video/mp4;base64,QUJDRA==",
                    verification_state="verified",
                    note="Liveness clip",
                    face_match_confidence=0.88,
                    liveness_passed=True,
                ),
            ],
        )

        result = assess_applicant_risk(self.db, payload)

        self.assertEqual(len(result.artifacts), 2)
        self.assertEqual(result.artifacts[0].artifact_type, "document_evidence")
        self.assertEqual(result.artifacts[0].media_object_key, "identity/cases/doc.pdf")
        self.assertEqual(result.artifacts[1].artifact_type, "video_verification")
        self.assertEqual(result.artifacts[1].media_object_key, "identity/cases/video.mp4")
        self.assertEqual(result.artifacts[1].verification_state, "verified")
        self.assertTrue(result.artifacts[1].liveness_passed)
        self.assertEqual(result.artifacts[1].extracted_identity["auto_video_liveness"]["engine"], "opencv-dnn")
        self.assertIn("Automatic liveness score passed.", result.artifacts[1].note or "")
        self.assertIn("liveness_video", result.completed_checks)
        self.assertEqual(self.db.query(models.IdentityVerificationArtifact).count(), 2)
        self.assertTrue(mirror_document_mock.called)
        self.assertTrue(publish_domain_event_mock.called)


if __name__ == "__main__":
    unittest.main()
