import unittest
from datetime import datetime, timedelta

from fastapi import HTTPException

from app.auth_utils import password_expired, password_expires_at
from app.routers.auth import _validate_password_strength


class AuthPasswordPolicyTests(unittest.TestCase):
    def test_rejects_password_without_special_character(self):
        with self.assertRaises(HTTPException) as ctx:
            _validate_password_strength("Password123")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_rejects_password_without_number(self):
        with self.assertRaises(HTTPException) as ctx:
            _validate_password_strength("Password@abc")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_accepts_password_with_policy_requirements(self):
        try:
            _validate_password_strength("Strong@123")
        except HTTPException as exc:  # pragma: no cover - should not happen
            self.fail(f"Password policy unexpectedly rejected valid password: {exc.detail}")

    def test_password_expiry_uses_90_day_policy(self):
        updated_at = datetime.utcnow() - timedelta(days=91)
        user = {
            "password_hash": "salt$digest",
            "password_updated_at": updated_at,
            "created_at": datetime.utcnow(),
        }

        self.assertTrue(password_expired(user))
        self.assertEqual(password_expires_at(user), updated_at + timedelta(days=90))

    def test_password_setup_accounts_are_not_expired(self):
        user = {
            "password_hash": "",
            "password_setup_required": True,
            "created_at": datetime.utcnow() - timedelta(days=365),
        }

        self.assertFalse(password_expired(user))


if __name__ == "__main__":
    unittest.main()
