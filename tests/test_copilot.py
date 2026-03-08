import unittest
from datetime import date, datetime, timedelta
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.auth_utils import CurrentUser
from app.routers.copilot import copilot_query, list_copilot_audit


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
        self.today = today
        self.course_id = 501
        self.faculty_id = 11
        self.blocker_student_id = 101
        self.risk_student_id = 102

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


if __name__ == "__main__":
    unittest.main()
