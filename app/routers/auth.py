import os
import re
import secrets
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pymongo.errors import DuplicateKeyError, PyMongoError
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth_utils import (
    CurrentUser,
    create_access_token,
    generate_otp_code,
    get_current_user,
    hash_otp,
    hash_password,
    verify_otp,
    verify_password,
)
from ..database import get_db
from ..mongo import get_mongo_db, mirror_event, next_sequence
from ..otp_delivery import otp_expiry_minutes, send_login_otp

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)

GMAIL_EMAIL_SUFFIX = "@gmail.com"
ALTERNATE_EMAIL_SUFFIX = "@gmail.com"
PASSWORD_POLICY_MESSAGE = (
    "Password must be at least 8 characters and include letters, numbers, and special characters."
)
ACCESS_COOKIE_NAME = (os.getenv("APP_ACCESS_COOKIE_NAME", "lpu_access_token") or "lpu_access_token").strip()
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
    raw = os.getenv("OTP_DELIVERY_TIMEOUT_SECONDS", "12").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 12
    return max(5, min(30, value))


def _mongo_db_or_503():
    try:
        return get_mongo_db(required=True)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _ensure_auth_user_id(db, user_doc: dict) -> int:
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
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(send_login_otp, destination_email, otp_code)
        try:
            return future.result(timeout=timeout_seconds)
        except FuturesTimeoutError as exc:
            raise RuntimeError(
                f"OTP delivery timed out after {timeout_seconds} seconds. Please retry."
            ) from exc


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
        alternate_email=doc.get("alternate_email"),
        primary_login_verified=bool(doc.get("primary_login_verified", False)),
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


def _validate_role_email(email: str, role: models.UserRole) -> None:
    if role in (models.UserRole.FACULTY, models.UserRole.STUDENT, models.UserRole.OWNER):
        if not email.endswith(GMAIL_EMAIL_SUFFIX):
            raise HTTPException(status_code=400, detail=f"Email must end with {GMAIL_EMAIL_SUFFIX}")
        return

    raise HTTPException(status_code=400, detail="Only faculty, student, and owner roles are allowed")


def _upsert_mongo_by_id(db, collection: str, doc_id: int, payload: dict) -> None:
    body = dict(payload)
    body["id"] = doc_id
    db[collection].update_one({"id": doc_id}, {"$set": body}, upsert=True)


def _validate_alternate_email(email: str) -> str:
    value = email.strip().lower()
    if not value:
        raise HTTPException(status_code=400, detail="alternate_email cannot be empty")
    if not value.endswith(ALTERNATE_EMAIL_SUFFIX):
        raise HTTPException(status_code=400, detail=f"Alternate email must end with {ALTERNATE_EMAIL_SUFFIX}")
    return value


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


