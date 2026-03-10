import os
import logging
import asyncio
import threading
from decimal import Decimal
from datetime import date, datetime, time, timedelta
from enum import Enum as PyEnum
from pathlib import Path
import time as pytime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pymongo.errors import DuplicateKeyError
from sqlalchemy import inspect as sa_inspect, text
from sqlalchemy.orm import Session

from . import models
from .attendance_ledger import append_attendance_event, recompute_attendance_record
from .auth_utils import hash_password, require_roles
from .database import Base, SessionLocal, database_status, engine
from .env_loader import load_app_env
from .enterprise_controls import validate_production_secrets
from .food_bootstrap import bootstrap_food_hall_catalog
from .mongo import (
    close_mongo,
    get_mongo_db,
    init_mongo,
    mirror_document,
    mongo_persistence_required,
    mongo_status,
    next_sequence,
)
from .outbox import dispatch_outbox_batch
from .internal_scheduler import scheduler_status, start_internal_scheduler, stop_internal_scheduler
from .observability import install_observability, metrics_response, observability_router
from .otp_delivery import assert_otp_delivery_ready
from .performance import record_request_metric
from .redis_client import close_redis, init_redis, redis_required, redis_status
from .realtime_bus import realtime_hub
from .runtime_infra import managed_services_required
from .workers import (
    assert_worker_ready,
    inline_fallback_enabled as worker_inline_fallback_enabled,
    worker_live,
    worker_ready,
    worker_required,
    worker_transport_status,
)
from .routers import (
    admin_router,
    assets_router,
    attendance_router,
    auth_router,
    copilot_router,
    enterprise_router,
    food_router,
    identity_shield_router,
    remedial_router,
    messages_router,
    people_router,
    realtime_router,
    resources_router,
    saarthi_router,
)
from .routers.assets import build_static_asset_response, seed_static_assets_to_mongo

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_app_env()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LPU Smart Campus Management API",
    version="0.2.0",
    description=(
        "Smart Campus backend with mandatory modules + role-based auth + OTP login."
    ),
)
install_observability(app)
ALLOW_DEMO_SEED = os.getenv("ALLOW_DEMO_SEED", "false").strip().lower() in {"1", "true", "yes"}
_health_cache_lock = threading.Lock()
_health_cache_payload: dict[str, Any] | None = None
_health_cache_expires_at = 0.0
_health_cache_refreshing = False


