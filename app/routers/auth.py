import hashlib
import json
import os
import re
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request as UrlRequest, urlopen

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pymongo.errors import DuplicateKeyError, PyMongoError
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..academic_policy import assign_student_section
from ..auth_utils import (
    ACCESS_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    CurrentUser,
    create_session_tokens,
    decode_access_token,
    generate_otp_code,
    get_current_user,
    get_refresh_token_from_request,
    hash_otp,
    hash_password,
    password_expired,
    password_expires_at,
    PASSWORD_EXPIRED_DETAIL,
    revoke_access_token,
    revoke_all_user_sessions,
    revoke_session,
    rotate_session_tokens,
    upsert_sql_auth_user_record,
    verify_otp,
    verify_password,
)
from ..database import get_db
from ..enterprise_controls import (
    decrypt_pii,
    encrypt_pii,
    generate_backup_codes,
    generate_totp_qr_svg_data_uri,
    generate_totp_secret,
    hash_backup_code,
    hash_lookup_value,
    match_totp_code,
    verify_backup_code,
)
from ..identity_shield import assess_applicant_risk
from ..id_alignment import (
    align_auth_user_id_with_sql,
    align_faculty_profile_id_with_sql,
    align_student_profile_id_with_sql,
    bump_mongo_counter,
)
from ..media_storage import mark_media_deleted, store_data_url_object
from ..mongo import get_mongo_db, init_mongo, invalidate_mongo_connection, mirror_event, next_sequence
from ..otp_delivery import otp_expiry_minutes
from ..rate_limit import enforce_rate_limit
from ..validation import validate_email_address
from ..workers import dispatch_login_otp

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)

PASSWORD_POLICY_MESSAGE = (
    "Password must be at least 8 characters and include letters, numbers, and special characters."
)
ACCESS_COOKIE_SECURE = (os.getenv("APP_COOKIE_SECURE", "false") or "").strip().lower() in {"1", "true", "yes", "on"}
STUDENT_SECTION_PATTERN = re.compile(r"^[A-Z0-9/_-]+$")
RECAPTCHA_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
DEFAULT_BLOCKED_PRIMARY_EMAIL_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "outlook.com",
    "hotmail.com",
    "live.com",
    "msn.com",
    "yahoo.com",
    "ymail.com",
    "icloud.com",
    "me.com",
    "mac.com",
    "aol.com",
    "proton.me",
    "protonmail.com",
    "pm.me",
}


@router.get("/public-config", response_model=schemas.AuthPublicConfigOut)
def get_auth_public_config() -> schemas.AuthPublicConfigOut:
    enabled = _student_auth_recaptcha_enabled()
    return schemas.AuthPublicConfigOut(
        student_auth_captcha_enabled=enabled,
        student_auth_captcha_site_key=_student_auth_recaptcha_site_key() if enabled else None,
        student_auth_captcha_provider="cloudflare-turnstile",
    )


def _otp_resend_cooldown_seconds() -> int:
    raw = os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "30").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 30
    return max(5, min(180, value))


def _otp_delivery_timeout_seconds() -> int:
    raw = os.getenv("OTP_DELIVERY_TIMEOUT_SECONDS", "25").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 25
    return max(5, min(30, value))


def _student_auth_recaptcha_site_key() -> str:
    return str(os.getenv("STUDENT_AUTH_TURNSTILE_SITE_KEY", "") or "").strip()


def _student_auth_recaptcha_secret_key() -> str:
    return str(os.getenv("STUDENT_AUTH_TURNSTILE_SECRET_KEY", "") or "").strip()


def _student_auth_recaptcha_enabled() -> bool:
    raw = (os.getenv("STUDENT_AUTH_TURNSTILE_ENABLED", "false") or "").strip().lower()
    if raw not in {"1", "true", "yes", "on"}:
        return False
    return bool(_student_auth_recaptcha_site_key() and _student_auth_recaptcha_secret_key())


def _student_auth_recaptcha_timeout_seconds() -> float:
    raw = (os.getenv("STUDENT_AUTH_TURNSTILE_VERIFY_TIMEOUT_SECONDS", "6") or "").strip()
    try:
        value = float(raw)
    except ValueError:
        value = 6.0
    return max(2.0, min(15.0, value))


def _student_auth_recaptcha_expected_host() -> str | None:
    base_url = str(os.getenv("APP_BASE_URL", "") or "").strip()
    if not base_url:
        return None
    parsed = urlparse(base_url)
    host = str(parsed.hostname or "").strip().lower()
    return host or None


def _verify_student_auth_recaptcha(
    request: Request | None,
    captcha_token: str | None,
    *,
    action: str,
) -> None:
    if not _student_auth_recaptcha_enabled():
        return
    token = str(captcha_token or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Turnstile verification is required.")

    payload = {
        "secret": _student_auth_recaptcha_secret_key(),
        "response": token,
    }
    remote_ip = _request_ip(request)
    if remote_ip:
        payload["remoteip"] = remote_ip

    verify_request = UrlRequest(
        RECAPTCHA_VERIFY_URL,
        data=urlencode(payload).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(verify_request, timeout=_student_auth_recaptcha_timeout_seconds()) as response:
            verification = json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        logger.exception("Turnstile verification transport failed for action=%s", action)
        raise HTTPException(status_code=503, detail="Turnstile verification is temporarily unavailable.") from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Turnstile verification failed for action=%s", action)
        raise HTTPException(status_code=503, detail="Turnstile verification is temporarily unavailable.") from exc

    if not bool(verification.get("success")):
        raise HTTPException(status_code=403, detail="Turnstile verification failed. Please retry.")
    response_action = str(verification.get("action") or "").strip()
    if response_action and response_action != action:
        raise HTTPException(status_code=403, detail="Turnstile action mismatch. Please retry.")
    expected_host = _student_auth_recaptcha_expected_host()
    response_host = str(verification.get("hostname") or "").strip().lower()
    if expected_host and response_host and response_host != expected_host:
        raise HTTPException(status_code=403, detail="Turnstile host validation failed.")


def _mongo_db_or_503():
    def _acquire_writable_db():
        db = get_mongo_db(required=True)
        hello = db.client.admin.command("hello")
        if not bool(hello.get("isWritablePrimary", False)):
            raise RuntimeError("MongoDB writable primary is unavailable")
        return db

    try:
        return _acquire_writable_db()
    except (RuntimeError, PyMongoError) as exc:
        invalidate_mongo_connection(exc)

    if init_mongo(force=True):
        try:
            return _acquire_writable_db()
        except (RuntimeError, PyMongoError) as exc:
            invalidate_mongo_connection(exc)

    raise HTTPException(
        status_code=503,
        detail=(
            "Authentication datastore is temporarily unavailable for writes. "
            "Please retry in a few seconds."
        ),
    )


def _request_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    forwarded = (request.headers.get("x-forwarded-for") or "").strip()
    if forwarded:
        first = forwarded.split(",", 1)[0].strip()
        return first or None
    if request.client and request.client.host:
        return str(request.client.host)
    return None


def _request_device_id(request: Request | None) -> str | None:
    if request is None:
        return None
    explicit = (request.headers.get("x-device-id") or "").strip()
    if explicit:
        return explicit[:120]
    user_agent = (request.headers.get("user-agent") or "").strip()
    if not user_agent:
        return None
    digest = hashlib.sha256(user_agent.encode("utf-8")).hexdigest()
    return f"ua-{digest}"


def _raise_auth_datastore_unavailable(exc: Exception) -> None:
    invalidate_mongo_connection(exc)
    raise HTTPException(
        status_code=503,
        detail=(
            "Authentication datastore is temporarily unavailable for writes. "
            "Please retry in a few seconds."
        ),
    ) from exc


def _ensure_auth_user_id(db, user_doc: dict, sql_db: Session | None = None) -> int:
    aligned = align_auth_user_id_with_sql(db, sql_db, user_doc)
    if aligned is not None:
        return aligned

    raw_id = user_doc.get("id")
    try:
        user_id = int(raw_id)
        if user_id > 0:
            return user_id
    except (TypeError, ValueError):
        pass

    email = _normalize_email(str(user_doc.get("email", "")))
    if not email:
        raise HTTPException(status_code=500, detail="Invalid user record. Please contact support.")

    # Self-heal stale auth rows that were created without numeric id.
    assigned_id = _next_unique_id(db, collection="auth_users", sequence_name="auth_users")
    db["auth_users"].update_one(
        {
            "email": email,
            "$or": [
                {"id": {"$exists": False}},
                {"id": None},
                {"id": ""},
            ],
        },
        {"$set": {"id": assigned_id}},
    )
    refreshed = db["auth_users"].find_one({"email": email}, {"id": 1})
    if not refreshed or refreshed.get("id") is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Authentication datastore is temporarily unavailable for writes. "
                "Please retry in a few seconds."
            ),
        )
    try:
        user_id = int(refreshed.get("id"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail="Invalid user record. Please contact support.") from exc

    user_doc["id"] = user_id
    logger.warning("Recovered missing auth user id for email=%s", email)
    return user_id


def _send_login_otp_with_timeout(destination_email: str, otp_code: str) -> dict:
    timeout_seconds = _otp_delivery_timeout_seconds()
    return dispatch_login_otp(
        destination_email,
        otp_code,
        timeout_seconds=timeout_seconds,
    )


def _auth_user_out(doc: dict) -> schemas.AuthUserOut:
    role_raw = doc.get("role", models.UserRole.STUDENT.value)
    role = models.UserRole(role_raw)
    name_raw = str(doc.get("name", "") or "").strip()
    return schemas.AuthUserOut(
        id=int(doc["id"]),
        name=name_raw or None,
        email=str(doc.get("email", "")),
        role=role,
        student_id=doc.get("student_id"),
        faculty_id=doc.get("faculty_id"),
        alternate_email=_get_alternate_email(doc),
        primary_login_verified=bool(doc.get("primary_login_verified", False)),
        password_setup_required=_password_setup_required(doc),
        password_expired=password_expired(doc),
        password_expires_at=password_expires_at(doc),
        mfa_enabled=bool(doc.get("mfa_enabled", False)),
        primary_email_update_required=_primary_email_update_required(doc),
        is_active=bool(doc.get("is_active", True)),
        created_at=doc.get("created_at") or datetime.utcnow(),
        last_login_at=doc.get("last_login_at"),
    )


def _password_setup_required(doc: dict[str, Any]) -> bool:
    role_raw = str(doc.get("role", models.UserRole.STUDENT.value) or models.UserRole.STUDENT.value)
    if role_raw not in {
        models.UserRole.STUDENT.value,
        models.UserRole.ADMIN.value,
        models.UserRole.FACULTY.value,
    }:
        return False
    explicit = doc.get("password_setup_required")
    if explicit is not None:
        return bool(explicit)
    password_hash = str(doc.get("password_hash") or "").strip()
    if password_hash:
        return False
    return not bool(doc.get("password_updated_at"))


def _signup_verification_pending(doc: dict[str, Any]) -> bool:
    if not bool(doc.get("signup_verification_required", False)):
        return False
    return not bool(doc.get("primary_login_verified", False))


def _student_signup_verification_pending(doc: dict[str, Any]) -> bool:
    return _signup_verification_pending(doc)


def _next_unique_id(db, *, collection: str, sequence_name: str) -> int:
    try:
        candidate = next_sequence(sequence_name)
        while db[collection].find_one({"id": candidate}):
            candidate = next_sequence(sequence_name)
        return candidate
    except (RuntimeError, PyMongoError) as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Authentication datastore is temporarily unavailable for writes. "
                "Please retry in a few seconds."
            ),
        ) from exc


