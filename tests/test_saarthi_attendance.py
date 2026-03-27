import json
import os
import unittest
from datetime import date, datetime, timedelta
from unittest import mock

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.attendance_recovery import evaluate_attendance_recovery
from app.routers.attendance import (
    get_absentees,
    get_student_attendance_aggregate,
    get_student_attendance_history,
    mark_attendance_bulk,
)
from app.routers.saarthi import get_saarthi_status, send_saarthi_message
from app.saarthi_service import (
    SAARTHI_ATTENDANCE_MINUTES,
    SAARTHI_COURSE_CODE,
    _build_saarthi_llm_user_prompt,
    _generate_saarthi_reply_deterministic,
    _saarthi_gemini_api_keys,
    _saarthi_openrouter_api_keys,
    _saarthi_openrouter_model,
    create_saarthi_turn,
    ensure_saarthi_bundle,
    get_or_create_saarthi_session,
    materialize_saarthi_attendance,
)


class SaarthiAttendanceTests(unittest.TestCase):
    def setUp(self):
        self._env_patcher = mock.patch.dict(
            os.environ,
            {
                "APP_SECRETS_PROVIDER": "env",
                "APP_ENV": "development",
                "MONGO_PERSISTENCE_REQUIRED": "false",
                "SQL_OUTBOX_ENABLED": "false",
            },
            clear=True,
        )
        self._env_patcher.start()
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        SessionLocal = sessionmaker(bind=self.engine)
        self.db = SessionLocal()
        self._seed()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()
        self._env_patcher.stop()

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

    @staticmethod
    def _admin_user() -> models.AuthUser:
        return models.AuthUser(
            id=9100,
            email="admin.saarthi@example.com",
            password_hash="x",
            role=models.UserRole.ADMIN,
            student_id=None,
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

    def test_con111_absentee_list_targets_only_missed_mandatory_sunday_students(self):
        second_student = models.Student(
            id=2,
            name="Saarthi Missed Student",
            email="saarthi.missed@example.com",
            registration_number="22BCS5002",
            section="P132",
            department="CSE",
            semester=6,
        )
        self.db.add(second_student)
        self.db.commit()

        bundle = ensure_saarthi_bundle(self.db, student_id=int(self.student.id))
        ensure_saarthi_bundle(self.db, student_id=int(second_student.id))
        create_saarthi_turn(
            self.db,
            student=self.student,
            message="Checking in for mandatory Sunday counselling.",
            current_dt=datetime(2026, 3, 8, 10, 5, 0),
            academic_start=date(2026, 3, 2),
        )
        self.db.commit()

        absentees = get_absentees(
            course_id=int(bundle.course.id),
            attendance_date=date(2026, 3, 8),
            db=self.db,
        )
        absentee_ids = sorted(int(item.id) for item in absentees)

        self.assertEqual(absentee_ids, [int(second_student.id)])

    def test_con111_bulk_absence_notifications_skip_students_who_attended_mandatory_sunday(self):
        second_student = models.Student(
            id=2,
            name="Saarthi Missed Student",
            email="saarthi.missed@example.com",
            registration_number="22BCS5002",
            section="P132",
            department="CSE",
            semester=6,
        )
        self.db.add(second_student)
        self.db.commit()

        bundle = ensure_saarthi_bundle(self.db, student_id=int(self.student.id))
        ensure_saarthi_bundle(self.db, student_id=int(second_student.id))
        create_saarthi_turn(
            self.db,
            student=self.student,
            message="Sunday counselling check-in complete.",
            current_dt=datetime(2026, 3, 8, 9, 10, 0),
            academic_start=date(2026, 3, 2),
        )
        self.db.commit()

        result = mark_attendance_bulk(
            schemas.AttendanceBulkMarkRequest(
                course_id=int(bundle.course.id),
                faculty_id=int(bundle.faculty.id),
                attendance_date=date(2026, 3, 8),
                default_status=models.AttendanceStatus.ABSENT,
                source="faculty-web",
                overrides=[],
            ),
            db=self.db,
            current_user=self._admin_user(),
        )

        self.assertEqual(sorted(result.absent_student_ids), [1, 2])
        self.assertEqual(result.notifications_sent, 1)

        logs = self.db.query(models.NotificationLog).order_by(models.NotificationLog.id.asc()).all()
        self.assertEqual(len(logs), 1)
        self.assertEqual(int(logs[0].student_id), int(second_student.id))
        self.assertEqual(logs[0].sent_to, second_student.email)

    def test_llm_prompt_includes_prior_conversation_memory(self):
        recent_messages = [
            models.SaarthiMessage(sender_role="student", message="I am stressed about exams and deadlines."),
            models.SaarthiMessage(sender_role="assistant", message="I hear you. We can take this slowly."),
            models.SaarthiMessage(sender_role="student", message="I was stressed again before my exam today."),
            models.SaarthiMessage(sender_role="assistant", message="That sounds heavy."),
            models.SaarthiMessage(sender_role="student", message="I will try one 20 minute focus block tonight."),
            models.SaarthiMessage(sender_role="assistant", message="That is a strong step."),
            models.SaarthiMessage(sender_role="student", message="I still feel stressed and cannot focus."),
        ]
        prompt = _build_saarthi_llm_user_prompt(
            student_name="Saarthi Student",
            student_message="I still feel stressed and cannot focus.",
            recent_messages=recent_messages,
            current_dt=datetime(2026, 3, 8, 18, 30, 0),
            mandatory_date=date(2026, 3, 8),
            attendance_awarded_now=False,
            attendance_already_awarded=False,
        )

        self.assertIn("Conversation memory (use only if it fits naturally and do not invent details):", prompt)
        self.assertIn("Recurring student context:", prompt)
        self.assertIn('Prior student intention to acknowledge naturally: "I will try one 20 minute focus block tonight".', prompt)

    def test_deterministic_reply_bridges_prior_student_context(self):
        recent_messages = [
            models.SaarthiMessage(sender_role="student", message="I am stressed about exams and deadlines."),
            models.SaarthiMessage(sender_role="assistant", message="I hear you. We can take this slowly."),
            models.SaarthiMessage(sender_role="student", message="I will try one 20 minute focus block tonight."),
            models.SaarthiMessage(sender_role="assistant", message="That is a strong step."),
            models.SaarthiMessage(sender_role="student", message="I still feel stressed and cannot focus today."),
        ]

        reply = _generate_saarthi_reply_deterministic(
            student_name="Saarthi Student",
            student_message="I still feel stressed and cannot focus today.",
            current_dt=datetime(2026, 3, 8, 18, 45, 0),
            mandatory_date=date(2026, 3, 8),
            attendance_awarded_now=False,
            attendance_already_awarded=False,
            recent_messages=recent_messages,
        )

        self.assertIn("You mentioned earlier", reply)
        self.assertIn("20 minute focus block", reply)
        self.assertIn("?", reply)

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
                                    "parts": [
                                        {
                                            "text": (
                                                "That sounds heavy, and I'm glad you said it out loud. "
                                                "What you're feeling is valid, especially when pressure keeps building. "
                                                "Something that could help is choosing one gentle task for the next 20 minutes "
                                                "and then pausing to breathe. What feels hardest to carry right now?"
                                            )
                                        }
                                    ],
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

        self.assertTrue(out["reply"].startswith("Hi, I'm Saarthi."))
        self.assertIn("That sounds heavy, and I'm glad you said it out loud.", out["reply"])
        self.assertIn("Something that could help is choosing one gentle task", out["reply"])
        self.assertIn("What feels hardest to carry right now?", out["reply"])

    def test_partial_llm_reply_falls_back_to_readable_saarthi_response(self):
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
                                    "parts": [{"text": "Hi Ankan, I'm Saarthi. I'"}],
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
                message="feeling low",
                current_dt=datetime(2026, 3, 8, 9, 15, 0),
                academic_start=date(2026, 3, 2),
        )

        self.assertNotEqual(out["reply"], "Hi Ankan, I'm Saarthi. I'")
        self.assertNotIn("Hi Ankan, I'm Saarthi.", out["reply"])
        self.assertIn("I'm here to listen and support you.", out["reply"])
        self.assertIn("?", out["reply"])
        self.assertGreater(len(out["reply"]), 120)

    def test_required_llm_missing_keys_returns_503_without_fallback_reply(self):
        mocked_now = datetime(2026, 3, 8, 9, 0, 0)

        with mock.patch.dict(
            os.environ,
            {
                "SAARTHI_LLM_PROVIDER": "gemini",
                "SAARTHI_LLM_REQUIRED": "true",
                "GEMINI_API_KEY": "",
                "GEMINI_API_KEYS_JSON": "",
                "GEMINI_API_KEYRING_JSON": "",
                "OPENROUTER_API_KEY": "",
                "OPENROUTER_API_KEYS_JSON": "",
                "OPENROUTER_API_KEYRING_JSON": "",
            },
            clear=False,
        ), mock.patch("app.routers.saarthi._saarthi_now", return_value=mocked_now):
            with self.assertRaises(HTTPException) as ctx:
                send_saarthi_message(
                    payload=schemas.SaarthiChatRequest(message="Need help right now."),
                    db=self.db,
                    current_user=self._student_user(),
                )

        self.assertEqual(ctx.exception.status_code, 503)
        self.assertIn("GEMINI_API_KEY", ctx.exception.detail)
        self.assertEqual(self.db.query(models.SaarthiSession).count(), 0)
        self.assertEqual(self.db.query(models.SaarthiMessage).count(), 0)
        self.assertEqual(self.db.query(models.AttendanceRecord).count(), 0)
        self.assertEqual(self.db.query(models.AttendanceEvent).count(), 0)

    def test_router_uses_local_saarthi_clock_for_status_and_chat(self):
        mocked_now = datetime(2026, 3, 8, 0, 30, 0)

        with mock.patch("app.routers.saarthi._saarthi_now", return_value=mocked_now):
            status = get_saarthi_status(
                db=self.db,
                current_user=self._student_user(),
            )
            reply = send_saarthi_message(
                payload=schemas.SaarthiChatRequest(message="Checking in on the mandatory Sunday window."),
                db=self.db,
                current_user=self._student_user(),
            )

        self.assertEqual(status.mandatory_date, date(2026, 3, 8))
        self.assertIn("Today is your mandatory Saarthi Sunday check-in.", status.status_message)
        self.assertTrue(reply.attendance_awarded_now)
        self.assertEqual(reply.session.mandatory_date, date(2026, 3, 8))
        self.assertTrue(reply.session.session_completed_for_week)
        self.assertEqual(reply.session.attendance_credit_minutes_for_week, SAARTHI_ATTENDANCE_MINUTES)

    def test_status_reports_full_message_count_and_latest_window(self):
        current_dt = datetime(2026, 3, 9, 9, 0, 0)
        _, session = get_or_create_saarthi_session(
            self.db,
            student_id=int(self.student.id),
            current_dt=current_dt,
        )
        for idx in range(82):
            self.db.add(
                models.SaarthiMessage(
                    session_id=int(session.id),
                    sender_role="student" if idx % 2 == 0 else "assistant",
                    message=f"turn-{idx:02d}",
                    created_at=current_dt + timedelta(minutes=idx),
                )
            )
        self.db.commit()

        with mock.patch("app.routers.saarthi._saarthi_now", return_value=current_dt):
            status = get_saarthi_status(
                db=self.db,
                current_user=self._student_user(),
            )

        self.assertEqual(status.current_week_message_count, 82)
        self.assertEqual(len(status.messages), 80)
        self.assertEqual(status.messages[0].message, "turn-02")
        self.assertEqual(status.messages[-1].message, "turn-81")

    def test_chat_uses_latest_recent_message_window_for_long_sessions(self):
        current_dt = datetime(2026, 3, 9, 10, 0, 0)
        _, session = get_or_create_saarthi_session(
            self.db,
            student_id=int(self.student.id),
            current_dt=current_dt,
        )
        for idx in range(14):
            self.db.add(
                models.SaarthiMessage(
                    session_id=int(session.id),
                    sender_role="student" if idx % 2 == 0 else "assistant",
                    message=f"turn-{idx:02d}",
                    created_at=current_dt + timedelta(minutes=idx),
                )
            )
        self.db.commit()

        captured: dict[str, list[str]] = {}

        def _fake_generate(**kwargs):
            captured["messages"] = [row.message for row in kwargs["recent_messages"]]
            return "I hear you. What feels hardest right now?"

        with mock.patch("app.saarthi_service.generate_saarthi_reply", side_effect=_fake_generate):
            create_saarthi_turn(
                self.db,
                student=self.student,
                message="latest-question",
                current_dt=current_dt + timedelta(minutes=15),
                academic_start=date(2026, 3, 9),
            )

        self.assertEqual(
            captured["messages"],
            [
                "turn-03",
                "turn-04",
                "turn-05",
                "turn-06",
                "turn-07",
                "turn-08",
                "turn-09",
                "turn-10",
                "turn-11",
                "turn-12",
                "turn-13",
                "latest-question",
            ],
        )

    def test_chat_failure_rolls_back_partial_saarthi_writes(self):
        mocked_now = datetime(2026, 3, 8, 9, 0, 0)

        with mock.patch("app.routers.saarthi._saarthi_now", return_value=mocked_now), mock.patch(
            "app.saarthi_service.generate_saarthi_reply",
            side_effect=RuntimeError("Saarthi upstream unavailable"),
        ):
            with self.assertRaises(HTTPException) as ctx:
                send_saarthi_message(
                    payload=schemas.SaarthiChatRequest(message="Need help right now."),
                    db=self.db,
                    current_user=self._student_user(),
                )

        self.assertEqual(ctx.exception.status_code, 503)
        self.assertEqual(self.db.query(models.SaarthiSession).count(), 0)
        self.assertEqual(self.db.query(models.SaarthiMessage).count(), 0)
        self.assertEqual(self.db.query(models.AttendanceRecord).count(), 0)
        self.assertEqual(self.db.query(models.AttendanceEvent).count(), 0)

        with mock.patch("app.routers.saarthi._saarthi_now", return_value=mocked_now):
            reply = send_saarthi_message(
                payload=schemas.SaarthiChatRequest(message="Need help right now."),
                db=self.db,
                current_user=self._student_user(),
            )

        self.assertTrue(reply.attendance_awarded_now)
        self.assertEqual(reply.session.current_week_message_count, 2)

    def test_openrouter_model_defaults_to_google_prefixed_gemini_model(self):
        with mock.patch.dict(
            os.environ,
            {
                "SAARTHI_LLM_MODEL": "gemini-2.5-flash",
                "SAARTHI_OPENROUTER_MODEL": "",
            },
            clear=False,
        ):
            self.assertEqual(_saarthi_openrouter_model(), "google/gemini-2.5-flash")

    def test_openrouter_model_honors_explicit_override(self):
        with mock.patch.dict(
            os.environ,
            {
                "SAARTHI_LLM_MODEL": "gemini-2.5-flash",
                "SAARTHI_OPENROUTER_MODEL": "google/gemini-2.0-flash-001",
            },
            clear=False,
        ):
            self.assertEqual(_saarthi_openrouter_model(), "google/gemini-2.0-flash-001")

    def test_saarthi_shared_gemini_pool_uses_even_index_partition(self):
        with mock.patch.dict(
            os.environ,
            {
                "GEMINI_API_KEYS_JSON": json.dumps(["g0", "g1", "g2", "g3", "g4", "g5"]),
                "SAARTHI_GEMINI_API_KEYS_JSON": "",
                "SAARTHI_GEMINI_API_KEY": "",
                "GEMINI_API_KEY": "",
            },
            clear=False,
        ):
            self.assertEqual(_saarthi_gemini_api_keys(), ["g0", "g2", "g4"])

    def test_saarthi_dedicated_gemini_pool_overrides_shared_partition(self):
        with mock.patch.dict(
            os.environ,
            {
                "GEMINI_API_KEYS_JSON": json.dumps(["g0", "g1", "g2", "g3"]),
                "SAARTHI_GEMINI_API_KEYS_JSON": json.dumps(["sg0", "sg1"]),
                "SAARTHI_GEMINI_API_KEY": "",
                "GEMINI_API_KEY": "",
            },
            clear=False,
        ):
            self.assertEqual(_saarthi_gemini_api_keys(), ["sg0", "sg1"])

    def test_saarthi_shared_openrouter_pool_uses_even_index_partition(self):
        with mock.patch.dict(
            os.environ,
            {
                "OPENROUTER_API_KEYS_JSON": json.dumps(["or0", "or1"]),
                "OPENROUTER_API_KEY": "",
                "SAARTHI_OPENROUTER_API_KEYS_JSON": "",
                "SAARTHI_OPENROUTER_API_KEY": "",
            },
            clear=False,
        ):
            self.assertEqual(_saarthi_openrouter_api_keys(), ["or0"])


if __name__ == "__main__":
    unittest.main()
