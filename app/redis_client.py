import json
import logging
import os
import threading
import time
import math
import sys
from urllib.parse import SplitResult
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable
from pathlib import Path

try:  # pragma: no cover - optional dependency in some runtime shells
    from dotenv import dotenv_values, load_dotenv
except Exception:  # noqa: BLE001
    def load_dotenv(*_args, **_kwargs):
        return False

    def dotenv_values(*_args, **_kwargs):
        return {}

from .runtime_infra import (
    is_remote_service_host,
    install_socket_dns_fallback,
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
_local_rate_limit_lock = threading.Lock()
_local_rate_limit_counters: dict[str, tuple[int, float]] = {}
_LOCAL_RATE_LIMIT_MAX_TRACKED = 50_000
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ORIGINAL_ENV = dict(os.environ)
_ENV_LOADED = False


@dataclass(slots=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    used: int
    remaining: int
    retry_after_seconds: int


def _running_under_pytest() -> bool:
    if "PYTEST_CURRENT_TEST" in os.environ:
        return True
    if "pytest" in sys.modules:
        return True
    return any("pytest" in str(arg).lower() for arg in sys.argv)


def _load_environment_files() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    if _running_under_pytest():
        return
    load_dotenv(_PROJECT_ROOT / ".env")
    local_values = dotenv_values(_PROJECT_ROOT / ".env.local")
    for key, value in local_values.items():
        if value is None:
            continue
        if key in _ORIGINAL_ENV:
            continue
        os.environ[key] = str(value)
    _ENV_LOADED = True


def _local_rate_limit_hit(redis_key: str, *, limit: int, window_seconds: int, now: float) -> RateLimitDecision:
    expires_at_default = now + window_seconds
    with _local_rate_limit_lock:
        # Opportunistic cleanup to avoid unbounded growth if Redis is unavailable.
        if len(_local_rate_limit_counters) > _LOCAL_RATE_LIMIT_MAX_TRACKED:
            stale = [key for key, (_, expiry) in _local_rate_limit_counters.items() if expiry <= now]
            for key in stale[:10_000]:
                _local_rate_limit_counters.pop(key, None)

        used, expires_at = _local_rate_limit_counters.get(redis_key, (0, expires_at_default))
        if expires_at <= now:
            used = 0
            expires_at = expires_at_default
        used += 1
        _local_rate_limit_counters[redis_key] = (used, expires_at)

    ttl = max(1, int(math.ceil(expires_at - now)))
    return RateLimitDecision(
        allowed=used <= limit,
        limit=limit,
        used=used,
        remaining=max(0, limit - used),
        retry_after_seconds=ttl,
    )


def _redis_url() -> str:
    _load_environment_files()
    return (os.getenv("REDIS_URL") or "").strip()


def _redis_required() -> bool:
    raw = (os.getenv("REDIS_REQUIRED", "false") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _redis_auto_degrade_on_quota_exceeded() -> bool:
    raw = (os.getenv("REDIS_AUTO_DEGRADE_ON_QUOTA_EXCEEDED", "true") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _is_redis_quota_exceeded_error(message: str | None) -> bool:
    raw = str(message or "").strip().lower()
    return "max requests limit exceeded" in raw


def _redis_quota_degraded() -> bool:
    if not _redis_auto_degrade_on_quota_exceeded():
        return False
    return _is_redis_quota_exceeded_error(_redis_error)


def _rate_limit_allow_local_fallback() -> bool:
    raw = (os.getenv("API_RATE_LIMIT_ALLOW_LOCAL_FALLBACK", "false") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def redis_required() -> bool:
    return _redis_required()


def redis_runtime_required() -> bool:
    return _redis_required() and not _redis_quota_degraded()


def redis_quota_degraded() -> bool:
    return _redis_quota_degraded()


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


def _socket_keepalive_enabled() -> bool:
    raw = (os.getenv("REDIS_SOCKET_KEEPALIVE", "true") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _retry_on_timeout_enabled() -> bool:
    raw = (os.getenv("REDIS_RETRY_ON_TIMEOUT", "true") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _should_retry_redis_error(exc: Exception) -> bool:
    message = str(exc or "").lower()
    if "connection closed by server" in message:
        return True
    if "connection reset" in message:
        return True
    if "connection aborted" in message:
        return True
    if "connection refused" in message:
        return True
    if "connection error" in message:
        return True
    return False


def _retry_redis_call(operation: Callable[[Redis], Any]) -> Any:
    client = get_redis(required=False)
    if client is None:
        raise RedisError(_redis_error or "Redis is unavailable")
    try:
        return operation(client)
    except RedisError as exc:
        if not _should_retry_redis_error(exc):
            raise
        close_redis()
        init_redis(force=True)
        client = get_redis(required=False)
        if client is None:
            raise
        return operation(client)


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
        install_socket_dns_fallback()
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
            socket_keepalive=_socket_keepalive_enabled(),
            retry_on_timeout=_retry_on_timeout_enabled(),
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
        "runtime_required": redis_runtime_required(),
        "quota_degraded": _redis_quota_degraded(),
        "host": host,
        "scheme": scheme,
        "remote_host": is_remote_service_host(host),
        "tls_enabled": _redis_tls_enabled(),
        "error": None if client is not None else _redis_error,
    }


def cache_get_json(key: str) -> Any | None:
    client = get_redis(required=False)
    if client is None:
        if redis_runtime_required():
            raise RuntimeError(_redis_error or "Redis is unavailable")
        return None
    try:
        raw = _retry_redis_call(lambda active_client: active_client.get(key))
    except RedisError as exc:
        if redis_runtime_required():
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
        if redis_runtime_required():
            raise RuntimeError(_redis_error or "Redis is unavailable")
        return False
    ttl = max(1, int(ttl_seconds))
    try:
        _retry_redis_call(
            lambda active_client: active_client.set(
                key,
                json.dumps(payload, default=_json_default),
                ex=ttl,
            )
        )
        return True
    except RedisError as exc:
        if redis_runtime_required():
            raise RuntimeError(str(exc) or "Redis cache write failed") from exc
        return False


def cache_delete(key: str) -> bool:
    client = get_redis(required=False)
    if client is None:
        if redis_runtime_required():
            raise RuntimeError(_redis_error or "Redis is unavailable")
        return False
    try:
        _retry_redis_call(lambda active_client: active_client.delete(key))
        return True
    except RedisError as exc:
        if redis_runtime_required():
            raise RuntimeError(str(exc) or "Redis cache delete failed") from exc
        return False


def rate_limit_hit(key: str, *, limit: int, window_seconds: int) -> RateLimitDecision:
    global _redis_error
    safe_limit = max(1, int(limit))
    safe_window = max(1, int(window_seconds))
    now = time.time()

    runtime_required = redis_runtime_required()
    client = get_redis(required=True if runtime_required else False)
    bucket = int(now // safe_window)
    redis_key = f"rl:{key}:{bucket}"
    if client is None:
        if (not runtime_required) and (_rate_limit_allow_local_fallback() or _redis_quota_degraded()):
            return _local_rate_limit_hit(
                redis_key,
                limit=safe_limit,
                window_seconds=safe_window,
                now=now,
            )
        raise RuntimeError(_redis_error or "Redis rate limiter is unavailable")

    try:
        def _op(active_client: Redis):
            pipe = active_client.pipeline()
            pipe.incr(redis_key, 1)
            pipe.ttl(redis_key)
            return pipe.execute()

        used_raw, ttl_raw = _retry_redis_call(_op)
        used = int(used_raw or 0)
        ttl = int(ttl_raw or -1)
        if used == 1 or ttl < 0:
            _retry_redis_call(lambda active_client: active_client.expire(redis_key, safe_window))
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
        message = str(exc) or "Redis rate limiter is unavailable"
        # Upstash monthly quota exhaustion must degrade gracefully so API stays up.
        if _redis_auto_degrade_on_quota_exceeded() and _is_redis_quota_exceeded_error(message):
            _redis_error = message
            close_redis()
            logger.warning(
                "Redis quota exceeded during rate limiting; using in-memory fallback window. key=%s",
                key,
            )
            return _local_rate_limit_hit(
                redis_key,
                limit=safe_limit,
                window_seconds=safe_window,
                now=now,
            )
        raise RuntimeError(str(exc) or "Redis rate limiter is unavailable") from exc


def publish_json(channel: str, payload: dict[str, Any]) -> bool:
    client = get_redis(required=False)
    if client is None:
        if redis_runtime_required():
            raise RuntimeError(_redis_error or "Redis publish channel is unavailable")
        return False
    try:
        _retry_redis_call(
            lambda active_client: active_client.publish(
                channel,
                json.dumps(payload, default=_json_default),
            )
        )
        return True
    except RedisError as exc:
        if redis_runtime_required():
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
        if redis_runtime_required():
            raise RuntimeError(_redis_error or "Redis pubsub is unavailable")
        return None

    def _runner() -> None:
        reconnect_delay = 0.4
        while not stop_event.is_set():
            pubsub = None
            active_client = get_redis(required=False)
            if active_client is None:
                if redis_runtime_required():
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
                last_ping = time.monotonic()
                while not stop_event.is_set():
                    now = time.monotonic()
                    if now - last_ping >= 20.0:
                        try:
                            pubsub.ping()
                        except Exception as exc:  # noqa: BLE001
                            raise exc
                        last_ping = now
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
                if redis_runtime_required():
                    logger.exception(
                        "Redis pubsub listener error channel=%s error=%s",
                        channel,
                        exc,
                    )
                if _should_retry_redis_error(exc):
                    close_redis()
                    init_redis(force=True)
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
