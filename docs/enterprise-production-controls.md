# Enterprise Controls To Reach Production-Grade

This document translates enterprise requirements into an implementation-ready plan for this repository (`FastAPI + SQLite + MongoDB + web UI`).

## Baseline Snapshot (as of 2026-03-04)

- Identity: OTP/password auth exists; no enterprise SSO federation, SCIM, or enforced admin/faculty MFA policy.
- Data protection: no explicit field-level envelope encryption for PII columns/documents; no documented key rotation flow.
- Compliance: audit logs exist for some domains, but no unified evidence export package for SOC2/ISO-style controls.
- Resilience: no documented backup policy, restore drills, promotion gates, or rollback runbooks.
- Performance: no formal p95 SLA definitions, repeatable load tests, or capacity headroom model.

## 1) Identity And Access Controls

### Target State

- SSO for workforce users (admin/faculty) via OIDC and SAML.
- SCIM 2.0 user/group provisioning and deprovisioning.
- MFA required for `admin` and `faculty` roles (step-up for sensitive operations).

### Implementation Plan

1. Add identity provider abstraction:
   - `IdentityProvider` interface with OIDC and SAML adapters.
   - New mapping store for external subject -> internal user (`issuer`, `subject`, `email`, `role`).
2. Add SSO endpoints:
   - OIDC authorize/callback, SAML ACS/metadata.
   - Session issuance aligned with existing auth cookie controls.
3. Add SCIM endpoints:
   - `/scim/v2/Users`, `/scim/v2/Groups`.
   - Provision, patch, deactivate, and hard-delete handling.
4. Add MFA policy engine:
   - TOTP/WebAuthn factor enrollment for admin/faculty.
   - Step-up check for admin-critical routes (bootstrap, destructive operations, audit export).
5. Add break-glass controls:
   - One emergency owner account excluded from IdP outage lockouts.
   - Dedicated alert on break-glass usage.

### Acceptance Criteria

- New faculty/admin users can be auto-provisioned from SCIM in under 2 minutes.
- Deprovisioned users lose app access within 5 minutes.
- 100% of admin/faculty sessions require MFA (policy enforced server-side).
- SSO login works with at least one OIDC and one SAML IdP in staging.

## 2) Data Protection (PII Encryption, Key Rotation, Secrets)

### Target State

- PII is encrypted at field level using envelope encryption with key versions.
- Application secrets come only from a secrets manager; `.env` used for local development only.
- Documented and tested key rotation with no data loss.

### Implementation Plan

1. Define data classification:
   - Tier-1 PII: phone, alternate email, profile photo/template data, payment identifiers.
   - Tier-2 sensitive ops data: attendance events linked to identity.
2. Build crypto service:
   - `encrypt_field(plaintext, key_id, aad)` / `decrypt_field(ciphertext, key_id, aad)`.
   - Store `key_version` and `ciphertext` per protected field.
3. Integrate with persistence layer:
   - Encrypt Tier-1 fields before SQL/Mongo write.
   - Decrypt only at API boundary for authorized roles.
4. Add key rotation job:
   - Re-encrypt data from `key_version=n` to `n+1`.
   - Idempotent batches with checkpointing and metrics.
5. Secrets manager integration:
   - Load runtime secrets from AWS Secrets Manager / GCP Secret Manager / Vault.
   - Add startup validation that production cannot boot with plaintext secrets.

### Acceptance Criteria

- Direct DB/Mongo reads show encrypted ciphertext for all Tier-1 PII fields.
- Key rotation can complete on staging data with 0 failed records.
- Rotation rollback plan validated (can decrypt with previous key version).
- Production startup fails fast if required secrets are missing.

## 3) Compliance-Ready Auditing, Retention, And Deletion

### Target State

- Unified audit event model across auth, attendance, remedial, food, and admin actions.
- Evidence exports for SOC2/ISO control narratives.
- Configurable retention and deletion workflows with legal-hold support.

### Implementation Plan

1. Standardize audit event schema:
   - `event_id`, `occurred_at`, `actor`, `action`, `resource`, `before`, `after`, `ip`, `request_id`, `result`.
2. Emit immutable audit logs:
   - Append-only write path.
   - Periodic export to WORM-capable object storage.
