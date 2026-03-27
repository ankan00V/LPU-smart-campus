import json
import unittest
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.routers.attendance import mark_realtime_attendance
from app.routers.realtime import _format_sse_message


class RealtimeAttendanceDemoTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        SessionLocal = sessionmaker(bind=self.engine)
        self.db = SessionLocal()
        self.user = self._seed_student_user()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _seed_student_user(self) -> models.AuthUser:
        student = models.Student(
            id=1101,
            name="Demo Student",
            email="demo.student@example.com",
            department="CSE",
            semester=6,
            section="P132",
            registration_number="REG1101",
            profile_photo_data_url="data:image/jpeg;base64," + ("A" * 256),
            profile_face_template_json=json.dumps({"embeddings": [[0.1, 0.2, 0.3]]}),
            enrollment_video_template_json=json.dumps({"embeddings": [[0.1, 0.2, 0.3]]}),
        )
        user = models.AuthUser(
            id=2101,
            email="demo.student@example.com",
            password_hash="hash",
            role=models.UserRole.STUDENT,
            student_id=1101,
            is_active=True,
        )
        self.db.add_all([student, user])
        self.db.commit()
        return user

    def _build_demo_payload(self) -> schemas.RealtimeAttendanceMarkRequest:
        frame = "data:image/jpeg;base64," + ("B" * 320)
        return schemas.RealtimeAttendanceMarkRequest(
            demo_mode=True,
            selfie_photo_data_url=frame,
            selfie_frames_data_urls=[frame] * 8,
        )

    def test_request_model_requires_schedule_id_when_demo_off(self):
        with self.assertRaises(ValueError):
            schemas.RealtimeAttendanceMarkRequest(
                demo_mode=False,
                selfie_photo_data_url="data:image/jpeg;base64," + ("A" * 200),
                selfie_frames_data_urls=["data:image/jpeg;base64," + ("A" * 200)] * 8,
            )

        payload = schemas.RealtimeAttendanceMarkRequest(
            demo_mode=True,
            selfie_photo_data_url="data:image/jpeg;base64," + ("A" * 200),
            selfie_frames_data_urls=["data:image/jpeg;base64," + ("A" * 200)] * 8,
        )
        self.assertIsNone(payload.schedule_id)

    def test_demo_mode_verification_skips_all_persistence(self):
        payload = self._build_demo_payload()

        with mock.patch(
            "app.routers.attendance.verify_face_sequence_opencv",
            return_value={
                "available": True,
                "match": True,
                "confidence": 0.99,
                "engine": "opencv-embedding",
                "reason": "face-verified",
                "liveness": {"ok": True},
                "required_consecutive_frames": 8,
                "consecutive_frames_matched": 8,
                "accepted_frames": 8,
                "total_frames": 8,
            },
        ) as verify_patch, mock.patch(
            "app.routers.attendance.store_data_url_object"
        ) as media_patch, mock.patch(
            "app.routers.attendance._upsert_present_attendance"
        ) as upsert_patch, mock.patch(
            "app.routers.attendance._upsert_mongo_by_id"
        ) as mongo_patch, mock.patch(
            "app.routers.attendance.publish_domain_event"
        ) as publish_patch, mock.patch(
            "app.routers.attendance.enqueue_face_reverification"
        ) as reverification_patch, mock.patch(
            "app.routers.attendance.enqueue_recompute"
        ) as recompute_patch:
            response = mark_realtime_attendance(payload=payload, db=self.db, current_user=self.user)

        self.assertEqual(response.submission_id, 0)
        self.assertTrue(response.demo_mode)
        self.assertTrue(response.persistence_skipped)
        self.assertEqual(response.status, models.AttendanceSubmissionStatus.VERIFIED)
        self.assertEqual(self.db.query(models.AttendanceSubmission).count(), 0)
        self.assertEqual(self.db.query(models.AttendanceRecord).count(), 0)

        self.assertEqual(verify_patch.call_count, 2)
        media_patch.assert_not_called()
        upsert_patch.assert_not_called()
        mongo_patch.assert_not_called()
        publish_patch.assert_not_called()
        reverification_patch.assert_not_called()
        recompute_patch.assert_not_called()

    def test_demo_mode_rejection_still_skips_all_persistence(self):
        payload = self._build_demo_payload()

        with mock.patch(
            "app.routers.attendance.verify_face_sequence_opencv",
            return_value={
                "available": True,
                "match": False,
                "confidence": 0.18,
                "engine": "opencv-embedding",
                "reason": "liveness check failed",
                "liveness": {"ok": False},
                "required_consecutive_frames": 8,
                "consecutive_frames_matched": 0,
                "accepted_frames": 0,
                "total_frames": 8,
            },
        ), mock.patch(
            "app.routers.attendance.store_data_url_object"
        ) as media_patch:
            response = mark_realtime_attendance(payload=payload, db=self.db, current_user=self.user)

        self.assertEqual(response.status, models.AttendanceSubmissionStatus.REJECTED)
        self.assertTrue(response.demo_mode)
        self.assertTrue(response.persistence_skipped)
        self.assertIn("did not save any attendance data", response.message.lower())
        self.assertEqual(self.db.query(models.AttendanceSubmission).count(), 0)
        self.assertEqual(self.db.query(models.AttendanceRecord).count(), 0)
        media_patch.assert_not_called()

    def test_demo_mode_requires_match_against_enrollment_and_profile_templates(self):
        payload = self._build_demo_payload()

        with mock.patch(
            "app.routers.attendance.verify_face_sequence_opencv",
            side_effect=[
                {
                    "available": True,
                    "match": True,
                    "confidence": 0.99,
                    "engine": "opencv-dnn-yunet-sface-v1",
                    "reason": "verified",
                    "liveness": {"ok": True},
                    "required_consecutive_frames": 8,
                    "consecutive_frames_matched": 8,
                    "accepted_frames": 8,
                    "total_frames": 8,
                },
                {
                    "available": True,
                    "match": False,
                    "confidence": 0.22,
                    "engine": "opencv-dnn-yunet-sface-v1",
                    "reason": "different person",
                    "liveness": {"ok": True},
                    "required_consecutive_frames": 8,
                    "consecutive_frames_matched": 0,
                    "accepted_frames": 0,
                    "total_frames": 8,
                },
            ],
        ) as verify_patch:
            response = mark_realtime_attendance(payload=payload, db=self.db, current_user=self.user)

        self.assertEqual(verify_patch.call_count, 2)
        self.assertEqual(response.status, models.AttendanceSubmissionStatus.REJECTED)
        self.assertIn("did not save any attendance data", response.message.lower())
        self.assertEqual(self.db.query(models.AttendanceSubmission).count(), 0)

    def test_sse_messages_use_default_event_channel_for_frontend_bus(self):
        encoded = _format_sse_message(
            {
                "id": "evt-1",
                "event_type": "attendance.updated",
                "payload": {"student_id": 1101},
            }
        )

        self.assertIn("id: evt-1\n", encoded)
        self.assertIn('"event_type": "attendance.updated"', encoded)
        self.assertNotIn("\nevent:", encoded)


if __name__ == "__main__":
    unittest.main()
