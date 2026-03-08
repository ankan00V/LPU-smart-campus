# Enterprise Rollout Roadmap

This roadmap tracks implementation status for production-grade controls in this repository.

Current status matrix: `docs/enterprise-production-status.md`

## Phase 0: Foundations (Completed)

- Added control blueprint: `docs/enterprise-production-controls.md`
- Added enterprise control router: `/enterprise/*`
- Added request latency capture middleware and SLA snapshots

## Phase 1: Identity And Access (Completed)

- Completed:
  - Admin/faculty MFA enforcement at authorization boundary (`require_roles`)
  - TOTP enrollment + activation + backup code rotation (`/auth/mfa/*`)
  - OIDC token exchange endpoint (`POST /enterprise/sso/oidc/exchange`)
  - SAML ACS endpoint (`POST /enterprise/sso/saml/acs`)
  - SCIM endpoints for provisioning/deprovisioning (`/enterprise/scim/v2/Users`)
  - Tenant-aware SSO guardrails (provider-tenant allow list + tenant-domain policy)
  - SCIM group-to-role mapping extensions (`SCIM_GROUP_ROLE_MAP_JSON`)

## Phase 2: Data Security (Completed)

- Completed:
  - Field encryption service (`app/enterprise_controls.py`)
  - Alternate email encryption at rest + hash-based uniqueness
  - Encryption rotation endpoint (`POST /enterprise/security/encryption/rotate`)
  - Encryption rotation run evidence (`GET /enterprise/security/encryption/rotation-runs`)
  - Scheduled key rotation utility (`scripts/run_field_key_rotation.py`)
  - Secrets provider abstraction (env/file/AWS Secrets Manager)
  - Mongo mirror PII coverage for `students`, `faculty`, and `auth_users`

## Phase 3: Compliance Operations (Completed)

- Completed:
  - Audit export bundle generation (`POST /enterprise/compliance/audit-export`)
  - Retention execution endpoint (`POST /enterprise/compliance/retention/run`)
  - Deletion request workflow (`/enterprise/compliance/deletion/requests*`)
  - Legal-hold update + dual-control approval/execution workflow
  - Evidence package endpoint (`POST /enterprise/compliance/evidence/package`)
  - Scheduled evidence script (`scripts/package_compliance_evidence.py`)

## Phase 4: DR And Release Safety (Completed)

- Completed:
  - API-level DR backup and restore drill endpoints
  - CLI backup and drill scripts:
    - `scripts/disaster_recovery_backup.py`
    - `scripts/disaster_recovery_restore_drill.py`
  - Offsite replication script (`scripts/dr_replicate_offsite.py`)
  - Release readiness gate script (`scripts/release_readiness_check.py`)
  - CI release gate workflow (`.github/workflows/enterprise-release-gates.yml`)

## Phase 5: SLA And Capacity (Completed)

- Completed:
  - Real-time latency capture middleware
  - SLA view endpoint (`GET /enterprise/performance/sla`)
  - Load test utility (`scripts/sla_load_test.py`)
  - Capacity plan endpoint (`GET /enterprise/performance/capacity-plan`)
  - Autoscale trigger recommendation from live capacity plan
  - Capacity report script (`scripts/capacity_plan_report.py`)

## Priority Execution Order

1. Stabilize MFA + SSO + SCIM in staging with one real IdP.
2. Enable field encryption required-mode in non-local environments.
3. Automate retention, deletion approvals, and audit exports.
4. Institutionalize backup + restore drill cadence.
5. Lock performance budgets into release gates.
