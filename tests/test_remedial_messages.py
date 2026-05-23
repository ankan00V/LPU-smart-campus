from datetime import date, datetime, time, timedelta
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.routers.remedial import get_student_remedial_messages


class RemedialMessagesVisibilityTests(unittest.TestCase):
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
        self.db.add_all(
            [
                models.Faculty(
                    id=1,
                    name="Faculty One",
                    email="faculty.one@example.com",
                    department="CSE",
                    section="P132",
                ),
                models.Student(
                    id=10,
                    name="Student One",
                    email="student.one@example.com",
                    department="CSE",
                    semester=6,
                    section="P132",
                ),
                models.Course(
                    id=20,
                    code="CSE310",
                    title="JAVA PROGRAMMING",
                    faculty_id=1,
                ),
                models.MakeUpClass(
                    id=100,
                    course_id=20,
                    faculty_id=1,
                    class_date=date.today() - timedelta(days=1),
                    start_time=time(15, 0),
                    end_time=time(16, 0),
                    topic="Completed Remedial",
                    sections_json='["P132"]',
                    class_mode="offline",
                    room_number="27-401",
                    online_link=None,
                    remedial_code="OLD100AA",
                    code_generated_at=now_dt - timedelta(days=1, minutes=5),
                    code_expires_at=now_dt - timedelta(days=1, minutes=1),
                    attendance_open_minutes=15,
                    scheduled_at=now_dt - timedelta(days=1, minutes=10),
                    is_active=True,
                ),
                models.MakeUpClass(
                    id=101,
                    course_id=20,
                    faculty_id=1,
                    class_date=date.today() + timedelta(days=1),
                    start_time=time(15, 0),
                    end_time=time(16, 0),
                    topic="Upcoming Remedial",
                    sections_json='["P132"]',
                    class_mode="offline",
                    room_number="27-401",
                    online_link=None,
                    remedial_code="NEW101BB",
                    code_generated_at=now_dt,
                    code_expires_at=now_dt + timedelta(days=1),
                    attendance_open_minutes=15,
                    scheduled_at=now_dt,
                    is_active=True,
                ),
                models.RemedialMessage(
                    id=1000,
                    makeup_class_id=100,
                    faculty_id=1,
                    student_id=10,
                    section="P132",
                    remedial_code="OLD100AA",
                    message="Completed class code",
                    created_at=now_dt,
                ),
                models.RemedialMessage(
                    id=1001,
                    makeup_class_id=101,
                    faculty_id=1,
                    student_id=10,
                    section="P132",
                    remedial_code="NEW101BB",
                    message="Upcoming class code",
                    created_at=now_dt - timedelta(minutes=1),
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
            student_id=10,
            faculty_id=None,
            is_active=True,
        )

    def test_completed_classes_are_hidden_from_student_remedial_messages(self):
        rows = get_student_remedial_messages(limit=50, db=self.db, current_user=self._student_user())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].class_id, 101)
        self.assertEqual(rows[0].remedial_code, "NEW101BB")


if __name__ == "__main__":
    unittest.main()
