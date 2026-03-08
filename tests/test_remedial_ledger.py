from datetime import datetime, timedelta
import json
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.routers.attendance import (
    get_student_attendance_aggregate,
    get_student_attendance_history,
)
from app.routers.remedial import get_student_remedial_attendance_history


class RemedialLedgerTests(unittest.TestCase):
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
        present_start_dt = now_dt - timedelta(minutes=5)
        present_end_dt = now_dt + timedelta(minutes=55)
        absent_start_dt = now_dt - timedelta(hours=2)
        absent_end_dt = now_dt - timedelta(hours=1, minutes=20)
        pending_start_dt = now_dt + timedelta(minutes=10)
        pending_end_dt = now_dt + timedelta(minutes=70)

        self.student_id = 1
        self.course_id = 205

        self.db.add_all(
            [
                models.Student(
                    id=self.student_id,
                    name="Ledger Student",
                    email="ledger.student@example.com",
                    department="CSE",
                    semester=6,
                    section="P132",
                ),
                models.Faculty(
                    id=11,
                    name="Ledger Faculty",
                    email="ledger.faculty@example.com",
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
                    id=501,
                    course_id=self.course_id,
                    faculty_id=11,
                    class_date=present_start_dt.date(),
                    start_time=present_start_dt.time(),
                    end_time=present_end_dt.time(),
                    topic="Remedial DSA",
                    sections_json=json.dumps(["P132"]),
                    class_mode="offline",
                    room_number="25-801",
                    online_link=None,
                    remedial_code="LEDGER01",
                    code_generated_at=now_dt - timedelta(minutes=10),
                    code_expires_at=now_dt + timedelta(minutes=20),
                    attendance_open_minutes=15,
                    scheduled_at=now_dt - timedelta(minutes=10),
                    is_active=True,
                ),
                models.MakeUpClass(
                    id=502,
                    course_id=self.course_id,
                    faculty_id=11,
                    class_date=absent_start_dt.date(),
                    start_time=absent_start_dt.time(),
                    end_time=absent_end_dt.time(),
                    topic="Remedial DSA - Absent",
                    sections_json=json.dumps(["P132"]),
                    class_mode="offline",
                    room_number="25-801",
                    online_link=None,
                    remedial_code="LEDGER02",
                    code_generated_at=now_dt - timedelta(hours=2, minutes=15),
                    code_expires_at=now_dt - timedelta(hours=1, minutes=45),
                    attendance_open_minutes=15,
                    scheduled_at=now_dt - timedelta(hours=2, minutes=15),
                    is_active=True,
                ),
                models.MakeUpClass(
                    id=503,
                    course_id=self.course_id,
                    faculty_id=11,
                    class_date=pending_start_dt.date(),
                    start_time=pending_start_dt.time(),
                    end_time=pending_end_dt.time(),
                    topic="Remedial DSA - Pending",
                    sections_json=json.dumps(["P132"]),
                    class_mode="offline",
                    room_number="25-801",
                    online_link=None,
                    remedial_code="LEDGER03",
                    code_generated_at=now_dt - timedelta(minutes=5),
                    code_expires_at=now_dt + timedelta(minutes=10),
                    attendance_open_minutes=15,
                    scheduled_at=now_dt - timedelta(minutes=5),
                    is_active=True,
                ),
                models.RemedialMessage(
                    makeup_class_id=501,
                    faculty_id=11,
                    student_id=self.student_id,
                    section="P132",
                    remedial_code="LEDGER01",
                    message="Use code LEDGER01",
                    created_at=now_dt - timedelta(minutes=3),
                ),
                models.RemedialMessage(
                    makeup_class_id=502,
                    faculty_id=11,
                    student_id=self.student_id,
                    section="P132",
                    remedial_code="LEDGER02",
                    message="Use code LEDGER02",
                    created_at=now_dt - timedelta(hours=2, minutes=1),
                ),
                models.RemedialMessage(
                    makeup_class_id=503,
                    faculty_id=11,
                    student_id=self.student_id,
                    section="P132",
                    remedial_code="LEDGER03",
                    message="Use code LEDGER03",
                    created_at=now_dt - timedelta(minutes=1),
                ),
                models.RemedialAttendance(
                    makeup_class_id=501,
                    student_id=self.student_id,
                    source="remedial-face-opencv-verified",
                    marked_at=now_dt - timedelta(minutes=2),
                ),
            ]
        )
        self.db.commit()

    def _student_user(self) -> models.AuthUser:
        return models.AuthUser(
            id=9001,
            email="ledger.student@example.com",
            password_hash="x",
            role=models.UserRole.STUDENT,
            student_id=self.student_id,
            faculty_id=None,
            is_active=True,
        )

    def test_history_excludes_marked_remedial_attendance(self):
        payload = get_student_attendance_history(
            limit=20,
            db=self.db,
            current_user=self._student_user(),
        )
        self.assertFalse(payload.records)
        remedial_rows = [row for row in payload.records if "remedial" in str(row.source or "").lower()]
        self.assertFalse(remedial_rows)

    def test_aggregate_excludes_marked_remedial_attendance(self):
        payload = get_student_attendance_aggregate(
            db=self.db,
            current_user=self._student_user(),
        )
        self.assertEqual(payload.delivered_total, 0)
        self.assertEqual(payload.attended_total, 0)
        self.assertEqual(payload.courses, [])

    def test_student_remedial_attendance_ledger_lists_present_and_absent_entries(self):
        payload = get_student_remedial_attendance_history(
            limit=20,
            db=self.db,
            current_user=self._student_user(),
        )
        self.assertEqual(len(payload), 2)
        by_class_id = {row.class_id: row for row in payload}
        self.assertIn(501, by_class_id)
        self.assertIn(502, by_class_id)
        self.assertNotIn(503, by_class_id)

        present_row = by_class_id[501]
        self.assertEqual(present_row.course_id, self.course_id)
        self.assertEqual(present_row.course_code, "CSE205")
        self.assertEqual(present_row.course_title, "Data Structure and Algorithm")
        self.assertEqual(present_row.status, "present")
        self.assertIsNotNone(present_row.marked_at)
        self.assertIn("remedial", str(present_row.source or "").lower())

        absent_row = by_class_id[502]
        self.assertEqual(absent_row.status, "absent")
        self.assertIsNone(absent_row.marked_at)
        self.assertIsNone(absent_row.source)


if __name__ == "__main__":
    unittest.main()