def _normalize_email(email: str) -> str:
    try:
        return validate_email_address(email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Enter a valid email address.") from exc


def _allowed_email_suffixes() -> list[str]:
    raw = (os.getenv("AUTH_EMAIL_SUFFIXES") or "").strip()
    if not raw:
        return []
    suffixes: list[str] = []
    for token in raw.replace(";", ",").split(","):
        suffix = token.strip().lower()
        if suffix and suffix not in suffixes:
            suffixes.append(suffix)
    return suffixes


def _email_suffix_allowed(email: str) -> bool:
    suffixes = _allowed_email_suffixes()
    if not suffixes:
        return True
    normalized = _normalize_email(email)
    return any(normalized.endswith(suffix) for suffix in suffixes)


def _blocked_primary_email_domains() -> set[str]:
    raw_value = os.getenv("AUTH_PRIMARY_EMAIL_BLOCKED_DOMAINS")
    if raw_value is not None and not str(raw_value).strip():
        return set()
    domains = set(DEFAULT_BLOCKED_PRIMARY_EMAIL_DOMAINS)
    raw = (raw_value or "").strip()
    if not raw:
        return domains
    for token in raw.replace(";", ",").split(","):
        domain = token.strip().lower().lstrip("@")
        if domain:
            domains.add(domain)
    return domains


def _is_blocked_primary_email(email: str) -> bool:
    normalized = _normalize_email(email)
    domain = normalized.rsplit("@", 1)[-1]
    return domain in _blocked_primary_email_domains()


def _primary_email_update_required(doc: dict[str, Any]) -> bool:
    try:
        role = models.UserRole(doc.get("role", models.UserRole.STUDENT.value))
    except ValueError:
        return False
    if role not in {models.UserRole.STUDENT, models.UserRole.FACULTY, models.UserRole.ADMIN}:
        return False
    return _is_blocked_primary_email(str(doc.get("email", "") or ""))


LEGACY_PRIMARY_EMAIL_MIGRATION_LOGIN_LIMIT = 3


def _legacy_primary_email_migration_login_count(doc: dict[str, Any]) -> int:
    try:
        explicit_count = int(doc.get("primary_email_migration_login_count", 0) or 0)
    except (TypeError, ValueError):
        explicit_count = 0
    if explicit_count > 0:
        return explicit_count
    return 1 if doc.get("primary_email_migration_started_at") else 0


def _reject_if_legacy_primary_login_consumed(doc: dict[str, Any]) -> None:
    if not _primary_email_update_required(doc):
        return
    if _legacy_primary_email_migration_login_count(doc) >= LEGACY_PRIMARY_EMAIL_MIGRATION_LOGIN_LIMIT:
        raise HTTPException(
            status_code=403,
            detail=(
                "This legacy primary email has used all 3 migration login attempts. "
                "Contact support if you need the migration window reset."
            ),
        )


def _mark_legacy_primary_migration_login(
    doc: dict[str, Any],
    *,
    now: datetime,
    auth_update: dict[str, Any],
    auth_inc: dict[str, int],
) -> None:
    if not _primary_email_update_required(doc):
        return
    if not doc.get("primary_email_migration_started_at"):
        auth_update["primary_email_migration_started_at"] = now
    increment_by = 1
    if doc.get("primary_email_migration_started_at") and not doc.get("primary_email_migration_login_count"):
        increment_by = 2
    auth_update["primary_email_migration_last_login_at"] = now
    auth_inc["primary_email_migration_login_count"] = increment_by


def _validate_primary_login_email(email: str, *, allow_blocked_primary: bool = False) -> str:
    normalized = _normalize_email(email)
    if _is_blocked_primary_email(normalized) and not allow_blocked_primary:
        raise HTTPException(
            status_code=400,
            detail=(
                "Use your official university or company email for primary login. "
                "Personal mailboxes can be added later as a secondary email."
            ),
        )
    return normalized


def _validate_role_email(email: str, role: models.UserRole, *, allow_legacy_primary: bool = False) -> None:
    if role in (
        models.UserRole.ADMIN,
        models.UserRole.FACULTY,
        models.UserRole.STUDENT,
        models.UserRole.OWNER,
    ):
        normalized = _validate_primary_login_email(email, allow_blocked_primary=allow_legacy_primary)
        if not allow_legacy_primary and not _email_suffix_allowed(normalized):
            suffixes = _allowed_email_suffixes()
            suffix_text = ", ".join(suffixes) if suffixes else "the configured institute domain"
            raise HTTPException(status_code=400, detail=f"Email must end with {suffix_text}")
        return

    raise HTTPException(status_code=400, detail="Only admin, faculty, student, and owner roles are allowed")


def _ensure_selected_login_role(actual_role: models.UserRole, selected_role: models.UserRole) -> None:
    if actual_role == selected_role:
        return
    raise HTTPException(
        status_code=403,
        detail=(
            f"This email is registered as a {actual_role.value} account, not a {selected_role.value} account. "
            f"Select {actual_role.value} in the role dropdown or use the correct {selected_role.value} account."
        ),
    )


def _upsert_mongo_by_id(db, collection: str, doc_id: int, payload: dict) -> None:
    body = dict(payload)
    body["id"] = doc_id
    pii_fields_by_collection: dict[str, list[str]] = {
        "students": [
            "parent_email",
            "profile_photo_data_url",
            "profile_face_template_json",
            "enrollment_video_template_json",
        ],
        "faculty": ["profile_photo_data_url"],
    }
    pii_fields = pii_fields_by_collection.get(collection, [])
    for field_name in pii_fields:
        raw_value = body.get(field_name)
        if not isinstance(raw_value, str):
            continue
        clean = raw_value.strip()
        if not clean:
            continue
        aad = f"{collection}:{int(doc_id)}:{field_name}"
        body[f"{field_name}_encrypted"] = encrypt_pii(clean, aad=aad)
        body[field_name] = None
    db[collection].update_one({"id": doc_id}, {"$set": body}, upsert=True)
    bump_mongo_counter(db, collection, int(doc_id))


def _validate_alternate_email(email: str) -> str:
    return _normalize_email(email)


def _validate_new_primary_email(email: str) -> str:
    value = _normalize_email(email)
    _validate_primary_login_email(value)
    if not _email_suffix_allowed(value):
        suffixes = _allowed_email_suffixes()
        suffix_text = ", ".join(suffixes) if suffixes else "the configured institute domain"
        raise HTTPException(status_code=400, detail=f"Primary email must end with {suffix_text}")
    return value


def _ensure_email_available_for_primary(db, sql_db: Session, *, new_email: str, current_user_id: int) -> None:
    existing = db["auth_users"].find_one({"email": new_email}, {"id": 1})
    if existing and int(existing.get("id") or 0) != int(current_user_id):
        raise HTTPException(status_code=409, detail="Primary email is already used by another account.")

    alt_hash = hash_lookup_value(new_email, purpose="alternate-email")
    conflict = db["auth_users"].find_one(
        {
            "id": {"$ne": int(current_user_id)},
            "$or": [
                {"alternate_email_hash": alt_hash},
                {"alternate_email": new_email},
            ],
        },
        {"id": 1},
    )
    if conflict:
        raise HTTPException(status_code=409, detail="Primary email is already used as another account's secondary email.")

    sql_query = getattr(sql_db, "query", None)
    if callable(sql_query):
        sql_user = (
            sql_query(models.AuthUser)
            .filter(func.lower(models.AuthUser.email) == new_email)
            .first()
        )
        if sql_user and int(sql_user.id or 0) != int(current_user_id):
            raise HTTPException(status_code=409, detail="Primary email is already used by another account.")


def _write_primary_email_change(
    db,
    sql_db: Session,
    *,
    user_doc: dict[str, Any],
    role: models.UserRole,
    new_email: str,
) -> dict[str, Any]:
    user_id = int(user_doc["id"])
    old_email = _normalize_email(str(user_doc.get("email", "")))
    if new_email == old_email:
        raise HTTPException(status_code=400, detail="New primary email must be different from the current primary email.")

    _ensure_email_available_for_primary(db, sql_db, new_email=new_email, current_user_id=user_id)

    alternate_fields = _build_alternate_email_update_fields(user_id, old_email)
    auth_update = {
        **alternate_fields,
        "email": new_email,
        "primary_login_verified": True,
        "primary_email_updated_at": datetime.utcnow(),
    }

    sql_user = sql_db.get(models.AuthUser, user_id) if hasattr(sql_db, "get") else None
    if sql_user:
        sql_user.email = new_email
    if role == models.UserRole.STUDENT:
        student_id = user_doc.get("student_id")
        if student_id and hasattr(sql_db, "get"):
            student = sql_db.get(models.Student, int(student_id))
            if student:
                student.email = new_email
        db["students"].update_one({"id": int(student_id)} if student_id else {"email": old_email}, {"$set": {"email": new_email}})
    elif role == models.UserRole.FACULTY:
        faculty_id = user_doc.get("faculty_id")
        if faculty_id and hasattr(sql_db, "get"):
            faculty = sql_db.get(models.Faculty, int(faculty_id))
            if faculty:
                faculty.email = new_email
        db["faculty"].update_one({"id": int(faculty_id)} if faculty_id else {"email": old_email}, {"$set": {"email": new_email}})

    try:
        sql_db.flush()
        sql_db.commit()
    except Exception:
        sql_db.rollback()
        raise

    db["auth_users"].update_one({"id": user_id}, {"$set": auth_update})
    updated = db["auth_users"].find_one({"id": user_id})
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return updated


def _privileged_mfa_required() -> bool:
    return (os.getenv("APP_ENFORCE_PRIVILEGED_MFA", "true") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _is_privileged_role(role: models.UserRole) -> bool:
    return role in {models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.OWNER}


def _requires_totp_mfa_role(role: models.UserRole) -> bool:
    return role in {models.UserRole.ADMIN, models.UserRole.OWNER}


def _mfa_setup_ttl_minutes() -> int:
    raw = (os.getenv("MFA_SETUP_TTL_MINUTES", "15") or "").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 15
    return max(5, min(60, value))


def _bounded_int_env(name: str, *, default: int, minimum: int, maximum: int) -> int:
    raw = (os.getenv(name, str(default)) or "").strip()
    try:
        value = int(raw)
    except ValueError:
        value = int(default)
    return max(int(minimum), min(int(maximum), value))


def _mfa_totp_login_drift_steps() -> int:
    return _bounded_int_env("MFA_TOTP_LOGIN_DRIFT_STEPS", default=4, minimum=1, maximum=20)


def _mfa_totp_activation_drift_steps() -> int:
    return _bounded_int_env("MFA_TOTP_ACTIVATION_DRIFT_STEPS", default=10, minimum=2, maximum=30)


def _mfa_totp_sanitized_skew(raw_value: Any) -> int:
    try:
        skew = int(raw_value)
    except (TypeError, ValueError):
        skew = 0
    return max(-30, min(30, skew))


def _match_user_totp(secret: str, code: str, user_doc: dict, *, allowed_drift_steps: int) -> int | None:
    preferred_delta = _mfa_totp_sanitized_skew(user_doc.get("mfa_totp_skew_steps"))
    return match_totp_code(
        secret,
        code,
        allowed_drift_steps=allowed_drift_steps,
        digits=6,
        preferred_delta=preferred_delta,
    )


def _normalize_otp_candidate(code: str | None) -> str:
    return re.sub(r"\D+", "", str(code or ""))


def _normalize_backup_code_candidate(code: str | None) -> str:
    return re.sub(r"[\s-]+", "", str(code or "").strip()).upper()


def _get_alternate_email(user_doc: dict) -> str | None:
    encrypted = str(user_doc.get("alternate_email_encrypted") or "").strip()
    if encrypted:
        try:
            user_id = int(user_doc.get("id") or 0)
            aad = f"auth_users:{user_id}:alternate_email"
            return decrypt_pii(encrypted, aad=aad)
        except Exception:
            return None
    plain = str(user_doc.get("alternate_email") or "").strip().lower()
    return plain or None


def _build_alternate_email_update_fields(user_id: int, alternate_email: str | None) -> dict[str, Any]:
    if not alternate_email:
        return {
            "alternate_email": None,
            "alternate_email_encrypted": None,
            "alternate_email_hash": None,
        }
    aad = f"auth_users:{int(user_id)}:alternate_email"
    encrypted = encrypt_pii(alternate_email, aad=aad)
    return {
        "alternate_email": None,
        "alternate_email_encrypted": encrypted,
        "alternate_email_hash": hash_lookup_value(alternate_email, purpose="alternate-email"),
    }


def _issue_backup_codes() -> tuple[list[str], list[str]]:
    plain_codes = generate_backup_codes(count=8)
    return plain_codes, [hash_backup_code(code) for code in plain_codes]


def _verify_and_consume_mfa_code(db, user_doc: dict, mfa_code: str | None) -> bool:
    raw_code = str(mfa_code or "").strip()
    if not raw_code:
        return False
    secret = str(user_doc.get("mfa_totp_secret") or "").strip()
    totp_candidate = _normalize_otp_candidate(raw_code)
    if secret:
        matched_delta = _match_user_totp(
            secret,
            totp_candidate,
            user_doc,
            allowed_drift_steps=_mfa_totp_login_drift_steps(),
        )
        if matched_delta is not None:
            previous_delta = _mfa_totp_sanitized_skew(user_doc.get("mfa_totp_skew_steps"))
            if matched_delta != previous_delta:
                db["auth_users"].update_one(
                    {"id": int(user_doc["id"])},
                    {"$set": {"mfa_totp_skew_steps": int(matched_delta)}},
                )
                user_doc["mfa_totp_skew_steps"] = int(matched_delta)
            return True

    backup_hashes = [str(item) for item in (user_doc.get("mfa_backup_code_hashes") or []) if str(item)]
    backup_candidate = _normalize_backup_code_candidate(raw_code)
    for idx, stored_hash in enumerate(backup_hashes):
        if not verify_backup_code(backup_candidate, stored_hash):
            continue
        backup_hashes.pop(idx)
        db["auth_users"].update_one(
            {"id": int(user_doc["id"])},
            {"$set": {"mfa_backup_code_hashes": backup_hashes, "mfa_last_verified_at": datetime.utcnow()}},
        )
        user_doc["mfa_backup_code_hashes"] = backup_hashes
        return True
    return False


def _normalize_registration_number(value: str) -> str:
    normalized = re.sub(r"\s+", "", value.strip().upper())
    if len(normalized) < 3:
        raise HTTPException(status_code=400, detail="registration_number must be at least 3 characters")
    if not re.fullmatch(r"[A-Z0-9/-]+", normalized):
        raise HTTPException(
            status_code=400,
            detail="registration_number can contain only letters, numbers, slash, and hyphen",
        )
    return normalized


def _generate_admin_registration_number(db) -> str:
    for _ in range(25):
        candidate = f"{secrets.randbelow(90000) + 10000:05d}"
        if not db["auth_users"].find_one({"registration_number": candidate}):
            return candidate
    raise HTTPException(status_code=500, detail="Unable to generate admin registration number")


def _arrival_year(value: datetime | None, fallback: datetime | None = None) -> int:
    source = value or fallback or datetime.utcnow()
    return int(source.year)


def _student_registration_number_for_position(year: int, position: int) -> str:
    if position < 1 or position > 99999:
        raise HTTPException(status_code=500, detail="Student registration sequence exhausted for year")
    return f"1{year % 100:02d}{position:05d}"


def _faculty_identifier_for_position(year: int, position: int) -> str:
    if position < 1 or position > 9999:
        raise HTTPException(status_code=500, detail="Faculty identifier sequence exhausted for year")
    year_suffix = f"{year % 100:02d}"[::-1]
    return f"{year_suffix}{position:04d}"


def _students_for_year(sql_db: Session, year: int) -> list[models.Student]:
    rows = sql_db.query(models.Student).all()
    return sorted(
        [row for row in rows if _arrival_year(row.created_at) == year],
        key=lambda row: (row.created_at or datetime.min, int(row.id or 0)),
    )


def _faculty_for_year(sql_db: Session, year: int) -> list[models.Faculty]:
    rows = sql_db.query(models.Faculty).all()
    return sorted(
        [row for row in rows if _arrival_year(row.created_at) == year],
        key=lambda row: (row.created_at or datetime.min, int(row.id or 0)),
    )


def _next_student_registration_number(sql_db: Session, *, now: datetime) -> str:
    year = _arrival_year(now)
    position = len(_students_for_year(sql_db, year)) + 1
    return _student_registration_number_for_position(year, position)


def _next_faculty_identifier(sql_db: Session, *, now: datetime) -> str:
    year = _arrival_year(now)
    position = len(_faculty_for_year(sql_db, year)) + 1
    return _faculty_identifier_for_position(year, position)


def _arrival_position(rows: list[Any], target_id: int | None) -> int:
    for index, row in enumerate(rows, start=1):
        if int(row.id or 0) == int(target_id or 0):
            return index
    return len(rows) + 1


def reissue_generated_profile_identifiers(sql_db: Session) -> dict[str, int]:
    """Replace manually supplied profile IDs with deterministic arrival-order IDs."""
    student_updates: list[tuple[models.Student, str]] = []
    faculty_updates: list[tuple[models.Faculty, str]] = []

    student_years = sorted({_arrival_year(row.created_at) for row in sql_db.query(models.Student).all()})
    for year in student_years:
        for position, student in enumerate(_students_for_year(sql_db, year), start=1):
            generated = _student_registration_number_for_position(year, position)
            if student.registration_number != generated:
                student_updates.append((student, generated))

    faculty_years = sorted({_arrival_year(row.created_at) for row in sql_db.query(models.Faculty).all()})
    for year in faculty_years:
        for position, faculty in enumerate(_faculty_for_year(sql_db, year), start=1):
            generated = _faculty_identifier_for_position(year, position)
            if faculty.faculty_identifier != generated:
                faculty_updates.append((faculty, generated))

    for student, _ in student_updates:
        student.registration_number = f"REISSUE-STU-{int(student.id or 0)}"
    for faculty, _ in faculty_updates:
        faculty.faculty_identifier = f"REISSUE-FAC-{int(faculty.id or 0)}"

    if student_updates or faculty_updates:
        sql_db.flush()

    for student, generated in student_updates:
        student.registration_number = generated
    for faculty, generated in faculty_updates:
        faculty.faculty_identifier = generated

    sql_db.flush()
    return {"students": len(student_updates), "faculty": len(faculty_updates)}


def _normalize_faculty_identifier(value: str) -> str:
    normalized = re.sub(r"\s+", "", str(value or "").strip().upper())
    if len(normalized) < 3:
        raise HTTPException(status_code=400, detail="faculty_identifier must be at least 3 characters")
    if not re.fullmatch(r"[A-Z0-9/-]+", normalized):
        raise HTTPException(
            status_code=400,
            detail="faculty_identifier can contain only letters, numbers, slash, and hyphen",
        )
    return normalized


def _validate_password_strength(password: str) -> None:
    raw = str(password or "")
    if len(raw) < 8:
        raise HTTPException(status_code=400, detail=PASSWORD_POLICY_MESSAGE)
    if not re.search(r"[A-Za-z]", raw):
        raise HTTPException(status_code=400, detail=PASSWORD_POLICY_MESSAGE)
    if not re.search(r"\d", raw):
        raise HTTPException(status_code=400, detail=PASSWORD_POLICY_MESSAGE)
    if not re.search(r"[^A-Za-z0-9]", raw):
        raise HTTPException(status_code=400, detail=PASSWORD_POLICY_MESSAGE)


def _password_reset_token_validity_minutes() -> int:
    raw = os.getenv("PASSWORD_RESET_TOKEN_EXPIRES_MINUTES", "10").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 10
    return max(5, min(30, value))


def _cookie_max_age(expires_at: datetime) -> int:
    now_utc = datetime.utcnow()
    return int(max(0, (_to_utc_naive(expires_at) - now_utc).total_seconds()))


def _set_auth_cookies(
    response: Response,
    *,
    access_token: str,
    access_expires_at: datetime,
    refresh_token: str,
    refresh_expires_at: datetime,
) -> None:
    access_max_age = _cookie_max_age(access_expires_at)
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=access_token,
        max_age=access_max_age,
        expires=access_max_age,
        httponly=True,
        samesite="lax",
        secure=ACCESS_COOKIE_SECURE,
        path="/",
    )
    refresh_max_age = _cookie_max_age(refresh_expires_at)
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=refresh_max_age,
        expires=refresh_max_age,
        httponly=True,
        samesite="lax",
        secure=ACCESS_COOKIE_SECURE,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        key=ACCESS_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=ACCESS_COOKIE_SECURE,
    )
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=ACCESS_COOKIE_SECURE,
    )