def _set_auth_cookie(response: Response, token: str, expires_at: datetime) -> None:
    now_utc = datetime.utcnow()
    max_age = int(max(0, (_to_utc_naive(expires_at) - now_utc).total_seconds()))
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=token,
        max_age=max_age,
        expires=max_age,
        httponly=True,
        samesite="lax",
        secure=ACCESS_COOKIE_SECURE,
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=ACCESS_COOKIE_NAME,
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
    sql_db: Session = Depends(get_db),
):
    db = _mongo_db_or_503()

    role = payload.role
    if role == models.UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="Admin role is disabled")

    email = _normalize_email(payload.email)
    _validate_role_email(email, role)
    _validate_password_strength(payload.password)

    if db["auth_users"].find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Email already exists")

    now = datetime.utcnow()
    student_id = None
    faculty_id = None

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

            student = sql_db.query(models.Student).filter(models.Student.email == email).first()
            if student:
                student.name = payload.name
                student.department = payload.department
                student.semester = payload.semester
                student.parent_email = payload.parent_email
                student.section = incoming_section
                student.section_updated_at = now
            else:
                student = models.Student(
                    name=payload.name,
                    email=email,
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
                    "profile_photo_data_url": student.profile_photo_data_url,
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
            else:
                faculty = models.Faculty(
                    name=payload.name,
                    email=email,
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
                    "profile_photo_data_url": faculty.profile_photo_data_url,
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

        user_doc = {
            "id": _next_unique_id(db, collection="auth_users", sequence_name="auth_users"),
            "name": payload.name.strip(),
            "email": email,
            "password_hash": hash_password(payload.password),
            "role": role.value,
            "student_id": student_id,
            "faculty_id": faculty_id,
            "alternate_email": None,
            "primary_login_verified": False,
            "is_active": True,
            "created_at": now,
            "last_login_at": None,
        }

        db["auth_users"].insert_one(user_doc)
        sql_db.commit()
    except DuplicateKeyError as exc:
        sql_db.rollback()
        raise HTTPException(status_code=409, detail="Email or linked profile already exists") from exc
    except HTTPException:
        sql_db.rollback()
        raise
    except Exception as exc:  # noqa: BLE001
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
        detail="Admin bootstrap is disabled. Use /auth/register with faculty or student role.",
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


@router.post("/login/request-otp", response_model=schemas.OTPRequestResponse)
def request_login_otp(
    payload: schemas.LoginOTPRequest,
    sql_db: Session = Depends(get_db),
):
    db = _mongo_db_or_503()
    try:
        email = _normalize_email(payload.email)
        user = db["auth_users"].find_one({"email": email})
        if not user or not verify_password(payload.password, user.get("password_hash", "")):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not bool(user.get("is_active", True)):
            raise HTTPException(status_code=403, detail="User account is inactive")

        try:
            role = models.UserRole(user.get("role", models.UserRole.STUDENT.value))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid user role for OTP login") from exc
        if role == models.UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Admin login is disabled")
        _validate_role_email(email, role)
        user_id = _ensure_auth_user_id(db, user)
        _ensure_role_profile_link(db, sql_db, user_doc=user, role=role, email=email)

        destination_email = user["email"]
        if payload.send_to_alternate:
            if not bool(user.get("primary_login_verified", False)):
                raise HTTPException(
                    status_code=403,
                    detail="Alternate OTP delivery is allowed only after one successful primary email login.",
                )
            alternate_email = user.get("alternate_email")
            if not alternate_email:
                raise HTTPException(status_code=400, detail="No alternate email configured on profile.")
            destination_email = _validate_alternate_email(str(alternate_email))

        now = datetime.utcnow()
        cooldown_seconds = _otp_resend_cooldown_seconds()
        last_otp = db["auth_otps"].find_one(
            {"user_id": user_id, "purpose": "login"},
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
                detail=(
                    "Failed to send OTP from server mail channel. End users do not need email passwords. "
                    f"Check OTP delivery configuration. ({exc})"
                ),
            ) from exc

        db["auth_otp_delivery"].insert_one(
            {
                "id": _next_unique_id(db, collection="auth_otp_delivery", sequence_name="auth_otp_delivery"),
                "user_id": user_id,
                "destination": destination_email,
                "channel": delivery.get("channel", "email"),
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
            otp_debug_code=delivery.get("otp_debug_code"),
            cooldown_seconds=cooldown_seconds,
            validity_minutes=validity_minutes,
        )
    except HTTPException:
        raise
    except PyMongoError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Authentication datastore is temporarily unavailable for writes. "
                "Please retry in a few seconds."
            ),
        ) from exc
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
    sql_db: Session = Depends(get_db),
):
    db = _mongo_db_or_503()
    try:
        email = _normalize_email(payload.email)
        user = db["auth_users"].find_one({"email": email})
        if not user:
            raise HTTPException(status_code=401, detail="Invalid OTP flow")

        try:
            role = models.UserRole(user.get("role", models.UserRole.STUDENT.value))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid user role for OTP login") from exc
        if role == models.UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Admin login is disabled")
        _validate_role_email(email, role)
        user_id = _ensure_auth_user_id(db, user)
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

        if not verify_otp(payload.otp_code, otp_row.get("otp_hash", ""), otp_row.get("otp_salt", "")):
            db["auth_otps"].update_one(
                {"id": otp_row["id"]},
                {"$inc": {"attempts_count": 1}},
            )
            raise HTTPException(status_code=400, detail="Invalid OTP")

        db["auth_otps"].update_one({"id": otp_row["id"]}, {"$set": {"used_at": now}})
        db["auth_users"].update_one(
            {"id": user_id},
            {"$set": {"last_login_at": now, "primary_login_verified": True}},
        )
        user["last_login_at"] = now
        user["primary_login_verified"] = True

        access_token, expires_at = create_access_token(
            CurrentUser(
                id=user_id,
                email=user["email"],
                role=models.UserRole(user["role"]),
                student_id=user.get("student_id"),
                faculty_id=user.get("faculty_id"),
                alternate_email=user.get("alternate_email"),
                primary_login_verified=bool(user.get("primary_login_verified", False)),
                is_active=bool(user.get("is_active", True)),
                created_at=user.get("created_at"),
                last_login_at=user.get("last_login_at"),
            )
        )

        mirror_event(
            "auth.login_success",
            {"user_id": user_id, "email": user["email"], "expires_at": expires_at},
            actor={"user_id": user_id, "email": user["email"], "role": user["role"]},
        )
        _set_auth_cookie(response, access_token, expires_at)

        return schemas.TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_at=expires_at,
            user=_auth_user_out(user),
        )
    except HTTPException:
        raise
    except PyMongoError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Authentication datastore is temporarily unavailable for writes. "
                "Please retry in a few seconds."
            ),
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected OTP verify failure for email=%s", payload.email)
        raise HTTPException(
            status_code=503,
            detail=(
                "Unable to verify OTP right now. Please retry in a few seconds."
            ),
        ) from exc


