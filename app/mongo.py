import logging
import os
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qsl, urlencode
from urllib.parse import SplitResult

from pymongo import ASCENDING, MongoClient, ReturnDocument
from pymongo.errors import PyMongoError

from .enterprise_controls import apply_pii_encryption_policy
from .realtime_bus import infer_topics, publish_domain_event
from .runtime_infra import is_remote_service_host, normalize_host, split_url

_mongo_client: MongoClient | None = None
_mongo_db = None
_mongo_error: str | None = None
_last_init_attempt: datetime | None = None
LOGGER = logging.getLogger(__name__)

try:
    import dns.resolver as dns_resolver
except Exception:  # noqa: BLE001
    dns_resolver = None


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


def _mongo_uri_fallback() -> str:
    return (os.getenv("MONGO_URI_FALLBACK") or os.getenv("MONGODB_URI_FALLBACK") or "").strip()


def _mongo_db_name() -> str:
    return (
        os.getenv("MONGO_DB_NAME")
        or os.getenv("MONGODB_DB_NAME")
        or "lpu_smart_campus"
    ).strip() or "lpu_smart_campus"


def _mongo_dns_nameservers() -> list[str]:
    raw = (os.getenv("MONGO_DNS_NAMESERVERS") or "1.1.1.1,8.8.8.8").strip()
    return [token.strip() for token in raw.split(",") if token.strip()]


def _mongo_dns_resolver():
    if dns_resolver is None:
        return None
    resolver = dns_resolver.Resolver(configure=False)
    nameservers = _mongo_dns_nameservers()
    if nameservers:
        resolver.nameservers = nameservers
    resolver.lifetime = max(1.0, float(_int_env("MONGO_DNS_LIFETIME_SECONDS", 10, minimum=1)))
    resolver.timeout = max(1.0, float(_int_env("MONGO_DNS_TIMEOUT_SECONDS", 5, minimum=1)))
    return resolver


def _merge_query_params(*parts: str) -> str:
    merged: dict[str, str] = {}
    for part in parts:
        for key, value in parse_qsl(str(part or "").strip(), keep_blank_values=True):
            merged[key] = value
    if "tls" not in merged and "ssl" not in merged:
        merged["tls"] = "true"
    return urlencode(merged)


def _mongo_hostname_fallback_uri(uri: str) -> str | None:
    raw_uri = str(uri or "").strip()
    if not raw_uri:
        return None
    parts = _mongo_url_parts(raw_uri)
    if str(parts.scheme or "").strip().lower() != "mongodb+srv":
        return None

    netloc = str(parts.netloc or "")
    if "@" in netloc:
        userinfo, host = netloc.rsplit("@", 1)
        userinfo = f"{userinfo}@"
    else:
        userinfo = ""
        host = netloc
    host = normalize_host(host)
    if not host:
        return None

    resolver = _mongo_dns_resolver()
    if resolver is None:
        return None

    try:
        srv_records = resolver.resolve(f"_mongodb._tcp.{host}", "SRV")
    except Exception:
        return None

    hosts: list[str] = []
    for record in srv_records:
        target = normalize_host(str(getattr(record, "target", "")).rstrip("."))
        port = int(getattr(record, "port", 27017) or 27017)
        if target:
            hosts.append(f"{target}:{port}")
    if not hosts:
        return None

    txt_query = ""
    try:
        txt_records = resolver.resolve(host, "TXT")
        txt_parts: list[str] = []
        for record in txt_records:
            if hasattr(record, "strings"):
                txt_parts.extend(
                    chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk)
                    for chunk in record.strings
                )
            elif hasattr(record, "to_text"):
                txt_parts.append(str(record.to_text()).strip('"'))
        txt_query = "&".join(part for part in txt_parts if part)
    except Exception:
        txt_query = ""

    query = _merge_query_params(txt_query, parts.query)
    path = parts.path or ""
    return f"mongodb://{userinfo}{','.join(hosts)}{path}?{query}"


