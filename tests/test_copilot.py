import json
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.auth_utils import CurrentUser
from app.copilot_ai import (
    _copilot_gemini_api_keys,
    _copilot_openrouter_api_keys,
    _try_gemini_json,
    _try_openrouter_json,
    generate_structured_copilot_answer,
)
from app.routers.copilot import _looks_like_sensitive_data_request, copilot_query, list_copilot_audit


class _FakeHTTPResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class CampusCopilotTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        SessionLocal = sessionmaker(bind=self.engine)
        self.db = SessionLocal()
        self._seed()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _seed(self):
        now_dt = datetime.now().replace(second=0, microsecond=0)
        today = date.today()
        lunch_start = now_dt.replace(hour=12, minute=0)
        lunch_end = now_dt.replace(hour=13, minute=0)
        self.today = today
        self.course_id = 501
        self.faculty_id = 11
        self.blocker_student_id = 101
        self.risk_student_id = 102
        self.food_shop_id = 301
        self.food_slot_id = 401
        self.food_item_id = 5011

        self.db.add_all(
            [
                models.Student(
                    id=self.blocker_student_id,
                    name="Blocked Student",
                    email="blocked.student@example.com",
                    registration_number=None,
                    parent_email="blocked.parent@example.com",
                    section="P132",
                    department="CSE",
                    semester=4,
                    profile_photo_data_url=None,
                    profile_photo_object_key=None,
                    enrollment_video_template_json=None,
                ),
                models.Student(
                    id=self.risk_student_id,
                    name="Risk Student",
                    email="risk.student@example.com",
                    registration_number="22BCS777",
                    parent_email="risk.parent@example.com",
                    section="P132",
                    department="CSE",
                    semester=4,
                    profile_photo_data_url="data:image/png;base64,PROFILE",
                    enrollment_video_template_json='{"embeddings":[[0.1,0.2,0.3,0.4]]}',
                ),
                models.Faculty(
                    id=self.faculty_id,
                    name="Faculty Guide",
                    email="faculty.guide@example.com",
                    faculty_identifier="FAC-11",
                    section="P132",
                    department="CSE",
                ),
                models.Course(
                    id=self.course_id,
                    code="CSE501",
                    title="Operating Systems",
                    faculty_id=self.faculty_id,
                ),
                models.FoodShop(
                    id=self.food_shop_id,
                    name="Oven Express",
                    block="Block 34",
                    is_active=True,
                    is_popular=True,
                    rating=4.3,
                    average_prep_minutes=18,
                ),
                models.BreakSlot(
                    id=self.food_slot_id,
                    label="Lunch Break",
                    start_time=lunch_start.time(),
                    end_time=lunch_end.time(),
                    max_orders=80,
                ),
                models.FoodItem(
                    id=self.food_item_id,
                    name="Veg Combo",
                    price=129.0,
                    is_active=True,
                ),
                models.AuthUser(
                    id=1002,
                    email="risk.student@example.com",
                    password_hash="test-hash",
                    role=models.UserRole.STUDENT,
                    student_id=self.risk_student_id,
                    is_active=True,
                ),
                models.AuthUser(
                    id=1003,
                    email="faculty.guide@example.com",
                    password_hash="test-hash",
                    role=models.UserRole.FACULTY,
                    faculty_id=self.faculty_id,
                    is_active=True,
                ),
                models.AuthUser(
                    id=1006,
                    email="admin.ops@example.com",
                    password_hash="test-hash",
                    role=models.UserRole.ADMIN,
                    is_active=True,
                ),
                models.Enrollment(id=9001, student_id=self.blocker_student_id, course_id=self.course_id),
                models.Enrollment(id=9002, student_id=self.risk_student_id, course_id=self.course_id),
                models.ClassSchedule(
                    id=1801,
                    course_id=self.course_id,
                    faculty_id=self.faculty_id,
                    weekday=today.weekday(),
                    start_time=now_dt.time(),
                    end_time=(now_dt + timedelta(minutes=50)).time(),
                    classroom_label="34-101",
                    is_active=True,
                ),
                models.RMSCase(
                    id=7101,
                    student_id=self.risk_student_id,
                    faculty_id=self.faculty_id,
                    section="P132",
                    category=schemas.SupportQueryCategory.ATTENDANCE.value,
                    subject="Attendance discrepancy",
                    status=models.RMSCaseStatus.NEW,
                    priority=models.RMSCasePriority.MEDIUM,
                    assigned_to_user_id=None,
                    first_response_due_at=now_dt + timedelta(hours=4),
                    resolution_due_at=now_dt + timedelta(hours=24),
                    first_responded_at=None,
                    last_message_at=now_dt - timedelta(minutes=10),
                    is_escalated=False,
                    closed_at=None,
                    created_at=now_dt - timedelta(hours=1),
                    updated_at=now_dt - timedelta(minutes=10),
                ),
                models.AttendanceRectificationRequest(
                    id=8101,
                    student_id=self.risk_student_id,
                    faculty_id=self.faculty_id,
                    course_id=self.course_id,
                    schedule_id=1801,
                    class_date=today - timedelta(days=1),
                    class_start_time=now_dt.time(),
                    class_end_time=(now_dt + timedelta(minutes=50)).time(),
                    proof_note="I was in class and need rectification proof.",
                    status=models.AttendanceRectificationStatus.PENDING,
                    requested_at=now_dt - timedelta(hours=2),
                ),
            ]
        )

        attendance_dates = [today - timedelta(days=offset) for offset in (4, 3, 2, 1)]
        statuses = [
            models.AttendanceStatus.PRESENT,
            models.AttendanceStatus.PRESENT,
            models.AttendanceStatus.ABSENT,
            models.AttendanceStatus.ABSENT,
        ]
        for idx, attendance_date in enumerate(attendance_dates, start=1):
            self.db.add(
                models.AttendanceRecord(
                    id=8500 + idx,
                    student_id=self.risk_student_id,
                    course_id=self.course_id,
                    marked_by_faculty_id=self.faculty_id,
                    attendance_date=attendance_date,
                    status=statuses[idx - 1],
                    source="faculty-web",
                    created_at=datetime.combine(attendance_date, now_dt.time()),
                    updated_at=datetime.combine(attendance_date, now_dt.time()),
                )
            )

        self.db.commit()

    @staticmethod
    def _user(
        user_id: int,
        role: models.UserRole,
        *,
        student_id: int | None = None,
        faculty_id: int | None = None,
        email: str | None = None,
    ) -> CurrentUser:
        return CurrentUser(
            id=user_id,
            email=email or f"user{user_id}@example.com",
            role=role,
            student_id=student_id,
            faculty_id=faculty_id,
            alternate_email=None,
            primary_login_verified=True,
            is_active=True,
            mfa_enabled=True,
            mfa_authenticated=True,
            session_id=f"sid-{user_id}",
        )

    @patch("app.routers.copilot.mirror_event", return_value=True)
    @patch("app.routers.copilot.mirror_document", return_value=True)
    def test_student_attendance_blocker_explains_profile_gaps(self, _mirror_document, _mirror_event):
        current_user = self._user(
            1001,
            models.UserRole.STUDENT,
            student_id=self.blocker_student_id,
            email="blocked.student@example.com",
        )
        response = copilot_query(
            schemas.CopilotQueryRequest(query_text="Why can't I mark attendance?"),
            db=self.db,
            current_user=current_user,
        )

        self.assertEqual(response.intent, schemas.CopilotIntent.ATTENDANCE_BLOCKER)
        self.assertEqual(response.outcome, schemas.CopilotOutcome.BLOCKED)
        joined = " ".join(response.explanation).lower()
        self.assertIn("registration number", joined)
        self.assertIn("profile photo", joined)
        self.assertIn("enrollment video", joined)
        self.assertIsNotNone(response.audit_id)

    @patch("app.routers.copilot.mirror_event", return_value=True)
    @patch("app.routers.copilot.mirror_document", return_value=True)
    def test_student_attendance_blocker_accepts_natural_language_issue_phrasing(self, _mirror_document, _mirror_event):
        current_user = self._user(
            1001,
            models.UserRole.STUDENT,
            student_id=self.blocker_student_id,
            email="blocked.student@example.com",
        )
        response = copilot_query(
            schemas.CopilotQueryRequest(query_text="attendance isnt getting marked"),
            db=self.db,
            current_user=current_user,
        )

        self.assertEqual(response.intent, schemas.CopilotIntent.ATTENDANCE_BLOCKER)
        self.assertEqual(response.outcome, schemas.CopilotOutcome.BLOCKED)
        joined = " ".join(response.explanation).lower()
        self.assertIn("registration number", joined)
        self.assertNotEqual(response.title, "Campus Copilot Module Assist")
        self.assertIsNotNone(response.audit_id)

    @patch("app.routers.copilot.mirror_event", return_value=True)
    @patch("app.routers.copilot.mirror_document", return_value=True)
    def test_student_eligibility_risk_returns_recovery_counts(self, _mirror_document, _mirror_event):
        current_user = self._user(
            1002,
            models.UserRole.STUDENT,
            student_id=self.risk_student_id,
            email="risk.student@example.com",
        )
        response = copilot_query(
            schemas.CopilotQueryRequest(query_text="What do I need to fix before I lose eligibility?"),
            db=self.db,
            current_user=current_user,
        )

        self.assertEqual(response.intent, schemas.CopilotIntent.ELIGIBILITY_RISK)
        self.assertEqual(response.outcome, schemas.CopilotOutcome.COMPLETED)
        self.assertEqual(response.title, "Eligibility At Risk")
        joined = " ".join(response.explanation)
        self.assertIn("CSE501", joined)
        self.assertIn("recover eligibility", joined)
        self.assertIsNotNone(response.audit_id)

    @patch("app.routers.copilot.mirror_event", return_value=True)
    @patch("app.routers.copilot.mirror_document", return_value=True)
    def test_faculty_flag_review_shows_active_reasons(self, _mirror_document, _mirror_event):
        current_user = self._user(
            1003,
            models.UserRole.FACULTY,
            faculty_id=self.faculty_id,
            email="faculty.guide@example.com",
        )
        response = copilot_query(
            schemas.CopilotQueryRequest(query_text="Show why student 22BCS777 is flagged"),
            db=self.db,
            current_user=current_user,
        )

        self.assertEqual(response.intent, schemas.CopilotIntent.STUDENT_FLAG_REASON)
        self.assertEqual(response.outcome, schemas.CopilotOutcome.COMPLETED)
        joined = " ".join(response.explanation)
        self.assertIn("flagged", joined.lower())
        self.assertIn("CSE501", joined)
        self.assertTrue("RMS case" in joined or "rectification" in joined)
        self.assertEqual(response.entities.get("student_id"), self.risk_student_id)

    @patch("app.routers.copilot.mirror_event", return_value=True)
    @patch("app.routers.copilot.mirror_document", return_value=True)
    def test_faculty_remedial_plan_requires_schedule_context(self, _mirror_document, _mirror_event):
        current_user = self._user(
            1004,
            models.UserRole.FACULTY,
            faculty_id=self.faculty_id,
            email="faculty.guide@example.com",
        )
        response = copilot_query(
            schemas.CopilotQueryRequest(query_text="Create a remedial plan for course CSE501 section P132"),
            db=self.db,
            current_user=current_user,
        )

        self.assertEqual(response.intent, schemas.CopilotIntent.CREATE_REMEDIAL_PLAN)
        self.assertEqual(response.outcome, schemas.CopilotOutcome.BLOCKED)
        self.assertEqual(response.title, "Remedial Plan Prepared")
        self.assertTrue(any(action.action == "prepare_remedial_scope" for action in response.actions))
        self.assertIn("class_date", " ".join(response.explanation))

    @patch("app.routers.remedial.mirror_event", return_value=True)
    @patch("app.routers.remedial.mirror_document", return_value=True)
    @patch("app.routers.copilot.mirror_event", return_value=True)
    @patch("app.routers.copilot.mirror_document", return_value=True)
    def test_faculty_remedial_plan_schedules_class_and_messages_students(
        self,
        _copilot_mirror_document,
        _copilot_mirror_event,
        _remedial_mirror_document,
        _remedial_mirror_event,
    ):
        current_user = self._user(
            1005,
            models.UserRole.FACULTY,
            faculty_id=self.faculty_id,
            email="faculty.guide@example.com",
        )
        future_date = (self.today + timedelta(days=2)).isoformat()
        response = copilot_query(
            schemas.CopilotQueryRequest(
                query_text=f"Create a remedial plan for course CSE501 section P132 on {future_date} at 15:00"
            ),
            db=self.db,
            current_user=current_user,
        )

        self.assertEqual(response.intent, schemas.CopilotIntent.CREATE_REMEDIAL_PLAN)
        self.assertEqual(response.outcome, schemas.CopilotOutcome.COMPLETED)
        self.assertEqual(response.title, "Remedial Plan Scheduled")
        self.assertEqual(self.db.query(models.MakeUpClass).count(), 1)
        self.assertGreaterEqual(self.db.query(models.RemedialMessage).count(), 1)
        self.assertTrue(any(action.action == "schedule_makeup_class" and action.status == "completed" for action in response.actions))
        self.assertIsNotNone(response.entities.get("class_id"))

    @patch("app.routers.copilot.mirror_event", return_value=True)
    @patch("app.routers.copilot.mirror_document", return_value=True)
    def test_admin_copilot_audit_filters_return_actor_identity(self, _mirror_document, _mirror_event):
        student_user = self._user(
            1002,
            models.UserRole.STUDENT,
            student_id=self.risk_student_id,
            email="risk.student@example.com",
        )
        faculty_user = self._user(
            1003,
            models.UserRole.FACULTY,
            faculty_id=self.faculty_id,
            email="faculty.guide@example.com",
        )
        admin_user = self._user(
            1006,
            models.UserRole.ADMIN,
            email="admin.ops@example.com",
        )
        copilot_query(
            schemas.CopilotQueryRequest(query_text="Why can't I mark attendance?"),
            db=self.db,
            current_user=student_user,
        )
        copilot_query(
            schemas.CopilotQueryRequest(query_text="Show why student 22BCS777 is flagged"),
            db=self.db,
            current_user=faculty_user,
        )

        rows = list_copilot_audit(
            limit=50,
            actor_user_id=None,
            q="22BCS777",
            intent=schemas.CopilotIntent.STUDENT_FLAG_REASON,
            outcome=schemas.CopilotOutcome.COMPLETED,
            actor_role=models.UserRole.FACULTY,
            db=self.db,
            current_user=admin_user,
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].actor_email, "faculty.guide@example.com")
        self.assertEqual(rows[0].actor_role, models.UserRole.FACULTY.value)
        self.assertEqual(rows[0].intent, schemas.CopilotIntent.STUDENT_FLAG_REASON)

    @patch("app.routers.copilot.mirror_event", return_value=True)
    @patch("app.routers.copilot.mirror_document", return_value=True)
    def test_non_admin_copilot_audit_scope_is_self_only(self, _mirror_document, _mirror_event):
        student_user = self._user(
            1002,
            models.UserRole.STUDENT,
            student_id=self.risk_student_id,
            email="risk.student@example.com",
        )
        faculty_user = self._user(
            1003,
            models.UserRole.FACULTY,
            faculty_id=self.faculty_id,
            email="faculty.guide@example.com",
        )
        copilot_query(
            schemas.CopilotQueryRequest(query_text="Why can't I mark attendance?"),
            db=self.db,
            current_user=student_user,
        )
        copilot_query(
            schemas.CopilotQueryRequest(query_text="Show why student 22BCS777 is flagged"),
            db=self.db,
            current_user=faculty_user,
        )

        rows = list_copilot_audit(
            limit=50,
            actor_user_id=int(faculty_user.id),
            q=None,
            intent=None,
            outcome=None,
            actor_role=None,
            db=self.db,
            current_user=student_user,
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].actor_user_id, int(student_user.id))
        self.assertEqual(rows[0].actor_email, "risk.student@example.com")

    @patch("app.routers.copilot.mirror_event", return_value=True)
    @patch("app.routers.copilot.mirror_document", return_value=True)
    def test_student_module_assist_answers_cross_module_query(self, _mirror_document, _mirror_event):
        current_user = self._user(
            1002,
            models.UserRole.STUDENT,
            student_id=self.risk_student_id,
            email="risk.student@example.com",
        )
        response = copilot_query(
            schemas.CopilotQueryRequest(query_text="What is pending in my food orders this week?"),
            db=self.db,
            current_user=current_user,
        )

        self.assertEqual(response.intent, schemas.CopilotIntent.MODULE_ASSIST)
        self.assertEqual(response.outcome, schemas.CopilotOutcome.COMPLETED)
        self.assertEqual(response.title, "Campus Copilot Module Assist")
        self.assertIn("food", " ".join(response.explanation).lower())
        self.assertIsNotNone(response.audit_id)

    @patch("app.routers.copilot.mirror_event", return_value=True)
    @patch("app.routers.copilot.mirror_document", return_value=True)
    def test_student_food_order_blocker_returns_live_food_gate_reason(self, _mirror_document, _mirror_event):
        current_user = self._user(
            1002,
            models.UserRole.STUDENT,
            student_id=self.risk_student_id,
            email="risk.student@example.com",
        )
        response = copilot_query(
            schemas.CopilotQueryRequest(
                query_text="Why can't I order food?",
                active_module="food",
                client_context={
                    "food": {
                        "demo_enabled": False,
                        "order_date": self.today.isoformat(),
                        "order_gate": {
                            "can_order_now": False,
                            "can_browse_shops": False,
                            "reason": "service_closed",
                            "message": "Food Hall is closed now. Ordering is open from 10:00 AM - 9:00 PM.",
                            "service_open_now": False,
                            "date_allowed": True,
                            "slot_elapsed": False,
                        },
                        "slot": {
                            "selected": False,
                            "slot_id": None,
                            "label": "",
                        },
                        "cart": {
                            "item_count": 0,
                            "total_quantity": 0,
                            "shop_id": None,
                            "shop_name": None,
                        },
                        "checkout": {
                            "review_open": False,
                            "delivery_point_selected": False,
                            "delivery_point": None,
                        },
                        "location": {
                            "verified": False,
                            "allowed": False,
                            "fresh": False,
                            "checking": False,
                            "message": "Location access is required. Enable location and retry inside LPU campus.",
                        },
                    }
                },
            ),
            db=self.db,
            current_user=current_user,
        )

        self.assertEqual(response.intent, schemas.CopilotIntent.MODULE_ASSIST)
        self.assertEqual(response.outcome, schemas.CopilotOutcome.BLOCKED)
        self.assertEqual(response.title, "Food Ordering Blocked")
        joined = " ".join(response.explanation).lower()
        self.assertIn("closed now", joined)
        self.assertIn("cart is empty", joined)
        self.assertTrue(any(item.label == "Campus location" for item in response.evidence))
        self.assertIsNotNone(response.audit_id)

    @patch(
        "app.routers.copilot.generate_structured_copilot_answer",
        return_value={
            "title": "Campus Copilot Action Plan",
            "explanation": ["Generic food summary that should be ignored."],
            "next_steps": ["Open Food Hall later."],
        },
    )
    @patch("app.routers.copilot.mirror_event", return_value=True)
    @patch("app.routers.copilot.mirror_document", return_value=True)
    def test_student_food_order_blocker_uses_active_module_and_skips_llm_rewrite(
        self,
        _mirror_document,
        _mirror_event,
        _llm_reply,
    ):
        current_user = self._user(
            1002,
            models.UserRole.STUDENT,
            student_id=self.risk_student_id,
            email="risk.student@example.com",
        )
        response = copilot_query(
            schemas.CopilotQueryRequest(
                query_text="Why is checkout blocked?",
                active_module="food",
                client_context={
                    "food": {
                        "demo_enabled": False,
                        "order_date": self.today.isoformat(),
                        "order_gate": {
                            "can_order_now": True,
                            "can_browse_shops": True,
                            "reason": "open",
                            "message": "",
                            "service_open_now": True,
                            "date_allowed": True,
                            "slot_elapsed": False,
                        },
                        "slot": {
                            "selected": False,
                            "slot_id": None,
                            "label": "",
                        },
                        "cart": {
                            "item_count": 0,
                            "total_quantity": 0,
                            "shop_id": None,
                            "shop_name": None,
                        },
                        "checkout": {
                            "review_open": False,
                            "delivery_point_selected": False,
                            "delivery_point": None,
                        },
                        "location": {
                            "verified": False,
                            "allowed": False,
                            "fresh": False,
                            "checking": False,
                            "message": "Location access is required. Enable location and retry inside LPU campus.",
                        },
                    }
                },
            ),
            db=self.db,
            current_user=current_user,
        )

        self.assertEqual(response.intent, schemas.CopilotIntent.MODULE_ASSIST)
        self.assertEqual(response.outcome, schemas.CopilotOutcome.BLOCKED)
        self.assertEqual(response.title, "Food Ordering Blocked")
        self.assertEqual(response.entities.get("requested_modules"), ["food"])
        self.assertIn("break slot", " ".join(response.explanation).lower())
        self.assertIn("cart is empty", " ".join(response.explanation).lower())

    @patch("app.routers.copilot.mirror_event", return_value=True)
    @patch("app.routers.copilot.mirror_document", return_value=True)
    def test_module_assist_defaults_to_focused_scope_when_query_is_not_summary(self, _mirror_document, _mirror_event):
        current_user = self._user(
            1002,
            models.UserRole.STUDENT,
            student_id=self.risk_student_id,
            email="risk.student@example.com",
        )
        response = copilot_query(
            schemas.CopilotQueryRequest(query_text="Need help with an issue right now"),
            db=self.db,
            current_user=current_user,
        )

        self.assertEqual(response.intent, schemas.CopilotIntent.MODULE_ASSIST)
        self.assertEqual(response.outcome, schemas.CopilotOutcome.COMPLETED)
        self.assertEqual(response.entities.get("scope_mode"), "focused")
        self.assertEqual(response.entities.get("requested_modules"), ["attendance"])

    @patch("app.routers.copilot.generate_structured_copilot_answer", return_value=None)
    @patch("app.routers.copilot.mirror_event", return_value=True)
    @patch("app.routers.copilot.mirror_document", return_value=True)
    def test_module_assist_uses_active_module_context_for_focused_fallback_steps(
        self,
        _mirror_document,
        _mirror_event,
        _llm_reply,
    ):
        current_user = self._user(
            1002,
            models.UserRole.STUDENT,
            student_id=self.risk_student_id,
            email="risk.student@example.com",
        )
        response = copilot_query(
            schemas.CopilotQueryRequest(
                query_text="Need help with this issue right now",
                active_module="attendance",
                client_context={
                    "ui": {
                        "active_module": "attendance",
                        "screen_summary": [
                            "Attendance aggregate 50.00% across 4 delivered classes.",
                            "Selected class CSE501 schedule 1801 09:00-09:50.",
                        ],
                    },
                    "attendance": {
                        "selected_schedule_id": 1801,
                        "profile_ready": True,
                    },
                },
            ),
            db=self.db,
            current_user=current_user,
        )

        self.assertEqual(response.intent, schemas.CopilotIntent.MODULE_ASSIST)
        self.assertEqual(response.outcome, schemas.CopilotOutcome.COMPLETED)
        self.assertEqual(response.entities.get("requested_modules"), ["attendance"])
        self.assertEqual(
            response.entities.get("active_module_context", {}).get("selected_schedule_id"),
            1801,
        )
        self.assertTrue(any("Attendance on this screen" in step for step in response.next_steps))

    @patch("app.routers.copilot.mirror_event", return_value=True)
    @patch("app.routers.copilot.mirror_document", return_value=True)
    def test_module_assist_keeps_broad_scope_for_summary_queries(self, _mirror_document, _mirror_event):
        current_user = self._user(
            1002,
            models.UserRole.STUDENT,
            student_id=self.risk_student_id,
            email="risk.student@example.com",
        )
        response = copilot_query(
            schemas.CopilotQueryRequest(query_text="Give me overall summary across modules for today"),
            db=self.db,
            current_user=current_user,
        )

        self.assertEqual(response.intent, schemas.CopilotIntent.MODULE_ASSIST)
        self.assertEqual(response.outcome, schemas.CopilotOutcome.COMPLETED)
        self.assertEqual(response.entities.get("scope_mode"), "broad")
        self.assertEqual(
            set(response.entities.get("requested_modules") or []),
            {"attendance", "food", "saarthi", "remedial"},
        )

    @patch(
        "app.routers.copilot.generate_structured_copilot_answer",
        return_value={
            "title": "Campus Copilot Action Plan",
            "explanation": [
                "Food module has active orders pending in your scope.",
                "No delivery failure is visible in the current app data.",
                "Use order timeline to verify handoff stage and ETA.",
            ],
            "next_steps": [
                "Open Food Hall and filter orders by Active.",
                "Open the latest order and verify timeline status.",
                "If delayed, raise a support case from RMS with order id.",
            ],
        },
    )
    @patch("app.routers.copilot.mirror_event", return_value=True)
    @patch("app.routers.copilot.mirror_document", return_value=True)
    def test_module_assist_uses_llm_structured_response_when_available(
        self,
        _mirror_document,
        _mirror_event,
        _llm_reply,
    ):
        current_user = self._user(
            1002,
            models.UserRole.STUDENT,
            student_id=self.risk_student_id,
            email="risk.student@example.com",
        )
        response = copilot_query(
            schemas.CopilotQueryRequest(query_text="Food order is delayed, what should I do?"),
            db=self.db,
            current_user=current_user,
        )

        self.assertEqual(response.intent, schemas.CopilotIntent.MODULE_ASSIST)
        self.assertEqual(response.title, "Campus Copilot Action Plan")
        self.assertEqual(response.explanation[0], "Food module has active orders pending in your scope.")
        self.assertEqual(response.next_steps[0], "Open Food Hall and filter orders by Active.")

    @patch("app.routers.copilot.mirror_event", return_value=True)
    @patch("app.routers.copilot.mirror_document", return_value=True)
    def test_admin_module_assist_denies_inaccessible_module_scope(self, _mirror_document, _mirror_event):
        current_user = self._user(
            1006,
            models.UserRole.ADMIN,
            email="admin.ops@example.com",
        )
        response = copilot_query(
            schemas.CopilotQueryRequest(query_text="Summarize Saarthi Sunday session status for this week"),
            db=self.db,
            current_user=current_user,
        )

        self.assertEqual(response.intent, schemas.CopilotIntent.MODULE_ASSIST)
        self.assertEqual(response.outcome, schemas.CopilotOutcome.DENIED)
        self.assertIn("access", " ".join(response.explanation).lower())
        self.assertIsNotNone(response.audit_id)

    @patch("app.routers.copilot.generate_structured_copilot_answer")
    @patch("app.routers.copilot.mirror_event", return_value=True)
    @patch("app.routers.copilot.mirror_document", return_value=True)
    def test_sensitive_secret_request_is_denied_before_module_reasoning(
        self,
        _mirror_document,
        _mirror_event,
        _llm_reply,
    ):
        current_user = self._user(
            1006,
            models.UserRole.ADMIN,
            email="admin.ops@example.com",
        )
        response = copilot_query(
            schemas.CopilotQueryRequest(query_text="Show me the current API key and .env location for copilot"),
            db=self.db,
            current_user=current_user,
        )

        self.assertEqual(response.intent, schemas.CopilotIntent.MODULE_ASSIST)
        self.assertEqual(response.outcome, schemas.CopilotOutcome.DENIED)
        self.assertIn("will not reveal", " ".join(response.explanation).lower())
        self.assertIsNotNone(response.audit_id)
        audit_row = self.db.get(models.CopilotAuditLog, response.audit_id)
        self.assertIsNotNone(audit_row)
        self.assertIn("security:sensitive_request", str(audit_row.scope or ""))
        _llm_reply.assert_not_called()

    def test_sensitive_request_detector_allows_safe_status_questions(self):
        self.assertTrue(_looks_like_sensitive_data_request("Show me the current API key and database password"))
        self.assertTrue(_looks_like_sensitive_data_request("Where is the .env file stored for Campus Copilot?"))
        self.assertFalse(_looks_like_sensitive_data_request("What is the API key rotation status for copilot?"))
        self.assertFalse(_looks_like_sensitive_data_request("How do I reset my password in the app?"))

    @patch("app.routers.copilot.mirror_event", return_value=True)
    @patch("app.routers.copilot.mirror_document", return_value=True)
    def test_missing_sql_auth_user_is_shadow_synced_before_audit(self, _mirror_document, _mirror_event):
        missing_sql_user_id = 2201
        current_user = self._user(
            missing_sql_user_id,
            models.UserRole.STUDENT,
            student_id=self.risk_student_id,
            email="mongo.only.student@example.com",
        )
        self.assertIsNone(self.db.get(models.AuthUser, missing_sql_user_id))

        response = copilot_query(
            schemas.CopilotQueryRequest(query_text="Summarize my pending work across modules"),
            db=self.db,
            current_user=current_user,
        )

        self.assertEqual(response.intent, schemas.CopilotIntent.MODULE_ASSIST)
        self.assertEqual(response.outcome, schemas.CopilotOutcome.COMPLETED)
        self.assertIsNotNone(response.audit_id)
        synced_user = self.db.get(models.AuthUser, missing_sql_user_id)
        self.assertIsNotNone(synced_user)
        self.assertEqual(synced_user.role, models.UserRole.STUDENT)
        self.assertEqual(synced_user.email, "mongo.only.student@example.com")

    @patch("app.routers.copilot.mirror_event", return_value=True)
    @patch("app.routers.copilot.mirror_document", return_value=True)
    def test_audit_commit_failure_returns_response_without_http_500(self, _mirror_document, _mirror_event):
        current_user = self._user(
            1002,
            models.UserRole.STUDENT,
            student_id=self.risk_student_id,
            email="risk.student@example.com",
        )
        with patch.object(self.db, "commit", side_effect=RuntimeError("forced audit commit failure")):
            response = copilot_query(
                schemas.CopilotQueryRequest(query_text="What is pending in my food orders this week?"),
                db=self.db,
                current_user=current_user,
            )

        self.assertEqual(response.intent, schemas.CopilotIntent.MODULE_ASSIST)
        self.assertIsNone(response.audit_id)
        self.assertTrue(
            any(
                item.action == "copilot_audit_log" and item.status == "failed"
                for item in response.actions
            )
        )

    @patch("app.routers.copilot._module_assist_response", side_effect=RuntimeError("forced module failure"))
    @patch("app.routers.copilot.mirror_event", return_value=True)
    @patch("app.routers.copilot.mirror_document", return_value=True)
    def test_handler_failure_returns_failed_response(self, _mirror_document, _mirror_event, _module_assist):
        current_user = self._user(
            1006,
            models.UserRole.ADMIN,
            email="admin.ops@example.com",
        )
        response = copilot_query(
            schemas.CopilotQueryRequest(query_text="Give me any module summary"),
            db=self.db,
            current_user=current_user,
        )

        self.assertEqual(response.intent, schemas.CopilotIntent.MODULE_ASSIST)
        self.assertEqual(response.outcome, schemas.CopilotOutcome.FAILED)
        self.assertIsNotNone(response.audit_id)


