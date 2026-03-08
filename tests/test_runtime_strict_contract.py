import os
import unittest
from unittest import mock

os.environ["APP_RUNTIME_STRICT"] = "false"
os.environ["SQLALCHEMY_DATABASE_URL"] = "sqlite:///:memory:"

from app import otp_delivery, redis_client, workers
from app.main import _assert_strict_runtime_contract


class RuntimeStrictContractTests(unittest.TestCase):
    def setUp(self):
        self._env_backup = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)

    def test_redis_required_defaults_to_false(self):
        os.environ.pop("REDIS_REQUIRED", None)
        self.assertFalse(redis_client.redis_required())

    def test_worker_required_defaults_to_false(self):
        os.environ.pop("WORKER_REQUIRED", None)
        self.assertFalse(workers.worker_required())

    def test_worker_inline_fallback_defaults_to_true(self):
        os.environ.pop("WORKER_INLINE_FALLBACK_ENABLED", None)
        self.assertTrue(workers.inline_fallback_enabled())

    @mock.patch("app.redis_client.get_redis", return_value=None)
    def test_rate_limit_has_no_local_fallback(self, _get_redis):
        os.environ["REDIS_REQUIRED"] = "false"
        with self.assertRaises(RuntimeError):
            redis_client.rate_limit_hit("auth:127.0.0.1:user", limit=10, window_seconds=60)

    @mock.patch("app.workers.get_celery_app", return_value=None)
    def test_dispatch_login_otp_fails_when_inline_fallback_disabled(self, _celery):
        os.environ["WORKER_REQUIRED"] = "false"
        os.environ["WORKER_ENABLE_OTP"] = "true"
        os.environ["WORKER_INLINE_FALLBACK_ENABLED"] = "false"
        with self.assertRaises(RuntimeError):
            workers.dispatch_login_otp("person@example.com", "123456", timeout_seconds=5)

    @mock.patch("app.workers.get_celery_app", return_value=None)
    def test_dispatch_login_otp_never_uses_inline_fallback(self, _celery):
        os.environ["WORKER_REQUIRED"] = "false"
        os.environ["WORKER_ENABLE_OTP"] = "true"
        os.environ["WORKER_INLINE_FALLBACK_ENABLED"] = "true"
        with self.assertRaises(RuntimeError):
            workers.dispatch_login_otp("person@example.com", "123456", timeout_seconds=5)

    def test_dispatch_login_otp_requires_result_confirmation(self):
        os.environ["WORKER_ENABLE_OTP"] = "true"
        os.environ["WORKER_WAIT_FOR_OTP_RESULT"] = "false"
        with self.assertRaises(RuntimeError):
            workers.dispatch_login_otp("person@example.com", "123456", timeout_seconds=5)

    @mock.patch("app.workers.get_celery_app")
    def test_dispatch_login_otp_returns_confirmed_delivery_channel(self, get_celery_app):
        class DummyResult:
            def get(self, timeout):  # noqa: ANN001
                return {"channel": "smtp-email", "otp_debug_code": "999999"}

        class DummyCelery:
            def send_task(self, name, kwargs):  # noqa: ANN001
                return DummyResult()

        os.environ["WORKER_ENABLE_OTP"] = "true"
        os.environ["WORKER_WAIT_FOR_OTP_RESULT"] = "true"
        get_celery_app.return_value = DummyCelery()
        payload = workers.dispatch_login_otp("person@example.com", "123456", timeout_seconds=5)
        self.assertEqual(payload, {"channel": "smtp-email"})

    def test_runtime_strict_contract_rejects_non_strict_flags(self):
        os.environ["APP_RUNTIME_STRICT"] = "true"
        os.environ["REDIS_REQUIRED"] = "false"
        os.environ["WORKER_REQUIRED"] = "false"
        os.environ["WORKER_INLINE_FALLBACK_ENABLED"] = "true"
        with self.assertRaises(RuntimeError):
            _assert_strict_runtime_contract()

    def test_runtime_strict_contract_rejects_debug_otp_mode(self):
        os.environ["APP_RUNTIME_STRICT"] = "true"
        os.environ["MONGO_PERSISTENCE_REQUIRED"] = "true"
        os.environ["REDIS_REQUIRED"] = "true"
        os.environ["WORKER_REQUIRED"] = "true"
        os.environ["WORKER_ENABLE_OTP"] = "true"
        os.environ["WORKER_ENABLE_NOTIFICATIONS"] = "true"
        os.environ["WORKER_ENABLE_FACE_REVERIFY"] = "true"
        os.environ["WORKER_ENABLE_RECOMPUTE"] = "true"
        os.environ["WORKER_INLINE_FALLBACK_ENABLED"] = "false"
        os.environ["WORKER_WAIT_FOR_OTP_RESULT"] = "true"
        os.environ["OTP_DELIVERY_MODE"] = "debug"
        with (
            mock.patch(
                "app.main.database_status",
                return_value={"backend": "postgresql", "connected": True},
            ),
            mock.patch("app.main.mongo_status", return_value={"remote_host": True, "tls_enabled": True}),
            mock.patch("app.main.redis_status", return_value={"remote_host": True, "tls_enabled": True}),
            mock.patch("app.main.worker_transport_status", return_value={}),
        ):
            with self.assertRaises(RuntimeError):
                _assert_strict_runtime_contract()

    def test_runtime_strict_contract_accepts_strict_flags(self):
        os.environ["APP_RUNTIME_STRICT"] = "true"
        os.environ["MONGO_PERSISTENCE_REQUIRED"] = "true"
        os.environ["REDIS_REQUIRED"] = "true"
        os.environ["WORKER_REQUIRED"] = "true"
        os.environ["WORKER_ENABLE_OTP"] = "true"
        os.environ["WORKER_ENABLE_NOTIFICATIONS"] = "true"
        os.environ["WORKER_ENABLE_FACE_REVERIFY"] = "true"
        os.environ["WORKER_ENABLE_RECOMPUTE"] = "true"
        os.environ["WORKER_INLINE_FALLBACK_ENABLED"] = "false"
        os.environ["WORKER_WAIT_FOR_OTP_RESULT"] = "true"
        os.environ["OTP_DELIVERY_MODE"] = "smtp"
        with (
            mock.patch(
                "app.main.database_status",
                return_value={"backend": "postgresql", "connected": True},
            ),
            mock.patch("app.main.mongo_status", return_value={"remote_host": True, "tls_enabled": True}),
            mock.patch("app.main.redis_status", return_value={"remote_host": True, "tls_enabled": True}),
            mock.patch("app.main.worker_transport_status", return_value={}),
        ):
            _assert_strict_runtime_contract()

    def test_runtime_strict_contract_rejects_local_managed_services(self):
        os.environ["APP_RUNTIME_STRICT"] = "true"
        os.environ["APP_MANAGED_SERVICES_REQUIRED"] = "true"
        os.environ["MONGO_PERSISTENCE_REQUIRED"] = "true"
        os.environ["REDIS_REQUIRED"] = "true"
        os.environ["WORKER_REQUIRED"] = "true"
        os.environ["WORKER_ENABLE_OTP"] = "true"
        os.environ["WORKER_ENABLE_NOTIFICATIONS"] = "true"
        os.environ["WORKER_ENABLE_FACE_REVERIFY"] = "true"
        os.environ["WORKER_ENABLE_RECOMPUTE"] = "true"
        os.environ["WORKER_INLINE_FALLBACK_ENABLED"] = "false"
        os.environ["WORKER_WAIT_FOR_OTP_RESULT"] = "true"
        os.environ["OTP_DELIVERY_MODE"] = "smtp"
        with (
            mock.patch(
                "app.main.database_status",
                return_value={
                    "backend": "postgresql",
                    "connected": True,
                    "remote_host": False,
                    "tls_enabled": False,
                },
            ),
            mock.patch(
                "app.main.mongo_status",
                return_value={"remote_host": False, "tls_enabled": True},
            ),
            mock.patch(
                "app.main.redis_status",
                return_value={"remote_host": False, "tls_enabled": False},
            ),
            mock.patch(
                "app.main.worker_transport_status",
                return_value={
                    "broker": {"configured": True, "remote_host": False, "tls_enabled": False},
                    "backend": {"configured": True, "remote_host": False, "tls_enabled": False},
                },
            ),
        ):
            with self.assertRaises(RuntimeError):
                _assert_strict_runtime_contract()

    def test_runtime_strict_contract_accepts_remote_managed_services(self):
        os.environ["APP_RUNTIME_STRICT"] = "true"
        os.environ["APP_MANAGED_SERVICES_REQUIRED"] = "true"
        os.environ["MONGO_PERSISTENCE_REQUIRED"] = "true"
        os.environ["REDIS_REQUIRED"] = "true"
        os.environ["WORKER_REQUIRED"] = "true"
        os.environ["WORKER_ENABLE_OTP"] = "true"
        os.environ["WORKER_ENABLE_NOTIFICATIONS"] = "true"
        os.environ["WORKER_ENABLE_FACE_REVERIFY"] = "true"
        os.environ["WORKER_ENABLE_RECOMPUTE"] = "true"
        os.environ["WORKER_INLINE_FALLBACK_ENABLED"] = "false"
        os.environ["WORKER_WAIT_FOR_OTP_RESULT"] = "true"
        os.environ["OTP_DELIVERY_MODE"] = "smtp"
        with (
            mock.patch(
                "app.main.database_status",
                return_value={
                    "backend": "postgresql",
                    "connected": True,
                    "remote_host": True,
                    "tls_enabled": True,
                },
            ),
            mock.patch(
                "app.main.mongo_status",
                return_value={"remote_host": True, "tls_enabled": True},
            ),
            mock.patch(
                "app.main.redis_status",
                return_value={"remote_host": True, "tls_enabled": True},
            ),
            mock.patch(
                "app.main.worker_transport_status",
                return_value={
                    "broker": {"configured": True, "remote_host": True, "tls_enabled": True},
                    "backend": {"configured": True, "remote_host": True, "tls_enabled": True},
                },
            ),
        ):
            _assert_strict_runtime_contract()

    def test_otp_delivery_contract_rejects_debug_mode(self):
        os.environ["OTP_DELIVERY_MODE"] = "debug"
        with self.assertRaises(RuntimeError):
            otp_delivery.assert_otp_delivery_ready()
