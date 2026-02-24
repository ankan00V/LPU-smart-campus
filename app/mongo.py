import os
from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, MongoClient, ReturnDocument
from pymongo.errors import PyMongoError

_mongo_client: MongoClient | None = None
_mongo_db = None
_mongo_error: str | None = None
_last_init_attempt: datetime | None = None


def _bool_env(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name, "true" if default else "false") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int, minimum: int = 0) -> int:
    raw = (os.getenv(name, str(default)) or "").strip()
    try:
        value = int(raw)
    except ValueError:
        return max(minimum, default)
    return max(minimum, value)


def _mongo_uri() -> str:
    return (os.getenv("MONGO_URI") or os.getenv("MONGODB_URI") or "").strip()


def _mongo_db_name() -> str:
    return (
        os.getenv("MONGO_DB_NAME")
        or os.getenv("MONGODB_DB_NAME")
        or "lpu_smart_campus"
    ).strip() or "lpu_smart_campus"


def _ensure_indexes(db) -> None:
    db["students"].create_index([("id", ASCENDING)], unique=True)
    db["students"].create_index([("email", ASCENDING)], unique=True)
    student_indexes = {idx["name"]: idx for idx in db["students"].list_indexes()}
    reg_idx = student_indexes.get("registration_number_1")
    if reg_idx and not reg_idx.get("partialFilterExpression"):
        db["students"].drop_index("registration_number_1")
    db["students"].create_index(
        [("registration_number", ASCENDING)],
        unique=True,
        partialFilterExpression={"registration_number": {"$type": "string"}},
    )

    db["faculty"].create_index([("id", ASCENDING)], unique=True)
    db["faculty"].create_index([("email", ASCENDING)], unique=True)

    db["courses"].create_index([("id", ASCENDING)], unique=True)
    db["courses"].create_index([("code", ASCENDING)], unique=True)

    db["enrollments"].create_index([("id", ASCENDING)], unique=True)
    db["enrollments"].create_index([("student_id", ASCENDING), ("course_id", ASCENDING)], unique=True)

    db["classrooms"].create_index([("id", ASCENDING)], unique=True)
    db["classrooms"].create_index([("block", ASCENDING), ("room_number", ASCENDING)], unique=True)

    db["course_classrooms"].create_index([("id", ASCENDING)], unique=True)
    db["course_classrooms"].create_index([("course_id", ASCENDING)], unique=True)

    db["attendance_records"].create_index([("id", ASCENDING)], unique=True)
    db["attendance_records"].create_index(
        [("student_id", ASCENDING), ("course_id", ASCENDING), ("attendance_date", ASCENDING)],
        unique=True,
    )

    db["notification_logs"].create_index([("id", ASCENDING)], unique=True)

    db["food_items"].create_index([("id", ASCENDING)], unique=True)
    db["food_items"].create_index([("name", ASCENDING)], unique=True)

    db["break_slots"].create_index([("id", ASCENDING)], unique=True)
    db["break_slots"].create_index([("label", ASCENDING)], unique=True)

    db["food_orders"].create_index([("id", ASCENDING)], unique=True)
    db["food_orders"].create_index([("order_id", ASCENDING)], unique=True, partialFilterExpression={"order_id": {"$exists": True}})
    db["food_orders"].create_index([("student_id", ASCENDING), ("order_date", ASCENDING)])
    db["food_orders"].create_index([("shop_id", ASCENDING), ("order_date", ASCENDING)])
    db["food_orders"].create_index([("status", ASCENDING), ("created_at", ASCENDING)])
    db["food_orders"].create_index(
        [("student_id", ASCENDING), ("order_date", ASCENDING), ("idempotency_key", ASCENDING)],
        unique=True,
        partialFilterExpression={"idempotency_key": {"$type": "string"}},
    )

    db["food_shops"].create_index([("shop_id", ASCENDING)], unique=True)
    db["food_shops"].create_index([("name", ASCENDING), ("block", ASCENDING)], unique=True)
    db["food_shops"].create_index([("owner_user_id", ASCENDING), ("is_active", ASCENDING)])
    db["food_shops"].create_index([("block", ASCENDING), ("is_active", ASCENDING)])

    db["food_menu_items"].create_index([("menu_item_id", ASCENDING)], unique=True)
    db["food_menu_items"].create_index([("shop_id", ASCENDING), ("name", ASCENDING)], unique=True)
    db["food_menu_items"].create_index([("shop_id", ASCENDING), ("is_active", ASCENDING), ("sold_out", ASCENDING)])

    db["food_carts"].create_index([("student_id", ASCENDING)], unique=True)
    db["food_carts"].create_index([("updated_at", ASCENDING)])
    db["food_carts"].create_index([("shop_id", ASCENDING), ("updated_at", ASCENDING)])

    db["food_payments"].create_index([("payment_id", ASCENDING)], unique=True, partialFilterExpression={"payment_id": {"$exists": True}})
    db["food_payments"].create_index([("payment_reference", ASCENDING)], unique=True)
    db["food_payments"].create_index([("provider_order_id", ASCENDING)])
    db["food_payments"].create_index([("provider_payment_id", ASCENDING)])
    db["food_payments"].create_index([("student_id", ASCENDING), ("created_at", ASCENDING)])
    db["food_payments"].create_index([("status", ASCENDING), ("created_at", ASCENDING)])

    db["payment_webhook_events"].create_index(
        [("provider", ASCENDING), ("event_id", ASCENDING)],
        unique=True,
        partialFilterExpression={"event_id": {"$type": "string"}},
    )
    db["payment_webhook_events"].create_index([("provider", ASCENDING), ("fingerprint", ASCENDING)], unique=True)
    db["payment_webhook_events"].create_index([("created_at", ASCENDING)])

    db["food_order_audit"].create_index([("order_id", ASCENDING), ("created_at", ASCENDING)])
    db["food_order_audit"].create_index([("event_type", ASCENDING), ("created_at", ASCENDING)])

    db["makeup_classes"].create_index([("id", ASCENDING)], unique=True)
    db["makeup_classes"].create_index([("remedial_code", ASCENDING)], unique=True)

    db["remedial_attendance"].create_index([("id", ASCENDING)], unique=True)
    db["remedial_attendance"].create_index(
        [("makeup_class_id", ASCENDING), ("student_id", ASCENDING)],
        unique=True,
    )

    db["class_schedules"].create_index([("id", ASCENDING)], unique=True)
    db["class_schedules"].create_index(
        [("course_id", ASCENDING), ("weekday", ASCENDING), ("start_time", ASCENDING)],
        unique=True,
    )

    db["attendance_submissions"].create_index([("id", ASCENDING)], unique=True)
    db["attendance_submissions"].create_index(
        [("schedule_id", ASCENDING), ("student_id", ASCENDING), ("class_date", ASCENDING)],
        unique=True,
    )

    db["classroom_analyses"].create_index([("id", ASCENDING)], unique=True)

    db["auth_users"].create_index([("id", ASCENDING)], unique=True)
    db["auth_users"].create_index([("email", ASCENDING)], unique=True)
    db["auth_users"].create_index(
        [("alternate_email", ASCENDING)],
        unique=True,
        partialFilterExpression={"alternate_email": {"$type": "string"}},
    )

    # Replace old sparse unique indexes so multiple admin/faculty/student-null docs are allowed.
    auth_indexes = {idx["name"]: idx for idx in db["auth_users"].list_indexes()}
    student_idx = auth_indexes.get("student_id_1")
    if student_idx and not student_idx.get("partialFilterExpression"):
        db["auth_users"].drop_index("student_id_1")
    faculty_idx = auth_indexes.get("faculty_id_1")
    if faculty_idx and not faculty_idx.get("partialFilterExpression"):
        db["auth_users"].drop_index("faculty_id_1")

    db["auth_users"].create_index(
        [("student_id", ASCENDING)],
        unique=True,
        partialFilterExpression={"student_id": {"$type": "int"}},
    )
    db["auth_users"].create_index(
        [("faculty_id", ASCENDING)],
        unique=True,
        partialFilterExpression={"faculty_id": {"$type": "int"}},
    )

    db["auth_otps"].create_index([("id", ASCENDING)], unique=True)
    db["auth_otps"].create_index([("user_id", ASCENDING), ("purpose", ASCENDING), ("created_at", ASCENDING)])
    db["auth_otps"].create_index(
        [("expires_at", ASCENDING)],
        expireAfterSeconds=0,
        name="otp_expiry_ttl",
    )

    db["auth_otp_delivery"].create_index([("id", ASCENDING)], unique=True)
    db["auth_otp_delivery"].create_index(
        [("created_at", ASCENDING)],
        expireAfterSeconds=_otp_delivery_retention_seconds(),
        name="otp_delivery_retention_ttl",
    )
    db["auth_password_resets"].create_index([("id", ASCENDING)], unique=True)
    db["auth_password_resets"].create_index([("user_id", ASCENDING), ("created_at", ASCENDING)])
    db["auth_password_resets"].create_index(
        [("expires_at", ASCENDING)],
        expireAfterSeconds=0,
        name="password_reset_expiry_ttl",
    )

    db["event_stream"].create_index([("created_at", ASCENDING)])
    db["static_assets"].create_index([("key", ASCENDING)], unique=True)


