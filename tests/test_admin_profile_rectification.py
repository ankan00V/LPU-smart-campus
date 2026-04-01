import unittest
from datetime import datetime, timedelta
from unittest import mock

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.routers.admin import (
    admin_rectify_faculty_profile,
    admin_rectify_student_profile,
    admin_search_faculty_for_rectification,
    admin_search_student_for_rectification,
)
from app.routers.attendance import list_profile_notices


class _FakeCursor:
    def __init__(self, docs):
        self.docs = list(docs)

    def sort(self, key, direction):
        reverse = int(direction) < 0
        self.docs.sort(key=lambda item: item.get(key) or datetime.min, reverse=reverse)
        return self

    def limit(self, value):
        self.docs = self.docs[: int(value)]
        return self

    def __iter__(self):
        return iter(self.docs)


class _FakeCollection:
    def __init__(self, docs):
        self.docs = list(docs)

    def find(self, query):
        actions = set(query.get("action", {}).get("$in", []))
        subject_role = query.get("subject_role")
        subject_id = int(query.get("subject_id") or 0)
        wants_notice = bool(query.get("notice_message", {}).get("$exists"))
        rows = []
        for doc in self.docs:
            if actions and doc.get("action") not in actions:
                continue
            if doc.get("subject_role") != subject_role:
                continue
            if int(doc.get("subject_id") or 0) != subject_id:
                continue
            if wants_notice and "notice_message" not in doc:
                continue
            rows.append(dict(doc))
        return _FakeCursor(rows)


class _FakeMongoDb(dict):
    def __init__(self, docs):
        super().__init__({"admin_audit_logs": _FakeCollection(docs)})


