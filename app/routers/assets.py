from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse, Response

from ..mongo import get_mongo_db

router = APIRouter(prefix="/assets", tags=["Static Assets"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ASSETS_DIR = PROJECT_ROOT / "web" / "assets"
ASSET_COLLECTION = "static_assets"
LOGGER = logging.getLogger(__name__)

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
        "filename": "campus-route-map.jpg",
        "content_type": "image/jpeg",
        "remote_url": "https://blog402.wordpress.com/wp-content/uploads/2011/04/campus-map1.jpg",
    },
}


def _asset_file_path(asset_key: str) -> Path:
    config = STATIC_ASSETS[asset_key]
    return WEB_ASSETS_DIR / config["filename"]


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


def seed_static_assets_to_mongo() -> dict[str, int]:
    mongo_db = get_mongo_db()
    if mongo_db is None:
        return {"stored": 0, "skipped": len(STATIC_ASSETS)}

    stored = 0
    skipped = 0
    for asset_key, config in STATIC_ASSETS.items():
        file_path = _asset_file_path(asset_key)
        data: bytes | None = None
        if file_path.exists():
            data = file_path.read_bytes()

        if not data:
            remote_url = str(config.get("remote_url") or "").strip()
            if remote_url:
                data = _fetch_remote_bytes(remote_url)

        if not data:
            skipped += 1
            continue

        digest = hashlib.sha256(data).hexdigest()
        current = mongo_db[ASSET_COLLECTION].find_one({"key": asset_key}, {"sha256": 1})
        if current and current.get("sha256") == digest:
            skipped += 1
            continue

        mongo_db[ASSET_COLLECTION].update_one(
            {"key": asset_key},
            {
                "$set": {
                    "key": asset_key,
                    "filename": config["filename"],
                    "content_type": config["content_type"],
                    "size": len(data),
                    "sha256": digest,
                    "data": data,
                    "updated_at": datetime.now(timezone.utc),
                    "source": "startup-seed",
                }
            },
            upsert=True,
        )
        stored += 1

    return {"stored": stored, "skipped": skipped}


@router.get("/static/{asset_key}", include_in_schema=False)
def get_static_asset(asset_key: str):
    if asset_key not in STATIC_ASSETS:
        raise HTTPException(status_code=404, detail="Asset not found")

    config = STATIC_ASSETS[asset_key]
    mongo_db = get_mongo_db()
    if mongo_db is not None:
        doc = mongo_db[ASSET_COLLECTION].find_one(
            {"key": asset_key},
            {"_id": 0, "content_type": 1, "data": 1, "sha256": 1},
        )
        if doc:
            payload = _coerce_bytes(doc.get("data"))
            if payload:
                headers = {"Cache-Control": "public, max-age=86400"}
                etag = str(doc.get("sha256", "")).strip()
                if etag:
                    headers["ETag"] = etag
                return Response(
                    content=payload,
                    media_type=str(doc.get("content_type") or config["content_type"]),
                    headers=headers,
                )

    file_path = _asset_file_path(asset_key)
    if file_path.exists():
        return FileResponse(
            file_path,
            media_type=config["content_type"],
            headers={"Cache-Control": "public, max-age=3600"},
        )

    remote_url = str(config.get("remote_url") or "").strip()
    if remote_url:
        return RedirectResponse(url=remote_url, status_code=307)

    raise HTTPException(status_code=404, detail="Asset source unavailable")
