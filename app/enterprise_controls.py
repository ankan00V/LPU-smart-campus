import base64
import hashlib
import hmac
import io
import json
import os
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("utf-8")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def _normalize_text(value: str | None) -> str:
    return str(value or "").strip()


def _bool_env(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name, "true" if default else "false") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _is_production_env() -> bool:
    env = (_normalize_text(os.getenv("APP_ENV")) or "development").lower()
    return env in {"prod", "production"}


def _coerce_utc_dt(value: str | datetime | None) -> datetime | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = f"{raw[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _json_loads(value: str | None) -> dict[str, Any]:
    raw = _normalize_text(value)
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if isinstance(parsed, dict):
        return parsed
    return {}


def _json_or_csv_list(value: str | None) -> list[str]:
    raw = _normalize_text(value)
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    items: list[str] = []
    for line in raw.replace("\r", "\n").split("\n"):
        for part in line.split(","):
            token = str(part or "").strip()
            if token:
                items.append(token)
    return items


@lru_cache(maxsize=4)
def _load_secrets_blob(provider: str, source: str) -> dict[str, Any]:
    if provider == "file":
        path = Path(source)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    if provider == "aws_secrets_manager":
        if not source:
            return {}
        try:
            import boto3  # type: ignore
        except Exception:
            return {}
        region = _normalize_text(os.getenv("APP_AWS_REGION")) or "ap-south-1"
        try:
            client = boto3.client("secretsmanager", region_name=region)
            response = client.get_secret_value(SecretId=source)
            if "SecretString" in response:
                return _json_loads(str(response.get("SecretString")))
        except Exception:
            return {}
    return {}


def resolve_secret(name: str, default: str | None = None, *, required: bool = False) -> str | None:
    provider = (_normalize_text(os.getenv("APP_SECRETS_PROVIDER")) or "env").lower()
    if provider not in {"env", "file", "aws_secrets_manager"}:
        provider = "env"

    if provider == "env":
        resolved = os.getenv(name, default)
    elif provider == "file":
        source = _normalize_text(os.getenv("APP_SECRETS_FILE"))
        blob = _load_secrets_blob(provider, source)
        candidate = blob.get(name)
        resolved = str(candidate) if candidate is not None else default
    else:
        source = _normalize_text(os.getenv("APP_AWS_SECRET_ID"))
        blob = _load_secrets_blob(provider, source)
        candidate = blob.get(name)
        resolved = str(candidate) if candidate is not None else default

    if required and not _normalize_text(resolved):
        raise RuntimeError(f"Required secret is missing: {name}")
    return resolved


