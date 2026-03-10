import unittest
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class StrictStackComposeTests(unittest.TestCase):
    def test_strict_stack_env_matches_runtime_contract(self):
        compose_path = PROJECT_ROOT / "deploy" / "docker-compose.strict.yml"
        payload = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
        strict_env = payload["x-strict-env"]

        self.assertEqual(strict_env["APP_RUNTIME_STRICT"], "true")
        self.assertEqual(strict_env["WORKER_REQUIRED"], "true")
        self.assertEqual(strict_env["WORKER_INLINE_FALLBACK_ENABLED"], "false")
        self.assertEqual(strict_env["WORKER_WAIT_FOR_OTP_RESULT"], "true")
        self.assertIn(strict_env["OTP_DELIVERY_MODE"], {"smtp", "graph"})

    def test_strict_stack_includes_mailpit_backing_service(self):
        compose_path = PROJECT_ROOT / "deploy" / "docker-compose.strict.yml"
        payload = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
        services = payload["services"]

        self.assertIn("mailpit", services)
        self.assertEqual(services["app"]["depends_on"]["mailpit"]["condition"], "service_started")
        self.assertEqual(services["worker"]["depends_on"]["mailpit"]["condition"], "service_started")
