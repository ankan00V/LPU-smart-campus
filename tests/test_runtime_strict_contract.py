import os
import unittest
from unittest import mock

os.environ["APP_RUNTIME_STRICT"] = "false"
os.environ["SQLALCHEMY_DATABASE_URL"] = "sqlite:///:memory:"

from app import otp_delivery, redis_client, workers
from app.main import _assert_strict_runtime_contract, _otp_verify_connection_on_startup


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

    def test_otp_verify_connection_defaults_to_strict_mode(self):
        os.environ["APP_RUNTIME_STRICT"] = "true"
        os.environ.pop("OTP_VERIFY_CONNECTION_ON_STARTUP", None)
        self.assertTrue(_otp_verify_connection_on_startup())

    def test_otp_verify_connection_can_be_disabled_explicitly(self):
        os.environ["APP_RUNTIME_STRICT"] = "true"
        os.environ["OTP_VERIFY_CONNECTION_ON_STARTUP"] = "false"
        self.assertFalse(_otp_verify_connection_on_startup())

    @mock.patch("app.redis_client.get_redis", return_value=None)
    def test_rate_limit_has_no_local_fallback(self, _get_redis):
        os.environ["REDIS_REQUIRED"] = "false"
        with self.assertRaises(RuntimeError):
            redis_client.rate_limit_hit("auth:127.0.0.1:user", limit=10, window_seconds=60)

    @mock.patch("app.workers.send_login_otp", return_value={"channel": "smtp-email"})
    @mock.patch("app.workers._update_otp_delivery_record")
    @mock.patch("app.workers._create_otp_delivery_confirmation", return_value="token-77")
    def test_dispatch_login_otp_returns_confirmed_delivery_channel(
        self,
        create_confirmation,
        update_delivery_record,
        send_login_otp,
    ):
        os.environ["WORKER_ENABLE_OTP"] = "true"
        payload = workers.dispatch_login_otp("person@example.com", "123456", timeout_seconds=5, user_id=77)
        self.assertEqual(payload, {"channel": "smtp-email"})
        create_confirmation.assert_called_once_with(
            user_id=77,
            destination_email="person@example.com",
            purpose="login",
        )
        send_login_otp.assert_called_once_with("person@example.com", "123456")
        self.assertEqual(update_delivery_record.call_count, 2)
        update_delivery_record.assert_any_call("token-77", status="processing", channel="smtp-processing")
        update_delivery_record.assert_any_call("token-77", status="sent", channel="smtp-email")

    @mock.patch("app.workers._update_otp_delivery_record")
    @mock.patch("app.workers._create_otp_delivery_confirmation", return_value="token-11")
    @mock.patch("app.workers.send_login_otp", side_effect=RuntimeError("smtp down"))
    def test_dispatch_login_otp_marks_enqueue_failure(
        self,
        _send_login_otp,
        _create_confirmation,
        update_delivery_record,
    ):
        os.environ["WORKER_ENABLE_OTP"] = "true"
        with self.assertRaisesRegex(RuntimeError, "OTP delivery failed"):
            workers.dispatch_login_otp("person@example.com", "123456", timeout_seconds=5, user_id=11)
        self.assertEqual(update_delivery_record.call_count, 2)
        update_delivery_record.assert_any_call("token-11", status="processing", channel="smtp-processing")
        failed_call = update_delivery_record.call_args_list[-1]
        self.assertEqual(failed_call.args[0], "token-11")
        self.assertEqual(failed_call.kwargs["status"], "failed")
        self.assertEqual(failed_call.kwargs["channel"], "delivery-failed")
        self.assertIn("smtp down", failed_call.kwargs["error"])

    def test_assert_worker_ready_auto_bootstraps_local_worker(self):
        os.environ["WORKER_REQUIRED"] = "true"
        os.environ.pop("WORKER_AUTO_BOOTSTRAP", None)
        with (
            mock.patch("app.workers.worker_ready", return_value=True),
            mock.patch("app.workers.worker_live", side_effect=[False, False, True]),
            mock.patch("app.workers.app_env", return_value="development"),
            mock.patch("app.workers._spawn_worker_process", return_value=43210) as mocked_spawn,
            mock.patch("app.workers._read_autoboot_pid", return_value=None),
        ):
            workers.assert_worker_ready()
        mocked_spawn.assert_called_once()

    def test_assert_worker_ready_still_fails_when_autoboot_disabled(self):
        os.environ["WORKER_REQUIRED"] = "true"
        os.environ["WORKER_AUTO_BOOTSTRAP"] = "false"
        with (
            mock.patch("app.workers.worker_ready", return_value=True),
            mock.patch("app.workers.worker_live", return_value=False),
        ):
            with self.assertRaisesRegex(RuntimeError, "no active Celery worker responded to ping"):
                workers.assert_worker_ready()

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
        os.environ["MONGO_STARTUP_STRICT"] = "true"
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
        os.environ["MONGO_STARTUP_STRICT"] = "true"
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
        os.environ["MONGO_STARTUP_STRICT"] = "true"
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
        os.environ["MONGO_STARTUP_STRICT"] = "true"
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
