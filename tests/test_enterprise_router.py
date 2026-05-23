import os
import unittest

from fastapi import HTTPException

from app import models
from app.routers.enterprise import (
    _deletion_dual_control_required,
    _enforce_sso_tenant_constraints,
    _scim_role_from_groups,
)


class EnterpriseRouterControlsTests(unittest.TestCase):
    def setUp(self):
        self._original = {
            "SSO_PROVIDER_TENANTS_JSON": os.getenv("SSO_PROVIDER_TENANTS_JSON"),
            "SSO_TENANT_ALLOWED_DOMAINS_JSON": os.getenv("SSO_TENANT_ALLOWED_DOMAINS_JSON"),
            "SCIM_GROUP_ROLE_MAP_JSON": os.getenv("SCIM_GROUP_ROLE_MAP_JSON"),
            "APP_DELETION_DUAL_CONTROL_REQUIRED": os.getenv("APP_DELETION_DUAL_CONTROL_REQUIRED"),
        }

    def tearDown(self):
        for key, value in self._original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_tenant_constraint_allows_matching_domain(self):
        os.environ["SSO_PROVIDER_TENANTS_JSON"] = '{"OKTA":["acme"]}'
        os.environ["SSO_TENANT_ALLOWED_DOMAINS_JSON"] = '{"acme":["acme.edu"]}'
        tenant = _enforce_sso_tenant_constraints(provider="OKTA", tenant="acme", email="user@acme.edu")
        self.assertEqual(tenant, "acme")

    def test_tenant_constraint_blocks_non_matching_domain(self):
        os.environ["SSO_PROVIDER_TENANTS_JSON"] = '{"OKTA":["acme"]}'
        os.environ["SSO_TENANT_ALLOWED_DOMAINS_JSON"] = '{"acme":["acme.edu"]}'
        with self.assertRaises(HTTPException) as ctx:
            _enforce_sso_tenant_constraints(provider="OKTA", tenant="acme", email="user@other.edu")
        self.assertEqual(ctx.exception.status_code, 403)

    def test_scim_group_role_mapping(self):
        os.environ["SCIM_GROUP_ROLE_MAP_JSON"] = '{"cn=faculty":"faculty","cn=admins":"admin"}'
        role = _scim_role_from_groups(["cn=faculty"])
        self.assertEqual(role, models.UserRole.FACULTY)

    def test_deletion_dual_control_default_true(self):
        os.environ.pop("APP_DELETION_DUAL_CONTROL_REQUIRED", None)
        self.assertTrue(_deletion_dual_control_required())


if __name__ == "__main__":
    unittest.main()
