from __future__ import annotations

import logging
import os
import socket
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models
from .database import SessionLocal
from .observability import record_scheduler_job_run
from .saarthi_service import queue_saarthi_missed_notifications_for_reference

logger = logging.getLogger(__name__)

_INSTANCE_ID = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:10]}"
_STATE_LOCK = threading.Lock()
_SCHEDULER_THREAD: threading.Thread | None = None
_SCHEDULER_STOP_EVENT = threading.Event()
_SCHEDULER_STARTED_AT: str | None = None
_SCHEDULER_STOPPED_AT: str | None = None
_LAST_TICK_AT: str | None = None
_JOB_STATE: dict[str, dict[str, Any]] = {}


@dataclass(frozen=True)
class SchedulerJob:
    name: str
    interval_seconds: int
    runner: Callable[[Session, datetime], dict[str, Any]]


def _bool_env(name: str, default: bool) -> bool:
    raw = (os.getenv(name, "true" if default else "false") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def scheduler_enabled() -> bool:
    raw = (os.getenv("APP_INTERNAL_SCHEDULER_ENABLED") or "").strip()
    if raw:
        return raw.lower() in {"1", "true", "yes", "on"}
    if os.getenv("PYTEST_CURRENT_TEST"):
        return False
    return True


def _env_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = (os.getenv(name, str(default)) or "").strip()
    try:
        value = int(raw)
    except ValueError:
        value = int(default)
    return max(minimum, min(maximum, value))


def scheduler_poll_seconds() -> int:
    return _env_int("APP_INTERNAL_SCHEDULER_POLL_SECONDS", 30, minimum=5, maximum=900)


def scheduler_initial_delay_seconds() -> int:
    return _env_int("APP_INTERNAL_SCHEDULER_INITIAL_DELAY_SECONDS", 15, minimum=0, maximum=1800)


def _scheduler_lease_seconds() -> int:
    return _env_int("APP_INTERNAL_SCHEDULER_LEASE_SECONDS", 900, minimum=30, maximum=7200)


def _scheduler_failure_retry_seconds() -> int:
    return _env_int("APP_INTERNAL_SCHEDULER_FAILURE_RETRY_SECONDS", 300, minimum=30, maximum=3600)


def _saarthi_sweep_interval_seconds() -> int:
    return _env_int("APP_INTERNAL_SCHEDULER_SAARTHI_SWEEP_INTERVAL_SECONDS", 3600, minimum=300, maximum=86400)


def _scheduler_timezone_name() -> str:
    return (
        (os.getenv("APP_INTERNAL_SCHEDULER_TIMEZONE") or "").strip()
        or (os.getenv("APP_TIMEZONE") or "").strip()
        or "Asia/Kolkata"
    )


def _scheduler_timezone() -> ZoneInfo:
    name = _scheduler_timezone_name()
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        logger.warning("Invalid APP_INTERNAL_SCHEDULER_TIMEZONE=%s. Falling back to Asia/Kolkata.", name)
        return ZoneInfo("Asia/Kolkata")


def _registered_jobs() -> list[SchedulerJob]:
    return [
        SchedulerJob(
            name="saarthi_missed_notifications",
            interval_seconds=_saarthi_sweep_interval_seconds(),
            runner=_run_saarthi_missed_notifications_job,
        )
    ]


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _utc_naive(now_utc: datetime | None = None) -> datetime:
    effective = now_utc or _now_utc()
    return effective.astimezone(timezone.utc).replace(tzinfo=None)


def _isoformat(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None:
        return None
    return str(value)


def _update_job_state(job_name: str, **changes: Any) -> None:
    with _STATE_LOCK:
        current = dict(_JOB_STATE.get(job_name) or {})
        current.update(changes)
        _JOB_STATE[job_name] = current


def _claim_job(job: SchedulerJob, *, now_dt: datetime) -> bool:
    lease_expires_at = now_dt + timedelta(seconds=_scheduler_lease_seconds())
    next_due_at = lease_expires_at
    update_payload = {
        models.SchedulerLease.owner_id: _INSTANCE_ID,
        models.SchedulerLease.lease_expires_at: lease_expires_at,
        models.SchedulerLease.next_due_at: next_due_at,
        models.SchedulerLease.heartbeat_at: now_dt,
        models.SchedulerLease.last_started_at: now_dt,
        models.SchedulerLease.last_status: "running",
        models.SchedulerLease.last_error: None,
        models.SchedulerLease.updated_at: now_dt,
    }

    with SessionLocal() as db:
        updated = (
            db.query(models.SchedulerLease)
            .filter(
                models.SchedulerLease.job_name == job.name,
                or_(
                    models.SchedulerLease.next_due_at.is_(None),
                    models.SchedulerLease.next_due_at <= now_dt,
                ),
                or_(
                    models.SchedulerLease.lease_expires_at.is_(None),
                    models.SchedulerLease.lease_expires_at <= now_dt,
                    models.SchedulerLease.owner_id == _INSTANCE_ID,
                ),
            )
            .update(update_payload, synchronize_session=False)
        )
        if updated:
            db.commit()
            return True

        db.add(
            models.SchedulerLease(
                job_name=job.name,
                owner_id=_INSTANCE_ID,
                lease_expires_at=lease_expires_at,
                next_due_at=next_due_at,
                heartbeat_at=now_dt,
                last_started_at=now_dt,
                last_status="running",
                last_error=None,
                created_at=now_dt,
                updated_at=now_dt,
            )
        )
        try:
            db.commit()
            return True
        except IntegrityError:
            db.rollback()

        updated = (
            db.query(models.SchedulerLease)
            .filter(
                models.SchedulerLease.job_name == job.name,
                or_(
                    models.SchedulerLease.next_due_at.is_(None),
                    models.SchedulerLease.next_due_at <= now_dt,
                ),
                or_(
                    models.SchedulerLease.lease_expires_at.is_(None),
                    models.SchedulerLease.lease_expires_at <= now_dt,
                    models.SchedulerLease.owner_id == _INSTANCE_ID,
                ),
            )
            .update(update_payload, synchronize_session=False)
        )
        if not updated:
            db.rollback()
            return False
        db.commit()
        return True


def _finalize_job(
    job: SchedulerJob,
    *,
    completed_at: datetime,
    status: str,
    error_message: str | None = None,
) -> None:
    success_due_at = completed_at + timedelta(seconds=max(1, int(job.interval_seconds)))
    retry_due_at = completed_at + timedelta(seconds=_scheduler_failure_retry_seconds())
    with SessionLocal() as db:
        row = db.get(models.SchedulerLease, job.name)
        if row is None:
            return
        row.lease_expires_at = completed_at
        row.heartbeat_at = completed_at
        row.last_completed_at = completed_at
        row.last_status = str(status or "unknown").strip().lower() or "unknown"
        row.last_error = (str(error_message or "").strip()[:600] or None)
        row.updated_at = completed_at
        if row.last_status == "success":
            row.next_due_at = success_due_at
        else:
            row.next_due_at = retry_due_at
        db.commit()


def _run_saarthi_missed_notifications_job(db: Session, now_utc: datetime) -> dict[str, Any]:
    reference_date = now_utc.astimezone(_scheduler_timezone()).date()
    result = queue_saarthi_missed_notifications_for_reference(db, reference_date=reference_date)
    result["timezone"] = _scheduler_timezone_name()
    return result


def run_due_scheduler_jobs_once() -> dict[str, Any]:
    jobs = _registered_jobs()
    now_utc = _now_utc()
    now_dt = _utc_naive(now_utc)
    summaries: list[dict[str, Any]] = []
    ran_jobs = 0

    for job in jobs:
        _update_job_state(job.name, interval_seconds=int(job.interval_seconds))
        if not _claim_job(job, now_dt=now_dt):
            continue
        ran_jobs += 1
        started_perf = time.perf_counter()
        _update_job_state(
            job.name,
            last_started_at=_isoformat(now_utc),
            last_status="running",
            last_error=None,
            next_due_at=_isoformat(now_dt + timedelta(seconds=_scheduler_lease_seconds())),
        )
        try:
            with SessionLocal() as db:
                result = job.runner(db, now_utc)
                db.commit()
            completed_at = _utc_naive()
            duration_seconds = time.perf_counter() - started_perf
            _finalize_job(job, completed_at=completed_at, status="success")
            record_scheduler_job_run(job_name=job.name, status="success", duration_seconds=duration_seconds)
            _update_job_state(
                job.name,
                last_completed_at=_isoformat(completed_at),
                last_status="success",
                last_duration_seconds=round(float(duration_seconds), 6),
                last_result=result,
                last_error=None,
            )
            summaries.append({"job_name": job.name, "status": "success", "result": result})
            logger.info("Scheduler job completed", extra={"job_name": job.name, "result": result})
        except Exception as exc:  # noqa: BLE001
            completed_at = _utc_naive()
            duration_seconds = time.perf_counter() - started_perf
            _finalize_job(job, completed_at=completed_at, status="failed", error_message=str(exc))
            record_scheduler_job_run(job_name=job.name, status="failed", duration_seconds=duration_seconds)
            _update_job_state(
                job.name,
                last_completed_at=_isoformat(completed_at),
                last_status="failed",
                last_duration_seconds=round(float(duration_seconds), 6),
                last_result=None,
                last_error=str(exc),
                next_due_at=_isoformat(completed_at + timedelta(seconds=_scheduler_failure_retry_seconds())),
            )
            summaries.append({"job_name": job.name, "status": "failed", "error": str(exc)})
            logger.exception("Scheduler job failed", extra={"job_name": job.name})

    return {
        "instance_id": _INSTANCE_ID,
        "evaluated_jobs": len(jobs),
        "ran_jobs": ran_jobs,
        "jobs": summaries,
        "tick_at": _isoformat(now_utc),
    }


def _scheduler_loop() -> None:
    global _LAST_TICK_AT, _SCHEDULER_STOPPED_AT
    initial_delay = scheduler_initial_delay_seconds()
    if initial_delay > 0 and _SCHEDULER_STOP_EVENT.wait(initial_delay):
        with _STATE_LOCK:
            _SCHEDULER_STOPPED_AT = _isoformat(_now_utc())
        return

    while not _SCHEDULER_STOP_EVENT.is_set():
        try:
            result = run_due_scheduler_jobs_once()
            with _STATE_LOCK:
                _LAST_TICK_AT = str(result.get("tick_at") or _isoformat(_now_utc()))
        except Exception:  # noqa: BLE001
            logger.exception("Internal scheduler tick failed")
            record_scheduler_job_run(job_name="scheduler_loop", status="failed")
        if _SCHEDULER_STOP_EVENT.wait(scheduler_poll_seconds()):
            break

    with _STATE_LOCK:
        _SCHEDULER_STOPPED_AT = _isoformat(_now_utc())


def start_internal_scheduler() -> bool:
    global _SCHEDULER_THREAD, _SCHEDULER_STARTED_AT, _SCHEDULER_STOPPED_AT
    if not scheduler_enabled():
        logger.info("Internal scheduler is disabled by configuration")
        return False

    with _STATE_LOCK:
        if _SCHEDULER_THREAD is not None and _SCHEDULER_THREAD.is_alive():
            return True
        _SCHEDULER_STOP_EVENT.clear()
        _SCHEDULER_THREAD = threading.Thread(
            target=_scheduler_loop,
            name="smartcampus-internal-scheduler",
            daemon=True,
        )
        _SCHEDULER_STARTED_AT = _isoformat(_now_utc())
        _SCHEDULER_STOPPED_AT = None
        _SCHEDULER_THREAD.start()
    logger.info("Internal scheduler started", extra={"instance_id": _INSTANCE_ID})
    return True


def stop_internal_scheduler(timeout_seconds: float = 5.0) -> None:
    global _SCHEDULER_THREAD
    with _STATE_LOCK:
        thread = _SCHEDULER_THREAD
    if thread is None:
        return

    _SCHEDULER_STOP_EVENT.set()
    thread.join(timeout=max(0.2, float(timeout_seconds)))
    with _STATE_LOCK:
        if _SCHEDULER_THREAD is thread:
            _SCHEDULER_THREAD = None
    logger.info("Internal scheduler stopped", extra={"instance_id": _INSTANCE_ID})


def scheduler_status() -> dict[str, Any]:
    jobs = _registered_jobs()
    with _STATE_LOCK:
        thread = _SCHEDULER_THREAD
        job_state = {name: dict(value) for name, value in _JOB_STATE.items()}
        started_at = _SCHEDULER_STARTED_AT
        stopped_at = _SCHEDULER_STOPPED_AT
        last_tick_at = _LAST_TICK_AT

    serialized_jobs: list[dict[str, Any]] = []
    for job in jobs:
        current = job_state.get(job.name) or {}
        serialized_jobs.append(
            {
                "name": job.name,
                "interval_seconds": int(job.interval_seconds),
                "last_started_at": current.get("last_started_at"),
                "last_completed_at": current.get("last_completed_at"),
                "last_status": current.get("last_status") or "pending",
                "last_error": current.get("last_error"),
                "last_duration_seconds": current.get("last_duration_seconds"),
                "next_due_at": current.get("next_due_at"),
                "last_result": current.get("last_result"),
            }
        )

    return {
        "enabled": scheduler_enabled(),
        "running": bool(thread is not None and thread.is_alive()),
        "instance_id": _INSTANCE_ID,
        "timezone": _scheduler_timezone_name(),
        "poll_seconds": scheduler_poll_seconds(),
        "initial_delay_seconds": scheduler_initial_delay_seconds(),
        "lease_seconds": _scheduler_lease_seconds(),
        "failure_retry_seconds": _scheduler_failure_retry_seconds(),
        "started_at": started_at,
        "stopped_at": stopped_at,
        "last_tick_at": last_tick_at,
        "jobs": serialized_jobs,
    }
