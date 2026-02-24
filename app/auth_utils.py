import base64
import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import models
from .mongo import get_mongo_db

AUTH_SECRET = os.getenv("APP_AUTH_SECRET", "lpu-dev-secret-change-in-production")
ACCESS_TOKEN_MINUTES = int(os.getenv("APP_ACCESS_TOKEN_MINUTES", "480"))
ACCESS_COOKIE_NAME = (os.getenv("APP_ACCESS_COOKIE_NAME", "lpu_access_token") or "lpu_access_token").strip()

bearer_scheme = HTTPBearer(auto_error=False)


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
    created_at: datetime | None = None
    last_login_at: datetime | None = None


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("utf-8")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


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


def create_access_token(user: Any) -> tuple[str, datetime]:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=ACCESS_TOKEN_MINUTES)

    role_value = user.role.value if hasattr(user.role, "value") else str(user.role)

    header = {"alg": "HS256", "typ": "JWT"}
    payload: dict[str, Any] = {
        "sub": str(user.id),
        "role": role_value,
        "exp": int(expires_at.timestamp()),
        "iat": int(now.timestamp()),
    }

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

    signature = hmac.new(AUTH_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)

    token = f"{header_b64}.{payload_b64}.{signature_b64}"
    return token, expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc

    try:
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_signature = hmac.new(AUTH_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual_signature = _b64url_decode(signature_b64)
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc

    if not hmac.compare_digest(expected_signature, actual_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")

    exp = payload.get("exp")
    if not isinstance(exp, int) or exp < int(datetime.now(timezone.utc).timestamp()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token expired")

    return payload


def generate_otp_code(length: int = 6) -> str:
    digits = "0123456789"
    return "".join(secrets.choice(digits) for _ in range(length))


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
    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc

    try:
        db = get_mongo_db(required=True)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    user_doc = db["auth_users"].find_one({"id": user_id})
    if not user_doc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user session")

    role_raw = user_doc.get("role")
    try:
        role = models.UserRole(role_raw)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user role") from exc

    user = CurrentUser(
        id=int(user_doc["id"]),
        email=str(user_doc.get("email", "")),
        role=role,
        student_id=user_doc.get("student_id"),
        faculty_id=user_doc.get("faculty_id"),
        alternate_email=user_doc.get("alternate_email"),
        primary_login_verified=bool(user_doc.get("primary_login_verified", False)),
        is_active=bool(user_doc.get("is_active", True)),
        created_at=user_doc.get("created_at"),
        last_login_at=user_doc.get("last_login_at"),
    )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user session")

    return user


def require_roles(*roles: models.UserRole) -> Callable[[CurrentUser], CurrentUser]:
    role_values = {role.value for role in roles}

    def dependency(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role.value not in role_values:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role permissions")
        return current_user

    return dependency
