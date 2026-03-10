import importlib
import os
import unittest
from unittest.mock import patch


class DatabaseConnectionConfigTests(unittest.TestCase):
    def setUp(self):
        self._env_backup = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)
        import app.database as database

        importlib.reload(database)

    def _reload_database(self):
        import app.database as database

        return importlib.reload(database)

    def test_pooler_host_disables_prepared_statements_by_default(self):
        os.environ["APP_RUNTIME_STRICT"] = "false"
        os.environ["SQLALCHEMY_DATABASE_URL"] = (
            "postgresql://smartcampus:secret@ep-cool-rain-a1b2c3-pooler.ap-south-1.aws.neon.tech/"
            "lpu_smart?sslmode=require"
        )
        os.environ.pop("DATABASE_DISABLE_PREPARED_STATEMENTS", None)

        database = self._reload_database()

        self.assertTrue(database._database_pooler_host())
        self.assertTrue(database._database_disable_prepared_statements())
        self.assertIsNone(database._engine_options()["connect_args"].get("prepare_threshold"))

    def test_explicit_disable_flag_can_be_overridden(self):
        os.environ["APP_RUNTIME_STRICT"] = "false"
        os.environ["SQLALCHEMY_DATABASE_URL"] = (
            "postgresql://smartcampus:secret@ep-cool-rain-a1b2c3-pooler.ap-south-1.aws.neon.tech/"
            "lpu_smart?sslmode=require"
        )
        os.environ["DATABASE_DISABLE_PREPARED_STATEMENTS"] = "false"

        database = self._reload_database()

        self.assertFalse(database._database_disable_prepared_statements())
        self.assertNotIn("prepare_threshold", database._engine_options()["connect_args"])

    def test_admin_database_url_prefers_explicit_direct_endpoint(self):
        os.environ["APP_RUNTIME_STRICT"] = "false"
        os.environ["SQLALCHEMY_DATABASE_URL"] = (
            "postgresql://smartcampus:secret@ep-cool-rain-a1b2c3-pooler.ap-south-1.aws.neon.tech/"
            "lpu_smart?sslmode=require"
        )
        os.environ["POSTGRES_ADMIN_DATABASE_URL"] = (
            "postgresql://smartcampus:secret@ep-cool-rain-a1b2c3.ap-south-1.aws.neon.tech/"
            "lpu_smart?sslmode=require"
        )

        database = self._reload_database()

        self.assertIn("-pooler.", database.SQLALCHEMY_DATABASE_URL)
        self.assertNotIn("-pooler.", database.POSTGRES_ADMIN_DATABASE_URL or "")
        self.assertTrue((database.POSTGRES_ADMIN_LIBPQ_URL or "").startswith("postgresql://"))

    def test_database_hostaddr_env_overrides_resolution(self):
        os.environ["APP_RUNTIME_STRICT"] = "false"
        os.environ["SQLALCHEMY_DATABASE_URL"] = (
            "postgresql://smartcampus:secret@ep-cool-rain-a1b2c3-pooler.ap-south-1.aws.neon.tech/"
            "lpu_smart?sslmode=require"
        )
        os.environ["DATABASE_HOSTADDR"] = "13.228.184.177"

        database = self._reload_database()

        self.assertEqual(database._database_hostaddr(), "13.228.184.177")
        self.assertEqual(database._engine_options()["connect_args"].get("hostaddr"), "13.228.184.177")

    def test_database_prefers_resolved_ipv4_hostaddr(self):
        os.environ["APP_RUNTIME_STRICT"] = "false"
        os.environ["SQLALCHEMY_DATABASE_URL"] = (
            "postgresql://smartcampus:secret@ep-cool-rain-a1b2c3-pooler.ap-south-1.aws.neon.tech/"
            "lpu_smart?sslmode=require"
        )
        os.environ.pop("DATABASE_HOSTADDR", None)
        os.environ["DATABASE_PREFER_IPV4"] = "true"

        database = self._reload_database()
        with patch.object(
            database.socket,
            "getaddrinfo",
            return_value=[
                (None, None, None, None, ("13.228.184.177", 0)),
                (None, None, None, None, ("52.220.170.93", 0)),
            ],
        ):
            self.assertEqual(database._database_hostaddr(), "13.228.184.177")
            self.assertEqual(database._engine_options()["connect_args"].get("hostaddr"), "13.228.184.177")
