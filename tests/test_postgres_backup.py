import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app import postgres_backup


class PostgresBackupTests(unittest.TestCase):
    def test_create_backup_artifact_falls_back_to_portable_snapshot_without_exact_pg_dump(self):
        expected = {
            "backend": "postgresql",
            "format": "portable_snapshot",
            "path": "/tmp/postgres.portable.json",
            "size_bytes": 123,
            "sha256": "abc",
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            with (
                mock.patch("app.postgres_backup.postgres_server_major_version", return_value=17),
                mock.patch("app.postgres_backup.find_postgres_command", return_value=None),
                mock.patch("app.postgres_backup._portable_snapshot_artifact", return_value=expected) as mocked_portable,
            ):
                result = postgres_backup.create_postgresql_backup_artifact(Path(tmp_dir), "postgresql://db.test/app")
        self.assertEqual(result, expected)
        mocked_portable.assert_called_once()

    def test_validate_backup_artifact_accepts_portable_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            snapshot_path = Path(tmp_dir) / "postgres.portable.json"
            snapshot_path.write_text(
                json.dumps(
                    {
                        "format": "portable-postgresql-snapshot",
                        "table_count": 1,
                        "total_row_count": 2,
                        "tables": [
                            {
                                "schema": "public",
                                "name": "students",
                                "columns": [{"name": "id", "type": "INTEGER"}],
                                "rows": [{"id": 1}, {"id": 2}],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            result = postgres_backup.validate_postgresql_backup_artifact(Path(tmp_dir))
        self.assertEqual(result["backend"], "postgresql")
        self.assertEqual(result["format"], "portable_snapshot")
        self.assertTrue(result["validated"])
        self.assertEqual(result["table_count"], 1)


if __name__ == "__main__":
    unittest.main()
