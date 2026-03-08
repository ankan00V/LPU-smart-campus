import unittest

from fastapi import HTTPException

from app import models
from app.routers.auth import _validate_role_email


class AuthAdminRoleTests(unittest.TestCase):
    def test_admin_role_accepts_gmail_signup_email(self):
        try:
            _validate_role_email("admin.user@gmail.com", models.UserRole.ADMIN)
        except HTTPException as exc:  # pragma: no cover - should not happen
            self.fail(f"Admin gmail email should be allowed, got: {exc.detail}")

    def test_admin_role_rejects_non_gmail_signup_email(self):
        with self.assertRaises(HTTPException) as ctx:
            _validate_role_email("admin.user@example.com", models.UserRole.ADMIN)
        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