def _strict_runtime_enabled() -> bool:
    return _bool_env("APP_RUNTIME_STRICT", default=True)


def _mongo_url_parts(value: str | None = None) -> SplitResult:
    return split_url(value if value is not None else _mongo_uri())


def _mongo_scheme(value: str | None = None) -> str | None:
    scheme = str(_mongo_url_parts(value).scheme or "").strip().lower()
    return scheme or None


def _mongo_hosts(value: str | None = None) -> list[str]:
    netloc = str(_mongo_url_parts(value).netloc or "")
    if "@" in netloc:
        netloc = netloc.rsplit("@", 1)[-1]
    hosts: list[str] = []
    for segment in netloc.split(","):
        chunk = segment.strip()
        if not chunk:
            continue
        host = chunk
        if chunk.startswith("[") and "]" in chunk:
            host = chunk[1:].split("]", 1)[0]
        elif ":" in chunk:
            host = chunk.split(":", 1)[0]
        normalized = normalize_host(host)
        if normalized:
            hosts.append(normalized)
    return hosts


def _mongo_tls_enabled() -> bool:
    scheme = _mongo_scheme()
    if scheme == "mongodb+srv":
        return True
    query = {
        str(key or "").strip().lower(): str(value or "").strip().lower()
        for key, value in parse_qsl(str(_mongo_url_parts().query or ""), keep_blank_values=True)
    }
    for name in ("tls", "ssl"):
        if name not in query:
            continue
        return query[name] in {"1", "true", "yes", "on", "required"}
    return False


