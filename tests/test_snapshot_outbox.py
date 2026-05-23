import os
import unittest
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["APP_RUNTIME_STRICT"] = "false"
os.environ["SQLALCHEMY_DATABASE_URL"] = "sqlite:///:memory:"

from app import models
from app.main import sync_sql_snapshot_to_mongo


class StartupSnapshotOutboxFallbackTests(unittest.TestCase):
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
        student = models.Student(
            id=1,
            name="Snapshot Student",
            email="snapshot.student@example.com",
            registration_number="REG-001",
            parent_email="parent@example.com",
            section="P132",
            department="CSE",
            semester=4,
        )
        self.db.add(student)
        self.db.flush()

        auth_user = models.AuthUser(
            id=101,
            email=student.email,
            password_hash="hash",
            role=models.UserRole.STUDENT,
            student_id=int(student.id),
            faculty_id=None,
            is_active=True,
        )
        self.db.add(auth_user)
        self.db.commit()

    def test_sync_snapshot_queues_mirror_writes_when_mongo_unavailable(self):
        with mock.patch("app.main.get_mongo_db", return_value=None), mock.patch(
            "app.main.mirror_document",
            return_value=False,
        ) as mirror_document:
            sync_sql_snapshot_to_mongo(self.db)

        mirrored_collections = [call.args[0] for call in mirror_document.call_args_list]
        self.assertIn("students", mirrored_collections)
        self.assertIn("auth_users", mirrored_collections)

        student_call = next(call for call in mirror_document.call_args_list if call.args[0] == "students")
        self.assertEqual(student_call.kwargs.get("upsert_filter"), {"id": 1})

        auth_call = next(call for call in mirror_document.call_args_list if call.args[0] == "auth_users")
        self.assertEqual(auth_call.kwargs.get("upsert_filter"), {"email": "snapshot.student@example.com"})
        self.assertEqual(int(auth_call.args[1]["id"]), 101)


if __name__ == "__main__":
    unittest.main()
