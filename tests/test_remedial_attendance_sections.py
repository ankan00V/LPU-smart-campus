from datetime import date, datetime, time, timedelta
import json
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.routers.makeup import get_makeup_class_attendance


class RemedialAttendanceSectionTests(unittest.TestCase):
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
        self.makeup_class_id = 7001

        self.db.add_all(
            [
                models.Faculty(
                    id=201,
                    name="Faculty A",
                    email="faculty.a@example.com",
                    department="CSE",
                    section="P132 P133",
                ),
                models.Course(
                    id=301,
                    code="CSE310",
                    title="JAVA PROGRAMMING",
                    faculty_id=201,
                ),
                models.Student(
                    id=11,
                    name="Ankan Ghosh",
                    email="ankan@example.com",
                    department="CSE",
                    semester=6,
                    section="P132",
                ),
                models.Student(
                    id=12,
                    name="Riya Sen",
                    email="riya@example.com",
                    department="CSE",
                    semester=6,
                    section="P132",
                ),
                models.Student(
                    id=13,
                    name="Karan Das",
                    email="karan@example.com",
                    department="CSE",
                    semester=6,
                    section="P133",
                ),
                models.Student(
                    id=14,
                    name="Other Section Student",
                    email="other@example.com",
                    department="CSE",
                    semester=6,
                    section="P140",
                ),
                models.MakeUpClass(
                    id=self.makeup_class_id,
                    course_id=301,
                    faculty_id=201,
                    class_date=date.today(),
                    start_time=time(16, 0),
                    end_time=time(17, 0),
                    topic="Collections",
                    sections_json=json.dumps(["P132", "P133"]),
                    class_mode="offline",
                    room_number="27-401",
                    online_link=None,
                    remedial_code="SECT310A",
                    code_generated_at=now_dt,
                    code_expires_at=now_dt + timedelta(hours=1),
                    attendance_open_minutes=15,
                    scheduled_at=now_dt,
                    is_active=True,
                ),
                models.RemedialAttendance(
                    makeup_class_id=self.makeup_class_id,
                    student_id=11,
                    source="remedial-code",
                    marked_at=now_dt + timedelta(minutes=2),
                ),
            ]
        )
        self.db.commit()

    def _faculty_user(self) -> models.AuthUser:
        return models.AuthUser(
            id=9011,
            email="faculty.a@example.com",
            password_hash="x",
            role=models.UserRole.FACULTY,
            faculty_id=201,
            student_id=None,
            is_active=True,
        )

    def test_class_attendance_returns_section_wise_marked_and_not_marked(self):
        payload = get_makeup_class_attendance(
            class_id=self.makeup_class_id,
            db=self.db,
            current_user=self._faculty_user(),
        )

        self.assertEqual(payload["sections"], ["P132", "P133"])
        self.assertEqual(payload["student_count"], 3)
        self.assertEqual(payload["attendance_count"], 1)
        self.assertEqual(payload["not_marked_count"], 2)

        marked_rows = payload["students"]
        self.assertEqual(len(marked_rows), 1)
        self.assertEqual(marked_rows[0]["student_id"], 11)
        self.assertTrue(marked_rows[0]["marked"])

        all_rows = payload["all_students"]
        self.assertEqual(len(all_rows), 3)
        self.assertFalse(any(row["student_id"] == 14 for row in all_rows))
        self.assertEqual(
            {row["student_id"]: row["status"] for row in all_rows},
            {
                11: "marked",
                12: "not_marked",
                13: "not_marked",
            },
        )

        summaries = {item["section"]: item for item in payload["section_summaries"]}
        self.assertEqual(set(summaries.keys()), {"P132", "P133"})
        self.assertEqual(summaries["P132"]["total_students"], 2)
        self.assertEqual(summaries["P132"]["marked_students"], 1)
        self.assertEqual(summaries["P132"]["not_marked_students"], 1)
        self.assertEqual(summaries["P133"]["total_students"], 1)
        self.assertEqual(summaries["P133"]["marked_students"], 0)
        self.assertEqual(summaries["P133"]["not_marked_students"], 1)


if __name__ == "__main__":
    unittest.main()
