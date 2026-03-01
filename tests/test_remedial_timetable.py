from datetime import datetime, timedelta
import json
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.routers.attendance import get_student_weekly_timetable


class RemedialTimetableTests(unittest.TestCase):
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
        now_dt = datetime.now().replace(second=0, microsecond=0)
        absent_start = now_dt - timedelta(minutes=45)
        absent_end = now_dt - timedelta(minutes=25)
        present_start = now_dt - timedelta(minutes=40)
        present_end = now_dt - timedelta(minutes=20)

        self.week_start = absent_start.date() - timedelta(days=absent_start.date().weekday())

        self.student_id = 1
        self.course_id = 205
        self.absent_class_id = 501
        self.present_class_id = 502

        self.db.add_all(
            [
                models.Student(
                    id=self.student_id,
                    name="Student One",
                    email="student.one@example.com",
                    department="CSE",
                    semester=6,
                    section="P132",
                ),
                models.Faculty(
                    id=11,
                    name="Faculty One",
                    email="faculty.one@example.com",
                    department="CSE",
                    section="P132",
                ),
                models.Course(
                    id=self.course_id,
                    code="CSE205",
                    title="Data Structure and Algorithm",
                    faculty_id=11,
                ),
                models.MakeUpClass(
                    id=self.absent_class_id,
                    course_id=self.course_id,
                    faculty_id=11,
                    class_date=absent_start.date(),
                    start_time=absent_start.time(),
                    end_time=absent_end.time(),
                    topic="Remedial DSA",
                    sections_json=json.dumps(["P132"]),
                    class_mode="offline",
                    room_number="25-801",
                    online_link=None,
                    remedial_code="ABSENT01",
                    code_generated_at=now_dt,
                    code_expires_at=now_dt + timedelta(hours=1),
                    attendance_open_minutes=15,
                    scheduled_at=now_dt,
                    is_active=True,
                ),
                models.MakeUpClass(
                    id=self.present_class_id,
                    course_id=self.course_id,
                    faculty_id=11,
                    class_date=present_start.date(),
                    start_time=present_start.time(),
                    end_time=present_end.time(),
                    topic="Remedial DSA 2",
                    sections_json=json.dumps(["P132"]),
                    class_mode="offline",
                    room_number="25-802",
                    online_link=None,
                    remedial_code="PRESENT1",
                    code_generated_at=now_dt,
                    code_expires_at=now_dt + timedelta(hours=1),
                    attendance_open_minutes=15,
                    scheduled_at=now_dt,
                    is_active=True,
                ),
                models.RemedialMessage(
                    makeup_class_id=self.absent_class_id,
                    faculty_id=11,
                    student_id=self.student_id,
                    section="P132",
                    remedial_code="ABSENT01",
                    message="Use code ABSENT01",
                    created_at=now_dt,
                ),
                models.RemedialMessage(
                    makeup_class_id=self.present_class_id,
                    faculty_id=11,
                    student_id=self.student_id,
                    section="P132",
                    remedial_code="PRESENT1",
                    message="Use code PRESENT1",
                    created_at=now_dt,
                ),
                models.RemedialAttendance(
                    makeup_class_id=self.present_class_id,
                    student_id=self.student_id,
                    source="remedial-code",
                    marked_at=now_dt,
                ),
            ]
        )
        self.db.commit()

    def _student_user(self) -> models.AuthUser:
        return models.AuthUser(
            id=9001,
            email="student.one@example.com",
            password_hash="x",
            role=models.UserRole.STUDENT,
            student_id=self.student_id,
            faculty_id=None,
            is_active=True,
        )

    def test_student_timetable_includes_message_targeted_remedials_with_status(self):
        with patch("app.routers.attendance._ensure_default_timetable_for_student", return_value={
            "faculty": 0,
            "courses": 0,
            "classrooms": 0,
            "schedules": 0,
            "enrollments": 0,
            "total_classes": 0,
        }), patch("app.routers.attendance._academic_start_date", return_value=self.week_start):
            payload = get_student_weekly_timetable(
                week_start=self.week_start,
                db=self.db,
                current_user=self._student_user(),
            )

        remedials = [row for row in payload.classes if row.class_kind == "remedial"]
        self.assertGreaterEqual(len(remedials), 2)

        by_id = {int(row.remedial_class_id or 0): row for row in remedials}
        self.assertIn(self.absent_class_id, by_id)
        self.assertIn(self.present_class_id, by_id)

        absent_row = by_id[self.absent_class_id]
        present_row = by_id[self.present_class_id]

        self.assertEqual(absent_row.attendance_status, "absent")
        self.assertEqual(present_row.attendance_status, "present")
        self.assertTrue(absent_row.remedial_code_required)
        self.assertTrue(present_row.remedial_code_required)


if __name__ == "__main__":
    unittest.main()