def _coerce_datetime(value) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        if raw.endswith("Z"):
            raw = f"{raw[:-1]}+00:00"
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return None
    return None


def _to_utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _release_stale_profile_link(
    db,
    sql_db: Session,
    *,
    field_name: str,
    profile_id: int | None,
    current_email: str,
) -> None:
    if profile_id is None:
        return

    existing = db["auth_users"].find_one({field_name: profile_id})
    if not existing:
        return

    existing_email = str(existing.get("email", "")).strip().lower()
    if existing_email == current_email:
        return

    if field_name == "student_id":
        profile_row = sql_db.get(models.Student, profile_id)
        profile_exists = profile_row is not None
    else:
        profile_row = sql_db.get(models.Faculty, profile_id)
        profile_exists = profile_row is not None

    # Recover from stale Mongo links when SQLite row IDs were reused.
    if profile_exists and str(getattr(profile_row, "email", "")).strip().lower() == current_email:
        db["auth_users"].update_one({"id": existing["id"]}, {"$set": {field_name: None}})
        return

    if profile_exists:
        raise HTTPException(status_code=409, detail="Linked profile is already attached to another auth account")

    db["auth_users"].update_one({"id": existing["id"]}, {"$set": {field_name: None}})


def _ensure_role_profile_link(
    db,
    sql_db: Session,
    *,
    user_doc: dict,
    role: models.UserRole,
    email: str,
) -> None:
    field_name: str | None = None
    profile_id: int | None = None

    if role == models.UserRole.STUDENT:
        field_name = "student_id"
        profile_id = user_doc.get("student_id")
    elif role == models.UserRole.FACULTY:
        field_name = "faculty_id"
        profile_id = user_doc.get("faculty_id")

    if not field_name:
        return

    if role == models.UserRole.STUDENT:
        aligned = align_student_profile_id_with_sql(db, sql_db, email=email, user_doc=user_doc)
        if aligned is not None:
            return
        created = _restore_missing_student_profile_from_mongo(
            db,
            sql_db,
            user_doc=user_doc,
            email=email,
        )
        if created is not None:
            align_student_profile_id_with_sql(db, sql_db, email=email, user_doc=user_doc)
            return
    if role == models.UserRole.FACULTY:
        aligned = align_faculty_profile_id_with_sql(db, sql_db, email=email, user_doc=user_doc)
        if aligned is not None:
            return
        created = _restore_missing_faculty_profile_from_mongo(
            db,
            sql_db,
            user_doc=user_doc,
            email=email,
        )
        if created is not None:
            align_faculty_profile_id_with_sql(db, sql_db, email=email, user_doc=user_doc)
            return

    if profile_id:
        return

    if role == models.UserRole.STUDENT:
        profile = sql_db.query(models.Student).filter(models.Student.email == email).first()
    else:
        profile = sql_db.query(models.Faculty).filter(models.Faculty.email == email).first()

    if not profile:
        return

    _release_stale_profile_link(
        db,
        sql_db,
        field_name=field_name,
        profile_id=profile.id,
        current_email=email,
    )

    db["auth_users"].update_one({"id": user_doc["id"]}, {"$set": {field_name: int(profile.id)}})
    user_doc[field_name] = int(profile.id)


def _decrypt_mongo_pii_value(collection: str, doc_id: int, field_name: str, doc: dict[str, Any]) -> str | None:
    raw_value = doc.get(field_name)
    if isinstance(raw_value, str) and raw_value.strip():
        return raw_value.strip()
    encrypted_value = doc.get(f"{field_name}_encrypted")
    if not isinstance(encrypted_value, str) or not encrypted_value.strip():
        return None
    aad = f"{collection}:{int(doc_id)}:{field_name}"
    try:
        return decrypt_pii(encrypted_value.strip(), aad=aad)
    except Exception:
        logger.exception(
            "mongo_profile_field_decrypt_failed collection=%s id=%s field=%s",
            collection,
            int(doc_id),
            field_name,
        )
        return None


def _restore_missing_student_profile_from_mongo(
    db,
    sql_db: Session,
    *,
    user_doc: dict[str, Any],
    email: str,
) -> int | None:
    email_norm = _normalize_email(email)
    if not email_norm:
        return None

    student_doc = None
    linked_student_id = user_doc.get("student_id")
    try:
        linked_student_id = int(linked_student_id) if linked_student_id is not None else None
    except (TypeError, ValueError):
        linked_student_id = None
    if linked_student_id:
        student_doc = db["students"].find_one({"id": linked_student_id})
    if not student_doc:
        student_doc = db["students"].find_one({"email": email_norm})
    if not student_doc:
        return None

    try:
        source_student_id = int(student_doc.get("id") or 0) or linked_student_id
    except (TypeError, ValueError):
        source_student_id = linked_student_id

    name = str(student_doc.get("name") or "").strip()
    department = str(student_doc.get("department") or "").strip()
    semester_raw = student_doc.get("semester")
    try:
        semester = int(semester_raw)
    except (TypeError, ValueError):
        semester = 0

    if not name or not department or semester <= 0:
        raise HTTPException(
            status_code=409,
            detail="Student profile data is incomplete. Please contact support to restore your account profile.",
        )

    target_id = source_student_id if source_student_id and not sql_db.get(models.Student, int(source_student_id)) else None
    if target_id is None and linked_student_id:
        existing = sql_db.get(models.Student, int(linked_student_id))
        if existing and _normalize_email(str(existing.email or "")) != email_norm:
            raise HTTPException(status_code=409, detail="Student profile id collision detected")

    student = models.Student(
        id=int(target_id) if target_id else None,
        name=name,
        email=email_norm,
        registration_number=str(student_doc.get("registration_number") or "").strip() or None,
        parent_email=_decrypt_mongo_pii_value("students", int(source_student_id or 0), "parent_email", student_doc),
        section=str(student_doc.get("section") or "").strip() or None,
        section_updated_at=_coerce_datetime(student_doc.get("section_updated_at")),
        profile_photo_data_url=_decrypt_mongo_pii_value(
            "students",
            int(source_student_id or 0),
            "profile_photo_data_url",
            student_doc,
        ),
        profile_photo_object_key=str(student_doc.get("profile_photo_object_key") or "").strip() or None,
        profile_photo_updated_at=_coerce_datetime(student_doc.get("profile_photo_updated_at")),
        profile_photo_locked_until=_coerce_datetime(student_doc.get("profile_photo_locked_until")),
        profile_face_template_json=_decrypt_mongo_pii_value(
            "students",
            int(source_student_id or 0),
            "profile_face_template_json",
            student_doc,
        ),
        profile_face_template_updated_at=_coerce_datetime(student_doc.get("profile_face_template_updated_at")),
        enrollment_video_template_json=_decrypt_mongo_pii_value(
            "students",
            int(source_student_id or 0),
            "enrollment_video_template_json",
            student_doc,
        ),
        enrollment_video_updated_at=_coerce_datetime(student_doc.get("enrollment_video_updated_at")),
        enrollment_video_locked_until=_coerce_datetime(student_doc.get("enrollment_video_locked_until")),
        department=department,
        semester=semester,
        created_at=_coerce_datetime(student_doc.get("created_at")) or datetime.utcnow(),
    )
    try:
        sql_db.add(student)
        sql_db.flush()
        sql_db.commit()
    except Exception:
        sql_db.rollback()
        raise

    if not source_student_id or int(student.id) != int(source_student_id):
        _upsert_mongo_by_id(
            db,
            "students",
            int(student.id),
            {
                "name": student.name,
                "email": student.email,
                "registration_number": student.registration_number,
                "parent_email": student.parent_email,
                "section": student.section,
                "section_updated_at": student.section_updated_at,
                "profile_photo_data_url": student.profile_photo_data_url,
                "profile_photo_object_key": student.profile_photo_object_key,
                "profile_photo_updated_at": student.profile_photo_updated_at,
                "profile_photo_locked_until": student.profile_photo_locked_until,
                "profile_face_template_json": student.profile_face_template_json,
                "profile_face_template_updated_at": student.profile_face_template_updated_at,
                "enrollment_video_template_json": student.enrollment_video_template_json,
                "enrollment_video_updated_at": student.enrollment_video_updated_at,
                "enrollment_video_locked_until": student.enrollment_video_locked_until,
                "department": student.department,
                "semester": student.semester,
                "created_at": student.created_at,
                "source": "auth-profile-restore",
            },
        )
    return int(student.id)


def _restore_missing_faculty_profile_from_mongo(
    db,
    sql_db: Session,
    *,
    user_doc: dict[str, Any],
    email: str,
) -> int | None:
    email_norm = _normalize_email(email)
    if not email_norm:
        return None

    faculty_doc = None
    linked_faculty_id = user_doc.get("faculty_id")
    try:
        linked_faculty_id = int(linked_faculty_id) if linked_faculty_id is not None else None
    except (TypeError, ValueError):
        linked_faculty_id = None
    if linked_faculty_id:
        faculty_doc = db["faculty"].find_one({"id": linked_faculty_id})
    if not faculty_doc:
        faculty_doc = db["faculty"].find_one({"email": email_norm})
    if not faculty_doc:
        return None

    try:
        source_faculty_id = int(faculty_doc.get("id") or 0) or linked_faculty_id
    except (TypeError, ValueError):
        source_faculty_id = linked_faculty_id

    name = str(faculty_doc.get("name") or "").strip()
    department = str(faculty_doc.get("department") or "").strip()
    if not name or not department:
        raise HTTPException(
            status_code=409,
            detail="Faculty profile data is incomplete. Please contact support to restore your account profile.",
        )

    target_id = source_faculty_id if source_faculty_id and not sql_db.get(models.Faculty, int(source_faculty_id)) else None
    if target_id is None and linked_faculty_id:
        existing = sql_db.get(models.Faculty, int(linked_faculty_id))
        if existing and _normalize_email(str(existing.email or "")) != email_norm:
            raise HTTPException(status_code=409, detail="Faculty profile id collision detected")

    faculty = models.Faculty(
        id=int(target_id) if target_id else None,
        name=name,
        email=email_norm,
        faculty_identifier=str(faculty_doc.get("faculty_identifier") or "").strip() or None,
        section=str(faculty_doc.get("section") or "").strip() or None,
        section_updated_at=_coerce_datetime(faculty_doc.get("section_updated_at")),
        profile_photo_data_url=_decrypt_mongo_pii_value(
            "faculty",
            int(source_faculty_id or 0),
            "profile_photo_data_url",
            faculty_doc,
        ),
        profile_photo_object_key=str(faculty_doc.get("profile_photo_object_key") or "").strip() or None,
        profile_photo_updated_at=_coerce_datetime(faculty_doc.get("profile_photo_updated_at")),
        profile_photo_locked_until=_coerce_datetime(faculty_doc.get("profile_photo_locked_until")),
        department=department,
        created_at=_coerce_datetime(faculty_doc.get("created_at")) or datetime.utcnow(),
    )
    try:
        sql_db.add(faculty)
        sql_db.flush()
        sql_db.commit()
    except Exception:
        sql_db.rollback()
        raise
    return int(faculty.id)