3. Build evidence export endpoints/job:
   - Auth changes, privileged actions, access attempts, backup/restore logs, deployment history.
   - Export format: timestamped ZIP with JSON and checksum manifest.
4. Add retention controls:
   - Policy by collection/table (`e.g., otp events 30d, security audit 1y+`).
   - Scheduled purge jobs with signed summary report.
5. Add deletion workflows:
   - Data subject delete request intake and status tracking.
   - Soft-delete + hard-delete stages with legal-hold override.

### Acceptance Criteria

- Evidence export for a selected time window can be generated in under 15 minutes.
- Every privileged admin action appears in audit logs with actor and request ID.
- Retention purge job produces verifiable reports and leaves legal-hold records untouched.
- Deletion request lifecycle has complete audit trace from request to finalization.

## 4) Disaster Recovery And Release Safety

### Target State

- Defined backup/restore policy with proven RPO/RTO.
- Staged promotion flow (`dev -> staging -> prod`) with migration checks.
- Rollback playbook for schema and application releases.

### Implementation Plan

1. Backup policy:
   - SQLite/Mongo logical backup every 15 minutes (or move primary SQL to managed Postgres).
   - Daily full backup + point-in-time backup store.
2. Restore automation:
   - One-command restore into isolated environment.
   - Automated integrity checks (row/doc counts, critical query checks).
3. Restore drills:
   - Monthly drill, quarterly game day.
   - Record measured RTO/RPO and remediation actions.
4. Multi-environment promotion:
   - CI gates: tests, schema migration dry-run, security scan, smoke tests.
   - Manual approval for production promotion.
5. Rollback playbooks:
   - App rollback (artifact pin).
   - DB rollback forward-fix strategy with reversible migrations where possible.

### Acceptance Criteria

- Demonstrated `RPO <= 15 minutes` and `RTO <= 60 minutes` in latest drill.
- Production deploys can be rolled back in under 15 minutes.
- Every release has changelog, migration plan, and rollback notes.

## 5) Performance SLAs, Load Testing, Capacity

### Target State

- Explicit p95 latency/error-rate SLOs per endpoint class.
- Repeatable load tests in CI/nightly.
- Capacity plan with headroom and scaling triggers.

### Implementation Plan

1. Define SLAs/SLOs:
   - Auth endpoints: p95 <= 250ms.
   - Attendance mark/review: p95 <= 400ms.
   - Food checkout/payment confirm: p95 <= 600ms.
   - Error budget: < 0.5% 5xx per month.
2. Instrumentation:
   - Add OpenTelemetry tracing + Prometheus metrics.
   - Publish RED metrics (rate, errors, duration) by route and role.
3. Load testing:
   - Build k6 or Locust scenarios for peak attendance windows and lunch rush.
   - Include mixed read/write plus failure injection.
4. Capacity planning:
   - Baseline throughput and CPU/memory/db utilization.
   - Define autoscale/manual scale thresholds and runbook actions.
5. Regression guardrails:
   - Fail release if p95 or error budget regresses beyond thresholds.

### Acceptance Criteria

- SLA dashboard is visible for all production routes.
- Weekly or per-release load test report is generated and archived.
- Capacity plan documents expected peak users, headroom %, and scale triggers.

## Suggested Rollout (90 Days)

1. Phase 1 (Weeks 1-3): Observability, SLA definitions, unified audit schema, backup policy.
2. Phase 2 (Weeks 4-6): SSO (OIDC), MFA enforcement, secrets manager integration.
3. Phase 3 (Weeks 7-9): SCIM provisioning, field-level encryption for Tier-1 PII, key rotation job.
4. Phase 4 (Weeks 10-12): Evidence exports, retention/deletion workflows, restore drill + rollback rehearsal.

## Definition Of Production-Grade (Enterprise)

All items below must be true:

- IAM: SSO + SCIM + MFA policies are enforced and tested.
- Data security: Tier-1 PII is encrypted with managed keys and rotation evidence.
- Compliance: audit and evidence exports satisfy internal SOC2/ISO control checks.
- Resilience: backup/restore drills demonstrate target RPO/RTO.
- Performance: p95 SLAs and error budgets are continuously measured and met.