def validate_production_secrets() -> None:
    if not _is_production_env():
        return
    required = ["APP_AUTH_SECRET", "SCIM_BEARER_TOKEN", "APP_LOOKUP_HASH_SECRET"]
    weak_values = {
        "change-me",
        "changeme",
        "replace-me",
        "replace_me",
        "set-me",
        "set_me",
        "secret",
        "password",
        "token",
    }
    resolved: dict[str, str] = {}
    for name in required:
        value = _normalize_text(resolve_secret(name, required=True))
        lowered = value.lower()
        if lowered in weak_values:
            raise RuntimeError(f"{name} cannot use placeholder values in production.")
        if len(value) < 12:
            raise RuntimeError(f"{name} must be at least 12 characters in production.")
        resolved[name] = value
    auth_secret = resolved.get("APP_AUTH_SECRET", "")
    if _normalize_text(auth_secret) == "lpu-dev-secret-change-in-production":
        raise RuntimeError("APP_AUTH_SECRET must not use development default in production.")

    lookup_secret = resolved.get("APP_LOOKUP_HASH_SECRET", "")
    if _normalize_text(lookup_secret) == "lookup-hash-dev-secret":
        raise RuntimeError("APP_LOOKUP_HASH_SECRET must not use development default in production.")

    provider = (_normalize_text(os.getenv("APP_SECRETS_PROVIDER")) or "env").lower()
    if provider not in {"file", "aws_secrets_manager"}:
        raise RuntimeError("Production requires APP_SECRETS_PROVIDER to be file or aws_secrets_manager.")

    saarthi_provider = _normalize_text(os.getenv("SAARTHI_LLM_PROVIDER")).lower()
    saarthi_required = _bool_env("SAARTHI_LLM_REQUIRED", default=False)
    if saarthi_required and not saarthi_provider:
        raise RuntimeError("Production requires SAARTHI_LLM_PROVIDER when SAARTHI_LLM_REQUIRED=true.")
    if saarthi_provider:
        if saarthi_provider not in {"gemini", "openrouter"}:
            raise RuntimeError("SAARTHI_LLM_PROVIDER must be 'gemini' or 'openrouter' in production.")
        if not saarthi_required:
            raise RuntimeError("Production requires SAARTHI_LLM_REQUIRED=true when Saarthi LLM is enabled.")
        if saarthi_provider == "gemini":
            gemini_key = _normalize_text(resolve_secret("GEMINI_API_KEY", default=""))
            if gemini_key.startswith("sk-or-v1-"):
                raise RuntimeError(
                    "GEMINI_API_KEY appears to be an OpenRouter key. "
                    "Use OPENROUTER_API_KEY only as the final fallback secret."
                )
            gemini_keys = _json_or_csv_list(resolve_secret("GEMINI_API_KEYS_JSON", default=""))
            if gemini_key:
                gemini_keys.append(gemini_key)
            gemini_keys = [token for token in gemini_keys if token and not token.startswith("sk-or-v1-")]
            if not gemini_keys:
                raise RuntimeError(
                    "Production Saarthi Gemini configuration requires GEMINI_API_KEYS_JSON "
                    "or GEMINI_API_KEY in secrets."
                )
        if saarthi_provider == "openrouter":
            openrouter_key = _normalize_text(resolve_secret("OPENROUTER_API_KEY", default=""))
            if not openrouter_key:
                raise RuntimeError("Production Saarthi OpenRouter configuration requires OPENROUTER_API_KEY in secrets.")

    if not _bool_env("APP_FIELD_ENCRYPTION_REQUIRED", default=True):
        raise RuntimeError("Production requires APP_FIELD_ENCRYPTION_REQUIRED=true.")
    if not _bool_env("APP_COOKIE_SECURE", default=False):
        raise RuntimeError("Production requires APP_COOKIE_SECURE=true.")
    if not _bool_env("APP_RUNTIME_STRICT", default=True):
        raise RuntimeError("Production requires APP_RUNTIME_STRICT=true.")
    if not _bool_env("APP_MANAGED_SERVICES_REQUIRED", default=True):
        raise RuntimeError("Production requires APP_MANAGED_SERVICES_REQUIRED=true.")
    if not _bool_env("REDIS_REQUIRED", default=True):
        raise RuntimeError("Production requires REDIS_REQUIRED=true.")
    if not _bool_env("WORKER_REQUIRED", default=True):
        raise RuntimeError("Production requires WORKER_REQUIRED=true.")
    if _bool_env("WORKER_INLINE_FALLBACK_ENABLED", default=False):
        raise RuntimeError("Production requires WORKER_INLINE_FALLBACK_ENABLED=false.")
    if not _bool_env("MONGO_PERSISTENCE_REQUIRED", default=True):
        raise RuntimeError("Production requires MONGO_PERSISTENCE_REQUIRED=true.")
    if not _bool_env("MONGO_STARTUP_STRICT", default=True):
        raise RuntimeError("Production requires MONGO_STARTUP_STRICT=true.")

    get_field_encryptor.cache_clear()
    encryptor = get_field_encryptor()
    primary_keyring = _json_loads(resolve_secret("APP_FIELD_ENCRYPTION_KEYS_JSON", default="{}"))
    if str(encryptor.active_key_id or "").startswith("dev-"):
        raise RuntimeError("Production field encryption key cannot use development fallback key ids.")
    if any(str(key_id).startswith("dev-") for key_id in primary_keyring):
        raise RuntimeError("Production primary field encryption keyring cannot include development key ids.")


