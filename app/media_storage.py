from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from bson.binary import Binary
from pymongo.errors import PyMongoError
from sqlalchemy.orm import Session

from . import models
from .enterprise_controls import resolve_secret
from .mongo import get_mongo_db, invalidate_mongo_connection

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEDIA_ROOT = Path(os.getenv("MEDIA_STORAGE_PATH", str(PROJECT_ROOT / ".media_objects"))).resolve()
MEDIA_BUCKET = (os.getenv("MEDIA_STORAGE_BUCKET", "profile-media") or "profile-media").strip() or "profile-media"
MEDIA_MONGO_COLLECTION = (
    os.getenv("MEDIA_MONGO_COLLECTION", "media_blobs") or "media_blobs"
).strip() or "media_blobs"
MEDIA_URL_TTL_SECONDS = max(60, int(os.getenv("MEDIA_SIGNED_URL_TTL_SECONDS", "900")))
DEFAULT_RETENTION_DAYS = max(1, int(os.getenv("MEDIA_RETENTION_DAYS", "180")))

_DATA_URL_PATTERN = re.compile(r"^data:([\w.+\-/]+);base64,(.+)$", re.IGNORECASE)


def _strict_runtime_enabled() -> bool:
    raw = (os.getenv("APP_RUNTIME_STRICT", "true") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _media_backend() -> str:
    raw = (os.getenv("MEDIA_STORAGE_BACKEND") or "").strip().lower()
    if raw:
        if raw in {"mongo", "mongodb"}:
            return "mongo"
        if raw in {"filesystem", "file", "local", "disk"}:
            if _strict_runtime_enabled() or _is_production_env():
                raise RuntimeError("MEDIA_STORAGE_BACKEND=filesystem is not allowed in strict/production mode.")
            return "filesystem"
        raise RuntimeError("MEDIA_STORAGE_BACKEND must be one of: mongo, filesystem.")

    if _strict_runtime_enabled() or _is_production_env():
        return "mongo"
    return "filesystem"


def _media_storage_remote_required() -> bool:
    raw = (os.getenv("MEDIA_STORAGE_REQUIRE_REMOTE") or "").strip().lower()
    if raw:
        return raw in {"1", "true", "yes", "on"}
    return _strict_runtime_enabled() or _is_production_env()


def assert_media_storage_ready() -> None:
    backend = _media_backend()
    if backend != "mongo":
        return
    mongo_db = get_mongo_db(required=_media_storage_remote_required())
    if mongo_db is None:
        raise RuntimeError("MEDIA_STORAGE_BACKEND=mongo requires MongoDB connectivity.")


def _is_production_env() -> bool:
    env = (os.getenv("APP_ENV", "development") or "development").strip().lower()
    return env in {"prod", "production"}


def _media_signing_secret() -> str:
    default = "lpu-dev-secret-change-in-production"
    fallback = resolve_secret("APP_AUTH_SECRET", default=default) or default
    secret = resolve_secret("APP_MEDIA_URL_SECRET", default=fallback) or fallback
    normalized = str(secret).strip()
    if _is_production_env():
        if not normalized:
            raise RuntimeError("APP_MEDIA_URL_SECRET (or APP_AUTH_SECRET) is required in production.")
        if normalized == default:
            raise RuntimeError("Media signing secret cannot use development default in production.")
    return normalized or default


def _ensure_media_root() -> None:
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)


def _safe_object_path(object_key: str) -> Path:
    candidate = (MEDIA_ROOT / object_key).resolve()
    if not str(candidate).startswith(str(MEDIA_ROOT)):
        raise HTTPException(status_code=400, detail="Invalid media object key")
    return candidate


def _decode_data_url(data_url: str) -> tuple[str, bytes]:
    raw = str(data_url or "").strip()
    match = _DATA_URL_PATTERN.match(raw)
    if not match:
        raise HTTPException(status_code=400, detail="Expected image data URL payload")

    content_type = str(match.group(1)).strip().lower()
    encoded = match.group(2).strip()
    try:
        payload = base64.b64decode(encoded, validate=False)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Invalid base64 media payload") from exc

    if not payload:
        raise HTTPException(status_code=400, detail="Empty media payload")
    return content_type, payload