def _strict_runtime_mode_enabled() -> bool:
    raw = (os.getenv("APP_RUNTIME_STRICT", "true") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _enabled_flag(name: str, default: bool) -> bool:
    raw = (os.getenv(name, "true" if default else "false") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _managed_services_contract_enabled() -> bool:
    raw = (os.getenv("APP_MANAGED_SERVICES_REQUIRED") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _health_cache_ttl_seconds() -> float:
    raw = (os.getenv("HEALTH_STATUS_CACHE_SECONDS", "10") or "").strip()
    try:
        value = float(raw)
    except ValueError:
        value = 10.0
    return max(1.0, min(60.0, value))


def _health_worker_live_timeout_seconds() -> float:
    raw = (os.getenv("HEALTH_WORKER_LIVE_TIMEOUT_SECONDS", "0.8") or "").strip()
    try:
        value = float(raw)
    except ValueError:
        value = 0.8
    return max(0.2, min(5.0, value))


def _otp_verify_connection_on_startup() -> bool:
    raw = (os.getenv("OTP_VERIFY_CONNECTION_ON_STARTUP") or "").strip().lower()
    if raw:
        return raw in {"1", "true", "yes", "on"}
    return _strict_runtime_mode_enabled()


def _build_health_payload() -> dict[str, Any]:
    return {
        "message": "Smart Campus Management API is running",
        "docs": "/docs",
        "ui": "/ui",
        "runtime_strict": _strict_runtime_mode_enabled(),
        "managed_services_required": managed_services_required(),
        "database": database_status(),
        "mongo": mongo_status(),
        "redis": redis_status(),
        "worker": {
            "required": worker_required(),
            "ready": worker_ready(),
            "live": worker_live(timeout_seconds=_health_worker_live_timeout_seconds()),
            "inline_fallback_enabled": worker_inline_fallback_enabled(),
            "transport": worker_transport_status(),
        },
        "scheduler": scheduler_status(),
    }


def _store_health_payload(payload: dict[str, Any]) -> dict[str, Any]:
    global _health_cache_payload, _health_cache_expires_at
    with _health_cache_lock:
        _health_cache_payload = payload
        _health_cache_expires_at = pytime.monotonic() + _health_cache_ttl_seconds()
    return payload


def _refresh_health_payload_sync() -> dict[str, Any]:
    global _health_cache_refreshing
    try:
        payload = _build_health_payload()
        return _store_health_payload(payload)
    finally:
        with _health_cache_lock:
            _health_cache_refreshing = False


def _refresh_health_payload_async() -> None:
    global _health_cache_refreshing
    with _health_cache_lock:
        if _health_cache_refreshing:
            return
        _health_cache_refreshing = True
    thread = threading.Thread(
        target=_refresh_health_payload_sync,
        name="smartcampus-health-refresh",
        daemon=True,
    )
    thread.start()


def _health_payload() -> dict[str, Any]:
    now = pytime.monotonic()
    with _health_cache_lock:
        payload = _health_cache_payload
        expires_at = _health_cache_expires_at

    if payload is None:
        return _refresh_health_payload_sync()

    if now >= expires_at:
        _refresh_health_payload_async()
    return payload


def _assert_strict_runtime_contract() -> None:
    if not _strict_runtime_mode_enabled():
        return
    db_state = database_status()
    mongo_state = mongo_status()
    redis_state = redis_status()
    if str(db_state.get("backend") or "").strip().lower() != "postgresql" or not bool(db_state.get("connected")):
        raise RuntimeError(
            "APP_RUNTIME_STRICT=true requires a live PostgreSQL SQLALCHEMY_DATABASE_URL."
        )
    if not mongo_persistence_required():
        raise RuntimeError(
            "APP_RUNTIME_STRICT=true requires MONGO_PERSISTENCE_REQUIRED=true."
        )
    if not redis_required():
        raise RuntimeError("APP_RUNTIME_STRICT=true requires REDIS_REQUIRED=true.")
    if not worker_required():
        raise RuntimeError("APP_RUNTIME_STRICT=true requires WORKER_REQUIRED=true.")
    if not _enabled_flag("MONGO_STARTUP_STRICT", default=True):
        raise RuntimeError("APP_RUNTIME_STRICT=true requires MONGO_STARTUP_STRICT=true.")
    if worker_inline_fallback_enabled():
        raise RuntimeError(
            "APP_RUNTIME_STRICT=true requires WORKER_INLINE_FALLBACK_ENABLED=false."
        )
    if not _enabled_flag("WORKER_WAIT_FOR_OTP_RESULT", default=True):
        raise RuntimeError(
            "APP_RUNTIME_STRICT=true requires WORKER_WAIT_FOR_OTP_RESULT=true."
        )
    otp_mode = (os.getenv("OTP_DELIVERY_MODE", "smtp") or "").strip().lower() or "smtp"
    if otp_mode not in {"smtp", "graph"}:
        raise RuntimeError(
            "APP_RUNTIME_STRICT=true requires OTP_DELIVERY_MODE to be 'smtp' or 'graph'."
        )
    required_worker_flags = [
        "WORKER_ENABLE_OTP",
        "WORKER_ENABLE_NOTIFICATIONS",
        "WORKER_ENABLE_FACE_REVERIFY",
        "WORKER_ENABLE_RECOMPUTE",
    ]
    disabled = [name for name in required_worker_flags if not _enabled_flag(name, default=True)]
    if disabled:
        raise RuntimeError(
            "APP_RUNTIME_STRICT=true requires worker queues enabled: "
            + ", ".join(disabled)
            + "."
        )
    if _managed_services_contract_enabled() and ("remote_host" in db_state or "tls_enabled" in db_state):
        if not bool(db_state.get("remote_host")):
            raise RuntimeError(
                "APP_MANAGED_SERVICES_REQUIRED=true requires SQLALCHEMY_DATABASE_URL to use a non-local PostgreSQL host."
            )
        if not bool(db_state.get("tls_enabled")):
            raise RuntimeError(
                "APP_MANAGED_SERVICES_REQUIRED=true requires PostgreSQL TLS via DATABASE_SSL_MODE=require|verify-ca|verify-full."
            )
        if not bool(mongo_state.get("remote_host")):
            raise RuntimeError(
                "APP_MANAGED_SERVICES_REQUIRED=true requires MONGO_URI to use a non-local MongoDB host."
            )
        if not bool(mongo_state.get("tls_enabled")):
            raise RuntimeError("APP_MANAGED_SERVICES_REQUIRED=true requires MongoDB TLS.")
        if not bool(redis_state.get("remote_host")):
            raise RuntimeError(
                "APP_MANAGED_SERVICES_REQUIRED=true requires REDIS_URL to use a non-local Redis host."
            )
        if not bool(redis_state.get("tls_enabled")):
            raise RuntimeError(
                "APP_MANAGED_SERVICES_REQUIRED=true requires REDIS_URL to use rediss:// with TLS."
            )

        worker_transport = worker_transport_status()
        for target_name in ("broker", "backend"):
            target = worker_transport.get(target_name) or {}
            if not bool(target.get("configured")):
                raise RuntimeError(
                    f"APP_MANAGED_SERVICES_REQUIRED=true requires worker {target_name} transport to be configured."
                )
            if not bool(target.get("remote_host")):
                raise RuntimeError(
                    f"APP_MANAGED_SERVICES_REQUIRED=true requires worker {target_name} transport to use a non-local Redis host."
                )
            if not bool(target.get("tls_enabled")):
                raise RuntimeError(
                    f"APP_MANAGED_SERVICES_REQUIRED=true requires worker {target_name} transport to use rediss:// with TLS."
                )


@app.middleware("http")
async def request_latency_middleware(request: Request, call_next):
    started_at = pytime.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        latency_ms = (pytime.perf_counter() - started_at) * 1000.0
        record_request_metric(request.url.path, request.method, 500, latency_ms)
        raise

    latency_ms = (pytime.perf_counter() - started_at) * 1000.0
    record_request_metric(request.url.path, request.method, int(response.status_code), latency_ms)
    response.headers["X-Request-Latency-Ms"] = f"{latency_ms:.2f}"
    return response


def apply_sqlite_migrations() -> None:
    if engine.dialect.name != "sqlite":
        return

    with engine.begin() as connection:
        student_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(students)")).fetchall()
        }
        if "profile_photo_data_url" not in student_columns:
            connection.execute(
                text("ALTER TABLE students ADD COLUMN profile_photo_data_url TEXT")
            )
        if "profile_photo_object_key" not in student_columns:
            connection.execute(
                text("ALTER TABLE students ADD COLUMN profile_photo_object_key TEXT")
            )
        if "profile_photo_updated_at" not in student_columns:
            connection.execute(
                text("ALTER TABLE students ADD COLUMN profile_photo_updated_at DATETIME")
            )
        if "profile_photo_locked_until" not in student_columns:
            connection.execute(
                text("ALTER TABLE students ADD COLUMN profile_photo_locked_until DATETIME")
            )
        if "profile_face_template_json" not in student_columns:
            connection.execute(
                text("ALTER TABLE students ADD COLUMN profile_face_template_json TEXT")
            )
        if "profile_face_template_updated_at" not in student_columns:
            connection.execute(
                text("ALTER TABLE students ADD COLUMN profile_face_template_updated_at DATETIME")
            )
        if "enrollment_video_template_json" not in student_columns:
            connection.execute(
                text("ALTER TABLE students ADD COLUMN enrollment_video_template_json TEXT")
            )
        if "enrollment_video_updated_at" not in student_columns:
            connection.execute(
                text("ALTER TABLE students ADD COLUMN enrollment_video_updated_at DATETIME")
            )
        if "enrollment_video_locked_until" not in student_columns:
            connection.execute(
                text("ALTER TABLE students ADD COLUMN enrollment_video_locked_until DATETIME")
            )
        if "registration_number" not in student_columns:
            connection.execute(
                text("ALTER TABLE students ADD COLUMN registration_number TEXT")
            )
        if "section" not in student_columns:
            connection.execute(
                text("ALTER TABLE students ADD COLUMN section TEXT")
            )
        if "section_updated_at" not in student_columns:
            connection.execute(
                text("ALTER TABLE students ADD COLUMN section_updated_at DATETIME")
            )

        faculty_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(faculty)")).fetchall()
        }
        if "faculty_identifier" not in faculty_columns:
            connection.execute(
                text("ALTER TABLE faculty ADD COLUMN faculty_identifier TEXT")
            )
        if "section" not in faculty_columns:
            connection.execute(
                text("ALTER TABLE faculty ADD COLUMN section TEXT")
            )
        if "section_updated_at" not in faculty_columns:
            connection.execute(
                text("ALTER TABLE faculty ADD COLUMN section_updated_at DATETIME")
            )
        if "profile_photo_data_url" not in faculty_columns:
            connection.execute(
                text("ALTER TABLE faculty ADD COLUMN profile_photo_data_url TEXT")
            )
        if "profile_photo_object_key" not in faculty_columns:
            connection.execute(
                text("ALTER TABLE faculty ADD COLUMN profile_photo_object_key TEXT")
            )
        if "profile_photo_updated_at" not in faculty_columns:
            connection.execute(
                text("ALTER TABLE faculty ADD COLUMN profile_photo_updated_at DATETIME")
            )
        if "profile_photo_locked_until" not in faculty_columns:
            connection.execute(
                text("ALTER TABLE faculty ADD COLUMN profile_photo_locked_until DATETIME")
            )

        food_menu_item_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(food_menu_items)")).fetchall()
        }
        if "prep_time_override_minutes" not in food_menu_item_columns:
            connection.execute(
                text("ALTER TABLE food_menu_items ADD COLUMN prep_time_override_minutes INTEGER")
            )

        food_order_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(food_orders)")).fetchall()
        }
        if "shop_name" not in food_order_columns:
            connection.execute(
                text("ALTER TABLE food_orders ADD COLUMN shop_name TEXT")
            )
        if "shop_block" not in food_order_columns:
            connection.execute(
                text("ALTER TABLE food_orders ADD COLUMN shop_block TEXT")
            )
        if "location_verified" not in food_order_columns:
            connection.execute(
                text("ALTER TABLE food_orders ADD COLUMN location_verified BOOLEAN DEFAULT 0")
            )
        if "location_latitude" not in food_order_columns:
            connection.execute(
                text("ALTER TABLE food_orders ADD COLUMN location_latitude FLOAT")
            )
        if "location_longitude" not in food_order_columns:
            connection.execute(
                text("ALTER TABLE food_orders ADD COLUMN location_longitude FLOAT")
            )
        if "location_accuracy_m" not in food_order_columns:
            connection.execute(
                text("ALTER TABLE food_orders ADD COLUMN location_accuracy_m FLOAT")
            )
        food_order_column_specs = {
            "shop_id": "INTEGER",
            "menu_item_id": "INTEGER",
            "quantity": "INTEGER DEFAULT 1",
            "unit_price": "FLOAT DEFAULT 0",
            "total_price": "FLOAT DEFAULT 0",
            "idempotency_key": "TEXT",
            "payment_status": "TEXT DEFAULT 'pending'",
            "payment_provider": "TEXT",
            "payment_reference": "TEXT",
            "status_note": "TEXT",
            "assigned_runner": "TEXT",
            "pickup_point": "TEXT",
            "delivery_eta_minutes": "INTEGER",
            "estimated_ready_at": "DATETIME",
            "last_location_verified_at": "DATETIME",
            "verified_at": "DATETIME",
            "preparing_at": "DATETIME",
            "out_for_delivery_at": "DATETIME",
            "delivered_at": "DATETIME",
            "cancelled_at": "DATETIME",
            "cancel_reason": "TEXT",
            "rating_stars": "INTEGER",
            "rating_comment": "TEXT",
            "rated_at": "DATETIME",
            "rating_locked_at": "DATETIME",
            "last_status_updated_at": "DATETIME",
        }
        for col_name, col_spec in food_order_column_specs.items():
            if col_name in food_order_columns:
                continue
            connection.execute(text(f"ALTER TABLE food_orders ADD COLUMN {col_name} {col_spec}"))

        food_payment_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(food_payments)")).fetchall()
        }
        food_payment_column_specs = {
            "provider_order_id": "TEXT",
            "provider_payment_id": "TEXT",
            "provider_signature": "TEXT",
            "order_state": "TEXT DEFAULT 'created'",
            "payment_state": "TEXT DEFAULT 'created'",
            "attempt_count": "INTEGER DEFAULT 0",
            "failed_reason": "TEXT",
            "metadata_json": "TEXT",
            "updated_at": "DATETIME",
        }
        for col_name, col_spec in food_payment_column_specs.items():
            if col_name in food_payment_columns:
                continue
            connection.execute(text(f"ALTER TABLE food_payments ADD COLUMN {col_name} {col_spec}"))

        makeup_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(makeup_classes)")).fetchall()
        }
        makeup_column_specs = {
            "sections_json": "TEXT DEFAULT '[]'",
            "class_mode": "TEXT DEFAULT 'offline'",
            "room_number": "TEXT",
            "online_link": "TEXT",
            "code_generated_at": "DATETIME",
            "code_expires_at": "DATETIME",
            "attendance_open_minutes": "INTEGER DEFAULT 15",
            "scheduled_at": "DATETIME",
        }
        for col_name, col_spec in makeup_column_specs.items():
            if col_name in makeup_columns:
                continue
            connection.execute(text(f"ALTER TABLE makeup_classes ADD COLUMN {col_name} {col_spec}"))
        connection.execute(
            text(
                "UPDATE makeup_classes "
                "SET sections_json = COALESCE(NULLIF(TRIM(sections_json), ''), '[\"ALL\"]') "
                "WHERE sections_json IS NULL OR TRIM(sections_json) = ''"
            )
        )
        connection.execute(
            text(
                "UPDATE makeup_classes "
                "SET class_mode = COALESCE(NULLIF(TRIM(class_mode), ''), 'offline') "
                "WHERE class_mode IS NULL OR TRIM(class_mode) = ''"
            )
        )
        connection.execute(
            text(
                "UPDATE makeup_classes "
                "SET attendance_open_minutes = COALESCE(attendance_open_minutes, 15) "
                "WHERE attendance_open_minutes IS NULL"
            )
        )
        connection.execute(
            text(
                "UPDATE makeup_classes "
                "SET code_generated_at = COALESCE(code_generated_at, created_at), "
                "scheduled_at = COALESCE(scheduled_at, created_at) "
                "WHERE code_generated_at IS NULL OR scheduled_at IS NULL"
            )
        )
        connection.execute(
            text(
                "UPDATE makeup_classes "
                "SET code_expires_at = COALESCE(code_expires_at, datetime(class_date || ' ' || start_time, '+15 minutes')) "
                "WHERE code_expires_at IS NULL"
            )
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_makeup_classes_class_date_start_time ON makeup_classes (class_date, start_time)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_makeup_classes_faculty_id ON makeup_classes (faculty_id)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_makeup_classes_code_expires_at ON makeup_classes (code_expires_at)")
        )
        connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS remedial_messages ("
                "id INTEGER PRIMARY KEY, "
                "makeup_class_id INTEGER NOT NULL, "
                "faculty_id INTEGER NOT NULL, "
                "student_id INTEGER NOT NULL, "
                "section TEXT NOT NULL, "
                "remedial_code TEXT NOT NULL, "
                "message TEXT NOT NULL, "
                "created_at DATETIME NOT NULL, "
                "read_at DATETIME, "
                "CONSTRAINT uq_remedial_message_class_student UNIQUE (makeup_class_id, student_id)"
                ")"
            )
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_remedial_messages_student_created ON remedial_messages (student_id, created_at)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_remedial_messages_class_created ON remedial_messages (makeup_class_id, created_at)")
        )
        # Backfill updated_at on older rows where column was just introduced.
        if "updated_at" in food_payment_column_specs:
            connection.execute(
                text(
                    "UPDATE food_payments SET updated_at = COALESCE(updated_at, created_at) "
                    "WHERE updated_at IS NULL"
                )
            )

        # Keep registration numbers unique when set; allow multiple NULL rows.
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_students_registration_number_unique "
                "ON students (registration_number) WHERE registration_number IS NOT NULL"
            )
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_faculty_identifier_unique "
                "ON faculty (faculty_identifier) WHERE faculty_identifier IS NOT NULL"
            )
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_food_orders_student_date_idempotency "
                "ON food_orders (student_id, order_date, idempotency_key) "
                "WHERE idempotency_key IS NOT NULL"
            )
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_food_orders_order_date_slot ON food_orders (order_date, slot_id)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_food_orders_shop_id ON food_orders (shop_id)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_food_payments_provider_order_id ON food_payments (provider_order_id)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_food_payments_provider_payment_id ON food_payments (provider_payment_id)")
        )

        attendance_record_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(attendance_records)")).fetchall()
        }
        if "updated_at" not in attendance_record_columns:
            connection.execute(
                text("ALTER TABLE attendance_records ADD COLUMN updated_at DATETIME")
            )
        if "computed_from_event_id" not in attendance_record_columns:
            connection.execute(
                text("ALTER TABLE attendance_records ADD COLUMN computed_from_event_id INTEGER")
            )
        connection.execute(
            text(
                "UPDATE attendance_records SET updated_at = COALESCE(updated_at, created_at) "
                "WHERE updated_at IS NULL"
            )
        )

        attendance_submission_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(attendance_submissions)")).fetchall()
        }
        if "selfie_photo_object_key" not in attendance_submission_columns:
            connection.execute(
                text("ALTER TABLE attendance_submissions ADD COLUMN selfie_photo_object_key TEXT")
            )

        rectification_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(attendance_rectification_requests)")).fetchall()
        }
        if "proof_photo_object_key" not in rectification_columns:
            connection.execute(
                text("ALTER TABLE attendance_rectification_requests ADD COLUMN proof_photo_object_key TEXT")
            )

        analysis_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(classroom_analyses)")).fetchall()
        }
        if "photo_object_key" not in analysis_columns:
            connection.execute(
                text("ALTER TABLE classroom_analyses ADD COLUMN photo_object_key TEXT")
            )

        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_students_profile_photo_object_key "
                "ON students (profile_photo_object_key)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_faculty_profile_photo_object_key "
                "ON faculty (profile_photo_object_key)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_attendance_records_updated_at "
                "ON attendance_records (updated_at)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_attendance_records_computed_from_event_id "
                "ON attendance_records (computed_from_event_id)"
            )
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_attendance_events_event_key "
                "ON attendance_events (event_key)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_attendance_events_student_course_date "
                "ON attendance_events (student_id, course_id, attendance_date, created_at)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_auth_sessions_user_id "
                "ON auth_sessions (user_id, revoked_at, refresh_expires_at)"
            )
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_auth_sessions_sid "
                "ON auth_sessions (sid)"
            )
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_auth_token_revocations_jti "
                "ON auth_token_revocations (jti)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_media_objects_owner "
                "ON media_objects (owner_table, owner_id, media_kind)"
            )
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_media_objects_object_key "
                "ON media_objects (object_key)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_outbox_events_status_available "
                "ON outbox_events (status, available_at)"
            )
        )


