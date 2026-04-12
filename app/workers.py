import logging
import os
import sys
import time as pytime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any
from urllib.parse import SplitResult
import ssl

from dotenv import dotenv_values, load_dotenv

from .otp_delivery import send_login_otp
from .redis_client import redis_quota_degraded
from .runtime_infra import (
    install_socket_dns_fallback,
    is_remote_service_host,
    managed_services_required,
    normalize_host,
    split_url,
)

logger = logging.getLogger(__name__)

_ORIGINAL_ENV = dict(os.environ)
_ENV_LOADED = False


def _load_environment_files() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    if "PYTEST_CURRENT_TEST" in os.environ:
        return
    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(project_root / ".env")
    local_values = dotenv_values(project_root / ".env.local")
    for key, value in local_values.items():
        if value is None:
            continue
        if key in _ORIGINAL_ENV:
            continue
        os.environ[key] = str(value)
    _ENV_LOADED = True


_load_environment_files()

try:  # pragma: no cover - optional dependency
    from celery import Celery
except Exception:  # noqa: BLE001
    Celery = None


TASK_SEND_OTP = "smartcampus.tasks.send_login_otp"
TASK_NOTIFY = "smartcampus.tasks.send_notification"
TASK_FACE_REVERIFY = "smartcampus.tasks.face_reverify"
TASK_RECOMPUTE = "smartcampus.tasks.recompute"
_OTP_DELIVERY_CHANNELS = {"smtp-email", "graph-email", "sendgrid-email"}

_executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="smartcampus-worker")
_celery_app = None


def _bool_env(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name, "true" if default else "false") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _otp_wait_for_result() -> bool:
    return _bool_env("WORKER_WAIT_FOR_OTP_RESULT", default=True)


def _otp_direct_sync_enabled() -> bool:
    return _bool_env("OTP_DELIVERY_DIRECT_SYNC", default=True)


def _app_runtime_strict_enabled() -> bool:
    return _bool_env("APP_RUNTIME_STRICT", default=True)


def _running_under_pytest() -> bool:
    if "PYTEST_CURRENT_TEST" in os.environ:
        return True
    if "pytest" in sys.modules:
        return True
    return any("pytest" in str(arg).lower() for arg in sys.argv)


def _otp_inline_fallback_runtime_allowed() -> bool:
    app_env = (os.getenv("APP_ENV", "") or "").strip().lower()
    return app_env in {"dev", "development", "local"}


def _otp_inline_fallback_enabled() -> bool:
    return _bool_env("OTP_INLINE_FALLBACK_ENABLED", default=False)


def _worker_startup_max_attempts() -> int:
    raw = (os.getenv("WORKER_STARTUP_MAX_ATTEMPTS", "4") or "").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 4
    return max(1, min(20, value))


def _worker_startup_retry_delay_seconds() -> float:
    raw = (os.getenv("WORKER_STARTUP_RETRY_DELAY_SECONDS", "1.0") or "").strip()
    try:
        value = float(raw)
    except ValueError:
        value = 1.0
    return max(0.0, min(10.0, value))


def _worker_startup_ping_timeout_seconds() -> float:
    raw = (os.getenv("WORKER_STARTUP_PING_TIMEOUT_SECONDS", "2.0") or "").strip()
    try:
        value = float(raw)
    except ValueError:
        value = 2.0
    return max(0.2, min(10.0, value))


def _redis_socket_timeout_seconds() -> float:
    raw = (os.getenv("REDIS_SOCKET_TIMEOUT_SECONDS", "1.5") or "").strip()
    try:
        value = float(raw)
    except ValueError:
        value = 1.5
    return max(0.2, min(10.0, value))


