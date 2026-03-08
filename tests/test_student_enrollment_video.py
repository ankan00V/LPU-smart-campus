import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.routers.attendance import (
    update_student_enrollment_video,
    update_student_profile_photo,
)


def _frame_payload(count: int = 8) -> list[str]:
    token = "data:image/jpeg;base64," + ("A" * 32)
    return [token for _ in range(count)]


class StudentEnrollmentVideoTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        SessionLocal = sessionmaker(bind=self.engine)
        self.db = SessionLocal()
        self.student = models.Student(
            id=101,
            name="Student One",
            email="student.one@example.com",
            registration_number="22BCS101",
            profile_photo_data_url="data:image/jpeg;base64," + ("B" * 32),
            department="CSE",
            semester=4,
        )
        self.db.add(self.student)
        self.db.commit()
        self.current_user = models.AuthUser(
            id=1,
            email="student.one@example.com",
            password_hash="x",
            role=models.UserRole.STUDENT,
            student_id=101,
            is_active=True,
        )

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    @patch("app.routers.attendance.mirror_document")
    @patch("app.routers.attendance._sync_student_to_mongo")
    @patch("app.routers.attendance.run_student_enrollment_screening")
    @patch("app.routers.attendance.build_enrollment_template_from_frames")
    def test_first_time_enrollment_persists_template(
        self,
        build_template_mock,
        screening_mock,
        sync_student_mock,
        mirror_document_mock,
    ):
        build_template_mock.return_value = {
            "signature": [0.2, 0.4, 0.6],
            "embeddings": [[0.2, 0.4, 0.6]],
            "quality": {
                "valid_frames_total": 8,
                "valid_frames_used": 8,
            },
        }
        screening_mock.return_value = SimpleNamespace(
            id=501,
            risk_level=models.FraudRiskLevel.LOW,
        )

        result = update_student_enrollment_video(
            payload=schemas.StudentEnrollmentVideoRequest(frames_data_urls=_frame_payload(8)),
            db=self.db,
            current_user=self.current_user,
        )

        stored_student = self.db.get(models.Student, 101)
        self.assertTrue(result.has_enrollment_video)
        self.assertFalse(result.can_update_now)
        self.assertEqual(result.valid_frames_used, 8)
        self.assertIsNotNone(stored_student.enrollment_video_template_json)
        self.assertIsNotNone(stored_student.enrollment_video_updated_at)
        self.assertIsNotNone(stored_student.enrollment_video_locked_until)
        self.assertEqual(
            json.loads(stored_student.enrollment_video_template_json)["quality"]["valid_frames_total"],
            8,
        )
        sync_student_mock.assert_called_once()
        mirror_document_mock.assert_called_once()
        screening_mock.assert_called_once_with(self.db, student_id=101)

    @patch("app.routers.attendance.build_enrollment_template_from_frames")
    def test_template_validation_failure_returns_http_400(self, build_template_mock):
        build_template_mock.side_effect = ValueError(
            "Head movement range is too low. Look left, right, up, and down while recording."
        )

        with self.assertRaises(HTTPException) as ctx:
            update_student_enrollment_video(
                payload=schemas.StudentEnrollmentVideoRequest(frames_data_urls=_frame_payload(8)),
                db=self.db,
                current_user=self.current_user,
            )

        stored_student = self.db.get(models.Student, 101)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Head movement range is too low", str(ctx.exception.detail))
        self.assertIsNone(stored_student.enrollment_video_template_json)

    @patch("app.routers.attendance.mirror_document")
    @patch("app.routers.attendance._sync_student_to_mongo")
    @patch("app.routers.attendance.run_student_enrollment_screening")
    @patch("app.routers.attendance._rebuild_profile_face_template")
    @patch("app.routers.attendance.store_data_url_object")
    def test_profile_photo_refresh_reruns_identity_screening_when_enrollment_exists(
        self,
        store_data_url_object_mock,
        rebuild_profile_mock,
        screening_mock,
        sync_student_mock,
        mirror_document_mock,
    ):
        self.student.enrollment_video_template_json = json.dumps(
            {
                "signature": [0.2, 0.4, 0.6],
                "embeddings": [[0.2, 0.4, 0.6]],
            }
        )
        self.db.commit()

        store_data_url_object_mock.return_value = SimpleNamespace(object_key="students/101/profile-photo.jpg")
        screening_mock.return_value = SimpleNamespace(
            id=777,
            risk_level=models.FraudRiskLevel.MEDIUM,
        )

        result = update_student_profile_photo(
            payload=schemas.StudentProfilePhotoUpdate(photo_data_url="data:image/jpeg;base64," + ("C" * 32)),
            db=self.db,
            current_user=self.current_user,
        )

        stored_student = self.db.get(models.Student, 101)
        self.assertTrue(result.has_profile_photo)
        self.assertEqual(stored_student.profile_photo_object_key, "students/101/profile-photo.jpg")
        rebuild_profile_mock.assert_called_once()
        sync_student_mock.assert_called_once()
        mirror_document_mock.assert_called_once()
        screening_mock.assert_called_once_with(self.db, student_id=101)


if __name__ == "__main__":
    unittest.main()
