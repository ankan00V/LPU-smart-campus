"""Migrate local media files from MEDIA_ROOT into Mongo and optionally delete local artifacts."""
from __future__ import annotations

import argparse
import hashlib
import logging
import os
from pathlib import Path
from typing import Iterable

from app import models
from app.database import SessionLocal
from app.media_storage import MEDIA_ROOT, _store_media_blob_in_mongo
from app.mongo import get_mongo_db

LOGGER = logging.getLogger("media_migration")


def _safe_object_path(object_key: str) -> Path:
    candidate = (MEDIA_ROOT / object_key).resolve()
    if not str(candidate).startswith(str(MEDIA_ROOT)):
        raise ValueError(f"Invalid object key path: {object_key}")
    return candidate


def _iter_media_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return (path for path in root.rglob("*") if path.is_file())


def _cleanup_empty_dirs(root: Path, start: Path) -> None:
    current = start
    while True:
        if current == root:
            break
        try:
            next(current.iterdir())
            break
        except StopIteration:
            current.rmdir()
            current = current.parent
        except FileNotFoundError:
            break


def migrate_media(*, dry_run: bool, delete_local: bool, delete_orphans: bool, include_deleted: bool) -> int:
    if not MEDIA_ROOT.exists():
        LOGGER.warning("MEDIA_ROOT does not exist: %s", MEDIA_ROOT)
        return 0

    # Ensure Mongo is reachable before making changes.
    get_mongo_db(required=True)

    session = SessionLocal()
    try:
        query = session.query(models.MediaObject)
        if not include_deleted:
            query = query.filter(models.MediaObject.deleted_at.is_(None))
        rows = query.all()

        db_keys = {str(row.object_key or "").strip(): row for row in rows if str(row.object_key or "").strip()}
        migrated = 0
        skipped = 0
        missing = 0

        for object_key, row in db_keys.items():
            try:
                path = _safe_object_path(object_key)
            except ValueError as exc:
                LOGGER.error("Skipping invalid object_key=%s error=%s", object_key, exc)
                skipped += 1
                continue

            if not path.exists() or not path.is_file():
                LOGGER.warning("Missing local media file for object_key=%s", object_key)
                missing += 1
                continue

            payload = path.read_bytes()
            checksum = hashlib.sha256(payload).hexdigest()
            if row.checksum_sha256 and row.checksum_sha256 != checksum:
                LOGGER.warning(
                    "Checksum mismatch for object_key=%s sql=%s file=%s",
                    object_key,
                    row.checksum_sha256,
                    checksum,
                )

            if dry_run:
                LOGGER.info("[dry-run] would migrate object_key=%s size=%s", object_key, len(payload))
            else:
                _store_media_blob_in_mongo(
                    object_key=object_key,
                    payload=payload,
                    content_type=str(row.content_type or "application/octet-stream"),
                    checksum=checksum,
                    owner_table=str(row.owner_table or ""),
                    owner_id=row.owner_id,
                    media_kind=str(row.media_kind or "media"),
                    retention_until=row.retention_until,
                )
                migrated += 1

            if delete_local and not dry_run:
                path.unlink(missing_ok=True)
                _cleanup_empty_dirs(MEDIA_ROOT, path.parent)

        if delete_orphans:
            for path in _iter_media_files(MEDIA_ROOT):
                try:
                    rel = path.relative_to(MEDIA_ROOT)
                except ValueError:
                    continue
                object_key = str(rel).replace(os.sep, "/")
                if object_key in db_keys:
                    continue
                if dry_run:
                    LOGGER.info("[dry-run] would delete orphan file=%s", path)
                else:
                    LOGGER.warning("Deleting orphan local media file=%s", path)
                    path.unlink(missing_ok=True)
                    _cleanup_empty_dirs(MEDIA_ROOT, path.parent)

        LOGGER.info(
            "Migration completed. migrated=%s skipped=%s missing=%s delete_local=%s delete_orphans=%s dry_run=%s",
            migrated,
            skipped,
            missing,
            delete_local,
            delete_orphans,
            dry_run,
        )
        return migrated
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate local media files into MongoDB.")
    parser.add_argument("--dry-run", action="store_true", help="Report actions without writing/deleting.")
    parser.add_argument("--keep-local", action="store_true", help="Do not delete local files after migration.")
    parser.add_argument("--keep-orphans", action="store_true", help="Do not delete orphan files in MEDIA_ROOT.")
    parser.add_argument("--include-deleted", action="store_true", help="Include media rows marked deleted.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    migrate_media(
        dry_run=bool(args.dry_run),
        delete_local=not args.keep_local,
        delete_orphans=not args.keep_orphans,
        include_deleted=bool(args.include_deleted),
    )


if __name__ == "__main__":
    main()
