import base64
import hashlib
import hmac
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from app.enterprise_controls import (
    _b64url_encode,
    apply_pii_encryption_policy,
    decode_hs256_jwt,
    encrypt_pii,
    get_field_encryptor,
    hash_backup_code,
    match_totp_code,
    parse_saml_assertion,
    rotate_collection_encryption,
    validate_production_secrets,
    verify_backup_code,
    verify_totp_code,
)


class EnterpriseControlsTests(unittest.TestCase):
    def test_match_totp_code_supports_clock_skew_windows(self):
        # RFC 6238 SHA1 test secret (base32) + known vector code.
        secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
        code = "89005924"  # for unix ts 1234567890 (8 digits)
        now_dt = datetime.fromtimestamp(1234567890 + 90, tz=timezone.utc)  # 3 windows ahead

        self.assertEqual(
            match_totp_code(secret, code, digits=8, allowed_drift_steps=4, now_dt=now_dt),
            -3,
        )
        self.assertTrue(verify_totp_code(secret, code, digits=8, allowed_drift_steps=4, now_dt=now_dt))
        self.assertFalse(verify_totp_code(secret, code, digits=8, allowed_drift_steps=2, now_dt=now_dt))

    def test_backup_code_hash_roundtrip(self):
        code = "ABCD1234"
        stored = hash_backup_code(code)
        self.assertTrue(verify_backup_code(code, stored))
        self.assertFalse(verify_backup_code("WRONG000", stored))

    def test_decode_hs256_jwt_validates_signature_and_claims(self):
        secret = "unit-test-secret"
        now = datetime.now(timezone.utc)
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": "101",
            "iss": "https://issuer.test",
            "aud": "campus-app",
            "exp": int((now + timedelta(minutes=10)).timestamp()),
            "iat": int(now.timestamp()),
        }
        header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        token = f"{header_b64}.{payload_b64}.{_b64url_encode(signature)}"

        decoded = decode_hs256_jwt(
            token,
            secret=secret,
            expected_issuer="https://issuer.test",
            expected_audience="campus-app",
        )
        self.assertEqual(decoded["sub"], "101")

    def test_parse_saml_assertion_extracts_nameid_and_attributes(self):
        xml = """<saml:Assertion xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">
  <saml:Subject>
    <saml:NameID>faculty.one@gmail.com</saml:NameID>
  </saml:Subject>
  <saml:AttributeStatement>
    <saml:Attribute Name="email">
      <saml:AttributeValue>faculty.one@gmail.com</saml:AttributeValue>
    </saml:Attribute>
    <saml:Attribute Name="role">
      <saml:AttributeValue>faculty</saml:AttributeValue>
    </saml:Attribute>
    <saml:Attribute Name="amr">
      <saml:AttributeValue>mfa</saml:AttributeValue>
    </saml:Attribute>
  </saml:AttributeStatement>
</saml:Assertion>"""
        payload = base64.b64encode(xml.encode("utf-8")).decode("utf-8")
        parsed = parse_saml_assertion(payload)
        self.assertEqual(parsed["name_id"], "faculty.one@gmail.com")
        self.assertIn("email", parsed["attributes"])
        self.assertEqual(parsed["attributes"]["role"][0], "faculty")

    def test_apply_pii_encryption_policy_encrypts_auth_alternate_email(self):
        doc = {"id": 12, "alternate_email": "AltUser@Example.com"}
        out = apply_pii_encryption_policy("auth_users", doc)
        self.assertIsNone(out["alternate_email"])
        self.assertIsInstance(out.get("alternate_email_encrypted"), str)
        self.assertTrue(out["alternate_email_encrypted"])
        self.assertIsInstance(out.get("alternate_email_hash"), str)
        self.assertTrue(out["alternate_email_hash"])

    def test_validate_production_secrets_rejects_env_provider(self):
        keys = [
            "APP_ENV",
            "APP_DEPLOY_TARGET",
            "APP_AUTH_SECRET",
            "SCIM_BEARER_TOKEN",
            "APP_LOOKUP_HASH_SECRET",
            "APP_SECRETS_PROVIDER",
            "APP_ALLOW_ENV_SECRETS_IN_PRODUCTION",
            "APP_FIELD_ENCRYPTION_REQUIRED",
            "APP_COOKIE_SECURE",
            "MONGO_PERSISTENCE_REQUIRED",
            "MONGO_STARTUP_STRICT",
            "APP_FIELD_ENCRYPTION_KEYS_JSON",
            "APP_FIELD_ENCRYPTION_ACTIVE_KEY_ID",
        ]
        backup = {key: os.environ.get(key) for key in keys}
        try:
            os.environ["APP_ENV"] = "production"
            os.environ["APP_AUTH_SECRET"] = "prod-auth-secret"
            os.environ["SCIM_BEARER_TOKEN"] = "prod-scim-token"
            os.environ["APP_LOOKUP_HASH_SECRET"] = "prod-lookup-secret"
            os.environ["APP_SECRETS_PROVIDER"] = "env"
            os.environ["APP_ALLOW_ENV_SECRETS_IN_PRODUCTION"] = "false"
            os.environ["APP_FIELD_ENCRYPTION_REQUIRED"] = "true"
            os.environ["APP_COOKIE_SECURE"] = "true"
            os.environ["MONGO_PERSISTENCE_REQUIRED"] = "true"
            os.environ["MONGO_STARTUP_STRICT"] = "true"
            os.environ["APP_FIELD_ENCRYPTION_KEYS_JSON"] = json.dumps(
                {"k1": base64.urlsafe_b64encode(b"a" * 32).decode("utf-8")}
            )
            os.environ["APP_FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "k1"
            with self.assertRaises(RuntimeError):
                validate_production_secrets()
        finally:
            for key, value in backup.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_validate_production_secrets_allows_env_provider_on_railway(self):
        keys = [
            "APP_ENV",
            "APP_DEPLOY_TARGET",
            "APP_AUTH_SECRET",
            "SCIM_BEARER_TOKEN",
            "APP_LOOKUP_HASH_SECRET",
            "APP_SECRETS_PROVIDER",
            "APP_ALLOW_ENV_SECRETS_IN_PRODUCTION",
            "APP_FIELD_ENCRYPTION_REQUIRED",
            "APP_COOKIE_SECURE",
            "APP_RUNTIME_STRICT",
            "REDIS_REQUIRED",
            "WORKER_REQUIRED",
            "WORKER_INLINE_FALLBACK_ENABLED",
            "MONGO_PERSISTENCE_REQUIRED",
            "MONGO_STARTUP_STRICT",
            "APP_FIELD_ENCRYPTION_KEYS_JSON",
            "APP_FIELD_ENCRYPTION_ACTIVE_KEY_ID",
        ]
        backup = {key: os.environ.get(key) for key in keys}
        try:
            os.environ["APP_ENV"] = "production"
            os.environ["APP_DEPLOY_TARGET"] = "railway"
            os.environ["APP_AUTH_SECRET"] = "prod-auth-secret-railway"
            os.environ["SCIM_BEARER_TOKEN"] = "prod-scim-token-railway"
            os.environ["APP_LOOKUP_HASH_SECRET"] = "prod-lookup-secret-railway"
            os.environ["APP_SECRETS_PROVIDER"] = "env"
            os.environ["APP_ALLOW_ENV_SECRETS_IN_PRODUCTION"] = "false"
            os.environ["APP_FIELD_ENCRYPTION_REQUIRED"] = "true"
            os.environ["APP_COOKIE_SECURE"] = "true"
            os.environ["APP_RUNTIME_STRICT"] = "true"
            os.environ["REDIS_REQUIRED"] = "true"
            os.environ["WORKER_REQUIRED"] = "true"
            os.environ["WORKER_INLINE_FALLBACK_ENABLED"] = "false"
            os.environ["MONGO_PERSISTENCE_REQUIRED"] = "true"
            os.environ["MONGO_STARTUP_STRICT"] = "true"
            os.environ["APP_FIELD_ENCRYPTION_KEYS_JSON"] = json.dumps(
                {"k1": base64.urlsafe_b64encode(b"a" * 32).decode("utf-8")}
            )
            os.environ["APP_FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "k1"
            validate_production_secrets()
        finally:
            for key, value in backup.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_validate_production_secrets_rejects_placeholder_secret_values(self):
        keys = [
            "APP_ENV",
            "APP_SECRETS_PROVIDER",
            "APP_SECRETS_FILE",
            "APP_FIELD_ENCRYPTION_REQUIRED",
            "APP_COOKIE_SECURE",
            "APP_RUNTIME_STRICT",
            "REDIS_REQUIRED",
            "WORKER_REQUIRED",
            "WORKER_INLINE_FALLBACK_ENABLED",
            "MONGO_PERSISTENCE_REQUIRED",
            "MONGO_STARTUP_STRICT",
            "APP_FIELD_ENCRYPTION_KEYS_JSON",
            "APP_FIELD_ENCRYPTION_ACTIVE_KEY_ID",
        ]
        backup = {key: os.environ.get(key) for key in keys}
        secret_file = ""
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
                tmp.write(
                    json.dumps(
                        {
                            "APP_AUTH_SECRET": "change-me",
                            "SCIM_BEARER_TOKEN": "prod-scim-token-123",
                            "APP_LOOKUP_HASH_SECRET": "prod-lookup-secret-123",
                        }
                    )
                )
                secret_file = tmp.name
            os.environ["APP_ENV"] = "production"
            os.environ["APP_SECRETS_PROVIDER"] = "file"
            os.environ["APP_SECRETS_FILE"] = secret_file
            os.environ["APP_FIELD_ENCRYPTION_REQUIRED"] = "true"
            os.environ["APP_COOKIE_SECURE"] = "true"
            os.environ["APP_RUNTIME_STRICT"] = "true"
            os.environ["REDIS_REQUIRED"] = "true"
            os.environ["WORKER_REQUIRED"] = "true"
            os.environ["WORKER_INLINE_FALLBACK_ENABLED"] = "false"
            os.environ["MONGO_PERSISTENCE_REQUIRED"] = "true"
            os.environ["MONGO_STARTUP_STRICT"] = "true"
            os.environ["APP_FIELD_ENCRYPTION_KEYS_JSON"] = json.dumps(
                {"k1": base64.urlsafe_b64encode(b"a" * 32).decode("utf-8")}
            )
            os.environ["APP_FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "k1"
            with self.assertRaises(RuntimeError):
                validate_production_secrets()
        finally:
            if secret_file:
                try:
                    os.unlink(secret_file)
                except FileNotFoundError:
                    pass
            for key, value in backup.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_encrypt_pii_in_production_does_not_fallback_to_plaintext(self):
        keys = [
            "APP_ENV",
            "APP_FIELD_ENCRYPTION_REQUIRED",
            "APP_FIELD_ENCRYPTION_KEYS_JSON",
            "APP_FIELD_ENCRYPTION_PRIMARY_KEY",
            "APP_FIELD_ENCRYPTION_ACTIVE_KEY_ID",
        ]
        backup = {key: os.environ.get(key) for key in keys}
        try:
            os.environ["APP_ENV"] = "production"
            os.environ["APP_FIELD_ENCRYPTION_REQUIRED"] = "true"
            os.environ["APP_FIELD_ENCRYPTION_KEYS_JSON"] = "{}"
            os.environ["APP_FIELD_ENCRYPTION_PRIMARY_KEY"] = ""
            os.environ["APP_FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = ""
            get_field_encryptor.cache_clear()
            with self.assertRaises(RuntimeError):
                encrypt_pii("secret@example.com", aad="auth_users:1:alternate_email")
        finally:
            get_field_encryptor.cache_clear()
            for key, value in backup.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_rotate_collection_encryption_handles_document_scoped_aad(self):
        class _Cursor(list):
            def batch_size(self, _size: int):
                return self

        class _Collection:
            def __init__(self, docs):
                self.docs = docs

            def find(self, _query, projection=None):
                rows = []
                for doc in self.docs:
                    if projection:
                        row = {}
                        for key in projection:
                            if key in doc:
                                row[key] = doc[key]
                    else:
                        row = dict(doc)
                    rows.append(row)
                return _Cursor(rows)

            def update_one(self, query, update):
                target_id = query.get("_id")
                for item in self.docs:
                    if item.get("_id") == target_id:
                        item.update(update.get("$set") or {})
                        break

        class _Mongo:
            def __init__(self, docs):
                self.collection = _Collection(docs)

            def __getitem__(self, _name):
                return self.collection

        keys = [
            "APP_FIELD_ENCRYPTION_KEYS_JSON",
            "APP_FIELD_ENCRYPTION_ACTIVE_KEY_ID",
            "APP_FIELD_ENCRYPTION_REQUIRED",
            "APP_ENV",
        ]
        backup = {key: os.environ.get(key) for key in keys}
        try:
            old_key = base64.urlsafe_b64encode(b"a" * 32).decode("utf-8")
            new_key = base64.urlsafe_b64encode(b"b" * 32).decode("utf-8")
            os.environ["APP_FIELD_ENCRYPTION_KEYS_JSON"] = json.dumps({"k1": old_key, "k2": new_key})
            os.environ["APP_FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "k1"
            os.environ["APP_FIELD_ENCRYPTION_REQUIRED"] = "true"
            os.environ["APP_ENV"] = "development"
            get_field_encryptor.cache_clear()
            old_encryptor = get_field_encryptor()
            ciphertext = old_encryptor.encrypt_text(
                "alt@example.com",
                aad="auth_users:101:alternate_email",
            )

            os.environ["APP_FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "k2"
            get_field_encryptor.cache_clear()
            docs = [{"_id": "abc-1", "id": 101, "alternate_email_encrypted": ciphertext}]
            result = rotate_collection_encryption(
                _Mongo(docs),
                collection_name="auth_users",
                field_names=["alternate_email_encrypted"],
                dry_run=False,
                batch_size=100,
            )
            self.assertEqual(result["failed"], 0)
            self.assertEqual(result["rotated"], 1)
            updated = docs[0]["alternate_email_encrypted"]
            self.assertNotEqual(updated, ciphertext)
            plaintext = get_field_encryptor().decrypt_text(updated, aad="auth_users:101:alternate_email")
            self.assertEqual(plaintext, "alt@example.com")
        finally:
            get_field_encryptor.cache_clear()
            for key, value in backup.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
