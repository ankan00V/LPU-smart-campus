import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest import mock

from fastapi import HTTPException
from starlette.requests import Request

from app import models
from app.auth_utils import (
    ACCESS_COOKIE_NAME,
    create_session_tokens,
    get_current_user,
    rotate_session_tokens,
)


class _UpdateResult:
    def __init__(self, *, matched_count: int = 0):
        self.matched_count = matched_count


class _Collection:
    def __init__(self):
        self._rows: list[dict] = []

    def insert_one(self, doc: dict):
        self._rows.append(dict(doc))

    def find(self, query: dict):
        return [dict(row) for row in self._rows if self._match(row, query)]

    def find_one(self, query: dict, projection: dict | None = None):
        for row in self._rows:
            if self._match(row, query):
                if not projection:
                    return dict(row)
                projected: dict = {}
                for key, include in projection.items():
                    if include and key in row:
                        projected[key] = row[key]
                return projected
        return None

    def update_one(self, query: dict, update: dict, upsert: bool = False):
        for idx, row in enumerate(self._rows):
            if not self._match(row, query):
                continue
            updated = dict(row)
            self._apply_update(updated, update, is_insert=False)
            self._rows[idx] = updated
            return _UpdateResult(matched_count=1)

        if upsert:
            created = {}
            for key, value in query.items():
                if not key.startswith("$") and not isinstance(value, dict):
                    created[key] = value
            self._apply_update(created, update, is_insert=True)
            self._rows.append(created)
        return _UpdateResult(matched_count=0)

    @staticmethod
    def _apply_update(row: dict, update: dict, *, is_insert: bool) -> None:
        for key, payload in update.items():
            if key == "$set":
                row.update(payload)
            elif key == "$setOnInsert":
                if is_insert:
                    row.update(payload)

    @staticmethod
    def _match(row: dict, query: dict) -> bool:
        for key, expected in query.items():
            if key == "$or":
                return any(_Collection._match(row, branch) for branch in expected)
            value = row.get(key)
            if isinstance(expected, dict):
                if "$gt" in expected and not (value is not None and value > expected["$gt"]):
                    return False
                if "$lt" in expected and not (value is not None and value < expected["$lt"]):
                    return False
                continue
            if value != expected:
                return False
        return True


class _FakeMongo:
    def __init__(self):
        self._collections: dict[str, _Collection] = {}

    def __getitem__(self, name: str) -> _Collection:
        if name not in self._collections:
            self._collections[name] = _Collection()
        return self._collections[name]


def _request(*, cookies: dict[str, str] | None = None, headers: dict[str, str] | None = None) -> Request:
    encoded_headers: list[tuple[bytes, bytes]] = []
    for key, value in (headers or {}).items():
        encoded_headers.append((key.lower().encode("utf-8"), str(value).encode("utf-8")))
    if cookies:
        cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
        encoded_headers.append((b"cookie", cookie_header.encode("utf-8")))
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": encoded_headers,
        "client": ("127.0.0.1", 5000),
        "query_string": b"",
    }
    return Request(scope)


class AuthHardenedSessionTests(unittest.TestCase):
    def setUp(self):
        self.mongo = _FakeMongo()
        self.mongo["auth_users"].insert_one(
            {
                "id": 9001,
                "email": "owner@gmail.com",
                "role": models.UserRole.OWNER.value,
                "student_id": None,
                "faculty_id": None,
                "alternate_email": None,
                "primary_login_verified": True,
                "is_active": True,
                "mfa_enabled": True,
                "created_at": datetime.utcnow(),
                "last_login_at": datetime.utcnow(),
            }
        )

    def test_refresh_rotation_revokes_old_access_token_and_detects_replay(self):
        principal = SimpleNamespace(
            id=9001,
            role=models.UserRole.OWNER,
            mfa_authenticated=True,
        )
        initial = create_session_tokens(
            self.mongo,
            principal,
            request=_request(headers={"user-agent": "pytest", "x-device-id": "device-1"}),
        )
        rotated = rotate_session_tokens(
            self.mongo,
            refresh_token=initial["refresh_token"],
            request=_request(headers={"user-agent": "pytest-rotated", "x-device-id": "device-1"}),
        )
        self.assertNotEqual(initial["refresh_token"], rotated["refresh_token"])

        with self.assertRaises(HTTPException) as replay_ctx:
            rotate_session_tokens(
                self.mongo,
                refresh_token=initial["refresh_token"],
                request=_request(headers={"user-agent": "pytest-replay"}),
            )
        self.assertEqual(replay_ctx.exception.status_code, 401)

        session_doc = self.mongo["auth_sessions"].find_one({"sid": initial["sid"]})
        self.assertIsNotNone(session_doc.get("revoked_at"))

        revoked_old_access = self.mongo["auth_token_revocations"].find_one({"jti": initial["access_jti"]})
        self.assertIsNotNone(revoked_old_access)

    def test_get_current_user_rejects_old_rotated_access_token(self):
        principal = SimpleNamespace(
            id=9001,
            role=models.UserRole.OWNER,
            mfa_authenticated=True,
        )
        initial = create_session_tokens(
            self.mongo,
            principal,
            request=_request(headers={"user-agent": "pytest", "x-device-id": "device-1"}),
        )
        rotate_session_tokens(
            self.mongo,
            refresh_token=initial["refresh_token"],
            request=_request(headers={"user-agent": "pytest-rotated"}),
        )

        with mock.patch("app.auth_utils.get_mongo_db", return_value=self.mongo):
            with self.assertRaises(HTTPException) as ctx:
                get_current_user(
                    request=_request(cookies={ACCESS_COOKIE_NAME: initial["access_token"]}),
                    credentials=None,
                )
        self.assertEqual(ctx.exception.status_code, 401)

if __name__ == "__main__":
    unittest.main()
