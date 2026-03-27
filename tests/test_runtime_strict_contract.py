import os
import unittest
from contextlib import ExitStack
from unittest import mock

os.environ["APP_RUNTIME_STRICT"] = "false"
os.environ["SQLALCHEMY_DATABASE_URL"] = "sqlite:///:memory:"

from app import otp_delivery, redis_client, workers
from app.main import _assert_strict_runtime_contract, _otp_verify_connection_on_startup, startup_event


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
    @mock.patch("app.workers._send_login_otp_task", return_value={"channel": "smtp-email"})
    def test_dispatch_login_otp_uses_direct_sync_when_worker_backend_unavailable(
        self,
        mock_send_login_otp_task,
        mock_get_celery_app,
    ):
        os.environ["WORKER_REQUIRED"] = "true"
        os.environ["WORKER_ENABLE_OTP"] = "true"
        os.environ["WORKER_INLINE_FALLBACK_ENABLED"] = "false"
        payload = workers.dispatch_login_otp("person@example.com", "123456", timeout_seconds=5)
        self.assertEqual(payload, {"channel": "smtp-email"})
        mock_send_login_otp_task.assert_called_once_with("person@example.com", "123456")
        mock_get_celery_app.assert_not_called()

    @mock.patch("app.workers._send_login_otp_task", return_value={})
    def test_dispatch_login_otp_direct_sync_requires_valid_delivery_channel(self, _send_login_otp_task):
        os.environ["WORKER_REQUIRED"] = "false"
        os.environ["WORKER_ENABLE_OTP"] = "true"
        os.environ["WORKER_INLINE_FALLBACK_ENABLED"] = "true"
        with self.assertRaisesRegex(RuntimeError, "invalid delivery channel"):
            workers.dispatch_login_otp("person@example.com", "123456", timeout_seconds=5)

    @mock.patch("app.workers._send_login_otp_task", return_value={"channel": "email"})
    def test_dispatch_login_otp_rejects_unknown_delivery_channel(self, _send_login_otp_task):
        os.environ["WORKER_REQUIRED"] = "true"
        os.environ["WORKER_ENABLE_OTP"] = "true"
        with self.assertRaisesRegex(RuntimeError, "invalid delivery channel"):
            workers.dispatch_login_otp("person@example.com", "123456", timeout_seconds=5)

    def test_dispatch_login_otp_requires_result_confirmation(self):
        os.environ["WORKER_ENABLE_OTP"] = "true"
        os.environ["WORKER_WAIT_FOR_OTP_RESULT"] = "false"
        with self.assertRaises(RuntimeError):
            workers.dispatch_login_otp("person@example.com", "123456", timeout_seconds=5)

    @mock.patch("app.workers.pytime.sleep", autospec=True)
    @mock.patch("app.workers.worker_live", side_effect=[False, False, True])
    @mock.patch("app.workers.worker_ready", return_value=True)
    def test_assert_worker_ready_retries_until_worker_is_live(
        self,
        _worker_ready,
        mock_worker_live,
        _sleep,
    ):
        os.environ["WORKER_REQUIRED"] = "true"
        os.environ["WORKER_STARTUP_MAX_ATTEMPTS"] = "3"
        os.environ["WORKER_STARTUP_RETRY_DELAY_SECONDS"] = "0"
        os.environ["WORKER_STARTUP_PING_TIMEOUT_SECONDS"] = "0.2"

        workers.assert_worker_ready()
        self.assertEqual(mock_worker_live.call_count, 3)

    @mock.patch("app.workers.pytime.sleep", autospec=True)
    @mock.patch("app.workers.worker_live", return_value=False)
    @mock.patch("app.workers.worker_ready", return_value=True)
    def test_assert_worker_ready_raises_after_retry_budget(
        self,
        _worker_ready,
        _worker_live,
        _sleep,
    ):
        os.environ["WORKER_REQUIRED"] = "true"
        os.environ["WORKER_STARTUP_MAX_ATTEMPTS"] = "2"
        os.environ["WORKER_STARTUP_RETRY_DELAY_SECONDS"] = "0"
        os.environ["WORKER_STARTUP_PING_TIMEOUT_SECONDS"] = "0.2"

        with self.assertRaisesRegex(RuntimeError, "after 2 startup checks"):
            workers.assert_worker_ready()

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
        os.environ["OTP_DELIVERY_DIRECT_SYNC"] = "false"
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


class StartupEventAsyncSafetyTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._env_backup = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)

    async def test_startup_event_uses_async_sleep_for_mongo_retries(self):
        os.environ["MONGO_STARTUP_MAX_ATTEMPTS"] = "2"
        os.environ["MONGO_STARTUP_RETRY_DELAY_SECONDS"] = "0.25"
        os.environ["MONGO_STARTUP_SQL_SNAPSHOT_SYNC"] = "true"

        mock_db = mock.MagicMock()
        mock_realtime_hub = mock.MagicMock()
        mock_realtime_hub.start = mock.AsyncMock()
        mock_realtime_hub.stop = mock.AsyncMock()

        with ExitStack() as stack:
            stack.enter_context(mock.patch("app.main._assert_strict_runtime_contract"))
            stack.enter_context(mock.patch("app.main.init_sql_schema"))
            stack.enter_context(mock.patch("app.main.validate_production_secrets"))
            stack.enter_context(mock.patch("app.main.assert_otp_delivery_ready"))
            stack.enter_context(mock.patch("app.main.init_redis", return_value=True))
            stack.enter_context(mock.patch("app.main.redis_status", return_value={"enabled": True}))
            stack.enter_context(mock.patch("app.main.redis_required", return_value=False))
            stack.enter_context(mock.patch("app.main.assert_worker_ready"))
            stack.enter_context(mock.patch("app.main.realtime_hub", new=mock_realtime_hub))
            stack.enter_context(mock.patch("app.main.mongo_persistence_required", return_value=False))
            init_mongo = stack.enter_context(mock.patch("app.main.init_mongo", side_effect=[False, True]))
            stack.enter_context(
                mock.patch(
                    "app.main.mongo_status",
                    side_effect=[{"error": "temporary dns failure"}, {"backend": "mongodb"}],
                )
            )
            stack.enter_context(mock.patch("app.main.seed_static_assets_to_mongo"))
            stack.enter_context(mock.patch("app.main.assert_media_storage_ready"))
            stack.enter_context(mock.patch("app.main.dispatch_outbox_batch"))
            stack.enter_context(mock.patch("app.main.bootstrap_food_hall_catalog"))
            stack.enter_context(mock.patch("app.main.sync_sql_snapshot_to_mongo"))
            background_sync = stack.enter_context(
                mock.patch("app.main._start_background_sql_snapshot_sync", return_value=True)
            )
            stack.enter_context(mock.patch("app.main._build_health_payload", return_value={}))
            stack.enter_context(mock.patch("app.main._store_health_payload"))
            stack.enter_context(mock.patch("app.main.SessionLocal", return_value=mock_db))
            blocking_sleep = stack.enter_context(mock.patch("app.main.pytime.sleep", autospec=True))
            async_sleep = stack.enter_context(mock.patch("app.main.asyncio.sleep", new_callable=mock.AsyncMock))
            await startup_event()

        async_sleep.assert_awaited_once_with(0.25)
        blocking_sleep.assert_not_called()
        self.assertEqual(init_mongo.call_count, 2)
        mock_realtime_hub.bind_loop.assert_called_once()
        mock_realtime_hub.start.assert_awaited_once()
        background_sync.assert_called_once()
        mock_db.commit.assert_called()
        mock_db.close.assert_called_once()

    def test_runtime_strict_contract_allows_disabled_otp_startup_verification_for_local_dev(self):
        os.environ["APP_RUNTIME_STRICT"] = "true"
        os.environ["APP_MANAGED_SERVICES_REQUIRED"] = "false"
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
        os.environ["OTP_VERIFY_CONNECTION_ON_STARTUP"] = "false"
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

    def test_runtime_strict_contract_rejects_disabled_otp_startup_verification_for_managed_services(self):
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
        os.environ["OTP_VERIFY_CONNECTION_ON_STARTUP"] = "false"
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

    def test_otp_startup_verification_defaults_to_runtime_strict_mode(self):
        os.environ.pop("OTP_VERIFY_CONNECTION_ON_STARTUP", None)
        os.environ["APP_RUNTIME_STRICT"] = "true"
        self.assertTrue(_otp_verify_connection_on_startup())
        os.environ["APP_RUNTIME_STRICT"] = "false"
        self.assertFalse(_otp_verify_connection_on_startup())

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
        os.environ["OTP_VERIFY_CONNECTION_ON_STARTUP"] = "true"
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
        os.environ["OTP_VERIFY_CONNECTION_ON_STARTUP"] = "true"
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
