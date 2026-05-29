import json
import unittest
from datetime import date, datetime, time
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.routers.attendance import (
    _attendance_attempt_token_hash,
    _attendance_session_code_hash,
    _campus_datetime_to_epoch_ms,
    _generate_attendance_session_code,
    mark_realtime_attendance,
    open_schedule_attendance_session,
    validate_schedule_attendance_session_code,
)
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

    def _seed_realtime_schedule_pair(self):
        self.class_date = date(2026, 5, 22)
        self.db.add_all(
            [
                models.Faculty(
                    id=3101,
                    name="Realtime Faculty",
                    email="realtime.faculty@example.com",
                    department="CSE",
                    section="P132",
                ),
                models.Course(
                    id=4101,
                    code="PES319",
                    title="Soft Skills-II",
                    faculty_id=3101,
                ),
                models.Enrollment(
                    id=5101,
                    student_id=1101,
                    course_id=4101,
                ),
                models.ClassSchedule(
                    id=6101,
                    course_id=4101,
                    faculty_id=3101,
                    weekday=self.class_date.weekday(),
                    start_time=time(10, 0),
                    end_time=time(11, 0),
                    classroom_label="423ZK",
                    attendance_latitude=31.253000,
                    attendance_longitude=75.705000,
                    attendance_radius_m=75.0,
                    attendance_location_label="423ZK",
                    is_active=True,
                ),
                models.ClassSchedule(
                    id=6102,
                    course_id=4101,
                    faculty_id=3101,
                    weekday=self.class_date.weekday(),
                    start_time=time(11, 0),
                    end_time=time(12, 0),
                    classroom_label="423ZK",
                    attendance_latitude=31.253000,
                    attendance_longitude=75.705000,
                    attendance_radius_m=75.0,
                    attendance_location_label="423ZK",
                    is_active=True,
                ),
            ]
        )
        self.db.commit()
        current_schedule = self.db.get(models.ClassSchedule, 6102)
        self.realtime_now = datetime.combine(self.class_date, time(11, 5))
        self.realtime_session_code = _generate_attendance_session_code(
            current_schedule,
            self.class_date,
            now_dt=self.realtime_now,
        )
        self.realtime_attempt_token = "test-attendance-attempt-token"
        self.realtime_session_code_hash = _attendance_session_code_hash(
            self.realtime_session_code,
            schedule=current_schedule,
            class_date=self.class_date,
            now_dt=self.realtime_now,
        )
        self.db.add_all(
            [
                models.ClassAttendanceSession(
                    id=7102,
                    schedule_id=6102,
                    course_id=4101,
                    faculty_id=3101,
                    class_date=self.class_date,
                    session_code_hash=self.realtime_session_code_hash,
                    code_rotation_seconds=20,
                    current_code_expires_at=datetime.combine(self.class_date, time(11, 5, 20)),
                    generated_at=datetime.combine(self.class_date, time(11, 0)),
                    expires_at=datetime.combine(self.class_date, time(11, 10)),
                    opened_by_user_id=3101,
                    is_active=True,
                ),
                models.AttendanceAttemptToken(
                    id=8102,
                    attendance_session_id=7102,
                    schedule_id=6102,
                    student_id=1101,
                    class_date=self.class_date,
                    token_hash=_attendance_attempt_token_hash(self.realtime_attempt_token),
                    session_code_hash=self.realtime_session_code_hash,
                    issued_at=datetime.combine(self.class_date, time(11, 5)),
                    expires_at=datetime.combine(self.class_date, time(11, 9)),
                    attempt_count=0,
                    max_attempts=10,
                    created_at=datetime.combine(self.class_date, time(11, 5)),
                    updated_at=datetime.combine(self.class_date, time(11, 5)),
                ),
            ]
        )
        self.db.commit()

    def _build_realtime_payload(
        self,
        schedule_id: int,
        *,
        latitude: float | None = 31.253000,
        longitude: float | None = 75.705000,
        accuracy_m: float | None = 12.0,
        attendance_session_code: str | None = None,
        attendance_attempt_token: str | None = None,
    ) -> schemas.RealtimeAttendanceMarkRequest:
        frame = "data:image/jpeg;base64," + ("C" * 320)
        return schemas.RealtimeAttendanceMarkRequest(
            schedule_id=schedule_id,
            selfie_photo_data_url=frame,
            selfie_frames_data_urls=[frame] * 8,
            location_latitude=latitude,
            location_longitude=longitude,
            location_accuracy_m=accuracy_m,
            location_timestamp_ms=_campus_datetime_to_epoch_ms(datetime.combine(self.class_date, time(11, 5))),
            attendance_session_code=(
                attendance_session_code
                if attendance_session_code is not None
                else getattr(self, "realtime_session_code", None)
            ),
            attendance_attempt_token=(
                attendance_attempt_token
                if attendance_attempt_token is not None
                else getattr(self, "realtime_attempt_token", None)
            ),
            browser_fingerprint="test-browser-fingerprint",
            client_integrity_flags=["secure_context"],
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

    def test_realtime_mark_only_persists_current_open_schedule_slot(self):
        self._seed_realtime_schedule_pair()
        payload = self._build_realtime_payload(schedule_id=6102)

        face_verdict = {
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
        }
        with (
            mock.patch("app.routers.attendance.date") as date_mock,
            mock.patch("app.routers.attendance.datetime") as datetime_mock,
            mock.patch("app.routers.attendance.verify_face_sequence_opencv", return_value=face_verdict),
            mock.patch("app.routers.attendance.store_data_url_object") as media_patch,
            mock.patch("app.routers.attendance._upsert_mongo_by_id"),
            mock.patch("app.routers.attendance.publish_domain_event"),
            mock.patch("app.routers.attendance.enqueue_face_reverification"),
            mock.patch("app.routers.attendance.enqueue_recompute"),
            mock.patch("app.routers.attendance.evaluate_attendance_recovery"),
        ):
            date_mock.today.return_value = self.class_date
            date_mock.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
            datetime_mock.now.return_value = datetime.combine(self.class_date, time(11, 5))
            datetime_mock.combine.side_effect = datetime.combine
            datetime_mock.utcnow.side_effect = datetime.utcnow
            media_patch.return_value = type("Media", (), {"object_key": "attendance-selfie/test.jpg"})()

            response = mark_realtime_attendance(payload=payload, db=self.db, current_user=self.user)

        self.assertEqual(response.status, models.AttendanceSubmissionStatus.VERIFIED)
        submissions = self.db.query(models.AttendanceSubmission).all()
        self.assertEqual(len(submissions), 1)
        self.assertEqual(submissions[0].schedule_id, 6102)
        self.assertEqual(
            self.db.query(models.AttendanceSubmission)
            .filter(models.AttendanceSubmission.schedule_id == 6101)
            .count(),
            0,
        )

    def test_realtime_mark_rejects_previous_or_future_slot_even_with_valid_face(self):
        self._seed_realtime_schedule_pair()
        payload = self._build_realtime_payload(schedule_id=6101)

        with (
            mock.patch("app.routers.attendance.date") as date_mock,
            mock.patch("app.routers.attendance.datetime") as datetime_mock,
            mock.patch("app.routers.attendance.verify_face_sequence_opencv") as verify_patch,
        ):
            date_mock.today.return_value = self.class_date
            date_mock.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
            datetime_mock.now.return_value = datetime.combine(self.class_date, time(11, 5))
            datetime_mock.combine.side_effect = datetime.combine
            datetime_mock.utcnow.side_effect = datetime.utcnow
            with self.assertRaises(Exception) as ctx:
                mark_realtime_attendance(payload=payload, db=self.db, current_user=self.user)

        verify_patch.assert_not_called()
        self.assertIn("Attendance window is closed", str(ctx.exception))
        self.assertEqual(self.db.query(models.AttendanceSubmission).count(), 0)
        self.assertEqual(self.db.query(models.AttendanceRecord).count(), 0)

    def test_faculty_opens_class_session_code_for_active_window(self):
        self._seed_realtime_schedule_pair()
        faculty_user = models.AuthUser(
            id=3101,
            email="realtime.faculty@example.com",
            password_hash="hash",
            role=models.UserRole.FACULTY,
            faculty_id=3101,
            is_active=True,
        )

        with (
            mock.patch("app.routers.attendance.date") as date_mock,
            mock.patch("app.routers.attendance.datetime") as datetime_mock,
            mock.patch("app.routers.attendance._upsert_class_attendance_session_document") as mongo_patch,
            mock.patch("app.routers.attendance.publish_domain_event") as publish_patch,
        ):
            date_mock.today.return_value = self.class_date
            date_mock.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
            datetime_mock.now.return_value = datetime.combine(self.class_date, time(11, 5))
            datetime_mock.combine.side_effect = datetime.combine
            datetime_mock.utcnow.side_effect = datetime.utcnow

            response = open_schedule_attendance_session(schedule_id=6102, db=self.db, current_user=faculty_user)

        self.assertEqual(response.schedule_id, 6102)
        self.assertEqual(response.session_code, self.realtime_session_code)
        self.assertEqual(response.expires_at, datetime.combine(self.class_date, time(11, 10)))
        self.assertEqual(response.code_rotation_seconds, 20)
        self.assertEqual(response.code_expires_at, datetime.combine(self.class_date, time(11, 5, 20)))
        session = self.db.query(models.ClassAttendanceSession).filter_by(schedule_id=6102).one()
        self.assertEqual(session.session_code_hash, _attendance_session_code_hash(
            self.realtime_session_code,
            schedule=self.db.get(models.ClassSchedule, 6102),
            class_date=self.class_date,
            now_dt=datetime.combine(self.class_date, time(11, 5)),
        ))
        mongo_patch.assert_called_once()
        publish_patch.assert_called_once()

    def test_student_validates_rotating_class_code_before_camera(self):
        self._seed_realtime_schedule_pair()
        payload = schemas.AttendanceCodeValidateRequest(
            attendance_session_code=self.realtime_session_code,
            browser_fingerprint="student-browser-fingerprint",
            client_integrity_flags=["secure_context"],
        )

        with (
            mock.patch("app.routers.attendance.date") as date_mock,
            mock.patch("app.routers.attendance.datetime") as datetime_mock,
            mock.patch("app.routers.attendance.publish_domain_event") as publish_patch,
        ):
            date_mock.today.return_value = self.class_date
            date_mock.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
            datetime_mock.now.return_value = datetime.combine(self.class_date, time(11, 5))
            datetime_mock.combine.side_effect = datetime.combine
            datetime_mock.utcnow.side_effect = datetime.utcnow

            response = validate_schedule_attendance_session_code(
                schedule_id=6102,
                payload=payload,
                db=self.db,
                current_user=self.user,
            )

        self.assertEqual(response.schedule_id, 6102)
        self.assertTrue(response.attendance_attempt_token)
        self.assertEqual(response.code_rotation_seconds, 20)
        self.assertEqual(response.room, "423ZK")
        self.assertEqual(response.allowed_radius_m, 75.0)
        created_attempt = (
            self.db.query(models.AttendanceAttemptToken)
            .filter(models.AttendanceAttemptToken.token_hash == _attendance_attempt_token_hash(response.attendance_attempt_token))
            .one()
        )
        self.assertEqual(created_attempt.session_code_hash, self.realtime_session_code_hash)
        self.assertIsNotNone(created_attempt.browser_fingerprint_hash)
        publish_patch.assert_called_once()

    def test_realtime_mark_rejects_missing_browser_location_before_face_check(self):
        self._seed_realtime_schedule_pair()
        payload = self._build_realtime_payload(schedule_id=6102, latitude=None, longitude=None, accuracy_m=None)

        with (
            mock.patch("app.routers.attendance.date") as date_mock,
            mock.patch("app.routers.attendance.datetime") as datetime_mock,
            mock.patch("app.routers.attendance.verify_face_sequence_opencv") as verify_patch,
            mock.patch("app.routers.attendance._sync_location_rejected_submission_to_mongo") as mongo_patch,
            mock.patch("app.routers.attendance.publish_domain_event") as publish_patch,
        ):
            date_mock.today.return_value = self.class_date
            date_mock.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
            datetime_mock.now.return_value = datetime.combine(self.class_date, time(11, 5))
            datetime_mock.combine.side_effect = datetime.combine
            datetime_mock.utcnow.side_effect = datetime.utcnow
            with self.assertRaises(Exception) as ctx:
                mark_realtime_attendance(payload=payload, db=self.db, current_user=self.user)

        verify_patch.assert_not_called()
        self.assertIn("Browser location is required", str(ctx.exception))
        mongo_patch.assert_called_once()
        publish_patch.assert_called_once()
        submission = self.db.query(models.AttendanceSubmission).one()
        self.assertEqual(submission.status, models.AttendanceSubmissionStatus.REJECTED)
        self.assertEqual(submission.ai_model, "gps-geofence-v1")
        self.assertIsNone(submission.selfie_photo_object_key)
        self.assertIn("Browser location is required", submission.ai_reason)
        self.assertEqual(self.db.query(models.AttendanceRecord).count(), 0)

    def test_student_code_validation_rejects_invalid_rotating_code_before_face_check(self):
        self._seed_realtime_schedule_pair()
        payload = schemas.AttendanceCodeValidateRequest(
            attendance_session_code="WRNG-0000",
            browser_fingerprint="student-browser-fingerprint",
        )

        with (
            mock.patch("app.routers.attendance.date") as date_mock,
            mock.patch("app.routers.attendance.datetime") as datetime_mock,
        ):
            date_mock.today.return_value = self.class_date
            date_mock.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
            datetime_mock.now.return_value = datetime.combine(self.class_date, time(11, 5))
            datetime_mock.combine.side_effect = datetime.combine
            datetime_mock.utcnow.side_effect = datetime.utcnow
            with self.assertRaises(Exception) as ctx:
                validate_schedule_attendance_session_code(
                    schedule_id=6102,
                    payload=payload,
                    db=self.db,
                    current_user=self.user,
                )

        self.assertIn("Attendance session code rejected", str(ctx.exception))
        self.assertEqual(self.db.query(models.AttendanceSubmission).count(), 0)
        self.assertEqual(self.db.query(models.AttendanceRecord).count(), 0)

    def test_realtime_mark_rejects_missing_attempt_token_before_face_check(self):
        self._seed_realtime_schedule_pair()
        payload = self._build_realtime_payload(schedule_id=6102, attendance_attempt_token="")

        with (
            mock.patch("app.routers.attendance.date") as date_mock,
            mock.patch("app.routers.attendance.datetime") as datetime_mock,
            mock.patch("app.routers.attendance.verify_face_sequence_opencv") as verify_patch,
            mock.patch("app.routers.attendance._sync_location_rejected_submission_to_mongo") as mongo_patch,
            mock.patch("app.routers.attendance.publish_domain_event") as publish_patch,
        ):
            date_mock.today.return_value = self.class_date
            date_mock.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
            datetime_mock.now.return_value = datetime.combine(self.class_date, time(11, 5))
            datetime_mock.combine.side_effect = datetime.combine
            datetime_mock.utcnow.side_effect = datetime.utcnow
            with self.assertRaises(Exception) as ctx:
                mark_realtime_attendance(payload=payload, db=self.db, current_user=self.user)

        verify_patch.assert_not_called()
        self.assertIn("Validate the faculty attendance code", str(ctx.exception))
        mongo_patch.assert_called_once()
        publish_patch.assert_called_once()
        submission = self.db.query(models.AttendanceSubmission).one()
        self.assertEqual(submission.status, models.AttendanceSubmissionStatus.REJECTED)
        self.assertEqual(submission.ai_model, "attendance-session-token-v1")
        self.assertIsNone(submission.selfie_photo_object_key)
        self.assertEqual(self.db.query(models.AttendanceRecord).count(), 0)

    def test_realtime_mark_rejects_outside_class_geofence_before_face_check(self):
        self._seed_realtime_schedule_pair()
        payload = self._build_realtime_payload(schedule_id=6102, latitude=31.263000, longitude=75.715000)

        with (
            mock.patch("app.routers.attendance.date") as date_mock,
            mock.patch("app.routers.attendance.datetime") as datetime_mock,
            mock.patch("app.routers.attendance.verify_face_sequence_opencv") as verify_patch,
            mock.patch("app.routers.attendance._sync_location_rejected_submission_to_mongo") as mongo_patch,
            mock.patch("app.routers.attendance.publish_domain_event") as publish_patch,
        ):
            date_mock.today.return_value = self.class_date
            date_mock.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
            datetime_mock.now.return_value = datetime.combine(self.class_date, time(11, 5))
            datetime_mock.combine.side_effect = datetime.combine
            datetime_mock.utcnow.side_effect = datetime.utcnow
            with self.assertRaises(Exception) as ctx:
                mark_realtime_attendance(payload=payload, db=self.db, current_user=self.user)

        verify_patch.assert_not_called()
        self.assertIn("Attendance location rejected", str(ctx.exception))
        mongo_patch.assert_called_once()
        publish_patch.assert_called_once()
        submission = self.db.query(models.AttendanceSubmission).one()
        self.assertEqual(submission.status, models.AttendanceSubmissionStatus.REJECTED)
        self.assertEqual(submission.ai_model, "gps-geofence-v1")
        self.assertIsNone(submission.selfie_photo_object_key)
        self.assertGreater(float(submission.location_distance_m or 0.0), float(submission.location_allowed_radius_m or 0.0))
        self.assertEqual(self.db.query(models.AttendanceRecord).count(), 0)

    def test_realtime_mark_rejects_unconfigured_class_location_without_student_penalty(self):
        self._seed_realtime_schedule_pair()
        schedule = self.db.get(models.ClassSchedule, 6102)
        schedule.attendance_latitude = None
        schedule.attendance_longitude = None
        schedule.attendance_radius_m = None
        schedule.attendance_location_label = None
        self.db.commit()
        payload = self._build_realtime_payload(schedule_id=6102)

        with (
            mock.patch("app.routers.attendance.date") as date_mock,
            mock.patch("app.routers.attendance.datetime") as datetime_mock,
            mock.patch("app.routers.attendance.verify_face_sequence_opencv") as verify_patch,
            mock.patch("app.routers.attendance._sync_location_rejected_submission_to_mongo") as mongo_patch,
            mock.patch("app.routers.attendance.publish_domain_event") as publish_patch,
        ):
            date_mock.today.return_value = self.class_date
            date_mock.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
            datetime_mock.now.return_value = datetime.combine(self.class_date, time(11, 5))
            datetime_mock.combine.side_effect = datetime.combine
            datetime_mock.utcnow.side_effect = datetime.utcnow
            with self.assertRaises(Exception) as ctx:
                mark_realtime_attendance(payload=payload, db=self.db, current_user=self.user)

        verify_patch.assert_not_called()
        mongo_patch.assert_not_called()
        publish_patch.assert_not_called()
        self.assertIn("Attendance location is not configured", str(ctx.exception))
        self.assertEqual(self.db.query(models.AttendanceSubmission).count(), 0)
        self.assertEqual(self.db.query(models.AttendanceRecord).count(), 0)

    def test_realtime_mark_persists_verified_location_audit_fields(self):
        self._seed_realtime_schedule_pair()
        payload = self._build_realtime_payload(schedule_id=6102, latitude=31.253010, longitude=75.705010, accuracy_m=18.0)
        face_verdict = {
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
        }

        with (
            mock.patch("app.routers.attendance.date") as date_mock,
            mock.patch("app.routers.attendance.datetime") as datetime_mock,
            mock.patch("app.routers.attendance.verify_face_sequence_opencv", return_value=face_verdict),
            mock.patch("app.routers.attendance.store_data_url_object") as media_patch,
            mock.patch("app.routers.attendance._upsert_mongo_by_id"),
            mock.patch("app.routers.attendance.publish_domain_event"),
            mock.patch("app.routers.attendance.enqueue_face_reverification"),
            mock.patch("app.routers.attendance.enqueue_recompute"),
            mock.patch("app.routers.attendance.evaluate_attendance_recovery"),
        ):
            date_mock.today.return_value = self.class_date
            date_mock.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
            datetime_mock.now.return_value = datetime.combine(self.class_date, time(11, 5))
            datetime_mock.combine.side_effect = datetime.combine
            datetime_mock.utcnow.side_effect = datetime.utcnow
            media_patch.return_value = type("Media", (), {"object_key": "attendance-selfie/test.jpg"})()

            response = mark_realtime_attendance(payload=payload, db=self.db, current_user=self.user)

        self.assertEqual(response.status, models.AttendanceSubmissionStatus.VERIFIED)
        self.assertIsNotNone(response.location_distance_m)
        self.assertGreaterEqual(response.location_allowed_radius_m, 75.0)
        submission = self.db.query(models.AttendanceSubmission).one()
        self.assertAlmostEqual(submission.location_latitude, 31.253010)
        self.assertAlmostEqual(submission.location_longitude, 75.705010)
        self.assertAlmostEqual(submission.location_accuracy_m, 18.0)
        self.assertIsNotNone(submission.location_distance_m)
        self.assertGreaterEqual(float(submission.location_allowed_radius_m or 0), 75.0)
        self.assertEqual(submission.attendance_session_id, 7102)
        self.assertIsNotNone(submission.attendance_session_code_hash)
        self.assertEqual(submission.attendance_attempt_token_hash, _attendance_attempt_token_hash(self.realtime_attempt_token))
        self.assertIsNotNone(submission.client_integrity_flags)
        attempt = self.db.get(models.AttendanceAttemptToken, 8102)
        self.assertEqual(attempt.attempt_count, 1)
        self.assertIsNotNone(attempt.consumed_at)

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