def _retry_cooldown_seconds() -> int:
    value = os.getenv("MONGODB_RETRY_COOLDOWN_SECONDS", "60").strip()
    try:
        return max(0, int(value))
    except ValueError:
        return 60


def _otp_delivery_retention_seconds() -> int:
    value = os.getenv("OTP_DELIVERY_RETENTION_DAYS", "14").strip()
    try:
        days = max(1, int(value))
    except ValueError:
        days = 14
    return days * 24 * 60 * 60


def mongo_persistence_required() -> bool:
    raw = (os.getenv("MONGO_PERSISTENCE_REQUIRED", "true") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def init_mongo(force: bool = False) -> bool:
    global _mongo_client, _mongo_db, _mongo_error, _last_init_attempt

    uri = _mongo_uri()
    if not uri:
        _mongo_client = None
        _mongo_db = None
        _mongo_error = "MONGODB_URI is not configured"
        return False

    now = datetime.now(timezone.utc)
    if (
        not force
        and _mongo_db is None
        and _last_init_attempt is not None
        and (now - _last_init_attempt).total_seconds() < _retry_cooldown_seconds()
    ):
        return False
    _last_init_attempt = now

    try:
        mongo_kwargs: dict[str, Any] = {
            # Atlas SRV resolution + replica discovery can intermittently exceed 5s.
            "serverSelectionTimeoutMS": _int_env("MONGO_SERVER_SELECTION_TIMEOUT_MS", 15000, minimum=1000),
            "connectTimeoutMS": _int_env("MONGO_CONNECT_TIMEOUT_MS", 10000, minimum=1000),
            "socketTimeoutMS": _int_env("MONGO_SOCKET_TIMEOUT_MS", 20000, minimum=1000),
            "tls": True,
        }

        ca_file = (os.getenv("MONGO_TLS_CA_FILE") or "").strip()
        if not ca_file:
            try:
                import certifi  # type: ignore
                ca_file = certifi.where()
            except Exception:
                ca_file = ""
        if ca_file:
            mongo_kwargs["tlsCAFile"] = ca_file

        if _bool_env("MONGO_TLS_DISABLE_OCSP_ENDPOINT_CHECK", default=False):
            mongo_kwargs["tlsDisableOCSPEndpointCheck"] = True
        if _bool_env("MONGO_TLS_ALLOW_INVALID_CERTIFICATES", default=False):
            mongo_kwargs["tlsAllowInvalidCertificates"] = True
        if _bool_env("MONGO_TLS_ALLOW_INVALID_HOSTNAMES", default=False):
            mongo_kwargs["tlsAllowInvalidHostnames"] = True

        client = MongoClient(uri, **mongo_kwargs)
        client.admin.command("ping")
        _mongo_client = client
        _mongo_db = client[_mongo_db_name()]
        _ensure_indexes(_mongo_db)
        _mongo_error = None
        return True
    except PyMongoError as exc:
        _mongo_client = None
        _mongo_db = None
        _mongo_error = str(exc)
        return False


def close_mongo() -> None:
    global _mongo_client, _mongo_db, _last_init_attempt

    if _mongo_client is not None:
        _mongo_client.close()
    _mongo_client = None
    _mongo_db = None
    _last_init_attempt = None


def _get_mongo_db():
    if _mongo_db is None:
        init_mongo()
    return _mongo_db


def get_mongo_db(required: bool = False):
    db = _get_mongo_db()
    if required and db is None:
        raise RuntimeError(_mongo_error or "MongoDB is unavailable")
    return db


def mongo_status() -> dict[str, Any]:
    enabled = _get_mongo_db() is not None
    return {
        "enabled": enabled,
        "database": _mongo_db_name() if enabled else None,
        "error": None if enabled else _mongo_error,
    }


def mirror_document(
    collection_name: str,
    payload: dict[str, Any],
    *,
    required: bool | None = None,
    upsert_filter: dict[str, Any] | None = None,
) -> bool:
    global _mongo_error

    must_persist = mongo_persistence_required() if required is None else bool(required)
    db = get_mongo_db(required=must_persist)
    if db is None:
        return False

    doc = dict(payload)
    doc.setdefault("synced_at", datetime.now(timezone.utc))

    try:
        if upsert_filter:
            db[collection_name].update_one(dict(upsert_filter), {"$set": doc}, upsert=True)
        else:
            db[collection_name].insert_one(doc)
        return True
    except PyMongoError as exc:
        _mongo_error = str(exc)
        if must_persist:
            raise RuntimeError(_mongo_error) from exc
        return False


def next_sequence(name: str) -> int:
    db = get_mongo_db(required=True)
    row = db["counters"].find_one_and_update(
        {"_id": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    seq = row.get("seq") if row else None
    return int(seq or 1)


def mirror_event(
    event_type: str,
    payload: dict[str, Any] | None = None,
    *,
    source: str = "api",
    actor: dict[str, Any] | None = None,
    required: bool | None = None,
) -> bool:
    return mirror_document(
        "event_stream",
        {
            "event_type": event_type,
            "source": source,
            "actor": actor or {},
            "payload": payload or {},
            "created_at": datetime.now(timezone.utc),
        },
        required=required,
    )
