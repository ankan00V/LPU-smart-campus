import unittest
from unittest import mock

from app import postgres_tools


class PostgresToolsTests(unittest.TestCase):
    def test_require_postgres_command_prefers_matching_major_over_path_default(self):
        candidates = [
            "/opt/homebrew/bin/pg_dump",
            "/opt/homebrew/opt/postgresql@17/bin/pg_dump",
        ]
        with (
            mock.patch("app.postgres_tools._candidate_commands", return_value=candidates),
            mock.patch(
                "app.postgres_tools._command_major_version",
                side_effect=lambda command: 16 if command.endswith("/bin/pg_dump") and "@17" not in command else 17,
            ),
        ):
            resolved = postgres_tools.require_postgres_command("pg_dump", preferred_major=17)
        self.assertEqual(resolved, "/opt/homebrew/opt/postgresql@17/bin/pg_dump")

    def test_postgres_server_major_version_parses_version_num(self):
        class _Cursor:
            def execute(self, _query):
                return None

            def fetchone(self):
                return ("170008",)

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        class _Connection:
            def cursor(self):
                return _Cursor()

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        postgres_tools.postgres_server_major_version.cache_clear()
        with (
            mock.patch("app.database.postgres_libpq_url", return_value="postgresql://db.test/app"),
            mock.patch("psycopg.connect", return_value=_Connection()),
        ):
            major = postgres_tools.postgres_server_major_version("postgresql+psycopg://db.test/app")
        self.assertEqual(major, 17)


if __name__ == "__main__":
    unittest.main()
