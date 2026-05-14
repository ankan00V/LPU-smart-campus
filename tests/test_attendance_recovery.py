import json
import os
import unittest
from datetime import date, datetime, time, timedelta
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.attendance_recovery import (
    _recent_recovery_notice_exists_any,
    _safe_send_recovery_email,
    complete_remedial_recovery_action,
    evaluate_attendance_recovery,
    get_admin_recovery_plans,
    get_faculty_recovery_plans,
    retro_send_recovery_notifications,
)
from app.routers.admin import _build_admin_payload
from app.routers.attendance import get_student_recovery_plan_list


class AttendanceRecoveryWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        SessionLocal = sessionmaker(bind=self.engine)
        self.db = SessionLocal()
        self.today = date.today()
        self._previous_academic_start = os.environ.get("ACADEMIC_START_DATE")
        os.environ["ACADEMIC_START_DATE"] = (self.today - timedelta(days=8)).isoformat()
        self.future_makeup_date = self.today + timedelta(days=1)
        self._seed_base()

    def tearDown(self):
        if self._previous_academic_start is None:
            os.environ.pop("ACADEMIC_START_DATE", None)
        else:
            os.environ["ACADEMIC_START_DATE"] = self._previous_academic_start
        self.db.close()
        self.engine.dispose()

    def _seed_base(self):
        self.db.add_all(
            [
                models.Faculty(
                    id=201,
                    name="Faculty One",
                    email="faculty.one@example.com",
                    department="CSE",
                    section="P132",
                ),
                models.Student(
                    id=101,
                    name="Student One",
                    email="student.one@example.com",
                    registration_number="22BCS101",
                    section="P132",
                    department="CSE",
                    semester=4,
                    parent_email="parent.one@example.com",
                ),
                models.Course(
                    id=301,
                    code="CSE310",
                    title="Software Engineering",
                    faculty_id=201,
                ),
                models.Enrollment(
                    id=401,
                    student_id=101,
                    course_id=301,
                ),
                models.ClassSchedule(
                    id=501,
                    course_id=301,
                    faculty_id=201,
                    weekday=self.future_makeup_date.weekday(),
                    start_time=time(10, 0),
                    end_time=time(11, 0),
                    classroom_label="34-201",
                    is_active=True,
                ),
                models.MakeUpClass(
                    id=601,
                    course_id=301,
                    faculty_id=201,
                    class_date=self.future_makeup_date,
                    start_time=time(16, 0),
                    end_time=time(17, 0),
                    topic="Missed concepts",
                    sections_json=json.dumps(["P132"]),
                    class_mode="offline",
                    room_number="27-401",
                    online_link=None,
                    remedial_code="RECOV123",
                    code_generated_at=datetime.utcnow(),
                    code_expires_at=datetime.utcnow() + timedelta(hours=2),
                    attendance_open_minutes=15,
                    scheduled_at=datetime.utcnow(),
                    is_active=True,
                ),
                models.AuthUser(
                    id=801,
                    email="student.one@example.com",
                    password_hash="x",
                    role=models.UserRole.STUDENT,
                    student_id=101,
                    faculty_id=None,
                    is_active=True,
                ),
                models.AuthUser(
                    id=802,
                    email="faculty.one@example.com",
                    password_hash="x",
                    role=models.UserRole.FACULTY,
                    student_id=None,
                    faculty_id=201,
                    is_active=True,
                ),
            ]
        )
        self.db.commit()

    def _seed_attendance(self, statuses, *, start_offset_days):
        rows = []
        for idx, status in enumerate(statuses, start=1):
            attendance_date = self.today - timedelta(days=start_offset_days - (idx - 1))
            rows.append(
                models.AttendanceRecord(
                    id=1000 + len(rows) + self.db.query(models.AttendanceRecord).count(),
                    student_id=101,
                    course_id=301,
                    marked_by_faculty_id=201,
                    attendance_date=attendance_date,
                    status=status,
                    source="seed",
                )
            )
        self.db.add_all(rows)
        self.db.commit()

    def _actions_by_type(self):
        rows = (
            self.db.query(models.AttendanceRecoveryAction)
            .join(
                models.AttendanceRecoveryPlan,
                models.AttendanceRecoveryPlan.id == models.AttendanceRecoveryAction.plan_id,
            )
            .filter(
                models.AttendanceRecoveryPlan.student_id == 101,
                models.AttendanceRecoveryPlan.course_id == 301,
            )
            .order_by(models.AttendanceRecoveryAction.id.asc())
            .all()
        )
        return {row.action_type: row for row in rows}

    def test_watch_plan_creates_soft_warning_actions_only(self):
        self._seed_attendance(
            [
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.ABSENT,
                models.AttendanceStatus.ABSENT,
            ],
            start_offset_days=7,
        )

        plan = evaluate_attendance_recovery(self.db, student_id=101, course_id=301)

        self.assertIsNotNone(plan)
        self.assertEqual(plan.risk_level, models.AttendanceRecoveryRiskLevel.WATCH)
        self.assertEqual(plan.status, models.AttendanceRecoveryPlanStatus.ACTIVE)

        actions = self._actions_by_type()
        self.assertIn(models.AttendanceRecoveryActionType.FACULTY_NUDGE, actions)
        self.assertIn(models.AttendanceRecoveryActionType.REMEDIAL_SLOT, actions)
        self.assertNotIn(models.AttendanceRecoveryActionType.OFFICE_HOUR_INVITE, actions)
        self.assertNotIn(models.AttendanceRecoveryActionType.CATCH_UP_TASK, actions)
        self.assertNotIn(models.AttendanceRecoveryActionType.PARENT_ALERT, actions)

        remedial_meta = json.loads(actions[models.AttendanceRecoveryActionType.REMEDIAL_SLOT].metadata_json or "{}")
        faculty_meta = json.loads(actions[models.AttendanceRecoveryActionType.FACULTY_NUDGE].metadata_json or "{}")
        self.assertFalse(bool(remedial_meta.get("mandatory")))
        self.assertTrue(bool(faculty_meta.get("optional")))

    def test_plan_is_created_from_delivered_schedule_evidence_even_with_sparse_records(self):
        previous = os.environ.get("ACADEMIC_START_DATE")
        os.environ["ACADEMIC_START_DATE"] = (self.today - timedelta(days=90)).isoformat()
        try:
            # Only one explicit present record, but many delivered classes are inferred from schedule history.
            self._seed_attendance(
                [
                    models.AttendanceStatus.PRESENT,
                ],
                start_offset_days=3,
            )
            plan = evaluate_attendance_recovery(self.db, student_id=101, course_id=301)
            self.assertIsNotNone(plan)
            assert plan is not None
            self.assertGreater(plan.delivered_count, 1)
            self.assertLess(plan.attendance_percent, 75.0)
            self.assertIn(
                plan.risk_level,
                {
                    models.AttendanceRecoveryRiskLevel.HIGH,
                    models.AttendanceRecoveryRiskLevel.CRITICAL,
                    models.AttendanceRecoveryRiskLevel.WATCH,
                },
            )
        finally:
            if previous is None:
                os.environ.pop("ACADEMIC_START_DATE", None)
            else:
                os.environ["ACADEMIC_START_DATE"] = previous

    def test_high_plan_requires_acknowledgement_actions_without_parent_or_rms_escalation(self):
        self._seed_attendance(
            [
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.ABSENT,
                models.AttendanceStatus.ABSENT,
            ],
            start_offset_days=8,
        )

        plan = evaluate_attendance_recovery(self.db, student_id=101, course_id=301)

        self.assertIsNotNone(plan)
        self.assertEqual(plan.risk_level, models.AttendanceRecoveryRiskLevel.HIGH)
        self.assertEqual(plan.status, models.AttendanceRecoveryPlanStatus.ACTIVE)

        actions = self._actions_by_type()
        self.assertIn(models.AttendanceRecoveryActionType.FACULTY_NUDGE, actions)
        self.assertIn(models.AttendanceRecoveryActionType.REMEDIAL_SLOT, actions)
        self.assertIn(models.AttendanceRecoveryActionType.OFFICE_HOUR_INVITE, actions)
        self.assertIn(models.AttendanceRecoveryActionType.CATCH_UP_TASK, actions)
        self.assertNotIn(models.AttendanceRecoveryActionType.PARENT_ALERT, actions)

        remedial_meta = json.loads(actions[models.AttendanceRecoveryActionType.REMEDIAL_SLOT].metadata_json or "{}")
        catchup_meta = json.loads(actions[models.AttendanceRecoveryActionType.CATCH_UP_TASK].metadata_json or "{}")
        self.assertTrue(bool(remedial_meta.get("mandatory")))
        self.assertTrue(bool(catchup_meta.get("requires_acknowledgement")))
        self.assertEqual(self.db.query(models.RMSCase).count(), 0)

    def test_critical_plan_escalates_to_rms_and_admin_alerts(self):
        self._seed_attendance(
            [
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.ABSENT,
                models.AttendanceStatus.ABSENT,
            ],
            start_offset_days=8,
        )

        plan = evaluate_attendance_recovery(self.db, student_id=101, course_id=301)

        self.assertIsNotNone(plan)
        self.assertEqual(plan.risk_level, models.AttendanceRecoveryRiskLevel.CRITICAL)
        self.assertEqual(plan.status, models.AttendanceRecoveryPlanStatus.ESCALATED)

        rms_case = self.db.query(models.RMSCase).one()
        self.assertEqual(rms_case.category, "Attendance")
        self.assertEqual(rms_case.subject, "Attendance Recovery Autopilot - CSE310")
        self.assertEqual(rms_case.status, models.RMSCaseStatus.TRIAGE)
        self.assertEqual(rms_case.priority, models.RMSCasePriority.CRITICAL)
        self.assertTrue(rms_case.is_escalated)

        actions = self._actions_by_type()
        self.assertIn(models.AttendanceRecoveryActionType.PARENT_ALERT, actions)
        self.assertIn(models.AttendanceRecoveryActionType.CATCH_UP_TASK, actions)
        self.assertIn(models.AttendanceRecoveryActionType.OFFICE_HOUR_INVITE, actions)

        summary, _, _, alerts = _build_admin_payload(self.db, work_date=self.today, mode="enrollment")
        self.assertGreaterEqual(summary.at_risk_students, 1)
        self.assertTrue(any(alert.issue_type == "attendance_recovery" for alert in alerts))

    def test_remedial_completion_marks_recovery_action_completed(self):
        self._seed_attendance(
            [
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.ABSENT,
                models.AttendanceStatus.ABSENT,
            ],
            start_offset_days=8,
        )

        evaluate_attendance_recovery(self.db, student_id=101, course_id=301)
        updated = complete_remedial_recovery_action(self.db, student_id=101, makeup_class_id=601)
        self.db.commit()

        self.assertEqual(updated, 1)
        remedial_action = self._actions_by_type()[models.AttendanceRecoveryActionType.REMEDIAL_SLOT]
        self.assertEqual(remedial_action.status, models.AttendanceRecoveryActionStatus.COMPLETED)
        self.assertEqual(remedial_action.outcome_note, "Student attended the suggested remedial session.")

    def test_plan_is_marked_recovered_after_attendance_improves(self):
        self._seed_attendance(
            [
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.ABSENT,
                models.AttendanceStatus.ABSENT,
            ],
            start_offset_days=8,
        )

        initial_plan = evaluate_attendance_recovery(self.db, student_id=101, course_id=301)
        self.assertIsNotNone(initial_plan)
        self.assertEqual(initial_plan.status, models.AttendanceRecoveryPlanStatus.ACTIVE)

        self._seed_attendance(
            [
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.PRESENT,
            ],
            start_offset_days=3,
        )

        updated_plan = evaluate_attendance_recovery(self.db, student_id=101, course_id=301)
        self.assertIsNotNone(updated_plan)
        self.assertEqual(updated_plan.status, models.AttendanceRecoveryPlanStatus.RECOVERED)
        self.assertIn("recovered", updated_plan.summary.lower())

        active_actions = self._actions_by_type()
        pending_statuses = {
            models.AttendanceRecoveryActionStatus.PENDING,
            models.AttendanceRecoveryActionStatus.ACKNOWLEDGED,
            models.AttendanceRecoveryActionStatus.SENT,
        }
        self.assertFalse(any(action.status in pending_statuses for action in active_actions.values()))

    def test_admin_recovery_list_prioritizes_critical_plan_over_more_recent_watch_plan(self):
        now_dt = datetime.utcnow()
        self.db.add_all(
            [
                models.Student(
                    id=102,
                    name="Student Two",
                    email="student.two@example.com",
                    registration_number="22BCS102",
                    section="P133",
                    department="CSE",
                    semester=4,
                ),
                models.Course(
                    id=302,
                    code="CSE320",
                    title="Distributed Systems",
                    faculty_id=201,
                ),
                models.Enrollment(
                    id=402,
                    student_id=102,
                    course_id=302,
                ),
                models.AttendanceRecoveryPlan(
                    id=901,
                    student_id=101,
                    course_id=301,
                    faculty_id=201,
                    risk_level=models.AttendanceRecoveryRiskLevel.CRITICAL,
                    status=models.AttendanceRecoveryPlanStatus.ESCALATED,
                    attendance_percent=49.0,
                    present_count=2,
                    absent_count=5,
                    delivered_count=7,
                    consecutive_absences=4,
                    missed_remedials=1,
                    parent_alert_allowed=True,
                    recovery_due_at=now_dt - timedelta(days=1),
                    summary="Critical recovery plan.",
                    last_absent_on=self.today - timedelta(days=1),
                    last_evaluated_at=now_dt - timedelta(days=2),
                    updated_at=now_dt - timedelta(days=2),
                ),
                models.AttendanceRecoveryPlan(
                    id=902,
                    student_id=102,
                    course_id=302,
                    faculty_id=201,
                    risk_level=models.AttendanceRecoveryRiskLevel.WATCH,
                    status=models.AttendanceRecoveryPlanStatus.ACTIVE,
                    attendance_percent=78.0,
                    present_count=7,
                    absent_count=2,
                    delivered_count=9,
                    consecutive_absences=1,
                    missed_remedials=0,
                    parent_alert_allowed=False,
                    recovery_due_at=now_dt + timedelta(days=2),
                    summary="Watch recovery plan.",
                    last_absent_on=self.today,
                    last_evaluated_at=now_dt,
                    updated_at=now_dt,
                ),
            ]
        )
        self.db.commit()

        plans = get_admin_recovery_plans(self.db, limit=1)

        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0].id, 901)
        self.assertEqual(plans[0].risk_level, models.AttendanceRecoveryRiskLevel.CRITICAL)

    def test_faculty_recovery_list_prioritizes_critical_plan_over_more_recent_watch_plan(self):
        now_dt = datetime.utcnow()
        self.db.add_all(
            [
                models.Student(
                    id=103,
                    name="Student Three",
                    email="student.three@example.com",
                    registration_number="22BCS103",
                    section="P132",
                    department="CSE",
                    semester=4,
                ),
                models.Student(
                    id=104,
                    name="Student Four",
                    email="student.four@example.com",
                    registration_number="22BCS104",
                    section="P132",
                    department="CSE",
                    semester=4,
                ),
                models.Course(
                    id=303,
                    code="CSE330",
                    title="Cloud Systems",
                    faculty_id=201,
                ),
                models.Course(
                    id=304,
                    code="CSE340",
                    title="Human Computer Interaction",
                    faculty_id=201,
                ),
                models.Enrollment(id=403, student_id=103, course_id=303),
                models.Enrollment(id=404, student_id=104, course_id=304),
                models.AttendanceRecoveryPlan(
                    id=903,
                    student_id=103,
                    course_id=303,
                    faculty_id=201,
                    risk_level=models.AttendanceRecoveryRiskLevel.CRITICAL,
                    status=models.AttendanceRecoveryPlanStatus.ESCALATED,
                    attendance_percent=48.0,
                    present_count=2,
                    absent_count=4,
                    delivered_count=6,
                    consecutive_absences=4,
                    missed_remedials=1,
                    parent_alert_allowed=True,
                    recovery_due_at=now_dt - timedelta(hours=12),
                    summary="Escalated critical plan.",
                    last_absent_on=self.today,
                    last_evaluated_at=now_dt - timedelta(days=1),
                    updated_at=now_dt - timedelta(days=1),
                ),
                models.AttendanceRecoveryPlan(
                    id=904,
                    student_id=104,
                    course_id=304,
                    faculty_id=201,
                    risk_level=models.AttendanceRecoveryRiskLevel.WATCH,
                    status=models.AttendanceRecoveryPlanStatus.ACTIVE,
                    attendance_percent=79.0,
                    present_count=8,
                    absent_count=2,
                    delivered_count=10,
                    consecutive_absences=1,
                    missed_remedials=0,
                    parent_alert_allowed=False,
                    recovery_due_at=now_dt + timedelta(days=4),
                    summary="Recent watch plan.",
                    last_absent_on=self.today,
                    last_evaluated_at=now_dt,
                    updated_at=now_dt,
                ),
            ]
        )
        self.db.commit()

        plans = get_faculty_recovery_plans(self.db, faculty_id=201, limit=1)

        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0].id, 903)
        self.assertEqual(plans[0].risk_level, models.AttendanceRecoveryRiskLevel.CRITICAL)

    @mock.patch("app.attendance_recovery.enqueue_notification", return_value="inline-thread")
    @mock.patch("app.attendance_recovery._safe_send_recovery_email")
    def test_recovery_notifications_when_overall_is_healthy_but_subject_is_below_threshold(
        self,
        _safe_send_recovery_email,
        _enqueue_notification,
    ):
        self.db.add_all(
            [
                models.Course(
                    id=302,
                    code="CSE320",
                    title="Distributed Systems",
                    faculty_id=201,
                ),
                models.Enrollment(
                    id=405,
                    student_id=101,
                    course_id=302,
                ),
            ]
        )
        self.db.commit()

        self._seed_attendance(
            [
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.ABSENT,
            ],
            start_offset_days=4,
        )
        for idx in range(8):
            self.db.add(
                models.AttendanceRecord(
                    id=2000 + idx,
                    student_id=101,
                    course_id=302,
                    marked_by_faculty_id=201,
                    attendance_date=self.today - timedelta(days=7 - idx),
                    status=models.AttendanceStatus.PRESENT if idx < 7 else models.AttendanceStatus.ABSENT,
                    source="seed",
                )
            )
        self.db.commit()

        evaluate_attendance_recovery(self.db, student_id=101, course_id=301)

        calls = _safe_send_recovery_email.call_args_list
        self.assertGreaterEqual(len(calls), 2)
        student_call = next(
            (
                item
                for item in calls
                if str(item.kwargs.get("sent_to") or "").strip() == "student.one@example.com"
            ),
            None,
        )
        faculty_call = next(
            (
                item
                for item in calls
                if str(item.kwargs.get("sent_to") or "").strip() == "faculty.one@example.com"
            ),
            None,
        )
        self.assertIsNotNone(student_call)
        self.assertIsNotNone(faculty_call)
        student_body = str(student_call.kwargs.get("body") or "")
        faculty_body = str(faculty_call.kwargs.get("body") or "")

        self.assertIn("overall attendance is", student_body.lower())
        self.assertIn("specific subjects need immediate attention", student_body.lower())
        self.assertIn("saarthi", student_body.lower())
        self.assertIn("campus resources", student_body.lower())
        self.assertIn("schedule targeted remedial classes", faculty_body.lower())
        self.assertIn("timely short class tests", faculty_body.lower())
        self.assertGreaterEqual(_enqueue_notification.call_count, 2)

    @mock.patch("app.attendance_recovery._dispatch_recovery_communications")
    def test_retro_dispatch_skips_when_recent_notice_exists(self, _dispatch):
        self._seed_attendance(
            [
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.ABSENT,
                models.AttendanceStatus.ABSENT,
            ],
            start_offset_days=8,
        )
        plan = evaluate_attendance_recovery(self.db, student_id=101, course_id=301)
        self.assertIsNotNone(plan)
        _dispatch.reset_mock()
        self.db.add(
            models.NotificationLog(
                student_id=101,
                sent_to="student.one@example.com",
                channel="attendance-recovery-student-email",
                message="Recent recovery alert for CSE310",
                created_at=datetime.utcnow(),
            )
        )
        self.db.commit()

        result = retro_send_recovery_notifications(
            self.db,
            student_id=101,
            course_id=301,
            limit=20,
            force_resend=False,
            dry_run=False,
            refresh_scope=False,
            cooldown_minutes=360,
        )
        self.assertEqual(int(result["evaluated"]), 1)
        self.assertEqual(int(result["eligible"]), 0)
        self.assertEqual(int(result["dispatched"]), 0)
        self.assertEqual(int(result["skipped_cooldown"]), 1)
        _dispatch.assert_not_called()

    @mock.patch("app.attendance_recovery._dispatch_recovery_communications")
    def test_retro_dispatch_cooldown_is_per_student_not_per_course_text(self, _dispatch):
        self._seed_attendance(
            [
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.ABSENT,
                models.AttendanceStatus.ABSENT,
            ],
            start_offset_days=8,
        )
        plan = evaluate_attendance_recovery(self.db, student_id=101, course_id=301)
        self.assertIsNotNone(plan)
        _dispatch.reset_mock()
        self.db.add(
            models.NotificationLog(
                student_id=101,
                sent_to="student.one@example.com",
                channel="attendance-recovery-student-email",
                message="Recent recovery alert without the current course code",
                created_at=datetime.utcnow(),
            )
        )
        self.db.commit()

        result = retro_send_recovery_notifications(
            self.db,
            student_id=101,
            course_id=301,
            limit=20,
            force_resend=False,
            dry_run=False,
            refresh_scope=False,
            cooldown_minutes=360,
        )
        self.assertEqual(int(result["evaluated"]), 1)
        self.assertEqual(int(result["eligible"]), 0)
        self.assertEqual(int(result["dispatched"]), 0)
        self.assertEqual(int(result["skipped_cooldown"]), 1)
        _dispatch.assert_not_called()

    @mock.patch("app.attendance_recovery._dispatch_recovery_communications")
    def test_retro_dispatch_force_resend_bypasses_cooldown(self, _dispatch):
        self._seed_attendance(
            [
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.ABSENT,
                models.AttendanceStatus.ABSENT,
            ],
            start_offset_days=8,
        )
        plan = evaluate_attendance_recovery(self.db, student_id=101, course_id=301)
        self.assertIsNotNone(plan)
        _dispatch.reset_mock()
        self.db.add(
            models.NotificationLog(
                student_id=101,
                sent_to="student.one@example.com",
                channel="attendance-recovery-student-email",
                message="Recent recovery alert for CSE310",
                created_at=datetime.utcnow(),
            )
        )
        self.db.commit()

        result = retro_send_recovery_notifications(
            self.db,
            student_id=101,
            course_id=301,
            limit=20,
            force_resend=True,
            dry_run=False,
            refresh_scope=False,
            cooldown_minutes=360,
        )
        self.assertEqual(int(result["evaluated"]), 1)
        self.assertEqual(int(result["eligible"]), 1)
        self.assertEqual(int(result["dispatched"]), 1)
        self.assertEqual(int(result["skipped_cooldown"]), 0)
        _dispatch.assert_called_once()

    @mock.patch("app.attendance_recovery.send_notification_email", return_value={"channel": "smtp-email"})
    def test_recovery_email_logs_logical_channel_for_cooldown(self, _send_notification_email):
        with mock.patch.dict(os.environ, {"PYTEST_CURRENT_TEST": ""}):
            os.environ.pop("PYTEST_CURRENT_TEST", None)
            _safe_send_recovery_email(
                self.db,
                student_id=101,
                sent_to="student.one@example.com",
                subject="[Attendance Recovery] Action required for CSE310 (62.5%)",
                body="Recovery mail body",
                channel="attendance-recovery-student-email",
            )
        self.db.commit()

        rows = (
            self.db.query(models.NotificationLog)
            .filter(models.NotificationLog.student_id == 101)
            .order_by(models.NotificationLog.id.desc())
            .all()
        )
        self.assertTrue(rows)
        self.assertEqual(rows[0].channel, "attendance-recovery-student-email")
        self.assertIn("[delivery-backend:smtp-email]", rows[0].message)
        self.assertTrue(
            _recent_recovery_notice_exists_any(
                self.db,
                student_id=101,
                channel="attendance-recovery-student-email",
                cooldown_minutes=1440,
            )
        )

    @mock.patch("app.attendance_recovery.send_notification_email", return_value={"channel": "smtp-email"})
    def test_recovery_email_send_layer_blocks_second_mail_within_24_hours(self, _send_notification_email):
        with mock.patch.dict(os.environ, {"PYTEST_CURRENT_TEST": ""}):
            os.environ.pop("PYTEST_CURRENT_TEST", None)
            first_sent = _safe_send_recovery_email(
                self.db,
                student_id=101,
                sent_to="student.one@example.com",
                subject="[Attendance Recovery] First alert",
                body="First recovery mail body",
                channel="attendance-recovery-student-email",
            )
            second_sent = _safe_send_recovery_email(
                self.db,
                student_id=101,
                sent_to="student.one@example.com",
                subject="[Attendance Recovery] Duplicate alert",
                body="Duplicate recovery mail body",
                channel="attendance-recovery-student-email",
            )
        self.db.commit()

        self.assertTrue(first_sent)
        self.assertFalse(second_sent)
        _send_notification_email.assert_called_once()
        rows = (
            self.db.query(models.NotificationLog)
            .filter(
                models.NotificationLog.student_id == 101,
                models.NotificationLog.channel == "attendance-recovery-student-email",
            )
            .all()
        )
        self.assertEqual(len(rows), 1)
        self.assertIn("First alert", rows[0].message)

    def test_student_recovery_plan_read_does_not_recompute_or_dispatch(self):
        self._seed_attendance(
            [
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.ABSENT,
                models.AttendanceStatus.ABSENT,
            ],
            start_offset_days=8,
        )
        plan = evaluate_attendance_recovery(self.db, student_id=101, course_id=301)
        self.assertIsNotNone(plan)

        with mock.patch("app.routers.attendance.recompute_attendance_recovery_scope") as recompute_scope:
            payload = get_student_recovery_plan_list(
                include_resolved=False,
                limit=12,
                db=self.db,
                current_user=self.db.get(models.AuthUser, 801),
            )

        recompute_scope.assert_not_called()
        self.assertEqual(len(payload.plans), 1)
        self.assertEqual(payload.plans[0].course_code, "CSE310")


if __name__ == "__main__":
    unittest.main()
