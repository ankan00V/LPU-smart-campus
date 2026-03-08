from __future__ import annotations

import contextvars
import json
import logging
import os
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from decimal import Decimal
from threading import Lock
from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import PlainTextResponse

try:  # pragma: no cover - optional dependency in some local envs
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
except Exception:  # noqa: BLE001
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4"
    Counter = None
    Histogram = None
    generate_latest = None


logger = logging.getLogger(__name__)
trace_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="-")


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


class TraceIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = trace_id_ctx.get("-")
        return True


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "trace_id": getattr(record, "trace_id", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        for key in ("path", "method", "status_code", "duration_ms", "event"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, default=_json_default)


class ErrorBudgetTracker:
    def __init__(self) -> None:
        self._events: deque[tuple[float, bool]] = deque()
        self._lock = Lock()

    def add(self, *, ok: bool, timestamp: float | None = None) -> None:
        ts = timestamp if timestamp is not None else time.time()
        with self._lock:
            self._events.append((ts, ok))

    def snapshot(self, *, target: float, window_seconds: int) -> dict[str, Any]:
        now = time.time()
        oldest = now - max(60, int(window_seconds))
        with self._lock:
            while self._events and self._events[0][0] < oldest:
                self._events.popleft()
            total = len(self._events)
            errors = sum(1 for _, ok in self._events if not ok)

        success = max(0, total - errors)
        availability = (success / total) if total else 1.0
        error_rate = (errors / total) if total else 0.0
        budget = max(1e-9, 1.0 - target)
        burn_rate = error_rate / budget
        budget_remaining = max(0.0, 1.0 - burn_rate)

        alert_state = "healthy"
        if burn_rate >= 2.0:
            alert_state = "critical"
        elif burn_rate >= 1.0:
            alert_state = "warning"

        return {
            "window_seconds": int(window_seconds),
            "target_availability": round(float(target), 6),
            "observed_availability": round(float(availability), 6),
            "total_requests": int(total),
            "errors": int(errors),
            "error_rate": round(float(error_rate), 6),
            "budget_remaining_ratio": round(float(budget_remaining), 6),
            "burn_rate": round(float(burn_rate), 6),
            "alert_state": alert_state,
            "sampled_at": datetime.now(timezone.utc).isoformat(),
        }


REQUEST_COUNTER = (
    Counter(
        "smartcampus_http_requests_total",
        "HTTP requests",
        ["method", "path", "status"],
    )
    if Counter is not None
    else None
)
REQUEST_DURATION = (
    Histogram(
        "smartcampus_http_request_duration_seconds",
        "HTTP request duration",
        ["method", "path"],
    )
    if Histogram is not None
    else None
)
NOTIFICATION_ATTEMPT_COUNTER = (
    Counter(
        "smartcampus_notification_delivery_attempts_total",
        "Notification delivery attempts",
        ["notification_type", "channel", "status"],
    )
    if Counter is not None
    else None
)
NOTIFICATION_DURATION = (
    Histogram(
        "smartcampus_notification_delivery_duration_seconds",
        "Notification delivery duration",
        ["notification_type", "channel"],
    )
    if Histogram is not None
    else None
)
SCHEDULER_JOB_COUNTER = (
    Counter(
        "smartcampus_scheduler_jobs_total",
        "Scheduler job executions",
        ["job_name", "status"],
    )
    if Counter is not None
    else None
)
SCHEDULER_JOB_DURATION = (
    Histogram(
        "smartcampus_scheduler_job_duration_seconds",
        "Scheduler job execution duration",
        ["job_name", "status"],
    )
    if Histogram is not None
    else None
)

error_budget_tracker = ErrorBudgetTracker()
_last_alert_state = "healthy"
_last_alert_emit_ts = 0.0


OBS_TARGET = max(0.90, min(0.9999, float(os.getenv("ERROR_BUDGET_TARGET", "0.995"))))
OBS_WINDOW_SECONDS = max(300, int(os.getenv("ERROR_BUDGET_WINDOW_SECONDS", "3600")))


observability_router = APIRouter(prefix="/observability", tags=["Observability"])


@observability_router.get("/error-budget")
def get_error_budget() -> dict[str, Any]:
    return error_budget_tracker.snapshot(target=OBS_TARGET, window_seconds=OBS_WINDOW_SECONDS)


@observability_router.get("/alerts")
def get_observability_alerts() -> dict[str, Any]:
    snapshot = error_budget_tracker.snapshot(target=OBS_TARGET, window_seconds=OBS_WINDOW_SECONDS)
    alerts: list[dict[str, Any]] = []
    state = str(snapshot.get("alert_state") or "healthy")
    if state == "warning":
        alerts.append(
            {
                "severity": "warning",
                "rule": "error-budget-burn",
                "message": "Error budget burn is above 1x. Investigate recent 5xx spikes.",
                "snapshot": snapshot,
            }
        )
    elif state == "critical":
        alerts.append(
            {
                "severity": "critical",
                "rule": "error-budget-burn",
                "message": "Error budget burn is above 2x. Immediate action required.",
                "snapshot": snapshot,
            }
        )
    return {"alerts": alerts, "count": len(alerts)}


def metrics_as_text() -> str:
    if generate_latest is None:
        snapshot = error_budget_tracker.snapshot(target=OBS_TARGET, window_seconds=OBS_WINDOW_SECONDS)
        lines = [
            "# HELP smartcampus_error_budget_burn_rate Error budget burn rate",
            "# TYPE smartcampus_error_budget_burn_rate gauge",
            f"smartcampus_error_budget_burn_rate {snapshot['burn_rate']}",
            "# HELP smartcampus_error_budget_observed_availability Observed availability",
            "# TYPE smartcampus_error_budget_observed_availability gauge",
            f"smartcampus_error_budget_observed_availability {snapshot['observed_availability']}",
        ]
        return "\n".join(lines) + "\n"
    return generate_latest().decode("utf-8")


def metrics_response() -> PlainTextResponse:
    return PlainTextResponse(metrics_as_text(), media_type=CONTENT_TYPE_LATEST)


def record_notification_delivery_attempt(
    *,
    notification_type: str,
    channel: str,
    status: str,
    duration_seconds: float | None = None,
) -> None:
    type_label = str(notification_type or "unknown").strip() or "unknown"
    channel_label = str(channel or "unknown").strip() or "unknown"
    status_label = str(status or "unknown").strip() or "unknown"
    if NOTIFICATION_ATTEMPT_COUNTER is not None:
        NOTIFICATION_ATTEMPT_COUNTER.labels(
            notification_type=type_label,
            channel=channel_label,
            status=status_label,
        ).inc()
    if duration_seconds is not None and NOTIFICATION_DURATION is not None:
        NOTIFICATION_DURATION.labels(
            notification_type=type_label,
            channel=channel_label,
        ).observe(max(0.0, float(duration_seconds)))


def record_scheduler_job_run(
    *,
    job_name: str,
    status: str,
    duration_seconds: float | None = None,
) -> None:
    job_label = str(job_name or "unknown").strip() or "unknown"
    status_label = str(status or "unknown").strip() or "unknown"
    if SCHEDULER_JOB_COUNTER is not None:
        SCHEDULER_JOB_COUNTER.labels(job_name=job_label, status=status_label).inc()
    if duration_seconds is not None and SCHEDULER_JOB_DURATION is not None:
        SCHEDULER_JOB_DURATION.labels(job_name=job_label, status=status_label).observe(
            max(0.0, float(duration_seconds))
        )


def configure_logging() -> None:
    root = logging.getLogger()
    if getattr(root, "_smartcampus_logging_configured", False):
        return

    raw_level = (os.getenv("LOG_LEVEL", "INFO") or "INFO").strip().upper()
    level = getattr(logging, raw_level, logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    handler.addFilter(TraceIdFilter())

    root.handlers = [handler]
    root.setLevel(level)
    setattr(root, "_smartcampus_logging_configured", True)


def install_observability(app: FastAPI) -> None:
    configure_logging()

    @app.middleware("http")
    async def trace_and_metrics_middleware(request: Request, call_next):
        trace_id = (
            request.headers.get("x-trace-id")
            or request.headers.get("x-request-id")
            or uuid.uuid4().hex
        )
        token = trace_id_ctx.set(trace_id)
        started = time.perf_counter()
        status_code = 500
        response = None

        try:
            response = await call_next(request)
            status_code = int(response.status_code)
        except Exception:
            status_code = 500
            logger.exception(
                "Unhandled request error",
                extra={
                    "event": "http.error",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                },
            )
            raise
        finally:
            elapsed = max(0.0, (time.perf_counter() - started) * 1000.0)
            path_template = request.url.path
            route = request.scope.get("route")
            if route is not None and getattr(route, "path", None):
                path_template = str(route.path)

            if REQUEST_COUNTER is not None:
                REQUEST_COUNTER.labels(
                    method=request.method,
                    path=path_template,
                    status=str(status_code),
                ).inc()
            if REQUEST_DURATION is not None:
                REQUEST_DURATION.labels(method=request.method, path=path_template).observe(elapsed / 1000.0)

            error_budget_tracker.add(ok=status_code < 500)
            logger.info(
                "HTTP request completed",
                extra={
                    "event": "http.request",
                    "method": request.method,
                    "path": path_template,
                    "status_code": status_code,
                    "duration_ms": round(elapsed, 3),
                },
            )
            global _last_alert_state, _last_alert_emit_ts
            snapshot = error_budget_tracker.snapshot(target=OBS_TARGET, window_seconds=OBS_WINDOW_SECONDS)
            current_state = str(snapshot.get("alert_state") or "healthy")
            now_ts = time.time()
            should_emit = current_state != "healthy" and (
                current_state != _last_alert_state or (now_ts - _last_alert_emit_ts) >= 60
            )
            if should_emit:
                if current_state == "critical":
                    logger.error("Error budget alert", extra={"event": "slo.alert", "alert": snapshot})
                else:
                    logger.warning("Error budget alert", extra={"event": "slo.alert", "alert": snapshot})
                _last_alert_state = current_state
                _last_alert_emit_ts = now_ts
            elif current_state == "healthy" and _last_alert_state != "healthy":
                logger.info("Error budget recovered", extra={"event": "slo.recovered", "alert": snapshot})
                _last_alert_state = "healthy"
                _last_alert_emit_ts = now_ts
            if response is not None:
                response.headers["X-Trace-Id"] = trace_id
            trace_id_ctx.reset(token)
        return response
