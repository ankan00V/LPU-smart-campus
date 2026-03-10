#!/usr/bin/env python3
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from app.enterprise_controls import get_field_encryptor, rotate_collection_encryption
from app.mongo import get_mongo_db, init_mongo, next_sequence


def _default_collections() -> list[dict[str, list[str]]]:
    return [
        {"name": "auth_users", "fields": ["alternate_email_encrypted"]},
        {
            "name": "students",
            "fields": [
                "parent_email_encrypted",
                "profile_photo_data_url_encrypted",
                "profile_face_template_json_encrypted",
                "enrollment_video_template_json_encrypted",
            ],
        },
        {"name": "faculty", "fields": ["profile_photo_data_url_encrypted"]},
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run field encryption key rotation and persist evidence")
    parser.add_argument("--dry-run", action="store_true", help="Scan only; do not persist rotated ciphertext")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--collections", default="", help="JSON list: [{\"name\":\"...\",\"fields\":[...]}]")
    parser.add_argument("--triggered-by", default="automation")
    args = parser.parse_args()

    if not init_mongo(force=True):
        raise SystemExit("MongoDB is unavailable. Rotation requires MongoDB.")
    db = get_mongo_db(required=True)

    collections = _default_collections()
    raw_collections = str(args.collections or "").strip()
    if raw_collections:
        try:
            parsed = json.loads(raw_collections)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid --collections JSON: {exc}") from exc
        if isinstance(parsed, list):
            normalized = []
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "").strip()
                fields = [str(field).strip() for field in (item.get("fields") or []) if str(field).strip()]
                if name and fields:
                    normalized.append({"name": name, "fields": fields})
            if normalized:
                collections = normalized

    results = []
    for item in collections:
        result = rotate_collection_encryption(
            db,
            collection_name=item["name"],
            field_names=item["fields"],
            dry_run=bool(args.dry_run),
            batch_size=max(10, min(5000, int(args.batch_size))),
        )
        results.append(result)

    encryptor = get_field_encryptor()
    run_doc = {
        "id": next_sequence("security_key_rotation_runs"),
        "dry_run": bool(args.dry_run),
        "results": results,
        "active_key_id": encryptor.active_key_id,
        "triggered_by_user_id": None,
        "triggered_by_email": str(args.triggered_by or "automation"),
        "created_at": datetime.utcnow(),
    }
    db["security_key_rotation_runs"].insert_one(run_doc)
    print(
        json.dumps(
            {
                "rotation_run_id": int(run_doc["id"]),
                "dry_run": bool(args.dry_run),
                "active_key_id": encryptor.active_key_id,
                "results": results,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
