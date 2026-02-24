import unittest

import numpy as np

from app.face_verification import FaceVerificationConfig, evaluate_embedding_sequence, evaluate_liveness_sequence


def _vec(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    value = rng.normal(size=64).astype(np.float32)
    norm = np.linalg.norm(value)
    if norm < 1e-8:
        return value
    return value / norm


class FaceVerificationSequenceTests(unittest.TestCase):
    def test_rejects_wrong_person_even_with_multiple_frames(self):
        profile = _vec(1)
        wrong = [_vec(100 + idx) for idx in range(6)]
        result = evaluate_embedding_sequence(
            profile,
            wrong,
            min_similarity=0.82,
            min_consecutive_frames=5,
        )
        self.assertFalse(result["match"])
        self.assertLess(result["confidence"], 0.82)

    def test_requires_consecutive_frames(self):
        profile = _vec(2)
        near = profile.copy()
        far = _vec(999)
        # Similarity high for 3 frames, then broken, then 2 more. Never reaches 5 consecutive.
        frames = [near, near, near, far, near, near]
        result = evaluate_embedding_sequence(
            profile,
            frames,
            min_similarity=0.82,
            min_consecutive_frames=5,
        )
        self.assertFalse(result["match"])
        self.assertLess(result["best_streak"], 5)

    def test_accepts_only_after_five_strong_frames(self):
        profile = _vec(3)
        frames = [profile.copy() for _ in range(5)]
        result = evaluate_embedding_sequence(
            profile,
            frames,
            min_similarity=0.82,
            min_consecutive_frames=5,
        )
        self.assertTrue(result["match"])
        self.assertGreaterEqual(result["confidence"], 0.99)
        self.assertEqual(result["best_streak"], 5)

    def test_requires_majority_match_across_live_frames(self):
        profile = _vec(42)
        matching = [profile.copy() for _ in range(5)]
        non_matching = [_vec(500 + idx) for idx in range(5)]
        frames = matching + non_matching
        result = evaluate_embedding_sequence(
            profile,
            frames,
            min_similarity=0.82,
            min_consecutive_frames=5,
        )
        self.assertFalse(result["match"])
        self.assertFalse(result["majority_met"])
        self.assertEqual(result["accepted_frames"], 5)
        self.assertEqual(result["majority_required"], 6)

    def test_spoof_or_invalid_frames_reset_streak(self):
        profile = _vec(4)
        frames = [profile.copy() for _ in range(6)]
        valid_flags = [True, True, False, True, True, True]
        reasons = ["", "", "Face appears covered", "", "", ""]
        result = evaluate_embedding_sequence(
            profile,
            frames,
            min_similarity=0.82,
            min_consecutive_frames=5,
            frame_valid_flags=valid_flags,
            frame_reasons=reasons,
        )
        self.assertFalse(result["match"])
        self.assertLess(result["best_streak"], 5)

    def test_threshold_blocks_borderline_similarity(self):
        profile = _vec(5)
        frames = [profile * 0.55 + _vec(6) * 0.45 for _ in range(5)]
        result = evaluate_embedding_sequence(
            profile,
            frames,
            min_similarity=0.95,
            min_consecutive_frames=5,
        )
        self.assertFalse(result["match"])

    def test_embedding_sequence_supports_multiple_profile_embeddings(self):
        profile_refs = [_vec(7), _vec(8)]
        frames = [_vec(8) for _ in range(5)]
        result = evaluate_embedding_sequence(
            profile_refs,
            frames,
            min_similarity=0.82,
            min_consecutive_frames=5,
        )
        self.assertTrue(result["match"])
        self.assertGreaterEqual(result["confidence"], 0.95)

    def test_liveness_rejects_static_sequence(self):
        config = FaceVerificationConfig(
            min_similarity=0.78,
            min_consecutive_frames=5,
            max_frames=8,
            min_frame_width=280,
            min_frame_height=280,
            blur_threshold=110.0,
            min_face_area_ratio=0.09,
            max_center_offset_ratio=0.34,
            min_eye_distance_ratio=0.17,
            min_lower_texture_ratio=0.26,
            min_contrast=18.0,
            min_liveness_motion=0.028,
            min_liveness_pose_delta=0.02,
            min_liveness_yaw_range=0.02,
            min_liveness_pitch_range=0.012,
            min_liveness_texture_jitter=0.012,
            min_liveness_contrast_jitter=0.9,
            min_primary_face_dominance_ratio=2.6,
        )
        static_frames = [
            {
                "center_x": 0.51,
                "center_y": 0.49,
                "yaw_proxy": 0.0,
                "pitch_proxy": 0.0,
                "texture_ratio": 0.31,
                "contrast": 30.0,
            }
            for _ in range(5)
        ]
        liveness = evaluate_liveness_sequence(static_frames, config=config, min_frames=5)
        self.assertFalse(liveness["ok"])
        self.assertIn("liveness check failed", liveness["reason"].lower())

    def test_liveness_accepts_natural_head_movement(self):
        config = FaceVerificationConfig(
            min_similarity=0.78,
            min_consecutive_frames=5,
            max_frames=8,
            min_frame_width=280,
            min_frame_height=280,
            blur_threshold=110.0,
            min_face_area_ratio=0.09,
            max_center_offset_ratio=0.34,
            min_eye_distance_ratio=0.17,
            min_lower_texture_ratio=0.26,
            min_contrast=18.0,
            min_liveness_motion=0.028,
            min_liveness_pose_delta=0.02,
            min_liveness_yaw_range=0.02,
            min_liveness_pitch_range=0.012,
            min_liveness_texture_jitter=0.012,
            min_liveness_contrast_jitter=0.9,
            min_primary_face_dominance_ratio=2.6,
        )
        live_frames = [
            {
                "center_x": 0.47 + (idx * 0.01),
                "center_y": 0.49 + (idx * 0.004),
                "yaw_proxy": -0.02 + (idx * 0.01),
                "pitch_proxy": -0.01 + (idx * 0.004),
                "texture_ratio": 0.27 + (idx * 0.015),
                "contrast": 27.0 + (idx * 1.1),
            }
            for idx in range(5)
        ]
        liveness = evaluate_liveness_sequence(live_frames, config=config, min_frames=5)
        self.assertTrue(liveness["ok"])

    def test_liveness_rejects_if_directional_pose_change_missing(self):
        config = FaceVerificationConfig(
            min_similarity=0.78,
            min_consecutive_frames=5,
            max_frames=8,
            min_frame_width=280,
            min_frame_height=280,
            blur_threshold=110.0,
            min_face_area_ratio=0.09,
            max_center_offset_ratio=0.34,
            min_eye_distance_ratio=0.17,
            min_lower_texture_ratio=0.26,
            min_contrast=18.0,
            min_liveness_motion=0.028,
            min_liveness_pose_delta=0.02,
            min_liveness_yaw_range=0.02,
            min_liveness_pitch_range=0.012,
            min_liveness_texture_jitter=0.012,
            min_liveness_contrast_jitter=0.9,
            min_primary_face_dominance_ratio=2.6,
        )
        frames_without_pose_change = [
            {
                "center_x": 0.45 + (idx * 0.015),
                "center_y": 0.50 + (idx * 0.008),
                "yaw_proxy": 0.0,
                "pitch_proxy": 0.0,
                "texture_ratio": 0.29 + (idx * 0.005),
                "contrast": 28.0 + (idx * 0.4),
            }
            for idx in range(5)
        ]
        liveness = evaluate_liveness_sequence(frames_without_pose_change, config=config, min_frames=5)
        self.assertFalse(liveness["ok"])
        self.assertIn("challenge", liveness["reason"].lower())


if __name__ == "__main__":
    unittest.main()