def _has_real_profile_for_legacy_otp_login(
    db,
    sql_db: Session,
    *,
    role: models.UserRole,
    user_doc: dict[str, Any],
    email: str,
) -> bool:
    email_norm = _normalize_email(email)
    sql_get = getattr(sql_db, "get", None)
    sql_query = getattr(sql_db, "query", None)
    if role == models.UserRole.ADMIN:
        sql_auth_user = None
        if callable(sql_query):
            sql_auth_user = (
                sql_query(models.AuthUser)
                .filter(func.lower(models.AuthUser.email) == email_norm)
                .first()
            )
        if sql_auth_user and sql_auth_user.role == models.UserRole.ADMIN:
            return True
        if bool(user_doc.get("signup_verification_required", False)):
            return True
        if bool(user_doc.get("primary_login_verified", False)):
            return True
        if str(user_doc.get("registration_number") or "").strip():
            return True
        if str(user_doc.get("profile_photo_object_key") or "").strip():
            return True
        if user_doc.get("profile_photo_updated_at"):
            return True
        return False
    if role == models.UserRole.STUDENT:
        student_id = user_doc.get("student_id")
        try:
            student_id = int(student_id) if student_id is not None else None
        except (TypeError, ValueError):
            student_id = None
        if student_id and callable(sql_get) and sql_get(models.Student, student_id):
            return True
        if callable(sql_query) and sql_query(models.Student).filter(func.lower(models.Student.email) == email_norm).first():
            return True
        if student_id and db["students"].find_one({"id": student_id}):
            return True
        if db["students"].find_one({"email": email_norm}):
            return True
        return False
    if role == models.UserRole.FACULTY:
        faculty_id = user_doc.get("faculty_id")
        try:
            faculty_id = int(faculty_id) if faculty_id is not None else None
        except (TypeError, ValueError):
            faculty_id = None
        if faculty_id and callable(sql_get) and sql_get(models.Faculty, faculty_id):
            return True
        if callable(sql_query) and sql_query(models.Faculty).filter(func.lower(models.Faculty.email) == email_norm).first():
            return True
        if faculty_id and db["faculty"].find_one({"id": faculty_id}):
            return True
        if db["faculty"].find_one({"email": email_norm}):
            return True
        return False
    return True


@router.post("/register", response_model=schemas.AuthUserOut, status_code=status.HTTP_201_CREATED)
def register_auth_user(
    payload: schemas.AuthRegisterRequest,
    request: Request,
    sql_db: Session = Depends(get_db),
):
    db = _mongo_db_or_503()

    role = payload.role

    email = _normalize_email(payload.email)
    _validate_role_email(email, role)
    _validate_password_strength(payload.password)
    if role == models.UserRole.STUDENT:
        _verify_student_auth_recaptcha(
            request,
            payload.captcha_token,
            action="student_signup",
        )
    admin_photo_data_url = str(payload.profile_photo_data_url or "").strip()
    if role == models.UserRole.ADMIN and not admin_photo_data_url:
        raise HTTPException(status_code=400, detail="Admin profile photo is required for registration")

    try:
        assess_applicant_risk(
            sql_db,
            schemas.ApplicantRiskAssessmentRequest(
                applicant_email=email,
                claimed_role=role.value,
                registration_number=payload.registration_number,
                parent_email=payload.parent_email,
                device_id=_request_device_id(request),
                user_agent=(request.headers.get("user-agent") if request else None),
                ip_address=_request_ip(request),
                external_subject_key=f"signup:{email}",
                suspicious_flags=[],
            ),
        )
    except Exception:
        sql_db.rollback()
        logger.exception("signup_identity_screening_failed email=%s role=%s", email, role.value)

    if db["auth_users"].find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Email already exists")
    if (
        sql_db.query(models.AuthUser)
        .filter(func.lower(models.AuthUser.email) == email)
        .first()
    ):
        raise HTTPException(status_code=409, detail="Email already exists")

    now = datetime.utcnow()
    password_hash = hash_password(payload.password)
    student_id = None
    faculty_id = None
    user_id = None
    admin_photo_object_key = None
    admin_photo_updated_at = None
    admin_registration_number = None

    try:
        if role == models.UserRole.STUDENT:
            if payload.semester is None:
                raise HTTPException(status_code=400, detail="semester is required for student registration")
            student = sql_db.query(models.Student).filter(models.Student.email == email).first()
            if student:
                student.name = payload.name
                student.department = payload.department
                student.semester = payload.semester
                student.parent_email = payload.parent_email
                if not str(student.registration_number or "").strip():
                    student_year = _arrival_year(student.created_at, now)
                    student.registration_number = _student_registration_number_for_position(
                        student_year,
                        _arrival_position(_students_for_year(sql_db, student_year), student.id),
                    )
            else:
                generated_registration = _next_student_registration_number(sql_db, now=now)
                student = models.Student(
                    name=payload.name,
                    email=email,
                    registration_number=generated_registration,
                    parent_email=payload.parent_email,
                    department=payload.department,
                    semester=payload.semester,
                )
                sql_db.add(student)
                sql_db.flush()
            assign_student_section(sql_db, student, now=now, force=True)

            student_id = student.id
            _upsert_mongo_by_id(
                db,
                "students",
                student.id,
                {
                    "name": student.name,
                    "email": student.email,
                    "registration_number": student.registration_number,
                    "parent_email": student.parent_email,
                    "section": student.section,
                    "section_updated_at": student.section_updated_at,
                    "profile_photo_data_url": None,
                    "profile_photo_object_key": student.profile_photo_object_key,
                    "profile_photo_updated_at": student.profile_photo_updated_at,
                    "profile_photo_locked_until": student.profile_photo_locked_until,
                    "department": student.department,
                    "semester": student.semester,
                    "created_at": student.created_at,
                    "source": "self-register",
                },
            )
            _release_stale_profile_link(
                db,
                sql_db,
                field_name="student_id",
                profile_id=student_id,
                current_email=email,
            )

        if role == models.UserRole.FACULTY:
            incoming_section = re.sub(r"\s+", "", str(payload.section or "").strip().upper())
            if incoming_section:
                if len(incoming_section) > 80 or not STUDENT_SECTION_PATTERN.fullmatch(incoming_section):
                    raise HTTPException(
                        status_code=400,
                        detail="section can contain only letters, numbers, slash, hyphen, and underscore",
                    )
            faculty = sql_db.query(models.Faculty).filter(models.Faculty.email == email).first()
            if faculty:
                faculty.name = payload.name
                faculty.department = payload.department
                if incoming_section:
                    faculty.section = incoming_section
                    faculty.section_updated_at = now
                if not str(faculty.faculty_identifier or "").strip():
                    faculty_year = _arrival_year(faculty.created_at, now)
                    faculty.faculty_identifier = _faculty_identifier_for_position(
                        faculty_year,
                        _arrival_position(_faculty_for_year(sql_db, faculty_year), faculty.id),
                    )
            else:
                generated_faculty_identifier = _next_faculty_identifier(sql_db, now=now)
                faculty = models.Faculty(
                    name=payload.name,
                    email=email,
                    faculty_identifier=generated_faculty_identifier,
                    section=incoming_section or None,
                    section_updated_at=now if incoming_section else None,
                    department=payload.department,
                )
                sql_db.add(faculty)
                sql_db.flush()

            faculty_id = faculty.id
            _upsert_mongo_by_id(
                db,
                "faculty",
                faculty.id,
                {
                    "name": faculty.name,
                    "email": faculty.email,
                    "faculty_identifier": faculty.faculty_identifier,
                    "section": faculty.section,
                    "section_updated_at": faculty.section_updated_at,
                    "profile_photo_data_url": None,
                    "profile_photo_object_key": faculty.profile_photo_object_key,
                    "profile_photo_updated_at": faculty.profile_photo_updated_at,
                    "profile_photo_locked_until": faculty.profile_photo_locked_until,
                    "department": faculty.department,
                    "created_at": faculty.created_at,
                    "source": "self-register",
                },
            )
            _release_stale_profile_link(
                db,
                sql_db,
                field_name="faculty_id",
                profile_id=faculty_id,
                current_email=email,
            )

        sql_auth_user, _ = upsert_sql_auth_user_record(
            sql_db,
            email=email,
            password_hash=password_hash,
            role=role,
            student_id=student_id,
            faculty_id=faculty_id,
            is_active=True,
            created_at=now,
            password_updated_at=now,
        )
        user_id = int(sql_auth_user.id)

        if role == models.UserRole.ADMIN:
            admin_registration_number = _generate_admin_registration_number(db)
            media = store_data_url_object(
                sql_db,
                owner_table="auth_users",
                owner_id=user_id,
                media_kind="admin-profile-photo",
                data_url=admin_photo_data_url,
            )
            admin_photo_object_key = media.object_key
            admin_photo_updated_at = now

        user_doc = {
            "id": user_id,
            "name": payload.name.strip(),
            "email": email,
            "password_hash": password_hash,
            "role": role.value,
            "student_id": student_id,
            "faculty_id": faculty_id,
            "alternate_email": None,
            "alternate_email_encrypted": None,
            "alternate_email_hash": None,
            "primary_login_verified": False,
            "mfa_enabled": False,
            "mfa_totp_secret": None,
            "mfa_backup_code_hashes": [],
            "mfa_enrolled_at": None,
            "mfa_last_verified_at": None,
            "mfa_totp_skew_steps": 0,
            "mfa_setup_secret": None,
            "mfa_setup_backup_code_hashes": [],
            "mfa_setup_expires_at": None,
            "is_active": True,
            "created_at": now,
            "last_login_at": None,
            "password_updated_at": now,
            "password_setup_required": False,
            "signup_verification_required": True,
        }
        if admin_photo_object_key:
            user_doc["profile_photo_object_key"] = admin_photo_object_key
            user_doc["profile_photo_updated_at"] = admin_photo_updated_at
        if admin_registration_number:
            user_doc["registration_number"] = admin_registration_number

        _upsert_mongo_by_id(db, "auth_users", user_id, user_doc)
        sql_db.commit()
    except DuplicateKeyError as exc:
        if admin_photo_object_key:
            try:
                mark_media_deleted(sql_db, admin_photo_object_key)
            except Exception:
                pass
        sql_db.rollback()
        raise HTTPException(status_code=409, detail="Email or linked profile already exists") from exc
    except HTTPException:
        if admin_photo_object_key:
            try:
                mark_media_deleted(sql_db, admin_photo_object_key)
            except Exception:
                pass
        sql_db.rollback()
        raise
    except Exception as exc:  # noqa: BLE001
        if admin_photo_object_key:
            try:
                mark_media_deleted(sql_db, admin_photo_object_key)
            except Exception:
                pass
        sql_db.rollback()
        raise HTTPException(status_code=500, detail="Failed to register user") from exc

    mirror_event(
        "auth.register",
        {
            "user_id": user_doc["id"],
            "email": user_doc["email"],
            "role": user_doc["role"],
            "student_id": user_doc["student_id"],
            "faculty_id": user_doc["faculty_id"],
        },
        actor={"email": email, "role": role.value},
    )

    return _auth_user_out(user_doc)


@router.post("/bootstrap-admin", response_model=schemas.AuthUserOut, status_code=status.HTTP_201_CREATED)
def bootstrap_admin(payload: schemas.AdminBootstrapRequest):
    raise HTTPException(
        status_code=410,
        detail=(
            "Admin bootstrap is disabled. Use /auth/register for admin/faculty/owner roles."
        ),
    )


@router.post("/users", response_model=schemas.AuthUserOut, status_code=status.HTTP_201_CREATED)
def create_auth_user(
    payload: schemas.AuthUserCreate,
):
    raise HTTPException(status_code=410, detail="Use /auth/register for user self-registration.")


@router.get("/users", response_model=list[schemas.AuthUserOut])
def list_auth_users(
):
    raise HTTPException(status_code=410, detail="User listing endpoint is disabled in real-time mode.")


