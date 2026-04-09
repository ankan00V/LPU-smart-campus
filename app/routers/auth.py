import hashlib
import os
import re
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pymongo.errors import DuplicateKeyError, PyMongoError
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
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
    revoke_access_token,
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
from ..workers import dispatch_login_otp

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)

PASSWORD_POLICY_MESSAGE = (
    "Password must be at least 8 characters and include letters, numbers, and special characters."
)
ACCESS_COOKIE_SECURE = (os.getenv("APP_COOKIE_SECURE", "false") or "").strip().lower() in {"1", "true", "yes", "on"}
STUDENT_SECTION_PATTERN = re.compile(r"^[A-Z0-9/_-]+$")


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
        mfa_enabled=bool(doc.get("mfa_enabled", False)),
        is_active=bool(doc.get("is_active", True)),
        created_at=doc.get("created_at") or datetime.utcnow(),
        last_login_at=doc.get("last_login_at"),
    )


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
    return email.strip().lower()


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


def _validate_role_email(email: str, role: models.UserRole) -> None:
    if role in (
        models.UserRole.ADMIN,
        models.UserRole.FACULTY,
        models.UserRole.STUDENT,
        models.UserRole.OWNER,
    ):
        if not _email_suffix_allowed(email):
            suffixes = _allowed_email_suffixes()
            suffix_text = ", ".join(suffixes) if suffixes else "the configured institute domain"
            raise HTTPException(status_code=400, detail=f"Email must end with {suffix_text}")
        return

    raise HTTPException(status_code=400, detail="Only admin, faculty, student, and owner roles are allowed")


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
    value = email.strip().lower()
    if not value:
        raise HTTPException(status_code=400, detail="alternate_email cannot be empty")
    if not _email_suffix_allowed(value):
        suffixes = _allowed_email_suffixes()
        suffix_text = ", ".join(suffixes) if suffixes else "the configured institute domain"
        raise HTTPException(status_code=400, detail=f"Alternate email must end with {suffix_text}")
    return value