def apply_mysql_enrollment_schema_migrations() -> None:
    if engine.dialect.name != "mysql":
        return

    with engine.begin() as connection:
        inspector = sa_inspect(connection)
        if "students" not in set(inspector.get_table_names()):
            return

        student_columns = {
            column["name"]: column
            for column in inspector.get_columns("students")
        }
        required_additions = {
            "profile_face_template_json": "LONGTEXT NULL",
            "profile_face_template_updated_at": "DATETIME NULL",
            "enrollment_video_template_json": "LONGTEXT NULL",
            "enrollment_video_updated_at": "DATETIME NULL",
            "enrollment_video_locked_until": "DATETIME NULL",
        }
        for column_name, column_sql in required_additions.items():
            if column_name in student_columns:
                continue
            connection.execute(text(f"ALTER TABLE students ADD COLUMN {column_name} {column_sql}"))

        mysql_types = {
            row[0]: row[1]
            for row in connection.execute(
                text(
                    """
                    SELECT COLUMN_NAME, DATA_TYPE
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'students'
                    """
                )
            ).fetchall()
        }
        for column_name in ("profile_face_template_json", "enrollment_video_template_json"):
            if str(mysql_types.get(column_name, "")).lower() == "longtext":
                continue
            connection.execute(text(f"ALTER TABLE students MODIFY COLUMN {column_name} LONGTEXT NULL"))