@router.post("/invites/privileged-role", response_model=schemas.PrivilegedRoleInviteOut)
def create_privileged_role_invite(
    payload: schemas.PrivilegedRoleInviteCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    if current_user.role not in {models.UserRole.ADMIN, models.UserRole.OWNER}:
        raise HTTPException(status_code=403, detail="Only admin/owner can issue privileged role invites")
    if payload.role == models.UserRole.OWNER and current_user.role != models.UserRole.OWNER:
        raise HTTPException(status_code=403, detail="Only owner can issue owner-role invites")
    if not _is_privileged_role(payload.role):
        raise HTTPException(status_code=400, detail="Invite endpoint is only for admin/faculty/owner roles")

    db = _mongo_db_or_503()
    email = _normalize_email(payload.email)
    _validate_role_email(email, payload.role)

    invite_token = secrets.token_urlsafe(32)
    token_hash, token_salt = hash_otp(invite_token)
    expires_at = datetime.utcnow() + timedelta(hours=int(payload.expires_in_hours))
    invite_doc = {
        "id": _next_unique_id(db, collection="auth_role_invites", sequence_name="auth_role_invites"),
        "email": email,
        "role": payload.role.value,
        "token_hash": token_hash,
        "token_salt": token_salt,
        "created_by_user_id": int(current_user.id),
        "created_by_email": str(current_user.email or ""),
        "created_at": datetime.utcnow(),
        "expires_at": expires_at,
        "used_at": None,
    }
    db["auth_role_invites"].insert_one(invite_doc)
    mirror_event(
        "auth.privileged_invite_created",
        {
            "invite_id": invite_doc["id"],
            "email": email,
            "role": payload.role.value,
            "expires_at": expires_at,
        },
        actor={"user_id": int(current_user.id), "email": current_user.email, "role": current_user.role.value},
    )
    return schemas.PrivilegedRoleInviteOut(
        email=email,
        role=payload.role,
        invite_token=invite_token,
        expires_at=expires_at,
    )


@router.post("/login/request-otp", response_model=schemas.OTPRequestResponse)
def request_login_otp(
    payload: schemas.LoginOTPRequest,
    request: Request,
    sql_db: Session = Depends(get_db),
):
    db = _mongo_db_or_503()
    try:
        email = _normalize_email(payload.email)
        enforce_rate_limit(
            request,
            scope="auth.login.request_otp",
            principal=email,
            limit=10,
            window_seconds=300,
        )
        user = db["auth_users"].find_one({"email": email})
        if not user:
            raise HTTPException(
                status_code=404,
                detail="There is no account associated with this mail, kindly create one first.",
            )

        if not bool(user.get("is_active", True)):
            raise HTTPException(status_code=403, detail="User account is inactive")

        try:
            role = models.UserRole(user.get("role", models.UserRole.STUDENT.value))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid user role for OTP login") from exc
        _reject_if_legacy_primary_login_consumed(user)
        _validate_role_email(email, role, allow_legacy_primary=_primary_email_update_required(user))
        _ensure_selected_login_role(actual_role=role, selected_role=payload.role)
        requires_password_setup = _password_setup_required(user)
        signup_verification_pending = _student_signup_verification_pending(user)
        candidate_password = str(payload.password or "")
        if role != models.UserRole.STUDENT and requires_password_setup and role in {
            models.UserRole.ADMIN,
            models.UserRole.FACULTY,
        }:
            if candidate_password and not verify_password(candidate_password, user.get("password_hash", "")):
                raise HTTPException(status_code=401, detail="Incorrect password")
        elif role != models.UserRole.STUDENT and not candidate_password:
            raise HTTPException(status_code=401, detail="Password is required for this account")
        elif role != models.UserRole.STUDENT and not verify_password(candidate_password, user.get("password_hash", "")):
            raise HTTPException(status_code=401, detail="Incorrect password")
        if role == models.UserRole.STUDENT:
            _verify_student_auth_recaptcha(
                request,
                payload.captcha_token,
                action="student_login",
            )
        elif role in {models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.OWNER}:
            _verify_student_auth_recaptcha(
                request,
                payload.captcha_token,
                action="privileged_login_otp_request",
            )
        if not requires_password_setup and not signup_verification_pending and password_expired(user):
            raise HTTPException(status_code=status.HTTP_428_PRECONDITION_REQUIRED, detail=PASSWORD_EXPIRED_DETAIL)
        user_id = _ensure_auth_user_id(db, user, sql_db)
        _ensure_role_profile_link(db, sql_db, user_doc=user, role=role, email=email)
        if role == models.UserRole.STUDENT and not _has_real_profile_for_legacy_otp_login(
            db,
            sql_db,
            role=role,
            user_doc=user,
            email=email,
        ):
            raise HTTPException(
                status_code=404,
                detail="There is no account associated with this mail, kindly create one first.",
            )

        if role != models.UserRole.STUDENT and requires_password_setup and not _has_real_profile_for_legacy_otp_login(
            db,
            sql_db,
            role=role,
            user_doc=user,
            email=email,
        ):
            raise HTTPException(
                status_code=404,
                detail="There is no account associated with this mail, kindly create one first.",
            )

        destination_email = user["email"]
        if payload.send_to_alternate:
            raise HTTPException(
                status_code=400,
                detail="OTP delivery is restricted to the primary login email.",
            )

        now = datetime.utcnow()
        cooldown_seconds = _otp_resend_cooldown_seconds()
        last_otp = db["auth_otps"].find_one(
            {"user_id": user_id, "purpose": "login", "used_at": None},
            sort=[("created_at", -1)],
        )
        if last_otp:
            last_created = _coerce_datetime(last_otp.get("created_at"))
            if last_created:
                elapsed = (now - _to_utc_naive(last_created)).total_seconds()
                if elapsed < cooldown_seconds:
                    retry_after = max(1, int(cooldown_seconds - elapsed))
                    raise HTTPException(
                        status_code=429,
                        detail=f"OTP already sent. Please wait {retry_after} seconds before requesting again.",
                        headers={"Retry-After": str(retry_after)},
                    )

        db["auth_otps"].update_many(
            {
                "user_id": user_id,
                "purpose": "login",
                "used_at": None,
            },
            {"$set": {"used_at": now}},
        )

        otp_code = generate_otp_code()
        otp_hash, otp_salt = hash_otp(otp_code)
        validity_minutes = otp_expiry_minutes()
        expires_at = now + timedelta(minutes=validity_minutes)

        otp_doc = {
            "id": _next_unique_id(db, collection="auth_otps", sequence_name="auth_otps"),
            "user_id": user_id,
            "otp_hash": otp_hash,
            "otp_salt": otp_salt,
            "purpose": "login",
            "role": role.value,
            "attempts_count": 0,
            "expires_at": expires_at,
            "used_at": None,
            "created_at": now,
        }
        db["auth_otps"].insert_one(otp_doc)

        try:
            delivery = _send_login_otp_with_timeout(destination_email, otp_code)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Login OTP delivery failed for email=%s destination=%s", email, destination_email)
            db["auth_otps"].update_one({"id": otp_doc["id"]}, {"$set": {"used_at": datetime.utcnow()}})
            db["auth_otp_delivery"].insert_one(
                {
                    "id": _next_unique_id(db, collection="auth_otp_delivery", sequence_name="auth_otp_delivery"),
                    "user_id": user_id,
                    "destination": destination_email,
                    "channel": "delivery-failed",
                    "status": "failed",
                    "error": str(exc),
                    "created_at": datetime.utcnow(),
                }
            )
            raise HTTPException(
                status_code=503,
                detail="OTP delivery is temporarily unavailable. Please retry shortly or contact support.",
            ) from exc

        db["auth_otp_delivery"].insert_one(
            {
                "id": _next_unique_id(db, collection="auth_otp_delivery", sequence_name="auth_otp_delivery"),
                "user_id": user_id,
                "destination": destination_email,
                "channel": str(delivery["channel"]),
                "status": "sent",
                "created_at": datetime.utcnow(),
            }
        )

        mirror_event(
            "auth.otp_requested",
            {
                "user_id": user_id,
                "email": user["email"],
                "delivery_destination": destination_email,
                "expires_at": expires_at,
            },
            actor={"user_id": user_id, "email": user["email"], "role": user["role"]},
        )

        return schemas.OTPRequestResponse(
            message=(
                "OTP sent successfully. Verify it to complete your signup."
                if signup_verification_pending
                else "OTP sent successfully"
            ),
            expires_at=expires_at,
            delivered_to=destination_email,
            cooldown_seconds=cooldown_seconds,
            validity_minutes=validity_minutes,
        )
    except HTTPException:
        raise
    except PyMongoError as exc:
        _raise_auth_datastore_unavailable(exc)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected OTP request failure for email=%s", payload.email)
        raise HTTPException(
            status_code=503,
            detail=(
                "Unable to process OTP request right now. Please retry in a few seconds."
            ),
        ) from exc


@router.post("/student/login", response_model=schemas.TokenResponse)
def login_student_with_password(
    payload: schemas.LoginPasswordRequest,
    response: Response,
    request: Request,
    sql_db: Session = Depends(get_db),
):
    db = _mongo_db_or_503()
    try:
        email = _normalize_email(payload.email)
        enforce_rate_limit(
            request,
            scope="auth.student.login",
            principal=email,
            limit=12,
            window_seconds=300,
        )
        _verify_student_auth_recaptcha(
            request,
            payload.captcha_token,
            action="student_login",
        )
        user = db["auth_users"].find_one({"email": email})
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        try:
            actual_role = models.UserRole(user.get("role", models.UserRole.STUDENT.value))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid user role") from exc

        _reject_if_legacy_primary_login_consumed(user)
        _validate_role_email(email, actual_role, allow_legacy_primary=_primary_email_update_required(user))
        # Validate that the user selected the correct role in the dropdown
        _ensure_selected_login_role(actual_role=actual_role, selected_role=payload.role)

        if actual_role != models.UserRole.STUDENT:
            raise HTTPException(status_code=403, detail="Student password login is only available for student accounts")
        if not bool(user.get("is_active", True)):
            raise HTTPException(status_code=403, detail="User account is inactive")
        if _student_signup_verification_pending(user):
            raise HTTPException(
                status_code=428,
                detail="Complete signup OTP verification before signing in.",
            )
        if _password_setup_required(user):
            raise HTTPException(
                status_code=428,
                detail="You do not have your password set yet. Login via temporary OTP and set your password immediately.",
            )
        password_hash = str(user.get("password_hash") or "").strip()
        if not password_hash or not verify_password(payload.password, password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if password_expired(user):
            raise HTTPException(status_code=status.HTTP_428_PRECONDITION_REQUIRED, detail=PASSWORD_EXPIRED_DETAIL)

        user_id = _ensure_auth_user_id(db, user, sql_db)
        _ensure_role_profile_link(
            db,
            sql_db,
            user_doc=user,
            role=models.UserRole.STUDENT,
            email=email,
        )
        now = datetime.utcnow()

        # Revoke all existing sessions for single-session enforcement
        revoked_count = revoke_all_user_sessions(
            db,
            user_id=user_id,
            reason="new_login_single_session_enforcement",
        )
        if revoked_count > 0:
            logger.info(
                "Revoked %d existing session(s) for user_id=%d due to new login",
                revoked_count,
                user_id,
            )

        auth_update = {"last_login_at": now, "primary_login_verified": True}
        auth_inc: dict[str, int] = {}
        _mark_legacy_primary_migration_login(user, now=now, auth_update=auth_update, auth_inc=auth_inc)
        auth_write: dict[str, Any] = {"$set": auth_update}
        if auth_inc:
            auth_write["$inc"] = auth_inc
        db["auth_users"].update_one(
            {"id": user_id},
            auth_write,
        )
        user["last_login_at"] = now
        user["primary_login_verified"] = True
        if auth_update.get("primary_email_migration_started_at"):
            user["primary_email_migration_started_at"] = auth_update["primary_email_migration_started_at"]
        if auth_update.get("primary_email_migration_last_login_at"):
            user["primary_email_migration_last_login_at"] = auth_update["primary_email_migration_last_login_at"]
        if auth_inc.get("primary_email_migration_login_count"):
            user["primary_email_migration_login_count"] = _legacy_primary_email_migration_login_count(user) + 1

        session_tokens = create_session_tokens(
            db,
            CurrentUser(
                id=user_id,
                email=user["email"],
                role=models.UserRole.STUDENT,
                student_id=user.get("student_id"),
                faculty_id=user.get("faculty_id"),
                alternate_email=_get_alternate_email(user),
                primary_login_verified=True,
                is_active=True,
                created_at=user.get("created_at"),
                last_login_at=user.get("last_login_at"),
                mfa_enabled=False,
                mfa_authenticated=False,
            ),
            request=request,
        )
        mirror_event(
            "auth.student_login_success",
            {
                "user_id": user_id,
                "email": user["email"],
                "access_expires_at": session_tokens["access_expires_at"],
                "refresh_expires_at": session_tokens["refresh_expires_at"],
            },
            actor={"user_id": user_id, "email": user["email"], "role": user["role"]},
        )
        _set_auth_cookies(
            response,
            access_token=session_tokens["access_token"],
            access_expires_at=session_tokens["access_expires_at"],
            refresh_token=session_tokens["refresh_token"],
            refresh_expires_at=session_tokens["refresh_expires_at"],
        )
        return schemas.TokenResponse(
            access_token=session_tokens["access_token"],
            token_type="bearer",
            expires_at=session_tokens["access_expires_at"],
            refresh_token=session_tokens["refresh_token"],
            refresh_expires_at=session_tokens["refresh_expires_at"],
            user=_auth_user_out(user),
        )
    except HTTPException:
        raise
    except PyMongoError as exc:
        _raise_auth_datastore_unavailable(exc)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected student password login failure for email=%s", payload.email)
        raise HTTPException(status_code=503, detail="Unable to login right now. Please retry in a few seconds.") from exc


@router.post("/login/verify-otp", response_model=schemas.TokenResponse)
def verify_login_otp(
    payload: schemas.VerifyOTPRequest,
    response: Response,
    request: Request,
    sql_db: Session = Depends(get_db),
):
    db = _mongo_db_or_503()
    try:
        email = _normalize_email(payload.email)
        enforce_rate_limit(
            request,
            scope="auth.login.verify_otp",
            principal=email,
            limit=25,
            window_seconds=300,
        )
        user = db["auth_users"].find_one({"email": email})
        if not user:
            raise HTTPException(status_code=401, detail="Invalid OTP flow")

        try:
            role = models.UserRole(user.get("role", models.UserRole.STUDENT.value))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid user role for OTP login") from exc
        _reject_if_legacy_primary_login_consumed(user)
        _validate_role_email(email, role, allow_legacy_primary=_primary_email_update_required(user))
        _ensure_selected_login_role(actual_role=role, selected_role=payload.role)
        if not bool(user.get("is_active", True)):
            raise HTTPException(status_code=403, detail="User account is inactive")
        user_id = _ensure_auth_user_id(db, user, sql_db)
        _ensure_role_profile_link(db, sql_db, user_doc=user, role=role, email=email)
        if _password_setup_required(user) and not _has_real_profile_for_legacy_otp_login(
            db,
            sql_db,
            role=role,
            user_doc=user,
            email=email,
        ):
            raise HTTPException(
                status_code=404,
                detail="There is no account associated with this mail, kindly create one first.",
            )

        otp_row = db["auth_otps"].find_one(
            {
                "user_id": user_id,
                "purpose": "login",
                "used_at": None,
            },
            sort=[("created_at", -1)],
        )

        now = datetime.utcnow()

        if not otp_row:
            raise HTTPException(status_code=400, detail="No active OTP request found")
        otp_role = str(otp_row.get("role") or role.value).strip().lower()
        if otp_role != role.value:
            raise HTTPException(status_code=403, detail="OTP was requested for a different account role. Request a new OTP.")

        expires_at = _coerce_datetime(otp_row.get("expires_at"))
        if not expires_at:
            db["auth_otps"].update_one({"id": otp_row["id"]}, {"$set": {"used_at": now}})
            raise HTTPException(status_code=400, detail="Invalid OTP record. Request a new OTP.")

        if _to_utc_naive(expires_at) < now:
            db["auth_otps"].update_one({"id": otp_row["id"]}, {"$set": {"used_at": now}})
            raise HTTPException(status_code=400, detail="OTP expired")

        if int(otp_row.get("attempts_count", 0)) >= 5:
            db["auth_otps"].update_one({"id": otp_row["id"]}, {"$set": {"used_at": now}})
            raise HTTPException(status_code=400, detail="OTP attempts exceeded")

        otp_candidate = _normalize_otp_candidate(payload.otp_code)
        if not verify_otp(otp_candidate, otp_row.get("otp_hash", ""), otp_row.get("otp_salt", "")):
            db["auth_otps"].update_one(
                {"id": otp_row["id"]},
                {"$inc": {"attempts_count": 1}},
            )
            raise HTTPException(status_code=400, detail="Invalid OTP")

        mfa_required = _privileged_mfa_required() and _requires_totp_mfa_role(role)
        mfa_enabled = bool(user.get("mfa_enabled", False))
        mfa_authenticated = False
        if mfa_required and mfa_enabled:
            if not _verify_and_consume_mfa_code(db, user, payload.mfa_code):
                raise HTTPException(
                    status_code=401,
                    detail="MFA code is required and must be a valid TOTP or backup code.",
                )
            mfa_authenticated = True
        if not _password_setup_required(user) and not _student_signup_verification_pending(user) and password_expired(user, now=now):
            raise HTTPException(status_code=status.HTTP_428_PRECONDITION_REQUIRED, detail=PASSWORD_EXPIRED_DETAIL)

        consume_result = db["auth_otps"].update_one(
            {"id": otp_row["id"], "used_at": None},
            {"$set": {"used_at": now}},
        )
        if int(getattr(consume_result, "matched_count", 0)) != 1:
            raise HTTPException(status_code=400, detail="OTP already used. Request a new OTP.")

        # Revoke all existing sessions for single-session enforcement
        revoked_count = revoke_all_user_sessions(
            db,
            user_id=user_id,
            reason="new_login_single_session_enforcement",
        )
        if revoked_count > 0:
            logger.info(
                "Revoked %d existing session(s) for user_id=%d due to new login",
                revoked_count,
                user_id,
            )

        auth_update: dict[str, Any] = {"last_login_at": now, "primary_login_verified": True}
        auth_inc: dict[str, int] = {}
        _mark_legacy_primary_migration_login(user, now=now, auth_update=auth_update, auth_inc=auth_inc)
        if bool(user.get("signup_verification_required", False)):
            auth_update["signup_verification_required"] = False
        if mfa_authenticated:
            auth_update["mfa_last_verified_at"] = now

        auth_write: dict[str, Any] = {"$set": auth_update}
        if auth_inc:
            auth_write["$inc"] = auth_inc
        db["auth_users"].update_one(
            {"id": user_id},
            auth_write,
        )
        user["last_login_at"] = now
        user["primary_login_verified"] = True
        if auth_update.get("primary_email_migration_started_at"):
            user["primary_email_migration_started_at"] = auth_update["primary_email_migration_started_at"]
        if auth_update.get("primary_email_migration_last_login_at"):
            user["primary_email_migration_last_login_at"] = auth_update["primary_email_migration_last_login_at"]
        if auth_inc.get("primary_email_migration_login_count"):
            user["primary_email_migration_login_count"] = _legacy_primary_email_migration_login_count(user) + 1
        if bool(user.get("signup_verification_required", False)):
            user["signup_verification_required"] = False
        user["mfa_enabled"] = mfa_enabled

        session_tokens = create_session_tokens(
            db,
            CurrentUser(
                id=user_id,
                email=user["email"],
                role=models.UserRole(user["role"]),
                student_id=user.get("student_id"),
                faculty_id=user.get("faculty_id"),
                alternate_email=_get_alternate_email(user),
                primary_login_verified=bool(user.get("primary_login_verified", False)),
                is_active=bool(user.get("is_active", True)),
                created_at=user.get("created_at"),
                last_login_at=user.get("last_login_at"),
                mfa_enabled=mfa_enabled,
                mfa_authenticated=mfa_authenticated,
            ),
            request=request,
        )

        mirror_event(
            "auth.login_success",
            {
                "user_id": user_id,
                "email": user["email"],
                "access_expires_at": session_tokens["access_expires_at"],
                "refresh_expires_at": session_tokens["refresh_expires_at"],
                "mfa_required": mfa_required,
                "mfa_enabled": mfa_enabled,
                "mfa_authenticated": mfa_authenticated,
            },
            actor={"user_id": user_id, "email": user["email"], "role": user["role"]},
        )
        _set_auth_cookies(
            response,
            access_token=session_tokens["access_token"],
            access_expires_at=session_tokens["access_expires_at"],
            refresh_token=session_tokens["refresh_token"],
            refresh_expires_at=session_tokens["refresh_expires_at"],
        )

        return schemas.TokenResponse(
            access_token=session_tokens["access_token"],
            token_type="bearer",
            expires_at=session_tokens["access_expires_at"],
            refresh_token=session_tokens["refresh_token"],
            refresh_expires_at=session_tokens["refresh_expires_at"],
            user=_auth_user_out(user),
        )
    except HTTPException:
        raise
    except PyMongoError as exc:
        _raise_auth_datastore_unavailable(exc)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected OTP verify failure for email=%s", payload.email)
        raise HTTPException(
            status_code=503,
            detail=(
                "Unable to verify OTP right now. Please retry in a few seconds."
            ),
        ) from exc


@router.post("/token/refresh", response_model=schemas.TokenResponse)
def refresh_auth_token(
    response: Response,
    request: Request,
):
    db = _mongo_db_or_503()
    try:
        refresh_token = get_refresh_token_from_request(request)
        rotated = rotate_session_tokens(db, refresh_token=refresh_token, request=request)
        user_id = int(rotated["user"].id)
        user_doc = db["auth_users"].find_one({"id": user_id})
        if not user_doc:
            raise HTTPException(status_code=401, detail="Invalid refresh session")

        _set_auth_cookies(
            response,
            access_token=rotated["access_token"],
            access_expires_at=rotated["access_expires_at"],
            refresh_token=rotated["refresh_token"],
            refresh_expires_at=rotated["refresh_expires_at"],
        )

        mirror_event(
            "auth.token_refreshed",
            {
                "user_id": user_id,
                "session_id": rotated["sid"],
                "access_expires_at": rotated["access_expires_at"],
                "refresh_expires_at": rotated["refresh_expires_at"],
            },
            actor={
                "user_id": user_id,
                "email": user_doc.get("email"),
                "role": user_doc.get("role"),
            },
        )

        return schemas.TokenResponse(
            access_token=rotated["access_token"],
            token_type="bearer",
            expires_at=rotated["access_expires_at"],
            refresh_token=rotated["refresh_token"],
            refresh_expires_at=rotated["refresh_expires_at"],
            user=_auth_user_out(user_doc),
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected token refresh failure")
        raise HTTPException(status_code=401, detail="Invalid refresh session") from exc


@router.post("/password/request-otp", response_model=schemas.OTPRequestResponse)
def request_password_reset_otp(
    payload: schemas.PasswordResetOTPRequest,
    request: Request,
    sql_db: Session = Depends(get_db),
):
    db = _mongo_db_or_503()
    try:
        email = _normalize_email(payload.email)
        enforce_rate_limit(
            request,
            scope="auth.password.request_otp",
            principal=email,
            limit=8,
            window_seconds=300,
        )
        _verify_student_auth_recaptcha(
            request,
            payload.captcha_token,
            action="student_password_reset_request",
        )
        user = db["auth_users"].find_one({"email": email})
        if not user:
            sql_auth_user = (
                sql_db.query(models.AuthUser).filter(models.AuthUser.email == email).first()
            )
            if sql_auth_user:
                user = {
                    "id": int(sql_auth_user.id),
                    "email": str(sql_auth_user.email or "").strip().lower(),
                    "password_hash": str(sql_auth_user.password_hash or "").strip(),
                    "role": sql_auth_user.role.value,
                    "student_id": sql_auth_user.student_id,
                    "faculty_id": sql_auth_user.faculty_id,
                    "is_active": bool(sql_auth_user.is_active),
                    "created_at": sql_auth_user.created_at,
                    "last_login_at": sql_auth_user.last_login_at,
                    "password_updated_at": sql_auth_user.password_updated_at,
                }
                _upsert_mongo_by_id(db, "auth_users", int(sql_auth_user.id), user)
            else:
                sql_student = sql_db.query(models.Student).filter(models.Student.email == email).first()
                if sql_student and str(sql_student.registration_number or "").strip():
                    provided_registration = _normalize_registration_number(payload.registration_number)
                    linked_registration = _normalize_registration_number(str(sql_student.registration_number))
                    if provided_registration == linked_registration:
                        generated_password_hash = hash_password(secrets.token_urlsafe(24))
                        sql_auth_user, _ = upsert_sql_auth_user_record(
                            sql_db,
                            email=email,
                            password_hash=generated_password_hash,
                            role=models.UserRole.STUDENT,
                            student_id=int(sql_student.id),
                            faculty_id=None,
                            is_active=True,
                            created_at=datetime.utcnow(),
                        )
                        user_id = int(sql_auth_user.id)
                        user = {
                            "id": user_id,
                            "email": email,
                            "password_hash": generated_password_hash,
                            "role": models.UserRole.STUDENT.value,
                            "student_id": int(sql_student.id),
                            "faculty_id": None,
                            "alternate_email": None,
                            "alternate_email_encrypted": None,
                            "alternate_email_hash": None,
                            "primary_login_verified": False,
                            "mfa_enabled": False,
                            "mfa_totp_secret": None,
                            "mfa_backup_code_hashes": [],
                            "mfa_enrolled_at": None,
                            "mfa_last_verified_at": None,
                            "mfa_totp_skew_steps": 0,
                            "mfa_setup_secret": None,
                            "mfa_setup_backup_code_hashes": [],
                            "mfa_setup_expires_at": None,
                            "is_active": True,
                            "created_at": datetime.utcnow(),
                            "last_login_at": None,
                            "password_setup_required": True,
                        }
                        _upsert_mongo_by_id(db, "auth_users", user_id, user)
                if not user:
                    raise HTTPException(status_code=401, detail="Invalid email or registration number")

        if not bool(user.get("is_active", True)):
            raise HTTPException(status_code=403, detail="User account is inactive")

        try:
            role = models.UserRole(user.get("role", models.UserRole.STUDENT.value))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid user role for password reset") from exc
        _validate_role_email(email, role, allow_legacy_primary=_primary_email_update_required(user))
        user_id = _ensure_auth_user_id(db, user, sql_db)
        if role == models.UserRole.STUDENT:
            align_student_profile_id_with_sql(db, sql_db, email=email, user_doc=user)
        elif role == models.UserRole.FACULTY:
            align_faculty_profile_id_with_sql(db, sql_db, email=email, user_doc=user)

        if role == models.UserRole.STUDENT:
            student_id = user.get("student_id")
            registration_number = ""
            student = None
            if student_id:
                student = db["students"].find_one({"id": int(student_id)})
                registration_number = str(student.get("registration_number", "")).strip() if student else ""

            if not registration_number:
                sql_student = None
                if student_id:
                    sql_student = (
                        sql_db.query(models.Student).filter(models.Student.id == int(student_id)).first()
                    )
                if not sql_student:
                    sql_student = sql_db.query(models.Student).filter(models.Student.email == email).first()
                if sql_student:
                    registration_number = str(sql_student.registration_number or "").strip()
                    if not student_id:
                        student_id = int(sql_student.id)
                        db["auth_users"].update_one({"id": user_id}, {"$set": {"student_id": student_id}})
                        user["student_id"] = student_id
                    if student_id and registration_number:
                        _upsert_mongo_by_id(
                            db,
                            "students",
                            int(student_id),
                            {
                                "name": sql_student.name,
                                "email": sql_student.email,
                                "registration_number": sql_student.registration_number,
                                "parent_email": sql_student.parent_email,
                                "section": sql_student.section,
                                "section_updated_at": sql_student.section_updated_at,
                                "profile_photo_data_url": sql_student.profile_photo_data_url,
                                "profile_photo_object_key": sql_student.profile_photo_object_key,
                                "profile_photo_updated_at": sql_student.profile_photo_updated_at,
                                "profile_photo_locked_until": sql_student.profile_photo_locked_until,
                                "department": sql_student.department,
                                "semester": sql_student.semester,
                                "created_at": sql_student.created_at,
                                "source": "password-reset-sync",
                            },
                        )

            if not registration_number:
                raise HTTPException(status_code=401, detail="Invalid email or registration number")

            provided_registration = _normalize_registration_number(payload.registration_number)
            linked_registration = _normalize_registration_number(registration_number)
            if provided_registration != linked_registration:
                raise HTTPException(status_code=401, detail="Invalid email or registration number")

        now = datetime.utcnow()
        cooldown_seconds = _otp_resend_cooldown_seconds()
        last_otp = db["auth_otps"].find_one(
            {"user_id": user_id, "purpose": "password_reset", "used_at": None},
            sort=[("created_at", -1)],
        )
        if last_otp:
            last_created = _coerce_datetime(last_otp.get("created_at"))
            if last_created:
                elapsed = (now - _to_utc_naive(last_created)).total_seconds()
                if elapsed < cooldown_seconds:
                    retry_after = max(1, int(cooldown_seconds - elapsed))
                    raise HTTPException(
                        status_code=429,
                        detail=f"OTP already sent. Please wait {retry_after} seconds before requesting again.",
                        headers={"Retry-After": str(retry_after)},
                    )

        db["auth_otps"].update_many(
            {"user_id": user_id, "purpose": "password_reset", "used_at": None},
            {"$set": {"used_at": now}},
        )

        otp_code = generate_otp_code()
        otp_hash, otp_salt = hash_otp(otp_code)
        validity_minutes = otp_expiry_minutes()
        expires_at = now + timedelta(minutes=validity_minutes)

        otp_doc = {
            "id": _next_unique_id(db, collection="auth_otps", sequence_name="auth_otps"),
            "user_id": user_id,
            "otp_hash": otp_hash,
            "otp_salt": otp_salt,
            "purpose": "password_reset",
            "attempts_count": 0,
            "expires_at": expires_at,
            "used_at": None,
            "created_at": now,
        }
        db["auth_otps"].insert_one(otp_doc)

        try:
            delivery = _send_login_otp_with_timeout(email, otp_code)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Password reset OTP delivery failed for email=%s", email)
            db["auth_otps"].update_one({"id": otp_doc["id"]}, {"$set": {"used_at": datetime.utcnow()}})
            db["auth_otp_delivery"].insert_one(
                {
                    "id": _next_unique_id(db, collection="auth_otp_delivery", sequence_name="auth_otp_delivery"),
                    "user_id": user_id,
                    "destination": email,
                    "channel": "delivery-failed",
                    "status": "failed",
                    "error": str(exc),
                    "created_at": datetime.utcnow(),
                }
            )
            raise HTTPException(
                status_code=503,
                detail="OTP delivery is temporarily unavailable. Please retry shortly or contact support.",
            ) from exc

        db["auth_otp_delivery"].insert_one(
            {
                "id": _next_unique_id(db, collection="auth_otp_delivery", sequence_name="auth_otp_delivery"),
                "user_id": user_id,
                "destination": email,
                "channel": delivery.get("channel", "email"),
                "status": "sent",
                "created_at": datetime.utcnow(),
            }
        )

        mirror_event(
            "auth.password_reset_otp_requested",
            {
                "user_id": user_id,
                "email": user["email"],
                "expires_at": expires_at,
            },
            actor={"user_id": user_id, "email": user["email"], "role": user["role"]},
        )

        sql_db.commit()

        return schemas.OTPRequestResponse(
            message="Password reset OTP sent successfully",
            expires_at=expires_at,
            delivered_to=email,
            cooldown_seconds=cooldown_seconds,
            validity_minutes=validity_minutes,
        )
    except HTTPException:
        raise
    except PyMongoError as exc:
        _raise_auth_datastore_unavailable(exc)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected password-reset OTP request failure for email=%s", payload.email)
        raise HTTPException(
            status_code=503,
            detail=(
                "Unable to process password-reset OTP right now. Please retry in a few seconds."
            ),
        ) from exc


@router.post("/password/verify-otp", response_model=schemas.PasswordResetVerifyResponse)
def verify_password_reset_otp(
    payload: schemas.PasswordResetVerifyOTPRequest,
    request: Request,
    sql_db: Session = Depends(get_db),
):
    db = _mongo_db_or_503()
    try:
        email = _normalize_email(payload.email)
        enforce_rate_limit(
            request,
            scope="auth.password.verify_otp",
            principal=email,
            limit=20,
            window_seconds=300,
        )
        user = db["auth_users"].find_one({"email": email})
        if not user:
            raise HTTPException(status_code=401, detail="Invalid OTP flow")
        try:
            models.UserRole(user.get("role", models.UserRole.STUDENT.value))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid user role for password reset") from exc
        user_id = _ensure_auth_user_id(db, user, sql_db)

        otp_row = db["auth_otps"].find_one(
            {"user_id": user_id, "purpose": "password_reset", "used_at": None},
            sort=[("created_at", -1)],
        )
        now = datetime.utcnow()

        if not otp_row:
            raise HTTPException(status_code=400, detail="No active OTP request found")

        expires_at = _coerce_datetime(otp_row.get("expires_at"))
        if not expires_at:
            db["auth_otps"].update_one({"id": otp_row["id"]}, {"$set": {"used_at": now}})
            raise HTTPException(status_code=400, detail="Invalid OTP record. Request a new OTP.")

        if _to_utc_naive(expires_at) < now:
            db["auth_otps"].update_one({"id": otp_row["id"]}, {"$set": {"used_at": now}})
            raise HTTPException(status_code=400, detail="OTP expired")

        if int(otp_row.get("attempts_count", 0)) >= 5:
            db["auth_otps"].update_one({"id": otp_row["id"]}, {"$set": {"used_at": now}})
            raise HTTPException(status_code=400, detail="OTP attempts exceeded")

        otp_candidate = _normalize_otp_candidate(payload.otp_code)
        if not verify_otp(otp_candidate, otp_row.get("otp_hash", ""), otp_row.get("otp_salt", "")):
            db["auth_otps"].update_one({"id": otp_row["id"]}, {"$inc": {"attempts_count": 1}})
            raise HTTPException(status_code=400, detail="Invalid OTP")

        consume_result = db["auth_otps"].update_one(
            {"id": otp_row["id"], "used_at": None},
            {"$set": {"used_at": now}},
        )
        if int(getattr(consume_result, "matched_count", 0)) != 1:
            raise HTTPException(status_code=400, detail="OTP already used. Request a new OTP.")
        db["auth_password_resets"].update_many(
            {"user_id": user_id, "used_at": None},
            {"$set": {"used_at": now}},
        )

        reset_token = secrets.token_urlsafe(36)
        reset_hash, reset_salt = hash_otp(reset_token)
        reset_expires_at = now + timedelta(minutes=_password_reset_token_validity_minutes())
        reset_doc = {
            "id": _next_unique_id(db, collection="auth_password_resets", sequence_name="auth_password_resets"),
            "user_id": user_id,
            "email": email,
            "token_hash": reset_hash,
            "token_salt": reset_salt,
            "expires_at": reset_expires_at,
            "used_at": None,
            "created_at": now,
        }
        db["auth_password_resets"].insert_one(reset_doc)

        mirror_event(
            "auth.password_reset_otp_verified",
            {
                "user_id": user_id,
                "email": email,
                "reset_expires_at": reset_expires_at,
            },
            actor={"user_id": user_id, "email": email, "role": user.get("role")},
        )

        return schemas.PasswordResetVerifyResponse(
            message="OTP verified. You can now set a new password.",
            reset_token=reset_token,
            expires_at=reset_expires_at,
        )
    except HTTPException:
        raise
    except PyMongoError as exc:
        _raise_auth_datastore_unavailable(exc)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected password-reset OTP verification failure for email=%s", payload.email)
        raise HTTPException(
            status_code=503,
            detail=(
                "Unable to verify password-reset OTP right now. Please retry in a few seconds."
            ),
        ) from exc


@router.post("/password/reset", response_model=schemas.MessageResponse)
def reset_password(
    payload: schemas.PasswordResetConfirmRequest,
    request: Request,
    sql_db: Session = Depends(get_db),
):
    db = _mongo_db_or_503()
    try:
        email = _normalize_email(payload.email)
        enforce_rate_limit(
            request,
            scope="auth.password.reset",
            principal=email,
            limit=12,
            window_seconds=600,
        )
        _verify_student_auth_recaptcha(
            request,
            payload.captcha_token,
            action="student_password_reset_confirm",
        )
        user = db["auth_users"].find_one({"email": email})
        if not user:
            raise HTTPException(status_code=401, detail="Invalid password reset request")
        try:
            models.UserRole(user.get("role", models.UserRole.STUDENT.value))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid user role for password reset") from exc
        user_id = _ensure_auth_user_id(db, user, sql_db)

        _validate_password_strength(payload.new_password)

        reset_row = db["auth_password_resets"].find_one(
            {"user_id": user_id, "used_at": None},
            sort=[("created_at", -1)],
        )
        now = datetime.utcnow()
        if not reset_row:
            raise HTTPException(status_code=400, detail="Verify OTP before setting a new password")

        expires_at = _coerce_datetime(reset_row.get("expires_at"))
        if not expires_at:
            db["auth_password_resets"].update_one({"id": reset_row["id"]}, {"$set": {"used_at": now}})
            raise HTTPException(status_code=400, detail="Invalid reset session. Request OTP again.")

        if _to_utc_naive(expires_at) < now:
            db["auth_password_resets"].update_one({"id": reset_row["id"]}, {"$set": {"used_at": now}})
            raise HTTPException(status_code=400, detail="Reset session expired. Request OTP again.")

        if not verify_otp(payload.reset_token, reset_row.get("token_hash", ""), reset_row.get("token_salt", "")):
            raise HTTPException(status_code=400, detail="Invalid reset session. Request OTP again.")

        password_hash = hash_password(payload.new_password)
        db["auth_password_resets"].update_one({"id": reset_row["id"]}, {"$set": {"used_at": now}})
        db["auth_users"].update_one(
            {"id": user_id},
            {
                "$set": {
                    "password_hash": password_hash,
                    "password_updated_at": now,
                    "password_setup_required": False,
                }
            },
        )
        sql_user = sql_db.get(models.AuthUser, int(user_id))
        if sql_user is not None:
            sql_user.password_hash = password_hash
            sql_user.password_updated_at = now
            sql_db.commit()
        else:
            sql_db.rollback()
        db["auth_otps"].update_many(
            {"user_id": user_id, "purpose": {"$in": ["login", "password_reset"]}, "used_at": None},
            {"$set": {"used_at": now}},
        )

        mirror_event(
            "auth.password_reset_success",
            {"user_id": user_id, "email": email, "updated_at": now},
            actor={"user_id": user_id, "email": email, "role": user.get("role")},
        )

        return schemas.MessageResponse(message="Password updated successfully. Login with your new password.")
    except HTTPException:
        raise
    except PyMongoError as exc:
        _raise_auth_datastore_unavailable(exc)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected password reset failure for email=%s", payload.email)
        raise HTTPException(
            status_code=503,
            detail=(
                "Unable to reset password right now. Please retry in a few seconds."
            ),
        ) from exc


@router.post("/password/bootstrap", response_model=schemas.MessageResponse)
def bootstrap_account_password(
    payload: schemas.PasswordBootstrapRequest,
    current_user: CurrentUser = Depends(get_current_user),
    sql_db: Session = Depends(get_db),
):
    db = _mongo_db_or_503()
    user_doc = db["auth_users"].find_one({"id": int(current_user.id)})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid user session")
    role_raw = str(user_doc.get("role") or "").strip()
    if role_raw not in {
        models.UserRole.STUDENT.value,
        models.UserRole.ADMIN.value,
        models.UserRole.FACULTY.value,
    }:
        raise HTTPException(status_code=403, detail="Password bootstrap is not available for this account")
    if not _password_setup_required(user_doc):
        raise HTTPException(status_code=400, detail="Password setup is already complete for this account")

    _validate_password_strength(payload.new_password)
    now = datetime.utcnow()
    password_hash = hash_password(payload.new_password)
    db["auth_users"].update_one(
        {"id": int(current_user.id)},
        {
            "$set": {
                "password_hash": password_hash,
                "password_updated_at": now,
                "password_setup_required": False,
                "primary_login_verified": True,
            }
        },
    )
    try:
        sql_user = sql_db.get(models.AuthUser, int(current_user.id))
        if sql_user is not None:
            sql_user.password_hash = password_hash
            sql_user.password_updated_at = now
            sql_db.commit()
        else:
            sql_db.rollback()
    except Exception:
        sql_db.rollback()
        logger.exception("account_password_bootstrap_sql_sync_failed user_id=%s", current_user.id)

    mirror_event(
        "auth.account_password_bootstrap",
        {
            "user_id": int(current_user.id),
            "email": str(user_doc.get("email") or "").strip().lower(),
            "updated_at": now,
            "role": role_raw,
        },
        actor={
            "user_id": int(current_user.id),
            "email": str(user_doc.get("email") or "").strip().lower(),
            "role": role_raw,
        },
    )
    return schemas.MessageResponse(message="Password setup complete. Use email and password for future logins.")


@router.get("/mfa/status", response_model=schemas.MFAStatusResponse)
def mfa_status(current_user: CurrentUser = Depends(get_current_user)):
    db = _mongo_db_or_503()
    try:
        user_doc = db["auth_users"].find_one({"id": int(current_user.id)})
        if not user_doc:
            raise HTTPException(status_code=401, detail="Invalid user session")
        try:
            role = models.UserRole(user_doc.get("role", models.UserRole.STUDENT.value))
        except ValueError:
            role = models.UserRole.STUDENT
        required = _privileged_mfa_required() and _requires_totp_mfa_role(role)
        setup_expires = _coerce_datetime(user_doc.get("mfa_setup_expires_at"))
        pending_secret = str(user_doc.get("mfa_setup_secret") or "").strip()
        return schemas.MFAStatusResponse(
            required=required,
            enabled=bool(user_doc.get("mfa_enabled", False)),
            enrolled_at=_coerce_datetime(user_doc.get("mfa_enrolled_at")),
            backup_codes_remaining=len([x for x in (user_doc.get("mfa_backup_code_hashes") or []) if str(x).strip()]),
            setup_pending=bool(pending_secret and setup_expires and _to_utc_naive(setup_expires) >= datetime.utcnow()),
            setup_expires_at=setup_expires,
        )
    except HTTPException:
        raise
    except PyMongoError as exc:
        _raise_auth_datastore_unavailable(exc)


@router.post("/mfa/enroll", response_model=schemas.MFAEnrollResponse)
def mfa_enroll(current_user: CurrentUser = Depends(get_current_user)):
    if current_user.role not in {models.UserRole.ADMIN, models.UserRole.OWNER}:
        raise HTTPException(status_code=403, detail="MFA enrollment is reserved for admin and owner accounts.")
    db = _mongo_db_or_503()
    try:
        user_doc = db["auth_users"].find_one({"id": int(current_user.id)})
        if not user_doc:
            raise HTTPException(status_code=401, detail="Invalid user session")

        secret = generate_totp_secret()
        backup_codes, backup_hashes = _issue_backup_codes()
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=_mfa_setup_ttl_minutes())
        db["auth_users"].update_one(
            {"id": int(current_user.id)},
            {
                "$set": {
                    "mfa_setup_secret": secret,
                    "mfa_setup_backup_code_hashes": backup_hashes,
                    "mfa_setup_expires_at": expires_at,
                }
            },
        )

        issuer = quote((os.getenv("MFA_ISSUER_NAME", "LPU Smart Campus") or "LPU Smart Campus").strip(), safe="")
        label = quote(str(user_doc.get("email", f"user-{current_user.id}")), safe="")
        otpauth_uri = (
            f"otpauth://totp/{issuer}:{label}"
            f"?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"
        )
        qr_svg_data_uri = generate_totp_qr_svg_data_uri(otpauth_uri)

        mirror_event(
            "auth.mfa_setup_initiated",
            {
                "user_id": int(current_user.id),
                "email": user_doc.get("email"),
                "expires_at": expires_at,
            },
            actor={"user_id": int(current_user.id), "email": user_doc.get("email"), "role": user_doc.get("role")},
        )

        return schemas.MFAEnrollResponse(
            message="MFA setup initiated. Add the secret to your authenticator and verify one TOTP code.",
            secret=secret,
            otpauth_uri=otpauth_uri,
            qr_svg_data_uri=qr_svg_data_uri,
            backup_codes=backup_codes,
            setup_expires_at=expires_at,
        )
    except HTTPException:
        raise
    except PyMongoError as exc:
        _raise_auth_datastore_unavailable(exc)


@router.post("/mfa/activate", response_model=schemas.MessageResponse)
def mfa_activate(
    payload: schemas.MFAActivateRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    db = _mongo_db_or_503()
    try:
        user_doc = db["auth_users"].find_one({"id": int(current_user.id)})
        if not user_doc:
            raise HTTPException(status_code=401, detail="Invalid user session")
        try:
            role = models.UserRole(user_doc.get("role", models.UserRole.STUDENT.value))
        except ValueError:
            role = models.UserRole.STUDENT
        if role not in {models.UserRole.ADMIN, models.UserRole.OWNER}:
            raise HTTPException(status_code=403, detail="MFA activation is reserved for admin and owner accounts.")

        setup_secret = str(user_doc.get("mfa_setup_secret") or "").strip()
        setup_expires_at = _coerce_datetime(user_doc.get("mfa_setup_expires_at"))
        if not setup_secret or not setup_expires_at or _to_utc_naive(setup_expires_at) < datetime.utcnow():
            raise HTTPException(status_code=400, detail="MFA setup has expired. Start enrollment again.")
        totp_code = _normalize_otp_candidate(payload.totp_code)
        if len(totp_code) != 6:
            raise HTTPException(status_code=400, detail="Enter a valid 6-digit authenticator TOTP code.")
        matched_delta = _match_user_totp(
            setup_secret,
            totp_code,
            user_doc,
            allowed_drift_steps=_mfa_totp_activation_drift_steps(),
        )
        if matched_delta is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid TOTP code. Ensure Microsoft Authenticator account type is time-based "
                    "and your device time is set to automatic. If this persists, wait for a fresh code "
                    "and try again."
                ),
            )

        now = datetime.utcnow()
        backup_hashes = [str(item) for item in (user_doc.get("mfa_setup_backup_code_hashes") or []) if str(item).strip()]
        db["auth_users"].update_one(
            {"id": int(current_user.id)},
            {
                "$set": {
                    "mfa_enabled": True,
                    "mfa_totp_secret": setup_secret,
                    "mfa_backup_code_hashes": backup_hashes,
                    "mfa_enrolled_at": now,
                    "mfa_last_verified_at": now,
                    "mfa_totp_skew_steps": int(matched_delta),
                    "mfa_setup_secret": None,
                    "mfa_setup_backup_code_hashes": [],
                    "mfa_setup_expires_at": None,
                }
            },
        )
        if current_user.session_id:
            db["auth_sessions"].update_one(
                {"sid": str(current_user.session_id), "user_id": int(current_user.id)},
                {"$set": {"mfa_verified": True, "mfa_verified_at": now, "last_seen_at": now}},
            )

        mirror_event(
            "auth.mfa_enabled",
            {"user_id": int(current_user.id), "email": user_doc.get("email"), "enabled_at": now},
            actor={"user_id": int(current_user.id), "email": user_doc.get("email"), "role": user_doc.get("role")},
        )
        return schemas.MessageResponse(
            message="MFA has been activated. Use a fresh login with OTP + TOTP for protected routes."
        )
    except HTTPException:
        raise
    except PyMongoError as exc:
        _raise_auth_datastore_unavailable(exc)


@router.post("/mfa/backup-codes/rotate", response_model=schemas.MFABackupCodeRotateResponse)
def mfa_rotate_backup_codes(
    payload: schemas.MFAActivateRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    db = _mongo_db_or_503()
    try:
        user_doc = db["auth_users"].find_one({"id": int(current_user.id)})
        if not user_doc:
            raise HTTPException(status_code=401, detail="Invalid user session")
        if not bool(user_doc.get("mfa_enabled", False)):
            raise HTTPException(status_code=400, detail="MFA is not enabled for this account.")
        secret = str(user_doc.get("mfa_totp_secret") or "").strip()
        totp_code = _normalize_otp_candidate(payload.totp_code)
        if len(totp_code) != 6:
            raise HTTPException(status_code=400, detail="Enter a valid 6-digit authenticator TOTP code.")
        matched_delta = _match_user_totp(
            secret,
            totp_code,
            user_doc,
            allowed_drift_steps=_mfa_totp_login_drift_steps(),
        )
        if not secret or matched_delta is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid TOTP code. Ensure authenticator account type is time-based "
                    "and your device time is set to automatic."
                ),
            )

        backup_codes, backup_hashes = _issue_backup_codes()
        now = datetime.utcnow()
        db["auth_users"].update_one(
            {"id": int(current_user.id)},
            {
                "$set": {
                    "mfa_backup_code_hashes": backup_hashes,
                    "mfa_last_verified_at": now,
                    "mfa_totp_skew_steps": int(matched_delta),
                }
            },
        )
        mirror_event(
            "auth.mfa_backup_codes_rotated",
            {"user_id": int(current_user.id), "email": user_doc.get("email")},
            actor={"user_id": int(current_user.id), "email": user_doc.get("email"), "role": user_doc.get("role")},
        )
        return schemas.MFABackupCodeRotateResponse(
            message="Backup codes rotated successfully.",
            backup_codes=backup_codes,
        )
    except HTTPException:
        raise
    except PyMongoError as exc:
        _raise_auth_datastore_unavailable(exc)


