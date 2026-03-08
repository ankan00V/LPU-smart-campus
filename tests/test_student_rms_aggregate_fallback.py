import unittest
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.routers.attendance import get_student_attendance_aggregate


class StudentAggregateRmsFallbackTests(unittest.TestCase):
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
        self.class_date = date(2026, 3, 3)
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
                    code="CSE332",
                    title="Industry Ethics and Legal Issues",
                    faculty_id=11,
                ),
                models.AttendanceRecord(
                    id=401,
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

    def test_aggregate_uses_attendance_records_even_without_enrollment(self):
        payload = get_student_attendance_aggregate(
            db=self.db,
            current_user=self._student_user(),
        )
        self.assertEqual(payload.attended_total, 1)
        self.assertEqual(payload.delivered_total, 1)
        self.assertEqual(len(payload.courses), 1)
        self.assertEqual(payload.courses[0].course_code, "CSE332")
        self.assertEqual(payload.courses[0].attended_classes, 1)
        self.assertEqual(payload.courses[0].delivered_classes, 1)
        self.assertEqual(payload.aggregate_percent, 100.0)


if __name__ == "__main__":
    unittest.main()