def hash_lookup_value(value: str, *, purpose: str) -> str:
    secret = resolve_secret("APP_LOOKUP_HASH_SECRET", default="lookup-hash-dev-secret") or "lookup-hash-dev-secret"
    message = f"{purpose}:{value}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


@dataclass
class FieldEncryptor:
    keyring: dict[str, bytes]
    active_key_id: str

    @classmethod
    def from_environment(cls) -> "FieldEncryptor":
        keyring_raw = _json_loads(resolve_secret("APP_FIELD_ENCRYPTION_KEYS_JSON", default="{}"))
        legacy_keyring_raw = _json_loads(resolve_secret("APP_FIELD_ENCRYPTION_LEGACY_KEYS_JSON", default="{}"))
        active_key_id = _normalize_text(resolve_secret("APP_FIELD_ENCRYPTION_ACTIVE_KEY_ID", default=""))

        keyring: dict[str, bytes] = {}
        for source in (keyring_raw, legacy_keyring_raw):
            for key_id, key_value in source.items():
                try:
                    decoded = base64.urlsafe_b64decode(str(key_value))
                except Exception:
                    continue
                if len(decoded) != 32:
                    continue
                keyring.setdefault(str(key_id), decoded)

        if not keyring:
            fallback = resolve_secret("APP_FIELD_ENCRYPTION_PRIMARY_KEY", default="")
            fallback_key = _normalize_text(fallback)
            if fallback_key:
                try:
                    decoded = base64.urlsafe_b64decode(fallback_key)
                    if len(decoded) == 32:
                        keyring["v1"] = decoded
                        active_key_id = active_key_id or "v1"
                except Exception:
                    pass

        if not keyring:
            if _is_production_env():
                raise RuntimeError(
                    "Field encryption keys are missing. Set APP_FIELD_ENCRYPTION_KEYS_JSON "
                    "or APP_FIELD_ENCRYPTION_PRIMARY_KEY in production."
                )
            # Lazy local-development fallback key. Production must override with managed key material.
            seed = hashlib.sha256(b"lpu-enterprise-dev-field-encryption-key").digest()
            keyring["dev-v1"] = seed
            active_key_id = active_key_id or "dev-v1"

        if active_key_id not in keyring:
            active_key_id = next(iter(keyring.keys()))

        return cls(keyring=keyring, active_key_id=active_key_id)

    def _aesgcm(self):
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "cryptography package is required for field-level encryption. "
                "Install dependency and retry."
            ) from exc
        return AESGCM

    def encrypt_text(self, value: str, *, aad: str = "") -> str:
        plaintext = _normalize_text(value)
        if not plaintext:
            return ""
        AESGCM = self._aesgcm()
        key = self.keyring[self.active_key_id]
        nonce = secrets.token_bytes(12)
        aad_bytes = aad.encode("utf-8") if aad else b""
        ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), aad_bytes)
        envelope = {
            "v": 1,
            "alg": "AES256_GCM",
            "kid": self.active_key_id,
            "nonce": base64.urlsafe_b64encode(nonce).decode("utf-8"),
            "ct": base64.urlsafe_b64encode(ciphertext).decode("utf-8"),
        }
        return json.dumps(envelope, separators=(",", ":"))

    def decrypt_text(self, value: str | None, *, aad: str = "") -> str:
        raw = _normalize_text(value)
        if not raw:
            return ""
        try:
            envelope = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        if not isinstance(envelope, dict):
            return raw
        if envelope.get("alg") != "AES256_GCM":
            return raw
        key_id = str(envelope.get("kid", ""))
        key = self.keyring.get(key_id)
        if not key:
            raise RuntimeError(f"Encryption key not found for kid={key_id}")
        nonce_raw = envelope.get("nonce")
        ct_raw = envelope.get("ct")
        if not isinstance(nonce_raw, str) or not isinstance(ct_raw, str):
            return raw
        AESGCM = self._aesgcm()
        aad_bytes = aad.encode("utf-8") if aad else b""
        nonce = base64.urlsafe_b64decode(nonce_raw)
        ciphertext = base64.urlsafe_b64decode(ct_raw)
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, aad_bytes)
        return plaintext.decode("utf-8")

    def envelope_key_id(self, value: str | None) -> str | None:
        raw = _normalize_text(value)
        if not raw:
            return None
        try:
            envelope = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(envelope, dict):
            return None
        if envelope.get("alg") != "AES256_GCM":
            return None
        key_id = envelope.get("kid")
        if isinstance(key_id, str) and key_id:
            return key_id
        return None

    def needs_rotation(self, value: str | None) -> bool:
        kid = self.envelope_key_id(value)
        if kid is None:
            return bool(_normalize_text(value))
        return kid != self.active_key_id