Base.metadata.create_all(bind=engine)
apply_sqlite_migrations()
apply_mysql_enrollment_schema_migrations()

app.include_router(assets_router)
app.include_router(auth_router)
app.include_router(people_router)
app.include_router(attendance_router)
app.include_router(copilot_router)
app.include_router(food_router)
app.include_router(identity_shield_router)
app.include_router(resources_router)
app.include_router(admin_router)
app.include_router(remedial_router)
app.include_router(messages_router)
app.include_router(saarthi_router)
app.include_router(enterprise_router)
app.include_router(realtime_router)
app.include_router(observability_router)

WEB_DIR = PROJECT_ROOT / "web"
if WEB_DIR.exists():
    app.mount("/web", StaticFiles(directory=WEB_DIR, html=True), name="web")


@app.get("/")
def health_check():
    return _health_payload()


@app.get("/metrics", include_in_schema=False)
def prometheus_metrics():
    return metrics_response()


@app.get("/ui", include_in_schema=False)
def ui():
    index_file = WEB_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "UI is not available. Ensure web/index.html exists."}


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return build_static_asset_response("lpu-smart-campus-logo", prefer_database=True)


@app.get("/apple-touch-icon.png", include_in_schema=False)
def apple_touch_icon():
    return build_static_asset_response("lpu-smart-campus-logo", prefer_database=True)


