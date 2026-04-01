import hashlib
import hmac
import logging
import os
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from jwt import ExpiredSignatureError, ImmatureSignatureError, InvalidTokenError
from pymongo.errors import PyMongoError
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from . import models
from .database import SessionLocal
from .id_alignment import align_faculty_profile_id_with_sql, align_student_profile_id_with_sql
from .enterprise_controls import resolve_secret
from .identity_shield import observe_identity_session
from .mongo import get_mongo_db, invalidate_mongo_connection

ACCESS_TOKEN_MINUTES = max(5, min(30, int(os.getenv("APP_ACCESS_TOKEN_MINUTES", "15"))))
REFRESH_TOKEN_DAYS = max(1, min(60, int(os.getenv("APP_REFRESH_TOKEN_DAYS", "14"))))
ACCESS_COOKIE_NAME = (os.getenv("APP_ACCESS_COOKIE_NAME", "lpu_access_token") or "lpu_access_token").strip()
REFRESH_COOKIE_NAME = (os.getenv("APP_REFRESH_COOKIE_NAME", "lpu_refresh_token") or "lpu_refresh_token").strip()
JWT_ALGORITHM = "HS256"
REQUIRED_JWT_CLAIMS = ("sub", "role", "sid", "jti", "typ", "exp", "iat", "nbf")

bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)
_SQL_REQUEST_SYNC_TTL_SECONDS = max(30, min(3600, int(os.getenv("AUTH_SQL_SYNC_TTL_SECONDS", "900"))))
_SQL_REQUEST_SYNC_CACHE: dict[str, float] = {}
_SQL_REQUEST_SYNC_IN_PROGRESS: set[str] = set()
_SQL_REQUEST_SYNC_LOCK = threading.Lock()