@router.post("/logout", response_model=schemas.MessageResponse)
def logout(
    response: Response,
    request: Request,
):
    token = ""
    auth_header = str(request.headers.get("authorization") or "").strip()
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    if not token:
        token = (request.cookies.get(ACCESS_COOKIE_NAME) or "").strip()

    if token:
        try:
            payload = decode_access_token(token)
            sid = str(payload.get("sid") or "").strip()
            jti = str(payload.get("jti") or "").strip()
            user_id = int(payload.get("sub"))
            exp_raw = int(payload.get("exp"))
            expires_at = datetime.fromtimestamp(exp_raw, tz=timezone.utc)
            db = _mongo_db_or_503()
            if sid:
                revoke_session(db, sid=sid, reason="user_logout")
            if jti:
                revoke_access_token(
                    db,
                    jti=jti,
                    sid=sid or None,
                    user_id=user_id,
                    expires_at=expires_at,
                    reason="user_logout",
                )
        except Exception:  # noqa: BLE001
            pass

    _clear_auth_cookies(response)
    return schemas.MessageResponse(message="Logged out successfully.")


@router.get("/me", response_model=schemas.AuthUserOut)
def me(
    current_user: CurrentUser = Depends(get_current_user),
    sql_db: Session = Depends(get_db),
):
    db = _mongo_db_or_503()
    user_doc = db["auth_users"].find_one({"id": current_user.id})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid user session")
    try:
        role = models.UserRole(user_doc.get("role", models.UserRole.STUDENT.value))
    except ValueError:
        role = models.UserRole.STUDENT
    _ensure_role_profile_link(
        db,
        sql_db,
        user_doc=user_doc,
        role=role,
        email=_normalize_email(str(user_doc.get("email", ""))),
    )
    return _auth_user_out(user_doc)


