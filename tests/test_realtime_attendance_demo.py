import unittest
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.routers.attendance import mark_realtime_attendance


class RealtimeAttendanceDemoTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        SessionLocal = sessionmaker(bind=self.engine)
        self.db = SessionLocal()
        self._seed()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _seed(self):
        self.student_id = 1
        self.db.add_all(
            [
                models.Student(
                    id=self.student_id,
                    name="Demo Student",
                    email="demo.student@example.com",
                    registration_number="22BCS101",
                    section="P132",
                    department="CSE",
                    semester=4,
                    profile_photo_data_url="data:image/jpeg;base64,PROFILEPHOTO1234567890",
                    enrollment_video_template_json='{"template":"enrolled"}',
                ),
            ]
        )
        self.db.commit()

    def _student_user(self) -> models.AuthUser:
        return models.AuthUser(
            id=9001,
            email="demo.student@example.com",
            password_hash="x",
            role=models.UserRole.STUDENT,
            student_id=self.student_id,
            faculty_id=None,
            is_active=True,
        )

    @mock.patch("app.routers.attendance.enqueue_recompute", autospec=True)
    @mock.patch("app.routers.attendance.enqueue_face_reverification", autospec=True)
    @mock.patch("app.routers.attendance.publish_domain_event", autospec=True)
    @mock.patch("app.routers.attendance._upsert_mongo_by_id", autospec=True)
    @mock.patch("app.routers.attendance._upsert_present_attendance", autospec=True)
    @mock.patch("app.routers.attendance.store_data_url_object", autospec=True)
    @mock.patch("app.routers.attendance._verify_student_face_payload", autospec=True)
    @mock.patch("app.routers.attendance._window_flags", autospec=True)
    def test_demo_mode_uses_live_verification_but_skips_persistence(
        self,
        mock_window_flags,
        mock_verify_face_payload,
        mock_store_media,
        mock_upsert_present,
        mock_upsert_mongo,
        mock_publish_event,
        mock_enqueue_face_reverify,
        mock_enqueue_recompute,
    ):
        mock_window_flags.return_value = (False, True, False)
        mock_verify_face_payload.return_value = (
            "data:image/jpeg;base64,SELFIEFRAME1234567890",
            0.93,
            "opencv-embedding",
            models.AttendanceSubmissionStatus.VERIFIED,
            "Face verified",
        )
        payload = schemas.RealtimeAttendanceMarkRequest(
            schedule_id=None,
            selfie_photo_data_url="data:image/jpeg;base64,SELFIEFRAME1234567890",
            selfie_frames_data_urls=[
                "data:image/jpeg;base64,SELFIEFRAME1234567890",
                "data:image/jpeg;base64,SELFIEFRAME2234567890",
                "data:image/jpeg;base64,SELFIEFRAME3234567890",
                "data:image/jpeg;base64,SELFIEFRAME4234567890",
                "data:image/jpeg;base64,SELFIEFRAME5234567890",
                "data:image/jpeg;base64,SELFIEFRAME6234567890",
            ],
            demo_mode=True,
        )

        response = mark_realtime_attendance(
            payload=payload,
            db=self.db,
            current_user=self._student_user(),
        )

        self.assertEqual(response.submission_id, 0)
        self.assertEqual(response.status, models.AttendanceSubmissionStatus.VERIFIED)
        self.assertTrue(response.demo_mode)
        self.assertTrue(response.persistence_skipped)
        self.assertIn("no data was saved", response.message.lower())
        mock_verify_face_payload.assert_called_once()
        mock_store_media.assert_not_called()
        mock_upsert_present.assert_not_called()
        mock_upsert_mongo.assert_not_called()
        mock_publish_event.assert_not_called()
        mock_enqueue_face_reverify.assert_not_called()
        mock_enqueue_recompute.assert_not_called()
        self.assertEqual(self.db.query(models.AttendanceSubmission).count(), 0)
        self.assertEqual(self.db.query(models.AttendanceRecord).count(), 0)


if __name__ == "__main__":
    unittest.main()
