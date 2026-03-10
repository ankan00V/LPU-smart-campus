import importlib
import os
import unittest
from unittest import mock

import app.face_verification as face_verification


class FaceVerificationConfigTests(unittest.TestCase):
    def test_runtime_config_respects_env_similarity_threshold(self):
        with mock.patch.dict(
            os.environ,
            {
                "FACE_MATCH_PASS_THRESHOLD": "0.78",
                "FACE_MATCH_MIN_SIMILARITY": "0.78",
            },
            clear=False,
        ):
            reloaded = importlib.reload(face_verification)
            self.assertAlmostEqual(reloaded._load_config().min_similarity, 0.78, places=6)

        importlib.reload(face_verification)


if __name__ == "__main__":
    unittest.main()
