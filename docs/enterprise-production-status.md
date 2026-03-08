# Enterprise Production Status

Last updated: 2026-03-04

## Requirement Matrix

1. SSO (OIDC/SAML), SCIM provisioning, MFA for admin/faculty
   - Implemented:
     - `POST /enterprise/sso/oidc/exchange`
     - `POST /enterprise/sso/saml/acs` (signed assertion required)
     - SCIM user provisioning endpoints under `/enterprise/scim/v2/Users`
     - Admin/faculty MFA enforcement in `require_roles(...)`
     - MFA setup/activate/backup code rotation under `/auth/mfa/*`
   - Remaining operational work:
     - Wire at least one real OIDC IdP and one SAML IdP in staging/production secrets.
     - Validate SCIM connector from the enterprise IdP against production policy mappings.

2. Field-level encryption for PII, key rotation, secrets manager integration
   - Implemented:
     - Field encryption service (`app/enterprise_controls.py`) with production required-mode.
     - Rotation API (`POST /enterprise/security/encryption/rotate`) + evidence list API.
     - Rotation automation script (`scripts/run_field_key_rotation.py`).
     - Production startup/validation blocks dev placeholders and weak secret values.
     - Secrets provider abstraction with `file`/`aws_secrets_manager`.
     - Rotation logic hardened for canonical/legacy AAD handling and plaintext migration.
   - Remaining operational work:
     - Populate production keyring and rotate keys on a scheduled cadence.
     - Store secrets in managed provider and remove plaintext runtime env injection.

3. Compliance-ready audit exports, retention and deletion workflows
   - Implemented:
     - Audit export endpoint (`POST /enterprise/compliance/audit-export`).
     - Evidence package endpoint (`POST /enterprise/compliance/evidence/package`).
     - Retention execution (`POST /enterprise/compliance/retention/run`).
     - Deletion request lifecycle with dual-control and legal hold.
     - Evidence packaging script (`scripts/package_compliance_evidence.py`).
   - Remaining operational work:
     - Schedule retention/evidence jobs and archive bundles in immutable storage.

4. Disaster recovery: backups, restore drills, multi-env promotion flow, rollback playbooks
   - Implemented:
     - Backup API (`POST /enterprise/dr/backup`) + list API.
     - Restore drill API (`POST /enterprise/dr/restore-drill`) + list API.
     - Backup/restore CLI scripts.
     - Manifest checksum verification in restore drills.
     - Promotion/rollback runbook and release gate workflow.
   - Remaining operational work:
     - Execute recurring drills and retain proof of latest `target_met=true`.
     - Replicate backup artifacts to offsite/object storage on schedule.

5. Performance SLAs: p95 targets, load tests, capacity planning
   - Implemented:
     - Route latency capture middleware and SLA snapshot API.
     - Capacity planning API + autoscale recommendation output.
     - Load test script (`scripts/sla_load_test.py`) and capacity report script.
     - Release readiness gate now validates SLA/capacity conditions.
   - Remaining operational work:
     - Run load tests in cadence (weekly/per-release) and track trend baselines.

## Definition Of Done For Production Cutover

All items below must be true at cutover time:

- Enterprise controls status endpoint returns secure settings (`file`/`aws_secrets_manager`, MFA enforced, SCIM enabled).
- Latest key rotation run evidence exists with zero failed records.
- Latest restore drill evidence exists with `target_met=true` and `manifest_integrity_ok=true`.
- SLA snapshot has non-zero sample set and no bucket target violations.
- Capacity plan has no SLA target violations and rollout approval is recorded.
