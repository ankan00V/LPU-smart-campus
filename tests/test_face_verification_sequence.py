import unittest
from unittest import mock

import numpy as np

from app.face_verification import (
    FaceVerificationConfig,
    _relaxed_attendance_verification_config,
    _should_attempt_arcface_fallback,
    _verify_face_sequence_dnn,
    evaluate_embedding_sequence,
    evaluate_liveness_sequence,
)


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

    def test_relaxed_attendance_liveness_accepts_smaller_but_real_motion(self):
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
        smaller_live_frames = [
            {
                "center_x": 0.48 + (idx * 0.003),
                "center_y": 0.49 + (idx * 0.001),
                "yaw_proxy": -0.008 + (idx * 0.004),
                "pitch_proxy": -0.004 + (idx * 0.002),
                "texture_ratio": 0.29 + (idx * 0.008),
                "contrast": 28.0 + (idx * 0.8),
            }
            for idx in range(5)
        ]
        strict_liveness = evaluate_liveness_sequence(smaller_live_frames, config=config, min_frames=5)
        relaxed_liveness = evaluate_liveness_sequence(
            smaller_live_frames,
            config=_relaxed_attendance_verification_config(config),
            min_frames=4,
        )
        self.assertFalse(strict_liveness["ok"])
        self.assertTrue(relaxed_liveness["ok"])

    def test_arcface_fallback_gate_triggers_only_on_nonfatal_eight_frame_failure(self):
        with (
            mock.patch("app.face_verification._arcface_fallback_enabled", return_value=True),
            mock.patch("app.face_verification._env_int", return_value=8),
        ):
            self.assertTrue(
                _should_attempt_arcface_fallback(
                    total_frames=8,
                    match=False,
                    liveness_ok=True,
                    fatal_reason="",
                )
            )
            self.assertFalse(
                _should_attempt_arcface_fallback(
                    total_frames=7,
                    match=False,
                    liveness_ok=True,
                    fatal_reason="",
                )
            )
            self.assertFalse(
                _should_attempt_arcface_fallback(
                    total_frames=8,
                    match=True,
                    liveness_ok=True,
                    fatal_reason="",
                )
            )
            self.assertFalse(
                _should_attempt_arcface_fallback(
                    total_frames=8,
                    match=False,
                    liveness_ok=False,
                    fatal_reason="",
                )
            )
            self.assertFalse(
                _should_attempt_arcface_fallback(
                    total_frames=8,
                    match=False,
                    liveness_ok=True,
                    fatal_reason="Face not centered",
                )
            )

    def test_dnn_verification_promotes_arcface_fallback_success(self):
        frame_bgr = np.zeros((320, 320, 3), dtype=np.uint8)
        base_audit = [
            {
                "frame_index": idx,
                "timestamp_utc": f"2026-03-10T10:00:0{idx}Z",
                "confidence": 0.71,
                "accepted": False,
                "reason": "Face not recognized",
            }
            for idx in range(8)
        ]
        fallback_audit = [
            {
                "frame_index": idx,
                "timestamp_utc": f"2026-03-10T10:00:1{idx}Z",
                "confidence": 0.90,
                "accepted": True,
                "reason": "ok",
            }
            for idx in range(8)
        ]
        profile_bundle = {
            "ok": True,
            "embedding": _vec(10),
            "center_x": 0.5,
            "center_y": 0.5,
            "yaw_proxy": 0.0,
            "pitch_proxy": 0.0,
            "texture_ratio": 0.3,
            "contrast": 24.0,
        }
        frame_bundle = {
            "ok": True,
            "embedding": _vec(11),
            "center_x": 0.5,
            "center_y": 0.5,
            "yaw_proxy": 0.01,
            "pitch_proxy": 0.01,
            "texture_ratio": 0.32,
            "contrast": 24.5,
        }

        with (
            mock.patch("app.face_verification._decode_data_url_to_bgr", return_value=frame_bgr) as mock_decode,
            mock.patch(
                "app.face_verification._extract_embedding_bundle_dnn",
                side_effect=[profile_bundle] + [frame_bundle.copy() for _ in range(8)],
            ) as mock_extract,
            mock.patch(
                "app.face_verification.evaluate_embedding_sequence",
                return_value={
                    "match": False,
                    "confidence": 0.71,
                    "best_streak": 2,
                    "required_streak": 5,
                    "accepted_frames": 3,
                    "valid_frames": 8,
                    "total_frames": 8,
                    "majority_required": 5,
                    "majority_met": False,
                    "frame_audit": base_audit,
                },
            ),
            mock.patch(
                "app.face_verification.evaluate_liveness_sequence",
                return_value={"ok": True, "reason": "ok", "metrics": {}},
            ),
            mock.patch("app.face_verification._should_attempt_arcface_fallback", return_value=True) as mock_should_fallback,
            mock.patch(
                "app.face_verification._verify_face_sequence_arcface_fallback",
                return_value={
                    "available": True,
                    "match": True,
                    "confidence": 0.92,
                    "engine": "arcface-onnx-buffalo_l-fallback-v1",
                    "reason": "ArcFace fallback verified",
                    "consecutive_frames_matched": 5,
                    "accepted_frames": 6,
                    "total_frames": 8,
                    "majority_required": 5,
                    "frame_audit": fallback_audit,
                    "liveness": {"ok": True, "reason": "ok", "metrics": {}},
                },
            ) as mock_arcface,
        ):
            verdict = _verify_face_sequence_dnn(
                "data:image/jpeg;base64,PROFILE",
                ["data:image/jpeg;base64,FRAME"] * 8,
                subject_label="demo.student@example.com",
                min_consecutive_frames=5,
                profile_template=None,
            )

        self.assertTrue(verdict["match"])
        self.assertAlmostEqual(verdict["confidence"], 0.92, places=6)
        self.assertEqual(verdict["engine"], "arcface-onnx-buffalo_l-fallback-v1")
        self.assertEqual(verdict["reason"], "ArcFace fallback verified")
        self.assertTrue(verdict["fallback_attempted"])
        self.assertTrue(verdict["fallback_available"])
        self.assertIsNone(verdict["fallback_reason"])
        self.assertEqual(len(verdict["frame_audit"]), 8)
        self.assertGreaterEqual(mock_decode.call_count, 9)
        self.assertGreaterEqual(mock_extract.call_count, 9)
        mock_should_fallback.assert_called_once()
        mock_arcface.assert_called_once()


if __name__ == "__main__":
    unittest.main()
