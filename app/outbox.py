from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from bson import json_util
from sqlalchemy.orm import Session

from . import models
from .mongo import mirror_document

logger = logging.getLogger(__name__)

_OUTBOX_BATCH_SIZE = max(1, int(os.getenv("OUTBOX_DISPATCH_BATCH_SIZE", "100")))
_OUTBOX_RETRY_SECONDS = max(2, int(os.getenv("OUTBOX_RETRY_SECONDS", "10")))
_OUTBOX_MAX_ATTEMPTS = max(1, int(os.getenv("OUTBOX_MAX_ATTEMPTS", "8")))


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _encode_payload(payload: dict[str, Any] | None) -> str | None:
    if payload is None:
        return None
    return json_util.dumps(payload)


def _decode_payload(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    parsed = json_util.loads(raw)
    if isinstance(parsed, dict):
        return parsed
    return None


def enqueue_mongo_upsert(
    db: Session,
    *,
    collection_name: str,
    payload: dict[str, Any],
    upsert_filter: dict[str, Any] | None = None,
    required: bool = False,
) -> models.OutboxEvent:
    event = models.OutboxEvent(
        destination="mongo",
        collection_name=collection_name,
        operation="upsert",
        payload_json=_encode_payload(payload) or "{}",
        upsert_filter_json=_encode_payload(upsert_filter),
        required=bool(required),
        status="pending",
        attempts=0,
        available_at=_utcnow_naive(),
        created_at=_utcnow_naive(),
    )
    db.add(event)
    db.flush()
    return event


def enqueue_realtime_event(
    db: Session,
    *,
    event: dict[str, Any],
    required: bool = False,
) -> models.OutboxEvent:
    outbox_event = models.OutboxEvent(
        destination="realtime",
        collection_name="realtime_events",
        operation="publish",
        payload_json=_encode_payload(event) or "{}",
        upsert_filter_json=None,
        required=bool(required),
        status="pending",
        attempts=0,
        available_at=_utcnow_naive(),
        created_at=_utcnow_naive(),
    )
    db.add(outbox_event)
    db.flush()
    return outbox_event


def _dispatch_one(event: models.OutboxEvent) -> None:
    payload = _decode_payload(event.payload_json) or {}
    if event.destination == "realtime":
        from .realtime_bus import publish_prebuilt_realtime_event

        publish_prebuilt_realtime_event(payload, allow_outbox=False)
        return

    upsert_filter = _decode_payload(event.upsert_filter_json)
    mirror_document(
        event.collection_name,
        payload,
        required=bool(event.required),
        upsert_filter=upsert_filter,
        allow_outbox=False,
    )


def dispatch_outbox_batch(db: Session, *, limit: int | None = None) -> dict[str, int]:
    now = _utcnow_naive()
    batch_limit = max(1, int(limit or _OUTBOX_BATCH_SIZE))
    rows = (
        db.query(models.OutboxEvent)
        .filter(
            models.OutboxEvent.status.in_(["pending", "failed"]),
            models.OutboxEvent.available_at <= now,
        )
        .order_by(models.OutboxEvent.id.asc())
        .limit(batch_limit)
        .all()
    )

    dispatched = 0
    failed = 0
    for row in rows:
        row.attempts = int(row.attempts or 0) + 1
        row.status = "processing"
        row.processed_at = None
        row.last_error = None
        db.flush()

        try:
            _dispatch_one(row)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            row.last_error = str(exc)[:900]
            if row.attempts >= _OUTBOX_MAX_ATTEMPTS:
                row.status = "failed"
            else:
                row.status = "pending"
            row.available_at = _utcnow_naive() + timedelta(seconds=_OUTBOX_RETRY_SECONDS)
            logger.warning(
                "outbox_dispatch_failed id=%s collection=%s attempt=%s err=%s",
                row.id,
                row.collection_name,
                row.attempts,
                exc,
            )
            continue

        row.status = "sent"
        row.processed_at = _utcnow_naive()
        row.available_at = row.processed_at
        row.last_error = None
        dispatched += 1

    if rows:
        db.flush()
    return {"attempted": len(rows), "dispatched": dispatched, "failed": failed}
