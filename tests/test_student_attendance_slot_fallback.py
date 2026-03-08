import unittest
from datetime import date, time
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.routers.attendance import (
    get_student_attendance_aggregate,
    get_student_attendance_history,
)


class StudentAttendanceSlotFallbackAlignmentTests(unittest.TestCase):
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
        self.class_date = date(2026, 3, 3)  # Tuesday
        self.db.add_all(
            [
                models.Student(
                    id=1,
                    name="Student One",
                    email="student.one@example.com",
                    registration_number="22BCS101",
                    section="P132",
                    department="CSE",
                    semester=4,
                ),
                models.Faculty(
                    id=11,
                    name="Faculty One",
                    email="faculty.one@example.com",
                    department="CSE",
                    section="P132",
                ),
                models.Course(
                    id=101,
                    code="CSE357",
                    title="Combinatorial Studies",
                    faculty_id=11,
                ),
                models.Enrollment(
                    id=201,
                    student_id=1,
                    course_id=101,
                ),
                models.ClassSchedule(
                    id=301,
                    course_id=101,
                    faculty_id=11,
                    weekday=self.class_date.weekday(),
                    start_time=time(9, 0),
                    end_time=time(10, 0),
                    classroom_label="37-101",
                    is_active=True,
                ),
                models.ClassSchedule(
                    id=302,
                    course_id=101,
                    faculty_id=11,
                    weekday=self.class_date.weekday(),
                    start_time=time(10, 0),
                    end_time=time(11, 0),
                    classroom_label="37-101",
                    is_active=True,
                ),
                models.AttendanceSubmission(
                    id=401,
                    schedule_id=301,
                    course_id=101,
                    faculty_id=11,
                    student_id=1,
                    class_date=self.class_date,
                    selfie_photo_data_url=None,
                    ai_match=True,
                    ai_confidence=1.0,
                    ai_model="opencv-test",
                    ai_reason="verified",
                    status=models.AttendanceSubmissionStatus.VERIFIED,
                ),
                models.AttendanceRecord(
                    id=501,
                    student_id=1,
                    course_id=101,
                    marked_by_faculty_id=11,
                    attendance_date=self.class_date,
                    status=models.AttendanceStatus.PRESENT,
                    source="rms-admin-attendance-override",
                ),
            ]
        )
        self.db.commit()

    @staticmethod
    def _student_user() -> models.AuthUser:
        return models.AuthUser(
            id=9001,
            email="student.one@example.com",
            password_hash="x",
            role=models.UserRole.STUDENT,
            student_id=1,
            faculty_id=None,
            is_active=True,
        )

    def test_aggregate_counts_record_fallback_for_missing_same_day_slots(self):
        with patch("app.routers.attendance._academic_start_date", return_value=self.class_date):
            payload = get_student_attendance_aggregate(
                db=self.db,
                current_user=self._student_user(),
            )

        self.assertEqual(payload.attended_total, 2)
        self.assertEqual(payload.delivered_total, 2)
        self.assertEqual(payload.aggregate_percent, 100.0)
        self.assertEqual(len(payload.courses), 1)
        self.assertEqual(payload.courses[0].course_code, "CSE357")
        self.assertEqual(payload.courses[0].attended_classes, 2)
        self.assertEqual(payload.courses[0].delivered_classes, 2)

    def test_history_expands_record_fallback_to_missing_schedule_slot(self):
        with patch("app.routers.attendance._academic_start_date", return_value=self.class_date):
            payload = get_student_attendance_history(
                limit=20,
                db=self.db,
                current_user=self._student_user(),
            )

        rows = [row for row in payload.records if row.course_code == "CSE357"]
        self.assertEqual(len(rows), 2)
        self.assertEqual({int(row.schedule_id or 0) for row in rows}, {301, 302})
        self.assertEqual(
            sum(1 for row in rows if row.status == models.AttendanceStatus.PRESENT),
            2,
        )


if __name__ == "__main__":
    unittest.main()
