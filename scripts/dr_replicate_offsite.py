#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


def _latest_backup(root: Path) -> Path | None:
    backups = [item for item in root.iterdir() if item.is_dir() and not item.name.startswith(".")]
    backups.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return backups[0] if backups else None


def _manifest_hash(path: Path) -> str | None:
    manifest = path / "manifest.json"
    if not manifest.exists():
        return None
    return hashlib.sha256(manifest.read_bytes()).hexdigest()


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Replicate local DR backup folder to offsite storage path")
    parser.add_argument("--backups-dir", default="backups", help="Local backups root")
    parser.add_argument("--offsite-dir", default="", help="Offsite destination root (defaults to DR_OFFSITE_PATH env)")
    parser.add_argument("--backup-id", default="", help="Specific backup folder name. Defaults to latest.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing offsite folder if present")
    args = parser.parse_args()

    local_root = Path(args.backups_dir).resolve()
    if not local_root.exists():
        raise SystemExit(f"Backups dir not found: {local_root}")

    offsite_raw = str(args.offsite_dir or os.getenv("DR_OFFSITE_PATH") or "").strip()
    if not offsite_raw:
        raise SystemExit("Missing --offsite-dir (or DR_OFFSITE_PATH env)")
    offsite_root = Path(offsite_raw).expanduser().resolve()
    offsite_root.mkdir(parents=True, exist_ok=True)

    source = (local_root / args.backup_id).resolve() if args.backup_id else _latest_backup(local_root)
    if source is None or not source.exists() or not source.is_dir():
        raise SystemExit("No backup folder found for replication")

    destination = offsite_root / source.name
    if destination.exists():
        if not args.overwrite:
            raise SystemExit(f"Destination already exists: {destination} (use --overwrite)")
        shutil.rmtree(destination)

    shutil.copytree(source, destination)
    replicated_at = datetime.utcnow()
    replication_manifest = {
        "backup_id": source.name,
        "source": str(source),
        "destination": str(destination),
        "replicated_at": replicated_at,
        "source_manifest_sha256": _manifest_hash(source),
        "destination_manifest_sha256": _manifest_hash(destination),
    }
    (destination / "offsite-replication.json").write_text(
        json.dumps(_jsonable(replication_manifest), indent=2),
        encoding="utf-8",
    )

    print(json.dumps(_jsonable(replication_manifest), indent=2))


if __name__ == "__main__":
    main()
