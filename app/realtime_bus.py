from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import select
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from .redis_client import publish_json, start_pubsub_listener

LOGGER = logging.getLogger(__name__)


def _normalize_backend(token: str | None) -> str | None:
    raw = str(token or "").strip().lower()
    if not raw:
        return None
    if raw in {"redis"}:
        return "redis"
    if raw in {"postgres", "postgresql", "pg"}:
        return "postgres"
    if raw in {"mongo", "mongodb"}:
        return "mongo"
    raise RuntimeError(f"Unknown realtime backend: {token}")


def _realtime_backends() -> list[str]:
    raw = (os.getenv("REALTIME_BACKENDS") or "").strip()
    backends: list[str] = []
    if raw:
        for token in raw.replace(";", ",").split(","):
            backend = _normalize_backend(token)
            if backend and backend not in backends:
                backends.append(backend)
        if not backends:
            raise RuntimeError("REALTIME_BACKENDS must include at least one backend.")
        return backends

    fallback = _normalize_backend(os.getenv("REALTIME_BACKEND") or "redis") or "redis"
    return [fallback]


def _realtime_backends_required() -> bool:
    raw = (os.getenv("REALTIME_BACKENDS_REQUIRED") or "").strip().lower()
    if raw:
        return raw in {"1", "true", "yes", "on"}
    return (os.getenv("APP_RUNTIME_STRICT", "true") or "").strip().lower() in {"1", "true", "yes", "on"}


