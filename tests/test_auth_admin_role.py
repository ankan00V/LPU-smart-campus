import unittest

from fastapi import HTTPException

from app import models
from app.routers.auth import _validate_role_email


class AuthAdminRoleTests(unittest.TestCase):
    def test_admin_role_accepts_institute_signup_email_by_default(self):
        try:
            _validate_role_email("admin.user@lpu.in", models.UserRole.ADMIN)
        except HTTPException as exc:  # pragma: no cover - should not happen
            self.fail(f"Admin gmail email should be allowed, got: {exc.detail}")

    def test_admin_role_restrictions_can_be_configured_via_suffix_env(self):
        with self.subTest("allowed"):
            try:
                _validate_role_email("admin.user@lpu.in", models.UserRole.ADMIN)
            except HTTPException as exc:  # pragma: no cover - should not happen
                self.fail(f"Institute email should be allowed by default, got: {exc.detail}")

        with self.subTest("blocked_when_configured"):
            import os

            prev = os.getenv("AUTH_EMAIL_SUFFIXES")
            os.environ["AUTH_EMAIL_SUFFIXES"] = "@lpu.in"
            try:
                with self.assertRaises(HTTPException):
                    _validate_role_email("admin.user@example.com", models.UserRole.ADMIN)
            finally:
                if prev is None:
                    os.environ.pop("AUTH_EMAIL_SUFFIXES", None)
                else:
                    os.environ["AUTH_EMAIL_SUFFIXES"] = prev


if __name__ == "__main__":
    unittest.main()
