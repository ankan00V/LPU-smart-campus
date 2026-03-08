import json
import os
import unittest
from datetime import date, datetime
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.attendance_recovery import evaluate_attendance_recovery
from app.routers.attendance import (
    get_student_attendance_aggregate,
    get_student_attendance_history,
)
from app.saarthi_service import (
    SAARTHI_ATTENDANCE_MINUTES,
    SAARTHI_COURSE_CODE,
    create_saarthi_turn,
    ensure_saarthi_bundle,
    materialize_saarthi_attendance,
)


class SaarthiAttendanceTests(unittest.TestCase):
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
        self.student = models.Student(
            id=1,
            name="Saarthi Student",
            email="saarthi.student@example.com",
            registration_number="22BCS5001",
            section="P132",
            department="CSE",
            semester=6,
        )
        self.db.add(self.student)
        self.db.commit()

    @staticmethod
    def _student_user() -> models.AuthUser:
        return models.AuthUser(
            id=9001,
            email="saarthi.student@example.com",
            password_hash="x",
            role=models.UserRole.STUDENT,
            student_id=1,
            faculty_id=None,
            is_active=True,
        )

    def test_sunday_chat_awards_single_hour_credit_once(self):
        sunday_dt = datetime(2026, 3, 8, 10, 30, 0)

        first_turn = create_saarthi_turn(
            self.db,
            student=self.student,
            message="I need help managing stress this week.",
            current_dt=sunday_dt,
            academic_start=date(2026, 3, 2),
        )
        second_turn = create_saarthi_turn(
            self.db,
            student=self.student,
            message="I am back with one more follow-up.",
            current_dt=datetime(2026, 3, 8, 19, 45, 0),
            academic_start=date(2026, 3, 2),
        )
        self.db.commit()

        bundle = ensure_saarthi_bundle(self.db, student_id=int(self.student.id))
        self.assertTrue(first_turn["attendance_awarded_now"])
        self.assertFalse(second_turn["attendance_awarded_now"])

        records = (
            self.db.query(models.AttendanceRecord)
            .filter(
                models.AttendanceRecord.student_id == int(self.student.id),
                models.AttendanceRecord.course_id == int(bundle.course.id),
            )
            .all()
        )
        events = (
            self.db.query(models.AttendanceEvent)
            .filter(
                models.AttendanceEvent.student_id == int(self.student.id),
                models.AttendanceEvent.course_id == int(bundle.course.id),
            )
            .all()
        )
        session = self.db.query(models.SaarthiSession).one()
        messages = self.db.query(models.SaarthiMessage).all()

        self.assertEqual(len(records), 1)
        self.assertEqual(len(events), 1)
        self.assertEqual(records[0].attendance_date, date(2026, 3, 8))
        self.assertEqual(records[0].status, models.AttendanceStatus.PRESENT)
        self.assertEqual(records[0].source, "saarthi-weekly-credit")
        self.assertEqual(session.attendance_credit_minutes, SAARTHI_ATTENDANCE_MINUTES)
        self.assertIsNotNone(session.attendance_marked_at)
        self.assertEqual(len(messages), 4)

        aggregate = get_student_attendance_aggregate(
            db=self.db,
            current_user=self._student_user(),
        )
        con111 = next((row for row in aggregate.courses if row.course_code == SAARTHI_COURSE_CODE), None)
        self.assertIsNotNone(con111)
        self.assertEqual(con111.attended_classes, 1)
        self.assertEqual(con111.delivered_classes, 1)
        self.assertEqual(con111.attendance_percent, 100.0)

    def test_non_sunday_chat_does_not_award_attendance(self):
        monday_dt = datetime(2026, 3, 9, 11, 0, 0)

        out = create_saarthi_turn(
            self.db,
            student=self.student,
            message="I want to talk about exams before Sunday.",
            current_dt=monday_dt,
            academic_start=date(2026, 3, 9),
        )
        self.db.commit()

        bundle = ensure_saarthi_bundle(self.db, student_id=int(self.student.id))
        records = (
            self.db.query(models.AttendanceRecord)
            .filter(
                models.AttendanceRecord.student_id == int(self.student.id),
                models.AttendanceRecord.course_id == int(bundle.course.id),
            )
            .all()
        )
        session = self.db.query(models.SaarthiSession).one()
        messages = self.db.query(models.SaarthiMessage).all()

        self.assertFalse(out["attendance_awarded_now"])
        self.assertEqual(len(records), 0)
        self.assertIsNone(session.attendance_marked_at)
        self.assertEqual(session.attendance_credit_minutes, 0)
        self.assertEqual(len(messages), 2)

    def test_missed_past_sunday_materializes_absent_record_in_aggregate_and_history(self):
        materialize_saarthi_attendance(
            self.db,
            student_id=int(self.student.id),
            academic_start=date(2026, 3, 2),
            today=date(2026, 3, 9),
        )
        self.db.commit()

        aggregate = get_student_attendance_aggregate(
            db=self.db,
            current_user=self._student_user(),
        )
        history = get_student_attendance_history(
            limit=20,
            db=self.db,
            current_user=self._student_user(),
        )

        con111 = next((row for row in aggregate.courses if row.course_code == SAARTHI_COURSE_CODE), None)
        self.assertIsNotNone(con111)
        self.assertEqual(con111.attended_classes, 0)
        self.assertEqual(con111.delivered_classes, 1)
        self.assertEqual(con111.attendance_percent, 0.0)

        saarthi_rows = [row for row in history.records if row.course_code == SAARTHI_COURSE_CODE]
        self.assertEqual(len(saarthi_rows), 1)
        self.assertEqual(saarthi_rows[0].class_date, date(2026, 3, 8))
        self.assertEqual(saarthi_rows[0].status, models.AttendanceStatus.ABSENT)
        self.assertEqual(saarthi_rows[0].source, "saarthi-mandatory-missed")

    def test_saarthi_course_is_excluded_from_recovery_automation(self):
        bundle = materialize_saarthi_attendance(
            self.db,
            student_id=int(self.student.id),
            academic_start=date(2026, 3, 2),
            today=date(2026, 3, 9),
        )
        self.db.commit()

        plan = evaluate_attendance_recovery(
            self.db,
            student_id=int(self.student.id),
            course_id=int(bundle.course.id),
        )

        self.assertIsNone(plan)

    def test_configured_gemini_llm_reply_is_used_when_available(self):
        class DummyResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(
                    {
                        "candidates": [
                            {
                                "content": {
                                    "parts": [{"text": "Live Gemini counselling reply."}],
                                }
                            }
                        ]
                    }
                ).encode("utf-8")

        with mock.patch.dict(
            os.environ,
            {
                "SAARTHI_LLM_PROVIDER": "gemini",
                "SAARTHI_LLM_REQUIRED": "true",
                "SAARTHI_LLM_MODEL": "gemini-2.5-flash",
                "GEMINI_API_KEY": "test-key",
            },
            clear=False,
        ), mock.patch("app.saarthi_service.urllib_request.urlopen", return_value=DummyResponse()):
            out = create_saarthi_turn(
                self.db,
                student=self.student,
                message="I need help planning this week.",
                current_dt=datetime(2026, 3, 8, 9, 0, 0),
                academic_start=date(2026, 3, 2),
            )

        self.assertEqual(out["reply"], "Live Gemini counselling reply.")


if __name__ == "__main__":
    unittest.main()
