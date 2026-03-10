import io
import json
import os
import tempfile
import unittest
from datetime import date, datetime
from unittest import mock
from urllib.error import HTTPError

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.attendance_recovery import evaluate_attendance_recovery
from app.routers.attendance import (
    get_student_attendance_aggregate,
    get_student_attendance_history,
    get_student_weekly_timetable,
)
from app.saarthi_service import (
    SAARTHI_ATTENDANCE_MINUTES,
    SAARTHI_COURSE_CODE,
    SAARTHI_IDENTITY_INTRO,
    SAARTHI_LLM_FREQUENCY_PENALTY,
    SAARTHI_LLM_PRESENCE_PENALTY,
    SAARTHI_LLM_TEMPERATURE,
    SAARTHI_LLM_TOP_P,
    create_saarthi_turn,
    ensure_saarthi_bundle,
    materialize_saarthi_attendance,
    start_new_saarthi_chat,
)


class SaarthiAttendanceTests(unittest.TestCase):
    def setUp(self):
        self._env_keys = [
            "APP_SECRETS_PROVIDER",
            "APP_SECRETS_FILE",
            "SAARTHI_LLM_PROVIDER",
            "SAARTHI_LLM_REQUIRED",
            "SAARTHI_LLM_MODEL",
            "SAARTHI_LLM_TIMEOUT_SECONDS",
            "GEMINI_API_KEYS_JSON",
            "GEMINI_API_KEY",
            "OPENROUTER_API_KEY",
        ]
        self._env_backup = {key: os.environ.get(key) for key in self._env_keys}
        for key in self._env_keys:
            os.environ.pop(key, None)
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        SessionLocal = sessionmaker(bind=self.engine)
        self.db = SessionLocal()
        self._seed()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()
        for key, value in self._env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _seed(self):
        self.student = models.Student(
            id=1,
            name="Saarthi Student",
            email="saarthi.student@example.com",
            registration_number="22BCS5001",
            section="P132",
            department="CSE",
            semester=6,
        )
        self.db.add(self.student)
        self.db.add(
            models.AuthUser(
                id=9002,
                email="admin@example.com",
                password_hash="x",
                role=models.UserRole.ADMIN,
                student_id=None,
                faculty_id=None,
                is_active=True,
            )
        )
        self.db.commit()

    @staticmethod
    def _student_user() -> models.AuthUser:
        return models.AuthUser(
            id=9001,
            email="saarthi.student@example.com",
            password_hash="x",
            role=models.UserRole.STUDENT,
            student_id=1,
            faculty_id=None,
            is_active=True,
        )

    def test_sunday_chat_awards_single_hour_credit_once(self):
        sunday_dt = datetime(2026, 3, 8, 10, 30, 0)

        first_turn = create_saarthi_turn(
            self.db,
            student=self.student,
            message="I need help managing stress this week.",
            current_dt=sunday_dt,
            academic_start=date(2026, 3, 2),
        )
        second_turn = create_saarthi_turn(
            self.db,
            student=self.student,
            message="I am back with one more follow-up.",
            current_dt=datetime(2026, 3, 8, 19, 45, 0),
            academic_start=date(2026, 3, 2),
        )
        self.db.commit()

        bundle = ensure_saarthi_bundle(self.db, student_id=int(self.student.id))
        self.assertTrue(first_turn["attendance_awarded_now"])
        self.assertFalse(second_turn["attendance_awarded_now"])

        records = (
            self.db.query(models.AttendanceRecord)
            .filter(
                models.AttendanceRecord.student_id == int(self.student.id),
                models.AttendanceRecord.course_id == int(bundle.course.id),
            )
            .all()
        )
        events = (
            self.db.query(models.AttendanceEvent)
            .filter(
                models.AttendanceEvent.student_id == int(self.student.id),
                models.AttendanceEvent.course_id == int(bundle.course.id),
            )
            .all()
        )
        session = self.db.query(models.SaarthiSession).one()
        messages = self.db.query(models.SaarthiMessage).all()

        self.assertEqual(len(records), 1)
        self.assertEqual(len(events), 1)
        self.assertEqual(records[0].attendance_date, date(2026, 3, 8))
        self.assertEqual(records[0].status, models.AttendanceStatus.PRESENT)
        self.assertEqual(records[0].source, "saarthi-weekly-credit")
        self.assertEqual(session.attendance_credit_minutes, SAARTHI_ATTENDANCE_MINUTES)
        self.assertIsNotNone(session.attendance_marked_at)
        self.assertEqual(len(messages), 4)

        aggregate = get_student_attendance_aggregate(
            db=self.db,
            current_user=self._student_user(),
        )
        con111 = next((row for row in aggregate.courses if row.course_code == SAARTHI_COURSE_CODE), None)
        self.assertIsNotNone(con111)
        self.assertEqual(con111.attended_classes, 1)
        self.assertEqual(con111.delivered_classes, 1)
        self.assertEqual(con111.attendance_percent, 100.0)

    def test_non_sunday_chat_does_not_award_attendance(self):
        monday_dt = datetime(2026, 3, 9, 11, 0, 0)

        out = create_saarthi_turn(
            self.db,
            student=self.student,
            message="I want to talk about exams before Sunday.",
            current_dt=monday_dt,
            academic_start=date(2026, 3, 9),
        )
        self.db.commit()

        bundle = ensure_saarthi_bundle(self.db, student_id=int(self.student.id))
        records = (
            self.db.query(models.AttendanceRecord)
            .filter(
                models.AttendanceRecord.student_id == int(self.student.id),
                models.AttendanceRecord.course_id == int(bundle.course.id),
            )
            .all()
        )
        session = self.db.query(models.SaarthiSession).one()
        messages = self.db.query(models.SaarthiMessage).all()

        self.assertFalse(out["attendance_awarded_now"])
        self.assertEqual(len(records), 0)
        self.assertIsNone(session.attendance_marked_at)
        self.assertEqual(session.attendance_credit_minutes, 0)
        self.assertEqual(len(messages), 2)

    def test_first_reply_uses_identity_intro_and_reflective_question_without_forcing_attendance(self):
        out = create_saarthi_turn(
            self.db,
            student=self.student,
            message="I feel overwhelmed with deadlines and I can't focus.",
            current_dt=datetime(2026, 3, 10, 18, 15, 0),
            academic_start=date(2026, 3, 9),
        )

        self.assertTrue(out["reply"].startswith(SAARTHI_IDENTITY_INTRO))
        self.assertIn("That sounds like a lot to carry at once.", out["reply"])
        self.assertIn("What part of this feels heaviest right now?", out["reply"])
        self.assertNotIn("CON111", out["reply"])

    def test_new_chat_resets_visible_context_for_next_reply(self):
        create_saarthi_turn(
            self.db,
            student=self.student,
            message="I need help with stress this week.",
            current_dt=datetime(2026, 3, 10, 12, 0, 0),
            academic_start=date(2026, 3, 9),
        )
        start_new_saarthi_chat(
            self.db,
            student_id=int(self.student.id),
            current_dt=datetime(2026, 3, 10, 12, 10, 0),
        )
        out = create_saarthi_turn(
            self.db,
            student=self.student,
            message="I want to start fresh and talk about motivation.",
            current_dt=datetime(2026, 3, 10, 12, 11, 0),
            academic_start=date(2026, 3, 9),
        )

        rows = self.db.query(models.SaarthiMessage).order_by(models.SaarthiMessage.id.asc()).all()
        self.assertTrue(any(str(row.sender_role) == "system" for row in rows))
        self.assertTrue(out["reply"].startswith(SAARTHI_IDENTITY_INTRO))

    def test_weekly_timetable_includes_all_day_saarthi_slot_and_auto_enrolls_student(self):
        payload = get_student_weekly_timetable(
            week_start=date(2026, 3, 2),
            db=self.db,
            current_user=self._student_user(),
        )

        saarthi_row = next((row for row in payload.classes if row.course_code == SAARTHI_COURSE_CODE), None)
        self.assertIsNotNone(saarthi_row)
        self.assertEqual(saarthi_row.class_kind, "saarthi")
        self.assertEqual(saarthi_row.class_date, date(2026, 3, 8))
        self.assertEqual(str(saarthi_row.start_time), "00:00:00")
        self.assertEqual(str(saarthi_row.end_time), "23:59:00")
        self.assertEqual(saarthi_row.attendance_window_minutes, 24 * 60)
        self.assertEqual(saarthi_row.classroom_label, "Saarthi Studio | Sunday all-day window")

        bundle = ensure_saarthi_bundle(self.db, student_id=int(self.student.id))
        enrollment = (
            self.db.query(models.Enrollment)
            .filter(
                models.Enrollment.student_id == int(self.student.id),
                models.Enrollment.course_id == int(bundle.course.id),
            )
            .first()
        )
        self.assertIsNotNone(enrollment)

    def test_timetable_marks_saarthi_present_after_sunday_credit(self):
        create_saarthi_turn(
            self.db,
            student=self.student,
            message="I need a Sunday Saarthi check-in.",
            current_dt=datetime(2026, 3, 8, 9, 15, 0),
            academic_start=date(2026, 3, 2),
        )
        self.db.commit()

        payload = get_student_weekly_timetable(
            week_start=date(2026, 3, 2),
            db=self.db,
            current_user=self._student_user(),
        )

        saarthi_row = next((row for row in payload.classes if row.course_code == SAARTHI_COURSE_CODE), None)
        self.assertIsNotNone(saarthi_row)
        self.assertEqual(saarthi_row.class_kind, "saarthi")
        self.assertEqual(saarthi_row.attendance_status, "present")

    def test_missed_past_sunday_materializes_absent_record_in_aggregate_and_history(self):
        materialize_saarthi_attendance(
            self.db,
            student_id=int(self.student.id),
            academic_start=date(2026, 3, 2),
            today=date(2026, 3, 9),
        )
        self.db.commit()

        aggregate = get_student_attendance_aggregate(
            db=self.db,
            current_user=self._student_user(),
        )
        history = get_student_attendance_history(
            limit=20,
            db=self.db,
            current_user=self._student_user(),
        )

        con111 = next((row for row in aggregate.courses if row.course_code == SAARTHI_COURSE_CODE), None)
        self.assertIsNotNone(con111)
        self.assertEqual(con111.attended_classes, 0)
        self.assertEqual(con111.delivered_classes, 1)
        self.assertEqual(con111.attendance_percent, 0.0)

        saarthi_rows = [row for row in history.records if row.course_code == SAARTHI_COURSE_CODE]
        self.assertEqual(len(saarthi_rows), 1)
        self.assertEqual(saarthi_rows[0].class_date, date(2026, 3, 8))
        self.assertEqual(saarthi_rows[0].status, models.AttendanceStatus.ABSENT)
        self.assertEqual(saarthi_rows[0].source, "saarthi-mandatory-missed")

    def test_missed_past_sunday_enqueues_student_and_admin_notifications_once_after_commit(self):
        with mock.patch("app.workers.enqueue_notification", return_value="inline-thread") as mocked_enqueue:
            materialize_saarthi_attendance(
                self.db,
                student_id=int(self.student.id),
                academic_start=date(2026, 3, 2),
                today=date(2026, 3, 9),
            )
            self.assertEqual(mocked_enqueue.call_count, 0)
            self.db.commit()

        self.assertEqual(mocked_enqueue.call_count, 2)
        payloads = [call.args[0] for call in mocked_enqueue.call_args_list]
        self.assertCountEqual(
            [payload["type"] for payload in payloads],
            ["saarthi_missed_student_alert", "saarthi_missed_admin_alert"],
        )
        self.assertEqual({payload["recipient_email"] for payload in payloads}, {"saarthi.student@example.com", "admin@example.com"})

        with self.db.begin():
            self.db.add(
                models.NotificationLog(
                    student_id=int(self.student.id),
                    message="saarthi-missed:1:2026-03-08",
                    channel="saarthi-missed-student",
                    sent_to="saarthi.student@example.com",
                )
            )
            self.db.add(
                models.NotificationLog(
                    student_id=int(self.student.id),
                    message="saarthi-missed:1:2026-03-08",
                    channel="saarthi-missed-admin",
                    sent_to="admin@example.com",
                )
            )

        with mock.patch("app.workers.enqueue_notification", return_value="inline-thread") as mocked_enqueue:
            materialize_saarthi_attendance(
                self.db,
                student_id=int(self.student.id),
                academic_start=date(2026, 3, 2),
                today=date(2026, 3, 9),
            )
            self.db.commit()

        mocked_enqueue.assert_not_called()

    def test_saarthi_course_is_excluded_from_recovery_automation(self):
        bundle = materialize_saarthi_attendance(
            self.db,
            student_id=int(self.student.id),
            academic_start=date(2026, 3, 2),
            today=date(2026, 3, 9),
        )
        self.db.commit()

        plan = evaluate_attendance_recovery(
            self.db,
            student_id=int(self.student.id),
            course_id=int(bundle.course.id),
        )

        self.assertIsNone(plan)

    def test_configured_gemini_llm_reply_is_used_when_available(self):
        class DummyResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(
                    {
                        "candidates": [
                            {
                                "content": {
                                    "parts": [{"text": "Live Gemini counselling reply."}],
                                }
                            }
                        ]
                    }
                ).encode("utf-8")

        with mock.patch.dict(
            os.environ,
            {
                "SAARTHI_LLM_PROVIDER": "gemini",
                "SAARTHI_LLM_REQUIRED": "true",
                "SAARTHI_LLM_MODEL": "gemini-2.5-flash",
                "GEMINI_API_KEY": "test-key",
            },
            clear=False,
        ), mock.patch("app.saarthi_service.urllib_request.urlopen", return_value=DummyResponse()):
            out = create_saarthi_turn(
                self.db,
                student=self.student,
                message="I need help planning this week.",
                current_dt=datetime(2026, 3, 8, 9, 0, 0),
                academic_start=date(2026, 3, 2),
            )

        self.assertTrue(out["reply"].startswith("Live Gemini counselling reply."))
        self.assertIn("?", out["reply"])

    def test_gemini_request_contains_companion_system_instruction(self):
        captured_body: dict[str, object] = {}

        class DummyResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(
                    {
                        "candidates": [
                            {
                                "content": {
                                    "parts": [{"text": "Live Gemini counselling reply."}],
                                }
                            }
                        ]
                    }
                ).encode("utf-8")

        def fake_urlopen(request, timeout=0):
            del timeout
            captured_body.update(json.loads(request.data.decode("utf-8")))
            return DummyResponse()

        with mock.patch.dict(
            os.environ,
            {
                "SAARTHI_LLM_PROVIDER": "gemini",
                "SAARTHI_LLM_REQUIRED": "true",
                "SAARTHI_LLM_MODEL": "gemini-2.5-flash",
                "GEMINI_API_KEY": "test-key",
            },
            clear=False,
        ), mock.patch("app.saarthi_service.urllib_request.urlopen", side_effect=fake_urlopen):
            out = create_saarthi_turn(
                self.db,
                student=self.student,
                message="I need help planning this week.",
                current_dt=datetime(2026, 3, 8, 9, 0, 0),
                academic_start=date(2026, 3, 2),
            )

        self.assertTrue(out["reply"].startswith("Live Gemini counselling reply."))
        self.assertIn("?", out["reply"])
        system_instruction = (
            captured_body.get("system_instruction", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
        user_prompt = (
            captured_body.get("contents", [{}])[0]
            .get("parts", [{}])[0]
            .get("text", "")
        )
        generation_config = captured_body.get("generationConfig", {})
        self.assertIn("wise, understanding senior", system_instruction)
        self.assertIn("4 to 8 sentences", system_instruction)
        self.assertEqual(generation_config.get("temperature"), SAARTHI_LLM_TEMPERATURE)
        self.assertEqual(generation_config.get("topP"), SAARTHI_LLM_TOP_P)
        self.assertNotIn("presencePenalty", generation_config)
        self.assertNotIn("frequencyPenalty", generation_config)
        self.assertIn("Detected emotional tone:", user_prompt)
        self.assertIn(SAARTHI_IDENTITY_INTRO, user_prompt)
        self.assertIn("thoughtful follow-up question", user_prompt)
        self.assertIn("mandatory once every week on Sunday", user_prompt)
        self.assertIn("one hour of attendance is credited", user_prompt)

    def test_gemini_rotates_to_next_key_on_quota_exhaustion(self):
        class DummyResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(
                    {
                        "candidates": [
                            {
                                "content": {
                                    "parts": [{"text": "Recovered Gemini counselling reply."}],
                                }
                            }
                        ]
                    }
                ).encode("utf-8")

        seen_urls: list[str] = []
        seen_keys: list[str | None] = []

        def fake_urlopen(request, timeout=0):
            seen_urls.append(request.full_url)
            seen_keys.append(request.headers.get("X-goog-api-key"))
            if len(seen_urls) == 1:
                raise HTTPError(
                    request.full_url,
                    429,
                    "Too Many Requests",
                    hdrs=None,
                    fp=io.BytesIO(
                        json.dumps(
                            {
                                "error": {
                                    "status": "RESOURCE_EXHAUSTED",
                                    "message": "Quota exhausted for the current API key.",
                                }
                            }
                        ).encode("utf-8")
                    ),
                )
            return DummyResponse()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            tmp.write(json.dumps({"GEMINI_API_KEYS_JSON": json.dumps(["key-one", "key-two"])}))
            secret_file = tmp.name
        try:
            with mock.patch.dict(
                os.environ,
                {
                    "APP_SECRETS_PROVIDER": "file",
                    "APP_SECRETS_FILE": secret_file,
                    "SAARTHI_LLM_PROVIDER": "gemini",
                    "SAARTHI_LLM_REQUIRED": "true",
                    "SAARTHI_LLM_MODEL": "gemini-2.5-flash",
                },
                clear=False,
            ), mock.patch("app.saarthi_service.urllib_request.urlopen", side_effect=fake_urlopen):
                out = create_saarthi_turn(
                    self.db,
                    student=self.student,
                    message="I need help planning this week.",
                    current_dt=datetime(2026, 3, 8, 9, 0, 0),
                    academic_start=date(2026, 3, 2),
                )
        finally:
            try:
                os.unlink(secret_file)
            except FileNotFoundError:
                pass

        self.assertTrue(out["reply"].startswith("Recovered Gemini counselling reply."))
        self.assertIn("?", out["reply"])
        self.assertEqual(len(seen_urls), 2)
        self.assertTrue(seen_urls[0].endswith(":generateContent"))
        self.assertEqual(seen_keys, ["key-one", "key-two"])

    def test_gemini_exhaustion_falls_back_to_openrouter_last(self):
        class OpenRouterResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(
                    {
                        "choices": [
                            {
                                "message": {
                                    "content": "OpenRouter final fallback reply.",
                                }
                            }
                        ]
                    }
                ).encode("utf-8")

        seen_urls: list[str] = []
        seen_keys: list[str | None] = []

        def fake_urlopen(request, timeout=0):
            seen_urls.append(request.full_url)
            seen_keys.append(request.headers.get("X-goog-api-key"))
            if "generativelanguage.googleapis.com" in request.full_url:
                raise HTTPError(
                    request.full_url,
                    429,
                    "Too Many Requests",
                    hdrs=None,
                    fp=io.BytesIO(
                        json.dumps(
                            {
                                "error": {
                                    "status": "RESOURCE_EXHAUSTED",
                                    "message": "Quota exhausted for the current API key.",
                                }
                            }
                        ).encode("utf-8")
                    ),
                )
            return OpenRouterResponse()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            tmp.write(
                json.dumps(
                    {
                        "GEMINI_API_KEYS_JSON": json.dumps(["key-one", "key-two"]),
                        "OPENROUTER_API_KEY": "test-openrouter-key",
                    }
                )
            )
            secret_file = tmp.name
        try:
            with mock.patch.dict(
                os.environ,
                {
                    "APP_SECRETS_PROVIDER": "file",
                    "APP_SECRETS_FILE": secret_file,
                    "SAARTHI_LLM_PROVIDER": "gemini",
                    "SAARTHI_LLM_REQUIRED": "true",
                    "SAARTHI_LLM_MODEL": "gemini-2.5-flash",
                },
                clear=False,
            ), mock.patch("app.saarthi_service.urllib_request.urlopen", side_effect=fake_urlopen):
                out = create_saarthi_turn(
                    self.db,
                    student=self.student,
                    message="I need help planning this week.",
                    current_dt=datetime(2026, 3, 8, 9, 0, 0),
                    academic_start=date(2026, 3, 2),
                )
        finally:
            try:
                os.unlink(secret_file)
            except FileNotFoundError:
                pass

        self.assertTrue(out["reply"].startswith("OpenRouter final fallback reply."))
        self.assertIn("?", out["reply"])
        self.assertEqual(len(seen_urls), 3)
        self.assertEqual(seen_keys[:2], ["key-one", "key-two"])
        self.assertTrue(seen_urls[2].endswith("/chat/completions"))

    def test_configured_openrouter_llm_reply_is_used_from_secrets_file(self):
        class DummyResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(
                    {
                        "choices": [
                            {
                                "message": {
                                    "content": "Live OpenRouter counselling reply.",
                                }
                            }
                        ]
                    }
                ).encode("utf-8")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            tmp.write(json.dumps({"OPENROUTER_API_KEY": "test-openrouter-key"}))
            secret_file = tmp.name
        try:
            with mock.patch.dict(
                os.environ,
                {
                    "APP_SECRETS_PROVIDER": "file",
                    "APP_SECRETS_FILE": secret_file,
                    "SAARTHI_LLM_PROVIDER": "openrouter",
                    "SAARTHI_LLM_REQUIRED": "true",
                    "SAARTHI_LLM_MODEL": "google/gemini-2.5-flash",
                },
                clear=False,
            ), mock.patch("app.saarthi_service.urllib_request.urlopen", return_value=DummyResponse()):
                out = create_saarthi_turn(
                    self.db,
                    student=self.student,
                    message="I need help planning this week.",
                    current_dt=datetime(2026, 3, 8, 9, 0, 0),
                    academic_start=date(2026, 3, 2),
                )
        finally:
            try:
                os.unlink(secret_file)
            except FileNotFoundError:
                pass

        self.assertTrue(out["reply"].startswith("Live OpenRouter counselling reply."))
        self.assertIn("?", out["reply"])

    def test_openrouter_request_contains_system_companion_message(self):
        captured_body: dict[str, object] = {}

        class DummyResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(
                    {
                        "choices": [
                            {
                                "message": {
                                    "content": "Live OpenRouter counselling reply.",
                                }
                            }
                        ]
                    }
                ).encode("utf-8")

        def fake_urlopen(request, timeout=0):
            del timeout
            captured_body.update(json.loads(request.data.decode("utf-8")))
            return DummyResponse()

        with mock.patch.dict(
            os.environ,
            {
                "SAARTHI_LLM_PROVIDER": "openrouter",
                "SAARTHI_LLM_REQUIRED": "true",
                "SAARTHI_LLM_MODEL": "google/gemini-2.5-flash",
                "OPENROUTER_API_KEY": "test-openrouter-key",
            },
            clear=False,
        ), mock.patch("app.saarthi_service.urllib_request.urlopen", side_effect=fake_urlopen):
            out = create_saarthi_turn(
                self.db,
                student=self.student,
                message="I feel really overwhelmed and alone.",
                current_dt=datetime(2026, 3, 8, 9, 0, 0),
                academic_start=date(2026, 3, 2),
            )

        self.assertTrue(out["reply"].startswith("Live OpenRouter counselling reply."))
        self.assertIn("?", out["reply"])
        messages = captured_body.get("messages", [])
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("wise, understanding senior", messages[0]["content"])
        self.assertEqual(messages[1]["role"], "user")
        self.assertEqual(captured_body.get("temperature"), SAARTHI_LLM_TEMPERATURE)
        self.assertEqual(captured_body.get("top_p"), SAARTHI_LLM_TOP_P)
        self.assertEqual(captured_body.get("presence_penalty"), SAARTHI_LLM_PRESENCE_PENALTY)
        self.assertEqual(captured_body.get("frequency_penalty"), SAARTHI_LLM_FREQUENCY_PENALTY)
        self.assertIn("Detected emotional tone:", messages[1]["content"])
        self.assertIn(SAARTHI_IDENTITY_INTRO, messages[1]["content"])
        self.assertIn("one hour of attendance is credited", messages[1]["content"])


if __name__ == "__main__":
    unittest.main()
