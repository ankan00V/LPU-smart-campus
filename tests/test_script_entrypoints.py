import subprocess
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ScriptEntrypointTests(unittest.TestCase):
    def test_script_entrypoints_import_without_module_errors(self):
        script_names = [
            "capacity_plan_report.py",
            "run_field_key_rotation.py",
            "package_compliance_evidence.py",
            "disaster_recovery_backup.py",
            "disaster_recovery_restore_drill.py",
            "sync_relational_to_mongo_snapshot.py",
            "realtime_mongo_persistence_audit.py",
            "migrate_sqlite_to_postgres.py",
            "migrate_postgres_to_postgres.py",
        ]
        for script_name in script_names:
            with self.subTest(script=script_name):
                script_path = PROJECT_ROOT / "scripts" / script_name
                result = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        (
                            "import runpy; "
                            f"runpy.run_path({str(script_path)!r}, run_name='__test__')"
                        ),
                    ],
                    cwd=str(PROJECT_ROOT),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    msg=f"{script_name} failed to import: {result.stderr or result.stdout}",
                )
