from datetime import date, datetime, time, timedelta
import json
import sqlite3
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.routers.remedial import (
    create_makeup_class,
    mark_remedial_attendance,
    regenerate_remedial_code,
    send_remedial_code_to_sections,
)


class RemedialIdempotencyTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()
        self._seed()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _seed(self):
        now_dt = datetime.now().replace(second=0, microsecond=0)
        class_start = now_dt - timedelta(minutes=5)
        class_end = now_dt + timedelta(minutes=55)
        self.db.add_all(
            [
                models.Faculty(
                    id=1,
                    name="Faculty One",
                    email="faculty.one@example.com",
                    department="CSE",
                    section="P132",
                ),
                models.Course(
                    id=1,
                    code="CSE500",
                    title="Distributed Systems",
                    faculty_id=1,
                ),
                models.Student(
                    id=10,
                    name="Student One",
                    email="student.one@example.com",
                    registration_number="REG-10",
                    department="CSE",
                    semester=6,
                    section="P132",
                    profile_photo_data_url="data:image/jpeg;base64,PROFILEA",
                    enrollment_video_template_json=json.dumps({"embeddings": [[0.1, 0.2, 0.3, 0.4]]}),
                    profile_face_template_json=json.dumps({"embeddings": [[0.4, 0.3, 0.2, 0.1]]}),
                ),
                models.MakeUpClass(
                    id=11,
                    course_id=1,
                    faculty_id=1,
                    class_date=class_start.date(),
                    start_time=class_start.time(),
                    end_time=class_end.time(),
                    topic="Current Remedial",
                    sections_json=json.dumps(["P132"]),
                    class_mode="offline",
                    room_number="25-801",
                    online_link=None,
                    remedial_code="LIVE500A",
                    code_generated_at=now_dt - timedelta(minutes=6),
                    code_expires_at=now_dt + timedelta(minutes=10),
                    attendance_open_minutes=15,
                    scheduled_at=now_dt - timedelta(minutes=10),
                    is_active=True,
                ),
                models.RemedialMessage(
                    id=51,
                    makeup_class_id=11,
                    faculty_id=1,
                    student_id=10,
                    section="P132",
                    remedial_code="LIVE500A",
                    message="Old message",
                    created_at=now_dt - timedelta(minutes=2),
                ),
            ]
        )
        self.db.commit()

    def _faculty_user(self) -> models.AuthUser:
        return models.AuthUser(
            id=101,
            email="faculty.one@example.com",
            password_hash="x",
            role=models.UserRole.FACULTY,
            faculty_id=1,
            student_id=None,
            is_active=True,
        )

    def _student_user(self) -> models.AuthUser:
        return models.AuthUser(
            id=201,
            email="student.one@example.com",
            password_hash="x",
            role=models.UserRole.STUDENT,
            faculty_id=None,
            student_id=10,
            is_active=True,
        )

    def test_create_makeup_class_retries_unique_code_collision_on_commit(self):
        payload = schemas.MakeUpClassCreate(
            course_id=1,
            faculty_id=1,
            class_date=date.today() + timedelta(days=2),
            start_time=time(15, 0),
            end_time=time(16, 0),
            topic="Retry scheduling",
            sections=["P132"],
            class_mode="offline",
            room_number="34-101",
        )
        real_commit = self.db.commit
        commit_calls = {"count": 0}

        def flaky_commit():
            commit_calls["count"] += 1
            if commit_calls["count"] == 1:
                raise IntegrityError(
                    "INSERT INTO makeup_classes",
                    {},
                    sqlite3.IntegrityError("UNIQUE constraint failed: makeup_classes.remedial_code"),
                )
            return real_commit()

        with patch("app.routers.remedial._generate_remedial_code", side_effect=["DUPE500A", "FRESH500"]), patch.object(
            self.db,
            "commit",
            side_effect=flaky_commit,
        ), patch("app.routers.remedial._sync_makeup_class_to_mongo", return_value=None), patch(
            "app.routers.remedial.mirror_event",
            return_value=None,
        ):
            out = create_makeup_class(payload=payload, db=self.db, current_user=self._faculty_user())

        self.assertEqual(out.remedial_code, "FRESH500")
        self.assertEqual(
            self.db.query(models.MakeUpClass).filter(models.MakeUpClass.remedial_code == "FRESH500").count(),
            1,
        )

    def test_create_makeup_class_succeeds_when_mirror_side_effects_fail(self):
        payload = schemas.MakeUpClassCreate(
            course_code="CSE550",
            course_title="Cloud Systems",
            faculty_id=1,
            class_date=date.today() + timedelta(days=2),
            start_time=time(17, 0),
            end_time=time(18, 0),
            topic="Mirror fallback",
            sections=["P132"],
            class_mode="offline",
            room_number="34-102",
        )

        with patch("app.routers.remedial.mirror_document", side_effect=RuntimeError("mongo down")), patch(
            "app.routers.remedial.mirror_event",
            side_effect=RuntimeError("event down"),
        ):
            out = create_makeup_class(payload=payload, db=self.db, current_user=self._faculty_user())

        self.assertEqual(out.course_id, 2)
        class_row = self.db.get(models.MakeUpClass, out.id)
        self.assertIsNotNone(class_row)
        self.assertTrue(bool(class_row.is_active))

    def test_create_makeup_class_uses_remedial_timezone_clock_for_same_day_rollover(self):
        fixed_now = datetime(2030, 1, 15, 23, 30)
        payload = schemas.MakeUpClassCreate(
            course_id=1,
            faculty_id=1,
            class_date=fixed_now.date(),
            start_time=time(23, 0),
            end_time=time(23, 45),
            topic="Late-night rollover",
            sections=["P132"],
            class_mode="offline",
            room_number="34-103",
        )

        with patch("app.routers.remedial._remedial_now", return_value=fixed_now), patch(
            "app.routers.remedial.mirror_document",
            return_value=None,
        ), patch("app.routers.remedial.mirror_event", return_value=None):
            out = create_makeup_class(payload=payload, db=self.db, current_user=self._faculty_user())

        self.assertEqual(out.class_date, fixed_now.date() + timedelta(days=1))

    def test_create_online_makeup_class_preserves_custom_online_link(self):
        payload = schemas.MakeUpClassCreate(
            course_id=1,
            faculty_id=1,
            class_date=date.today() + timedelta(days=2),
            start_time=time(15, 0),
            end_time=time(16, 0),
            topic="Custom online remedial",
            sections=["P132"],
            class_mode="online",
            online_link="https://meet.example.edu/remedial/cse500",
        )

        with patch("app.routers.remedial.mirror_document", return_value=None), patch(
            "app.routers.remedial.mirror_event",
            return_value=None,
        ):
            out = create_makeup_class(payload=payload, db=self.db, current_user=self._faculty_user())

        self.assertEqual(out.online_link, "https://meet.example.edu/remedial/cse500")
        class_row = self.db.get(models.MakeUpClass, out.id)
        self.assertEqual(class_row.online_link, "https://meet.example.edu/remedial/cse500")

    def test_send_message_retries_after_unique_commit_conflict(self):
        real_commit = self.db.commit
        commit_calls = {"count": 0}

        def flaky_commit():
            commit_calls["count"] += 1
            if commit_calls["count"] == 1:
                raise IntegrityError(
                    "UPDATE remedial_messages",
                    {},
                    sqlite3.IntegrityError("UNIQUE constraint failed: remedial_messages.makeup_class_id, remedial_messages.student_id"),
                )
            return real_commit()

        with patch.object(self.db, "commit", side_effect=flaky_commit), patch(
            "app.routers.remedial.mirror_document",
            return_value=None,
        ), patch("app.routers.remedial.mirror_event", return_value=None):
            out = send_remedial_code_to_sections(
                class_id=11,
                payload=schemas.RemedialSendMessageRequest(custom_message="Retry-safe message"),
                db=self.db,
                current_user=self._faculty_user(),
            )

        self.assertEqual(out.recipients, 1)
        row = (
            self.db.query(models.RemedialMessage)
            .filter(
                models.RemedialMessage.makeup_class_id == 11,
                models.RemedialMessage.student_id == 10,
            )
            .one()
        )
        self.assertEqual(row.message, "Retry-safe message")

    def test_mark_attendance_uses_remedial_timezone_clock_for_window_check(self):
        self.db.query(models.RemedialAttendance).delete()
        class_row = self.db.get(models.MakeUpClass, 11)
        fixed_now = datetime(2030, 1, 15, 10, 5)
        class_row.class_date = fixed_now.date()
        class_row.start_time = (fixed_now - timedelta(minutes=5)).time()
        class_row.end_time = (fixed_now + timedelta(minutes=55)).time()
        class_row.code_expires_at = fixed_now + timedelta(minutes=10)
        self.db.commit()

        payload = schemas.RemedialAttendanceMark(
            remedial_code="LIVE500A",
            student_id=10,
            selfie_photo_data_url="data:image/jpeg;base64,SELFIEA",
            selfie_frames_data_urls=[
                "data:image/jpeg;base64,SELFIEA",
                "data:image/jpeg;base64,SELFIEB",
                "data:image/jpeg;base64,SELFIEC",
                "data:image/jpeg;base64,SELFIED",
                "data:image/jpeg;base64,SELFIEE",
                "data:image/jpeg;base64,SELFIEF",
            ],
        )

        with patch("app.routers.remedial._remedial_now", return_value=fixed_now), patch(
            "app.routers.remedial._verify_remedial_face_payload",
            return_value=("frame", 0.99, "opencv", "verified"),
        ), patch("app.routers.remedial.mirror_document", return_value=None), patch(
            "app.routers.remedial.mirror_event",
            return_value=None,
        ):
            out = mark_remedial_attendance(payload=payload, db=self.db, current_user=self._student_user())

        self.assertEqual(out["message"], "Remedial attendance marked")

    def test_regenerate_code_succeeds_when_mirror_side_effects_fail(self):
        original_code = self.db.get(models.MakeUpClass, 11).remedial_code

        with patch("app.routers.remedial.mirror_document", side_effect=RuntimeError("mongo down")), patch(
            "app.routers.remedial.mirror_event",
            side_effect=RuntimeError("event down"),
        ), patch("app.routers.remedial._generate_remedial_code", return_value="REGEN501"):
            out = regenerate_remedial_code(class_id=11, db=self.db, current_user=self._faculty_user())

        self.assertEqual(out.remedial_code, "REGEN501")
        self.assertNotEqual(original_code, out.remedial_code)
        self.assertEqual(self.db.get(models.MakeUpClass, 11).remedial_code, "REGEN501")

    def test_mark_attendance_returns_already_marked_after_race(self):
        self.db.add(
            models.RemedialAttendance(
                makeup_class_id=11,
                student_id=10,
                source="remedial-face-opencv-verified",
            )
        )
        self.db.commit()

        payload = schemas.RemedialAttendanceMark(
            remedial_code="LIVE500A",
            student_id=10,
            selfie_photo_data_url="data:image/jpeg;base64,SELFIEA",
            selfie_frames_data_urls=[
                "data:image/jpeg;base64,SELFIEA",
                "data:image/jpeg;base64,SELFIEB",
                "data:image/jpeg;base64,SELFIEC",
                "data:image/jpeg;base64,SELFIED",
                "data:image/jpeg;base64,SELFIEE",
                "data:image/jpeg;base64,SELFIEF",
            ],
        )

        def duplicate_commit():
            raise IntegrityError(
                "INSERT INTO remedial_attendance",
                {},
                sqlite3.IntegrityError(
                    "UNIQUE constraint failed: remedial_attendance.makeup_class_id, remedial_attendance.student_id"
                ),
            )

        real_query = self.db.query
        first_lookup = {"pending": True}

        class _AttendanceQueryProxy:
            def __init__(self, query):
                self._query = query

            def filter(self, *args, **kwargs):
                self._query = self._query.filter(*args, **kwargs)
                return self

            def first(self):
                if first_lookup["pending"]:
                    first_lookup["pending"] = False
                    return None
                return self._query.first()

            def __getattr__(self, name):
                return getattr(self._query, name)

        def query_wrapper(*entities, **kwargs):
            query = real_query(*entities, **kwargs)
            if first_lookup["pending"] and entities and entities[0] is models.RemedialAttendance:
                return _AttendanceQueryProxy(query)
            return query

        with patch("app.routers.remedial._verify_remedial_face_payload", return_value=("frame", 0.99, "opencv", "verified")), patch.object(
            self.db,
            "commit",
            side_effect=duplicate_commit,
        ), patch.object(
            self.db,
            "query",
            side_effect=query_wrapper,
        ), patch("app.routers.remedial.mirror_document", return_value=None), patch(
            "app.routers.remedial.mirror_event",
            return_value=None,
        ):
            out = mark_remedial_attendance(payload=payload, db=self.db, current_user=self._student_user())

        self.assertEqual(out["message"], "Attendance already marked")
        self.assertEqual(
            self.db.query(models.RemedialAttendance)
            .filter(
                models.RemedialAttendance.makeup_class_id == 11,
                models.RemedialAttendance.student_id == 10,
            )
            .count(),
            1,
        )

    def test_mark_attendance_succeeds_when_mirror_side_effects_fail(self):
        self.db.query(models.RemedialAttendance).delete()
        self.db.commit()

        payload = schemas.RemedialAttendanceMark(
            remedial_code="LIVE500A",
            student_id=10,
            selfie_photo_data_url="data:image/jpeg;base64,SELFIEA",
            selfie_frames_data_urls=[
                "data:image/jpeg;base64,SELFIEA",
                "data:image/jpeg;base64,SELFIEB",
                "data:image/jpeg;base64,SELFIEC",
                "data:image/jpeg;base64,SELFIED",
                "data:image/jpeg;base64,SELFIEE",
                "data:image/jpeg;base64,SELFIEF",
            ],
        )

        with patch("app.routers.remedial._verify_remedial_face_payload", return_value=("frame", 0.99, "opencv", "verified")), patch(
            "app.routers.remedial.mirror_document",
            side_effect=RuntimeError("mongo down"),
        ), patch("app.routers.remedial.mirror_event", side_effect=RuntimeError("event down")):
            out = mark_remedial_attendance(payload=payload, db=self.db, current_user=self._student_user())

        self.assertEqual(out["message"], "Remedial attendance marked")
        self.assertEqual(
            self.db.query(models.RemedialAttendance)
            .filter(
                models.RemedialAttendance.makeup_class_id == 11,
                models.RemedialAttendance.student_id == 10,
            )
            .count(),
            1,
        )

    def test_mark_attendance_survives_recovery_followup_failure(self):
        self.db.query(models.RemedialAttendance).delete()
        now_dt = datetime.now().replace(second=0, microsecond=0)
        self.db.add(
            models.AttendanceRecoveryPlan(
                id=601,
                student_id=10,
                course_id=1,
                faculty_id=1,
                risk_level=models.AttendanceRecoveryRiskLevel.WATCH,
                status=models.AttendanceRecoveryPlanStatus.ACTIVE,
                attendance_percent=62.5,
                present_count=5,
                absent_count=3,
                delivered_count=8,
                consecutive_absences=2,
                missed_remedials=1,
                recommended_makeup_class_id=11,
                parent_alert_allowed=False,
                recovery_due_at=now_dt + timedelta(days=1),
                summary="Student should attend the next remedial session.",
                last_absent_on=now_dt.date(),
                last_evaluated_at=now_dt,
                created_at=now_dt,
                updated_at=now_dt,
            )
        )
        self.db.flush()
        self.db.add(
            models.AttendanceRecoveryAction(
                id=701,
                plan_id=601,
                action_type=models.AttendanceRecoveryActionType.REMEDIAL_SLOT,
                status=models.AttendanceRecoveryActionStatus.PENDING,
                title="Attend suggested remedial",
                description="Attend the scheduled remedial to recover attendance.",
                recipient_role="student",
                recipient_email="student.one@example.com",
                target_makeup_class_id=11,
                scheduled_for=now_dt + timedelta(hours=1),
                metadata_json="{}",
                created_at=now_dt,
                updated_at=now_dt,
            )
        )
        self.db.commit()

        payload = schemas.RemedialAttendanceMark(
            remedial_code="LIVE500A",
            student_id=10,
            selfie_photo_data_url="data:image/jpeg;base64,SELFIEA",
            selfie_frames_data_urls=[
                "data:image/jpeg;base64,SELFIEA",
                "data:image/jpeg;base64,SELFIEB",
                "data:image/jpeg;base64,SELFIEC",
                "data:image/jpeg;base64,SELFIED",
                "data:image/jpeg;base64,SELFIEE",
                "data:image/jpeg;base64,SELFIEF",
            ],
        )

        with patch("app.routers.remedial._verify_remedial_face_payload", return_value=("frame", 0.99, "opencv", "verified")), patch(
            "app.routers.remedial.evaluate_attendance_recovery",
            side_effect=RuntimeError("recovery refresh failed"),
        ), patch("app.routers.remedial.mirror_document", return_value=None), patch(
            "app.routers.remedial.mirror_event",
            return_value=None,
        ):
            out = mark_remedial_attendance(payload=payload, db=self.db, current_user=self._student_user())

        self.assertEqual(out["message"], "Remedial attendance marked")
        self.assertEqual(
            self.db.query(models.RemedialAttendance)
            .filter(
                models.RemedialAttendance.makeup_class_id == 11,
                models.RemedialAttendance.student_id == 10,
            )
            .count(),
            1,
        )
        action_row = self.db.get(models.AttendanceRecoveryAction, 701)
        self.assertEqual(action_row.status, models.AttendanceRecoveryActionStatus.PENDING)
        self.assertIsNone(action_row.completed_at)


if __name__ == "__main__":
    unittest.main()
