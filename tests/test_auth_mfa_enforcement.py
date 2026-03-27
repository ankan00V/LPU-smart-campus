import os
import unittest

from fastapi import HTTPException

from app import models
from app.auth_utils import CurrentUser, require_roles


class AuthMFAEnforcementTests(unittest.TestCase):
    def setUp(self):
        self.prev = os.getenv("APP_ENFORCE_PRIVILEGED_MFA")
        os.environ["APP_ENFORCE_PRIVILEGED_MFA"] = "true"

    def tearDown(self):
        if self.prev is None:
            os.environ.pop("APP_ENFORCE_PRIVILEGED_MFA", None)
        else:
            os.environ["APP_ENFORCE_PRIVILEGED_MFA"] = self.prev

    def test_admin_without_mfa_is_blocked(self):
        dep = require_roles(models.UserRole.ADMIN)
        user = CurrentUser(
            id=1,
            email="admin@gmail.com",
            role=models.UserRole.ADMIN,
            student_id=None,
            faculty_id=None,
            alternate_email=None,
            primary_login_verified=True,
            is_active=True,
            mfa_enabled=False,
            mfa_authenticated=False,
        )
        with self.assertRaises(HTTPException) as ctx:
            dep(user)
        self.assertEqual(ctx.exception.status_code, 428)
        self.assertIn("admin/faculty/owner", str(ctx.exception.detail))

    def test_admin_with_mfa_passes(self):
        dep = require_roles(models.UserRole.ADMIN)
        user = CurrentUser(
            id=2,
            email="admin2@gmail.com",
            role=models.UserRole.ADMIN,
            student_id=None,
            faculty_id=None,
            alternate_email=None,
            primary_login_verified=True,
            is_active=True,
            mfa_enabled=True,
            mfa_authenticated=True,
        )
        resolved = dep(user)
        self.assertEqual(resolved.id, 2)

    def test_owner_without_mfa_is_blocked(self):
        dep = require_roles(models.UserRole.OWNER)
        user = CurrentUser(
            id=3,
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
        with self.assertRaises(HTTPException) as ctx:
            dep(user)
        self.assertEqual(ctx.exception.status_code, 428)
        self.assertIn("admin/faculty/owner", str(ctx.exception.detail))


if __name__ == "__main__":
    unittest.main()
