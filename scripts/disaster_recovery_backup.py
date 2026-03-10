#!/usr/bin/env python3
import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _bootstrap import PROJECT_ROOT

from app.database import POSTGRES_ADMIN_LIBPQ_URL, SQLALCHEMY_DATABASE_URL, postgres_libpq_url  # noqa: E402
from app.mongo import get_mongo_db, init_mongo, next_sequence  # noqa: E402
from app.postgres_backup import create_postgresql_backup_artifact  # noqa: E402


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(val) for key, val in value.items()}
    return str(value)


def _sqlite_path() -> Path | None:
    if not SQLALCHEMY_DATABASE_URL.startswith("sqlite:///"):
        return None
    raw = SQLALCHEMY_DATABASE_URL[len("sqlite:///") :]
    path = Path(raw)
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    return path


def _is_postgres_url() -> bool:
    return SQLALCHEMY_DATABASE_URL.startswith("postgresql")


def _pg_dump_url() -> str:
    return str(POSTGRES_ADMIN_LIBPQ_URL or postgres_libpq_url(SQLALCHEMY_DATABASE_URL) or SQLALCHEMY_DATABASE_URL)


def _backup_relational_artifact(out_dir: Path, manifest: dict[str, Any]) -> None:
    sqlite_path = _sqlite_path()
    if sqlite_path and sqlite_path.exists():
        sqlite_dest = out_dir / sqlite_path.name
        shutil.copy2(sqlite_path, sqlite_dest)
        manifest["artifacts"]["relational:sqlite"] = {
            "backend": "sqlite",
            "path": str(sqlite_dest),
            "size_bytes": sqlite_dest.stat().st_size,
            "sha256": hashlib.sha256(sqlite_dest.read_bytes()).hexdigest(),
        }
        return

    if _is_postgres_url():
        manifest["artifacts"]["relational:postgresql"] = create_postgresql_backup_artifact(out_dir, _pg_dump_url())
        return

    raise RuntimeError("No supported relational database backend configured for DR backup")


def _mongo_backup_collections() -> list[str]:
    return [
        "auth_users",
        "auth_sessions",
        "auth_token_revocations",
        "auth_role_invites",
        "auth_otps",
        "auth_otp_delivery",
        "auth_password_resets",
        "event_stream",
        "admin_audit_logs",
        "attendance_records",
        "food_orders",
        "food_order_audit",
        "makeup_classes",
        "remedial_attendance",
        "compliance_deletion_requests",
        "compliance_retention_runs",
        "compliance_evidence_packages",
        "security_key_rotation_runs",
        "dr_restore_drills",
        "dr_backups",
        "scim_groups",
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Create DR backup snapshot for relational DB + MongoDB")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "backups"), help="Backup root directory")
    parser.add_argument("--label", default="", help="Optional backup label suffix")
    parser.add_argument("--skip-mongo", action="store_true", help="Skip Mongo export")
    parser.add_argument("--created-by", default="automation", help="Audit label for persisted DR evidence")
    args = parser.parse_args()

    run_ts = _utc_now()
    run_id = run_ts.strftime("%Y%m%dT%H%M%SZ")
    if args.label:
        safe_label = "".join(ch for ch in args.label if ch.isalnum() or ch in {"-", "_"}).strip("-_")
        if safe_label:
            run_id = f"{run_id}-{safe_label[:40]}"

    out_root = Path(args.output_dir).resolve()
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=False)

    manifest: dict[str, Any] = {"backup_id": run_id, "created_at": run_ts.isoformat(), "artifacts": {}}
    _backup_relational_artifact(out_dir, manifest)

    mongo_db = None
    if not args.skip_mongo:
        init_mongo(force=True)
        mongo_db = get_mongo_db(required=False)
        if mongo_db is not None:
            mongo_dir = out_dir / "mongo"
            mongo_dir.mkdir(parents=True, exist_ok=True)
            collections = _mongo_backup_collections()
            for name in collections:
                rows = list(mongo_db[name].find({}))
                file_path = mongo_dir / f"{name}.jsonl"
                lines = [json.dumps(_jsonable(row), separators=(",", ":")) for row in rows]
                file_path.write_text("\n".join(lines), encoding="utf-8")
                manifest["artifacts"][f"mongo:{name}"] = {
                    "path": str(file_path),
                    "count": len(rows),
                    "sha256": hashlib.sha256(file_path.read_bytes()).hexdigest(),
                }

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if mongo_db is not None:
        mongo_db["dr_backups"].insert_one(
            {
                "id": next_sequence("dr_backups"),
                "backup_id": run_id,
                "created_by_user_id": None,
                "created_by_email": str(args.created_by or "automation"),
                "created_at": run_ts,
                "location": str(out_dir),
                "manifest": manifest,
            }
        )
    print(json.dumps({"backup_id": run_id, "output": str(out_dir), "manifest": str(manifest_path)}, indent=2))


if __name__ == "__main__":
    main()