@app.get("/apple-touch-icon-precomposed.png", include_in_schema=False)
def apple_touch_icon_precomposed():
    return build_static_asset_response("lpu-smart-campus-logo", prefer_database=True)


@app.on_event("startup")
async def startup_event() -> None:
    _assert_strict_runtime_contract()
    validate_production_secrets()
    assert_otp_delivery_ready(verify_connection=_otp_verify_connection_on_startup())
    redis_ok = init_redis(force=False)
    if not redis_ok and redis_required():
        raise RuntimeError("REDIS_REQUIRED=true but Redis connection failed at startup.")
    assert_worker_ready()
    realtime_hub.bind_loop(asyncio.get_running_loop())
    await realtime_hub.start()
    requires_mongo = mongo_persistence_required()
    strict_startup = (os.getenv("MONGO_STARTUP_STRICT", "true") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    max_attempts_raw = os.getenv("MONGO_STARTUP_MAX_ATTEMPTS", "6").strip()
    retry_delay_raw = os.getenv("MONGO_STARTUP_RETRY_DELAY_SECONDS", "2.0").strip()
    try:
        max_attempts = max(1, int(max_attempts_raw))
    except ValueError:
        max_attempts = 6
    try:
        retry_delay_seconds = max(0.0, float(retry_delay_raw))
    except ValueError:
        retry_delay_seconds = 2.0

    ok = False
    last_reason = ""
    for attempt in range(1, max_attempts + 1):
        ok = get_mongo_db(required=False) is not None or init_mongo(force=(attempt == 1))
        if ok:
            break
        status = mongo_status()
        last_reason = str(status.get("error") or "MongoDB connection failed")
        if attempt < max_attempts:
            logger.warning(
                "MongoDB startup attempt %s/%s failed: %s. Retrying in %.1fs.",
                attempt,
                max_attempts,
                last_reason,
                retry_delay_seconds,
            )
            if retry_delay_seconds > 0:
                pytime.sleep(retry_delay_seconds)

    if not ok:
        status = mongo_status()
        reason = status.get("error") or last_reason or "MongoDB connection failed"
        if requires_mongo and strict_startup:
            raise RuntimeError(f"MongoDB is required for startup but connection failed: {reason}")
        logger.warning(
            "MongoDB unavailable at startup; continuing with degraded mode. "
            "reason=%s requires_mongo=%s strict_startup=%s",
            reason,
            requires_mongo,
            strict_startup,
        )
    else:
        seed_static_assets_to_mongo()
    db = SessionLocal()
    try:
        dispatch_outbox_batch(db, limit=200)
        db.commit()
        bootstrap_food_hall_catalog(db)
        startup_snapshot_sync = (os.getenv("MONGO_STARTUP_SQL_SNAPSHOT_SYNC", "true") or "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if ok and startup_snapshot_sync:
            sync_sql_snapshot_to_mongo(db)
            logger.info("Startup SQL->Mongo snapshot sync completed.")
    except Exception as exc:
        if requires_mongo and strict_startup:
            raise RuntimeError(f"Startup SQL->Mongo sync failed: {exc}") from exc
        logger.warning("Startup SQL->Mongo sync skipped due to non-fatal error: %s", exc)
    finally:
        db.close()
    start_internal_scheduler()
    _store_health_payload(_build_health_payload())


@app.on_event("shutdown")
async def shutdown_event() -> None:
    stop_internal_scheduler()
    await realtime_hub.stop()
    close_redis()
    close_mongo()


def ensure_auth_user(
    db: Session,
    *,
    email: str,
    role: models.UserRole,
    password: str,
    student_id: int | None = None,
    faculty_id: int | None = None,
) -> bool:
    existing = db.query(models.AuthUser).filter(models.AuthUser.email == email).first()
    if existing:
        changed = False
        if existing.role != role:
            existing.role = role
            changed = True
        if role == models.UserRole.STUDENT:
            if existing.faculty_id is not None:
                existing.faculty_id = None
                changed = True
            if student_id and existing.student_id != student_id:
                existing.student_id = student_id
                changed = True
        elif role == models.UserRole.FACULTY:
            if existing.student_id is not None:
                existing.student_id = None
                changed = True
            if faculty_id and existing.faculty_id != faculty_id:
                existing.faculty_id = faculty_id
                changed = True
        else:
            if existing.student_id is not None or existing.faculty_id is not None:
                existing.student_id = None
                existing.faculty_id = None
                changed = True
        if changed:
            db.flush()
        return False

    db.add(
        models.AuthUser(
            email=email,
            password_hash=hash_password(password),
            role=role,
            student_id=student_id,
            faculty_id=faculty_id,
            is_active=True,
        )
    )
    db.flush()
    return True


def sync_sql_snapshot_to_mongo(db: Session) -> None:
    mongo_db = get_mongo_db(required=False)

    def _normalize_value(value: Any) -> Any:
        if isinstance(value, PyEnum):
            return value.value
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, time):
            return value.isoformat()
        return value

    def _serialize_row(row: Any, *, source: str) -> dict[str, Any]:
        mapper = sa_inspect(row.__class__)
        payload: dict[str, Any] = {}
        for column in mapper.columns:
            payload[column.key] = _normalize_value(getattr(row, column.key))
        payload["source"] = source

        table_name = getattr(row.__class__, "__tablename__", "")
        if table_name == "food_orders":
            payload.setdefault("order_id", payload.get("id"))
        elif table_name == "food_shops":
            payload.setdefault("shop_id", payload.get("id"))
        elif table_name == "food_menu_items":
            payload.setdefault("menu_item_id", payload.get("id"))
        elif table_name == "food_payments":
            payload.setdefault("payment_id", payload.get("id"))
        elif table_name == "makeup_classes":
            payload.setdefault("makeup_class_id", payload.get("id"))
        return payload

    def _pk_filter(row: Any, payload: dict[str, Any], *, table_name: str) -> dict[str, Any]:
        if table_name == "food_payments" and payload.get("payment_id") is not None:
            return {"payment_id": payload["payment_id"]}
        mapper = sa_inspect(row.__class__)
        criteria: dict[str, Any] = {}
        for col in mapper.primary_key:
            value = payload.get(col.key)
            if value is not None:
                criteria[col.key] = value
        if criteria:
            return criteria
        if payload.get("id") is not None:
            return {"id": payload["id"]}
        raise RuntimeError(f"Unable to build Mongo upsert filter for {row.__class__.__name__}")

    def _safe_update_one(collection_name: str, match_filter: dict[str, Any], payload: dict[str, Any]) -> None:
        if mongo_db is None:
            mirror_document(
                collection_name,
                payload,
                upsert_filter=match_filter,
                required=False,
            )
            return
        collection = mongo_db[collection_name]
        try:
            collection.update_one(match_filter, {"$set": payload}, upsert=True)
            return
        except DuplicateKeyError as exc:
            details = getattr(exc, "details", {}) or {}
            key_value = details.get("keyValue")
            if not isinstance(key_value, dict) or not key_value:
                raise

            fallback_payload = dict(payload)
            fallback_payload.pop("id", None)
            result = collection.update_one(dict(key_value), {"$set": fallback_payload}, upsert=False)
            if result.matched_count:
                logger.debug(
                    "Resolved startup sync duplicate key for collection=%s via filter=%s",
                    collection_name,
                    key_value,
                )
                return
            logger.warning(
                "Skipping unresolved startup sync duplicate key for collection=%s filter=%s",
                collection_name,
                key_value,
            )
            return

    sync_models = [
        models.Student,
        models.Faculty,
        models.Course,
        models.Enrollment,
        models.Classroom,
        models.CourseClassroom,
        models.AttendanceRecord,
        models.AttendanceEvent,
        models.NotificationLog,
        models.FoodItem,
        models.FoodShop,
        models.FoodMenuItem,
        models.BreakSlot,
        models.FoodOrder,
        models.FoodPayment,
        models.FoodOrderAudit,
        models.MakeUpClass,
        models.RemedialAttendance,
        models.RemedialMessage,
        models.FacultyMessage,
        models.SupportQueryMessage,
        models.ClassSchedule,
        models.AttendanceSubmission,
        models.AttendanceRectificationRequest,
        models.ClassroomAnalysis,
        models.StudentGrade,
        models.AuthOTP,
        models.AuthOTPDelivery,
        models.AuthSession,
        models.AuthTokenRevocation,
        models.MediaObject,
        models.OutboxEvent,
    ]

    for model_cls in sync_models:
        collection_name = str(getattr(model_cls, "__tablename__", "")).strip()
        if not collection_name:
            continue
        for row in db.query(model_cls).all():
            payload = _serialize_row(row, source="startup-sql-sync")
            _safe_update_one(
                collection_name,
                _pk_filter(row, payload, table_name=collection_name),
                payload,
            )

    for auth_user in db.query(models.AuthUser).all():
        if mongo_db is None:
            auth_id = int(auth_user.id)
        else:
            auth_collection = mongo_db["auth_users"]
            existing_by_email = auth_collection.find_one({"email": auth_user.email})
            if existing_by_email:
                auth_id = int(existing_by_email["id"])
            else:
                auth_id = next_sequence("auth_users")
                while auth_collection.find_one({"id": auth_id}):
                    auth_id = next_sequence("auth_users")

        _safe_update_one(
            "auth_users",
            {"email": auth_user.email},
            {
                "id": auth_id,
                "email": auth_user.email,
                "password_hash": auth_user.password_hash,
                "role": auth_user.role.value,
                "student_id": auth_user.student_id,
                "faculty_id": auth_user.faculty_id,
                "is_active": auth_user.is_active,
                "created_at": auth_user.created_at,
                "last_login_at": auth_user.last_login_at,
                "source": "startup-sql-sync",
            },
        )


@app.post("/demo/seed")
def seed_demo_data(
    _: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    if not ALLOW_DEMO_SEED:
        raise HTTPException(
            status_code=403,
            detail="Demo seeding is disabled in real-time mode. Set ALLOW_DEMO_SEED=true to enable.",
        )

    db: Session = SessionLocal()
    try:
        created = {
            "faculty": 0,
            "students": 0,
            "courses": 0,
            "enrollments": 0,
            "classrooms": 0,
            "schedules": 0,
            "auth_users": 0,
        }

        faculty_1 = db.query(models.Faculty).filter(models.Faculty.email == "kavita.faculty@gmail.com").first()
        if not faculty_1:
            faculty_1 = models.Faculty(name="Dr. Kavita Sharma", email="kavita.faculty@gmail.com", department="CSE")
            db.add(faculty_1)
            db.flush()
            created["faculty"] += 1

        faculty_2 = db.query(models.Faculty).filter(models.Faculty.email == "arjun.faculty@gmail.com").first()
        if not faculty_2:
            faculty_2 = models.Faculty(name="Mr. Arjun Singh", email="arjun.faculty@gmail.com", department="CSE")
            db.add(faculty_2)
            db.flush()
            created["faculty"] += 1

        course_1 = db.query(models.Course).filter(models.Course.code == "CSE101").first()
        if not course_1:
            course_1 = models.Course(code="CSE101", title="Python Programming", faculty_id=faculty_1.id)
            db.add(course_1)
            db.flush()
            created["courses"] += 1
        else:
            course_1.faculty_id = faculty_1.id

        course_2 = db.query(models.Course).filter(models.Course.code == "CSE202").first()
        if not course_2:
            course_2 = models.Course(code="CSE202", title="Web Development", faculty_id=faculty_2.id)
            db.add(course_2)
            db.flush()
            created["courses"] += 1
        else:
            course_2.faculty_id = faculty_2.id

        student_profiles = [
            {
                "name": "Aman Verma",
                "email": "aman.student@gmail.com",
                "parent_email": "aman.parent@example.com",
                "department": "CSE",
                "semester": 3,
            },
            {
                "name": "Riya Kapoor",
                "email": "riya.student@gmail.com",
                "parent_email": "riya.parent@example.com",
                "department": "CSE",
                "semester": 3,
            },
            {
                "name": "Neha Sood",
                "email": "neha.student@gmail.com",
                "parent_email": "neha.parent@example.com",
                "department": "CSE",
                "semester": 3,
            },
        ]

        students_by_email: dict[str, models.Student] = {}
        for profile in student_profiles:
            student = db.query(models.Student).filter(models.Student.email == profile["email"]).first()
            if not student:
                student = models.Student(**profile)
                db.add(student)
                db.flush()
                created["students"] += 1
            students_by_email[profile["email"]] = student

        enrollment_pairs = [
            (students_by_email["aman.student@gmail.com"].id, course_1.id),
            (students_by_email["riya.student@gmail.com"].id, course_1.id),
            (students_by_email["neha.student@gmail.com"].id, course_1.id),
            (students_by_email["aman.student@gmail.com"].id, course_2.id),
            (students_by_email["riya.student@gmail.com"].id, course_2.id),
        ]
        for student_id, course_id in enrollment_pairs:
            exists = (
                db.query(models.Enrollment)
                .filter(models.Enrollment.student_id == student_id, models.Enrollment.course_id == course_id)
                .first()
            )
            if not exists:
                db.add(models.Enrollment(student_id=student_id, course_id=course_id))
                created["enrollments"] += 1

        classroom_1 = (
            db.query(models.Classroom)
            .filter(models.Classroom.block == "B1", models.Classroom.room_number == "201")
            .first()
        )
        if not classroom_1:
            classroom_1 = models.Classroom(block="B1", room_number="201", capacity=60)
            db.add(classroom_1)
            db.flush()
            created["classrooms"] += 1

        classroom_2 = (
            db.query(models.Classroom)
            .filter(models.Classroom.block == "B2", models.Classroom.room_number == "105")
            .first()
        )
        if not classroom_2:
            classroom_2 = models.Classroom(block="B2", room_number="105", capacity=40)
            db.add(classroom_2)
            db.flush()
            created["classrooms"] += 1

        for course_id, classroom_id in [(course_1.id, classroom_1.id), (course_2.id, classroom_2.id)]:
            assignment = (
                db.query(models.CourseClassroom)
                .filter(models.CourseClassroom.course_id == course_id)
                .first()
            )
            if assignment:
                assignment.classroom_id = classroom_id
            else:
                db.add(models.CourseClassroom(course_id=course_id, classroom_id=classroom_id))

        today = date.today()
        weekday_today = today.weekday()
        now_dt = datetime.now().replace(second=0, microsecond=0)
        demo_start = (now_dt - timedelta(minutes=2)).time()
        demo_end = (now_dt + timedelta(minutes=58)).time()
        if demo_end <= demo_start:
            demo_start = time(9, 0)
            demo_end = time(10, 0)
        schedule_specs = [
            (
                course_1.id,
                faculty_1.id,
                weekday_today,
                demo_start,
                demo_end,
                f"{classroom_1.block}-{classroom_1.room_number}",
            ),
            (
                course_2.id,
                faculty_2.id,
                (weekday_today + 1) % 7,
                time(11, 0),
                time(12, 0),
                f"{classroom_2.block}-{classroom_2.room_number}",
            ),
        ]
        for course_id, faculty_id, weekday, start_t, end_t, classroom_label in schedule_specs:
            existing_schedule = (
                db.query(models.ClassSchedule)
                .filter(
                    models.ClassSchedule.course_id == course_id,
                    models.ClassSchedule.weekday == weekday,
                )
                .first()
            )
            if existing_schedule:
                continue
            db.add(
                models.ClassSchedule(
                    course_id=course_id,
                    faculty_id=faculty_id,
                    weekday=weekday,
                    start_time=start_t,
                    end_time=end_t,
                    classroom_label=classroom_label,
                    is_active=True,
                )
            )
            created["schedules"] += 1

        food_items = [
            ("Veg Sandwich", 45.0),
            ("Pasta", 70.0),
            ("Lemon Soda", 30.0),
        ]
        for name, price in food_items:
            item = db.query(models.FoodItem).filter(models.FoodItem.name == name).first()
            if not item:
                db.add(models.FoodItem(name=name, price=price))

        slots = [
            ("Short Break", time(10, 30), time(10, 50), 80),
            ("Lunch", time(13, 0), time(14, 0), 150),
            ("Evening", time(16, 0), time(16, 20), 60),
        ]
        for label, start_t, end_t, max_orders in slots:
            slot = db.query(models.BreakSlot).filter(models.BreakSlot.label == label).first()
            if not slot:
                db.add(models.BreakSlot(label=label, start_time=start_t, end_time=end_t, max_orders=max_orders))

        attendance_exists = (
            db.query(models.AttendanceRecord)
            .filter(models.AttendanceRecord.course_id == course_1.id, models.AttendanceRecord.attendance_date == today)
            .count()
        )
        if not attendance_exists:
            demo_attendance = [
                (students_by_email["aman.student@gmail.com"].id, models.AttendanceStatus.PRESENT),
                (students_by_email["riya.student@gmail.com"].id, models.AttendanceStatus.ABSENT),
                (students_by_email["neha.student@gmail.com"].id, models.AttendanceStatus.PRESENT),
            ]
            for student_id, status_value in demo_attendance:
                append_attendance_event(
                    db,
                    student_id=int(student_id),
                    course_id=int(course_1.id),
                    attendance_date=today,
                    status=status_value,
                    source="demo-seed-attendance",
                    actor_faculty_id=int(faculty_1.id),
                    actor_role=models.UserRole.FACULTY,
                    note="Demo seed initialization",
                )
                recompute_attendance_record(
                    db,
                    student_id=int(student_id),
                    course_id=int(course_1.id),
                    attendance_date=today,
                )

        created["auth_users"] += int(
            ensure_auth_user(
                db,
                email="kavita.faculty@gmail.com",
                role=models.UserRole.FACULTY,
                password="Faculty@123",
                faculty_id=faculty_1.id,
            )
        )
        created["auth_users"] += int(
            ensure_auth_user(
                db,
                email="arjun.faculty@gmail.com",
                role=models.UserRole.FACULTY,
                password="Faculty@123",
                faculty_id=faculty_2.id,
            )
        )

        for student_email in ["aman.student@gmail.com", "riya.student@gmail.com", "neha.student@gmail.com"]:
            student = students_by_email[student_email]
            created["auth_users"] += int(
                ensure_auth_user(
                    db,
                    email=student_email,
                    role=models.UserRole.STUDENT,
                    password="Student@123",
                    student_id=student.id,
                )
            )

        db.commit()
        sync_sql_snapshot_to_mongo(db)

        return {
            "message": "Demo data seeding complete",
            "created": created,
            "demo_credentials": {
                "faculty_default_password": "Faculty@123",
                "student_default_password": "Student@123",
                "otp_flow": "Use /auth/login/request-otp then /auth/login/verify-otp",
            },
        }
    finally:
        db.close()