@lru_cache(maxsize=1)
def get_field_encryptor() -> FieldEncryptor:
    return FieldEncryptor.from_environment()


def field_encryption_key_status() -> dict[str, Any]:
    primary = sorted(
        [
            str(key_id).strip()
            for key_id in _json_loads(resolve_secret("APP_FIELD_ENCRYPTION_KEYS_JSON", default="{}")).keys()
            if str(key_id).strip()
        ]
    )
    legacy = sorted(
        [
            str(key_id).strip()
            for key_id in _json_loads(resolve_secret("APP_FIELD_ENCRYPTION_LEGACY_KEYS_JSON", default="{}")).keys()
            if str(key_id).strip()
        ]
    )
    encryptor = get_field_encryptor()
    return {
        "active_key_id": encryptor.active_key_id,
        "primary_key_ids": primary or sorted(list(encryptor.keyring.keys())),
        "legacy_key_ids": legacy,
    }


def encrypt_pii(value: str | None, *, aad: str = "") -> str | None:
    text = _normalize_text(value)
    if not text:
        return None
    try:
        encryptor = get_field_encryptor()
        return encryptor.encrypt_text(text, aad=aad)
    except Exception:
        required = _bool_env("APP_FIELD_ENCRYPTION_REQUIRED", default=False) or _is_production_env()
        if required:
            raise
        return text


def decrypt_pii(value: str | None, *, aad: str = "") -> str | None:
    text = _normalize_text(value)
    if not text:
        return None
    try:
        encryptor = get_field_encryptor()
        decrypted = encryptor.decrypt_text(text, aad=aad)
        return _normalize_text(decrypted) or None
    except Exception:
        if _bool_env("APP_FIELD_ENCRYPTION_REQUIRED", default=False) or _is_production_env():
            raise
        return text


PII_ENCRYPTION_FIELDS_BY_COLLECTION: dict[str, list[str]] = {
    "auth_users": ["alternate_email"],
    "students": [
        "parent_email",
        "profile_photo_data_url",
        "profile_face_template_json",
        "enrollment_video_template_json",
    ],
    "faculty": ["profile_photo_data_url"],
}


def _subject_for_aad(payload: dict[str, Any]) -> str:
    for key in ("id", "email", "registration_number", "faculty_identifier", "_id"):
        value = payload.get(key)
        if value is None:
            continue
        text = _normalize_text(str(value))
        if text:
            return text
    return "unknown"


def _looks_like_encrypted_envelope(value: str) -> bool:
    raw = _normalize_text(value)
    if not raw:
        return False
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return False
    if not isinstance(parsed, dict):
        return False
    return str(parsed.get("alg") or "") == "AES256_GCM" and bool(parsed.get("ct"))