class AdminProfileRectificationTests(unittest.TestCase):
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
                    id=101,
                    name="Student One",
                    email="student.one@example.com",
                    registration_number="22BCS101",
                    section="P132",
                    department="CSE",
                    semester=4,
                    parent_email="parent.one@example.com",
                ),
                models.Student(
                    id=102,
                    name="Student Two",
                    email="student.two@example.com",
                    registration_number="22BCS102",
                    section="P200",
                    department="ECE",
                    semester=5,
                ),
                models.Faculty(
                    id=11,
                    name="Faculty One",
                    email="faculty.one@example.com",
                    faculty_identifier="FAC101",
                    section="P132",
                    department="CSE",
                ),
                models.Faculty(
                    id=12,
                    name="Faculty Two",
                    email="faculty.two@example.com",
                    faculty_identifier="FAC102",
                    section="P200",
                    department="ECE",
                ),
            ]
        )
        self.db.commit()

    @staticmethod
    def _admin_user(user_id=900) -> models.AuthUser:
        return models.AuthUser(
            id=user_id,
            email=f"admin{user_id}@example.com",
            password_hash="x",
            role=models.UserRole.ADMIN,
            student_id=None,
            faculty_id=None,
            is_active=True,
        )

    @staticmethod
    def _student_user(student_id=101, user_id=901) -> models.AuthUser:
        return models.AuthUser(
            id=user_id,
            email="student.one@example.com",
            password_hash="x",
            role=models.UserRole.STUDENT,
            student_id=student_id,
            faculty_id=None,
            is_active=True,
        )

    def test_admin_can_search_student_profile_for_rectification_by_email(self):
        out = admin_search_student_for_rectification(
            query="student.one@example.com",
            db=self.db,
            _=self._admin_user(),
        )
        self.assertEqual(out.student_id, 101)
        self.assertEqual(out.registration_number, "22BCS101")
        self.assertEqual(out.email, "student.one@example.com")

    def test_admin_can_rectify_student_profile_and_publish_notice(self):
        with mock.patch("app.routers.admin.mirror_document"), mock.patch(
            "app.routers.admin._sync_student_to_mongo"
        ), mock.patch("app.routers.admin.publish_domain_event") as publish_patch:
            out = admin_rectify_student_profile(
                student_id=101,
                payload=schemas.AdminStudentProfileRectificationRequest(
                    name="Student Prime",
                    registration_number="22BCS555",
                    section="P300",
                    department="IT",
                    semester=6,
                    parent_email="parent.updated@example.com",
                    note="Updated after document verification.",
                ),
                db=self.db,
                current_user=self._admin_user(),
            )

        self.assertEqual(set(out.changed_fields), {"name", "registration_number", "section", "department", "semester", "parent_email"})
        self.assertIn("Your profile was updated by Admin", out.notice_message or "")
        refreshed = self.db.get(models.Student, 101)
        self.assertEqual(refreshed.name, "STUDENT PRIME")
        self.assertEqual(refreshed.registration_number, "22BCS555")
        self.assertEqual(refreshed.section, "P300")
        self.assertEqual(refreshed.department, "IT")
        self.assertEqual(refreshed.semester, 6)
        self.assertEqual(refreshed.parent_email, "parent.updated@example.com")
        self.assertEqual(publish_patch.call_args.args[0], "attendance.profile.rectified")
        self.assertEqual(
            publish_patch.call_args.kwargs["scopes"],
            {"student:101", "role:admin"},
        )

    def test_student_rectification_blocks_duplicate_registration_number(self):
        with self.assertRaises(HTTPException) as ctx:
            admin_rectify_student_profile(
                student_id=101,
                payload=schemas.AdminStudentProfileRectificationRequest(
                    registration_number="22BCS102",
                ),
                db=self.db,
                current_user=self._admin_user(),
            )
        self.assertEqual(ctx.exception.status_code, 409)

    def test_admin_can_search_and_rectify_faculty_profile(self):
        searched = admin_search_faculty_for_rectification(
            query="faculty.one@example.com",
            db=self.db,
            _=self._admin_user(),
        )
        self.assertEqual(searched.faculty_id, 11)
        self.assertEqual(searched.faculty_identifier, "FAC101")

        with mock.patch("app.routers.admin.mirror_document"), mock.patch(
            "app.routers.admin._sync_faculty_to_mongo"
        ), mock.patch("app.routers.admin.publish_domain_event") as publish_patch:
            out = admin_rectify_faculty_profile(
                faculty_id=11,
                payload=schemas.AdminFacultyProfileRectificationRequest(
                    name="Faculty Prime",
                    faculty_identifier="FAC777",
                    section="P500",
                    department="AIML",
                    note="Corrected identifier and section.",
                ),
                db=self.db,
                current_user=self._admin_user(),
            )

        self.assertEqual(set(out.changed_fields), {"name", "faculty_identifier", "section", "department"})
        refreshed = self.db.get(models.Faculty, 11)
        self.assertEqual(refreshed.name, "FACULTY PRIME")
        self.assertEqual(refreshed.faculty_identifier, "FAC777")
        self.assertEqual(refreshed.section, "P500")
        self.assertEqual(refreshed.department, "AIML")
        self.assertEqual(publish_patch.call_args.kwargs["scopes"], {"faculty:11", "role:admin"})

    def test_profile_notices_returns_latest_student_rectification_messages(self):
        now_dt = datetime.utcnow()
        docs = [
            {
                "action": "admin_student_profile_rectification",
                "subject_role": "student",
                "subject_id": 101,
                "notice_message": "Your profile was updated by Admin. Updated: section.",
                "actor_label": "Admin",
                "changed_fields": ["section"],
                "created_at": now_dt - timedelta(minutes=5),
            },
            {
                "action": "admin_student_profile_rectification",
                "subject_role": "student",
                "subject_id": 101,
                "notice_message": "Your profile was updated by Admin. Updated: registration number.",
                "actor_label": "Admin",
                "changed_fields": ["registration_number"],
                "created_at": now_dt - timedelta(minutes=1),
            },
            {
                "action": "admin_faculty_profile_rectification",
                "subject_role": "faculty",
                "subject_id": 11,
                "notice_message": "Ignore faculty notice for this test.",
                "actor_label": "Admin",
                "changed_fields": ["department"],
                "created_at": now_dt,
            },
        ]

        with mock.patch("app.routers.attendance.get_mongo_db", return_value=_FakeMongoDb(docs)):
            out = list_profile_notices(
                limit=2,
                current_user=self._student_user(),
            )

        self.assertEqual(len(out), 2)
        self.assertEqual(out[0].changed_fields, ["registration_number"])
        self.assertIn("registration number", out[0].message)
        self.assertEqual(out[1].changed_fields, ["section"])


if __name__ == "__main__":
    unittest.main()