def _guess_extension(content_type: str) -> str:
    if content_type.endswith("png"):
        return "png"
    if content_type.endswith("jpeg") or content_type.endswith("jpg"):
        return "jpg"
    if content_type.endswith("webp"):
        return "webp"
    if content_type.endswith("gif"):
        return "gif"
    return "bin"


def _new_object_key(media_kind: str, content_type: str) -> str:
    now = datetime.utcnow()
    ext = _guess_extension(content_type)
    token = secrets.token_urlsafe(18)
    kind = re.sub(r"[^a-z0-9/_-]+", "", media_kind.strip().lower()) or "media"
    return f"{kind}/{now.year:04d}/{now.month:02d}/{now.day:02d}/{token}.{ext}"


def _store_media_blob_in_mongo(
    *,
    object_key: str,
    payload: bytes,
    content_type: str,
    checksum: str,
    owner_table: str,
    owner_id: int | None,
    media_kind: str,
    retention_until: datetime | None,
) -> None:
    mongo_db = get_mongo_db(required=_media_storage_remote_required())
    if mongo_db is None:
        raise RuntimeError("MongoDB is unavailable for media storage.")

    now_dt = datetime.utcnow()
    doc = {
        "object_key": object_key,
        "bucket": MEDIA_BUCKET,
        "owner_table": owner_table,
        "owner_id": int(owner_id) if owner_id else None,
        "media_kind": media_kind,
        "content_type": content_type,
        "size_bytes": len(payload),
        "checksum_sha256": checksum,
        "retention_until": retention_until,
        "deleted_at": None,
        "updated_at": now_dt,
        "data": Binary(payload),
    }
    try:
        mongo_db[MEDIA_MONGO_COLLECTION].update_one(
            {"object_key": object_key},
            {"$set": doc, "$setOnInsert": {"created_at": now_dt}},
            upsert=True,
        )
    except PyMongoError as exc:
        invalidate_mongo_connection(exc)
        raise RuntimeError(f"MongoDB media storage failed: {exc}") from exc


def _load_media_blob_from_mongo(object_key: str) -> tuple[bytes, str] | None:
    mongo_db = get_mongo_db(required=_media_storage_remote_required())
    if mongo_db is None:
        raise RuntimeError("MongoDB is unavailable for media storage.")

    try:
        doc = mongo_db[MEDIA_MONGO_COLLECTION].find_one(
            {"object_key": object_key},
            {"data": 1, "content_type": 1, "deleted_at": 1},
        )
    except PyMongoError as exc:
        invalidate_mongo_connection(exc)
        raise RuntimeError(f"MongoDB media fetch failed: {exc}") from exc

    if not doc or doc.get("deleted_at") is not None:
        return None

    payload = doc.get("data")
    if payload is None:
        return None

    if isinstance(payload, Binary):
        payload_bytes = bytes(payload)
    elif isinstance(payload, (bytes, bytearray)):
        payload_bytes = bytes(payload)
    else:
        return None

    content_type = str(doc.get("content_type") or "application/octet-stream")
    return payload_bytes, content_type


def _mark_media_blob_deleted_in_mongo(object_key: str) -> None:
    mongo_db = get_mongo_db(required=False)
    if mongo_db is None:
        return
    try:
        mongo_db[MEDIA_MONGO_COLLECTION].update_one(
            {"object_key": object_key},
            {"$set": {"deleted_at": datetime.utcnow(), "updated_at": datetime.utcnow()}},
        )
    except PyMongoError as exc:
        invalidate_mongo_connection(exc)