def apply_pii_encryption_policy(collection_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = dict(payload)
    fields = PII_ENCRYPTION_FIELDS_BY_COLLECTION.get(str(collection_name), [])
    if not fields:
        return body

    subject = _subject_for_aad(body)
    for field_name in fields:
        encrypted_field_name = f"{field_name}_encrypted"

        # Keep encrypted payload canonical if already supplied.
        if _normalize_text(str(body.get(encrypted_field_name) or "")):
            body[field_name] = None
            continue

        raw_value = body.get(field_name)
        if not isinstance(raw_value, str):
            continue
        clean_value = _normalize_text(raw_value)
        if not clean_value:
            continue

        if _looks_like_encrypted_envelope(clean_value):
            encrypted_value = clean_value
        else:
            normalized_value = clean_value.lower() if field_name == "alternate_email" else clean_value
            encrypted_value = encrypt_pii(
                normalized_value,
                aad=f"{collection_name}:{subject}:{field_name}",
            )
            if (
                collection_name == "auth_users"
                and field_name == "alternate_email"
                and normalized_value
            ):
                body["alternate_email_hash"] = hash_lookup_value(normalized_value, purpose="alternate-email")

        body[encrypted_field_name] = encrypted_value
        body[field_name] = None

    return body


def rotate_collection_encryption(
    mongo_db,
    *,
    collection_name: str,
    field_names: list[str],
    dry_run: bool = True,
    batch_size: int = 500,
) -> dict[str, Any]:
    encryptor = get_field_encryptor()
    scanned = 0
    rotated = 0
    already_current = 0
    plaintext_migrated = 0
    skipped = 0
    failed = 0
    errors: list[str] = []

    projection = {"_id": 1}
    for subject_key in ("id", "email", "registration_number", "faculty_identifier"):
        projection[subject_key] = 1
    for field_name in field_names:
        projection[field_name] = 1

    cursor = mongo_db[collection_name].find({}, projection=projection).batch_size(max(1, int(batch_size)))
    for doc in cursor:
        scanned += 1
        updates: dict[str, Any] = {}
        for field_name in field_names:
            raw_value = doc.get(field_name)
            if raw_value is None:
                continue
            if not isinstance(raw_value, str):
                skipped += 1
                continue
            value = _normalize_text(raw_value)
            if not value:
                continue
            try:
                canonical_aad = _canonical_rotation_aad(collection_name, doc=doc, field_name=field_name)
                is_envelope = _looks_like_encrypted_envelope(value)
                if is_envelope:
                    current_kid = encryptor.envelope_key_id(value)
                    if current_kid == encryptor.active_key_id:
                        already_current += 1
                        continue
                    plaintext = _decrypt_rotation_value(
                        encryptor,
                        value=value,
                        collection_name=collection_name,
                        doc=doc,
                        field_name=field_name,
                    )
                else:
                    plaintext = value
                    plaintext_migrated += 1
                updates[field_name] = encryptor.encrypt_text(
                    plaintext,
                    aad=canonical_aad,
                )
            except Exception as exc:
                failed += 1
                errors.append(f"_id={doc.get('_id')} field={field_name}: {exc}")
        if not updates:
            continue
        rotated += 1
        if dry_run:
            continue
        mongo_db[collection_name].update_one({"_id": doc["_id"]}, {"$set": updates})

    return {
        "collection": collection_name,
        "fields": field_names,
        "dry_run": bool(dry_run),
        "scanned": int(scanned),
        "rotated": int(rotated),
        "already_current": int(already_current),
        "plaintext_migrated": int(plaintext_migrated),
        "skipped": int(skipped),
        "failed": int(failed),
        "errors": errors[:20],
        "active_key_id": encryptor.active_key_id,
    }


def _base_field_for_rotation(field_name: str) -> str:
    token = _normalize_text(field_name)
    if token.endswith("_encrypted"):
        return token[: -len("_encrypted")]
    return token


def _canonical_rotation_aad(
    collection_name: str,
    *,
    doc: dict[str, Any],
    field_name: str,
) -> str:
    subject = _subject_for_aad(doc)
    base_field = _base_field_for_rotation(field_name)
    return f"{collection_name}:{subject}:{base_field}"


def _rotation_aad_candidates(
    collection_name: str,
    *,
    doc: dict[str, Any],
    field_name: str,
) -> list[str]:
    subject = _subject_for_aad(doc)
    base_field = _base_field_for_rotation(field_name)
    candidates = [
        _canonical_rotation_aad(collection_name, doc=doc, field_name=field_name),
        f"{collection_name}:{subject}:{field_name}",
        f"{collection_name}:{base_field}",
        f"{collection_name}:{field_name}",
        "",
    ]
    unique: list[str] = []
    for aad in candidates:
        if aad not in unique:
            unique.append(aad)
    return unique


def _decrypt_rotation_value(
    encryptor: FieldEncryptor,
    *,
    value: str,
    collection_name: str,
    doc: dict[str, Any],
    field_name: str,
) -> str:
    last_error: Exception | None = None
    for aad in _rotation_aad_candidates(collection_name, doc=doc, field_name=field_name):
        try:
            return encryptor.decrypt_text(value, aad=aad)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    raise RuntimeError(f"unable to decrypt with known AAD patterns ({last_error})")


def generate_totp_secret() -> str:
    # RFC 6238-compatible secret (base32, no padding).
    return base64.b32encode(secrets.token_bytes(20)).decode("utf-8").replace("=", "")


def generate_totp_qr_svg_data_uri(otpauth_uri: str) -> str | None:
    value = _normalize_text(otpauth_uri)
    if not value:
        return None
    try:
        import qrcode  # type: ignore
        from qrcode.image.svg import SvgPathImage  # type: ignore
    except Exception:
        return None

    try:
        qr = qrcode.QRCode(  # type: ignore[attr-defined]
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,  # type: ignore[attr-defined]
            box_size=8,
            border=2,
        )
        qr.add_data(value)
        qr.make(fit=True)
        img = qr.make_image(image_factory=SvgPathImage)
        payload = io.BytesIO()
        img.save(payload)
        encoded = base64.b64encode(payload.getvalue()).decode("ascii")
        return f"data:image/svg+xml;base64,{encoded}"
    except Exception:
        return None


def _totp_counter(at_time: datetime, *, interval_seconds: int) -> int:
    ts = int(at_time.astimezone(timezone.utc).timestamp())
    return max(0, ts // max(1, int(interval_seconds)))


def _totp_code(secret_b32: str, *, counter: int, digits: int = 6) -> str:
    normalized = re.sub(r"\s+", "", secret_b32).upper()
    padding = "=" * (-len(normalized) % 8)
    secret = base64.b32decode(normalized + padding)
    msg = counter.to_bytes(8, "big")
    digest = hmac.new(secret, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = (
        ((digest[offset] & 0x7F) << 24)
        | ((digest[offset + 1] & 0xFF) << 16)
        | ((digest[offset + 2] & 0xFF) << 8)
        | (digest[offset + 3] & 0xFF)
    )
    otp = binary % (10 ** digits)
    return str(otp).zfill(digits)


def verify_totp_code(
    secret_b32: str,
    code: str,
    *,
    interval_seconds: int = 30,
    allowed_drift_steps: int = 2,
    digits: int = 6,
    now_dt: datetime | None = None,
) -> bool:
    return (
        match_totp_code(
            secret_b32,
            code,
            interval_seconds=interval_seconds,
            allowed_drift_steps=allowed_drift_steps,
            digits=digits,
            now_dt=now_dt,
        )
        is not None
    )


def _totp_delta_candidates(max_drift: int, *, preferred_delta: int | None = None) -> list[int]:
    max_abs = max(0, int(max_drift))
    if max_abs <= 0:
        return [0]
    deltas = list(range(-max_abs, max_abs + 1))
    if preferred_delta is None:
        return deltas
    preferred = max(-max_abs, min(max_abs, int(preferred_delta)))
    return sorted(deltas, key=lambda delta: (abs(delta - preferred), abs(delta), delta))


def match_totp_code(
    secret_b32: str,
    code: str,
    *,
    interval_seconds: int = 30,
    allowed_drift_steps: int = 2,
    digits: int = 6,
    preferred_delta: int | None = None,
    now_dt: datetime | None = None,
) -> int | None:
    expected_digits = max(4, min(10, int(digits or 6)))
    otp = re.sub(r"\D+", "", _normalize_text(code))
    if not otp or len(otp) != expected_digits:
        return None
    now_value = now_dt or _utc_now()
    current_counter = _totp_counter(now_value, interval_seconds=interval_seconds)
    drift = max(0, int(allowed_drift_steps))
    try:
        for delta in _totp_delta_candidates(drift, preferred_delta=preferred_delta):
            candidate = _totp_code(secret_b32, counter=current_counter + delta, digits=expected_digits)
            if hmac.compare_digest(candidate, otp):
                return int(delta)
    except Exception:
        return None
    return None


def generate_backup_codes(count: int = 8) -> list[str]:
    total = max(2, min(20, int(count)))
    return [secrets.token_hex(4).upper() for _ in range(total)]


def hash_backup_code(code: str) -> str:
    salt = secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", code.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()
    return f"{salt}${digest}"


def verify_backup_code(code: str, stored_hash: str) -> bool:
    try:
        salt, digest = stored_hash.split("$", 1)
    except ValueError:
        return False
    computed = hashlib.pbkdf2_hmac("sha256", code.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()
    return hmac.compare_digest(computed, digest)


def decode_hs256_jwt(
    token: str,
    *,
    secret: str,
    expected_issuer: str | None = None,
    expected_audience: str | None = None,
    leeway_seconds: int = 60,
) -> dict[str, Any]:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError as exc:
        raise ValueError("Invalid JWT structure") from exc

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual_sig = _b64url_decode(signature_b64)
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("Invalid JWT signature")

    try:
        header = json.loads(_b64url_decode(header_b64).decode("utf-8"))
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception as exc:
        raise ValueError("Invalid JWT payload") from exc

    if str(header.get("alg")) != "HS256":
        raise ValueError("Unsupported JWT algorithm")

    now_ts = int(_utc_now().timestamp())
    exp = payload.get("exp")
    if isinstance(exp, int) and exp < (now_ts - abs(int(leeway_seconds))):
        raise ValueError("JWT expired")
    nbf = payload.get("nbf")
    if isinstance(nbf, int) and nbf > (now_ts + abs(int(leeway_seconds))):
        raise ValueError("JWT not active yet")

    if expected_issuer and str(payload.get("iss", "")) != expected_issuer:
        raise ValueError("Unexpected JWT issuer")

    if expected_audience:
        aud = payload.get("aud")
        if isinstance(aud, list):
            if expected_audience not in [str(item) for item in aud]:
                raise ValueError("Unexpected JWT audience")
        elif str(aud or "") != expected_audience:
            raise ValueError("Unexpected JWT audience")

    return payload


def parse_saml_assertion(assertion_b64: str) -> dict[str, Any]:
    raw = assertion_b64.strip()
    if not raw:
        raise ValueError("SAML assertion is required")
    try:
        xml_bytes = base64.b64decode(raw)
    except Exception as exc:
        raise ValueError("Invalid SAML base64 payload") from exc
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ValueError("Invalid SAML XML payload") from exc

    def local_name(tag: str) -> str:
        if "}" in tag:
            return tag.split("}", 1)[1]
        return tag

    name_id = None
    attributes: dict[str, list[str]] = {}
    for elem in root.iter():
        tag = local_name(elem.tag)
        if tag == "NameID" and elem.text and not name_id:
            name_id = elem.text.strip()
        if tag != "Attribute":
            continue
        attr_name = _normalize_text(elem.attrib.get("Name") or elem.attrib.get("FriendlyName"))
        values: list[str] = []
        for child in list(elem):
            child_tag = local_name(child.tag)
            if child_tag == "AttributeValue" and child.text:
                values.append(child.text.strip())
        if attr_name:
            attributes[attr_name] = [v for v in values if v]

    if not name_id:
        raise ValueError("SAML assertion is missing NameID")

    return {
        "name_id": name_id,
        "attributes": attributes,
    }


def parse_datetime_param(value: str | None) -> datetime | None:
    return _coerce_utc_dt(value)


def iso_utc(value: datetime | None) -> str | None:
    if not value:
        return None
    normalized = value.astimezone(timezone.utc)
    return normalized.isoformat().replace("+00:00", "Z")


def compute_rpo_reference(now_dt: datetime | None = None) -> dict[str, Any]:
    current = now_dt or _utc_now()
    target = current - timedelta(minutes=15)
    return {
        "measured_at": iso_utc(current),
        "target_rpo_minutes": 15,
        "required_latest_backup_after": iso_utc(target),
    }