def _redis_retry_on_timeout() -> bool:
    raw = (os.getenv("REDIS_RETRY_ON_TIMEOUT", "true") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _redis_socket_keepalive() -> bool:
    raw = (os.getenv("REDIS_SOCKET_KEEPALIVE", "true") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _celery_transport_options() -> dict[str, Any]:
    timeout = _redis_socket_timeout_seconds()
    return {
        "socket_timeout": timeout,
        "socket_connect_timeout": timeout,
        "retry_on_timeout": _redis_retry_on_timeout(),
        "health_check_interval": 30,
        "socket_keepalive": _redis_socket_keepalive(),
    }


def _ssl_cert_reqs_setting() -> int:
    raw = (os.getenv("REDIS_SSL_CERT_REQS") or "").strip().lower() or "required"
    if raw in {"none", "false", "0"}:
        return ssl.CERT_NONE
    return ssl.CERT_REQUIRED


def _is_transient_redis_error(exc: Exception) -> bool:
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


def worker_required() -> bool:
    return _bool_env("WORKER_REQUIRED", default=False)


def _worker_auto_degrade_on_redis_quota_exceeded() -> bool:
    return _bool_env("WORKER_AUTO_DEGRADE_ON_REDIS_QUOTA_EXCEEDED", default=True)


def _worker_degraded_due_redis_quota() -> bool:
    if not _worker_auto_degrade_on_redis_quota_exceeded():
        return False
    return redis_quota_degraded()


def worker_runtime_required() -> bool:
    return worker_required() and (not _worker_degraded_due_redis_quota())


def inline_fallback_enabled() -> bool:
    return _bool_env("WORKER_INLINE_FALLBACK_ENABLED", default=True)


def _worker_redis_tls_required() -> bool:
    raw = (os.getenv("REDIS_SSL_REQUIRED") or "").strip()
    if raw:
        return raw.lower() in {"1", "true", "yes", "on"}
    return managed_services_required()


def _broker_url() -> str:
    return (
        os.getenv("CELERY_BROKER_URL")
        or os.getenv("WORKER_BROKER_URL")
        or os.getenv("REDIS_URL")
        or ""
    ).strip()


def _backend_url() -> str:
    return (
        os.getenv("CELERY_RESULT_BACKEND")
        or os.getenv("WORKER_RESULT_BACKEND")
        or os.getenv("REDIS_URL")
        or ""
    ).strip()


def _transport_url_parts(value: str | None) -> SplitResult:
    return split_url(value or "")


def _transport_status(value: str | None) -> dict[str, Any]:
    parts = _transport_url_parts(value)
    scheme = str(parts.scheme or "").strip().lower() or None
    host = normalize_host(parts.hostname)
    return {
        "configured": bool(str(value or "").strip()),
        "scheme": scheme,
        "host": host,
        "remote_host": is_remote_service_host(host),
        "tls_enabled": scheme == "rediss",
    }


def get_celery_app():
    global _celery_app
    if _celery_app is not None:
        return _celery_app
    if Celery is None:
        return None

    broker = _broker_url()
    if not broker:
        return None

    backend = _backend_url() or broker
    if _worker_redis_tls_required():
        if _transport_status(broker).get("tls_enabled") is not True:
            return None
        if _transport_status(backend).get("tls_enabled") is not True:
            return None
    install_socket_dns_fallback()
    app = Celery("smartcampus", broker=broker, backend=backend)
    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        task_track_started=True,
        task_time_limit=int(os.getenv("WORKER_TASK_TIME_LIMIT_SECONDS", "60")),
    )
    transport_options = _celery_transport_options()
    app.conf.broker_transport_options = dict(transport_options)
    app.conf.result_backend_transport_options = dict(transport_options)
    if _worker_redis_tls_required():
        ssl_options = {"ssl_cert_reqs": _ssl_cert_reqs_setting()}
        app.conf.broker_use_ssl = dict(ssl_options)
        app.conf.redis_backend_use_ssl = dict(ssl_options)
    _celery_app = app
    return app


def worker_ready() -> bool:
    return get_celery_app() is not None


def worker_live(timeout_seconds: float = 2.0) -> bool:
    app = get_celery_app()
    if app is None:
        return False
    try:
        inspector = app.control.inspect(timeout=max(0.2, float(timeout_seconds)))
        ping = inspector.ping() if inspector is not None else None
        return bool(ping)
    except Exception:  # noqa: BLE001
        return False


def worker_transport_status() -> dict[str, Any]:
    broker_url = _broker_url()
    backend_url = _backend_url() or broker_url
    return {
        "tls_required": _worker_redis_tls_required(),
        "broker": _transport_status(broker_url),
        "backend": _transport_status(backend_url),
    }


def assert_worker_ready() -> None:
    if not worker_required():
        return
    if _worker_degraded_due_redis_quota():
        logger.warning(
            "Worker startup requirement temporarily bypassed because Redis monthly quota is exhausted."
        )
        return
    if not worker_ready():
        raise RuntimeError(
            "WORKER_REQUIRED=true but Celery broker/backend is not configured or unavailable."
        )

    attempts = _worker_startup_max_attempts()
    retry_delay_seconds = _worker_startup_retry_delay_seconds()
    ping_timeout_seconds = _worker_startup_ping_timeout_seconds()
    for attempt in range(1, attempts + 1):
        if worker_live(timeout_seconds=ping_timeout_seconds):
            return
        if attempt < attempts:
            logger.warning(
                "Worker ping failed during startup (%s/%s). Retrying in %.1fs.",
                attempt,
                attempts,
                retry_delay_seconds,
            )
            if retry_delay_seconds > 0:
                pytime.sleep(retry_delay_seconds)
    raise RuntimeError(
        "WORKER_REQUIRED=true but no active Celery worker responded to ping "
        f"after {attempts} startup checks."
    )


def _send_login_otp_task(destination_email: str, otp_code: str) -> dict[str, Any]:
    return send_login_otp(destination_email, otp_code)


def _send_notification_task(payload: dict[str, Any]) -> dict[str, Any]:
    logger.info("Notification task processed", extra={"payload": payload})
    return {"status": "sent", "payload": payload}


def _face_reverify_task(payload: dict[str, Any]) -> dict[str, Any]:
    logger.info("Face verification recomputation task processed", extra={"payload": payload})
    return {"status": "accepted", "payload": payload}


def _recompute_task(payload: dict[str, Any]) -> dict[str, Any]:
    logger.info("Recompute task processed", extra={"payload": payload})
    return {"status": "accepted", "payload": payload}


def _send_task(task_name: str, kwargs: dict[str, Any]) -> bool:
    app = get_celery_app()
    if app is None:
        return False
    try:
        app.send_task(task_name, kwargs=kwargs)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Celery enqueue failed task=%s error=%s", task_name, exc)
        return False


def _validated_otp_delivery_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise RuntimeError("OTP delivery returned an invalid payload.")
    channel = str(payload.get("channel") or "").strip()
    if channel not in _OTP_DELIVERY_CHANNELS:
        raise RuntimeError("OTP delivery returned an invalid delivery channel.")
    return {"channel": channel}


def dispatch_login_otp(
    destination_email: str,
    otp_code: str,
    *,
    timeout_seconds: int,
) -> dict[str, Any]:
    otp_worker_enabled = _bool_env("WORKER_ENABLE_OTP", default=True)
    if not otp_worker_enabled:
        raise RuntimeError("WORKER_ENABLE_OTP must remain true because OTP delivery is mandatory.")
    if not _otp_wait_for_result():
        raise RuntimeError(
            "WORKER_WAIT_FOR_OTP_RESULT must remain true because OTP requests must confirm delivery before succeeding."
        )

    # Login OTP is a user-blocking action. By default, send it directly through
    # the verified delivery backend instead of depending on worker/result-backend health.
    if _otp_direct_sync_enabled():
        payload = _send_login_otp_task(destination_email, otp_code)
        return _validated_otp_delivery_payload(payload)

    required = worker_runtime_required()
    # OTP inline fallback is only allowed outside strict runtime mode.
    fallback_enabled = (
        (not _app_runtime_strict_enabled())
        and (not _running_under_pytest())
        and _otp_inline_fallback_runtime_allowed()
        and inline_fallback_enabled()
        and _otp_inline_fallback_enabled()
    ) or _worker_degraded_due_redis_quota()

    def _run_inline_fallback(reason: str) -> dict[str, Any]:
        if required or not fallback_enabled:
            raise RuntimeError(reason)
        payload = _send_login_otp_task(destination_email, otp_code)
        try:
            return _validated_otp_delivery_payload(payload)
        except RuntimeError as exc:
            raise RuntimeError("OTP inline fallback returned an invalid delivery channel.") from exc

    # In local/dev mode we prefer inline delivery when worker health is unstable,
    # so login is not blocked by queue latency.
    if fallback_enabled and not required and not worker_live(timeout_seconds=0.6):
        return _run_inline_fallback("OTP worker is not live.")

    app = get_celery_app()
    if app is None:
        return _run_inline_fallback("OTP worker backend is unavailable.")

    try:
        result = app.send_task(
            TASK_SEND_OTP,
            kwargs={"destination_email": destination_email, "otp_code": otp_code},
        )
    except Exception as exc:  # noqa: BLE001
        return _run_inline_fallback(f"OTP worker enqueue failed: {exc}")

    def _get_result_with_retry() -> dict[str, Any]:
        attempts = max(1, int(os.getenv("WORKER_RESULT_MAX_ATTEMPTS", "2")))
        delay = float(os.getenv("WORKER_RESULT_RETRY_DELAY_SECONDS", "0.4") or 0.4)
        timeout = max(3, int(timeout_seconds))
        last_exc: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                payload = result.get(timeout=timeout)
                return payload
            except FuturesTimeoutError as exc:
                last_exc = exc
                if attempt >= attempts:
                    raise
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt >= attempts or not _is_transient_redis_error(exc):
                    raise
            if delay > 0:
                pytime.sleep(delay)
        if last_exc:
            raise last_exc
        raise RuntimeError("OTP worker result unavailable.")

    try:
        payload = _get_result_with_retry()
    except FuturesTimeoutError:
        return _run_inline_fallback(f"OTP delivery timed out after {timeout_seconds} seconds.")
    except Exception as exc:  # noqa: BLE001
        return _run_inline_fallback(f"OTP worker execution failed: {exc}")

    try:
        return _validated_otp_delivery_payload(payload)
    except RuntimeError as exc:
        return _run_inline_fallback(str(exc))


def enqueue_notification(payload: dict[str, Any]) -> str:
    enabled = _bool_env("WORKER_ENABLE_NOTIFICATIONS", default=True)
    required = worker_runtime_required()
    fallback_enabled = inline_fallback_enabled() or _worker_degraded_due_redis_quota()
    if required and not enabled:
        raise RuntimeError("WORKER_REQUIRED=true but WORKER_ENABLE_NOTIFICATIONS=false.")
    if enabled:
        if _send_task(TASK_NOTIFY, {"payload": payload}):
            return "celery"
        if required or not fallback_enabled:
            raise RuntimeError("Notification worker enqueue failed and inline fallback is disabled.")
    if required or not fallback_enabled:
        raise RuntimeError("Notification worker is required but unavailable.")
    _executor.submit(_send_notification_task, payload)
    return "inline-thread"


def enqueue_face_reverification(payload: dict[str, Any]) -> str:
    enabled = _bool_env("WORKER_ENABLE_FACE_REVERIFY", default=True)
    required = worker_runtime_required()
    fallback_enabled = inline_fallback_enabled() or _worker_degraded_due_redis_quota()
    if required and not enabled:
        raise RuntimeError("WORKER_REQUIRED=true but WORKER_ENABLE_FACE_REVERIFY=false.")
    if enabled:
        if _send_task(TASK_FACE_REVERIFY, {"payload": payload}):
            return "celery"
        if required or not fallback_enabled:
            raise RuntimeError("Face reverify worker enqueue failed and inline fallback is disabled.")
    if required or not fallback_enabled:
        raise RuntimeError("Face reverify worker is required but unavailable.")
    _executor.submit(_face_reverify_task, payload)
    return "inline-thread"


def enqueue_recompute(payload: dict[str, Any]) -> str:
    enabled = _bool_env("WORKER_ENABLE_RECOMPUTE", default=True)
    required = worker_runtime_required()
    fallback_enabled = inline_fallback_enabled() or _worker_degraded_due_redis_quota()
    if required and not enabled:
        raise RuntimeError("WORKER_REQUIRED=true but WORKER_ENABLE_RECOMPUTE=false.")
    if enabled:
        if _send_task(TASK_RECOMPUTE, {"payload": payload}):
            return "celery"
        if required or not fallback_enabled:
            raise RuntimeError("Recompute worker enqueue failed and inline fallback is disabled.")
    if required or not fallback_enabled:
        raise RuntimeError("Recompute worker is required but unavailable.")
    _executor.submit(_recompute_task, payload)
    return "inline-thread"


celery_app = get_celery_app()
if celery_app is not None:

    @celery_app.task(name=TASK_SEND_OTP)
    def send_login_otp_task(destination_email: str, otp_code: str) -> dict[str, Any]:
        return _send_login_otp_task(destination_email, otp_code)

    @celery_app.task(name=TASK_NOTIFY)
    def send_notification_task(payload: dict[str, Any]) -> dict[str, Any]:
        return _send_notification_task(payload)

    @celery_app.task(name=TASK_FACE_REVERIFY)
    def face_reverify_task(payload: dict[str, Any]) -> dict[str, Any]:
        return _face_reverify_task(payload)

    @celery_app.task(name=TASK_RECOMPUTE)
    def recompute_task(payload: dict[str, Any]) -> dict[str, Any]:
        return _recompute_task(payload)
