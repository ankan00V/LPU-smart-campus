import asyncio
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from .. import models
from ..auth_utils import require_roles
from ..realtime_bus import parse_topics, realtime_hub, user_scopes

router = APIRouter(prefix="/events", tags=["Realtime Events"])


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def _format_sse_message(event: dict[str, Any]) -> str:
    event_id = str(event.get("id") or "")
    data = json.dumps(event, default=_json_default)
    return f"id: {event_id}\ndata: {data}\n\n"


@router.get("/stream")
async def stream_events(
    request: Request,
    topics: str | None = Query(default=None, description="Comma-separated topic filters"),
    current_user: models.AuthUser = Depends(
        require_roles(
            models.UserRole.ADMIN,
            models.UserRole.FACULTY,
            models.UserRole.STUDENT,
            models.UserRole.OWNER,
        )
    ),
):
    subscriber_id, queue = await realtime_hub.subscribe(
        scopes=user_scopes(current_user),
        topics=parse_topics(topics),
    )

    async def event_generator():
        yield "retry: 3000\n\n"
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
                    continue

                yield _format_sse_message(event)
        finally:
            await realtime_hub.unsubscribe(subscriber_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
