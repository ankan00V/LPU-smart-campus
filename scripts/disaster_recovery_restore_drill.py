#!/usr/bin/env python3
import argparse
import hashlib
import json
import sys
import shutil
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _bootstrap import PROJECT_ROOT
from app.mongo import get_mongo_db, init_mongo, next_sequence
from app.postgres_backup import validate_postgresql_backup_artifact


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _latest_backup(root: Path) -> Path | None:
    if not root.exists():
        return None
    candidates = sorted([p for p in root.iterdir() if p.is_dir()], reverse=True)
    return candidates[0] if candidates else None


def _sqlite_check(sqlite_path: Path) -> dict[str, Any]:
    temp_path = sqlite_path.parent / f".drill-{int(time.time())}-{sqlite_path.name}"
    shutil.copy2(sqlite_path, temp_path)
    conn = sqlite3.connect(str(temp_path))
    try:
        table_count = int(conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0])
    finally:
        conn.close()
        temp_path.unlink(missing_ok=True)
    return {"restored": True, "table_count": table_count}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_artifact_path(backup: Path, raw_path: Any) -> Path | None:
    token = str(raw_path or "").strip()
    if not token:
        return None
    path = Path(token)
    if path.is_absolute():
        if path.exists():
            return path
        direct_fallback = (backup / path.name).resolve()
        if direct_fallback.exists():
            return direct_fallback
        mongo_fallback = (backup / "mongo" / path.name).resolve()
        if mongo_fallback.exists():
            return mongo_fallback
        matches = list(backup.rglob(path.name))
        if matches:
            return matches[0]
        return path
    resolved = (backup / token).resolve()
    if resolved.exists():
        return resolved
    direct_fallback = (backup / Path(token).name).resolve()
    if direct_fallback.exists():
        return direct_fallback
    return resolved


def _verify_manifest_artifacts(backup: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        return {
            "total_checked": 0,
            "verified": 0,
            "missing": 0,
            "mismatched": 0,
            "errors": ["manifest.artifacts missing or invalid"],
        }

    checked = 0
    verified = 0
    missing = 0
    mismatched = 0
    errors: list[str] = []
    for artifact_name, artifact in artifacts.items():
        if not isinstance(artifact, dict):
            continue
        expected_sha = str(artifact.get("sha256") or "").strip().lower()
        artifact_path = _resolve_artifact_path(backup, artifact.get("path"))
        if not expected_sha or artifact_path is None:
            continue
        checked += 1
        if not artifact_path.exists():
            missing += 1
            errors.append(f"{artifact_name}: missing artifact {artifact_path}")
            continue
        actual_sha = _sha256_file(artifact_path).lower()
        if actual_sha != expected_sha:
            mismatched += 1
            errors.append(f"{artifact_name}: checksum mismatch")
            continue
        verified += 1
    return {
        "total_checked": int(checked),
        "verified": int(verified),
        "missing": int(missing),
        "mismatched": int(mismatched),
        "errors": errors[:20],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run restore drill from a backup snapshot directory")
    parser.add_argument("--backups-dir", default=str(PROJECT_ROOT / "backups"), help="Backup root directory")
    parser.add_argument("--backup-id", default="", help="Specific backup folder name")
    parser.add_argument("--executed-by", default="automation", help="Audit label for persisted DR evidence")
    args = parser.parse_args()

    root = Path(args.backups_dir).resolve()
    backup = (root / args.backup_id).resolve() if args.backup_id else _latest_backup(root)
    if backup is None or not backup.exists():
        raise SystemExit("No backup found to run restore drill")

    started = time.perf_counter()
    manifest_path = backup / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit("Backup manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_integrity = _verify_manifest_artifacts(backup, manifest)
    manifest_integrity_ok = (
        int(manifest_integrity.get("total_checked", 0)) > 0
        and int(manifest_integrity.get("missing", 0)) == 0
        and int(manifest_integrity.get("mismatched", 0)) == 0
    )

    relational_result = {"backend": "unknown", "validated": False}
    sqlite_files = [p for p in backup.glob("*.db")]
    if sqlite_files:
        relational_result = {"backend": "sqlite", **_sqlite_check(sqlite_files[0])}
    else:
        relational_result = validate_postgresql_backup_artifact(backup)

    mongo_files = list((backup / "mongo").glob("*.jsonl")) if (backup / "mongo").exists() else []
    elapsed = round(time.perf_counter() - started, 3)

    out = {
        "backup_id": backup.name,
        "backup_path": str(backup),
        "manifest_ok": True,
        "manifest_integrity": manifest_integrity,
        "manifest_integrity_ok": manifest_integrity_ok,
        "relational": relational_result,
        "mongo_files": len(mongo_files),
        "rto_seconds": elapsed,
        "target_rto_seconds": 3600,
        "target_met": elapsed <= 3600 and bool(relational_result.get("validated") or relational_result.get("restored")) and manifest_integrity_ok,
        "artifact_count": len((manifest.get("artifacts") or {})),
    }
    if init_mongo(force=True):
        mongo_db = get_mongo_db(required=False)
        if mongo_db is not None:
            mongo_db["dr_restore_drills"].insert_one(
                {
                    "id": next_sequence("dr_restore_drills"),
                    "backup_id": backup.name,
                    "started_at": _utc_now(),
                    "executed_by_user_id": None,
                    "executed_by_email": str(args.executed_by or "automation"),
                    "relational_checks": out["relational"],
                    "manifest_exists": bool(manifest_path.exists()),
                    "manifest_integrity": out["manifest_integrity"],
                    "manifest_integrity_ok": bool(out["manifest_integrity_ok"]),
                    "mongo_artifacts_present": bool(mongo_files),
                    "rto_seconds": out["rto_seconds"],
                    "target_rto_seconds": out["target_rto_seconds"],
                    "target_met": bool(out["target_met"]),
                }
            )
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