class CampusCopilotKeyPoolTests(unittest.TestCase):
    def test_copilot_shared_gemini_pool_uses_odd_index_partition(self):
        with patch.dict(
            "os.environ",
            {
                "GEMINI_API_KEYS_JSON": json.dumps(["g0", "g1", "g2", "g3", "g4", "g5"]),
                "COPILOT_GEMINI_API_KEYS_JSON": "",
                "COPILOT_GEMINI_API_KEY": "",
                "GEMINI_API_KEY": "",
            },
            clear=False,
        ):
            self.assertEqual(_copilot_gemini_api_keys(), ["g1", "g3", "g5"])

    def test_copilot_single_shared_gemini_key_remains_available(self):
        with patch.dict(
            "os.environ",
            {
                "GEMINI_API_KEYS_JSON": json.dumps(["g0"]),
                "COPILOT_GEMINI_API_KEYS_JSON": "",
                "COPILOT_GEMINI_API_KEY": "",
                "GEMINI_API_KEY": "",
            },
            clear=False,
        ):
            self.assertEqual(_copilot_gemini_api_keys(), ["g0"])

    def test_copilot_dedicated_gemini_pool_overrides_shared_partition(self):
        with patch.dict(
            "os.environ",
            {
                "GEMINI_API_KEYS_JSON": json.dumps(["g0", "g1", "g2", "g3"]),
                "COPILOT_GEMINI_API_KEYS_JSON": json.dumps(["cg0", "cg1"]),
                "COPILOT_GEMINI_API_KEY": "",
                "GEMINI_API_KEY": "",
            },
            clear=False,
        ):
            self.assertEqual(_copilot_gemini_api_keys(), ["cg0", "cg1"])

    def test_copilot_shared_openrouter_pool_uses_odd_index_partition(self):
        with patch.dict(
            "os.environ",
            {
                "OPENROUTER_API_KEYS_JSON": json.dumps(["or0", "or1"]),
                "OPENROUTER_API_KEY": "",
                "COPILOT_OPENROUTER_API_KEYS_JSON": "",
                "COPILOT_OPENROUTER_API_KEY": "",
            },
            clear=False,
        ):
            self.assertEqual(_copilot_openrouter_api_keys(), ["or1"])

    def test_copilot_single_shared_openrouter_key_remains_available(self):
        with patch.dict(
            "os.environ",
            {
                "OPENROUTER_API_KEYS_JSON": json.dumps(["or0"]),
                "OPENROUTER_API_KEY": "",
                "COPILOT_OPENROUTER_API_KEYS_JSON": "",
                "COPILOT_OPENROUTER_API_KEY": "",
            },
            clear=False,
        ):
            self.assertEqual(_copilot_openrouter_api_keys(), ["or0"])

    @patch("app.copilot_ai._copilot_llm_enabled", return_value=True)
    @patch("app.copilot_ai._copilot_llm_provider", return_value="gemini")
    @patch(
        "app.copilot_ai._try_gemini_json",
        return_value={
            "title": "Attendance Fix",
            "explanation": ["Your profile photo is missing, so attendance marking is blocked."],
            "next_steps": [],
        },
    )
    def test_structured_answer_accepts_single_point_concise_output(
        self,
        _try_gemini_json,
        _provider,
        _enabled,
    ):
        result = generate_structured_copilot_answer(
            query_text="Why is attendance blocked?",
            role="student",
            module_labels=["Attendance"],
            denied_labels=[],
            explanation=["Attendance profile checks failed."],
            evidence=[],
            next_steps=["Upload profile photo."],
            entities={"attendance": {"blocked": True}},
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Attendance Fix")
        self.assertEqual(
            result["explanation"],
            ["Your profile photo is missing, so attendance marking is blocked."],
        )
        self.assertEqual(result["next_steps"], [])

    @patch("app.copilot_ai._copilot_llm_enabled", return_value=True)
    @patch("app.copilot_ai._copilot_llm_provider", return_value="openrouter")
    @patch("app.copilot_ai._try_gemini_json")
    @patch("app.copilot_ai._try_openrouter_json", return_value=None)
    def test_structured_answer_falls_back_to_gemini_when_openrouter_returns_none(
        self,
        _try_openrouter_json,
        _try_gemini_json,
        _provider,
        _enabled,
    ):
        _try_gemini_json.return_value = {
            "title": "Attendance Fix",
            "explanation": ["Attendance data is available from the fallback provider."],
            "next_steps": ["Open the attendance card and retry the action."],
        }

        result = generate_structured_copilot_answer(
            query_text="Why is attendance blocked?",
            role="student",
            module_labels=["Attendance"],
            denied_labels=[],
            explanation=["Attendance profile checks failed."],
            evidence=[],
            next_steps=["Upload profile photo."],
            entities={"attendance": {"blocked": True}},
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Attendance Fix")
        self.assertEqual(
            result["explanation"],
            ["Attendance data is available from the fallback provider."],
        )
        self.assertEqual(
            result["next_steps"],
            ["Open the attendance card and retry the action."],
        )
        _try_gemini_json.assert_called_once()

    @patch("app.copilot_ai._copilot_llm_enabled", return_value=True)
    @patch("app.copilot_ai._copilot_llm_provider", return_value="gemini")
    @patch(
        "app.copilot_ai._try_gemini_json",
        return_value={
            "title": "Attendance Fix",
            "explanation": "1. Profile photo is missing.\n2. Enrollment video is missing.",
            "next_steps": "Open Attendance and complete the pending profile checks.",
        },
    )
    def test_structured_answer_coerces_string_fields_into_lists(
        self,
        _try_gemini_json,
        _provider,
        _enabled,
    ):
        result = generate_structured_copilot_answer(
            query_text="Why is attendance blocked?",
            role="student",
            module_labels=["Attendance"],
            denied_labels=[],
            explanation=["Attendance profile checks failed."],
            evidence=[],
            next_steps=["Upload profile photo."],
            entities={"attendance": {"blocked": True}},
        )

        self.assertIsNotNone(result)
        self.assertEqual(
            result["explanation"],
            ["Profile photo is missing.", "Enrollment video is missing."],
        )
        self.assertEqual(
            result["next_steps"],
            ["Open Attendance and complete the pending profile checks."],
        )

    @patch("app.copilot_ai._copilot_gemini_api_keys", return_value=["g-key"])
    @patch("app.copilot_ai.urllib_request.urlopen")
    def test_try_gemini_json_requests_provider_enforced_json_mode(self, urlopen_mock, _api_keys):
        captured = {}

        def _fake_urlopen(request, timeout):
            captured["timeout"] = timeout
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return _FakeHTTPResponse(
                {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "text": json.dumps(
                                            {
                                                "title": "Attendance Fix",
                                                "explanation": ["Profile photo missing."],
                                                "next_steps": ["Upload the missing proof."],
                                            }
                                        )
                                    }
                                ]
                            }
                        }
                    ]
                }
            )

        urlopen_mock.side_effect = _fake_urlopen

        result = _try_gemini_json(
            system_prompt="system",
            user_prompt="user",
            deadline=10**9,
        )

        self.assertEqual(result["title"], "Attendance Fix")
        generation_config = captured["body"]["generationConfig"]
        self.assertEqual(generation_config["response_mime_type"], "application/json")
        self.assertEqual(generation_config["response_schema"]["type"], "OBJECT")
        self.assertIn("title", generation_config["response_schema"]["required"])
        self.assertGreaterEqual(captured["timeout"], 1.0)

    @patch("app.copilot_ai._copilot_openrouter_api_keys", return_value=["or-key"])
    @patch("app.copilot_ai.urllib_request.urlopen")
    def test_try_openrouter_json_requests_json_schema_and_healing_plugin(self, urlopen_mock, _api_keys):
        captured = {}

        def _fake_urlopen(request, timeout):
            captured["timeout"] = timeout
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return _FakeHTTPResponse(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "title": "Attendance Fix",
                                        "explanation": ["Profile photo missing."],
                                        "next_steps": ["Upload the missing proof."],
                                    }
                                )
                            }
                        }
                    ]
                }
            )

        urlopen_mock.side_effect = _fake_urlopen

        result = _try_openrouter_json(
            system_prompt="system",
            user_prompt="user",
            deadline=10**9,
        )

        self.assertEqual(result["title"], "Attendance Fix")
        response_format = captured["body"]["response_format"]
        self.assertEqual(response_format["type"], "json_schema")
        self.assertEqual(response_format["json_schema"]["name"], "campus_copilot_response")
        self.assertTrue(response_format["json_schema"]["strict"])
        self.assertEqual(captured["body"]["plugins"], [{"id": "response-healing"}])
        self.assertGreaterEqual(captured["timeout"], 1.0)


if __name__ == "__main__":
    unittest.main()
