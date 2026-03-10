import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_script_module(script_name: str):
    script_path = PROJECT_ROOT / "scripts" / script_name
    module_name = f"test_{script_name.replace('.', '_')}"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {script_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class _Collection:
    def __init__(self, rows=None):
        self.rows = list(rows or [])
        self.inserted: list[dict] = []

    def find(self, _query):
        return list(self.rows)

    def insert_one(self, doc):
        self.inserted.append(dict(doc))
        return {"inserted_id": len(self.inserted)}


class _Mongo:
    def __init__(self):
        self.collections = {}

    def __getitem__(self, name):
        self.collections.setdefault(name, _Collection())
        return self.collections[name]


class DRScriptEvidenceTests(unittest.TestCase):
    def test_backup_script_persists_dr_backup_record(self):
        module = _load_script_module("disaster_recovery_backup.py")
        mongo = _Mongo()

        def fake_backup(out_dir, manifest):
            dump_path = out_dir / "postgres.sql"
            dump_path.write_text("-- PostgreSQL database dump\nCREATE TABLE sample(id int);\n", encoding="utf-8")
            manifest["artifacts"]["relational:postgresql"] = {
                "backend": "postgresql",
                "path": str(dump_path),
                "size_bytes": dump_path.stat().st_size,
                "sha256": hashlib.sha256(dump_path.read_bytes()).hexdigest(),
            }

        with tempfile.TemporaryDirectory() as tmp_dir:
            argv = [
                "disaster_recovery_backup.py",
                "--output-dir",
                tmp_dir,
                "--label",
                "unit-test",
                "--created-by",
                "unit",
            ]
            with (
                mock.patch.object(module, "_backup_relational_artifact", side_effect=fake_backup),
                mock.patch.object(module, "init_mongo", return_value=True),
                mock.patch.object(module, "get_mongo_db", return_value=mongo),
                mock.patch.object(module, "next_sequence", return_value=41),
                mock.patch.object(sys, "argv", argv),
            ):
                module.main()

        inserted = mongo["dr_backups"].inserted
        self.assertEqual(len(inserted), 1)
        self.assertEqual(inserted[0]["id"], 41)
        self.assertEqual(inserted[0]["created_by_email"], "unit")
        self.assertIn("relational:postgresql", inserted[0]["manifest"]["artifacts"])

    def test_restore_drill_script_persists_drill_record(self):
        module = _load_script_module("disaster_recovery_restore_drill.py")
        mongo = _Mongo()

        with tempfile.TemporaryDirectory() as tmp_dir:
            backup_dir = Path(tmp_dir) / "20260308T000000Z-unit"
            backup_dir.mkdir(parents=True, exist_ok=True)
            dump_path = backup_dir / "postgres.sql"
            dump_path.write_text("-- PostgreSQL database dump\nCREATE TABLE sample(id int);\n", encoding="utf-8")
            manifest = {
                "artifacts": {
                    "relational:postgresql": {
                        "path": str(dump_path),
                        "sha256": hashlib.sha256(dump_path.read_bytes()).hexdigest(),
                    }
                }
            }
            (backup_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            argv = [
                "disaster_recovery_restore_drill.py",
                "--backups-dir",
                tmp_dir,
                "--backup-id",
                backup_dir.name,
                "--executed-by",
                "unit",
            ]
            with (
                mock.patch.object(module, "init_mongo", return_value=True),
                mock.patch.object(module, "get_mongo_db", return_value=mongo),
                mock.patch.object(module, "next_sequence", return_value=73),
                mock.patch.object(sys, "argv", argv),
            ):
                module.main()

        inserted = mongo["dr_restore_drills"].inserted
        self.assertEqual(len(inserted), 1)
        self.assertEqual(inserted[0]["id"], 73)
        self.assertEqual(inserted[0]["executed_by_email"], "unit")
        self.assertTrue(inserted[0]["manifest_integrity_ok"])
        self.assertTrue(inserted[0]["target_met"])


if __name__ == "__main__":
    unittest.main()
