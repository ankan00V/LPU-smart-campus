import json
import logging
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime
from typing import Any
from urllib.parse import SplitResult

from . import models
from .database import SessionLocal, add_after_commit_hook
from .observability import record_notification_delivery_attempt
from .otp_delivery import send_login_otp, send_transactional_email
from .runtime_infra import (
    app_env,
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
_AUTOBOOT_STATE_DIR = Path(__file__).resolve().parent.parent / ".runtime"
_AUTOBOOT_PID_FILE = _AUTOBOOT_STATE_DIR / "celery-autoboot.pid"
_AUTOBOOT_LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "celery-autoboot.log"


def _bool_env(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name, "true" if default else "false") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _otp_wait_for_result() -> bool:
    return _bool_env("WORKER_WAIT_FOR_OTP_RESULT", default=True)


def worker_required() -> bool:
    return _bool_env("WORKER_REQUIRED", default=False)


def inline_fallback_enabled() -> bool:
    return _bool_env("WORKER_INLINE_FALLBACK_ENABLED", default=True)


def _worker_autoboot_enabled() -> bool:
    raw = (os.getenv("WORKER_AUTO_BOOTSTRAP") or "").strip()
    if raw:
        return raw.lower() in {"1", "true", "yes", "on"}
    return app_env() not in {"prod", "production"}


def _autoboot_timeout_seconds() -> float:
    raw = (os.getenv("WORKER_AUTO_BOOTSTRAP_TIMEOUT_SECONDS", "20") or "").strip()
    try:
        value = float(raw)
    except ValueError:
        value = 20.0
    return max(3.0, min(60.0, value))


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(int(pid), 0)
    except (OSError, ValueError):
        return False
    return True


def _read_autoboot_pid() -> int | None:
    try:
        raw = _AUTOBOOT_PID_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    except OSError:
        return None
    try:
        pid = int(raw)
    except ValueError:
        return None
    return pid if pid > 0 else None


def _clear_autoboot_pid_file() -> None:
    try:
        _AUTOBOOT_PID_FILE.unlink()
    except FileNotFoundError:
        return
    except OSError:
        logger.warning("Failed to remove worker autoboot pid file", extra={"path": str(_AUTOBOOT_PID_FILE)})


def _write_autoboot_pid(pid: int) -> None:
    _AUTOBOOT_STATE_DIR.mkdir(parents=True, exist_ok=True)
    _AUTOBOOT_PID_FILE.write_text(str(int(pid)), encoding="utf-8")


def _ensure_autoboot_paths() -> None:
    _AUTOBOOT_STATE_DIR.mkdir(parents=True, exist_ok=True)
    _AUTOBOOT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def _spawn_worker_process() -> int:
    _ensure_autoboot_paths()
    env = dict(os.environ)
    env["SMARTCAMPUS_AUTOSTARTED_WORKER"] = "1"
    command = [
        sys.executable,
        "-m",
        "celery",
        "-A",
        "app.workers:celery_app",
        "worker",
        f"--loglevel={os.getenv('CELERY_LOG_LEVEL', 'INFO')}",
        f"--concurrency={os.getenv('CELERY_WORKER_CONCURRENCY', '2')}",
        f"--hostname={os.getenv('CELERY_WORKER_HOSTNAME', 'worker-autoboot@%h')}",
    ]
    with _AUTOBOOT_LOG_FILE.open("ab") as log_handle:
        process = subprocess.Popen(
            command,
            cwd=str(Path(__file__).resolve().parent.parent),
            env=env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
    _write_autoboot_pid(int(process.pid))
    logger.info(
        "Auto-started local Celery worker",
        extra={"pid": int(process.pid), "log_file": str(_AUTOBOOT_LOG_FILE)},
    )
    return int(process.pid)


def _wait_for_worker_live(*, timeout_seconds: float) -> bool:
    deadline = time.monotonic() + max(0.5, float(timeout_seconds))
    while time.monotonic() < deadline:
        if worker_live(timeout_seconds=0.5):
            return True
        time.sleep(0.5)
    return worker_live(timeout_seconds=0.5)


def _ensure_worker_bootstrapped() -> bool:
    if not worker_required():
        return False
    if worker_live(timeout_seconds=0.5):
        return True
    if not _worker_autoboot_enabled():
        return False

    existing_pid = _read_autoboot_pid()
    if existing_pid is not None and not _pid_alive(existing_pid):
        _clear_autoboot_pid_file()
        existing_pid = None

    if existing_pid is not None:
        if _wait_for_worker_live(timeout_seconds=min(5.0, _autoboot_timeout_seconds())):
            return True
        logger.warning(
            "Existing auto-bootstrapped worker pid did not become healthy; replacing it",
            extra={"pid": existing_pid},
        )
        _clear_autoboot_pid_file()
        existing_pid = None

    if existing_pid is None:
        try:
            _spawn_worker_process()
        except Exception:
            logger.exception("Automatic local worker bootstrap failed")
            return False

    return _wait_for_worker_live(timeout_seconds=_autoboot_timeout_seconds())


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
        if _ensure_worker_bootstrapped():
            return
        raise RuntimeError(
            "WORKER_REQUIRED=true but no active Celery worker responded to ping."
        )


def _otp_delivery_poll_interval_seconds() -> float:
    raw = (os.getenv("OTP_DELIVERY_POLL_INTERVAL_SECONDS", "0.25") or "").strip()
    try:
        value = float(raw)
    except ValueError:
        value = 0.25
    return max(0.05, min(1.0, value))


def _create_otp_delivery_confirmation(
    *,
    user_id: int,
    destination_email: str,
    purpose: str,
) -> str:
    delivery_token = secrets.token_hex(5)
    with SessionLocal() as db:
        row = models.AuthOTPDeliveryReceipt(
            delivery_token=delivery_token,
            user_id=int(user_id),
            destination=str(destination_email or "").strip(),
            purpose=str(purpose or "").strip() or "login",
            channel="worker-pending",
        )
        db.add(row)
        db.commit()
    return delivery_token


def _update_otp_delivery_record(
    delivery_token: str,
    *,
    status: str,
    channel: str | None = None,
    error: str | None = None,
) -> None:
    normalized_status = str(status or "").strip().lower() or "unknown"
    resolved_channel = str(channel or "").strip()
    if normalized_status == "processing":
        resolved_channel = "worker-processing"
    elif normalized_status == "failed":
        resolved_channel = "delivery-failed"
    elif not resolved_channel:
        resolved_channel = "worker-pending"

    with SessionLocal() as db:
        row = (
            db.query(models.AuthOTPDeliveryReceipt)
            .filter(models.AuthOTPDeliveryReceipt.delivery_token == str(delivery_token))
            .first()
        )
        if row is None:
            raise RuntimeError("OTP delivery confirmation record is missing.")
        row.channel = resolved_channel[:40]
        row.updated_at = datetime.utcnow()
        row.error_message = str(error).strip()[:600] if error else None
        db.flush()
        db.commit()

    if error:
        logger.warning(
            "OTP delivery worker state updated with failure",
            extra={"delivery_token": delivery_token, "error": str(error)[:1000]},
        )


def _wait_for_otp_delivery_confirmation(delivery_token: str, *, timeout_seconds: int) -> dict[str, Any]:
    deadline = time.monotonic() + max(3, int(timeout_seconds))
    poll_interval = _otp_delivery_poll_interval_seconds()
    pending_channels = {"worker-pending", "worker-processing"}
    while time.monotonic() < deadline:
        with SessionLocal() as db:
            row = (
                db.query(models.AuthOTPDeliveryReceipt)
                .filter(models.AuthOTPDeliveryReceipt.delivery_token == str(delivery_token))
                .first()
            )
        if row is not None:
            channel = str(row.channel or "").strip()
            if channel == "delivery-failed":
                raise RuntimeError("OTP worker reported delivery failure.")
            if channel and channel not in pending_channels:
                return {"channel": channel}
        time.sleep(poll_interval)

    with SessionLocal() as db:
        row = (
            db.query(models.AuthOTPDeliveryReceipt)
            .filter(models.AuthOTPDeliveryReceipt.delivery_token == str(delivery_token))
            .first()
        )
    if row is not None:
        channel = str(row.channel or "").strip()
        if channel == "delivery-failed":
            raise RuntimeError("OTP worker reported delivery failure.")
        if channel and channel not in pending_channels:
            return {"channel": channel}
    raise RuntimeError(f"OTP delivery timed out after {timeout_seconds} seconds.")


def _send_login_otp_task(
    destination_email: str,
    otp_code: str,
    *,
    delivery_token: str | None = None,
) -> dict[str, Any]:
    if delivery_token is not None:
        _update_otp_delivery_record(delivery_token, status="processing", channel="worker-processing")
    try:
        delivery = send_login_otp(destination_email, otp_code)
    except Exception as exc:
        if delivery_token is not None:
            try:
                _update_otp_delivery_record(
                    delivery_token,
                    status="failed",
                    channel="delivery-failed",
                    error=str(exc),
                )
            except Exception:  # noqa: BLE001
                logger.exception("Failed to persist OTP delivery failure state", extra={"delivery_token": delivery_token})
        raise

    if delivery_token is not None:
        _update_otp_delivery_record(
            delivery_token,
            status="sent",
            channel=str(delivery.get("channel") or "").strip() or "email",
        )
    return delivery


def _compact_text(value: Any, *, default: str = "", max_len: int | None = None) -> str:
    text = str(value or "").strip() or default
    if max_len is not None:
        return text[:max_len]
    return text


def _parse_iso_datetime(raw: Any) -> datetime | None:
    value = str(raw or "").strip()
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _format_datetime_label(raw: Any, *, default: str = "Not scheduled") -> str:
    dt = _parse_iso_datetime(raw)
    if dt is None:
        return _compact_text(raw, default=default)
    return dt.strftime("%d %b %Y %I:%M %p")


def _format_attendance_percent(raw: Any) -> str:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return "0.0%"
    return f"{value:.1f}%"


def _write_notification_log(
    db,
    *,
    student_id: int,
    sent_to: str,
    channel: str,
    message: str,
) -> models.NotificationLog:
    row = models.NotificationLog(
        student_id=int(student_id),
        message=_compact_text(message, max_len=500),
        channel=_compact_text(channel, default="worker-email", max_len=50),
        sent_to=_compact_text(sent_to, max_len=120),
    )
    db.add(row)
    db.flush()
    return row


def _mark_recovery_action_sent(db, *, action_id: int | None) -> None:
    if not action_id:
        return
    action = db.get(models.AttendanceRecoveryAction, int(action_id))
    if action is None:
        return
    if action.status in {
        models.AttendanceRecoveryActionStatus.CANCELLED,
        models.AttendanceRecoveryActionStatus.COMPLETED,
        models.AttendanceRecoveryActionStatus.SKIPPED,
    }:
        return
    action.status = models.AttendanceRecoveryActionStatus.SENT
    action.updated_at = datetime.utcnow()
    db.flush()


def _positive_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _normalize_notification_status(value: Any, *, default: str = "unknown") -> str:
    normalized = str(value or default).strip().lower().replace("-", "_")
    return normalized or default


def _notification_attempt_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for key in (
        "student_name",
        "registration_number",
        "course_id",
        "course_code",
        "course_title",
        "risk_level",
        "attendance_percent",
        "consecutive_absences",
        "missed_remedials",
        "summary",
        "recovery_due_at",
        "suggested_remedial",
        "office_hour_at",
        "message",
        "log_channel",
    ):
        value = payload.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                continue
            metadata[key] = cleaned
            continue
        metadata[key] = value
    return metadata


def _write_notification_delivery_attempt(
    db,
    *,
    payload: dict[str, Any],
    status: str,
    channel: str,
    attempt_number: int,
    error_message: str | None = None,
) -> models.NotificationDeliveryAttempt:
    row = models.NotificationDeliveryAttempt(
        student_id=_positive_int(payload.get("student_id")),
        recovery_action_id=_positive_int(payload.get("action_id")),
        notification_type=_compact_text(payload.get("type"), default="unknown", max_len=80),
        recipient_email=_compact_text(payload.get("recipient_email"), default="unknown@example.invalid", max_len=120),
        channel=_compact_text(channel, default="transactional-email", max_len=50),
        status=_normalize_notification_status(status),
        attempt_number=max(1, int(attempt_number or 1)),
        error_message=_compact_text(error_message, max_len=600) or None,
        metadata_json=json.dumps(
            _notification_attempt_metadata(payload),
            separators=(",", ":"),
            sort_keys=True,
        ),
    )
    db.add(row)
    db.flush()
    return row


def _recovery_notification_subject(payload: dict[str, Any]) -> str:
    notification_type = _compact_text(payload.get("type"))
    student_name = _compact_text(payload.get("student_name"), default="Student")
    course_code = _compact_text(payload.get("course_code"), default="Course")
    if notification_type == "attendance_recovery_parent_alert":
        return f"Attendance recovery escalation for {student_name} - {course_code}"
    return f"Attendance recovery action required for {student_name} - {course_code}"


def _recovery_notification_body(payload: dict[str, Any]) -> str:
    notification_type = _compact_text(payload.get("type"))
    student_name = _compact_text(payload.get("student_name"), default="Student")
    registration_number = _compact_text(payload.get("registration_number"), default="Not available")
    course_code = _compact_text(payload.get("course_code"), default="Course")
    course_title = _compact_text(payload.get("course_title"), default="Untitled course")
    risk_level = _compact_text(payload.get("risk_level"), default="watch").upper()
    attendance_percent = _format_attendance_percent(payload.get("attendance_percent"))
    consecutive_absences = int(payload.get("consecutive_absences") or 0)
    missed_remedials = int(payload.get("missed_remedials") or 0)
    summary = _compact_text(payload.get("summary"), default="Recovery plan has been updated.")
    suggested_remedial = _compact_text(
        payload.get("suggested_remedial"),
        default="No remedial slot is currently assigned.",
    )
    office_hour_at = _compact_text(
        payload.get("office_hour_at"),
        default="No office-hour check-in is currently scheduled.",
    )
    recovery_due_at = _format_datetime_label(payload.get("recovery_due_at"), default="No due date assigned")
    action_message = _compact_text(payload.get("message"), default=summary)

    intro = [
        "An attendance recovery intervention has been triggered.",
        "",
        f"Student: {student_name}",
        f"Registration: {registration_number}",
        f"Course: {course_code} - {course_title}",
        f"Risk level: {risk_level}",
        f"Attendance: {attendance_percent}",
        f"Consecutive absences: {consecutive_absences}",
        f"Missed remedials: {missed_remedials}",
        f"Recovery due by: {recovery_due_at}",
        "",
        f"Plan summary: {summary}",
        f"Recommended remedial slot: {suggested_remedial}",
        f"Suggested office-hour follow-up: {office_hour_at}",
        "",
        f"Action: {action_message}",
    ]
    if notification_type == "attendance_recovery_parent_alert":
        intro.extend(
            [
                "",
                "This alert was generated because the student has moved into a policy-approved critical attendance recovery state.",
                "Please coordinate with the student and the assigned faculty advisor to complete the recovery steps on time.",
            ]
        )
    else:
        intro.extend(
            [
                "",
                "Please review the recovery plan, follow up with the student, and confirm the next intervention step in the portal.",
            ]
        )
    return "\n".join(intro)


def _send_recovery_notification(payload: dict[str, Any], *, attempt_number: int = 1) -> dict[str, Any]:
    recipient_email = _compact_text(payload.get("recipient_email"))
    if not recipient_email:
        raise RuntimeError("Attendance recovery notification payload is missing recipient_email.")

    student_id = int(payload.get("student_id") or 0)
    if student_id <= 0:
        raise RuntimeError("Attendance recovery notification payload is missing student_id.")

    subject = _recovery_notification_subject(payload)
    body = _recovery_notification_body(payload)
    log_channel = _compact_text(
        payload.get("log_channel"),
        default="attendance-recovery-email",
        max_len=50,
    )
    log_message = _compact_text(payload.get("message"), default=subject, max_len=500)

    with SessionLocal() as db:
        existing_log = (
            db.query(models.NotificationLog)
            .filter(
                models.NotificationLog.student_id == student_id,
                models.NotificationLog.sent_to == recipient_email,
                models.NotificationLog.channel == log_channel,
                models.NotificationLog.message == log_message,
            )
            .order_by(models.NotificationLog.id.desc())
            .first()
        )
        if existing_log is not None:
            _mark_recovery_action_sent(db, action_id=payload.get("action_id"))
            _write_notification_delivery_attempt(
                db,
                payload=payload,
                status="already_sent",
                channel=log_channel,
                attempt_number=attempt_number,
            )
            db.commit()
            return {
                "status": "already_sent",
                "channel": log_channel,
                "recipient_email": recipient_email,
            }

    try:
        delivery = send_transactional_email(recipient_email, subject=subject, body=body)
    except Exception as exc:
        with SessionLocal() as db:
            _write_notification_delivery_attempt(
                db,
                payload=payload,
                status="failed",
                channel="transactional-email",
                attempt_number=attempt_number,
                error_message=str(exc),
            )
            db.commit()
        raise

    with SessionLocal() as db:
        _mark_recovery_action_sent(db, action_id=payload.get("action_id"))
        _write_notification_log(
            db,
            student_id=student_id,
            sent_to=recipient_email,
            channel=log_channel,
            message=log_message,
        )
        _write_notification_delivery_attempt(
            db,
            payload=payload,
            status="sent",
            channel=_compact_text(delivery.get("channel"), default="transactional-email", max_len=50),
            attempt_number=attempt_number,
        )
        db.commit()

    return {
        "status": "sent",
        "channel": _compact_text(delivery.get("channel"), default=log_channel),
        "recipient_email": recipient_email,
    }


def _saarthi_notification_subject(payload: dict[str, Any]) -> str:
    notification_type = _compact_text(payload.get("type"))
    student_name = _compact_text(payload.get("student_name"), default="Student")
    mandatory_date = _compact_text(payload.get("mandatory_date"), default="scheduled Sunday")
    course_code = _compact_text(payload.get("course_code"), default="CON111")
    if notification_type == "saarthi_missed_admin_alert":
        return f"Saarthi escalation required for {student_name} - {course_code} - {mandatory_date}"
    return f"Missed mandatory Saarthi counselling - {course_code} - {mandatory_date}"


def _saarthi_notification_body(payload: dict[str, Any]) -> str:
    notification_type = _compact_text(payload.get("type"))
    student_name = _compact_text(payload.get("student_name"), default="Student")
    registration_number = _compact_text(payload.get("registration_number"), default="Not available")
    course_code = _compact_text(payload.get("course_code"), default="CON111")
    course_title = _compact_text(payload.get("course_title"), default="Councelling and Happiness")
    faculty_name = _compact_text(payload.get("faculty_name"), default="Saarthi (AI Mentor)")
    mandatory_date = _compact_text(payload.get("mandatory_date"), default="scheduled Sunday")
    week_start_date = _compact_text(payload.get("week_start_date"), default="this week")
    section = _compact_text(payload.get("section"), default="Unknown")
    department = _compact_text(payload.get("department"), default="Unknown")
    message_count = int(payload.get("message_count") or 0)
    last_message_at = _format_datetime_label(payload.get("last_message_at"), default="No prior messages recorded")

    if notification_type == "saarthi_missed_admin_alert":
        return "\n".join(
            [
                "A student missed the mandatory Saarthi Sunday counselling check-in.",
                "",
                f"Student: {student_name}",
                f"Registration: {registration_number}",
                f"Department/Section: {department} / {section}",
                f"Course: {course_code} - {course_title}",
                f"Faculty: {faculty_name}",
                f"Week start: {week_start_date}",
                f"Mandatory Sunday: {mandatory_date}",
                f"Transcript activity this week: {message_count} message(s)",
                f"Last Saarthi activity: {last_message_at}",
                "",
                "Attendance impact: the student has been marked absent for this week's mandatory CON111 counselling slot.",
                "Action: review the student's engagement and follow up if additional intervention is required.",
            ]
        )

    return "\n".join(
        [
            f"You missed the mandatory Saarthi Sunday counselling check-in on {mandatory_date}.",
            "",
            f"Course: {course_code} - {course_title}",
            f"Faculty: {faculty_name}",
            f"Week start: {week_start_date}",
            "",
            "Attendance impact: CON111 has been marked absent for that Sunday. Chatting with Saarthi on other days is still available, but attendance can only be credited once on the mandatory Sunday.",
            "Next step: complete the next Sunday Saarthi session to secure the next weekly 1-hour attendance credit.",
        ]
    )


def _send_saarthi_notification(payload: dict[str, Any], *, attempt_number: int = 1) -> dict[str, Any]:
    recipient_email = _compact_text(payload.get("recipient_email"))
    if not recipient_email:
        raise RuntimeError("Saarthi notification payload is missing recipient_email.")

    student_id = int(payload.get("student_id") or 0)
    if student_id <= 0:
        raise RuntimeError("Saarthi notification payload is missing student_id.")

    subject = _saarthi_notification_subject(payload)
    body = _saarthi_notification_body(payload)
    log_channel = _compact_text(
        payload.get("log_channel"),
        default="saarthi-missed-email",
        max_len=50,
    )
    log_message = _compact_text(payload.get("message"), default=subject, max_len=500)

    with SessionLocal() as db:
        existing_log = (
            db.query(models.NotificationLog)
            .filter(
                models.NotificationLog.student_id == student_id,
                models.NotificationLog.sent_to == recipient_email,
                models.NotificationLog.channel == log_channel,
                models.NotificationLog.message == log_message,
            )
            .order_by(models.NotificationLog.id.desc())
            .first()
        )
        if existing_log is not None:
            _write_notification_delivery_attempt(
                db,
                payload=payload,
                status="already_sent",
                channel=log_channel,
                attempt_number=attempt_number,
            )
            db.commit()
            return {
                "status": "already_sent",
                "channel": log_channel,
                "recipient_email": recipient_email,
            }

    try:
        delivery = send_transactional_email(recipient_email, subject=subject, body=body)
    except Exception as exc:
        with SessionLocal() as db:
            _write_notification_delivery_attempt(
                db,
                payload=payload,
                status="failed",
                channel="transactional-email",
                attempt_number=attempt_number,
                error_message=str(exc),
            )
            db.commit()
        raise

    with SessionLocal() as db:
        _write_notification_log(
            db,
            student_id=student_id,
            sent_to=recipient_email,
            channel=log_channel,
            message=log_message,
        )
        _write_notification_delivery_attempt(
            db,
            payload=payload,
            status="sent",
            channel=_compact_text(delivery.get("channel"), default="transactional-email", max_len=50),
            attempt_number=attempt_number,
        )
        db.commit()

    return {
        "status": "sent",
        "channel": _compact_text(delivery.get("channel"), default=log_channel),
        "recipient_email": recipient_email,
    }


def _send_notification_task(payload: dict[str, Any], *, attempt_number: int = 1) -> dict[str, Any]:
    notification_type = _compact_text(payload.get("type"))
    if notification_type in {
        "attendance_recovery_faculty_alert",
        "attendance_recovery_parent_alert",
    }:
        started = time.perf_counter()
        try:
            result = _send_recovery_notification(payload, attempt_number=max(1, int(attempt_number or 1)))
        except Exception:
            record_notification_delivery_attempt(
                notification_type=notification_type,
                channel="transactional-email",
                status="failed",
                duration_seconds=time.perf_counter() - started,
            )
            logger.exception(
                "Attendance recovery notification delivery failed",
                extra={"payload": payload, "attempt_number": attempt_number},
            )
            raise
        record_notification_delivery_attempt(
            notification_type=notification_type,
            channel=_compact_text(result.get("channel"), default="transactional-email"),
            status=_normalize_notification_status(result.get("status"), default="sent"),
            duration_seconds=time.perf_counter() - started,
        )
        logger.info(
            "Attendance recovery notification delivered",
            extra={"payload": payload, "result": result, "attempt_number": attempt_number},
        )
        return result
    if notification_type in {
        "saarthi_missed_student_alert",
        "saarthi_missed_admin_alert",
    }:
        started = time.perf_counter()
        try:
            result = _send_saarthi_notification(payload, attempt_number=max(1, int(attempt_number or 1)))
        except Exception:
            record_notification_delivery_attempt(
                notification_type=notification_type,
                channel="transactional-email",
                status="failed",
                duration_seconds=time.perf_counter() - started,
            )
            logger.exception(
                "Saarthi missed notification delivery failed",
                extra={"payload": payload, "attempt_number": attempt_number},
            )
            raise
        record_notification_delivery_attempt(
            notification_type=notification_type,
            channel=_compact_text(result.get("channel"), default="transactional-email"),
            status=_normalize_notification_status(result.get("status"), default="sent"),
            duration_seconds=time.perf_counter() - started,
        )
        logger.info(
            "Saarthi missed notification delivered",
            extra={"payload": payload, "result": result, "attempt_number": attempt_number},
        )
        return result
    logger.info("Notification task accepted without external delivery handler", extra={"payload": payload})
    return {"status": "accepted", "payload": payload}


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
    user_id: int,
    purpose: str = "login",
) -> dict[str, Any]:
    otp_worker_enabled = _bool_env("WORKER_ENABLE_OTP", default=True)
    if not otp_worker_enabled:
        raise RuntimeError("WORKER_ENABLE_OTP must remain true because OTP delivery is mandatory.")

    delivery_token = _create_otp_delivery_confirmation(
        user_id=int(user_id),
        destination_email=destination_email,
        purpose=purpose,
    )
    try:
        _update_otp_delivery_record(
            delivery_token,
            status="processing",
            channel="smtp-processing",
        )
        payload = send_login_otp(destination_email, otp_code)
    except Exception as exc:  # noqa: BLE001
        try:
            _update_otp_delivery_record(
                delivery_token,
                status="failed",
                channel="delivery-failed",
                error=f"OTP delivery failed: {exc}",
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to persist OTP delivery failure state", extra={"delivery_token": delivery_token})
        raise RuntimeError(f"OTP delivery failed: {exc}") from exc

    channel = str(payload.get("channel") or "").strip() if isinstance(payload, dict) else ""
    if not channel:
        try:
            _update_otp_delivery_record(
                delivery_token,
                status="failed",
                channel="delivery-failed",
                error="OTP delivery returned an invalid channel.",
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to persist invalid OTP delivery payload", extra={"delivery_token": delivery_token})
        raise RuntimeError("OTP delivery returned an invalid channel.")

    try:
        _update_otp_delivery_record(
            delivery_token,
            status="sent",
            channel=channel,
        )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"OTP delivery confirmation persistence failed: {exc}") from exc

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


def enqueue_notification_after_commit(db, payload: dict[str, Any]) -> None:
    frozen_payload = dict(payload)

    def _dispatch() -> None:
        try:
            enqueue_notification(frozen_payload)
        except Exception:  # noqa: BLE001
            logger.exception(
                "Post-commit notification enqueue failed",
                extra={"payload": frozen_payload},
            )

    add_after_commit_hook(db, _dispatch)


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

    @celery_app.task(name=TASK_SEND_OTP, ignore_result=True)
    def send_login_otp_task(
        destination_email: str,
        otp_code: str,
        delivery_token: str | None = None,
    ) -> dict[str, Any]:
        return _send_login_otp_task(destination_email, otp_code, delivery_token=delivery_token)

    @celery_app.task(
        name=TASK_NOTIFY,
        bind=True,
        autoretry_for=(Exception,),
        retry_backoff=max(1, int(os.getenv("WORKER_NOTIFICATION_RETRY_BACKOFF_SECONDS", "30"))),
        retry_backoff_max=max(30, int(os.getenv("WORKER_NOTIFICATION_RETRY_BACKOFF_MAX_SECONDS", "300"))),
        retry_jitter=True,
        retry_kwargs={
            "max_retries": max(0, int(os.getenv("WORKER_NOTIFICATION_MAX_RETRIES", "3"))),
        },
    )
    def send_notification_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        attempt_number = int(getattr(getattr(self, "request", None), "retries", 0) or 0) + 1
        return _send_notification_task(payload, attempt_number=attempt_number)

    @celery_app.task(name=TASK_FACE_REVERIFY)
    def face_reverify_task(payload: dict[str, Any]) -> dict[str, Any]:
        return _face_reverify_task(payload)

    @celery_app.task(name=TASK_RECOMPUTE)
    def recompute_task(payload: dict[str, Any]) -> dict[str, Any]:
        return _recompute_task(payload)
