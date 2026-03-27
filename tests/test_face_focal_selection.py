import unittest

import numpy as np

from app.face_verification import (
    FaceVerificationConfig,
    _secondary_faces_are_ignorable_dnn,
    _select_primary_face_row_dnn,
)


def _face_row(x: float, y: float, w: float, h: float, score: float) -> np.ndarray:
    row = np.zeros((15,), dtype=np.float32)
    row[0] = float(x)
    row[1] = float(y)
    row[2] = float(w)
    row[3] = float(h)
    row[14] = float(score)
    return row


def _config() -> FaceVerificationConfig:
    return FaceVerificationConfig(
        min_similarity=0.8,
        min_consecutive_frames=5,
        max_frames=12,
        min_frame_width=280,
        min_frame_height=280,
        blur_threshold=70.0,
        min_face_area_ratio=0.09,
        max_center_offset_ratio=0.36,
        min_eye_distance_ratio=0.13,
        min_lower_texture_ratio=0.18,
        min_contrast=12.0,
        min_liveness_motion=0.018,
        min_liveness_pose_delta=0.012,
        min_liveness_yaw_range=0.012,
        min_liveness_pitch_range=0.008,
        min_liveness_texture_jitter=0.011,
        min_liveness_contrast_jitter=0.55,
        min_primary_face_dominance_ratio=3.0,
        min_valid_frame_ratio=0.85,
        min_detection_score=0.90,
        max_ignorable_secondary_face_area_ratio=0.035,
        min_secondary_face_center_offset_ratio=0.30,
    )


class FaceFocalSelectionTests(unittest.TestCase):
    def test_primary_face_selection_prefers_confident_centered_subject(self):
        # Face-1: slightly smaller but centered and higher confidence.
        # Face-2: slightly larger but off-center and lower confidence.
        rows = [
            _face_row(220, 120, 180, 220, 0.95),
            _face_row(20, 90, 200, 235, 0.86),
        ]
        primary_index, metrics = _select_primary_face_row_dnn(rows, image_w=640, image_h=480)
        self.assertEqual(primary_index, 0)
        self.assertGreater(metrics[0]["focus_score"], metrics[1]["focus_score"])

    def test_secondary_faces_ignored_when_tiny_and_off_center(self):
        rows = [
            _face_row(210, 110, 220, 250, 0.96),  # primary
            _face_row(8, 20, 34, 38, 0.91),       # tiny background face
        ]
        primary_index, metrics = _select_primary_face_row_dnn(rows, image_w=640, image_h=480)
        ok, meta = _secondary_faces_are_ignorable_dnn(metrics, primary_index=primary_index, config=_config())
        self.assertTrue(ok)
        self.assertEqual(int(meta["offending_faces"]), 0)
        self.assertGreaterEqual(int(meta["ignored_faces"]), 1)

    def test_secondary_faces_rejected_when_substantial_or_central(self):
        rows = [
            _face_row(220, 100, 210, 240, 0.96),  # primary
            _face_row(120, 120, 130, 150, 0.90),  # large enough + close to center => not ignorable
        ]
        primary_index, metrics = _select_primary_face_row_dnn(rows, image_w=640, image_h=480)
        ok, meta = _secondary_faces_are_ignorable_dnn(metrics, primary_index=primary_index, config=_config())
        self.assertFalse(ok)
        self.assertGreaterEqual(int(meta["offending_faces"]), 1)


if __name__ == "__main__":
    unittest.main()
