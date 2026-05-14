import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from pymongo.errors import PyMongoError
from starlette.requests import Request
from starlette.responses import Response

from app import models, schemas
from app.auth_utils import CurrentUser, hash_otp, hash_password
from app.enterprise_controls import hash_backup_code
from app.routers import auth


class _UpdateResult:
    def __init__(self, *, matched_count: int = 0):
        self.matched_count = matched_count


class _Collection:
    def __init__(self):
        self._rows: list[dict] = []

    def insert_one(self, doc: dict):
        self._rows.append(dict(doc))

    def find_one(self, query: dict, projection: dict | None = None, sort: list[tuple[str, int]] | None = None):
        matches = [dict(row) for row in self._rows if self._match(row, query)]
        if sort:
            for key, direction in reversed(sort):
                matches.sort(key=lambda row: row.get(key), reverse=int(direction) < 0)
        if not matches:
            return None
        row = matches[0]
        if not projection:
            return row
        projected: dict = {}
        for key, include in projection.items():
            if include and key in row:
                projected[key] = row[key]
        return projected

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

    def update_many(self, query: dict, update: dict):
        matched = 0
        for idx, row in enumerate(self._rows):
            if not self._match(row, query):
                continue
            updated = dict(row)
            self._apply_update(updated, update, is_insert=False)
            self._rows[idx] = updated
            matched += 1
        return _UpdateResult(matched_count=matched)

    @staticmethod
    def _apply_update(row: dict, update: dict, *, is_insert: bool):
        for operator, payload in update.items():
            if operator == "$set":
                row.update(payload)
            elif operator == "$inc":
                for field_name, value in payload.items():
                    row[field_name] = int(row.get(field_name, 0)) + int(value)
            elif operator == "$setOnInsert" and is_insert:
                row.update(payload)

    @staticmethod
    def _match(row: dict, query: dict) -> bool:
        for key, expected in query.items():
            if key == "$or":
                return any(_Collection._match(row, branch) for branch in expected)
            value = row.get(key)
            if isinstance(expected, dict):
                if "$in" in expected and value not in expected["$in"]:
                    return False
                if "$exists" in expected:
                    exists = key in row
                    if exists != bool(expected["$exists"]):
                        return False
                continue
            if value != expected:
                return False
        return True


class _ConsumeConflictCollection(_Collection):
    def update_one(self, query: dict, update: dict, upsert: bool = False):
        if query.get("id") == 31 and query.get("used_at", object()) is None:
            return _UpdateResult(matched_count=0)
        return super().update_one(query, update, upsert=upsert)


class _RaisingCollection:
    def __init__(self, *, find_one_exc: Exception | None = None, update_one_exc: Exception | None = None):
        self._find_one_exc = find_one_exc
        self._update_one_exc = update_one_exc

    def find_one(self, *_args, **_kwargs):
        if self._find_one_exc is not None:
            raise self._find_one_exc
        return None

    def update_one(self, *_args, **_kwargs):
        if self._update_one_exc is not None:
            raise self._update_one_exc
        return _UpdateResult(matched_count=0)


class _FakeMongo:
    def __init__(self, *, auth_otps_collection: _Collection | None = None):
        self._collections: dict[str, _Collection] = {}
        if auth_otps_collection is not None:
            self._collections["auth_otps"] = auth_otps_collection

    def __getitem__(self, name: str) -> _Collection:
        if name not in self._collections:
            self._collections[name] = _Collection()
        return self._collections[name]


def _request(path: str) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": path,
        "headers": [(b"user-agent", b"pytest"), (b"x-device-id", b"device-1")],
        "client": ("127.0.0.1", 9000),
        "query_string": b"",
    }
    return Request(scope)