def _realtime_transport_enabled() -> bool:
    raw = (os.getenv("REALTIME_TRANSPORT_ENABLED", "true") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _realtime_redis_channel() -> str:
    return (os.getenv("REALTIME_REDIS_CHANNEL") or "campus:events:stream").strip()


def _realtime_pg_channel() -> str:
    raw = (os.getenv("REALTIME_PG_CHANNEL") or "campus_events_stream").strip()
    if not raw:
        raw = "campus_events_stream"
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", raw):
        raise RuntimeError("REALTIME_PG_CHANNEL must be a valid PostgreSQL channel identifier.")
    return raw


def _realtime_mongo_collection() -> str:
    return (os.getenv("REALTIME_MONGO_COLLECTION") or "realtime_events").strip() or "realtime_events"


def _realtime_dedupe_ttl_seconds() -> int:
    raw = (os.getenv("REALTIME_DEDUPE_TTL_SECONDS") or "30").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 30


def _realtime_dedupe_max() -> int:
    raw = (os.getenv("REALTIME_DEDUPE_MAX") or "5000").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 5000


def _publish_backend_event(event: dict[str, Any]) -> None:
    if not _realtime_transport_enabled():
        return
    errors: list[tuple[str, str]] = []
    successes = 0
    for backend in _realtime_backends():
        try:
            if backend == "redis":
                publish_json(_realtime_redis_channel(), event)
            elif backend == "postgres":
                _publish_postgres_event(event)
            elif backend == "mongo":
                _publish_mongo_event(event)
        except Exception as exc:  # noqa: BLE001
            message = str(exc) or "realtime publish failed"
            errors.append((backend, message))
            LOGGER.warning("Realtime publish failed backend=%s error=%s", backend, message)
        else:
            successes += 1

    if errors and successes == 0:
        combined = "; ".join(f"{backend}={message}" for backend, message in errors)
        raise RuntimeError(f"Realtime publish failed for all backends: {combined}")

    if errors and successes > 0:
        combined = "; ".join(f"{backend}={message}" for backend, message in errors)
        LOGGER.warning(
            "Realtime publish degraded but delivered via remaining backends: %s",
            combined,
        )


def _sql_realtime_outbox_enabled() -> bool:
    raw = (os.getenv("SQL_OUTBOX_ENABLED", "true") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _enqueue_realtime_outbox(event: dict[str, Any]) -> bool:
    if not _sql_realtime_outbox_enabled():
        return False

    try:
        from .database import SessionLocal
        from .outbox import dispatch_outbox_batch, enqueue_realtime_event
    except Exception:
        return False

    session = SessionLocal()
    queued = False
    try:
        enqueue_realtime_event(
            session,
            event=dict(event),
            required=_realtime_backends_required(),
        )
        session.commit()
        queued = True
        dispatch_outbox_batch(session, limit=20)
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()
    return queued


def _start_backend_listeners(
    *,
    on_message,
    stop_event: threading.Event,
) -> list[threading.Thread]:
    if not _realtime_transport_enabled():
        return []
    threads: list[threading.Thread] = []
    for backend in _realtime_backends():
        if backend == "redis":
            thread = start_pubsub_listener(
                channel=_realtime_redis_channel(),
                on_message=on_message,
                stop_event=stop_event,
                thread_name="realtime-redis-listener",
            )
        elif backend == "postgres":
            thread = _start_postgres_listener(on_message=on_message, stop_event=stop_event)
        elif backend == "mongo":
            thread = _start_mongo_listener(on_message=on_message, stop_event=stop_event)
        else:
            thread = None
        if thread is not None:
            threads.append(thread)
    return threads


def _publish_postgres_event(event: dict[str, Any]) -> None:
    from sqlalchemy import text

    from .database import engine

    channel = _realtime_pg_channel()
    payload = json.dumps(event, separators=(",", ":"), ensure_ascii=True)
    with engine.begin() as conn:
        conn.execute(text(f"NOTIFY {channel}, :payload"), {"payload": payload})


def _postgres_dsn() -> str | None:
    try:
        from .database import SQLALCHEMY_DATABASE_URL, postgres_libpq_url
    except Exception:
        return None
    override = (os.getenv("REALTIME_PG_DSN") or "").strip()
    if override:
        return postgres_libpq_url(override)
    return postgres_libpq_url(SQLALCHEMY_DATABASE_URL)


def _drain_pg_notifies(conn, on_message) -> None:
    poll_fn = getattr(conn, "poll", None)
    if callable(poll_fn):
        try:
            poll_fn()
        except Exception:
            return

    notifies = list(getattr(conn, "notifies", []) or [])
    try:
        getattr(conn, "notifies", []).clear()
    except Exception:
        pass

    for notify in notifies:
        payload = getattr(notify, "payload", None)
        if not payload:
            continue
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            on_message(parsed)


def _wait_for_pg_activity(conn, stop_event: threading.Event, timeout_seconds: float = 1.0) -> None:
    try:
        fileno = conn.fileno()
    except Exception:
        stop_event.wait(timeout_seconds)
        return
    try:
        select.select([fileno], [], [], timeout_seconds)
    except Exception:
        stop_event.wait(timeout_seconds)


def _start_postgres_listener(*, on_message, stop_event: threading.Event) -> threading.Thread | None:
    def _runner() -> None:
        reconnect_delay = 0.4
        while not stop_event.is_set():
            dsn = _postgres_dsn()
            if not dsn:
                LOGGER.error("Postgres realtime backend requires SQLALCHEMY_DATABASE_URL.")
                stop_event.wait(reconnect_delay)
                reconnect_delay = min(5.0, reconnect_delay * 1.8)
                continue
            try:
                import psycopg  # type: ignore
            except Exception as exc:  # noqa: BLE001
                LOGGER.error("Postgres realtime backend requires psycopg: %s", exc)
                return

            conn = None
            try:
                conn = psycopg.connect(dsn)
                conn.autocommit = True
                conn.execute(f"LISTEN {_realtime_pg_channel()}")
                reconnect_delay = 0.4
                while not stop_event.is_set():
                    _wait_for_pg_activity(conn, stop_event, 1.0)
                    _drain_pg_notifies(conn, on_message)
            except Exception as exc:  # noqa: BLE001
                if stop_event.is_set():
                    break
                LOGGER.exception("Postgres realtime listener error: %s", exc)
                stop_event.wait(reconnect_delay)
                reconnect_delay = min(5.0, reconnect_delay * 1.8)
            finally:
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass

    thread = threading.Thread(target=_runner, name="realtime-postgres-listener", daemon=True)
    thread.start()
    return thread


def _publish_mongo_event(event: dict[str, Any]) -> None:
    from .mongo import get_mongo_db
    from pymongo.errors import DuplicateKeyError

    mongo_db = get_mongo_db(required=True)
    doc = dict(event)
    doc["_id"] = doc.get("id") or uuid.uuid4().hex
    doc["created_at_dt"] = datetime.now(timezone.utc)
    try:
        mongo_db[_realtime_mongo_collection()].insert_one(doc)
    except DuplicateKeyError:
        return


def _start_mongo_listener(*, on_message, stop_event: threading.Event) -> threading.Thread | None:
    def _runner() -> None:
        reconnect_delay = 0.4
        while not stop_event.is_set():
            try:
                from .mongo import get_mongo_db

                mongo_db = get_mongo_db(required=True)
                collection = mongo_db[_realtime_mongo_collection()]
                with collection.watch(
                    [{"$match": {"operationType": "insert"}}],
                    full_document="updateLookup",
                    max_await_time_ms=1000,
                ) as stream:
                    reconnect_delay = 0.4
                    while not stop_event.is_set():
                        change = stream.try_next()
                        if change is None:
                            stop_event.wait(0.4)
                            continue
                        doc = change.get("fullDocument") or {}
                        if isinstance(doc, dict):
                            event = dict(doc)
                            event.pop("_id", None)
                            event.pop("created_at_dt", None)
                            on_message(event)
            except Exception as exc:  # noqa: BLE001
                if stop_event.is_set():
                    break
                LOGGER.exception("Mongo realtime listener error: %s", exc)
                stop_event.wait(reconnect_delay)
                reconnect_delay = min(5.0, reconnect_delay * 1.8)

    thread = threading.Thread(target=_runner, name="realtime-mongo-listener", daemon=True)
    thread.start()
    return thread


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
        self._listener_stop = threading.Event()
        self._listener_threads: list[threading.Thread] = []
        self._dedupe_lock = threading.Lock()
        self._dedupe_cache: OrderedDict[str, float] = OrderedDict()

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def start(self) -> None:
        self._listener_stop.clear()
        self._listener_threads = [thread for thread in self._listener_threads if thread.is_alive()]
        if self._listener_threads:
            return
        self._listener_threads = _start_backend_listeners(
            on_message=self._on_backend_message,
            stop_event=self._listener_stop,
        )

    async def stop(self) -> None:
        self._listener_stop.set()
        for thread in list(self._listener_threads):
            join_fn = getattr(thread, "join", None)
            if callable(join_fn):
                try:
                    join_fn(timeout=1.0)
                except Exception:
                    pass
        self._listener_threads = []
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
        self._remember_recent_event(str(event.get("id") or ""))
        self._schedule(self._publish_local(event))
        try:
            _publish_backend_event(event)
        except Exception as exc:
            if _enqueue_realtime_outbox(event):
                LOGGER.warning(
                    "Realtime publish deferred to SQL outbox event_type=%s error=%s",
                    event.get("event_type"),
                    exc,
                )
                return
            raise

    def publish_prebuilt(self, event: dict[str, Any], *, allow_outbox: bool = True) -> None:
        self._remember_recent_event(str(event.get("id") or ""))
        self._schedule(self._publish_local(event))
        try:
            _publish_backend_event(event)
        except Exception as exc:
            if allow_outbox and _enqueue_realtime_outbox(event):
                LOGGER.warning(
                    "Realtime publish deferred to SQL outbox event_type=%s error=%s",
                    event.get("event_type"),
                    exc,
                )
                return
            raise

    def _on_backend_message(self, event: dict[str, Any]) -> None:
        origin = str(event.get("origin") or "")
        if origin == self._instance_id:
            return
        event_id = str(event.get("id") or "")
        if event_id and self._seen_recent_event(event_id):
            return
        self._schedule(self._publish_local(event))

    def _remember_recent_event(self, event_id: str) -> None:
        if not event_id:
            return
        self._track_recent_event(event_id)

    def _seen_recent_event(self, event_id: str) -> bool:
        return self._track_recent_event(event_id)

    def _track_recent_event(self, event_id: str) -> bool:
        ttl_seconds = _realtime_dedupe_ttl_seconds()
        max_items = _realtime_dedupe_max()
        if ttl_seconds <= 0 or max_items <= 0:
            return False
        now = time.time()
        with self._dedupe_lock:
            while self._dedupe_cache:
                _oldest_id, oldest_ts = next(iter(self._dedupe_cache.items()))
                if now - oldest_ts <= ttl_seconds:
                    break
                self._dedupe_cache.popitem(last=False)
            already_seen = event_id in self._dedupe_cache
            self._dedupe_cache[event_id] = now
            self._dedupe_cache.move_to_end(event_id)
            if len(self._dedupe_cache) > max_items:
                self._dedupe_cache.popitem(last=False)
        return already_seen

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
    if prefix in {
        "attendance",
        "messages",
        "rms",
        "admin",
        "auth",
        "system",
        "food",
        "remedial",
        "identity",
        "identity_shield",
    }:
        return {prefix}
    return {"system"}


def user_scopes(current_user: Any) -> set[str]:
    scopes = {
        f"role:{str(getattr(current_user, 'role', 'unknown')).split('.')[-1].lower()}",
        f"user:{int(getattr(current_user, 'id', 0) or 0)}",
    }
    role_value = str(getattr(current_user, "role", "unknown")).split(".")[-1].lower()
    student_id = getattr(current_user, "student_id", None)
    faculty_id = getattr(current_user, "faculty_id", None)
    if student_id:
        scopes.add(f"student:{int(student_id)}")
    if faculty_id:
        scopes.add(f"faculty:{int(faculty_id)}")
    if role_value == "owner":
        scopes.update(_owner_shop_scopes(int(getattr(current_user, "id", 0) or 0)))
    return scopes


def _owner_shop_scopes(owner_user_id: int) -> set[str]:
    if owner_user_id <= 0:
        return set()
    try:
        from . import models
        from .database import SessionLocal
    except Exception:
        return set()

    session = SessionLocal()
    try:
        rows = (
            session.query(models.FoodShop.id)
            .filter(models.FoodShop.owner_user_id == int(owner_user_id))
            .all()
        )
        return {f"shop:{int(row.id)}" for row in rows if getattr(row, "id", None)}
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Failed to resolve owner realtime shop scopes for user_id=%s: %s", owner_user_id, exc)
        return set()
    finally:
        session.close()


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


def publish_prebuilt_realtime_event(event: dict[str, Any], *, allow_outbox: bool = True) -> None:
    realtime_hub.publish_prebuilt(event, allow_outbox=allow_outbox)
