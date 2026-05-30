import unittest
from datetime import datetime
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.routers.messages import (
    _build_support_contacts_for_student,
    get_support_query_thread,
    send_support_query_message,
)


class SupportQuerySubjectContactsTests(unittest.TestCase):
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
        self.db.add_all(
            [
                models.Student(
                    id=1,
                    name="Student One",
                    email="student.one@example.com",
                    registration_number="22BCS101",
                    section="423ZK",
                    department="CSE",
                    semester=4,
                ),
                models.Faculty(
                    id=16,
                    name="RUDRANIL MONDAL",
                    email="rudranilmondal23@lpu.in",
                    department="CSE",
                    section="423ZK",
                ),
                models.Course(
                    id=101,
                    code="CSE332",
                    title="Industry Ethics and Legal Issues",
                    faculty_id=16,
                ),
                models.Course(
                    id=102,
                    code="INT312",
                    title="Big Data Fundamentals",
                    faculty_id=16,
                ),
                models.Enrollment(id=201, student_id=1, course_id=101),
                models.Enrollment(id=202, student_id=1, course_id=102),
                models.SupportQueryMessage(
                    id=301,
                    student_id=1,
                    faculty_id=16,
                    section="423ZK",
                    category="Attendance",
                    subject="CSE332 - Industry Ethics and Legal Issues",
                    message="Please check CSE332 attendance.",
                    sender_role="student",
                    created_at=datetime(2026, 5, 30, 10, 0, 0),
                ),
                models.SupportQueryMessage(
                    id=302,
                    student_id=1,
                    faculty_id=16,
                    section="423ZK",
                    category="Attendance",
                    subject="INT312 - Big Data Fundamentals",
                    message="Please check INT312 attendance.",
                    sender_role="student",
                    created_at=datetime(2026, 5, 30, 10, 5, 0),
                ),
            ]
        )
        self.db.commit()

    def _student_user(self):
        return models.AuthUser(
            id=9001,
            email="student.one@example.com",
            password_hash="x",
            role=models.UserRole.STUDENT,
            student_id=1,
            faculty_id=None,
            is_active=True,
        )

    def test_student_contacts_stay_split_by_subject_for_same_faculty(self):
        contacts, _ = _build_support_contacts_for_student(self.db, student_id=1)

        self.assertEqual([contact.id for contact in contacts], [16, 16])
        self.assertEqual([contact.course_code for contact in contacts], ["CSE332", "INT312"])
        self.assertEqual(len({contact.contact_key for contact in contacts}), 2)
        self.assertTrue(all(contact.name == "RUDRANIL MONDAL" for contact in contacts))
        self.assertIn("Industry Ethics", contacts[0].descriptor)
        self.assertIn("Big Data", contacts[1].descriptor)

    def test_student_thread_can_filter_same_faculty_by_subject(self):
        rows = get_support_query_thread(
            counterparty_id=16,
            category="Attendance",
            subject="INT312 - Big Data Fundamentals",
            limit=120,
            db=self.db,
            current_user=self._student_user(),
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].subject, "INT312 - Big Data Fundamentals")
        self.assertEqual(rows[0].message, "Please check INT312 attendance.")

    @mock.patch("app.routers.messages.enqueue_notification", autospec=True)
    @mock.patch("app.routers.messages.publish_domain_event", autospec=True)
    @mock.patch("app.routers.messages.mirror_document", autospec=True)
    def test_student_support_message_notifies_faculty_not_admin(
        self,
        _mirror_document,
        publish_event,
        _enqueue_notification,
    ):
        payload = schemas.SupportQuerySend(
            recipient_id=16,
            category=schemas.SupportQueryCategory.ATTENDANCE,
            subject="INT312 - Big Data Fundamentals",
            message="Please review my INT312 absent class.",
        )

        out = send_support_query_message(
            payload=payload,
            db=self.db,
            current_user=self._student_user(),
        )

        self.assertEqual(out.subject, "INT312 - Big Data Fundamentals")
        publish_event.assert_called_once()
        self.assertEqual(publish_event.call_args.args[0], "messages.support.updated")
        self.assertEqual(
            publish_event.call_args.kwargs["scopes"],
            {"student:1", "faculty:16"},
        )
        self.assertEqual(
            publish_event.call_args.kwargs["payload"]["subject"],
            "INT312 - Big Data Fundamentals",
        )


if __name__ == "__main__":
    unittest.main()
