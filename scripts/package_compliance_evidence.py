#!/usr/bin/env python3
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from dotenv import load_dotenv

from app.mongo import get_mongo_db, init_mongo, next_sequence
from app.performance import snapshot_sla

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc).isoformat()
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(val) for key, val in value.items()}
    return str(value)


def _parse_dt(raw_value: str | None) -> datetime | None:
    raw = str(raw_value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = f"{raw[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _safe_label(raw_value: str | None) -> str:
    raw = str(raw_value or "").strip()
    if not raw:
        return ""
    return "".join(ch for ch in raw if ch.isalnum() or ch in {"-", "_"}).strip("-_")[:30]


def _default_collections() -> list[str]:
    return [
        "event_stream",
        "admin_audit_logs",
        "auth_users",
        "auth_sessions",
        "auth_token_revocations",
        "auth_otps",
        "auth_otp_delivery",
        "food_order_audit",
        "compliance_deletion_requests",
        "compliance_retention_runs",
        "compliance_evidence_packages",
        "security_key_rotation_runs",
        "dr_restore_drills",
        "dr_backups",
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate compliance evidence ZIP for audit windows")
    parser.add_argument("--start-at", default="", help="Window start ISO timestamp")
    parser.add_argument("--end-at", default="", help="Window end ISO timestamp")
    parser.add_argument("--label", default="", help="Optional safe label suffix")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / ".enterprise_exports"))
    parser.add_argument("--collections", default="", help="Comma-separated Mongo collections")
    parser.add_argument("--max-docs", type=int, default=100000)
    parser.add_argument("--sla-window-minutes", type=int, default=60)
    parser.add_argument("--created-by", default="automation")
    args = parser.parse_args()

    if not init_mongo(force=True):
        raise SystemExit("MongoDB is unavailable. Evidence package generation requires MongoDB.")
    mongo_db = get_mongo_db(required=True)

    start_dt = _parse_dt(args.start_at)
    end_dt = _parse_dt(args.end_at)
    if start_dt and end_dt and start_dt > end_dt:
        raise SystemExit("--start-at must be earlier than --end-at")

    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    label = _safe_label(args.label)
    suffix = f"-{label}" if label else ""
    archive_path = out_dir / f"evidence-package-{stamp}{suffix}.zip"

    collections = [item.strip() for item in args.collections.split(",") if item.strip()] or _default_collections()
    max_docs = max(1000, min(300_000, int(args.max_docs)))
    sla_window = max(5, min(360, int(args.sla_window_minutes)))

    latest_backup = mongo_db["dr_backups"].find_one({}, sort=[("created_at", -1)])
    latest_drill = mongo_db["dr_restore_drills"].find_one({}, sort=[("started_at", -1)])
    metadata = {
        "package_type": "soc2_iso_evidence_bundle",
        "created_by": str(args.created_by or "automation"),
        "latest_backup_id": latest_backup.get("backup_id") if isinstance(latest_backup, dict) else None,
        "latest_restore_drill_id": latest_drill.get("id") if isinstance(latest_drill, dict) else None,
        "latest_restore_target_met": bool(latest_drill.get("target_met")) if isinstance(latest_drill, dict) else None,
        "sla_snapshot": snapshot_sla(window_minutes=sla_window),
    }
    manifest: dict[str, Any] = {
        "generated_at": datetime.utcnow().isoformat(),
        "window": {"start_at": _jsonable(start_dt), "end_at": _jsonable(end_dt)},
        "collections": {},
        "metadata": _jsonable(metadata),
    }

    with ZipFile(archive_path, mode="w", compression=ZIP_DEFLATED) as zf:
        for collection_name in collections:
            query: dict[str, Any] = {}
            if start_dt or end_dt:
                created_filter: dict[str, Any] = {}
                if start_dt:
                    created_filter["$gte"] = start_dt
                if end_dt:
                    created_filter["$lte"] = end_dt
                query["created_at"] = created_filter
            rows = list(mongo_db[collection_name].find(query).sort("created_at", 1).limit(max_docs))
            lines = [json.dumps(_jsonable(row), separators=(",", ":")) for row in rows]
            body = "\n".join(lines).encode("utf-8")
            zf.writestr(f"{collection_name}.jsonl", body)
            manifest["collections"][collection_name] = {
                "count": len(rows),
                "sha256": hashlib.sha256(body).hexdigest(),
                "truncated": len(rows) >= max_docs,
            }
        zf.writestr("manifest.json", json.dumps(_jsonable(manifest), indent=2, sort_keys=True).encode("utf-8"))

    evidence_doc = {
        "id": next_sequence("compliance_evidence_packages"),
        "archive": str(archive_path),
        "window": {"start_at": start_dt, "end_at": end_dt},
        "collections": collections,
        "manifest": manifest,
        "created_by_user_id": None,
        "created_by_email": str(args.created_by or "automation"),
        "created_at": datetime.utcnow(),
    }
    mongo_db["compliance_evidence_packages"].insert_one(evidence_doc)

    print(
        json.dumps(
            {
                "evidence_package_id": int(evidence_doc["id"]),
                "archive": str(archive_path),
                "collections": collections,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
