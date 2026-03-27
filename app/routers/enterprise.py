import hashlib
import hmac
import json
import os
import subprocess
import shutil
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse
from pydantic import Field

from .. import models, schemas
from sqlalchemy.orm import Session

from ..auth_utils import (
    ACCESS_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    CurrentUser,
    create_session_tokens,
    hash_password,
    require_roles,
    upsert_sql_auth_user_record,
)
from ..database import POSTGRES_ADMIN_LIBPQ_URL, SQLALCHEMY_DATABASE_URL, get_db, postgres_libpq_url
from ..enterprise_controls import (
    compute_rpo_reference,
    decode_hs256_jwt,
    decrypt_pii,
    get_field_encryptor,
    iso_utc,
    parse_datetime_param,
    parse_saml_assertion,
    resolve_secret,
    rotate_collection_encryption,
    validate_production_secrets,
)
from ..id_alignment import bump_mongo_counter
from ..mongo import get_mongo_db, mirror_event, next_sequence
from ..performance import build_capacity_plan, get_sla_targets_ms, snapshot_sla
from ..postgres_tools import require_postgres_command
from ..validation import StrictSchemaModel

router = APIRouter(prefix="/enterprise", tags=["Enterprise Controls"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BaseModel = StrictSchemaModel


class OIDCExchangeRequest(BaseModel):
    provider: str = Field(min_length=2, max_length=40)
    id_token: str = Field(min_length=20)
    tenant: str | None = Field(default=None, max_length=80)


class SAMLACSRequest(BaseModel):
    provider: str = Field(min_length=2, max_length=40)
    assertion_b64: str = Field(min_length=20)
    assertion_signature: str | None = None
    tenant: str | None = Field(default=None, max_length=80)


class EncryptionRotateCollectionRequest(BaseModel):
    name: str
    fields: list[str]


class EncryptionRotateRequest(BaseModel):
    dry_run: bool = True
    batch_size: int = Field(default=500, ge=10, le=5000)
    collections: list[EncryptionRotateCollectionRequest] = Field(default_factory=list)


class AuditExportRequest(BaseModel):
    start_at: str | None = None
    end_at: str | None = None
    collections: list[str] = Field(default_factory=list)


class RetentionRunRequest(BaseModel):
    dry_run: bool = True
    policies_days: dict[str, int] = Field(default_factory=dict)


class DeletionRequestCreate(BaseModel):
    email: str
    mode: str = Field(default="soft", pattern="^(soft|hard)$")
    reason: str = Field(min_length=4, max_length=500)
    legal_hold: bool = False


class DeletionApprovalRequest(BaseModel):
    note: str | None = Field(default=None, max_length=600)


class DeletionLegalHoldRequest(BaseModel):
    legal_hold: bool
    reason: str | None = Field(default=None, max_length=600)


class DRBackupRequest(BaseModel):
    include_mongo: bool = True
    label: str | None = Field(default=None, max_length=80)


class DRRestoreDrillRequest(BaseModel):
    backup_id: str | None = None


class SCIMEmailEntry(BaseModel):
    value: str = Field(min_length=5, max_length=254)
    type: str | None = Field(default=None, max_length=40)
    primary: bool | None = None


class SCIMNameEntry(BaseModel):
    formatted: str | None = Field(default=None, max_length=120)
    givenName: str | None = Field(default=None, max_length=80)
    familyName: str | None = Field(default=None, max_length=80)


class SCIMCreateRequest(BaseModel):
    schemas: list[str] = Field(default_factory=list, max_length=8)
    userName: str | None = Field(default=None, min_length=5, max_length=254)
    emails: list[SCIMEmailEntry] = Field(default_factory=list, max_length=8)
    name: SCIMNameEntry | None = None
    displayName: str | None = Field(default=None, max_length=120)
    active: bool = True
    externalId: str | None = Field(default=None, max_length=120)
    groups: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    roles: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    userType: str | None = Field(default=None, max_length=40)


class SCIMPatchOperation(BaseModel):
    op: str = Field(min_length=3, max_length=20)
    path: str | None = Field(default=None, max_length=120)
    value: Any = None


class SCIMPatchRequest(BaseModel):
    Operations: list[SCIMPatchOperation] = Field(default_factory=list, max_length=100)


class EvidencePackageRequest(BaseModel):
    start_at: str | None = None
    end_at: str | None = None
    collections: list[str] = Field(default_factory=list)
    label: str | None = Field(default=None, max_length=80)


def _mongo_or_503():
    try:
        return get_mongo_db(required=True)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _cookie_secure() -> bool:
    return (os.getenv("APP_COOKIE_SECURE", "false") or "").strip().lower() in {"1", "true", "yes", "on"}


def _is_production_env() -> bool:
    env = (os.getenv("APP_ENV", "development") or "development").strip().lower()
    return env in {"prod", "production"}


def _to_utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


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
        secure=_cookie_secure(),
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
        secure=_cookie_secure(),
        path="/",
    )


def _normalize_email(value: str) -> str:
    return str(value or "").strip().lower()


def _normalize_role(value: str | None) -> models.UserRole:
    raw = str(value or "").strip().lower()
    if raw in {"admin", "administrator"}:
        return models.UserRole.ADMIN
    if raw in {"faculty", "teacher", "professor"}:
        return models.UserRole.FACULTY
    if raw in {"owner"}:
        return models.UserRole.OWNER
    return models.UserRole.STUDENT


def _normalize_tenant(value: str | None) -> str | None:
    token = str(value or "").strip().lower()
    if not token:
        return None
    token = "".join(ch for ch in token if ch.isalnum() or ch in {"-", "_", "."})
    return token or None


def _json_secret_dict(secret_name: str) -> dict[str, Any]:
    raw = (resolve_secret(secret_name, default="") or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if isinstance(parsed, dict):
        return parsed
    return {}


def _provider_tenant_allow_map() -> dict[str, set[str]]:
    raw = _json_secret_dict("SSO_PROVIDER_TENANTS_JSON")
    out: dict[str, set[str]] = {}
    for provider, tenants in raw.items():
        if not isinstance(tenants, list):
            continue
        provider_key = str(provider or "").strip().upper()
        normalized_tenants = {
            str(item or "").strip().lower()
            for item in tenants
            if str(item or "").strip()
        }
        if provider_key and normalized_tenants:
            out[provider_key] = normalized_tenants
    return out


def _tenant_domain_allow_map() -> dict[str, set[str]]:
    raw = _json_secret_dict("SSO_TENANT_ALLOWED_DOMAINS_JSON")
    out: dict[str, set[str]] = {}
    for tenant, domains in raw.items():
        if not isinstance(domains, list):
            continue
        tenant_key = str(tenant or "").strip().lower()
        normalized_domains = {
            str(item or "").strip().lower()
            for item in domains
            if str(item or "").strip()
        }
        if tenant_key and normalized_domains:
            out[tenant_key] = normalized_domains
    return out


def _enforce_sso_tenant_constraints(
    *,
    provider: str,
    tenant: str | None,
    email: str,
) -> str | None:
    normalized_tenant = _normalize_tenant(tenant)
    provider_tenants = _provider_tenant_allow_map().get(provider.strip().upper())
    if provider_tenants:
        if not normalized_tenant:
            raise HTTPException(status_code=400, detail="tenant is required for this SSO provider")
        if normalized_tenant not in provider_tenants:
            raise HTTPException(status_code=403, detail="tenant is not allowed for this SSO provider")

    if normalized_tenant:
        domains = _tenant_domain_allow_map().get(normalized_tenant)
        if domains:
            domain = email.split("@", 1)[1].lower() if "@" in email else ""
            if domain not in domains:
                raise HTTPException(
                    status_code=403,
                    detail=f"Email domain is not allowed for tenant '{normalized_tenant}'",
                )
    return normalized_tenant


def _is_privileged_role(role: models.UserRole) -> bool:
    return role in {models.UserRole.ADMIN, models.UserRole.FACULTY}


def _scim_enabled() -> bool:
    return bool((resolve_secret("SCIM_BEARER_TOKEN", default="") or "").strip())


def _scim_group_role_map() -> dict[str, models.UserRole]:
    raw = _json_secret_dict("SCIM_GROUP_ROLE_MAP_JSON")
    mapping: dict[str, models.UserRole] = {}
    for group, role_value in raw.items():
        group_key = str(group or "").strip().lower()
        if not group_key:
            continue
        mapping[group_key] = _normalize_role(str(role_value or "student"))
    return mapping


def _extract_scim_groups(payload: dict[str, Any]) -> list[str]:
    groups = payload.get("groups")
    if not isinstance(groups, list):
        return []
    tokens: list[str] = []
    for item in groups:
        if isinstance(item, dict):
            candidate = item.get("value") or item.get("display")
        else:
            candidate = item
        token = str(candidate or "").strip()
        if token:
            tokens.append(token)
    return tokens


def _scim_role_from_groups(groups: list[str]) -> models.UserRole | None:
    mapping = _scim_group_role_map()
    for group in groups:
        resolved = mapping.get(str(group or "").strip().lower())
        if resolved is not None:
            return resolved
    return None


def _scim_explicit_role(payload: dict[str, Any]) -> models.UserRole | None:
    role_value = None
    if isinstance(payload.get("roles"), list) and payload["roles"]:
        first_role = payload["roles"][0]
        if isinstance(first_role, dict):
            role_value = first_role.get("value")
        else:
            role_value = first_role
    if not role_value:
        role_value = payload.get("userType")
    role_token = str(role_value or "").strip()
    if not role_token:
        return None
    return _normalize_role(role_token)


def _require_scim_token(request: Request) -> str:
    expected = (resolve_secret("SCIM_BEARER_TOKEN", default="") or "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="SCIM is not configured")
    auth_header = (request.headers.get("authorization") or "").strip()
    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="SCIM bearer token is required")
    token = auth_header.split(" ", 1)[1].strip()
    if not token or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="Invalid SCIM bearer token")
    return token


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(val) for key, val in value.items()}
    return str(value)


