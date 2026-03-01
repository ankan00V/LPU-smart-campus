import os
import logging
from decimal import Decimal
from datetime import date, datetime, time, timedelta
from enum import Enum as PyEnum
from pathlib import Path
import time as pytime
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pymongo.errors import DuplicateKeyError
from sqlalchemy import inspect as sa_inspect, text
from sqlalchemy.orm import Session

from . import models
from .auth_utils import hash_password, require_roles
from .database import Base, SessionLocal, engine
from .food_bootstrap import bootstrap_food_hall_catalog
from .mongo import (
    close_mongo,
    get_mongo_db,
    init_mongo,
    mongo_persistence_required,
    mongo_status,
    next_sequence,
)
from .routers import (
    admin_router,
    assets_router,
    attendance_router,
    auth_router,
    food_router,
    makeup_router,
    messages_router,
    people_router,
    resources_router,
)
from .routers.assets import seed_static_assets_to_mongo

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LPU Smart Campus Management API",
    version="0.2.0",
    description=(
        "Smart Campus backend with mandatory modules + role-based auth + OTP login."
    ),
)
ALLOW_DEMO_SEED = os.getenv("ALLOW_DEMO_SEED", "false").strip().lower() in {"1", "true", "yes"}


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

Base.metadata.create_all(bind=engine)
apply_sqlite_migrations()

app.include_router(assets_router)
app.include_router(auth_router)
app.include_router(people_router)
app.include_router(attendance_router)
app.include_router(food_router)
app.include_router(resources_router)
app.include_router(admin_router)
app.include_router(makeup_router)
app.include_router(messages_router)

WEB_DIR = PROJECT_ROOT / "web"
if WEB_DIR.exists():
    app.mount("/web", StaticFiles(directory=WEB_DIR), name="web")


@app.get("/")
def health_check():
    return {
        "message": "Smart Campus Management API is running",
        "docs": "/docs",
        "ui": "/ui",
        "mongo": mongo_status(),
    }


@app.get("/ui", include_in_schema=False)
def ui():
    index_file = WEB_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "UI is not available. Ensure web/index.html exists."}


def _ui_logo_file() -> Path:
    return WEB_DIR / "assets" / "lpu-smart-campus-logo.png"


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    logo_file = _ui_logo_file()
    if logo_file.exists():
        return FileResponse(logo_file, media_type="image/png")
    raise HTTPException(status_code=404, detail="Favicon not found")


@app.get("/apple-touch-icon.png", include_in_schema=False)
def apple_touch_icon():
    logo_file = _ui_logo_file()
    if logo_file.exists():
        return FileResponse(logo_file, media_type="image/png")
    raise HTTPException(status_code=404, detail="Apple touch icon not found")


@app.get("/apple-touch-icon-precomposed.png", include_in_schema=False)
def apple_touch_icon_precomposed():
    logo_file = _ui_logo_file()
    if logo_file.exists():
        return FileResponse(logo_file, media_type="image/png")
    raise HTTPException(status_code=404, detail="Apple touch icon not found")


@app.on_event("startup")
def startup_event() -> None:
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
        ok = init_mongo(force=True)
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


@app.on_event("shutdown")
def shutdown_event() -> None:
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
    mongo_db = get_mongo_db()
    if mongo_db is None:
        return

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
                logger.warning(
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
        models.ClassSchedule,
        models.AttendanceSubmission,
        models.ClassroomAnalysis,
        models.AuthOTP,
        models.AuthOTPDelivery,
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

    auth_collection = mongo_db["auth_users"]
    for auth_user in db.query(models.AuthUser).all():
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
            db.add_all(
                [
                    models.AttendanceRecord(
                        student_id=students_by_email["aman.student@gmail.com"].id,
                        course_id=course_1.id,
                        marked_by_faculty_id=faculty_1.id,
                        attendance_date=today,
                        status=models.AttendanceStatus.PRESENT,
                        source="faculty-web",
                    ),
                    models.AttendanceRecord(
                        student_id=students_by_email["riya.student@gmail.com"].id,
                        course_id=course_1.id,
                        marked_by_faculty_id=faculty_1.id,
                        attendance_date=today,
                        status=models.AttendanceStatus.ABSENT,
                        source="faculty-web",
                    ),
                    models.AttendanceRecord(
                        student_id=students_by_email["neha.student@gmail.com"].id,
                        course_id=course_1.id,
                        marked_by_faculty_id=faculty_1.id,
                        attendance_date=today,
                        status=models.AttendanceStatus.PRESENT,
                        source="faculty-web",
                    ),
                ]
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
