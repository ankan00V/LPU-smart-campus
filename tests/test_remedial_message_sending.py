from datetime import date, datetime, time
import json
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.routers.remedial import send_remedial_code_to_sections


class RemedialSendMessageTests(unittest.TestCase):
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
        faculty = models.Faculty(
            id=1,
            name="Faculty One",
            email="faculty1@example.com",
            department="CSE",
            section="P132",
        )
        course = models.Course(
            id=1,
            code="CSE205",
            title="Data Structure and Algorithm",
            faculty_id=1,
        )
        class_row = models.MakeUpClass(
            id=1,
            course_id=1,
            faculty_id=1,
            class_date=date(2026, 3, 1),
            start_time=time(12, 5),
            end_time=time(13, 5),
            topic="DSA concepts",
            sections_json=json.dumps(["P132"]),
            class_mode="offline",
            room_number="25-801",
            online_link=None,
            remedial_code="X35YKMBI",
            code_generated_at=datetime.utcnow(),
            code_expires_at=datetime.utcnow(),
            attendance_open_minutes=15,
            scheduled_at=datetime.utcnow(),
            is_active=True,
        )
        self.db.add_all(
            [
                faculty,
                course,
                class_row,
                models.Student(
                    id=10,
                    name="Student A",
                    email="stud-a@example.com",
                    department="CSE",
                    semester=5,
                    section="P132",
                ),
                models.Student(
                    id=11,
                    name="Student B",
                    email="stud-b@example.com",
                    department="CSE",
                    semester=5,
                    section="P132",
                ),
                models.Student(
                    id=12,
                    name="Student C",
                    email="stud-c@example.com",
                    department="CSE",
                    semester=5,
                    section="P133",
                ),
            ]
        )
        self.db.flush()
        self.db.add(
            models.AuthUser(
                id=101,
                email="faculty1@example.com",
                password_hash="x",
                role=models.UserRole.FACULTY,
                faculty_id=1,
                student_id=None,
                is_active=True,
            )
        )
        self.db.commit()

    def test_send_message_succeeds_when_mirror_fails(self):
        current_user = models.AuthUser(
            id=101,
            email="faculty1@example.com",
            password_hash="x",
            role=models.UserRole.FACULTY,
            faculty_id=1,
            student_id=None,
            is_active=True,
        )
        payload = schemas.RemedialSendMessageRequest(custom_message="Bring assignment notebook.")

        with patch("app.routers.remedial.mirror_document", side_effect=RuntimeError("mongo down")), patch(
            "app.routers.remedial.mirror_event",
            side_effect=RuntimeError("mongo down"),
        ):
            out = send_remedial_code_to_sections(
                class_id=1,
                payload=payload,
                db=self.db,
                current_user=current_user,
            )

        self.assertEqual(out.class_id, 1)
        self.assertEqual(out.remedial_code, "X35YKMBI")
        self.assertEqual(out.sections, ["P132"])
        self.assertEqual(out.recipients, 2)
        self.assertIn("Message sent to 2", out.message)

        rows = (
            self.db.query(models.RemedialMessage)
            .filter(models.RemedialMessage.makeup_class_id == 1)
            .order_by(models.RemedialMessage.student_id.asc())
            .all()
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].student_id, 10)
        self.assertEqual(rows[1].student_id, 11)
        self.assertTrue(all(row.section == "P132" for row in rows))

    def test_send_message_normalizes_legacy_student_section_values(self):
        self.db.add(
            models.Student(
                id=13,
                name="Student Legacy",
                email="stud-legacy@example.com",
                department="CSE",
                semester=5,
                section=" p 132 ",
            )
        )
        self.db.commit()

        current_user = models.AuthUser(
            id=101,
            email="faculty1@example.com",
            password_hash="x",
            role=models.UserRole.FACULTY,
            faculty_id=1,
            student_id=None,
            is_active=True,
        )
        payload = schemas.RemedialSendMessageRequest(custom_message="Normalization check.")

        with patch("app.routers.remedial.mirror_document", return_value=None), patch(
            "app.routers.remedial.mirror_event",
            return_value=None,
        ):
            out = send_remedial_code_to_sections(
                class_id=1,
                payload=payload,
                db=self.db,
                current_user=current_user,
            )

        self.assertEqual(out.recipients, 3)
        rows = (
            self.db.query(models.RemedialMessage)
            .filter(models.RemedialMessage.makeup_class_id == 1)
            .order_by(models.RemedialMessage.student_id.asc())
            .all()
        )
        self.assertEqual([row.student_id for row in rows], [10, 11, 13])
        self.assertEqual(rows[-1].section, "P132")

    def test_send_message_normalizes_legacy_class_section_values(self):
        faculty = self.db.get(models.Faculty, 1)
        faculty.section = "P132, P133"
        class_row = self.db.get(models.MakeUpClass, 1)
        class_row.sections_json = json.dumps([" p 132 , p133 "])
        self.db.commit()

        current_user = models.AuthUser(
            id=101,
            email="faculty1@example.com",
            password_hash="x",
            role=models.UserRole.FACULTY,
            faculty_id=1,
            student_id=None,
            is_active=True,
        )
        payload = schemas.RemedialSendMessageRequest(custom_message="Legacy class section normalization.")

        with patch("app.routers.remedial.mirror_document", return_value=None), patch(
            "app.routers.remedial.mirror_event",
            return_value=None,
        ):
            out = send_remedial_code_to_sections(
                class_id=1,
                payload=payload,
                db=self.db,
                current_user=current_user,
            )

        self.assertEqual(out.sections, ["P132", "P133"])
        self.assertEqual(out.recipients, 3)
        rows = (
            self.db.query(models.RemedialMessage)
            .filter(models.RemedialMessage.makeup_class_id == 1)
            .order_by(models.RemedialMessage.student_id.asc())
            .all()
        )
        self.assertEqual([row.student_id for row in rows], [10, 11, 12])
        self.assertEqual([row.section for row in rows], ["P132", "P132", "P133"])


if __name__ == "__main__":
    unittest.main()