def _auth_user_out(user_doc: dict[str, Any]) -> schemas.AuthUserOut:
    user_id = int(user_doc["id"])
    encrypted_alt = str(user_doc.get("alternate_email_encrypted") or "").strip()
    alternate_email = ""
    if encrypted_alt:
        alternate_email = str(decrypt_pii(encrypted_alt, aad=f"auth_users:{user_id}:alternate_email") or "").strip()
    if not alternate_email:
        alternate_email = str(user_doc.get("alternate_email") or "").strip()
    role = _normalize_role(str(user_doc.get("role") or "student"))
    return schemas.AuthUserOut(
        id=user_id,
        name=str(user_doc.get("name") or "").strip() or None,
        email=str(user_doc.get("email") or ""),
        role=role,
        student_id=user_doc.get("student_id"),
        faculty_id=user_doc.get("faculty_id"),
        alternate_email=alternate_email or None,
        primary_login_verified=bool(user_doc.get("primary_login_verified", False)),
        mfa_enabled=bool(user_doc.get("mfa_enabled", False)),
        is_active=bool(user_doc.get("is_active", True)),
        created_at=user_doc.get("created_at") or datetime.utcnow(),
        last_login_at=user_doc.get("last_login_at"),
    )


def _scim_resource(user_doc: dict[str, Any]) -> dict[str, Any]:
    groups = [str(item) for item in (user_doc.get("scim_groups") or []) if str(item).strip()]
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "id": str(user_doc["id"]),
        "externalId": user_doc.get("scim_external_id"),
        "userName": user_doc.get("email"),
        "active": bool(user_doc.get("is_active", True)),
        "name": {"formatted": str(user_doc.get("name") or "").strip() or None},
        "emails": [{"value": user_doc.get("email"), "primary": True}],
        "roles": [{"value": user_doc.get("role")}],
        "groups": [{"value": group} for group in groups],
        "meta": {
            "resourceType": "User",
            "lastModified": iso_utc(user_doc.get("updated_at") or user_doc.get("created_at")),
        },
    }


def _default_retention_policies() -> dict[str, int]:
    defaults: dict[str, int] = {
        "auth_otps": 30,
        "auth_otp_delivery": 30,
        "auth_password_resets": 30,
        "event_stream": 365,
        "admin_audit_logs": 365,
        "food_order_audit": 365,
        "compliance_deletion_requests": 730,
    }
    raw = (resolve_secret("APP_RETENTION_POLICIES_DAYS_JSON", default="") or "").strip()
    if not raw:
        return defaults
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return defaults
    if not isinstance(parsed, dict):
        return defaults
    merged = dict(defaults)
    for key, value in parsed.items():
        try:
            merged[str(key)] = max(1, int(value))
        except (TypeError, ValueError):
            continue
    return merged


def _default_audit_collections() -> list[str]:
    return [
        "event_stream",
        "admin_audit_logs",
        "auth_users",
        "auth_sessions",
        "auth_token_revocations",
        "auth_otps",
        "auth_otp_delivery",
        "food_order_audit",
        "compliance_deletion_requests",
        "compliance_retention_runs",
        "compliance_evidence_packages",
        "security_key_rotation_runs",
        "dr_restore_drills",
        "dr_backups",
    ]


def _safe_label(value: str | None, *, max_len: int = 40) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    return "".join(ch for ch in raw if ch.isalnum() or ch in {"-", "_"}).strip("-_")[:max_len]


def _write_audit_zip_bundle(
    db,
    *,
    archive_path: Path,
    start_dt: datetime | None,
    end_dt: datetime | None,
    collections: list[str],
    max_docs: int,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "generated_at": datetime.utcnow().isoformat(),
        "collections": {},
        "window": {"start_at": iso_utc(start_dt), "end_at": iso_utc(end_dt)},
    }
    if metadata:
        manifest["metadata"] = _jsonable(metadata)

    with ZipFile(archive_path, mode="w", compression=ZIP_DEFLATED) as zf:
        for collection_name in collections:
            query: dict[str, Any] = {}
            if start_dt or end_dt:
                created_filter: dict[str, Any] = {}
                if start_dt:
                    created_filter["$gte"] = start_dt
                if end_dt:
                    created_filter["$lte"] = end_dt
                query["created_at"] = created_filter

            docs = list(db[collection_name].find(query).sort("created_at", 1).limit(max_docs))
            json_lines: list[str] = []
            for doc in docs:
                normalized = _jsonable(doc)
                json_lines.append(json.dumps(normalized, separators=(",", ":")))
            body = ("\n".join(json_lines)).encode("utf-8")
            filename = f"{collection_name}.jsonl"
            zf.writestr(filename, body)
            manifest["collections"][collection_name] = {
                "count": len(docs),
                "sha256": hashlib.sha256(body).hexdigest(),
                "truncated": len(docs) >= max_docs,
            }

        manifest_bytes = json.dumps(_jsonable(manifest), indent=2, sort_keys=True).encode("utf-8")
        zf.writestr("manifest.json", manifest_bytes)
    return manifest