def build_signed_media_url(object_key: str, *, ttl_seconds: int | None = None) -> str:
    expires_at = int((datetime.utcnow() + timedelta(seconds=max(60, int(ttl_seconds or MEDIA_URL_TTL_SECONDS)))).timestamp())
    payload = f"{object_key}|{expires_at}".encode("utf-8")
    signature = hmac.new(_media_signing_secret().encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"/assets/media/{object_key}?exp={expires_at}&sig={signature}"


def verify_signed_media_url(object_key: str, *, exp: int, sig: str) -> bool:
    now_ts = int(datetime.utcnow().timestamp())
    if exp < now_ts:
        return False
    payload = f"{object_key}|{exp}".encode("utf-8")
    expected = hmac.new(_media_signing_secret().encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, str(sig or ""))


def store_data_url_object(
    db: Session,
    *,
    owner_table: str,
    owner_id: int | None,
    media_kind: str,
    data_url: str,
    retention_days: int | None = None,
) -> models.MediaObject:
    content_type, payload = _decode_data_url(data_url)
    object_key = _new_object_key(media_kind=media_kind, content_type=content_type)

    checksum = hashlib.sha256(payload).hexdigest()
    now_dt = datetime.utcnow()
    keep_days = max(1, int(retention_days or DEFAULT_RETENTION_DAYS))
    retention_until = now_dt + timedelta(days=keep_days)

    backend = _media_backend()
    if backend == "filesystem":
        _ensure_media_root()
        object_path = _safe_object_path(object_key)
        object_path.parent.mkdir(parents=True, exist_ok=True)
        object_path.write_bytes(payload)
    elif backend == "mongo":
        _store_media_blob_in_mongo(
            object_key=object_key,
            payload=payload,
            content_type=content_type,
            checksum=checksum,
            owner_table=owner_table,
            owner_id=owner_id,
            media_kind=media_kind,
            retention_until=retention_until,
        )
    else:
        raise RuntimeError(f"Unsupported media storage backend: {backend}")

    media = models.MediaObject(
        object_key=object_key,
        bucket=MEDIA_BUCKET,
        owner_table=owner_table,
        owner_id=int(owner_id) if owner_id else None,
        media_kind=media_kind,
        content_type=content_type,
        size_bytes=len(payload),
        checksum_sha256=checksum,
        retention_until=retention_until,
        created_at=now_dt,
        updated_at=now_dt,
    )
    db.add(media)
    db.flush()
    return media


def mark_media_deleted(db: Session, object_key: str | None) -> None:
    token = str(object_key or "").strip()
    if not token:
        return
    row = db.query(models.MediaObject).filter(models.MediaObject.object_key == token).first()
    if row is None:
        return
    row.deleted_at = datetime.utcnow()
    row.updated_at = datetime.utcnow()
    db.flush()
    if _media_backend() == "mongo":
        _mark_media_blob_deleted_in_mongo(token)


def open_media_bytes(db: Session, object_key: str) -> tuple[bytes, str]:
    key = str(object_key or "").strip()
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media object not found")

    row = db.query(models.MediaObject).filter(models.MediaObject.object_key == key).first()
    if row is None or row.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media object not found")

    backend = _media_backend()
    if backend == "mongo":
        blob = _load_media_blob_from_mongo(key)
        if not blob:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media object not found")
        payload, blob_content_type = blob
        return payload, str(row.content_type or blob_content_type or "application/octet-stream")

    if backend == "filesystem":
        path = _safe_object_path(key)
        if not path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media object not found")
        return path.read_bytes(), str(row.content_type or "application/octet-stream")

    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Media storage backend misconfigured")


def data_url_for_object(db: Session, object_key: str) -> str | None:
    key = str(object_key or "").strip()
    if not key:
        return None
    try:
        payload, content_type = open_media_bytes(db, key)
    except HTTPException:
        return None
    encoded = base64.b64encode(payload).decode("utf-8")
    return f"data:{content_type};base64,{encoded}"


def signed_url_for_object(object_key: str | None) -> str | None:
    key = str(object_key or "").strip()
    if not key:
        return None
    return build_signed_media_url(key)


def soft_delete_expired_media(db: Session, *, now_dt: datetime | None = None, limit: int = 500) -> int:
    now_ts = now_dt or datetime.utcnow()
    rows = (
        db.query(models.MediaObject)
        .filter(
            models.MediaObject.deleted_at.is_(None),
            models.MediaObject.retention_until.isnot(None),
            models.MediaObject.retention_until < now_ts,
        )
        .order_by(models.MediaObject.retention_until.asc())
        .limit(max(1, int(limit)))
        .all()
    )
    updated = 0
    for row in rows:
        row.deleted_at = now_ts
        row.updated_at = now_ts
        updated += 1
    if updated:
        db.flush()
    return updated


def media_owner_ref(owner_table: str, owner_id: int | None) -> dict[str, Any]:
    return {
        "owner_table": owner_table,
        "owner_id": int(owner_id) if owner_id else None,
    }
