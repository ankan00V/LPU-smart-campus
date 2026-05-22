import os
import unittest
from unittest import mock

from app import recovery_ai


class RecoveryAIConfigTests(unittest.TestCase):
    def setUp(self):
        self._env_backup = dict(os.environ)
        os.environ.pop("PYTEST_CURRENT_TEST", None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)

    def _clear_recovery_provider_env(self):
        for key in list(os.environ):
            if key.startswith("RECOVERY_") or key.startswith("COPILOT_") or key.startswith("SAARTHI_"):
                os.environ.pop(key, None)
        os.environ.pop("AWS_BEARER_TOKEN_BEDROCK", None)

    def test_recovery_provider_prefers_dedicated_recovery_openrouter_key_over_copilot(self):
        self._clear_recovery_provider_env()
        os.environ["RECOVERY_OPENROUTER_API_KEY"] = "recovery-key"
        os.environ["COPILOT_OPENROUTER_API_KEY"] = "copilot-key"

        self.assertEqual(recovery_ai._recovery_llm_provider(), "openrouter")
        self.assertEqual(recovery_ai._recovery_openrouter_api_keys(), ["recovery-key"])

    def test_recovery_provider_falls_back_to_copilot_key_when_recovery_key_absent(self):
        self._clear_recovery_provider_env()
        os.environ["COPILOT_OPENROUTER_API_KEY"] = "copilot-key"

        self.assertEqual(recovery_ai._recovery_llm_provider(), "openrouter")
        self.assertEqual(recovery_ai._recovery_openrouter_api_keys(), ["copilot-key"])

    def test_recovery_provider_uses_nvidia_after_copilot_fallbacks_are_absent(self):
        self._clear_recovery_provider_env()
        os.environ["RECOVERY_NVIDIA_API_KEY"] = "nvidia-key"

        self.assertEqual(recovery_ai._recovery_llm_provider(), "nvidia")
        self.assertEqual(recovery_ai._recovery_nvidia_api_keys(), ["nvidia-key"])

    def test_saarthi_keys_are_not_used_for_recovery_provider(self):
        self._clear_recovery_provider_env()
        os.environ["SAARTHI_OPENROUTER_API_KEY"] = "saarthi-key"

        self.assertEqual(recovery_ai._recovery_llm_provider(), "")
        self.assertEqual(recovery_ai._recovery_openrouter_api_keys(), [])

    def test_student_email_generator_uses_nvidia_provider_directly(self):
        self._clear_recovery_provider_env()
        os.environ["RECOVERY_NVIDIA_API_KEY"] = "nvidia-key"
        captured = {}

        def fake_nvidia_text(**kwargs):
            captured.update(kwargs)
            return "generated with nvidia"

        with mock.patch.object(recovery_ai, "_nvidia_text", side_effect=fake_nvidia_text) as nvidia:
            body = recovery_ai.generate_recovery_student_email_body(
                student_name="Asha",
                overall_attendance_percent=71.2,
                watch_threshold=75.0,
                subject_focus_lines=["- CSE310 - Software Engineering: 62.0%"],
                risk_level="high",
                consecutive_absences=2,
                missed_remedials=1,
                next_slot_line="- Remedial slot suggested: today.",
                office_hour_line="- Faculty check-in suggested by: tomorrow.",
                study_resource_lines=[
                    "CSE310 - Software Engineering (62.0%):",
                    "  Resource: SWEBOK Guide - https://www.computer.org/education/bodies-of-knowledge/software-engineering",
                ],
            )

        self.assertEqual(body, "generated with nvidia")
        nvidia.assert_called_once()
        self.assertIn("CSE310 - Software Engineering (62.0%):", captured["user"])
        self.assertIn("SWEBOK Guide", captured["user"])

    def test_faculty_email_generator_falls_back_from_openrouter_to_nvidia(self):
        self._clear_recovery_provider_env()
        os.environ["RECOVERY_OPENROUTER_API_KEY"] = "openrouter-key"
        os.environ["RECOVERY_NVIDIA_API_KEY"] = "nvidia-key"

        with (
            mock.patch.object(recovery_ai, "_openrouter_text", return_value=None) as openrouter,
            mock.patch.object(recovery_ai, "_gemini_text", return_value=None) as gemini,
            mock.patch.object(recovery_ai, "_nvidia_text", return_value="faculty nvidia body") as nvidia,
        ):
            body = recovery_ai.generate_recovery_faculty_email_body(
                faculty_name="Dr Rao",
                student_name="Asha",
                course_code="CSE310",
                course_attendance_percent=62.0,
                overall_attendance_percent=71.2,
                risk_level="high",
                consecutive_absences=2,
            )

        self.assertEqual(body, "faculty nvidia body")
        openrouter.assert_called_once()
        gemini.assert_called_once()
        nvidia.assert_called_once()


if __name__ == "__main__":
    unittest.main()