def _deletion_dual_control_required() -> bool:
    return (os.getenv("APP_DELETION_DUAL_CONTROL_REQUIRED", "true") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _upsert_federated_user(
    db,
    sql_db: Session,
    *,
    email: str,
    name: str | None,
    role: models.UserRole,
    provider: str,
    tenant: str | None,
    subject: str,
    idp_mfa_verified: bool,
) -> dict[str, Any]:
    now = datetime.utcnow()
    existing = db["auth_users"].find_one({"email": email})
    if existing:
        sql_auth_user, _ = upsert_sql_auth_user_record(
            sql_db,
            email=email,
            password_hash=str(existing.get("password_hash") or hash_password(secrets_token_placeholder())),
            role=role,
            student_id=existing.get("student_id"),
            faculty_id=existing.get("faculty_id"),
            is_active=True,
            last_login_at=now,
            created_at=existing.get("created_at"),
            requested_id=int(existing.get("id")) if existing.get("id") else None,
        )
        update = {
            "id": int(sql_auth_user.id),
            "name": name or existing.get("name"),
            "role": role.value,
            "password_hash": str(sql_auth_user.password_hash),
            "sso_provider": provider,
            "sso_tenant": tenant,
            "sso_subject": subject,
            "primary_login_verified": True,
            "is_active": True,
            "last_login_at": now,
            "updated_at": now,
        }
        if _is_privileged_role(role) and idp_mfa_verified:
            update["mfa_enabled"] = True
            update["mfa_source"] = "idp"
            update["mfa_last_verified_at"] = now
        db["auth_users"].update_one({"email": email}, {"$set": update})
        updated = db["auth_users"].find_one({"id": int(sql_auth_user.id)}) or db["auth_users"].find_one({"email": email})
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update federated user")
        sql_db.commit()
        return updated

    password_hash = hash_password(secrets_token_placeholder())
    sql_auth_user, _ = upsert_sql_auth_user_record(
        sql_db,
        email=email,
        password_hash=password_hash,
        role=role,
        student_id=None,
        faculty_id=None,
        is_active=True,
        last_login_at=now,
        created_at=now,
    )
    new_user = {
        "id": int(sql_auth_user.id),
        "name": name or email.split("@", 1)[0],
        "email": email,
        "password_hash": password_hash,
        "role": role.value,
        "student_id": None,
        "faculty_id": None,
        "alternate_email": None,
        "alternate_email_encrypted": None,
        "alternate_email_hash": None,
        "primary_login_verified": True,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
        "last_login_at": now,
        "sso_provider": provider,
        "sso_tenant": tenant,
        "sso_subject": subject,
        "mfa_enabled": bool(idp_mfa_verified and _is_privileged_role(role)),
        "mfa_source": "idp" if idp_mfa_verified and _is_privileged_role(role) else "local",
        "mfa_last_verified_at": now if idp_mfa_verified and _is_privileged_role(role) else None,
        "mfa_totp_secret": None,
        "mfa_backup_code_hashes": [],
        "mfa_enrolled_at": None,
        "mfa_setup_secret": None,
        "mfa_setup_backup_code_hashes": [],
        "mfa_setup_expires_at": None,
    }
    db["auth_users"].insert_one(new_user)
    bump_mongo_counter(db, "auth_users", int(sql_auth_user.id))
    sql_db.commit()
    return new_user


def secrets_token_placeholder() -> str:
    return f"SSO::{os.urandom(8).hex()}::{datetime.utcnow().timestamp()}"


def _issue_session_response(
    response: Response,
    *,
    db,
    user_doc: dict[str, Any],
    mfa_authenticated: bool,
    request: Request,
) -> schemas.TokenResponse:
    user_out = _auth_user_out(user_doc)
    principal = CurrentUser(
        id=int(user_doc["id"]),
        email=str(user_doc.get("email") or ""),
        role=_normalize_role(str(user_doc.get("role") or "student")),
        student_id=user_doc.get("student_id"),
        faculty_id=user_doc.get("faculty_id"),
        alternate_email=user_out.alternate_email,
        primary_login_verified=bool(user_doc.get("primary_login_verified", False)),
        is_active=bool(user_doc.get("is_active", True)),
        mfa_enabled=bool(user_doc.get("mfa_enabled", False)),
        mfa_authenticated=bool(mfa_authenticated),
        created_at=user_doc.get("created_at"),
        last_login_at=user_doc.get("last_login_at"),
    )
    session_tokens = create_session_tokens(db, principal, request=request)
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
        user=user_out,
    )