@router.post("/password/request-otp", response_model=schemas.OTPRequestResponse)
def request_password_reset_otp(payload: schemas.PasswordResetOTPRequest):
    db = _mongo_db_or_503()
    try:
        email = _normalize_email(payload.email)
        user = db["auth_users"].find_one({"email": email})
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
        user_id = _ensure_auth_user_id(db, user)

        student_id = user.get("student_id")
        if not student_id:
            raise HTTPException(status_code=401, detail="Invalid email or registration number")
        student = db["students"].find_one({"id": int(student_id)})
        registration_number = str(student.get("registration_number", "")).strip() if student else ""
        if not student or not registration_number:
            raise HTTPException(status_code=401, detail="Invalid email or registration number")

        provided_registration = _normalize_registration_number(payload.registration_number)
        linked_registration = _normalize_registration_number(registration_number)
        if provided_registration != linked_registration:
            raise HTTPException(status_code=401, detail="Invalid email or registration number")

        now = datetime.utcnow()
        cooldown_seconds = _otp_resend_cooldown_seconds()
        last_otp = db["auth_otps"].find_one(
            {"user_id": user_id, "purpose": "password_reset"},
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
                detail=(
                    "Failed to send OTP from server mail channel. End users do not need email passwords. "
                    f"Check OTP delivery configuration. ({exc})"
                ),
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

        return schemas.OTPRequestResponse(
            message="Password reset OTP sent successfully",
            expires_at=expires_at,
            delivered_to=email,
            otp_debug_code=delivery.get("otp_debug_code"),
            cooldown_seconds=cooldown_seconds,
            validity_minutes=validity_minutes,
        )
    except HTTPException:
        raise
    except PyMongoError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Authentication datastore is temporarily unavailable for writes. "
                "Please retry in a few seconds."
            ),
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected password-reset OTP request failure for email=%s", payload.email)
        raise HTTPException(
            status_code=503,
            detail=(
                "Unable to process password-reset OTP right now. Please retry in a few seconds."
            ),
        ) from exc


@router.post("/password/verify-otp", response_model=schemas.PasswordResetVerifyResponse)
def verify_password_reset_otp(payload: schemas.PasswordResetVerifyOTPRequest):
    db = _mongo_db_or_503()
    try:
        email = _normalize_email(payload.email)
        user = db["auth_users"].find_one({"email": email})
        if not user:
            raise HTTPException(status_code=401, detail="Invalid OTP flow")
        try:
            role = models.UserRole(user.get("role", models.UserRole.STUDENT.value))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid user role for password reset") from exc
        if role == models.UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Admin password reset is disabled")
        user_id = _ensure_auth_user_id(db, user)

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

        if not verify_otp(payload.otp_code, otp_row.get("otp_hash", ""), otp_row.get("otp_salt", "")):
            db["auth_otps"].update_one({"id": otp_row["id"]}, {"$inc": {"attempts_count": 1}})
            raise HTTPException(status_code=400, detail="Invalid OTP")

        db["auth_otps"].update_one({"id": otp_row["id"]}, {"$set": {"used_at": now}})
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
        raise HTTPException(
            status_code=503,
            detail=(
                "Authentication datastore is temporarily unavailable for writes. "
                "Please retry in a few seconds."
            ),
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected password-reset OTP verification failure for email=%s", payload.email)
        raise HTTPException(
            status_code=503,
            detail=(
                "Unable to verify password-reset OTP right now. Please retry in a few seconds."
            ),
        ) from exc


@router.post("/password/reset", response_model=schemas.MessageResponse)
def reset_password(payload: schemas.PasswordResetConfirmRequest):
    db = _mongo_db_or_503()
    try:
        email = _normalize_email(payload.email)
        user = db["auth_users"].find_one({"email": email})
        if not user:
            raise HTTPException(status_code=401, detail="Invalid password reset request")
        try:
            role = models.UserRole(user.get("role", models.UserRole.STUDENT.value))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid user role for password reset") from exc
        if role == models.UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Admin password reset is disabled")
        user_id = _ensure_auth_user_id(db, user)

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
        raise HTTPException(
            status_code=503,
            detail=(
                "Authentication datastore is temporarily unavailable for writes. "
                "Please retry in a few seconds."
            ),
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected password reset failure for email=%s", payload.email)
        raise HTTPException(
            status_code=503,
            detail=(
                "Unable to reset password right now. Please retry in a few seconds."
            ),
        ) from exc


@router.post("/logout", response_model=schemas.MessageResponse)
def logout(response: Response):
    _clear_auth_cookie(response)
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

    update_payload: dict[str, str | None] = {"alternate_email": None}
    if payload.alternate_email:
        alt_email = _validate_alternate_email(payload.alternate_email)
        if alt_email == str(user_doc.get("email", "")).lower():
            raise HTTPException(status_code=400, detail="Alternate email must be different from primary email")
        update_payload["alternate_email"] = alt_email

    try:
        db["auth_users"].update_one({"id": current_user.id}, {"$set": update_payload})
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="Alternate email already used by another account") from exc

    updated = db["auth_users"].find_one({"id": current_user.id})
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")

    mirror_event(
        "auth.alternate_email_updated",
        {
            "user_id": current_user.id,
            "email": updated.get("email"),
            "alternate_email": updated.get("alternate_email"),
        },
        actor={"user_id": current_user.id, "email": updated.get("email"), "role": updated.get("role")},
    )
    return _auth_user_out(updated)
