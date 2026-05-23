import unittest
from datetime import date, time
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.routers.attendance import get_student_weekly_timetable


class StudentTimetableRmsSyncTests(unittest.TestCase):
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
        self.week_start = date(2026, 3, 2)  # Monday
        self.class_date = date(2026, 3, 3)  # Tuesday
        student = models.Student(
            id=1,
            name="Student One",
            email="student.one@example.com",
            registration_number="22BCS101",
            section="P132",
            department="CSE",
            semester=4,
        )
        faculty = models.Faculty(
            id=11,
            name="Faculty One",
            email="faculty.one@example.com",
            department="CSE",
            section="P132",
        )
        course = models.Course(
            id=101,
            code="CSE332",
            title="Industry Ethics and Legal Issues",
            faculty_id=11,
        )
        enrollment = models.Enrollment(
            id=201,
            student_id=1,
            course_id=101,
        )
        schedule = models.ClassSchedule(
            id=301,
            course_id=101,
            faculty_id=11,
            weekday=self.class_date.weekday(),
            start_time=time(9, 0),
            end_time=time(10, 0),
            classroom_label="34-201",
            is_active=True,
        )
        admin_override_record = models.AttendanceRecord(
            id=401,
            student_id=1,
            course_id=101,
            marked_by_faculty_id=11,
            attendance_date=self.class_date,
            status=models.AttendanceStatus.PRESENT,
            source="rms-admin-attendance-override",
        )
        self.db.add_all(
            [
                student,
                faculty,
                course,
                enrollment,
                schedule,
                admin_override_record,
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

    def test_timetable_preserves_existing_enrollments_and_uses_record_fallback(self):
        with patch("app.routers.attendance._ensure_default_timetable_for_student") as mocked_loader, patch(
            "app.routers.attendance._academic_start_date",
            return_value=self.week_start,
        ):
            payload = get_student_weekly_timetable(
                week_start=self.week_start,
                db=self.db,
                current_user=self._student_user(),
            )

        mocked_loader.assert_not_called()
        enrollment = (
            self.db.query(models.Enrollment)
            .filter(models.Enrollment.student_id == 1, models.Enrollment.course_id == 101)
            .first()
        )
        self.assertIsNotNone(enrollment)

        target_row = next(
            (
                row for row in payload.classes
                if row.course_code == "CSE332" and row.class_date == self.class_date
            ),
            None,
        )
        self.assertIsNotNone(target_row)
        self.assertEqual(target_row.attendance_status, "present")


if __name__ == "__main__":
    unittest.main()
