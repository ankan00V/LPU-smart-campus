import unittest

from fastapi import HTTPException

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


if __name__ == "__main__":
    unittest.main()
