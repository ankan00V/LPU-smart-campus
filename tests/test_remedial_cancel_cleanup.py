from datetime import date, datetime, timedelta, time
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.routers.makeup import cancel_makeup_class, get_student_remedial_messages


class RemedialCancelCleanupTests(unittest.TestCase):
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
        now_dt = datetime.utcnow().replace(second=0, microsecond=0)

        self.db.add_all(
            [
                models.Faculty(
                    id=21,
                    name="Faculty R",
                    email="faculty.r@example.com",
                    department="CSE",
                    section="P132",
                ),
                models.Student(
                    id=31,
                    name="Student R",
                    email="student.r@example.com",
                    department="CSE",
                    semester=6,
                    section="P132",
                ),
                models.Course(
                    id=41,
                    code="CSE241",
                    title="Networks",
                    faculty_id=21,
                ),
                models.MakeUpClass(
                    id=51,
                    course_id=41,
                    faculty_id=21,
                    class_date=date.today() + timedelta(days=1),
                    start_time=time(12, 0),
                    end_time=time(13, 0),
                    topic="Routing remedial",
                    sections_json='["P132"]',
                    class_mode="offline",
                    room_number="25-801",
                    online_link=None,
                    remedial_code="NET241AA",
                    code_generated_at=now_dt,
                    code_expires_at=now_dt + timedelta(days=1),
                    attendance_open_minutes=15,
                    scheduled_at=now_dt,
                    is_active=True,
                ),
                models.MakeUpClass(
                    id=52,
                    course_id=41,
                    faculty_id=21,
                    class_date=date.today() + timedelta(days=1),
                    start_time=time(14, 0),
                    end_time=time(15, 0),
                    topic="Late cancel blocked",
                    sections_json='["P132"]',
                    class_mode="offline",
                    room_number="25-802",
                    online_link=None,
                    remedial_code="NET241BB",
                    code_generated_at=now_dt - timedelta(minutes=31),
                    code_expires_at=now_dt + timedelta(days=1),
                    attendance_open_minutes=15,
                    scheduled_at=now_dt - timedelta(minutes=31),
                    is_active=True,
                ),
                models.RemedialMessage(
                    id=61,
                    makeup_class_id=51,
                    faculty_id=21,
                    student_id=31,
                    section="P132",
                    remedial_code="NET241AA",
                    message="Use code NET241AA",
                    created_at=now_dt,
                ),
                models.RemedialMessage(
                    id=62,
                    makeup_class_id=52,
                    faculty_id=21,
                    student_id=31,
                    section="P132",
                    remedial_code="NET241BB",
                    message="Use code NET241BB",
                    created_at=now_dt,
                ),
            ]
        )
        self.db.commit()

    def _faculty_user(self) -> models.AuthUser:
        return models.AuthUser(
            id=901,
            email="faculty.r@example.com",
            password_hash="x",
            role=models.UserRole.FACULTY,
            faculty_id=21,
            student_id=None,
            is_active=True,
        )

    def _student_user(self) -> models.AuthUser:
        return models.AuthUser(
            id=902,
            email="student.r@example.com",
            password_hash="x",
            role=models.UserRole.STUDENT,
            faculty_id=None,
            student_id=31,
            is_active=True,
        )

    def test_cancel_removes_student_messages_and_hides_from_feed(self):
        before_rows = get_student_remedial_messages(limit=50, db=self.db, current_user=self._student_user())
        self.assertEqual(len(before_rows), 2)

        with patch("app.routers.makeup._sync_makeup_class_to_mongo", return_value=None), patch(
            "app.routers.makeup.mirror_event",
            return_value=False,
        ), patch("app.routers.makeup.get_mongo_db", return_value=None):
            cancel_makeup_class(class_id=51, db=self.db, current_user=self._faculty_user())

        message_rows = (
            self.db.query(models.RemedialMessage)
            .filter(models.RemedialMessage.makeup_class_id == 51)
            .all()
        )
        self.assertEqual(message_rows, [])

        after_rows = get_student_remedial_messages(limit=50, db=self.db, current_user=self._student_user())
        self.assertEqual(len(after_rows), 1)
        self.assertEqual(after_rows[0].class_id, 52)

    def test_cancel_reject_window_blocks_after_30_minutes(self):
        with patch("app.routers.makeup._sync_makeup_class_to_mongo", return_value=None), patch(
            "app.routers.makeup.mirror_event",
            return_value=False,
        ), patch("app.routers.makeup.get_mongo_db", return_value=None):
            with self.assertRaises(HTTPException) as exc:
                cancel_makeup_class(class_id=52, db=self.db, current_user=self._faculty_user())

        self.assertEqual(exc.exception.status_code, 400)
        self.assertIn("within 30 minutes", str(exc.exception.detail))

        class_row = self.db.get(models.MakeUpClass, 52)
        self.assertIsNotNone(class_row)
        self.assertTrue(bool(class_row.is_active))


if __name__ == "__main__":
    unittest.main()