@dataclass
class CurrentUser:
    id: int
    email: str
    role: models.UserRole
    student_id: int | None
    faculty_id: int | None
    alternate_email: str | None
    primary_login_verified: bool
    is_active: bool
    mfa_enabled: bool = False
    mfa_authenticated: bool = False
    session_id: str | None = None
    token_jti: str | None = None
    device_id: str | None = None
    created_at: datetime | None = None
    last_login_at: datetime | None = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _int_or_zero(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _sql_request_sync_key(*, user_id: int, role: models.UserRole, student_id: Any, faculty_id: Any) -> str:
    return f"{int(user_id)}:{role.value}:{_int_or_zero(student_id)}:{_int_or_zero(faculty_id)}"


def _prune_sql_request_sync_cache(now_monotonic: float) -> None:
    if not _SQL_REQUEST_SYNC_CACHE:
        return
    cutoff = now_monotonic - _SQL_REQUEST_SYNC_TTL_SECONDS
    stale_keys = [key for key, synced_at in _SQL_REQUEST_SYNC_CACHE.items() if synced_at < cutoff]
    for key in stale_keys:
        _SQL_REQUEST_SYNC_CACHE.pop(key, None)


def _begin_sql_request_sync(sync_key: str) -> bool:
    now_monotonic = time.monotonic()
    with _SQL_REQUEST_SYNC_LOCK:
        _prune_sql_request_sync_cache(now_monotonic)
        last_synced = _SQL_REQUEST_SYNC_CACHE.get(sync_key)
        if last_synced is not None and (now_monotonic - last_synced) < _SQL_REQUEST_SYNC_TTL_SECONDS:
            return False
        if sync_key in _SQL_REQUEST_SYNC_IN_PROGRESS:
            return False
        _SQL_REQUEST_SYNC_IN_PROGRESS.add(sync_key)
        return True


def _finish_sql_request_sync(sync_key: str, *, success: bool) -> None:
    now_monotonic = time.monotonic()
    with _SQL_REQUEST_SYNC_LOCK:
        _SQL_REQUEST_SYNC_IN_PROGRESS.discard(sync_key)
        if success:
            _SQL_REQUEST_SYNC_CACHE[sync_key] = now_monotonic
        _prune_sql_request_sync_cache(now_monotonic)


def sync_auth_user_pk_sequence(db: Session) -> None:
    bind = db.get_bind()
    if bind is None or getattr(bind.dialect, "name", "") != "postgresql":
        return
    max_id = db.query(func.max(models.AuthUser.id)).scalar()
    if max_id is None:
        db.execute(text("SELECT setval(pg_get_serial_sequence('auth_users', 'id'), 1, false)"))
        return
    db.execute(
        text("SELECT setval(pg_get_serial_sequence('auth_users', 'id'), :value, true)"),
        {"value": int(max_id)},
    )


def upsert_sql_auth_user_record(
    db: Session,
    *,
    email: str,
    password_hash: str,
    role: models.UserRole,
    student_id: int | None = None,
    faculty_id: int | None = None,
    is_active: bool = True,
    last_login_at: datetime | None = None,
    created_at: datetime | None = None,
    requested_id: int | None = None,
) -> tuple[models.AuthUser, bool]:
    email_norm = str(email or "").strip().lower()
    if not email_norm:
        raise HTTPException(status_code=500, detail="Invalid auth user email")

    desired_student_id: int | None = None
    desired_faculty_id: int | None = None
    if role == models.UserRole.STUDENT:
        desired_student_id = int(student_id) if student_id else None
    elif role == models.UserRole.FACULTY:
        desired_faculty_id = int(faculty_id) if faculty_id else None

    existing_by_email = (
        db.query(models.AuthUser)
        .filter(func.lower(models.AuthUser.email) == email_norm)
        .first()
    )
    if existing_by_email:
        changed = False
        if str(existing_by_email.email or "").strip().lower() != email_norm:
            existing_by_email.email = email_norm
            changed = True
        if existing_by_email.password_hash != password_hash:
            existing_by_email.password_hash = password_hash
            changed = True
        if existing_by_email.role != role:
            existing_by_email.role = role
            changed = True
        if existing_by_email.student_id != desired_student_id:
            existing_by_email.student_id = desired_student_id
            changed = True
        if existing_by_email.faculty_id != desired_faculty_id:
            existing_by_email.faculty_id = desired_faculty_id
            changed = True
        if existing_by_email.is_active != is_active:
            existing_by_email.is_active = is_active
            changed = True
        if last_login_at and existing_by_email.last_login_at != last_login_at:
            existing_by_email.last_login_at = last_login_at
            changed = True
        if changed:
            db.flush()
        return existing_by_email, False

    requested_numeric_id = int(requested_id) if requested_id else None
    if requested_numeric_id is not None:
        existing_by_id = db.get(models.AuthUser, requested_numeric_id)
        if existing_by_id:
            if str(existing_by_id.email or "").strip().lower() != email_norm:
                raise HTTPException(
                    status_code=409,
                    detail="Auth user id collision detected. Contact support to reconcile auth records.",
                )
            changed = False
            if existing_by_id.password_hash != password_hash:
                existing_by_id.password_hash = password_hash
                changed = True
            if existing_by_id.role != role:
                existing_by_id.role = role
                changed = True
            if existing_by_id.student_id != desired_student_id:
                existing_by_id.student_id = desired_student_id
                changed = True
            if existing_by_id.faculty_id != desired_faculty_id:
                existing_by_id.faculty_id = desired_faculty_id
                changed = True
            if existing_by_id.is_active != is_active:
                existing_by_id.is_active = is_active
                changed = True
            if last_login_at and existing_by_id.last_login_at != last_login_at:
                existing_by_id.last_login_at = last_login_at
                changed = True
            if changed:
                db.flush()
            return existing_by_id, False

    new_user = models.AuthUser(
        id=requested_numeric_id,
        email=email_norm,
        password_hash=password_hash,
        role=role,
        student_id=desired_student_id,
        faculty_id=desired_faculty_id,
        is_active=is_active,
        last_login_at=last_login_at,
        created_at=created_at or datetime.utcnow(),
    )
    db.add(new_user)
    db.flush()
    if requested_numeric_id is not None:
        sync_auth_user_pk_sequence(db)
    return new_user, True


def _is_production_env() -> bool:
    env = (os.getenv("APP_ENV", "development") or "development").strip().lower()
    return env in {"prod", "production"}


def _auth_secret() -> str:
    default = "lpu-dev-secret-change-in-production"
    secret = resolve_secret("APP_AUTH_SECRET", default="" if _is_production_env() else default)
    normalized = str(secret or "").strip()
    if _is_production_env():
        if not normalized:
            raise RuntimeError("APP_AUTH_SECRET is required in production.")
        if normalized == default:
            raise RuntimeError("APP_AUTH_SECRET cannot use development default in production.")
        return normalized
    return normalized or default


def _hash_with_salt(secret: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return digest.hex()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    return f"{salt}${_hash_with_salt(password, salt)}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, digest = stored_hash.split("$", 1)
    except ValueError:
        return False
    computed = _hash_with_salt(password, salt)
    return hmac.compare_digest(computed, digest)


def hash_otp(otp_code: str) -> tuple[str, str]:
    salt = secrets.token_hex(8)
    return _hash_with_salt(otp_code, salt), salt


def verify_otp(otp_code: str, otp_hash: str, otp_salt: str) -> bool:
    computed = _hash_with_salt(otp_code, otp_salt)
    return hmac.compare_digest(computed, otp_hash)


def _encode_signed_token(payload: dict[str, Any]) -> str:
    token = jwt.encode(payload, _auth_secret(), algorithm=JWT_ALGORITHM)
    return str(token)


def _decode_signed_token(token: str) -> dict[str, Any]:
    raw_token = str(token or "").strip()
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")
    try:
        payload = jwt.decode(
            raw_token,
            _auth_secret(),
            algorithms=[JWT_ALGORITHM],
            options={
                "require": list(REQUIRED_JWT_CLAIMS),
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
            },
        )
    except ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token expired") from exc
    except ImmatureSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token not active yet") from exc
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")
    return payload


def create_access_token(
    user: Any,
    *,
    session_id: str,
    token_jti: str | None = None,
) -> tuple[str, datetime, str]:
    now = _utc_now()
    expires_at = now + timedelta(minutes=ACCESS_TOKEN_MINUTES)

    role_value = user.role.value if hasattr(user.role, "value") else str(user.role)
    jti = token_jti or secrets.token_urlsafe(20)
    payload: dict[str, Any] = {
        "sub": str(user.id),
        "role": role_value,
        "sid": session_id,
        "jti": jti,
        "mfa": bool(getattr(user, "mfa_authenticated", False)),
        "typ": "access",
        "exp": int(expires_at.timestamp()),
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
    }
    return _encode_signed_token(payload), expires_at, jti


def decode_access_token(token: str) -> dict[str, Any]:
    payload = _decode_signed_token(token)
    if payload.get("typ") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")
    return payload


def generate_otp_code(length: int = 6) -> str:
    digits = "0123456789"
    return "".join(secrets.choice(digits) for _ in range(length))


def _request_ip(request: Request) -> str | None:
    forwarded = (request.headers.get("x-forwarded-for") or "").strip()
    if forwarded:
        first = forwarded.split(",", 1)[0].strip()
        return first or None
    if request.client and request.client.host:
        return str(request.client.host)
    return None


def _request_device_id(request: Request) -> str | None:
    explicit = (request.headers.get("x-device-id") or "").strip()
    if explicit:
        return explicit[:120]
    user_agent = (request.headers.get("user-agent") or "").strip()
    if not user_agent:
        return None
    digest = hashlib.sha256(user_agent.encode("utf-8")).hexdigest()
    return f"ua-{digest[:24]}"


def _session_active(session_doc: dict[str, Any]) -> bool:
    now = _utc_now()
    if session_doc.get("revoked_at") is not None:
        return False
    refresh_expires_at = session_doc.get("refresh_expires_at")
    if isinstance(refresh_expires_at, datetime):
        refresh_exp = refresh_expires_at
        if refresh_exp.tzinfo is None:
            refresh_exp = refresh_exp.replace(tzinfo=timezone.utc)
        return refresh_exp >= now
    return False


def _token_revoked(db, *, jti: str) -> bool:
    if not jti:
        return False
    row = db["auth_token_revocations"].find_one({"jti": jti})
    return row is not None


def revoke_access_token(
    db,
    *,
    jti: str,
    sid: str | None,
    user_id: int | None,
    expires_at: datetime,
    reason: str,
) -> None:
    if not jti:
        return
    db["auth_token_revocations"].update_one(
        {"jti": jti},
        {
            "$setOnInsert": {
                "jti": jti,
                "sid": sid,
                "user_id": int(user_id) if user_id else None,
                "token_type": "access",
                "reason": reason,
                "expires_at": expires_at,
                "created_at": _utc_now(),
            }
        },
        upsert=True,
    )


def revoke_session(
    db,
    *,
    sid: str,
    reason: str,
) -> None:
    now = _utc_now()
    db["auth_sessions"].update_one(
        {"sid": sid},
        {
            "$set": {
                "revoked_at": now,
                "revoked_reason": reason,
                "last_seen_at": now,
            }
        },
    )


def _refresh_token_expiry() -> datetime:
    return _utc_now() + timedelta(days=REFRESH_TOKEN_DAYS)


def _new_session_id() -> str:
    return secrets.token_urlsafe(24)


def _new_refresh_token(sid: str) -> str:
    return f"{sid}.{secrets.token_urlsafe(48)}"


def _parse_refresh_token(token: str) -> str:
    raw = str(token or "").strip()
    if not raw or "." not in raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    sid, _ = raw.split(".", 1)
    if not sid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    return sid


def _refresh_token_valid(token: str, token_hash: str | None, token_salt: str | None) -> bool:
    if not token_hash or not token_salt:
        return False
    return verify_otp(token, token_hash, token_salt)


def create_session_tokens(db, user: Any, *, request: Request) -> dict[str, Any]:
    session_id = _new_session_id()
    refresh_token = _new_refresh_token(session_id)
    refresh_hash, refresh_salt = hash_otp(refresh_token)
    refresh_expires_at = _refresh_token_expiry()
    access_token, access_expires_at, access_jti = create_access_token(user, session_id=session_id)

    now = _utc_now()
    device_id = _request_device_id(request)
    user_agent = (request.headers.get("user-agent") or "").strip()[:300] or None
    ip_address = _request_ip(request)
    role_value = user.role.value if hasattr(user.role, "value") else str(user.role)
    db["auth_sessions"].insert_one(
        {
            "sid": session_id,
            "user_id": int(user.id),
            "mfa_verified": bool(getattr(user, "mfa_authenticated", False)),
            "device_id": device_id,
            "user_agent": user_agent,
            "ip_address": ip_address,
            "current_refresh_hash": refresh_hash,
            "current_refresh_salt": refresh_salt,
            "previous_refresh_hash": None,
            "previous_refresh_salt": None,
            "refresh_expires_at": refresh_expires_at,
            "last_seen_at": now,
            "rotated_at": None,
            "last_access_jti": access_jti,
            "revoked_at": None,
            "revoked_reason": None,
            "created_at": now,
        }
    )
    try:
        observe_identity_session(
            db,
            user_id=int(user.id),
            email=str(getattr(user, "email", "") or "").strip() or None,
            role=role_value,
            student_id=getattr(user, "student_id", None),
            faculty_id=getattr(user, "faculty_id", None),
            device_id=device_id,
            user_agent=user_agent,
            ip_address=ip_address,
            session_id=session_id,
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "identity_session_observation_failed sid=%s user_id=%s",
            session_id,
            getattr(user, "id", None),
        )

    return {
        "sid": session_id,
        "access_token": access_token,
        "access_expires_at": access_expires_at,
        "access_jti": access_jti,
        "refresh_token": refresh_token,
        "refresh_expires_at": refresh_expires_at,
    }


def rotate_session_tokens(db, *, refresh_token: str, request: Request) -> dict[str, Any]:
    sid = _parse_refresh_token(refresh_token)
    session_doc = db["auth_sessions"].find_one({"sid": sid})
    if not session_doc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh session")
    if not _session_active(session_doc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session expired")

    if _refresh_token_valid(
        refresh_token,
        session_doc.get("current_refresh_hash"),
        session_doc.get("current_refresh_salt"),
    ):
        pass
    elif _refresh_token_valid(
        refresh_token,
        session_doc.get("previous_refresh_hash"),
        session_doc.get("previous_refresh_salt"),
    ):
        revoke_session(db, sid=sid, reason="refresh_token_reuse_detected")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token replay detected")
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_id = int(session_doc.get("user_id"))
    user_doc = db["auth_users"].find_one({"id": user_id})
    if not user_doc:
        revoke_session(db, sid=sid, reason="refresh_user_missing")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh session")
    if not bool(user_doc.get("is_active", True)):
        revoke_session(db, sid=sid, reason="refresh_user_inactive")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive")

    role = models.UserRole(user_doc.get("role", models.UserRole.STUDENT.value))
    current_user = CurrentUser(
        id=user_id,
        email=str(user_doc.get("email", "")),
        role=role,
        student_id=user_doc.get("student_id"),
        faculty_id=user_doc.get("faculty_id"),
        alternate_email=user_doc.get("alternate_email"),
        primary_login_verified=bool(user_doc.get("primary_login_verified", False)),
        is_active=bool(user_doc.get("is_active", True)),
        mfa_enabled=bool(user_doc.get("mfa_enabled", False)),
        mfa_authenticated=bool(session_doc.get("mfa_verified", False)),
        session_id=sid,
        created_at=user_doc.get("created_at"),
        last_login_at=user_doc.get("last_login_at"),
    )

    new_refresh_token = _new_refresh_token(sid)
    new_hash, new_salt = hash_otp(new_refresh_token)
    refresh_expires_at = _refresh_token_expiry()
    now = _utc_now()
    previous_access_jti = str(session_doc.get("last_access_jti") or "").strip()
    if previous_access_jti:
        revoke_access_token(
            db,
            jti=previous_access_jti,
            sid=sid,
            user_id=user_id,
            expires_at=now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
            reason="refresh_rotation",
        )

    access_token, access_expires_at, access_jti = create_access_token(current_user, session_id=sid)
    device_id = _request_device_id(request)
    user_agent = (request.headers.get("user-agent") or "").strip()[:300] or None
    ip_address = _request_ip(request)
    db["auth_sessions"].update_one(
        {"sid": sid},
        {
            "$set": {
                "previous_refresh_hash": session_doc.get("current_refresh_hash"),
                "previous_refresh_salt": session_doc.get("current_refresh_salt"),
                "current_refresh_hash": new_hash,
                "current_refresh_salt": new_salt,
                "refresh_expires_at": refresh_expires_at,
                "rotated_at": now,
                "last_seen_at": now,
                "last_access_jti": access_jti,
                "user_agent": user_agent,
                "ip_address": ip_address,
                "device_id": device_id,
            }
        },
    )
    try:
        observe_identity_session(
            db,
            user_id=user_id,
            email=str(user_doc.get("email") or "").strip() or None,
            role=role.value,
            student_id=current_user.student_id,
            faculty_id=current_user.faculty_id,
            device_id=device_id,
            user_agent=user_agent,
            ip_address=ip_address,
            session_id=sid,
        )
    except Exception:  # noqa: BLE001
        logger.exception("identity_session_observation_failed sid=%s user_id=%s", sid, user_id)

    return {
        "sid": sid,
        "user": current_user,
        "access_token": access_token,
        "access_expires_at": access_expires_at,
        "access_jti": access_jti,
        "refresh_token": new_refresh_token,
        "refresh_expires_at": refresh_expires_at,
    }


def get_refresh_token_from_request(request: Request) -> str:
    from_cookie = (request.cookies.get(REFRESH_COOKIE_NAME) or "").strip()
    if from_cookie:
        return from_cookie
    auth_header = (request.headers.get("authorization") or "").strip()
    if auth_header.lower().startswith("bearer "):
        raw = auth_header.split(" ", 1)[1].strip()
        if raw and raw.count(".") >= 1:
            return raw
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token required")


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    token = ""
    if credentials and credentials.credentials:
        token = credentials.credentials
    else:
        token = (request.cookies.get(ACCESS_COOKIE_NAME) or "").strip()

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    payload = decode_access_token(token)
    user_id_raw = payload.get("sub")
    sid = str(payload.get("sid") or "").strip()
    jti = str(payload.get("jti") or "").strip()

    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc

    if not sid or not jti:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")

    try:
        db = get_mongo_db(required=True)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    try:
        if _token_revoked(db, jti=jti):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token revoked")

        session_doc = db["auth_sessions"].find_one({"sid": sid, "user_id": user_id})
        if not session_doc or not _session_active(session_doc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user session")
        session_jti = str(session_doc.get("last_access_jti") or "").strip()
        if session_jti and session_jti != jti:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session token rotated")

        user_doc = db["auth_users"].find_one({"id": user_id})
        if not user_doc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user session")

        role_raw = user_doc.get("role")
        try:
            role = models.UserRole(role_raw)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user role") from exc

        _sync_request_user_with_sql(db, user_doc=user_doc, role=role)

        user = CurrentUser(
            id=int(user_doc["id"]),
            email=str(user_doc.get("email", "")),
            role=role,
            student_id=user_doc.get("student_id"),
            faculty_id=user_doc.get("faculty_id"),
            alternate_email=user_doc.get("alternate_email"),
            primary_login_verified=bool(user_doc.get("primary_login_verified", False)),
            is_active=bool(user_doc.get("is_active", True)),
            mfa_enabled=bool(user_doc.get("mfa_enabled", False)),
            mfa_authenticated=bool(payload.get("mfa", False) or session_doc.get("mfa_verified", False)),
            session_id=sid,
            token_jti=jti,
            device_id=session_doc.get("device_id"),
            created_at=user_doc.get("created_at"),
            last_login_at=user_doc.get("last_login_at"),
        )

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user session")

        db["auth_sessions"].update_one({"sid": sid}, {"$set": {"last_seen_at": _utc_now()}})
        return user
    except PyMongoError as exc:
        invalidate_mongo_connection(exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication datastore is temporarily unavailable. Please retry in a few seconds.",
        ) from exc


def require_roles(*roles: models.UserRole) -> Callable[[CurrentUser], CurrentUser]:
    role_values = {role.value for role in roles}

    def dependency(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role.value not in role_values:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role permissions")
        enforce_mfa = (os.getenv("APP_ENFORCE_PRIVILEGED_MFA", "true") or "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if enforce_mfa and current_user.role in {
            models.UserRole.ADMIN,
            models.UserRole.FACULTY,
            models.UserRole.OWNER,
        }:
            if not current_user.mfa_enabled:
                raise HTTPException(
                    status_code=status.HTTP_428_PRECONDITION_REQUIRED,
                    detail=(
                        "MFA enrollment is required for admin/faculty/owner accounts. "
                        "Complete /auth/mfa/enroll and /auth/mfa/activate first."
                    ),
                )
            if not current_user.mfa_authenticated:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="MFA verification is required for this action.",
                )
        return current_user

    return dependency


def _sync_request_user_with_sql(db, *, user_doc: dict[str, Any], role: models.UserRole) -> None:
    user_id = _int_or_zero(user_doc.get("id"))
    if user_id <= 0:
        return

    sync_key = _sql_request_sync_key(
        user_id=user_id,
        role=role,
        student_id=user_doc.get("student_id"),
        faculty_id=user_doc.get("faculty_id"),
    )
    if not _begin_sql_request_sync(sync_key):
        return

    success = False
    try:
        with SessionLocal() as sql_db:
            if role == models.UserRole.STUDENT:
                align_student_profile_id_with_sql(
                    db,
                    sql_db,
                    email=str(user_doc.get("email", "")),
                    user_doc=user_doc,
                )
            elif role == models.UserRole.FACULTY:
                align_faculty_profile_id_with_sql(
                    db,
                    sql_db,
                    email=str(user_doc.get("email", "")),
                    user_doc=user_doc,
                )
            _ensure_sql_auth_user(user_doc, sql_db=sql_db)
            sql_db.commit()
        success = True
    except HTTPException as exc:
        if exc.status_code < 500:
            raise
        logger.warning(
            "request_sql_sync_degraded user_id=%s role=%s detail=%s",
            user_id,
            role.value,
            exc.detail,
        )
    except Exception:
        logger.exception("request_sql_sync_failed user_id=%s role=%s", user_id, role.value)
    finally:
        _finish_sql_request_sync(sync_key, success=success)


def _ensure_sql_auth_user(user_doc: dict[str, Any], sql_db: Session | None = None) -> None:
    raw_id = user_doc.get("id")
    try:
        user_id = int(raw_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail="Invalid auth user id in session") from exc
    if user_id <= 0:
        raise HTTPException(status_code=500, detail="Invalid auth user id in session")

    email = str(user_doc.get("email") or "").strip()
    if not email:
        raise HTTPException(status_code=500, detail="Invalid auth user email in session")
    email_norm = email.lower()

    try:
        role = models.UserRole(user_doc.get("role", models.UserRole.STUDENT.value))
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="Invalid auth user role in session") from exc

    password_hash = str(user_doc.get("password_hash") or "").strip()
    if not password_hash:
        raise HTTPException(status_code=500, detail="Auth user password hash missing in session")

    student_id = user_doc.get("student_id")
    faculty_id = user_doc.get("faculty_id")
    is_active = bool(user_doc.get("is_active", True))
    created_at = user_doc.get("created_at")
    last_login_at = user_doc.get("last_login_at")

    owns_session = sql_db is None
    db = sql_db or SessionLocal()
    try:
        existing = db.get(models.AuthUser, user_id)
        if existing:
            if str(existing.email or "").strip().lower() != email_norm:
                raise HTTPException(
                    status_code=409,
                    detail="Auth user id collision detected. Contact support to reconcile auth records.",
                )
            changed = False
            if existing.role != role:
                existing.role = role
                changed = True
            if existing.password_hash != password_hash:
                existing.password_hash = password_hash
                changed = True
            if role == models.UserRole.STUDENT:
                if existing.faculty_id is not None:
                    existing.faculty_id = None
                    changed = True
                if student_id and existing.student_id != int(student_id):
                    existing.student_id = int(student_id)
                    changed = True
            elif role == models.UserRole.FACULTY:
                if existing.student_id is not None:
                    existing.student_id = None
                    changed = True
                if faculty_id and existing.faculty_id != int(faculty_id):
                    existing.faculty_id = int(faculty_id)
                    changed = True
            else:
                if existing.student_id is not None or existing.faculty_id is not None:
                    existing.student_id = None
                    existing.faculty_id = None
                    changed = True
            if existing.is_active != is_active:
                existing.is_active = is_active
                changed = True
            if last_login_at and existing.last_login_at != last_login_at:
                existing.last_login_at = last_login_at
                changed = True
            if changed:
                if owns_session:
                    db.commit()
                else:
                    db.flush()
            return

        existing_by_email = (
            db.query(models.AuthUser)
            .filter(func.lower(models.AuthUser.email) == email_norm)
            .first()
        )
        if existing_by_email:
            if int(existing_by_email.id) != user_id:
                raise HTTPException(
                    status_code=409,
                    detail="Auth user email already mapped to a different id. Contact support to reconcile.",
                )
            return

        new_user = models.AuthUser(
            id=user_id,
            email=email,
            password_hash=password_hash,
            role=role,
            student_id=int(student_id) if student_id else None,
            faculty_id=int(faculty_id) if faculty_id else None,
            is_active=is_active,
            last_login_at=last_login_at,
            created_at=created_at or datetime.utcnow(),
        )
        db.add(new_user)
        db.flush()
        sync_auth_user_pk_sequence(db)
        if owns_session:
            db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing = db.get(models.AuthUser, user_id)
        if existing and str(existing.email or "").strip().lower() == email_norm:
            return
        raise HTTPException(status_code=500, detail="Failed to sync auth user to SQL") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Authentication SQL datastore unavailable") from exc
    finally:
        if owns_session:
            db.close()
