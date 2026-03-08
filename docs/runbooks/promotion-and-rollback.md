# Promotion And Rollback Runbook

## Promotion Flow

1. `dev -> staging`
2. `staging -> production` (manual approval gate)

## Promotion Gates

- Unit/integration tests pass.
- Security checks pass.
- `GET /enterprise/performance/sla` shows target compliance in staging.
- `GET /enterprise/performance/capacity-plan` confirms planned headroom.
- Latest key rotation run exists (`GET /enterprise/security/encryption/rotation-runs`).
- Latest DR backup exists and latest restore drill is successful with integrity checks:
  - `GET /enterprise/dr/backups?limit=1`
  - `GET /enterprise/dr/restore-drills?limit=1` (`target_met=true`, `manifest_integrity_ok=true`)
- Release gate script passes:
  - `PYTHONPATH=. .venv/bin/python scripts/release_readiness_check.py --base-url http://127.0.0.1:8000 --admin-token "<token>"`

## Production Promotion Checklist

1. Generate deployment note with schema changes.
2. Run backup: `POST /enterprise/dr/backup`.
3. Run key rotation evidence step:
   - `PYTHONPATH=. .venv/bin/python scripts/run_field_key_rotation.py --dry-run`
4. Generate evidence package for current audit window:
   - `POST /enterprise/compliance/evidence/package`
5. Deploy application artifact.
6. Validate health:
   - `GET /`
   - `GET /enterprise/controls/status`
7. Validate core flows: auth, attendance, food checkout, remedial.

## Rollback Playbook

1. Trigger application rollback to previous artifact.
2. Revoke problematic sessions if auth regression occurred (`/auth/logout` path + session revocations).
3. If data migration impacts state:
   - Restore from latest known-good backup snapshot.
   - Re-run restore validation checks.
4. Publish incident report with root cause and action items.

## Required Evidence

- Backup ID before release.
- Evidence package ID/archive path.
- Rollout timestamps.
- Validation results.
- Rollback proof if rollback executed.