def _privileged_mfa_required() -> bool:
    return (os.getenv("APP_ENFORCE_PRIVILEGED_MFA", "true") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _is_privileged_role(role: models.UserRole) -> bool:
    return role in {models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.OWNER}

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
    if role == models.UserRole.FACULTY:
        aligned = align_faculty_profile_id_with_sql(db, sql_db, email=email, user_doc=user_doc)
        if aligned is not None:
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
            incoming_section = re.sub(r"\s+", "", str(payload.section or "").strip().upper())
            if not incoming_section:
                raise HTTPException(status_code=400, detail="section is required for student registration")
            if len(incoming_section) > 80 or not STUDENT_SECTION_PATTERN.fullmatch(incoming_section):
                raise HTTPException(
                    status_code=400,
                    detail="section can contain only letters, numbers, slash, hyphen, and underscore",
                )
            incoming_registration = None
            if payload.registration_number is not None and str(payload.registration_number or "").strip():
                incoming_registration = _normalize_registration_number(str(payload.registration_number))
                duplicate = (
                    sql_db.query(models.Student)
                    .filter(models.Student.registration_number == incoming_registration)
                    .first()
                )
                if duplicate and str(duplicate.email or "").strip().lower() != email:
                    raise HTTPException(status_code=409, detail="registration_number already exists")

            student = sql_db.query(models.Student).filter(models.Student.email == email).first()
            if student:
                student.name = payload.name
                student.department = payload.department
                student.semester = payload.semester
                student.parent_email = payload.parent_email
                student.section = incoming_section
                student.section_updated_at = now
                if incoming_registration:
                    existing_registration = str(student.registration_number or "").strip().upper()
                    if existing_registration and existing_registration != incoming_registration:
                        raise HTTPException(status_code=409, detail="registration_number already linked to this student")
                    if not existing_registration:
                        student.registration_number = incoming_registration
            else:
                student = models.Student(
                    name=payload.name,
                    email=email,
                    registration_number=incoming_registration,
                    parent_email=payload.parent_email,
                    section=incoming_section,
                    section_updated_at=now,
                    department=payload.department,
                    semester=payload.semester,
                )
                sql_db.add(student)
                sql_db.flush()

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
            incoming_faculty_identifier = None
            if payload.faculty_identifier is not None and str(payload.faculty_identifier or "").strip():
                incoming_faculty_identifier = _normalize_faculty_identifier(str(payload.faculty_identifier))
                duplicate = (
                    sql_db.query(models.Faculty)
                    .filter(models.Faculty.faculty_identifier == incoming_faculty_identifier)
                    .first()
                )
                if duplicate and str(duplicate.email or "").strip().lower() != email:
                    raise HTTPException(status_code=409, detail="faculty_identifier already exists")
            faculty = sql_db.query(models.Faculty).filter(models.Faculty.email == email).first()
            if faculty:
                faculty.name = payload.name
                faculty.department = payload.department
                if incoming_section:
                    faculty.section = incoming_section
                    faculty.section_updated_at = now
                if incoming_faculty_identifier:
                    existing_identifier = str(faculty.faculty_identifier or "").strip().upper()
                    if existing_identifier and existing_identifier != incoming_faculty_identifier:
                        raise HTTPException(status_code=409, detail="faculty_identifier already linked to this faculty")
                    if not existing_identifier:
                        faculty.faculty_identifier = incoming_faculty_identifier
            else:
                faculty = models.Faculty(
                    name=payload.name,
                    email=email,
                    faculty_identifier=incoming_faculty_identifier,
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
        if not user or not verify_password(payload.password, user.get("password_hash", "")):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not bool(user.get("is_active", True)):
            raise HTTPException(status_code=403, detail="User account is inactive")

        try:
            role = models.UserRole(user.get("role", models.UserRole.STUDENT.value))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid user role for OTP login") from exc
        _validate_role_email(email, role)
        user_id = _ensure_auth_user_id(db, user, sql_db)
        _ensure_role_profile_link(db, sql_db, user_doc=user, role=role, email=email)

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
            message="OTP sent successfully",
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
        _validate_role_email(email, role)
        if not bool(user.get("is_active", True)):
            raise HTTPException(status_code=403, detail="User account is inactive")
        user_id = _ensure_auth_user_id(db, user, sql_db)
        _ensure_role_profile_link(db, sql_db, user_doc=user, role=role, email=email)

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

        mfa_required = _privileged_mfa_required() and _is_privileged_role(role)
        mfa_enabled = bool(user.get("mfa_enabled", False))
        mfa_authenticated = False
        if mfa_required and mfa_enabled:
            if not _verify_and_consume_mfa_code(db, user, payload.mfa_code):
                raise HTTPException(
                    status_code=401,
                    detail="MFA code is required and must be a valid TOTP or backup code.",
                )
            mfa_authenticated = True

        consume_result = db["auth_otps"].update_one(
            {"id": otp_row["id"], "used_at": None},
            {"$set": {"used_at": now}},
        )
        if int(getattr(consume_result, "matched_count", 0)) != 1:
            raise HTTPException(status_code=400, detail="OTP already used. Request a new OTP.")

        auth_update: dict[str, Any] = {"last_login_at": now, "primary_login_verified": True}
        if mfa_authenticated:
            auth_update["mfa_last_verified_at"] = now

        db["auth_users"].update_one(
            {"id": user_id},
            {"$set": auth_update},
        )
        user["last_login_at"] = now
        user["primary_login_verified"] = True
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
        if role == models.UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Admin password reset is disabled")
        _validate_role_email(email, role)
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
            role = models.UserRole(user.get("role", models.UserRole.STUDENT.value))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid user role for password reset") from exc
        if role == models.UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Admin password reset is disabled")
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
        user = db["auth_users"].find_one({"email": email})
        if not user:
            raise HTTPException(status_code=401, detail="Invalid password reset request")
        try:
            role = models.UserRole(user.get("role", models.UserRole.STUDENT.value))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid user role for password reset") from exc
        if role == models.UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Admin password reset is disabled")
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

        db["auth_password_resets"].update_one({"id": reset_row["id"]}, {"$set": {"used_at": now}})
        db["auth_users"].update_one(
            {"id": user_id},
            {"$set": {"password_hash": hash_password(payload.new_password), "password_updated_at": now}},
        )
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
        required = _privileged_mfa_required() and _is_privileged_role(role)
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
    if current_user.role not in {models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.OWNER}:
        raise HTTPException(status_code=403, detail="MFA enrollment is reserved for privileged roles.")
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
        if role not in {models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.OWNER}:
            raise HTTPException(status_code=403, detail="MFA activation is reserved for privileged roles.")

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
