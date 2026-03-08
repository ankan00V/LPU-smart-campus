import hashlib
import tempfile
import unittest
from pathlib import Path

from app.routers.enterprise import _verify_manifest_artifacts


class EnterpriseDRIntegrityTests(unittest.TestCase):
    def test_manifest_integrity_verifies_checksums(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            backup = Path(tmp_dir)
            artifact = backup / "sample.txt"
            artifact.write_text("hello-dr", encoding="utf-8")
            manifest = {
                "artifacts": {
                    "sample": {
                        "path": str(artifact),
                        "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                    }
                }
            }
            result = _verify_manifest_artifacts(backup, manifest)
            self.assertEqual(result["total_checked"], 1)
            self.assertEqual(result["verified"], 1)
            self.assertEqual(result["missing"], 0)
            self.assertEqual(result["mismatched"], 0)

    def test_manifest_integrity_detects_missing_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            backup = Path(tmp_dir)
            missing = backup / "missing.txt"
            manifest = {
                "artifacts": {
                    "missing": {
                        "path": str(missing),
                        "sha256": hashlib.sha256(b"none").hexdigest(),
                    }
                }
            }
            result = _verify_manifest_artifacts(backup, manifest)
            self.assertEqual(result["total_checked"], 1)
            self.assertEqual(result["verified"], 0)
            self.assertEqual(result["missing"], 1)


if __name__ == "__main__":
    unittest.main()
