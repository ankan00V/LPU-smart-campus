import json
import logging
import os
import threading
import time
from urllib.parse import SplitResult
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable

from .runtime_infra import (
    is_remote_service_host,
    managed_services_required,
    normalize_host,
    split_url,
)

try:  # pragma: no cover - optional dependency in local dev
    import redis
    from redis import Redis
    from redis.exceptions import RedisError
except Exception:  # noqa: BLE001
    redis = None
    Redis = Any  # type: ignore[assignment]

    class RedisError(Exception):
        pass


_redis_client: Redis | None = None
_redis_error: str | None = None
logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    used: int
    remaining: int
    retry_after_seconds: int


def _redis_url() -> str:
    return (os.getenv("REDIS_URL") or "").strip()


def _redis_required() -> bool:
    raw = (os.getenv("REDIS_REQUIRED", "false") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def redis_required() -> bool:
    return _redis_required()


def _redis_ssl_required() -> bool:
    raw = (os.getenv("REDIS_SSL_REQUIRED") or "").strip()
    if raw:
        return raw.lower() in {"1", "true", "yes", "on"}
    return managed_services_required()


def _redis_url_parts(value: str | None = None) -> SplitResult:
    return split_url(value if value is not None else _redis_url())


def _redis_scheme(value: str | None = None) -> str | None:
    scheme = str(_redis_url_parts(value).scheme or "").strip().lower()
    return scheme or None


def _redis_host(value: str | None = None) -> str | None:
    return normalize_host(_redis_url_parts(value).hostname)


def _redis_tls_enabled(value: str | None = None) -> bool:
    return _redis_scheme(value) == "rediss"


def _socket_timeout_seconds() -> float:
    raw = (os.getenv("REDIS_SOCKET_TIMEOUT_SECONDS", "1.5") or "").strip()
    try:
        value = float(raw)
    except ValueError:
        value = 1.5
    return max(0.2, min(10.0, value))


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def init_redis(force: bool = False) -> bool:
    global _redis_client, _redis_error

    if _redis_client is not None and not force:
        return True

    url = _redis_url()
    if not url:
        _redis_client = None
        _redis_error = "REDIS_URL is not configured"
        return False

    if redis is None:
        _redis_client = None
        _redis_error = "redis package is not installed"
        return False

    scheme = _redis_scheme(url)
    if _redis_ssl_required() and scheme != "rediss":
        _redis_client = None
        _redis_error = "Managed runtime requires REDIS_URL to use rediss:// with TLS enabled."
        return False

    try:
        client_kwargs: dict[str, Any] = {}
        if scheme == "rediss":
            ssl_ca_file = (os.getenv("REDIS_SSL_CA_FILE") or "").strip()
            ssl_cert_file = (os.getenv("REDIS_SSL_CERT_FILE") or "").strip()
            ssl_key_file = (os.getenv("REDIS_SSL_KEY_FILE") or "").strip()
            ssl_check_hostname_raw = (os.getenv("REDIS_SSL_CHECK_HOSTNAME") or "").strip()
            ssl_cert_reqs = (os.getenv("REDIS_SSL_CERT_REQS") or "").strip().lower() or "required"
            client_kwargs["ssl_cert_reqs"] = ssl_cert_reqs
            if ssl_ca_file:
                client_kwargs["ssl_ca_certs"] = ssl_ca_file
            if ssl_cert_file:
                client_kwargs["ssl_certfile"] = ssl_cert_file
            if ssl_key_file:
                client_kwargs["ssl_keyfile"] = ssl_key_file
            if ssl_check_hostname_raw:
                client_kwargs["ssl_check_hostname"] = ssl_check_hostname_raw.lower() in {
                    "1",
                    "true",
                    "yes",
                    "on",
                }

        client: Redis = redis.Redis.from_url(  # type: ignore[union-attr]
            url,
            decode_responses=True,
            socket_timeout=_socket_timeout_seconds(),
            socket_connect_timeout=_socket_timeout_seconds(),
            health_check_interval=30,
            **client_kwargs,
        )
        client.ping()
        _redis_client = client
        _redis_error = None
        return True
    except RedisError as exc:
        _redis_client = None
        _redis_error = str(exc)
        return False


def close_redis() -> None:
    global _redis_client
    client = _redis_client
    _redis_client = None
    if client is None:
        return
    try:
        client.close()
    except Exception:
        return


def get_redis(required: bool = False) -> Redis | None:
    client = _redis_client
    if client is None:
        init_redis(force=False)
        client = _redis_client
    if required and client is None:
        raise RuntimeError(_redis_error or "Redis is unavailable")
    return client


def redis_status() -> dict[str, Any]:
    client = get_redis(required=False)
    host = _redis_host()
    scheme = _redis_scheme()
    return {
        "enabled": client is not None,
        "required": _redis_required(),
        "host": host,
        "scheme": scheme,
        "remote_host": is_remote_service_host(host),
        "tls_enabled": _redis_tls_enabled(),
        "error": None if client is not None else _redis_error,
    }


def cache_get_json(key: str) -> Any | None:
    client = get_redis(required=False)
    if client is None:
        if _redis_required():
            raise RuntimeError(_redis_error or "Redis is unavailable")
        return None
    try:
        raw = client.get(key)
    except RedisError as exc:
        if _redis_required():
            raise RuntimeError(str(exc) or "Redis cache read failed") from exc
        return None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def cache_set_json(key: str, payload: Any, ttl_seconds: int = 30) -> bool:
    client = get_redis(required=False)
    if client is None:
        if _redis_required():
            raise RuntimeError(_redis_error or "Redis is unavailable")
        return False
    ttl = max(1, int(ttl_seconds))
    try:
        client.set(key, json.dumps(payload, default=_json_default), ex=ttl)
        return True
    except RedisError as exc:
        if _redis_required():
            raise RuntimeError(str(exc) or "Redis cache write failed") from exc
        return False


def cache_delete(key: str) -> bool:
    client = get_redis(required=False)
    if client is None:
        if _redis_required():
            raise RuntimeError(_redis_error or "Redis is unavailable")
        return False
    try:
        client.delete(key)
        return True
    except RedisError as exc:
        if _redis_required():
            raise RuntimeError(str(exc) or "Redis cache delete failed") from exc
        return False


def rate_limit_hit(key: str, *, limit: int, window_seconds: int) -> RateLimitDecision:
    safe_limit = max(1, int(limit))
    safe_window = max(1, int(window_seconds))
    now = time.time()

    client = get_redis(required=True if _redis_required() else False)
    if client is None:
        raise RuntimeError(_redis_error or "Redis rate limiter is unavailable")

    bucket = int(now // safe_window)
    redis_key = f"rl:{key}:{bucket}"
    try:
        pipe = client.pipeline()
        pipe.incr(redis_key, 1)
        pipe.ttl(redis_key)
        used_raw, ttl_raw = pipe.execute()
        used = int(used_raw or 0)
        ttl = int(ttl_raw or -1)
        if used == 1 or ttl < 0:
            client.expire(redis_key, safe_window)
            ttl = safe_window
        allowed = used <= safe_limit
        remaining = max(0, safe_limit - used)
        retry_after = max(1, ttl if ttl > 0 else safe_window)
        return RateLimitDecision(
            allowed=allowed,
            limit=safe_limit,
            used=used,
            remaining=remaining,
            retry_after_seconds=retry_after,
        )
    except RedisError as exc:
        raise RuntimeError(str(exc) or "Redis rate limiter is unavailable") from exc


def publish_json(channel: str, payload: dict[str, Any]) -> bool:
    client = get_redis(required=False)
    if client is None:
        if _redis_required():
            raise RuntimeError(_redis_error or "Redis publish channel is unavailable")
        return False
    try:
        client.publish(channel, json.dumps(payload, default=_json_default))
        return True
    except RedisError as exc:
        if _redis_required():
            raise RuntimeError(str(exc) or "Redis publish failed") from exc
        return False


def start_pubsub_listener(
    *,
    channel: str,
    on_message: Callable[[dict[str, Any]], None],
    stop_event: threading.Event,
    thread_name: str,
) -> threading.Thread | None:
    client = get_redis(required=False)
    if client is None:
        if _redis_required():
            raise RuntimeError(_redis_error or "Redis pubsub is unavailable")
        return None

    def _runner() -> None:
        reconnect_delay = 0.4
        while not stop_event.is_set():
            pubsub = None
            active_client = get_redis(required=False)
            if active_client is None:
                if _redis_required():
                    logger.error(
                        "Redis pubsub unavailable for channel=%s; retrying. reason=%s",
                        channel,
                        _redis_error or "unknown",
                    )
                stop_event.wait(reconnect_delay)
                reconnect_delay = min(5.0, reconnect_delay * 1.8)
                continue
            try:
                pubsub = active_client.pubsub(ignore_subscribe_messages=True)
                pubsub.subscribe(channel)
                reconnect_delay = 0.4
                while not stop_event.is_set():
                    raw = pubsub.get_message(timeout=1.0)
                    if not raw:
                        continue
                    if raw.get("type") != "message":
                        continue
                    body = raw.get("data")
                    if isinstance(body, bytes):
                        body = body.decode("utf-8", errors="replace")
                    if not isinstance(body, str):
                        continue
                    try:
                        payload = json.loads(body)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(payload, dict):
                        on_message(payload)
            except Exception as exc:  # noqa: BLE001
                message = str(exc or "").strip().lower()
                if stop_event.is_set() or "closed file" in message:
                    break
                if _redis_required():
                    logger.exception(
                        "Redis pubsub listener error channel=%s error=%s",
                        channel,
                        exc,
                    )
                stop_event.wait(reconnect_delay)
                reconnect_delay = min(5.0, reconnect_delay * 1.8)
            finally:
                if pubsub is not None:
                    try:
                        pubsub.close()
                    except Exception:
                        pass

    thread = threading.Thread(target=_runner, name=thread_name, daemon=True)
    thread.start()
    return thread
