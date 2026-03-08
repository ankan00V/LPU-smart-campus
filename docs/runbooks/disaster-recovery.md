# Disaster Recovery Runbook

## Objectives

- `RPO <= 15 minutes`
- `RTO <= 60 minutes`

## Backup Execution

### API Trigger

1. Authenticate as admin.
2. Call `POST /enterprise/dr/backup`.
3. Save returned `backup_id`, `location`, and `manifest_path`.

### CLI Trigger

```bash
PYTHONPATH=. .venv/bin/python scripts/disaster_recovery_backup.py --label scheduled
```

## Restore Drill Execution

### API Trigger

1. Call `POST /enterprise/dr/restore-drill` (optional body: `{"backup_id":"..."}`).
2. Verify:
   - `target_met=true`
   - `manifest_integrity_ok=true`
3. Track recent drill history:
   - `GET /enterprise/dr/restore-drills?limit=10`

### CLI Trigger

```bash
PYTHONPATH=. .venv/bin/python scripts/disaster_recovery_restore_drill.py --backups-dir backups
```

## Offsite Replication

Replicate the most recent backup folder to offsite storage after each successful backup run:

```bash
PYTHONPATH=. .venv/bin/python scripts/dr_replicate_offsite.py \
  --backups-dir backups \
  --offsite-dir /mnt/offsite-campus-backups
```

## Verification Checklist

- Manifest exists and checksums are present.
- Manifest integrity check reports `missing=0` and `mismatched=0`.
- SQLite artifact can be restored and queried.
- Mongo export files exist for critical collections.
- Drill report recorded with measured `rto_seconds`.

## Escalation

- If restore drill fails, declare incident and freeze production deploys until corrective action completes.