@router.get("/controls/status")
def enterprise_controls_status(
    _: CurrentUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    encryptor = get_field_encryptor()
    return {
        "mfa_enforced_for_admin_faculty": (os.getenv("APP_ENFORCE_PRIVILEGED_MFA", "true") or "").strip().lower()
        in {"1", "true", "yes", "on"},
        "secrets_provider": (os.getenv("APP_SECRETS_PROVIDER", "env") or "env").strip().lower(),
        "scim_enabled": _scim_enabled(),
        "scim_group_role_map": {key: value.value for key, value in _scim_group_role_map().items()},
        "sso_provider_tenant_constraints": {
            provider: sorted(list(tenants)) for provider, tenants in _provider_tenant_allow_map().items()
        },
        "sso_tenant_domain_allowlist": {
            tenant: sorted(list(domains)) for tenant, domains in _tenant_domain_allow_map().items()
        },
        "field_encryption_active_key_id": encryptor.active_key_id,
        "field_encryption_key_ids": sorted(list(encryptor.keyring.keys())),
        "default_retention_policies_days": _default_retention_policies(),
        "deletion_dual_control_required": _deletion_dual_control_required(),
        "sla_targets_ms": get_sla_targets_ms(),
    }


@router.post("/sso/oidc/exchange", response_model=schemas.TokenResponse)
def oidc_exchange(
    payload: OIDCExchangeRequest,
    response: Response,
    request: Request,
    sql_db: Session = Depends(get_db),
):
    db = _mongo_or_503()
    provider = payload.provider.strip().upper()
    secret = (resolve_secret(f"SSO_OIDC_{provider}_HS256_SECRET", default="") or "").strip()
    if not secret:
        raise HTTPException(status_code=400, detail=f"OIDC provider {payload.provider} is not configured")
    issuer = (resolve_secret(f"SSO_OIDC_{provider}_ISSUER", default="") or "").strip() or None
    audience = (resolve_secret(f"SSO_OIDC_{provider}_AUDIENCE", default="") or "").strip() or None
    if _is_production_env() and (not issuer or not audience):
        raise HTTPException(
            status_code=400,
            detail=f"OIDC provider {payload.provider} is missing issuer/audience configuration",
        )
    try:
        claims = decode_hs256_jwt(
            payload.id_token,
            secret=secret,
            expected_issuer=issuer,
            expected_audience=audience,
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid OIDC token: {exc}") from exc

    email = _normalize_email(str(claims.get("email") or claims.get("upn") or ""))
    if not email:
        raise HTTPException(status_code=400, detail="OIDC token is missing email claim")
    tenant = _enforce_sso_tenant_constraints(
        provider=provider,
        tenant=payload.tenant,
        email=email,
    )
    subject = str(claims.get("sub") or "").strip()
    if not subject:
        raise HTTPException(status_code=400, detail="OIDC token is missing subject")

    role = _normalize_role(str(claims.get("role") or claims.get("userType") or "student"))
    amr = claims.get("amr") if isinstance(claims.get("amr"), list) else []
    amr_values = {str(item).lower() for item in amr}
    idp_mfa_verified = bool(amr_values & {"mfa", "otp", "totp", "pwd+mfa"})
    if _is_privileged_role(role) and not idp_mfa_verified:
        raise HTTPException(status_code=401, detail="OIDC assertion for privileged role must include MFA evidence")

    user_doc = _upsert_federated_user(
        db,
        sql_db,
        email=email,
        name=str(claims.get("name") or "").strip() or None,
        role=role,
        provider=f"oidc:{payload.provider}",
        tenant=tenant,
        subject=subject,
        idp_mfa_verified=idp_mfa_verified,
    )
    token = _issue_session_response(
        response,
        db=db,
        user_doc=user_doc,
        mfa_authenticated=idp_mfa_verified,
        request=request,
    )

    mirror_event(
        "auth.sso.oidc.login",
        {
            "provider": payload.provider,
            "user_id": int(user_doc["id"]),
            "email": email,
            "role": role.value,
            "tenant": tenant,
            "idp_mfa_verified": idp_mfa_verified,
        },
        actor={"user_id": int(user_doc["id"]), "email": email, "role": role.value},
    )
    return token


@router.post("/sso/saml/acs", response_model=schemas.TokenResponse)
def saml_acs(
    payload: SAMLACSRequest,
    response: Response,
    request: Request,
    sql_db: Session = Depends(get_db),
):
    db = _mongo_or_503()
    provider = payload.provider.strip().upper()
    signing_secret = (resolve_secret(f"SSO_SAML_{provider}_SIGNING_SECRET", default="") or "").strip()
    if not signing_secret:
        raise HTTPException(status_code=400, detail=f"SAML provider {payload.provider} is not configured")

    expected_signature = hmac.new(
        signing_secret.encode("utf-8"),
        payload.assertion_b64.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    provided_signature = (payload.assertion_signature or "").strip().lower()
    if not provided_signature:
        raise HTTPException(status_code=401, detail="SAML assertion signature is required")
    if not hmac.compare_digest(provided_signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid SAML assertion signature")

    try:
        parsed = parse_saml_assertion(payload.assertion_b64)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    attrs = {str(k).lower(): v for k, v in (parsed.get("attributes") or {}).items()}
    email = _normalize_email(
        (attrs.get("email", [None])[0])
        or (attrs.get("mail", [None])[0])
        or (attrs.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress", [None])[0])
        or parsed.get("name_id")
    )
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="SAML assertion is missing valid email")
    tenant = _enforce_sso_tenant_constraints(
        provider=provider,
        tenant=payload.tenant,
        email=email,
    )
    subject = str(parsed.get("name_id") or "").strip() or email
    role_raw = (attrs.get("role", [None])[0]) or (attrs.get("usertype", [None])[0]) or "student"
    role = _normalize_role(role_raw)
    amr_values = {str(item).lower() for item in attrs.get("amr", [])}
    idp_mfa_verified = bool(amr_values & {"mfa", "otp", "totp", "pwd+mfa"})
    if _is_privileged_role(role) and not idp_mfa_verified:
        raise HTTPException(status_code=401, detail="SAML assertion for privileged role must include MFA evidence")

    name = (attrs.get("displayname", [None])[0]) or (attrs.get("name", [None])[0])
    user_doc = _upsert_federated_user(
        db,
        sql_db,
        email=email,
        name=str(name).strip() if name else None,
        role=role,
        provider=f"saml:{payload.provider}",
        tenant=tenant,
        subject=subject,
        idp_mfa_verified=idp_mfa_verified,
    )
    token = _issue_session_response(
        response,
        db=db,
        user_doc=user_doc,
        mfa_authenticated=idp_mfa_verified,
        request=request,
    )
    mirror_event(
        "auth.sso.saml.login",
        {
            "provider": payload.provider,
            "user_id": int(user_doc["id"]),
            "email": email,
            "role": role.value,
            "tenant": tenant,
            "idp_mfa_verified": idp_mfa_verified,
        },
        actor={"user_id": int(user_doc["id"]), "email": email, "role": role.value},
    )
    return token


@router.get("/scim/v2/Users")
def scim_list_users(
    request: Request,
    startIndex: int = Query(default=1, ge=1, le=1_000_000),
    count: int = Query(default=100, ge=1, le=500),
):
    _require_scim_token(request)
    db = _mongo_or_503()
    start = max(1, int(startIndex))
    limit = max(1, min(500, int(count)))
    skip = start - 1
    query = {"scim_managed": True}
    total = db["auth_users"].count_documents(query)
    rows = list(db["auth_users"].find(query).sort("id", 1).skip(skip).limit(limit))
    resources = [_scim_resource(row) for row in rows]
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": int(total),
        "startIndex": start,
        "itemsPerPage": len(resources),
        "Resources": resources,
    }


@router.post("/scim/v2/Users", status_code=201)
def scim_create_user(
    payload: SCIMCreateRequest,
    request: Request,
    sql_db: Session = Depends(get_db),
):
    _require_scim_token(request)
    db = _mongo_or_503()
    payload_data = payload.model_dump(mode="python")
    email = _normalize_email(
        str(payload_data.get("userName") or "")
        or str((payload_data.get("emails") or [{}])[0].get("value") or "")
    )
    if not email:
        raise HTTPException(status_code=400, detail="SCIM userName/email is required")

    scim_groups = _extract_scim_groups(payload_data)
    explicit_role = _scim_explicit_role(payload_data)
    mapped_role = _scim_role_from_groups(scim_groups)
    role = explicit_role or mapped_role or models.UserRole.STUDENT
    name = None
    if isinstance(payload_data.get("name"), dict):
        name = payload_data["name"].get("formatted") or payload_data["name"].get("givenName")
    name = str(name or payload_data.get("displayName") or "").strip() or None
    active = bool(payload_data.get("active", True))
    external_id = str(payload_data.get("externalId") or "").strip() or None

    user_doc = db["auth_users"].find_one({"email": email})
    now = datetime.utcnow()
    if user_doc:
        sql_auth_user, _ = upsert_sql_auth_user_record(
            sql_db,
            email=email,
            password_hash=str(user_doc.get("password_hash") or hash_password(secrets_token_placeholder())),
            role=role,
            student_id=user_doc.get("student_id"),
            faculty_id=user_doc.get("faculty_id"),
            is_active=active,
            last_login_at=user_doc.get("last_login_at"),
            created_at=user_doc.get("created_at"),
            requested_id=int(user_doc.get("id")) if user_doc.get("id") else None,
        )
        update = {
            "id": int(sql_auth_user.id),
            "name": name or user_doc.get("name"),
            "role": role.value,
            "password_hash": str(sql_auth_user.password_hash),
            "is_active": active,
            "scim_external_id": external_id,
            "scim_last_sync_at": now,
            "scim_groups": scim_groups,
            "scim_managed": True,
            "updated_at": now,
        }
        db["auth_users"].update_one({"email": email}, {"$set": update})
        user_doc = db["auth_users"].find_one({"id": int(sql_auth_user.id)}) or db["auth_users"].find_one({"email": email})
    else:
        password_hash = hash_password(secrets_token_placeholder())
        sql_auth_user, _ = upsert_sql_auth_user_record(
            sql_db,
            email=email,
            password_hash=password_hash,
            role=role,
            student_id=None,
            faculty_id=None,
            is_active=active,
            last_login_at=None,
            created_at=now,
        )
        user_doc = {
            "id": int(sql_auth_user.id),
            "name": name or email.split("@", 1)[0],
            "email": email,
            "password_hash": password_hash,
            "role": role.value,
            "student_id": None,
            "faculty_id": None,
            "alternate_email": None,
            "alternate_email_encrypted": None,
            "alternate_email_hash": None,
            "primary_login_verified": False,
            "mfa_enabled": False,
            "is_active": active,
            "created_at": now,
            "updated_at": now,
            "last_login_at": None,
            "scim_external_id": external_id,
            "scim_last_sync_at": now,
            "scim_groups": scim_groups,
            "scim_managed": True,
        }
        db["auth_users"].insert_one(user_doc)
        bump_mongo_counter(db, "auth_users", int(sql_auth_user.id))

    sql_db.commit()

    mirror_event(
        "auth.scim.user_upserted",
        {
            "user_id": int(user_doc["id"]),
            "email": user_doc.get("email"),
            "role": user_doc.get("role"),
            "active": bool(user_doc.get("is_active", True)),
            "external_id": external_id,
            "scim_groups": scim_groups,
        },
        actor={"source": "scim"},
    )
    return _scim_resource(user_doc)


@router.patch("/scim/v2/Users/{user_id}")
def scim_patch_user(
    user_id: str,
    payload: SCIMPatchRequest,
    request: Request,
):
    _require_scim_token(request)
    db = _mongo_or_503()
    try:
        numeric_id = int(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid SCIM user id") from exc
    user_doc = db["auth_users"].find_one({"id": numeric_id})
    if not user_doc:
        raise HTTPException(status_code=404, detail="SCIM user not found")

    updates: dict[str, Any] = {"scim_last_sync_at": datetime.utcnow(), "scim_managed": True}
    explicit_role: models.UserRole | None = None
    scim_groups: list[str] | None = None
    for op in payload.Operations:
        name = str(op.path or "").strip().lower()
        action = str(op.op or "").strip().lower()
        if action not in {"add", "replace"}:
            continue
        if name in {"active", "isactive"}:
            updates["is_active"] = bool(op.value)
        elif name in {"username", "email", "emails"}:
            if isinstance(op.value, str):
                updates["email"] = _normalize_email(op.value)
        elif name in {"name.formatted", "displayname", "name"}:
            updates["name"] = str(op.value or "").strip() or user_doc.get("name")
        elif name in {"roles", "role", "usertype"}:
            if isinstance(op.value, list) and op.value:
                role_value = op.value[0].get("value") if isinstance(op.value[0], dict) else op.value[0]
            else:
                role_value = op.value
            explicit_role = _normalize_role(str(role_value or "student"))
        elif name in {"groups", "group"}:
            if isinstance(op.value, list):
                scim_groups = _extract_scim_groups({"groups": op.value})
            else:
                token = str(op.value or "").strip()
                scim_groups = [token] if token else []
    if scim_groups is not None:
        updates["scim_groups"] = scim_groups
    if explicit_role is not None:
        updates["role"] = explicit_role.value
    elif scim_groups is not None:
        mapped_role = _scim_role_from_groups(scim_groups)
        if mapped_role is not None:
            updates["role"] = mapped_role.value
    db["auth_users"].update_one({"id": numeric_id}, {"$set": updates})
    updated = db["auth_users"].find_one({"id": numeric_id})
    return _scim_resource(updated)


@router.delete("/scim/v2/Users/{user_id}", status_code=204)
def scim_deprovision_user(
    user_id: str,
    request: Request,
):
    _require_scim_token(request)
    db = _mongo_or_503()
    try:
        numeric_id = int(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid SCIM user id") from exc
    now = datetime.utcnow()
    result = db["auth_users"].update_one(
        {"id": numeric_id},
        {"$set": {"is_active": False, "deprovisioned_at": now, "scim_last_sync_at": now, "scim_managed": True}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="SCIM user not found")
    mirror_event(
        "auth.scim.user_deprovisioned",
        {"user_id": numeric_id, "deprovisioned_at": now},
        actor={"source": "scim"},
    )
    return Response(status_code=204)


@router.get("/security/encryption/status")
def encryption_status(
    _: CurrentUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    encryptor = get_field_encryptor()
    return {
        "active_key_id": encryptor.active_key_id,
        "configured_key_ids": sorted(list(encryptor.keyring.keys())),
        "algorithm": "AES256_GCM",
    }


@router.post("/security/encryption/rotate")
def rotate_encryption_keys(
    payload: EncryptionRotateRequest,
    current_user: CurrentUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    db = _mongo_or_503()
    collections = payload.collections or [
        EncryptionRotateCollectionRequest(name="auth_users", fields=["alternate_email_encrypted"]),
        EncryptionRotateCollectionRequest(
            name="students",
            fields=[
                "parent_email_encrypted",
                "profile_photo_data_url_encrypted",
                "profile_face_template_json_encrypted",
                "enrollment_video_template_json_encrypted",
            ],
        ),
        EncryptionRotateCollectionRequest(name="faculty", fields=["profile_photo_data_url_encrypted"]),
    ]
    results = []
    for item in collections:
        fields = [str(field).strip() for field in item.fields if str(field).strip()]
        if not fields:
            continue
        result = rotate_collection_encryption(
            db,
            collection_name=item.name,
            field_names=fields,
            dry_run=payload.dry_run,
            batch_size=payload.batch_size,
        )
        results.append(result)

    encryptor = get_field_encryptor()
    run_doc = {
        "id": next_sequence("security_key_rotation_runs"),
        "dry_run": bool(payload.dry_run),
        "results": results,
        "active_key_id": encryptor.active_key_id,
        "triggered_by_user_id": int(current_user.id),
        "triggered_by_email": current_user.email,
        "created_at": datetime.utcnow(),
    }
    db["security_key_rotation_runs"].insert_one(run_doc)
    mirror_event(
        "security.encryption.rotation_run",
        {
            "rotation_run_id": int(run_doc["id"]),
            "dry_run": bool(payload.dry_run),
            "active_key_id": encryptor.active_key_id,
            "collections": [item.get("collection") for item in results if isinstance(item, dict)],
        },
        actor={"user_id": int(current_user.id), "email": current_user.email, "role": current_user.role.value},
    )
    return {"rotation_run_id": int(run_doc["id"]), "dry_run": payload.dry_run, "results": results}


@router.get("/security/encryption/rotation-runs")
def list_encryption_rotation_runs(
    limit: int = 30,
    _: CurrentUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    db = _mongo_or_503()
    rows = list(
        db["security_key_rotation_runs"]
        .find({})
        .sort("created_at", -1)
        .limit(max(1, min(500, int(limit))))
    )
    return [_jsonable(row) for row in rows]


@router.post("/compliance/audit-export")
def export_audit_bundle(
    payload: AuditExportRequest,
    _: CurrentUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    db = _mongo_or_503()
    start_dt = parse_datetime_param(payload.start_at)
    end_dt = parse_datetime_param(payload.end_at)
    if start_dt and end_dt and start_dt > end_dt:
        raise HTTPException(status_code=400, detail="start_at must be earlier than end_at")

    export_dir = PROJECT_ROOT / ".enterprise_exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    archive_path = export_dir / f"audit-export-{stamp}.zip"

    collections = payload.collections or _default_audit_collections()

    max_docs = max(1000, min(300_000, int((os.getenv("APP_AUDIT_EXPORT_MAX_DOCS", "100000") or "100000"))))
    _ = _write_audit_zip_bundle(
        db,
        archive_path=archive_path,
        start_dt=start_dt,
        end_dt=end_dt,
        collections=collections,
        max_docs=max_docs,
    )

    mirror_event(
        "compliance.audit_export.generated",
        {
            "archive": str(archive_path),
            "collections": collections,
            "start_at": iso_utc(start_dt),
            "end_at": iso_utc(end_dt),
        },
        actor={"source": "enterprise"},
    )
    return FileResponse(
        path=str(archive_path),
        filename=archive_path.name,
        media_type="application/zip",
    )


@router.post("/compliance/evidence/package")
def package_compliance_evidence(
    payload: EvidencePackageRequest,
    current_user: CurrentUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    db = _mongo_or_503()
    start_dt = parse_datetime_param(payload.start_at)
    end_dt = parse_datetime_param(payload.end_at)
    if start_dt and end_dt and start_dt > end_dt:
        raise HTTPException(status_code=400, detail="start_at must be earlier than end_at")

    export_dir = PROJECT_ROOT / ".enterprise_exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    label = _safe_label(payload.label, max_len=30)
    suffix = f"-{label}" if label else ""
    archive_path = export_dir / f"evidence-package-{stamp}{suffix}.zip"

    collections = payload.collections or _default_audit_collections()
    max_docs = max(1000, min(300_000, int((os.getenv("APP_AUDIT_EXPORT_MAX_DOCS", "100000") or "100000"))))
    sla_window = max(5, min(360, int((os.getenv("APP_EVIDENCE_SLA_WINDOW_MINUTES", "60") or "60"))))

    latest_backup = db["dr_backups"].find_one({}, sort=[("created_at", -1)])
    latest_restore_drill = db["dr_restore_drills"].find_one({}, sort=[("started_at", -1)])
    metadata = {
        "package_type": "soc2_iso_evidence_bundle",
        "generated_by_user_id": int(current_user.id),
        "generated_by_email": current_user.email,
        "label": label or None,
        "latest_backup_id": latest_backup.get("backup_id") if isinstance(latest_backup, dict) else None,
        "latest_restore_drill_id": latest_restore_drill.get("id") if isinstance(latest_restore_drill, dict) else None,
        "latest_restore_target_met": (
            bool(latest_restore_drill.get("target_met"))
            if isinstance(latest_restore_drill, dict)
            else None
        ),
        "sla_snapshot": snapshot_sla(window_minutes=sla_window),
    }

    manifest = _write_audit_zip_bundle(
        db,
        archive_path=archive_path,
        start_dt=start_dt,
        end_dt=end_dt,
        collections=collections,
        max_docs=max_docs,
        metadata=metadata,
    )

    package_doc = {
        "id": next_sequence("compliance_evidence_packages"),
        "archive": str(archive_path),
        "window": {"start_at": start_dt, "end_at": end_dt},
        "collections": collections,
        "manifest": manifest,
        "created_by_user_id": int(current_user.id),
        "created_by_email": current_user.email,
        "created_at": datetime.utcnow(),
    }
    db["compliance_evidence_packages"].insert_one(package_doc)
    mirror_event(
        "compliance.evidence.package_generated",
        {
            "evidence_package_id": int(package_doc["id"]),
            "archive": str(archive_path),
            "collections": collections,
            "start_at": iso_utc(start_dt),
            "end_at": iso_utc(end_dt),
        },
        actor={"user_id": int(current_user.id), "email": current_user.email, "role": current_user.role.value},
    )
    return FileResponse(
        path=str(archive_path),
        filename=archive_path.name,
        media_type="application/zip",
    )


@router.post("/compliance/retention/run")
def run_retention(
    payload: RetentionRunRequest,
    current_user: CurrentUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    db = _mongo_or_503()
    now = datetime.utcnow()
    policies = _default_retention_policies()
    for collection_name, days in payload.policies_days.items():
        policies[str(collection_name)] = max(1, int(days))

    summary: dict[str, Any] = {"dry_run": bool(payload.dry_run), "collections": {}, "executed_at": now}
    for collection_name, days in policies.items():
        cutoff = now - timedelta(days=int(days))
        query = {
            "created_at": {"$lt": cutoff},
            "$or": [
                {"legal_hold": {"$exists": False}},
                {"legal_hold": False},
            ],
        }
        count = db[collection_name].count_documents(query)
        deleted = 0
        if not payload.dry_run and count > 0:
            deleted = int(db[collection_name].delete_many(query).deleted_count)
        summary["collections"][collection_name] = {
            "retention_days": int(days),
            "eligible_records": int(count),
            "deleted_records": int(deleted),
            "cutoff": cutoff.isoformat(),
        }

    run_doc = {
        "id": next_sequence("compliance_retention_runs"),
        "executed_by_user_id": int(current_user.id),
        "dry_run": bool(payload.dry_run),
        "summary": summary,
        "created_at": now,
    }
    db["compliance_retention_runs"].insert_one(run_doc)
    mirror_event(
        "compliance.retention.run",
        {
            "run_id": int(run_doc["id"]),
            "dry_run": bool(payload.dry_run),
            "collections": list(summary["collections"].keys()),
        },
        actor={"user_id": int(current_user.id), "email": current_user.email, "role": current_user.role.value},
    )
    return run_doc


@router.post("/compliance/deletion/requests")
def create_deletion_request(
    payload: DeletionRequestCreate,
    current_user: CurrentUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    db = _mongo_or_503()
    now = datetime.utcnow()
    email = _normalize_email(payload.email)
    request_doc = {
        "id": next_sequence("compliance_deletion_requests"),
        "email": email,
        "mode": payload.mode,
        "reason": payload.reason,
        "legal_hold": bool(payload.legal_hold),
        "legal_hold_reason": "Requested with legal hold" if bool(payload.legal_hold) else None,
        "status": "pending",
        "requested_by_user_id": int(current_user.id),
        "requested_by_email": current_user.email,
        "approved_by_user_id": None,
        "approved_by_email": None,
        "approved_at": None,
        "approval_note": None,
        "created_at": now,
    }
    db["compliance_deletion_requests"].insert_one(request_doc)
    mirror_event(
        "compliance.deletion.requested",
        {
            "request_id": int(request_doc["id"]),
            "email": email,
            "mode": payload.mode,
            "legal_hold": bool(payload.legal_hold),
        },
        actor={"user_id": int(current_user.id), "email": current_user.email, "role": current_user.role.value},
    )
    return request_doc


@router.post("/compliance/deletion/requests/{request_id}/approve")
def approve_deletion_request(
    request_id: int,
    payload: DeletionApprovalRequest,
    current_user: CurrentUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    db = _mongo_or_503()
    req = db["compliance_deletion_requests"].find_one({"id": int(request_id)})
    if not req:
        raise HTTPException(status_code=404, detail="Deletion request not found")
    if str(req.get("status") or "") != "pending":
        raise HTTPException(status_code=409, detail="Deletion request is not pending approval")
    if int(req.get("requested_by_user_id") or 0) == int(current_user.id):
        raise HTTPException(status_code=409, detail="Requester cannot approve their own deletion request")

    now = datetime.utcnow()
    db["compliance_deletion_requests"].update_one(
        {"id": int(request_id), "status": "pending"},
        {
            "$set": {
                "status": "approved",
                "approved_by_user_id": int(current_user.id),
                "approved_by_email": current_user.email,
                "approved_at": now,
                "approval_note": str(payload.note or "").strip() or None,
            }
        },
    )
    updated = db["compliance_deletion_requests"].find_one({"id": int(request_id)})
    mirror_event(
        "compliance.deletion.approved",
        {
            "request_id": int(request_id),
            "email": req.get("email"),
            "mode": req.get("mode"),
            "approval_note": str(payload.note or "").strip() or None,
        },
        actor={"user_id": int(current_user.id), "email": current_user.email, "role": current_user.role.value},
    )
    return _jsonable(updated or req)


@router.post("/compliance/deletion/requests/{request_id}/legal-hold")
def update_deletion_request_legal_hold(
    request_id: int,
    payload: DeletionLegalHoldRequest,
    current_user: CurrentUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    db = _mongo_or_503()
    req = db["compliance_deletion_requests"].find_one({"id": int(request_id)})
    if not req:
        raise HTTPException(status_code=404, detail="Deletion request not found")
    if str(req.get("status") or "") == "completed":
        raise HTTPException(status_code=409, detail="Cannot modify legal hold after execution")

    now = datetime.utcnow()
    hold_reason = str(payload.reason or "").strip() or None
    if payload.legal_hold and not hold_reason:
        hold_reason = "Legal hold applied by compliance admin."

    db["compliance_deletion_requests"].update_one(
        {"id": int(request_id)},
        {
            "$set": {
                "legal_hold": bool(payload.legal_hold),
                "legal_hold_reason": hold_reason,
                "legal_hold_updated_at": now,
                "legal_hold_updated_by_user_id": int(current_user.id),
                "legal_hold_updated_by_email": current_user.email,
            }
        },
    )
    updated = db["compliance_deletion_requests"].find_one({"id": int(request_id)})
    mirror_event(
        "compliance.deletion.legal_hold_updated",
        {
            "request_id": int(request_id),
            "legal_hold": bool(payload.legal_hold),
            "reason": hold_reason,
        },
        actor={"user_id": int(current_user.id), "email": current_user.email, "role": current_user.role.value},
    )
    return _jsonable(updated or req)


@router.get("/compliance/deletion/requests")
def list_deletion_requests(
    limit: int = 100,
    _: CurrentUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    db = _mongo_or_503()
    rows = list(
        db["compliance_deletion_requests"]
        .find({})
        .sort("created_at", -1)
        .limit(max(1, min(500, int(limit))))
    )
    return [_jsonable(row) for row in rows]


@router.post("/compliance/deletion/requests/{request_id}/execute")
def execute_deletion_request(
    request_id: int,
    current_user: CurrentUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    db = _mongo_or_503()
    req = db["compliance_deletion_requests"].find_one({"id": int(request_id)})
    if not req:
        raise HTTPException(status_code=404, detail="Deletion request not found")
    status_value = str(req.get("status") or "")
    if status_value not in {"pending", "approved"}:
        raise HTTPException(status_code=409, detail="Deletion request already processed")
    if _deletion_dual_control_required():
        if status_value != "approved":
            raise HTTPException(status_code=409, detail="Deletion request must be approved before execution")
        requested_by = int(req.get("requested_by_user_id") or 0)
        approved_by = int(req.get("approved_by_user_id") or 0)
        if requested_by and requested_by == int(current_user.id):
            raise HTTPException(status_code=409, detail="Requester cannot execute their own deletion request")
        if not approved_by:
            raise HTTPException(status_code=409, detail="Deletion request is missing approval metadata")
        if approved_by == int(current_user.id):
            raise HTTPException(status_code=409, detail="Approver cannot execute the same deletion request")
    if bool(req.get("legal_hold", False)):
        raise HTTPException(status_code=409, detail="Deletion request is under legal hold")

    email = _normalize_email(str(req.get("email") or ""))
    mode = str(req.get("mode") or "soft")
    user_doc = db["auth_users"].find_one({"email": email})
    now = datetime.utcnow()

    result_summary: dict[str, Any] = {
        "request_id": int(request_id),
        "mode": mode,
        "email": email,
        "executed_at": now.isoformat(),
        "executed_by_user_id": int(current_user.id),
        "affected_user_id": None,
        "status": "completed",
        "requested_by_user_id": int(req.get("requested_by_user_id") or 0) or None,
        "approved_by_user_id": int(req.get("approved_by_user_id") or 0) or None,
    }

    if user_doc:
        user_id = int(user_doc["id"])
        result_summary["affected_user_id"] = user_id
        if mode == "hard":
            db["auth_users"].delete_one({"id": user_id})
            for collection_name, filter_key in [
                ("auth_otps", "user_id"),
                ("auth_otp_delivery", "user_id"),
                ("auth_password_resets", "user_id"),
                ("auth_sessions", "user_id"),
            ]:
                db[collection_name].delete_many({filter_key: user_id})
            db["event_stream"].update_many(
                {"actor.user_id": user_id},
                {"$set": {"actor.user_id": None, "actor.redacted": True}},
            )
            result_summary["hard_deleted"] = True
        else:
            db["auth_users"].update_one(
                {"id": user_id},
                {
                    "$set": {
                        "is_active": False,
                        "deleted_at": now,
                        "deletion_reason": req.get("reason"),
                        "deletion_requested_id": int(request_id),
                    }
                },
            )
            result_summary["hard_deleted"] = False
    else:
        result_summary["note"] = "User record not found for email."

    db["compliance_deletion_requests"].update_one(
        {"id": int(request_id)},
        {
            "$set": {
                "status": "completed",
                "executed_at": now,
                "executed_by_user_id": int(current_user.id),
                "execution_summary": result_summary,
            }
        },
    )
    mirror_event(
        "compliance.deletion.executed",
        result_summary,
        actor={"user_id": int(current_user.id), "email": current_user.email, "role": current_user.role.value},
    )
    return result_summary


def _sqlite_file() -> Path | None:
    if not SQLALCHEMY_DATABASE_URL.startswith("sqlite:///"):
        return None
    raw_path = SQLALCHEMY_DATABASE_URL[len("sqlite:///") :]
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = (PROJECT_ROOT / candidate).resolve()
    return candidate


def _is_postgres_url() -> bool:
    return SQLALCHEMY_DATABASE_URL.startswith("postgresql")


def _pg_dump_url() -> str:
    return str(POSTGRES_ADMIN_LIBPQ_URL or postgres_libpq_url(SQLALCHEMY_DATABASE_URL) or SQLALCHEMY_DATABASE_URL)


def _create_relational_backup_artifact(destination: Path, manifest: dict[str, Any]) -> None:
    sqlite_path = _sqlite_file()
    if sqlite_path and sqlite_path.exists():
        sqlite_dest = destination / sqlite_path.name
        shutil.copy2(sqlite_path, sqlite_dest)
        manifest["artifacts"]["relational:sqlite"] = {
            "backend": "sqlite",
            "path": str(sqlite_dest),
            "size_bytes": sqlite_dest.stat().st_size,
            "sha256": hashlib.sha256(sqlite_dest.read_bytes()).hexdigest(),
        }
        return

    if _is_postgres_url():
        try:
            pg_dump = require_postgres_command("pg_dump")
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        dump_path = destination / "postgres.sql"
        try:
            subprocess.run(
                [
                    pg_dump,
                    "--dbname",
                    _pg_dump_url(),
                    "--file",
                    str(dump_path),
                    "--format=plain",
                    "--no-owner",
                    "--no-privileges",
                ],
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            raise HTTPException(status_code=500, detail="PostgreSQL backup export failed") from exc

        manifest["artifacts"]["relational:postgresql"] = {
            "backend": "postgresql",
            "path": str(dump_path),
            "size_bytes": dump_path.stat().st_size,
            "sha256": hashlib.sha256(dump_path.read_bytes()).hexdigest(),
        }
        return
    raise HTTPException(status_code=500, detail="No supported relational database backend configured for DR backup")

def _run_relational_restore_drill(backup_path: Path) -> dict[str, Any]:
    sqlite_files = [p for p in backup_path.glob("*.db")]
    if sqlite_files:
        sqlite_copy = sqlite_files[0]
        temp_restore = backup_path / f".drill-{int(time.time())}-{sqlite_copy.name}"
        shutil.copy2(sqlite_copy, temp_restore)
        conn = sqlite3.connect(str(temp_restore))
        try:
            table_count = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
            return {"backend": "sqlite", "restored": True, "validated": True, "table_count": int(table_count)}
        finally:
            conn.close()
            temp_restore.unlink(missing_ok=True)

    postgres_dumps = [p for p in backup_path.glob("*.sql")]
    if postgres_dumps:
        dump_path = postgres_dumps[0]
        content = dump_path.read_text(encoding="utf-8", errors="ignore")
        has_header = "PostgreSQL database dump" in content[:4096]
        has_schema = "CREATE TABLE" in content or "COPY " in content or "INSERT INTO" in content
        return {
            "backend": "postgresql",
            "restored": False,
            "validated": bool(has_header and has_schema and dump_path.stat().st_size > 0),
            "size_bytes": dump_path.stat().st_size,
            "has_header": has_header,
            "has_schema_statements": has_schema,
        }

    return {"backend": "unknown", "restored": False, "validated": False}


def _backup_root() -> Path:
    root = PROJECT_ROOT / "backups"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _dr_backup_collections() -> list[str]:
    return [
        "auth_users",
        "auth_sessions",
        "auth_token_revocations",
        "auth_role_invites",
        "auth_otps",
        "auth_otp_delivery",
        "auth_password_resets",
        "event_stream",
        "admin_audit_logs",
        "attendance_records",
        "food_orders",
        "food_order_audit",
        "makeup_classes",
        "remedial_attendance",
        "compliance_deletion_requests",
        "compliance_retention_runs",
        "compliance_evidence_packages",
        "security_key_rotation_runs",
        "dr_restore_drills",
        "dr_backups",
        "scim_groups",
    ]


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_manifest_path(backup_path: Path, raw_path: Any) -> Path | None:
    token = str(raw_path or "").strip()
    if not token:
        return None
    candidate = Path(token)
    if candidate.is_absolute():
        if candidate.exists():
            return candidate
        direct_fallback = (backup_path / candidate.name).resolve()
        if direct_fallback.exists():
            return direct_fallback
        mongo_fallback = (backup_path / "mongo" / candidate.name).resolve()
        if mongo_fallback.exists():
            return mongo_fallback
        matches = list(backup_path.rglob(candidate.name))
        if matches:
            return matches[0]
        return candidate
    resolved = (backup_path / token).resolve()
    if resolved.exists():
        return resolved
    direct_fallback = (backup_path / Path(token).name).resolve()
    if direct_fallback.exists():
        return direct_fallback
    return resolved


def _verify_manifest_artifacts(backup_path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        return {
            "total_checked": 0,
            "verified": 0,
            "missing": 0,
            "mismatched": 0,
            "errors": ["manifest.artifacts missing or invalid"],
        }

    checked = 0
    verified = 0
    missing = 0
    mismatched = 0
    errors: list[str] = []
    for artifact_name, artifact in artifacts.items():
        if not isinstance(artifact, dict):
            continue
        expected_sha = str(artifact.get("sha256") or "").strip().lower()
        artifact_path = _resolve_manifest_path(backup_path, artifact.get("path"))
        if not expected_sha or artifact_path is None:
            continue
        checked += 1
        if not artifact_path.exists():
            missing += 1
            errors.append(f"{artifact_name}: missing artifact {artifact_path}")
            continue
        actual_sha = _sha256_file(artifact_path).lower()
        if actual_sha != expected_sha:
            mismatched += 1
            errors.append(f"{artifact_name}: checksum mismatch")
            continue
        verified += 1
    return {
        "total_checked": int(checked),
        "verified": int(verified),
        "missing": int(missing),
        "mismatched": int(mismatched),
        "errors": errors[:20],
    }


@router.post("/dr/backup")
def create_dr_backup(
    payload: DRBackupRequest,
    current_user: CurrentUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    db = _mongo_or_503()
    run_ts = datetime.utcnow()
    backup_id = run_ts.strftime("%Y%m%dT%H%M%SZ")
    if payload.label:
        clean = "".join(ch for ch in payload.label if ch.isalnum() or ch in {"-", "_"}).strip("-_")
        if clean:
            backup_id = f"{backup_id}-{clean[:40]}"

    destination = _backup_root() / backup_id
    destination.mkdir(parents=True, exist_ok=False)

    manifest: dict[str, Any] = {"backup_id": backup_id, "created_at": run_ts.isoformat(), "artifacts": {}}
    _create_relational_backup_artifact(destination, manifest)

    if payload.include_mongo:
        mongo_dir = destination / "mongo"
        mongo_dir.mkdir(parents=True, exist_ok=True)
        collections = _dr_backup_collections()
        for collection_name in collections:
            rows = list(db[collection_name].find({}))
            file_path = mongo_dir / f"{collection_name}.jsonl"
            lines = [json.dumps(_jsonable(row), separators=(",", ":")) for row in rows]
            file_path.write_text("\n".join(lines), encoding="utf-8")
            manifest["artifacts"][f"mongo:{collection_name}"] = {
                "path": str(file_path),
                "count": len(rows),
                "sha256": hashlib.sha256(file_path.read_bytes()).hexdigest(),
            }

    manifest_path = destination / "manifest.json"
    manifest_path.write_text(json.dumps(_jsonable(manifest), indent=2), encoding="utf-8")
    db["dr_backups"].insert_one(
        {
            "id": next_sequence("dr_backups"),
            "backup_id": backup_id,
            "created_by_user_id": int(current_user.id),
            "created_at": run_ts,
            "location": str(destination),
            "manifest": manifest,
        }
    )
    mirror_event(
        "dr.backup.created",
        {
            "backup_id": backup_id,
            "location": str(destination),
            "include_mongo": bool(payload.include_mongo),
            "artifact_count": len(manifest.get("artifacts") or {}),
        },
        actor={"user_id": int(current_user.id), "email": current_user.email, "role": current_user.role.value},
    )
    return {
        "backup_id": backup_id,
        "location": str(destination),
        "manifest_path": str(manifest_path),
        "rpo_reference": compute_rpo_reference(),
    }


@router.get("/dr/backups")
def list_dr_backups(
    limit: int = 30,
    _: CurrentUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    db = _mongo_or_503()
    rows = list(
        db["dr_backups"]
        .find({})
        .sort("created_at", -1)
        .limit(max(1, min(200, int(limit))))
    )
    return [_jsonable(row) for row in rows]


@router.get("/dr/restore-drills")
def list_restore_drills(
    limit: int = 30,
    _: CurrentUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    db = _mongo_or_503()
    rows = list(
        db["dr_restore_drills"]
        .find({})
        .sort("started_at", -1)
        .limit(max(1, min(200, int(limit))))
    )
    return [_jsonable(row) for row in rows]


@router.post("/dr/restore-drill")
def run_restore_drill(
    payload: DRRestoreDrillRequest,
    current_user: CurrentUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    db = _mongo_or_503()
    start = time.perf_counter()
    backup_doc = None
    if payload.backup_id:
        backup_doc = db["dr_backups"].find_one({"backup_id": payload.backup_id})
    if not backup_doc:
        backup_doc = db["dr_backups"].find_one({}, sort=[("created_at", -1)])
    if not backup_doc:
        raise HTTPException(status_code=404, detail="No backup found for restore drill")

    backup_path = Path(str(backup_doc.get("location") or ""))
    if not backup_path.exists():
        raise HTTPException(status_code=404, detail="Backup location is not available on disk")

    manifest_path = backup_path / "manifest.json"
    manifest_exists = manifest_path.exists()
    manifest: dict[str, Any] = {}
    if manifest_exists:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}
            manifest_exists = False

    relational_checks = _run_relational_restore_drill(backup_path)

    checksum_summary = _verify_manifest_artifacts(backup_path, manifest)
    manifest_integrity_ok = (
        bool(manifest_exists)
        and int(checksum_summary.get("total_checked", 0)) > 0
        and int(checksum_summary.get("missing", 0)) == 0
        and int(checksum_summary.get("mismatched", 0)) == 0
    )
    mongo_dir_exists = (backup_path / "mongo").exists()
    rto_seconds = round(time.perf_counter() - start, 3)
    target_met = bool(
        rto_seconds <= 3600
        and bool(relational_checks.get("validated") or relational_checks.get("restored"))
        and bool(manifest_integrity_ok)
    )
    result = {
        "id": next_sequence("dr_restore_drills"),
        "backup_id": backup_doc.get("backup_id"),
        "started_at": datetime.utcnow(),
        "executed_by_user_id": int(current_user.id),
        "relational_checks": relational_checks,
        "manifest_exists": bool(manifest_exists),
        "manifest_integrity": checksum_summary,
        "manifest_integrity_ok": manifest_integrity_ok,
        "mongo_artifacts_present": bool(mongo_dir_exists),
        "rto_seconds": rto_seconds,
        "target_rto_seconds": 3600,
        "target_met": target_met,
    }
    db["dr_restore_drills"].insert_one(result)
    mirror_event(
        "dr.restore_drill.completed",
        {
            "drill_id": int(result["id"]),
            "backup_id": backup_doc.get("backup_id"),
            "rto_seconds": rto_seconds,
            "target_met": target_met,
            "manifest_integrity_ok": manifest_integrity_ok,
        },
        actor={"user_id": int(current_user.id), "email": current_user.email, "role": current_user.role.value},
    )
    return _jsonable(result)


@router.get("/performance/sla")
def performance_sla(
    window_minutes: int = 15,
    _: CurrentUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    return snapshot_sla(window_minutes=window_minutes)


@router.get("/performance/capacity-plan")
def performance_capacity_plan(
    window_minutes: int = 15,
    expected_peak_rps: float | None = None,
    growth_percent: float = 30.0,
    safety_factor: float = 1.3,
    _: CurrentUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    return build_capacity_plan(
        window_minutes=window_minutes,
        expected_peak_rps=expected_peak_rps,
        growth_percent=growth_percent,
        safety_factor=safety_factor,
    )


@router.post("/secrets/validate")
def validate_secrets(
    _: CurrentUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    try:
        validate_production_secrets()
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return {"status": "ok", "message": "Secrets validation passed for current environment."}