@router.put("/me/alternate-email", response_model=schemas.AuthUserOut)
def update_alternate_email(
    payload: schemas.AlternateEmailUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    db = _mongo_db_or_503()
    user_doc = db["auth_users"].find_one({"id": current_user.id})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid user session")

    if not bool(user_doc.get("primary_login_verified", False)):
        raise HTTPException(
            status_code=403,
            detail="Login once with your primary email before adding alternate email.",
        )

    update_payload: dict[str, Any] = _build_alternate_email_update_fields(current_user.id, None)
    if payload.alternate_email:
        alt_email = _validate_alternate_email(payload.alternate_email)
        if alt_email == str(user_doc.get("email", "")).lower():
            raise HTTPException(status_code=400, detail="Alternate email must be different from primary email")
        alt_hash = hash_lookup_value(alt_email, purpose="alternate-email")
        conflict = db["auth_users"].find_one(
            {
                "id": {"$ne": int(current_user.id)},
                "$or": [
                    {"alternate_email_hash": alt_hash},
                    {"alternate_email": alt_email},
                ],
            },
            {"id": 1},
        )
        if conflict:
            raise HTTPException(status_code=409, detail="Alternate email already used by another account")
        update_payload = _build_alternate_email_update_fields(current_user.id, alt_email)

    db["auth_users"].update_one({"id": current_user.id}, {"$set": update_payload})

    updated = db["auth_users"].find_one({"id": current_user.id})
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")

    mirror_event(
        "auth.alternate_email_updated",
        {
            "user_id": current_user.id,
            "email": updated.get("email"),
            "alternate_email": _get_alternate_email(updated),
        },
        actor={"user_id": current_user.id, "email": updated.get("email"), "role": updated.get("role")},
    )
    return _auth_user_out(updated)


@router.post("/me/primary-email/request-otp", response_model=schemas.OTPRequestResponse)
def request_primary_email_update_otp(
    payload: schemas.PrimaryEmailUpdateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    sql_db: Session = Depends(get_db),
):
    db = _mongo_db_or_503()
    user_doc = db["auth_users"].find_one({"id": int(current_user.id)})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid user session")
    if not _primary_email_update_required(user_doc):
        raise HTTPException(status_code=400, detail="Primary email update is not required for this account.")

    new_email = _validate_new_primary_email(payload.new_email)
    old_email = _normalize_email(str(user_doc.get("email", "")))
    if new_email == old_email:
        raise HTTPException(status_code=400, detail="New primary email must be different from the current primary email.")
    _ensure_email_available_for_primary(db, sql_db, new_email=new_email, current_user_id=int(current_user.id))

    enforce_rate_limit(
        request,
        scope="auth.primary_email.request_otp",
        principal=f"{int(current_user.id)}:{new_email}",
        limit=6,
        window_seconds=300,
    )
    now = datetime.utcnow()
    cooldown_seconds = _otp_resend_cooldown_seconds()
    last_otp = db["auth_otps"].find_one(
        {"user_id": int(current_user.id), "purpose": "primary_email_update", "used_at": None},
        sort=[("created_at", -1)],
    )
    if last_otp:
        last_created = _coerce_datetime(last_otp.get("created_at"))
        if last_created:
            elapsed = (now - _to_utc_naive(last_created)).total_seconds()
            if elapsed < cooldown_seconds:
                retry_after = max(1, int(cooldown_seconds - elapsed))
                raise HTTPException(
                    status_code=429,
                    detail=f"OTP already sent. Please wait {retry_after} seconds before requesting again.",
                    headers={"Retry-After": str(retry_after)},
                )

    db["auth_otps"].update_many(
        {"user_id": int(current_user.id), "purpose": "primary_email_update", "used_at": None},
        {"$set": {"used_at": now}},
    )
    otp_code = generate_otp_code()
    otp_hash, otp_salt = hash_otp(otp_code)
    validity_minutes = otp_expiry_minutes()
    expires_at = now + timedelta(minutes=validity_minutes)
    otp_doc = {
        "id": _next_unique_id(db, collection="auth_otps", sequence_name="auth_otps"),
        "user_id": int(current_user.id),
        "purpose": "primary_email_update",
        "new_email": new_email,
        "old_email": old_email,
        "otp_hash": otp_hash,
        "otp_salt": otp_salt,
        "attempts_count": 0,
        "expires_at": expires_at,
        "used_at": None,
        "created_at": now,
    }
    db["auth_otps"].insert_one(otp_doc)

    try:
        delivery = _send_login_otp_with_timeout(new_email, otp_code)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Primary email update OTP delivery failed user_id=%s destination=%s", current_user.id, new_email)
        db["auth_otps"].update_one({"id": otp_doc["id"]}, {"$set": {"used_at": datetime.utcnow()}})
        raise HTTPException(
            status_code=503,
            detail="OTP delivery is temporarily unavailable. Please retry shortly or contact support.",
        ) from exc

    db["auth_otp_delivery"].insert_one(
        {
            "id": _next_unique_id(db, collection="auth_otp_delivery", sequence_name="auth_otp_delivery"),
            "user_id": int(current_user.id),
            "destination": new_email,
            "channel": str(delivery["channel"]),
            "status": "sent",
            "purpose": "primary_email_update",
            "created_at": datetime.utcnow(),
        }
    )
    mirror_event(
        "auth.primary_email_update_otp_requested",
        {"user_id": int(current_user.id), "old_email": old_email, "new_email": new_email, "expires_at": expires_at},
        actor={"user_id": int(current_user.id), "email": old_email, "role": user_doc.get("role")},
    )
    return schemas.OTPRequestResponse(
        message="OTP sent to your new official email.",
        expires_at=expires_at,
        delivered_to=new_email,
        cooldown_seconds=cooldown_seconds,
        validity_minutes=validity_minutes,
    )


@router.post("/me/primary-email/verify", response_model=schemas.AuthUserOut)
def verify_primary_email_update(
    payload: schemas.PrimaryEmailVerifyRequest,
    current_user: CurrentUser = Depends(get_current_user),
    sql_db: Session = Depends(get_db),
):
    db = _mongo_db_or_503()
    user_doc = db["auth_users"].find_one({"id": int(current_user.id)})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid user session")
    if not _primary_email_update_required(user_doc):
        raise HTTPException(status_code=400, detail="Primary email update is not required for this account.")

    new_email = _validate_new_primary_email(payload.new_email)
    otp_row = db["auth_otps"].find_one(
        {
            "user_id": int(current_user.id),
            "purpose": "primary_email_update",
            "new_email": new_email,
            "used_at": None,
        },
        sort=[("created_at", -1)],
    )
    now = datetime.utcnow()
    if not otp_row:
        raise HTTPException(status_code=400, detail="No active primary email OTP request found.")
    expires_at = _coerce_datetime(otp_row.get("expires_at"))
    if not expires_at or _to_utc_naive(expires_at) < now:
        db["auth_otps"].update_one({"id": otp_row["id"]}, {"$set": {"used_at": now}})
        raise HTTPException(status_code=400, detail="OTP expired")
    if int(otp_row.get("attempts_count", 0)) >= 5:
        db["auth_otps"].update_one({"id": otp_row["id"]}, {"$set": {"used_at": now}})
        raise HTTPException(status_code=400, detail="OTP attempts exceeded")
    otp_candidate = _normalize_otp_candidate(payload.otp_code)
    if not verify_otp(otp_candidate, otp_row.get("otp_hash", ""), otp_row.get("otp_salt", "")):
        db["auth_otps"].update_one({"id": otp_row["id"]}, {"$inc": {"attempts_count": 1}})
        raise HTTPException(status_code=400, detail="Invalid OTP")

    try:
        role = models.UserRole(user_doc.get("role", models.UserRole.STUDENT.value))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid user role") from exc
    consume_result = db["auth_otps"].update_one(
        {"id": otp_row["id"], "used_at": None},
        {"$set": {"used_at": now}},
    )
    if int(getattr(consume_result, "matched_count", 0)) != 1:
        raise HTTPException(status_code=400, detail="OTP already used. Request a new OTP.")

    updated = _write_primary_email_change(db, sql_db, user_doc=user_doc, role=role, new_email=new_email)
    mirror_event(
        "auth.primary_email_updated",
        {
            "user_id": int(current_user.id),
            "old_email": _normalize_email(str(user_doc.get("email", ""))),
            "new_email": new_email,
        },
        actor={"user_id": int(current_user.id), "email": new_email, "role": role.value},
    )
    return _auth_user_out(updated)
