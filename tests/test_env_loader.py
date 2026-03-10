import os
import tempfile
import unittest
from pathlib import Path

from app import env_loader


class EnvLoaderTests(unittest.TestCase):
    def setUp(self):
        self._env_backup = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)

    def test_local_overlay_overrides_base_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".env").write_text(
                "APP_ENV=development\nAPP_RUNTIME_STRICT=true\nSQLALCHEMY_DATABASE_URL=postgresql+psycopg://primary/db\n",
                encoding="utf-8",
            )
            (root / ".env.local").write_text(
                "APP_RUNTIME_STRICT=false\nSQLALCHEMY_DATABASE_URL=sqlite:///./campus.db\n",
                encoding="utf-8",
            )
            os.environ.pop("APP_ENV", None)
            os.environ.pop("APP_RUNTIME_STRICT", None)
            os.environ.pop("SQLALCHEMY_DATABASE_URL", None)
            env_loader._ENV_LOADED = False
            env_loader.load_app_env(force=True, project_root=root)
            self.assertEqual(os.environ["APP_RUNTIME_STRICT"], "false")
            self.assertEqual(os.environ["SQLALCHEMY_DATABASE_URL"], "sqlite:///./campus.db")

    def test_development_prefers_project_env_over_explicit_shell_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".env").write_text(
                "APP_ENV=development\nAPP_RUNTIME_STRICT=false\n",
                encoding="utf-8",
            )
            (root / ".env.local").write_text(
                "APP_RUNTIME_STRICT=true\n",
                encoding="utf-8",
            )
            os.environ["APP_RUNTIME_STRICT"] = "false"
            env_loader._ENV_LOADED = False
            env_loader.load_app_env(force=True, project_root=root)
            self.assertEqual(os.environ["APP_RUNTIME_STRICT"], "true")

    def test_production_keeps_explicit_environment_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".env").write_text(
                "APP_ENV=production\nAPP_RUNTIME_STRICT=false\n",
                encoding="utf-8",
            )
            (root / ".env.production").write_text(
                "APP_RUNTIME_STRICT=true\n",
                encoding="utf-8",
            )
            os.environ["APP_RUNTIME_STRICT"] = "false"
            env_loader._ENV_LOADED = False
            env_loader.load_app_env(force=True, project_root=root)
            self.assertEqual(os.environ["APP_RUNTIME_STRICT"], "false")

    def test_production_uses_production_overlay(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".env").write_text(
                "APP_ENV=production\nAPP_RUNTIME_STRICT=false\n",
                encoding="utf-8",
            )
            (root / ".env.production").write_text(
                "APP_RUNTIME_STRICT=true\n",
                encoding="utf-8",
            )
            os.environ.pop("APP_ENV", None)
            os.environ.pop("APP_RUNTIME_STRICT", None)
            env_loader._ENV_LOADED = False
            env_loader.load_app_env(force=True, project_root=root)
            self.assertEqual(os.environ["APP_RUNTIME_STRICT"], "true")
