import logging
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any
from urllib.parse import SplitResult

from .otp_delivery import send_login_otp
from .runtime_infra import (
    is_remote_service_host,
    managed_services_required,
    normalize_host,
    split_url,
)

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    from celery import Celery
except Exception:  # noqa: BLE001
    Celery = None


TASK_SEND_OTP = "smartcampus.tasks.send_login_otp"
TASK_NOTIFY = "smartcampus.tasks.send_notification"
TASK_FACE_REVERIFY = "smartcampus.tasks.face_reverify"
TASK_RECOMPUTE = "smartcampus.tasks.recompute"

_executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="smartcampus-worker")
_celery_app = None


def _bool_env(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name, "true" if default else "false") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _otp_wait_for_result() -> bool:
    return _bool_env("WORKER_WAIT_FOR_OTP_RESULT", default=True)


def worker_required() -> bool:
    return _bool_env("WORKER_REQUIRED", default=False)


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
    app = Celery("smartcampus", broker=broker, backend=backend)
    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        task_track_started=True,
        task_time_limit=int(os.getenv("WORKER_TASK_TIME_LIMIT_SECONDS", "60")),
    )
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
    if not worker_ready():
        raise RuntimeError(
            "WORKER_REQUIRED=true but Celery broker/backend is not configured or unavailable."
        )
    if not worker_live():
        raise RuntimeError(
            "WORKER_REQUIRED=true but no active Celery worker responded to ping."
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

    app = get_celery_app()
    if app is None:
        raise RuntimeError("OTP worker backend is unavailable.")

    try:
        result = app.send_task(
            TASK_SEND_OTP,
            kwargs={"destination_email": destination_email, "otp_code": otp_code},
        )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"OTP worker enqueue failed: {exc}") from exc

    try:
        payload = result.get(timeout=max(3, int(timeout_seconds)))
    except FuturesTimeoutError as exc:
        raise RuntimeError(f"OTP delivery timed out after {timeout_seconds} seconds.") from exc
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"OTP worker execution failed: {exc}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("OTP worker returned an invalid payload.")

    channel = str(payload.get("channel") or "").strip()
    if not channel:
        raise RuntimeError("OTP worker returned an invalid delivery channel.")

    return {"channel": channel}


def enqueue_notification(payload: dict[str, Any]) -> str:
    enabled = _bool_env("WORKER_ENABLE_NOTIFICATIONS", default=True)
    required = worker_required()
    fallback_enabled = inline_fallback_enabled()
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
    required = worker_required()
    fallback_enabled = inline_fallback_enabled()
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
    required = worker_required()
    fallback_enabled = inline_fallback_enabled()
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
