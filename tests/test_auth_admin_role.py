import unittest
import os
from contextlib import contextmanager

from fastapi import HTTPException

from app import models
from app.routers.auth import _validate_alternate_email, _validate_role_email


@contextmanager
def _temporary_env(**updates):
    previous = {key: os.getenv(key) for key in updates}
    try:
        for key, value in updates.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class AuthAdminRoleTests(unittest.TestCase):
    def test_admin_role_accepts_official_signup_email_by_default(self):
        try:
            _validate_role_email("admin.user@lpu.in", models.UserRole.ADMIN)
        except HTTPException as exc:  # pragma: no cover - should not happen
            self.fail(f"Official email should be allowed, got: {exc.detail}")

    def test_admin_role_restrictions_can_be_configured_via_suffix_env(self):
        with self.subTest("allowed"):
            try:
                _validate_role_email("admin.user@lpu.in", models.UserRole.ADMIN)
            except HTTPException as exc:  # pragma: no cover - should not happen
                self.fail(f"Institute email should be allowed by default, got: {exc.detail}")

        with self.subTest("blocked_when_configured"):
            with _temporary_env(AUTH_EMAIL_SUFFIXES="@lpu.in"):
                with self.assertRaises(HTTPException):
                    _validate_role_email("admin.user@example.com", models.UserRole.ADMIN)

    def test_primary_login_rejects_configured_personal_mail_domains(self):
        with _temporary_env(AUTH_PRIMARY_EMAIL_BLOCKED_DOMAINS="gmail.com,outlook.com"):
            with self.assertRaises(HTTPException) as ctx:
                _validate_role_email("student.user@gmail.com", models.UserRole.STUDENT)

        self.assertIn("official university or company email", ctx.exception.detail)

    def test_primary_login_personal_mail_is_allowed_only_for_legacy_migration(self):
        with _temporary_env(AUTH_PRIMARY_EMAIL_BLOCKED_DOMAINS="gmail.com,outlook.com"):
            try:
                _validate_role_email(
                    "old.student@gmail.com",
                    models.UserRole.STUDENT,
                    allow_legacy_primary=True,
                )
            except HTTPException as exc:  # pragma: no cover - should not happen
                self.fail(f"Legacy migration login should allow old personal primary mail, got: {exc.detail}")

    def test_alternate_email_allows_personal_mail_even_when_primary_blocks_it(self):
        with _temporary_env(
            AUTH_PRIMARY_EMAIL_BLOCKED_DOMAINS="gmail.com,outlook.com",
            AUTH_EMAIL_SUFFIXES="@lpu.in",
        ):
            self.assertEqual(_validate_alternate_email(" Person@Gmail.COM "), "person@gmail.com")


if __name__ == "__main__":
    unittest.main()
