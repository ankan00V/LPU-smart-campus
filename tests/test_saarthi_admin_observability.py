import unittest
from datetime import date, datetime
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.routers.admin import admin_saarthi_export, admin_saarthi_overview
from app.saarthi_service import SAARTHI_ATTENDANCE_MINUTES, SAARTHI_COURSE_CODE


class SaarthiAdminObservabilityTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        SessionLocal = sessionmaker(bind=self.engine)
        self.db = SessionLocal()
        self._seed()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    @staticmethod
    def _admin_user() -> models.AuthUser:
        return models.AuthUser(
            id=1,
            email="admin@example.com",
            password_hash="x",
            role=models.UserRole.ADMIN,
            student_id=None,
            faculty_id=None,
            is_active=True,
        )

    def _seed(self):
        self.faculty = models.Faculty(
            id=11,
            name="Saarthi (AI Mentor)",
            email="saarthi.ai.mentor@example.com",
            faculty_identifier="SAARTHI-AI-MENTOR",
            section="ALL",
            department="Student Wellness",
        )
        self.course = models.Course(
            id=21,
            code=SAARTHI_COURSE_CODE,
            title="Councelling and Happiness",
            faculty_id=11,
        )
        self.students = [
            models.Student(
                id=101,
                name="Aarav",
                email="aarav@example.com",
                registration_number="22BCS101",
                section="P132",
                department="CSE",
                semester=6,
            ),
            models.Student(
                id=102,
                name="Bhavya",
                email="bhavya@example.com",
                registration_number="22ECE102",
                section="P242",
                department="ECE",
                semester=6,
            ),
            models.Student(
                id=103,
                name="Charu",
                email="charu@example.com",
                registration_number="22BCS103",
                section="P132",
                department="CSE",
                semester=6,
            ),
        ]
        self.db.add(self.faculty)
        self.db.add(self.course)
        self.db.add_all(self.students)
        self.db.flush()

        for idx, student in enumerate(self.students, start=1):
            self.db.add(
                models.Enrollment(
                    id=300 + idx,
                    student_id=int(student.id),
                    course_id=int(self.course.id),
                )
            )

        completed_session = models.SaarthiSession(
            id=401,
            student_id=101,
            course_id=21,
            faculty_id=11,
            week_start_date=date(2026, 3, 2),
            mandatory_date=date(2026, 3, 8),
            attendance_credit_minutes=SAARTHI_ATTENDANCE_MINUTES,
            attendance_marked_at=datetime(2026, 3, 8, 10, 30, 0),
            attendance_record_id=501,
            created_at=datetime(2026, 3, 8, 10, 0, 0),
            updated_at=datetime(2026, 3, 8, 10, 30, 0),
            last_message_at=datetime(2026, 3, 8, 10, 30, 0),
        )
        missed_session = models.SaarthiSession(
            id=402,
            student_id=102,
            course_id=21,
            faculty_id=11,
            week_start_date=date(2026, 3, 2),
            mandatory_date=date(2026, 3, 8),
            attendance_credit_minutes=0,
            attendance_marked_at=None,
            attendance_record_id=None,
            created_at=datetime(2026, 3, 6, 16, 0, 0),
            updated_at=datetime(2026, 3, 6, 16, 5, 0),
            last_message_at=datetime(2026, 3, 6, 16, 5, 0),
        )
        self.db.add_all([completed_session, missed_session])
        self.db.flush()

        self.db.add_all(
            [
                models.SaarthiMessage(
                    session_id=401,
                    sender_role="student",
                    message="I feel stressed before exams.",
                    created_at=datetime(2026, 3, 8, 10, 0, 0),
                ),
                models.SaarthiMessage(
                    session_id=401,
                    sender_role="assistant",
                    message="Let us break the pressure into one realistic task.",
                    created_at=datetime(2026, 3, 8, 10, 1, 0),
                ),
                models.SaarthiMessage(
                    session_id=402,
                    sender_role="student",
                    message="I want to talk before Sunday.",
                    created_at=datetime(2026, 3, 6, 16, 0, 0),
                ),
            ]
        )
        self.db.add(
            models.AttendanceRecord(
                id=501,
                student_id=101,
                course_id=21,
                marked_by_faculty_id=11,
                attendance_date=date(2026, 3, 8),
                status=models.AttendanceStatus.PRESENT,
                source="saarthi-weekly-credit",
                created_at=datetime(2026, 3, 8, 10, 30, 0),
                updated_at=datetime(2026, 3, 8, 10, 30, 0),
            )
        )
        self.db.add(
            models.AttendanceEvent(
                id=601,
                event_key="saarthi:101:2026-03-08:present",
                student_id=101,
                course_id=21,
                attendance_date=date(2026, 3, 8),
                status=models.AttendanceStatus.PRESENT,
                actor_user_id=None,
                actor_faculty_id=11,
                actor_role=models.UserRole.FACULTY.value,
                source="saarthi-weekly-credit",
                note="Mandatory Saarthi counselling completed. Weekly 1-hour credit applied.",
                created_at=datetime(2026, 3, 8, 10, 30, 0),
            )
        )
        self.db.commit()

    def test_admin_saarthi_overview_reports_completion_and_missed_alerts(self):
        with mock.patch("app.routers.admin.enqueue_saarthi_missed_notifications", return_value=1) as mocked_enqueue:
            out = admin_saarthi_overview(
                reference_date=date(2026, 3, 9),
                db=self.db,
                _=self._admin_user(),
            )

        self.assertEqual(out.week_start_date, date(2026, 3, 2))
        self.assertEqual(out.mandatory_date, date(2026, 3, 8))
        self.assertEqual(out.total_students, 3)
        self.assertEqual(out.completed_students, 1)
        self.assertEqual(out.missed_students, 2)
        self.assertEqual(out.pending_students, 0)
        self.assertEqual(out.due_today_students, 0)
        self.assertEqual(out.engaged_students, 2)
        self.assertEqual(out.total_messages, 3)
        self.assertEqual(len(out.missed_alerts), 2)
        self.assertEqual(out.departments[0].department, "CSE")
        self.assertEqual(out.departments[0].completed_students, 1)
        self.assertEqual(out.departments[1].department, "ECE")
        self.assertEqual(out.departments[1].missed_students, 1)
        self.assertEqual(mocked_enqueue.call_count, 2)

    def test_admin_saarthi_overview_marks_students_due_today_on_sunday(self):
        with mock.patch("app.routers.admin.enqueue_saarthi_missed_notifications", return_value=1) as mocked_enqueue:
            out = admin_saarthi_overview(
                reference_date=date(2026, 3, 8),
                db=self.db,
                _=self._admin_user(),
            )

        self.assertEqual(out.completed_students, 1)
        self.assertEqual(out.due_today_students, 2)
        self.assertEqual(out.missed_students, 0)
        mocked_enqueue.assert_not_called()

    def test_admin_saarthi_export_includes_transcript_and_attendance_audit(self):
        out = admin_saarthi_export(
            reference_date=date(2026, 3, 9),
            include_messages=True,
            db=self.db,
            _=self._admin_user(),
        )

        self.assertTrue(out.file_name.startswith("saarthi-audit-2026-03-02"))
        self.assertEqual(out.record_count, 3)
        self.assertTrue(out.checksum_sha256)
        completed_record = next((row for row in out.records if row.student.student_id == 101), None)
        self.assertIsNotNone(completed_record)
        self.assertEqual(completed_record.attendance_status, models.AttendanceStatus.PRESENT)
        self.assertEqual(completed_record.attendance_source, "saarthi-weekly-credit")
        self.assertEqual(completed_record.attendance_event_source, "saarthi-weekly-credit")
        self.assertEqual(len(completed_record.transcript), 2)
        missed_record = next((row for row in out.records if row.student.student_id == 103), None)
        self.assertIsNotNone(missed_record)
        self.assertEqual(missed_record.student.week_status, "missed")
        self.assertEqual(len(missed_record.transcript), 0)


if __name__ == "__main__":
    unittest.main()