def _ensure_indexes(db) -> None:
    db["students"].create_index([("id", ASCENDING)], unique=True)
    db["students"].create_index([("email", ASCENDING)], unique=True)
    db["students"].create_index([("section", ASCENDING), ("department", ASCENDING)])
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
    db["faculty"].create_index(
        [("faculty_identifier", ASCENDING)],
        unique=True,
        partialFilterExpression={"faculty_identifier": {"$type": "string"}},
    )

    db["courses"].create_index([("id", ASCENDING)], unique=True)
    db["courses"].create_index([("code", ASCENDING)], unique=True)

    db["enrollments"].create_index([("id", ASCENDING)], unique=True)
    db["enrollments"].create_index([("student_id", ASCENDING), ("course_id", ASCENDING)], unique=True)

    db["classrooms"].create_index([("id", ASCENDING)], unique=True)
    db["classrooms"].create_index([("block", ASCENDING), ("room_number", ASCENDING)], unique=True)

    db["course_classrooms"].create_index([("id", ASCENDING)], unique=True)
    db["course_classrooms"].create_index([("course_id", ASCENDING)], unique=True)
    db["course_classrooms"].create_index([("classroom_id", ASCENDING)])

    db["blocks"].create_index([("block", ASCENDING)], unique=True)
    db["blocks"].create_index([("updated_at", ASCENDING)])

    db["timetable"].create_index([("schedule_id", ASCENDING)], unique=True)
    db["timetable"].create_index([("weekday", ASCENDING), ("start_time", ASCENDING)])
    db["timetable"].create_index([("faculty_id", ASCENDING), ("weekday", ASCENDING), ("start_time", ASCENDING)])
    db["timetable"].create_index([("classroom_id", ASCENDING), ("weekday", ASCENDING), ("start_time", ASCENDING)])

    db["admin_summary_snapshots"].create_index([("created_at", ASCENDING)])
    db["admin_summary_snapshots"].create_index([("work_date", ASCENDING), ("created_at", ASCENDING)])
    db["admin_alerts"].create_index([("id", ASCENDING)], unique=True)
    db["admin_alerts"].create_index([("issue_type", ASCENDING), ("severity", ASCENDING)])
    db["admin_alerts"].create_index([("updated_at", ASCENDING)])
    db["admin_audit_logs"].create_index([("created_at", ASCENDING)])
    db["admin_audit_logs"].create_index([("action", ASCENDING), ("created_at", ASCENDING)])
    db["resource_allocations"].create_index([("course_id", ASCENDING)], unique=True)
    db["resource_allocations"].create_index([("classroom_id", ASCENDING)])

    db["attendance_records"].create_index([("id", ASCENDING)], unique=True)
    db["attendance_records"].create_index(
        [("student_id", ASCENDING), ("course_id", ASCENDING), ("attendance_date", ASCENDING)],
        unique=True,
    )
    db["attendance_records"].create_index([("updated_at", ASCENDING)])
    db["attendance_records"].create_index([("computed_from_event_id", ASCENDING)])
    db["attendance_events"].create_index([("id", ASCENDING)], unique=True)
    db["attendance_events"].create_index([("event_key", ASCENDING)], unique=True)
    db["attendance_events"].create_index(
        [("student_id", ASCENDING), ("course_id", ASCENDING), ("attendance_date", ASCENDING), ("created_at", ASCENDING)]
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
    db["makeup_classes"].create_index([("class_date", ASCENDING), ("start_time", ASCENDING)])
    db["makeup_classes"].create_index([("faculty_id", ASCENDING), ("class_date", ASCENDING)])
    db["makeup_classes"].create_index([("code_expires_at", ASCENDING)])
    db["makeup_classes"].create_index([("sections", ASCENDING)])

    db["remedial_attendance"].create_index([("id", ASCENDING)], unique=True)
    db["remedial_attendance"].create_index(
        [("makeup_class_id", ASCENDING), ("student_id", ASCENDING)],
        unique=True,
    )
    db["remedial_attendance"].create_index([("student_id", ASCENDING), ("marked_at", ASCENDING)])

    db["remedial_messages"].create_index([("id", ASCENDING)], unique=True)
    db["remedial_messages"].create_index(
        [("makeup_class_id", ASCENDING), ("student_id", ASCENDING)],
        unique=True,
    )
    db["remedial_messages"].create_index([("student_id", ASCENDING), ("created_at", ASCENDING)])
    db["remedial_messages"].create_index([("section", ASCENDING), ("created_at", ASCENDING)])

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
    db["attendance_rectification_requests"].create_index([("id", ASCENDING)], unique=True)
    db["attendance_rectification_requests"].create_index(
        [("student_id", ASCENDING), ("schedule_id", ASCENDING), ("class_date", ASCENDING)],
        unique=True,
    )
    db["attendance_rectification_requests"].create_index(
        [("faculty_id", ASCENDING), ("schedule_id", ASCENDING), ("status", ASCENDING), ("requested_at", ASCENDING)]
    )

    db["classroom_analyses"].create_index([("id", ASCENDING)], unique=True)
    db["student_grades"].create_index([("id", ASCENDING)], unique=True)
    db["student_grades"].create_index([("student_id", ASCENDING), ("course_id", ASCENDING)], unique=True)
    db["student_grades"].create_index([("faculty_id", ASCENDING), ("graded_at", ASCENDING)])
    db["student_grades"].create_index([("grade_letter", ASCENDING), ("graded_at", ASCENDING)])

    db["auth_users"].create_index([("id", ASCENDING)], unique=True)
    db["auth_users"].create_index([("email", ASCENDING)], unique=True)
    db["auth_users"].create_index(
        [("alternate_email", ASCENDING)],
        unique=True,
        partialFilterExpression={"alternate_email": {"$type": "string"}},
    )
    db["auth_users"].create_index(
        [("alternate_email_hash", ASCENDING)],
        unique=True,
        partialFilterExpression={"alternate_email_hash": {"$type": "string"}},
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
    db["auth_sessions"].create_index([("sid", ASCENDING)], unique=True)
    db["auth_sessions"].create_index([("user_id", ASCENDING), ("revoked_at", ASCENDING), ("refresh_expires_at", ASCENDING)])
    db["auth_sessions"].create_index(
        [("refresh_expires_at", ASCENDING)],
        expireAfterSeconds=0,
        name="auth_session_expiry_ttl",
    )
    db["auth_token_revocations"].create_index([("jti", ASCENDING)], unique=True)
    db["auth_token_revocations"].create_index([("sid", ASCENDING), ("created_at", ASCENDING)])
    db["auth_token_revocations"].create_index(
        [("expires_at", ASCENDING)],
        expireAfterSeconds=0,
        name="auth_token_revocation_expiry_ttl",
    )
    db["auth_role_invites"].create_index([("id", ASCENDING)], unique=True)
    db["auth_role_invites"].create_index([("token_hash", ASCENDING), ("token_salt", ASCENDING)])
    db["auth_role_invites"].create_index([("email", ASCENDING), ("role", ASCENDING), ("used_at", ASCENDING)])
    db["auth_role_invites"].create_index(
        [("expires_at", ASCENDING)],
        expireAfterSeconds=0,
        name="auth_role_invite_expiry_ttl",
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

    db["identity_verification_cases"].create_index([("id", ASCENDING)], unique=True)
    db["identity_verification_cases"].create_index([("workflow_key", ASCENDING), ("status", ASCENDING), ("created_at", ASCENDING)])
    db["identity_verification_cases"].create_index([("student_id", ASCENDING), ("created_at", ASCENDING)])
    db["identity_verification_cases"].create_index([("auth_user_id", ASCENDING), ("created_at", ASCENDING)])
    db["identity_verification_cases"].create_index([("applicant_email", ASCENDING), ("created_at", ASCENDING)])

    db["identity_risk_signals"].create_index([("id", ASCENDING)], unique=True)
    db["identity_risk_signals"].create_index([("case_id", ASCENDING), ("created_at", ASCENDING)])
    db["identity_risk_signals"].create_index([("signal_type", ASCENDING), ("severity", ASCENDING), ("created_at", ASCENDING)])

    db["identity_verification_artifacts"].create_index([("id", ASCENDING)], unique=True)
    db["identity_verification_artifacts"].create_index([("case_id", ASCENDING), ("created_at", ASCENDING)])
    db["identity_verification_artifacts"].create_index([("artifact_type", ASCENDING), ("created_at", ASCENDING)])

    db["identity_device_profiles"].create_index([("device_fingerprint", ASCENDING)], unique=True)
    db["identity_device_profiles"].create_index([("linked_user_ids", ASCENDING), ("updated_at", ASCENDING)])
    db["identity_device_profiles"].create_index([("linked_student_ids", ASCENDING), ("updated_at", ASCENDING)])
    db["identity_device_profiles"].create_index([("linked_applicant_email_hashes", ASCENDING), ("updated_at", ASCENDING)])
    db["identity_device_profiles"].create_index([("linked_external_subject_keys", ASCENDING), ("updated_at", ASCENDING)])

    db["event_stream"].create_index([("created_at", ASCENDING)])
    db["compliance_retention_runs"].create_index([("id", ASCENDING)], unique=True)
    db["compliance_retention_runs"].create_index([("created_at", ASCENDING)])
    db["compliance_deletion_requests"].create_index([("id", ASCENDING)], unique=True)
    db["compliance_deletion_requests"].create_index([("email", ASCENDING), ("created_at", ASCENDING)])
    db["compliance_deletion_requests"].create_index([("status", ASCENDING), ("created_at", ASCENDING)])
    db["compliance_deletion_requests"].create_index([("legal_hold", ASCENDING), ("created_at", ASCENDING)])
    db["compliance_evidence_packages"].create_index([("id", ASCENDING)], unique=True)
    db["compliance_evidence_packages"].create_index([("created_at", ASCENDING)])
    db["security_key_rotation_runs"].create_index([("id", ASCENDING)], unique=True)
    db["security_key_rotation_runs"].create_index([("created_at", ASCENDING)])
    db["dr_backups"].create_index([("id", ASCENDING)], unique=True)
    db["dr_backups"].create_index([("backup_id", ASCENDING)], unique=True)
    db["dr_backups"].create_index([("created_at", ASCENDING)])
    db["dr_restore_drills"].create_index([("id", ASCENDING)], unique=True)
    db["dr_restore_drills"].create_index([("started_at", ASCENDING)])
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
    fallback_uri = _mongo_uri_fallback()
    uri_candidates: list[str] = []
    if uri:
        uri_candidates.append(uri)
        hostname_fallback = _mongo_hostname_fallback_uri(uri)
        if hostname_fallback and hostname_fallback not in uri_candidates:
            uri_candidates.append(hostname_fallback)
    if fallback_uri and fallback_uri not in uri_candidates:
        uri_candidates.append(fallback_uri)

    if not uri_candidates:
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

    mongo_kwargs: dict[str, Any] = {
        # Atlas SRV resolution + replica discovery can intermittently exceed 5s.
        "serverSelectionTimeoutMS": _int_env("MONGO_SERVER_SELECTION_TIMEOUT_MS", 15000, minimum=1000),
        "connectTimeoutMS": _int_env("MONGO_CONNECT_TIMEOUT_MS", 10000, minimum=1000),
        "socketTimeoutMS": _int_env("MONGO_SOCKET_TIMEOUT_MS", 20000, minimum=1000),
    }
    tls_enabled = _mongo_tls_enabled()
    if tls_enabled:
        mongo_kwargs["tls"] = True

    ca_file = (os.getenv("MONGO_TLS_CA_FILE") or "").strip()
    if tls_enabled and not ca_file:
        try:
            import certifi  # type: ignore
            ca_file = certifi.where()
        except Exception:
            ca_file = ""
    if tls_enabled and ca_file:
        mongo_kwargs["tlsCAFile"] = ca_file

    if tls_enabled and _bool_env("MONGO_TLS_DISABLE_OCSP_ENDPOINT_CHECK", default=False):
        mongo_kwargs["tlsDisableOCSPEndpointCheck"] = True
    if tls_enabled and _bool_env("MONGO_TLS_ALLOW_INVALID_CERTIFICATES", default=False):
        mongo_kwargs["tlsAllowInvalidCertificates"] = True
    if tls_enabled and _bool_env("MONGO_TLS_ALLOW_INVALID_HOSTNAMES", default=False):
        mongo_kwargs["tlsAllowInvalidHostnames"] = True

    errors: list[str] = []
    for idx, candidate_uri in enumerate(uri_candidates):
        try:
            client = MongoClient(candidate_uri, **mongo_kwargs)
            client.admin.command("ping")
            _mongo_client = client
            _mongo_db = client[_mongo_db_name()]
            _ensure_indexes(_mongo_db)
            _mongo_error = None
            return True
        except PyMongoError as exc:
            errors.append(f"candidate[{idx + 1}] failed: {exc}")

    _mongo_client = None
    _mongo_db = None
    _mongo_error = " | ".join(errors) if errors else "MongoDB connection failed"
    return False


def close_mongo() -> None:
    global _mongo_client, _mongo_db, _last_init_attempt

    if _mongo_client is not None:
        _mongo_client.close()
    _mongo_client = None
    _mongo_db = None
    _last_init_attempt = None


def invalidate_mongo_connection(exc: Exception | None = None) -> None:
    global _mongo_client, _mongo_db, _mongo_error, _last_init_attempt

    if exc is not None:
        _mongo_error = str(exc)
        LOGGER.warning("MongoDB connection invalidated after operation failure: %s", exc)

    if _mongo_client is not None:
        try:
            _mongo_client.close()
        except Exception:
            pass

    _mongo_client = None
    _mongo_db = None
    _last_init_attempt = datetime.now(timezone.utc)


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
    hosts = _mongo_hosts()
    remote_host = bool(hosts) and all(is_remote_service_host(host) for host in hosts)
    return {
        "enabled": enabled,
        "database": _mongo_db_name() if enabled else None,
        "uri_scheme": _mongo_scheme(),
        "host": hosts[0] if hosts else None,
        "hosts": hosts,
        "remote_host": remote_host,
        "tls_enabled": _mongo_tls_enabled(),
        "error": None if enabled else _mongo_error,
    }


def _sql_outbox_enabled() -> bool:
    raw = (os.getenv("SQL_OUTBOX_ENABLED", "true") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _enqueue_sql_outbox(
    collection_name: str,
    payload: dict[str, Any],
    *,
    upsert_filter: dict[str, Any] | None,
    required: bool,
) -> None:
    if not _sql_outbox_enabled():
        return

    try:
        from .database import SessionLocal
        from .outbox import dispatch_outbox_batch, enqueue_mongo_upsert
    except Exception:
        return

    session = SessionLocal()
    try:
        enqueue_mongo_upsert(
            session,
            collection_name=collection_name,
            payload=payload,
            upsert_filter=upsert_filter,
            required=required,
        )
        session.commit()
        dispatch_outbox_batch(session, limit=20)
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


def mirror_document(
    collection_name: str,
    payload: dict[str, Any],
    *,
    required: bool | None = None,
    upsert_filter: dict[str, Any] | None = None,
    allow_outbox: bool = True,
) -> bool:
    global _mongo_error

    must_persist = mongo_persistence_required() if required is None else bool(required)
    if _strict_runtime_enabled() and mongo_persistence_required():
        must_persist = True
    doc = apply_pii_encryption_policy(collection_name, payload)
    doc.setdefault("synced_at", datetime.now(timezone.utc))

    db = get_mongo_db(required=must_persist)
    if db is None:
        if allow_outbox:
            _enqueue_sql_outbox(
                collection_name,
                dict(doc),
                upsert_filter=upsert_filter,
                required=must_persist,
            )
        return False

    try:
        if upsert_filter:
            db[collection_name].update_one(dict(upsert_filter), {"$set": doc}, upsert=True)
        else:
            db[collection_name].insert_one(doc)
        return True
    except PyMongoError as exc:
        invalidate_mongo_connection(exc)
        if allow_outbox:
            _enqueue_sql_outbox(
                collection_name,
                doc,
                upsert_filter=upsert_filter,
                required=must_persist,
            )
        if must_persist:
            raise RuntimeError(_mongo_error) from exc
        return False


def next_sequence(name: str) -> int:
    db = get_mongo_db(required=True)
    try:
        row = db["counters"].find_one_and_update(
            {"_id": name},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
    except PyMongoError as exc:
        # Atlas failover windows can temporarily drop the writable primary.
        # Force one immediate reconnect attempt before failing.
        if not init_mongo(force=True):
            raise RuntimeError(_mongo_error or str(exc)) from exc
        db = get_mongo_db(required=True)
        try:
            row = db["counters"].find_one_and_update(
                {"_id": name},
                {"$inc": {"seq": 1}},
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError as retry_exc:
            raise RuntimeError(str(retry_exc)) from retry_exc

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
    actor_payload = actor or {}
    realtime_scopes: set[str] = {"role:admin"}
    actor_user_id = actor_payload.get("user_id")
    try:
        if actor_user_id is not None:
            realtime_scopes.add(f"user:{int(actor_user_id)}")
    except (TypeError, ValueError):
        pass

    mirrored = mirror_document(
        "event_stream",
        {
            "event_type": event_type,
            "source": source,
            "actor": actor_payload,
            "payload": payload or {},
            "created_at": datetime.now(timezone.utc),
        },
        required=required,
    )
    publish_domain_event(
        event_type,
        payload=payload or {},
        actor=actor_payload,
        source=source,
        scopes=realtime_scopes,
        topics=infer_topics(event_type),
    )
    return mirrored
