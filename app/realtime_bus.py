from __future__ import annotations

import asyncio
import os
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from .redis_client import publish_json, start_pubsub_listener


@dataclass(slots=True)
class _Subscriber:
    queue: asyncio.Queue[dict[str, Any]]
    scopes: set[str]
    topics: set[str]


class RealtimeEventHub:
    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._subscribers: dict[str, _Subscriber] = {}
        self._lock = asyncio.Lock()
        self._instance_id = uuid.uuid4().hex
        self._redis_channel = (
            os.getenv("REALTIME_REDIS_CHANNEL") or "campus:events:stream"
        ).strip()
        self._listener_stop = threading.Event()
        self._listener_thread: threading.Thread | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def start(self) -> None:
        self._listener_stop.clear()
        if self._listener_thread is not None and self._listener_thread.is_alive():
            return
        self._listener_thread = start_pubsub_listener(
            channel=self._redis_channel,
            on_message=self._on_redis_message,
            stop_event=self._listener_stop,
            thread_name="realtime-redis-listener",
        )

    async def stop(self) -> None:
        self._listener_stop.set()
        async with self._lock:
            self._subscribers.clear()

    async def subscribe(
        self,
        *,
        scopes: Iterable[str],
        topics: Iterable[str],
        queue_size: int = 200,
    ) -> tuple[str, asyncio.Queue[dict[str, Any]]]:
        subscriber_id = uuid.uuid4().hex
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=max(10, int(queue_size)))
        subscriber = _Subscriber(
            queue=queue,
            scopes=self._normalize_scope_values(scopes),
            topics=self._normalize_topic_values(topics),
        )
        async with self._lock:
            self._subscribers[subscriber_id] = subscriber
        return subscriber_id, queue

    async def unsubscribe(self, subscriber_id: str) -> None:
        async with self._lock:
            self._subscribers.pop(subscriber_id, None)

    def publish(
        self,
        event_type: str,
        *,
        payload: dict[str, Any] | None = None,
        scopes: Iterable[str] | None = None,
        topics: Iterable[str] | None = None,
        actor: dict[str, Any] | None = None,
        source: str = "api",
    ) -> None:
        event = {
            "id": uuid.uuid4().hex,
            "origin": self._instance_id,
            "event_type": str(event_type or "system.update").strip() or "system.update",
            "source": str(source or "api"),
            "actor": dict(actor or {}),
            "payload": dict(payload or {}),
            "scopes": sorted(self._normalize_scope_values(scopes or {"scope:all"})),
            "topics": sorted(self._normalize_topic_values(topics or infer_topics(event_type))),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._schedule(self._publish_local(event))
        publish_json(self._redis_channel, event)

    def _on_redis_message(self, event: dict[str, Any]) -> None:
        origin = str(event.get("origin") or "")
        if origin == self._instance_id:
            return
        self._schedule(self._publish_local(event))

    def _schedule(self, coro: asyncio.Future | asyncio.Task | Any) -> None:
        loop = self._loop
        if loop is None:
            close_fn = getattr(coro, "close", None)
            if callable(close_fn):
                close_fn()
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None

        if running is loop:
            asyncio.create_task(coro)
            return

        try:
            asyncio.run_coroutine_threadsafe(coro, loop)
        except RuntimeError:
            close_fn = getattr(coro, "close", None)
            if callable(close_fn):
                close_fn()
            return

    async def _publish_local(self, event: dict[str, Any]) -> None:
        scopes = self._normalize_scope_values(event.get("scopes") or {"scope:all"})
        topics = self._normalize_topic_values(event.get("topics") or infer_topics(event.get("event_type", "")))

        async with self._lock:
            subscribers = list(self._subscribers.values())

        for subscriber in subscribers:
            if not self._scope_match(subscriber.scopes, scopes):
                continue
            if not self._topic_match(subscriber.topics, topics):
                continue
            if subscriber.queue.full():
                try:
                    subscriber.queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                subscriber.queue.put_nowait(event)
            except asyncio.QueueFull:
                continue

    @staticmethod
    def _normalize_scope_values(scopes: Iterable[str]) -> set[str]:
        output = {
            str(scope or "").strip().lower()
            for scope in scopes
            if str(scope or "").strip()
        }
        if not output:
            output = {"scope:all"}
        return output

    @staticmethod
    def _normalize_topic_values(topics: Iterable[str]) -> set[str]:
        output = {
            str(topic or "").strip().lower()
            for topic in topics
            if str(topic or "").strip()
        }
        if not output:
            output = {"*"}
        return output

    @staticmethod
    def _scope_match(subscriber_scopes: set[str], event_scopes: set[str]) -> bool:
        if "scope:all" in event_scopes:
            return True
        if "scope:all" in subscriber_scopes:
            return True
        return bool(subscriber_scopes.intersection(event_scopes))

    @staticmethod
    def _topic_match(subscriber_topics: set[str], event_topics: set[str]) -> bool:
        if "*" in subscriber_topics:
            return True
        if "*" in event_topics:
            return True
        return bool(subscriber_topics.intersection(event_topics))


realtime_hub = RealtimeEventHub()


def parse_topics(raw_topics: str | None) -> set[str]:
    if not raw_topics:
        return {"*"}
    tokens = set()
    for item in str(raw_topics).replace(";", ",").split(","):
        token = item.strip().lower()
        if token:
            tokens.add(token)
    return tokens or {"*"}


def infer_topics(event_type: str | None) -> set[str]:
    raw = str(event_type or "").strip().lower()
    if not raw:
        return {"system"}
    prefix = raw.split(".", 1)[0]
    if prefix in {"attendance", "messages", "rms", "admin", "auth", "system", "food", "remedial"}:
        return {prefix}
    return {"system"}


def user_scopes(current_user: Any) -> set[str]:
    scopes = {
        f"role:{str(getattr(current_user, 'role', 'unknown')).split('.')[-1].lower()}",
        f"user:{int(getattr(current_user, 'id', 0) or 0)}",
    }
    student_id = getattr(current_user, "student_id", None)
    faculty_id = getattr(current_user, "faculty_id", None)
    if student_id:
        scopes.add(f"student:{int(student_id)}")
    if faculty_id:
        scopes.add(f"faculty:{int(faculty_id)}")
    return scopes


def publish_domain_event(
    event_type: str,
    *,
    payload: dict[str, Any] | None = None,
    scopes: Iterable[str] | None = None,
    topics: Iterable[str] | None = None,
    actor: dict[str, Any] | None = None,
    source: str = "api",
) -> None:
    realtime_hub.publish(
        event_type,
        payload=payload,
        scopes=scopes,
        topics=topics,
        actor=actor,
        source=source,
    )
