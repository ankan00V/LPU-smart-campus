import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from app import models, schemas
from app.routers.auth import register_auth_user


class FakeCollection:
    def __init__(self):
        self.docs = []

    def _match(self, doc, query):
        return all(doc.get(key) == value for key, value in query.items())

    def find_one(self, query, projection=None):
        for doc in self.docs:
            if not self._match(doc, query):
                continue
            if not projection:
                return dict(doc)
            visible = {
                key: doc.get(key)
                for key, include in projection.items()
                if include and key in doc
            }
            if "_id" not in projection and "_id" in doc:
                visible["_id"] = doc["_id"]
            return visible
        return None

    def insert_one(self, doc):
        self.docs.append(dict(doc))
        return SimpleNamespace(inserted_id=doc.get("id"))

    def update_one(self, query, update, upsert=False):
        target = None
        for doc in self.docs:
            if self._match(doc, query):
                target = doc
                break
        if target is None:
            if not upsert:
                return SimpleNamespace(matched_count=0, modified_count=0, upserted_id=None)
            target = dict(query)
            self.docs.append(target)
        for key, value in update.get("$set", {}).items():
            target[key] = value
        for key, value in update.get("$setOnInsert", {}).items():
            target.setdefault(key, value)
        return SimpleNamespace(matched_count=1, modified_count=1, upserted_id=target.get("id"))


class FakeMongoDatabase(dict):
    def __getitem__(self, collection_name):
        if collection_name not in self:
            self[collection_name] = FakeCollection()
        return dict.__getitem__(self, collection_name)


def _fake_request() -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/auth/register",
        "headers": [
            (b"user-agent", b"Mozilla/5.0 Codex Test"),
            (b"x-forwarded-for", b"203.0.113.8"),
        ],
        "client": ("203.0.113.8", 443),
        "scheme": "https",
        "server": ("testserver", 443),
    }
    return Request(scope)


class AuthIdentityScreeningTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        SessionLocal = sessionmaker(bind=self.engine)
        self.db = SessionLocal()
        self.mongo = FakeMongoDatabase()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    @patch("app.routers.auth.mirror_event")
    @patch("app.routers.auth.assess_applicant_risk")
    @patch("app.routers.auth._next_unique_id", return_value=501)
    @patch("app.routers.auth._enforce_privileged_registration_gate")
    @patch("app.routers.auth._mongo_db_or_503")
    def test_register_runs_applicant_screening_before_user_insert(
        self,
        mongo_db_mock,
        _gate_mock,
        _next_unique_id_mock,
        assess_applicant_risk_mock,
        _mirror_event_mock,
    ):
        mongo_db_mock.return_value = self.mongo
        payload = schemas.AuthRegisterRequest(
            email="newstudent@gmail.com",
            password="StrongPass1!",
            role=models.UserRole.STUDENT,
            name="New Student",
            department="CSE",
            registration_number="24BCS777",
            section="CSE-A",
            semester=2,
            parent_email="parent@gmail.com",
        )

        result = register_auth_user(
            payload=payload,
            request=_fake_request(),
            sql_db=self.db,
        )

        self.assertEqual(result.email, "newstudent@gmail.com")
        self.assertEqual(result.role, models.UserRole.STUDENT)
        self.assertEqual(len(self.mongo["auth_users"].docs), 1)
        assess_applicant_risk_mock.assert_called_once()
        screening_payload = assess_applicant_risk_mock.call_args.args[1]
        self.assertEqual(screening_payload.applicant_email, "newstudent@gmail.com")
        self.assertEqual(screening_payload.external_subject_key, "signup:newstudent@gmail.com")
        self.assertEqual(screening_payload.claimed_role, "student")

    @patch("app.routers.auth.mirror_event")
    @patch("app.routers.auth.assess_applicant_risk")
    @patch("app.routers.auth._enforce_privileged_registration_gate")
    @patch("app.routers.auth._mongo_db_or_503")
    def test_register_duplicate_email_still_runs_applicant_screening(
        self,
        mongo_db_mock,
        _gate_mock,
        assess_applicant_risk_mock,
        _mirror_event_mock,
    ):
        mongo_db_mock.return_value = self.mongo
        self.mongo["auth_users"].insert_one(
            {
                "id": 99,
                "email": "duplicate@gmail.com",
                "role": "student",
                "password_hash": "x",
                "is_active": True,
            }
        )
        payload = schemas.AuthRegisterRequest(
            email="duplicate@gmail.com",
            password="StrongPass1!",
            role=models.UserRole.STUDENT,
            name="Duplicate Student",
            department="CSE",
            registration_number="24BCS778",
            section="CSE-A",
            semester=2,
        )

        with self.assertRaises(HTTPException) as ctx:
            register_auth_user(
                payload=payload,
                request=_fake_request(),
                sql_db=self.db,
            )

        self.assertEqual(ctx.exception.status_code, 409)
        assess_applicant_risk_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