class AuthOtpMfaReliabilityTests(unittest.TestCase):
    def test_request_login_otp_allows_retry_after_failed_delivery_for_privileged_roles(self):
        mongo = _FakeMongo()
        mongo["auth_users"].insert_one(
            {
                "id": 7,
                "email": "faculty@gmail.com",
                "password_hash": hash_password("Faculty@123"),
                "role": models.UserRole.FACULTY.value,
                "student_id": None,
                "faculty_id": None,
                "is_active": True,
                "password_updated_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
            }
        )
        now = datetime.utcnow()
        mongo["auth_otps"].insert_one(
            {
                "id": 1,
                "user_id": 7,
                "purpose": "login",
                "otp_hash": "old",
                "otp_salt": "old",
                "attempts_count": 0,
                "expires_at": now + timedelta(minutes=10),
                "used_at": now,
                "created_at": now,
            }
        )

        with (
            patch("app.routers.auth._mongo_db_or_503", return_value=mongo),
            patch("app.routers.auth._ensure_auth_user_id", return_value=7),
            patch("app.routers.auth._ensure_role_profile_link", return_value=None),
            patch("app.routers.auth.enforce_rate_limit", return_value=None),
            patch("app.routers.auth._verify_student_auth_recaptcha", return_value=None),
            patch("app.routers.auth._send_login_otp_with_timeout", return_value={"channel": "smtp-email"}),
            patch("app.routers.auth._next_unique_id", side_effect=[2, 3]),
            patch("app.routers.auth.mirror_event", return_value=None),
        ):
            result = auth.request_login_otp(
                schemas.LoginOTPRequest(
                    email="faculty@gmail.com",
                    password="Faculty@123",
                    captcha_token="turnstile-token-1234567890",
                ),
                request=_request("/auth/login/request-otp"),
                sql_db=SimpleNamespace(),
            )

        self.assertEqual(result.message, "OTP sent successfully")
        delivery = mongo["auth_otp_delivery"].find_one({"id": 3})
        self.assertIsNotNone(delivery)
        self.assertEqual(delivery["status"], "sent")

    def test_student_password_login_requires_password_setup_completion(self):
        mongo = _FakeMongo()
        mongo["auth_users"].insert_one(
            {
                "id": 70,
                "email": "legacy.student@gmail.com",
                "password_hash": hash_password("Student@123"),
                "role": models.UserRole.STUDENT.value,
                "student_id": None,
                "faculty_id": None,
                "is_active": True,
                "password_setup_required": True,
                "created_at": datetime.utcnow(),
            }
        )

        with (
            patch("app.routers.auth._mongo_db_or_503", return_value=mongo),
            patch("app.routers.auth.enforce_rate_limit", return_value=None),
            patch("app.routers.auth._verify_student_auth_recaptcha", return_value=None),
        ):
            with self.assertRaises(HTTPException) as ctx:
                auth.login_student_with_password(
                    schemas.LoginPasswordRequest(email="legacy.student@gmail.com", password="Student@123"),
                    response=Response(),
                    request=_request("/auth/student/login"),
                    sql_db=SimpleNamespace(),
                )

        self.assertEqual(ctx.exception.status_code, 428)
        self.assertIn("Login via temporary OTP", ctx.exception.detail)

    def test_student_passwordless_login_otp_is_allowed_only_for_password_setup_accounts(self):
        mongo = _FakeMongo()
        mongo["auth_users"].insert_one(
            {
                "id": 72,
                "email": "legacy.student@gmail.com",
                "password_hash": hash_password("temporary-placeholder"),
                "role": models.UserRole.STUDENT.value,
                "student_id": 172,
                "faculty_id": None,
                "is_active": True,
                "password_setup_required": True,
                "created_at": datetime.utcnow(),
            }
        )
        mongo["students"].insert_one(
            {
                "id": 172,
                "name": "LEGACY STUDENT",
                "email": "legacy.student@gmail.com",
                "registration_number": "12200172",
                "section": "K23AA",
                "department": "CSE",
                "semester": 4,
                "created_at": datetime.utcnow(),
            }
        )

        with (
            patch("app.routers.auth._mongo_db_or_503", return_value=mongo),
            patch("app.routers.auth._ensure_auth_user_id", return_value=72),
            patch("app.routers.auth._ensure_role_profile_link", return_value=None),
            patch("app.routers.auth.enforce_rate_limit", return_value=None),
            patch("app.routers.auth._verify_student_auth_recaptcha", return_value=None),
            patch("app.routers.auth._send_login_otp_with_timeout", return_value={"channel": "smtp-email"}),
            patch("app.routers.auth._next_unique_id", side_effect=[101, 102]),
            patch("app.routers.auth.mirror_event", return_value=None),
        ):
            result = auth.request_login_otp(
                schemas.LoginOTPRequest(
                    email="legacy.student@gmail.com",
                    captcha_token="turnstile-token-1234567890",
                ),
                request=_request("/auth/login/request-otp"),
                sql_db=SimpleNamespace(),
            )

        self.assertEqual(result.message, "OTP sent successfully")
        otp = mongo["auth_otps"].find_one({"id": 101})
        self.assertIsNotNone(otp)
        self.assertEqual(otp["purpose"], "login")

    def test_request_login_otp_rejects_unknown_email_with_create_account_message(self):
        mongo = _FakeMongo()

        with (
            patch("app.routers.auth._mongo_db_or_503", return_value=mongo),
            patch("app.routers.auth.enforce_rate_limit", return_value=None),
        ):
            with self.assertRaises(HTTPException) as ctx:
                auth.request_login_otp(
                    schemas.LoginOTPRequest(
                        email="missing.user@gmail.com",
                        captcha_token="turnstile-token-1234567890",
                    ),
                    request=_request("/auth/login/request-otp"),
                    sql_db=SimpleNamespace(),
                )

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(
            ctx.exception.detail,
            "There is no account associated with this mail, kindly create one first.",
        )

    def test_student_passwordless_login_otp_is_allowed_for_password_ready_accounts(self):
        mongo = _FakeMongo()
        mongo["auth_users"].insert_one(
            {
                "id": 73,
                "email": "ready.student@gmail.com",
                "password_hash": hash_password("Student@123"),
                "role": models.UserRole.STUDENT.value,
                "student_id": 273,
                "faculty_id": None,
                "is_active": True,
                "password_setup_required": False,
                "password_updated_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
            }
        )
        mongo["students"].insert_one(
            {
                "id": 273,
                "name": "READY STUDENT",
                "email": "ready.student@gmail.com",
                "registration_number": "12200273",
                "section": "K23AA",
                "department": "CSE",
                "semester": 4,
                "created_at": datetime.utcnow(),
            }
        )

        with (
            patch("app.routers.auth._mongo_db_or_503", return_value=mongo),
            patch("app.routers.auth._ensure_auth_user_id", return_value=73),
            patch("app.routers.auth._ensure_role_profile_link", return_value=None),
            patch("app.routers.auth.enforce_rate_limit", return_value=None),
            patch("app.routers.auth._verify_student_auth_recaptcha", return_value=None),
            patch("app.routers.auth._send_login_otp_with_timeout", return_value={"channel": "smtp-email"}),
            patch("app.routers.auth._next_unique_id", side_effect=[113, 114]),
            patch("app.routers.auth.mirror_event", return_value=None),
        ):
            result = auth.request_login_otp(
                schemas.LoginOTPRequest(
                    email="ready.student@gmail.com",
                    captcha_token="turnstile-token-1234567890",
                ),
                request=_request("/auth/login/request-otp"),
                sql_db=SimpleNamespace(),
            )

        self.assertEqual(result.message, "OTP sent successfully")

    def test_student_passwordless_login_otp_is_allowed_for_password_ready_accounts_when_flag_is_missing(self):
        mongo = _FakeMongo()
        mongo["auth_users"].insert_one(
            {
                "id": 74,
                "email": "ready.flagless.student@gmail.com",
                "password_hash": hash_password("Student@123"),
                "role": models.UserRole.STUDENT.value,
                "student_id": 274,
                "faculty_id": None,
                "is_active": True,
                "primary_login_verified": True,
                "created_at": datetime.utcnow(),
            }
        )
        mongo["students"].insert_one(
            {
                "id": 274,
                "name": "READY FLAGLESS",
                "email": "ready.flagless.student@gmail.com",
                "registration_number": "12200274",
                "section": "K23AA",
                "department": "CSE",
                "semester": 4,
                "created_at": datetime.utcnow(),
            }
        )

        with (
            patch("app.routers.auth._mongo_db_or_503", return_value=mongo),
            patch("app.routers.auth._ensure_auth_user_id", return_value=74),
            patch("app.routers.auth._ensure_role_profile_link", return_value=None),
            patch("app.routers.auth.enforce_rate_limit", return_value=None),
            patch("app.routers.auth._verify_student_auth_recaptcha", return_value=None),
            patch("app.routers.auth._send_login_otp_with_timeout", return_value={"channel": "smtp-email"}),
            patch("app.routers.auth._next_unique_id", side_effect=[115, 116]),
            patch("app.routers.auth.mirror_event", return_value=None),
        ):
            result = auth.request_login_otp(
                schemas.LoginOTPRequest(
                    email="ready.flagless.student@gmail.com",
                    captcha_token="turnstile-token-1234567890",
                ),
                request=_request("/auth/login/request-otp"),
                sql_db=SimpleNamespace(),
            )

        self.assertEqual(result.message, "OTP sent successfully")

    def test_faculty_passwordless_login_otp_is_allowed_for_legacy_accounts(self):
        mongo = _FakeMongo()
        mongo["auth_users"].insert_one(
            {
                "id": 81,
                "email": "legacy.faculty@gmail.com",
                "password_hash": hash_password("temporary-placeholder"),
                "role": models.UserRole.FACULTY.value,
                "student_id": None,
                "faculty_id": 14,
                "is_active": True,
                "password_setup_required": True,
                "created_at": datetime.utcnow(),
            }
        )
        mongo["faculty"].insert_one(
            {
                "id": 14,
                "name": "LEGACY FACULTY",
                "email": "legacy.faculty@gmail.com",
                "faculty_identifier": "FAC0014",
                "section": "K23AA",
                "department": "CSE",
                "created_at": datetime.utcnow(),
            }
        )

        with (
            patch("app.routers.auth._mongo_db_or_503", return_value=mongo),
            patch("app.routers.auth._ensure_auth_user_id", return_value=81),
            patch("app.routers.auth._ensure_role_profile_link", return_value=None),
            patch("app.routers.auth.enforce_rate_limit", return_value=None),
            patch("app.routers.auth._verify_student_auth_recaptcha", return_value=None),
            patch("app.routers.auth._send_login_otp_with_timeout", return_value={"channel": "smtp-email"}),
            patch("app.routers.auth._next_unique_id", side_effect=[111, 112]),
            patch("app.routers.auth.mirror_event", return_value=None),
        ):
            result = auth.request_login_otp(
                schemas.LoginOTPRequest(
                    email="legacy.faculty@gmail.com",
                    captcha_token="turnstile-token-1234567890",
                ),
                request=_request("/auth/login/request-otp"),
                sql_db=SimpleNamespace(),
            )

        self.assertEqual(result.message, "OTP sent successfully")
        otp = mongo["auth_otps"].find_one({"id": 111})
        self.assertIsNotNone(otp)
        self.assertEqual(otp["purpose"], "login")

    def test_faculty_request_login_otp_rejects_incorrect_password(self):
        mongo = _FakeMongo()
        mongo["auth_users"].insert_one(
            {
                "id": 82,
                "email": "faculty.ready@gmail.com",
                "password_hash": hash_password("Faculty@123"),
                "role": models.UserRole.FACULTY.value,
                "student_id": None,
                "faculty_id": 18,
                "is_active": True,
                "password_updated_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
            }
        )

        with (
            patch("app.routers.auth._mongo_db_or_503", return_value=mongo),
            patch("app.routers.auth.enforce_rate_limit", return_value=None),
            patch("app.routers.auth._verify_student_auth_recaptcha", return_value=None),
        ):
            with self.assertRaises(HTTPException) as ctx:
                auth.request_login_otp(
                    schemas.LoginOTPRequest(
                        email="faculty.ready@gmail.com",
                        password="Wrong@123",
                        captcha_token="turnstile-token-1234567890",
                    ),
                    request=_request("/auth/login/request-otp"),
                    sql_db=SimpleNamespace(),
                )

        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(ctx.exception.detail, "Incorrect password")

    def test_student_password_login_succeeds_with_completed_password_setup(self):
        mongo = _FakeMongo()
        mongo["auth_users"].insert_one(
            {
                "id": 71,
                "email": "student.ready@gmail.com",
                "password_hash": hash_password("Student@123"),
                "role": models.UserRole.STUDENT.value,
                "student_id": 9,
                "faculty_id": None,
                "is_active": True,
                "password_updated_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
            }
        )
        session_tokens = {
            "access_token": "access-token",
            "access_expires_at": datetime.utcnow() + timedelta(minutes=30),
            "refresh_token": "refresh-token",
            "refresh_expires_at": datetime.utcnow() + timedelta(days=7),
        }

        with (
            patch("app.routers.auth._mongo_db_or_503", return_value=mongo),
            patch("app.routers.auth.enforce_rate_limit", return_value=None),
            patch("app.routers.auth._verify_student_auth_recaptcha", return_value=None),
            patch("app.routers.auth._ensure_auth_user_id", return_value=71),
            patch("app.routers.auth._ensure_role_profile_link", return_value=None),
            patch("app.routers.auth.create_session_tokens", return_value=session_tokens),
            patch("app.routers.auth.mirror_event", return_value=None),
        ):
            result = auth.login_student_with_password(
                schemas.LoginPasswordRequest(email="student.ready@gmail.com", password="Student@123"),
                response=Response(),
                request=_request("/auth/student/login"),
                sql_db=SimpleNamespace(),
            )

        self.assertEqual(result.access_token, "access-token")
        self.assertEqual(result.user.email, "student.ready@gmail.com")
        self.assertFalse(result.user.password_setup_required)

    def test_password_bootstrap_allows_faculty_legacy_accounts(self):
        mongo = _FakeMongo()
        mongo["auth_users"].insert_one(
            {
                "id": 90,
                "email": "legacy.faculty@gmail.com",
                "password_hash": hash_password("temporary-placeholder"),
                "role": models.UserRole.FACULTY.value,
                "faculty_id": 18,
                "is_active": True,
                "password_setup_required": True,
                "created_at": datetime.utcnow(),
            }
        )
        sql_user = SimpleNamespace(password_hash="")
        sql_db = SimpleNamespace(
            get=lambda _model, _id: sql_user,
            commit=lambda: None,
            rollback=lambda: None,
        )

        with (
            patch("app.routers.auth._mongo_db_or_503", return_value=mongo),
            patch("app.routers.auth.mirror_event", return_value=None),
        ):
            result = auth.bootstrap_account_password(
                schemas.PasswordBootstrapRequest(new_password="Faculty@456"),
                current_user=CurrentUser(
                    id=90,
                    email="legacy.faculty@gmail.com",
                    role=models.UserRole.FACULTY,
                    student_id=None,
                    faculty_id=18,
                    alternate_email=None,
                    primary_login_verified=True,
                    is_active=True,
                ),
                sql_db=sql_db,
            )

        self.assertIn("Password setup complete", result.message)
        user = mongo["auth_users"].find_one({"id": 90})
        self.assertFalse(user["password_setup_required"])
        self.assertTrue(user["password_updated_at"])

    def test_verify_login_otp_blocks_inactive_account(self):
        mongo = _FakeMongo()
        otp_hash, otp_salt = hash_otp("123456")
        mongo["auth_users"].insert_one(
            {
                "id": 11,
                "email": "admin@gmail.com",
                "password_hash": hash_password("Admin@123"),
                "role": models.UserRole.ADMIN.value,
                "student_id": None,
                "faculty_id": None,
                "is_active": False,
                "mfa_enabled": False,
                "created_at": datetime.utcnow(),
            }
        )
        mongo["auth_otps"].insert_one(
            {
                "id": 21,
                "user_id": 11,
                "purpose": "login",
                "otp_hash": otp_hash,
                "otp_salt": otp_salt,
                "attempts_count": 0,
                "expires_at": datetime.utcnow() + timedelta(minutes=10),
                "used_at": None,
                "created_at": datetime.utcnow(),
            }
        )

        with (
            patch("app.routers.auth._mongo_db_or_503", return_value=mongo),
            patch("app.routers.auth._ensure_auth_user_id", return_value=11),
            patch("app.routers.auth._ensure_role_profile_link", return_value=None),
            patch("app.routers.auth.enforce_rate_limit", return_value=None),
        ):
            with self.assertRaises(HTTPException) as ctx:
                auth.verify_login_otp(
                    schemas.VerifyOTPRequest(email="admin@gmail.com", otp_code="123456"),
                    response=Response(),
                    request=_request("/auth/login/verify-otp"),
                    sql_db=SimpleNamespace(),
                )

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail, "User account is inactive")

    def test_verify_login_otp_accepts_formatted_otp(self):
        mongo = _FakeMongo()
        otp_hash, otp_salt = hash_otp("123456")
        mongo["auth_users"].insert_one(
            {
                "id": 12,
                "email": "owner@gmail.com",
                "password_hash": hash_password("Owner@123"),
                "role": models.UserRole.OWNER.value,
                "student_id": None,
                "faculty_id": None,
                "is_active": True,
                "mfa_enabled": False,
                "created_at": datetime.utcnow(),
            }
        )
        mongo["auth_otps"].insert_one(
            {
                "id": 22,
                "user_id": 12,
                "purpose": "login",
                "otp_hash": otp_hash,
                "otp_salt": otp_salt,
                "attempts_count": 0,
                "expires_at": datetime.utcnow() + timedelta(minutes=10),
                "used_at": None,
                "created_at": datetime.utcnow(),
            }
        )

        with (
            patch("app.routers.auth._mongo_db_or_503", return_value=mongo),
            patch("app.routers.auth._ensure_auth_user_id", return_value=12),
            patch("app.routers.auth._ensure_role_profile_link", return_value=None),
            patch("app.routers.auth.enforce_rate_limit", return_value=None),
            patch("app.routers.auth.mirror_event", return_value=None),
            patch("app.routers.auth._set_auth_cookies", return_value=None),
            patch(
                "app.routers.auth.create_session_tokens",
                return_value={
                    "access_token": "access-token",
                    "access_expires_at": datetime.utcnow() + timedelta(minutes=15),
                    "refresh_token": "refresh-token",
                    "refresh_expires_at": datetime.utcnow() + timedelta(days=14),
                },
            ),
        ):
            result = auth.verify_login_otp(
                schemas.VerifyOTPRequest(email="owner@gmail.com", otp_code="123 456"),
                response=Response(),
                request=_request("/auth/login/verify-otp"),
                sql_db=SimpleNamespace(),
            )

        self.assertEqual(result.access_token, "access-token")
        otp_row = mongo["auth_otps"].find_one({"id": 22})
        self.assertIsNotNone(otp_row["used_at"])

    def test_verify_login_otp_preserves_password_bootstrap_requirement_for_legacy_student(self):
        mongo = _FakeMongo()
        otp_hash, otp_salt = hash_otp("123456")
        mongo["auth_users"].insert_one(
            {
                "id": 14,
                "email": "legacy.student@gmail.com",
                "password_hash": hash_password("temporary-placeholder"),
                "role": models.UserRole.STUDENT.value,
                "student_id": 91,
                "faculty_id": None,
                "is_active": True,
                "password_setup_required": True,
                "mfa_enabled": False,
                "created_at": datetime.utcnow(),
            }
        )
        mongo["students"].insert_one(
            {
                "id": 91,
                "name": "LEGACY STUDENT",
                "email": "legacy.student@gmail.com",
                "registration_number": "12200091",
                "section": "K23AA",
                "department": "CSE",
                "semester": 4,
                "created_at": datetime.utcnow(),
            }
        )
        mongo["auth_otps"].insert_one(
            {
                "id": 32,
                "user_id": 14,
                "purpose": "login",
                "otp_hash": otp_hash,
                "otp_salt": otp_salt,
                "attempts_count": 0,
                "expires_at": datetime.utcnow() + timedelta(minutes=10),
                "used_at": None,
                "created_at": datetime.utcnow(),
            }
        )

        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)
        sql_db = SessionLocal()
        sql_db.add(
            models.AuthUser(
                id=14,
                email="legacy.student@gmail.com",
                password_hash=hash_password("temporary-placeholder"),
                role=models.UserRole.STUDENT,
                student_id=91,
                is_active=True,
                created_at=datetime.utcnow(),
            )
        )
        sql_db.commit()

        try:
            with (
                patch("app.routers.auth._mongo_db_or_503", return_value=mongo),
                patch("app.routers.auth._ensure_auth_user_id", return_value=14),
                patch("app.routers.auth.enforce_rate_limit", return_value=None),
                patch("app.routers.auth.mirror_event", return_value=None),
                patch("app.routers.auth._set_auth_cookies", return_value=None),
                patch(
                    "app.routers.auth.create_session_tokens",
                    return_value={
                        "access_token": "access-token",
                        "access_expires_at": datetime.utcnow() + timedelta(minutes=15),
                        "refresh_token": "refresh-token",
                        "refresh_expires_at": datetime.utcnow() + timedelta(days=14),
                    },
                ),
            ):
                result = auth.verify_login_otp(
                    schemas.VerifyOTPRequest(email="legacy.student@gmail.com", otp_code="123456"),
                    response=Response(),
                    request=_request("/auth/login/verify-otp"),
                    sql_db=sql_db,
                )
        finally:
            sql_db.close()
            engine.dispose()

        self.assertTrue(result.user.password_setup_required)
        self.assertEqual(result.user.student_id, 91)

    def test_verify_login_otp_rejects_consume_race(self):
        mongo = _FakeMongo(auth_otps_collection=_ConsumeConflictCollection())
        otp_hash, otp_salt = hash_otp("123456")
        mongo["auth_users"].insert_one(
            {
                "id": 13,
                "email": "faculty@gmail.com",
                "password_hash": hash_password("Faculty@123"),
                "role": models.UserRole.FACULTY.value,
                "student_id": None,
                "faculty_id": None,
                "is_active": True,
                "mfa_enabled": False,
                "password_updated_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
            }
        )
        mongo["auth_otps"].insert_one(
            {
                "id": 31,
                "user_id": 13,
                "purpose": "login",
                "otp_hash": otp_hash,
                "otp_salt": otp_salt,
                "attempts_count": 0,
                "expires_at": datetime.utcnow() + timedelta(minutes=10),
                "used_at": None,
                "created_at": datetime.utcnow(),
            }
        )

        with (
            patch("app.routers.auth._mongo_db_or_503", return_value=mongo),
            patch("app.routers.auth._ensure_auth_user_id", return_value=13),
            patch("app.routers.auth._ensure_role_profile_link", return_value=None),
            patch("app.routers.auth.enforce_rate_limit", return_value=None),
        ):
            with self.assertRaises(HTTPException) as ctx:
                auth.verify_login_otp(
                    schemas.VerifyOTPRequest(email="faculty@gmail.com", otp_code="123456"),
                    response=Response(),
                    request=_request("/auth/login/verify-otp"),
                    sql_db=SimpleNamespace(),
                )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "OTP already used. Request a new OTP.")

    def test_verify_and_consume_mfa_code_accepts_spaced_backup_code(self):
        mongo = _FakeMongo()
        mongo["auth_users"].insert_one(
            {
                "id": 50,
                "email": "owner@gmail.com",
                "role": models.UserRole.OWNER.value,
                "mfa_totp_secret": None,
                "mfa_backup_code_hashes": [hash_backup_code("AB12CD34")],
            }
        )
        user_doc = mongo["auth_users"].find_one({"id": 50})

        accepted = auth._verify_and_consume_mfa_code(mongo, user_doc, "ab12 cd34")

        self.assertTrue(accepted)
        stored_user = mongo["auth_users"].find_one({"id": 50})
        self.assertEqual(stored_user["mfa_backup_code_hashes"], [])

    def test_mfa_status_returns_503_when_datastore_read_fails(self):
        current_user = CurrentUser(
            id=99,
            email="owner@gmail.com",
            role=models.UserRole.OWNER,
            student_id=None,
            faculty_id=None,
            alternate_email=None,
            primary_login_verified=True,
            is_active=True,
            mfa_enabled=True,
            mfa_authenticated=True,
        )
        mongo = {"auth_users": _RaisingCollection(find_one_exc=PyMongoError("read failed"))}

        with (
            patch("app.routers.auth._mongo_db_or_503", return_value=mongo),
            patch("app.routers.auth.invalidate_mongo_connection", return_value=None),
        ):
            with self.assertRaises(HTTPException) as ctx:
                auth.mfa_status(current_user=current_user)

        self.assertEqual(ctx.exception.status_code, 503)
        self.assertIn("temporarily unavailable", str(ctx.exception.detail))

    def test_mfa_activate_returns_503_when_datastore_write_fails(self):
        mongo = {
            "auth_users": _RaisingCollection(update_one_exc=PyMongoError("write failed")),
            "auth_sessions": _Collection(),
        }
        mongo["auth_users"].find_one = lambda *_args, **_kwargs: {
            "id": 77,
            "email": "owner@gmail.com",
            "role": models.UserRole.OWNER.value,
            "mfa_setup_secret": "SECRET",
            "mfa_setup_expires_at": datetime.utcnow() + timedelta(minutes=5),
            "mfa_setup_backup_code_hashes": [hash_backup_code("AB12CD34")],
        }
        current_user = CurrentUser(
            id=77,
            email="owner@gmail.com",
            role=models.UserRole.OWNER,
            student_id=None,
            faculty_id=None,
            alternate_email=None,
            primary_login_verified=True,
            is_active=True,
            mfa_enabled=False,
            mfa_authenticated=False,
        )

        with (
            patch("app.routers.auth._mongo_db_or_503", return_value=mongo),
            patch("app.routers.auth._match_user_totp", return_value=0),
            patch("app.routers.auth.invalidate_mongo_connection", return_value=None),
        ):
            with self.assertRaises(HTTPException) as ctx:
                auth.mfa_activate(
                    schemas.MFAActivateRequest(totp_code="123456"),
                    current_user=current_user,
                )

        self.assertEqual(ctx.exception.status_code, 503)
        self.assertIn("temporarily unavailable", str(ctx.exception.detail))


if __name__ == "__main__":
    unittest.main()
