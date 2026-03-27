from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, TypeVar
from urllib.error import URLError
from urllib.request import urlopen

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse, Response
from pymongo.errors import PyMongoError
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from ..database import get_db
from ..media_storage import open_media_bytes, verify_signed_media_url
from ..mongo import get_mongo_db, init_mongo, invalidate_mongo_connection

router = APIRouter(prefix="/assets", tags=["Static Assets"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ASSETS_DIR = PROJECT_ROOT / "web" / "assets"
ASSET_COLLECTION = "static_assets"
LOGGER = logging.getLogger(__name__)
ASSET_CACHE_HEADERS = {"Cache-Control": "public, max-age=0, must-revalidate"}
MONGO_CONFIRMED_ASSET_KEYS: set[str] = set()
_T = TypeVar("_T")

STATIC_ASSETS: dict[str, dict[str, str]] = {
    "lpu-smart-campus-logo": {
        "filename": "lpu-smart-campus-logo.png",
        "content_type": "image/png",
    },
    "auth-side-panel-bg": {
        "filename": "auth-side-panel-bg.png",
        "content_type": "image/png",
    },
    "campus-route-map": {
        "filename": "campus-route-map.svg",
        "content_type": "image/svg+xml",
    },
}


def _bool_env(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name, "true" if default else "false") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _static_asset_mongo_required() -> bool:
    raw = (os.getenv("STATIC_ASSET_REQUIRE_MONGO") or "").strip().lower()
    if raw:
        return raw in {"1", "true", "yes", "on"}
    if _bool_env("MONGO_PERSISTENCE_REQUIRED", default=True):
        return True
    return _bool_env("APP_RUNTIME_STRICT", default=True)


def _asset_file_path(asset_key: str) -> Path:
    config = STATIC_ASSETS[asset_key]
    return WEB_ASSETS_DIR / config["filename"]


@lru_cache(maxsize=len(STATIC_ASSETS))
def _read_local_asset_bundle(asset_key: str) -> tuple[bytes, str] | None:
    file_path = _asset_file_path(asset_key)
    if not file_path.exists():
        return None
    payload = file_path.read_bytes()
    if not payload:
        return None
    return payload, hashlib.sha256(payload).hexdigest()


def _coerce_bytes(value: Any) -> bytes | None:
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    return None


def _fetch_remote_bytes(url: str, timeout_seconds: float = 4.0) -> bytes | None:
    try:
        with urlopen(url, timeout=timeout_seconds) as response:
            payload = response.read()
        return payload if payload else None
    except (URLError, TimeoutError, ValueError) as exc:
        LOGGER.warning("remote_asset_fetch_failed url=%s err=%s", url, exc)
        return None


def _mark_asset_seeded(asset_key: str) -> None:
    MONGO_CONFIRMED_ASSET_KEYS.add(asset_key)


def _run_mongo_asset_operation(operation: Callable[[Any], _T]) -> _T:
    last_exc: Exception | None = None
    invalidated = False
    for attempt in range(2):
        try:
            mongo_db = get_mongo_db(required=False)
        except TypeError:
            mongo_db = get_mongo_db()
        if mongo_db is None:
            init_mongo(force=True)
            try:
                mongo_db = get_mongo_db(required=False)
            except TypeError:
                mongo_db = get_mongo_db()
        if mongo_db is None:
            break
        try:
            return operation(mongo_db)
        except PyMongoError as exc:
            last_exc = exc
            if not invalidated:
                invalidate_mongo_connection(exc)
                invalidated = True
            if attempt == 0:
                continue
            raise
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("MongoDB is unavailable")


def _upsert_static_asset(asset_key: str, *, payload: bytes, digest: str, source: str) -> str:
    config = STATIC_ASSETS[asset_key]
    try:
        current = _run_mongo_asset_operation(
            lambda mongo_db: mongo_db[ASSET_COLLECTION].find_one({"key": asset_key}, {"sha256": 1})
        )
    except (PyMongoError, RuntimeError) as exc:
        LOGGER.warning("static_asset_seed_lookup_failed asset_key=%s err=%s", asset_key, exc)
        return "failed"

    if current and current.get("sha256") == digest:
        _mark_asset_seeded(asset_key)
        return "skipped"

    try:
        _run_mongo_asset_operation(
            lambda mongo_db: mongo_db[ASSET_COLLECTION].update_one(
                {"key": asset_key},
                {
                    "$set": {
                        "key": asset_key,
                        "filename": config["filename"],
                        "content_type": config["content_type"],
                        "size": len(payload),
                        "sha256": digest,
                        "data": payload,
                        "updated_at": datetime.now(timezone.utc),
                        "source": source,
                    }
                },
                upsert=True,
            )
        )
    except (PyMongoError, RuntimeError) as exc:
        LOGGER.warning("static_asset_seed_write_failed asset_key=%s err=%s", asset_key, exc)
        return "failed"

    _mark_asset_seeded(asset_key)
    return "stored"


def _seed_bundled_asset_to_mongo_in_background(asset_key: str) -> None:
    if asset_key in MONGO_CONFIRMED_ASSET_KEYS:
        return
    local_bundle = _read_local_asset_bundle(asset_key)
    if not local_bundle:
        return
    payload, digest = local_bundle
    _upsert_static_asset(asset_key, payload=payload, digest=digest, source="request-bundled-fallback")


def _response_from_mongo(asset_key: str) -> Response | None:
    config = STATIC_ASSETS[asset_key]
    try:
        doc = _run_mongo_asset_operation(
            lambda mongo_db: mongo_db[ASSET_COLLECTION].find_one(
                {"key": asset_key},
                {"_id": 0, "content_type": 1, "data": 1, "sha256": 1},
            )
        )
    except (PyMongoError, RuntimeError) as exc:
        LOGGER.warning("static_asset_lookup_failed asset_key=%s err=%s", asset_key, exc)
        return None

    if not doc:
        return None

    payload = _coerce_bytes(doc.get("data"))
    if not payload:
        return None

    _mark_asset_seeded(asset_key)
    headers = dict(ASSET_CACHE_HEADERS)
    etag = str(doc.get("sha256", "")).strip()
    if etag:
        headers["ETag"] = f"\"{etag}\""
    return Response(
        content=payload,
        media_type=str(doc.get("content_type") or config["content_type"]),
        headers=headers,
    )


def _response_from_local_bundle(asset_key: str) -> Response | None:
    config = STATIC_ASSETS[asset_key]
    local_bundle = _read_local_asset_bundle(asset_key)
    if not local_bundle:
        return None
    _payload, digest = local_bundle
    file_path = _asset_file_path(asset_key)
    if not file_path.exists():
        return None
    headers = dict(ASSET_CACHE_HEADERS)
    headers["ETag"] = f"\"{digest}\""
    background = None
    if asset_key not in MONGO_CONFIRMED_ASSET_KEYS:
        background = BackgroundTask(_seed_bundled_asset_to_mongo_in_background, asset_key)
    return FileResponse(
        file_path,
        media_type=config["content_type"],
        headers=headers,
        background=background,
    )


def build_static_asset_response(asset_key: str, *, prefer_database: bool = True) -> Response:
    if asset_key not in STATIC_ASSETS:
        raise HTTPException(status_code=404, detail="Asset not found")

    if _static_asset_mongo_required():
        mongo_response = _response_from_mongo(asset_key)
        if mongo_response is not None:
            return mongo_response
        raise HTTPException(
            status_code=503,
            detail="Static assets must be served from MongoDB in this environment.",
        )

    if prefer_database:
        mongo_response = _response_from_mongo(asset_key)
        if mongo_response is not None:
            return mongo_response

        local_response = _response_from_local_bundle(asset_key)
        if local_response is not None:
            return local_response
    else:
        local_response = _response_from_local_bundle(asset_key)
        if local_response is not None:
            return local_response

        mongo_response = _response_from_mongo(asset_key)
        if mongo_response is not None:
            return mongo_response

    config = STATIC_ASSETS[asset_key]
    file_path = _asset_file_path(asset_key)
    if file_path.exists():
        return FileResponse(
            file_path,
            media_type=config["content_type"],
            headers=dict(ASSET_CACHE_HEADERS),
        )

    remote_url = str(config.get("remote_url") or "").strip()
    if remote_url:
        return RedirectResponse(url=remote_url, status_code=307)

    raise HTTPException(status_code=404, detail="Asset source unavailable")


def seed_static_assets_to_mongo(*, required: bool = False) -> dict[str, int]:
    mongo_db = get_mongo_db(required=False)
    if mongo_db is None:
        if required:
            raise RuntimeError("MongoDB is unavailable for required static asset seeding.")
        return {"stored": 0, "skipped": len(STATIC_ASSETS), "failed": 0}

    stored = 0
    skipped = 0
    failed = 0
    for asset_key, config in STATIC_ASSETS.items():
        data: bytes | None = None
        digest = ""
        local_bundle = _read_local_asset_bundle(asset_key)
        if local_bundle:
            data, digest = local_bundle

        if not data:
            remote_url = str(config.get("remote_url") or "").strip()
            if remote_url:
                data = _fetch_remote_bytes(remote_url)
                if data:
                    digest = hashlib.sha256(data).hexdigest()

        if not data:
            failed += 1
            if required:
                raise RuntimeError(f"Required bundled asset is unavailable: {asset_key}")
            continue

        seed_status = _upsert_static_asset(asset_key, payload=data, digest=digest, source="startup-seed")
        if seed_status == "stored":
            stored += 1
            continue
        if seed_status == "skipped":
            skipped += 1
            continue

        failed += 1
        if required:
            raise RuntimeError(f"Failed to seed required static asset into MongoDB: {asset_key}")

    return {"stored": stored, "skipped": skipped, "failed": failed}


@router.get("/static/{asset_key}", include_in_schema=False)
def get_static_asset(asset_key: str):
    return build_static_asset_response(asset_key, prefer_database=True)


@router.get("/media/{object_key:path}", include_in_schema=False)
def get_signed_media_object(
    object_key: str,
    exp: int = Query(...),
    sig: str = Query(..., min_length=32, max_length=128),
    db: Session = Depends(get_db),
):
    if not verify_signed_media_url(object_key, exp=int(exp), sig=sig):
        raise HTTPException(status_code=403, detail="Invalid or expired media signature")
    payload, content_type = open_media_bytes(db, object_key)
    return Response(
        content=payload,
        media_type=content_type,
        headers={"Cache-Control": "private, max-age=60"},
    )
