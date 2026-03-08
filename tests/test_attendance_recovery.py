import json
import unittest
from datetime import date, datetime, time, timedelta
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.attendance_recovery import (
    complete_remedial_recovery_action,
    evaluate_attendance_recovery,
    get_admin_recovery_plans,
    get_faculty_recovery_plans,
)
from app.routers.admin import _build_admin_payload


class AttendanceRecoveryWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        SessionLocal = sessionmaker(bind=self.engine)
        self.db = SessionLocal()
        self.today = date.today()
        self.future_makeup_date = self.today + timedelta(days=1)
        self._seed_base()

    def tearDown(self):
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
                models.AttendanceStatus.ABSENT,
            ],
            start_offset_days=3,
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
        self.assertEqual(
            actions[models.AttendanceRecoveryActionType.FACULTY_NUDGE].status,
            models.AttendanceRecoveryActionStatus.PENDING,
        )

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
        self.assertEqual(
            actions[models.AttendanceRecoveryActionType.FACULTY_NUDGE].status,
            models.AttendanceRecoveryActionStatus.PENDING,
        )

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
        self.assertEqual(
            actions[models.AttendanceRecoveryActionType.PARENT_ALERT].status,
            models.AttendanceRecoveryActionStatus.PENDING,
        )

        summary, _, _, alerts = _build_admin_payload(self.db, work_date=self.today, mode="enrollment")
        self.assertGreaterEqual(summary.at_risk_students, 1)
        self.assertTrue(any(alert.issue_type == "attendance_recovery" for alert in alerts))

    def test_recovery_notifications_enqueue_only_after_commit(self):
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

        with mock.patch("app.workers.enqueue_notification") as mocked_enqueue:
            evaluate_attendance_recovery(self.db, student_id=101, course_id=301)

            self.assertEqual(mocked_enqueue.call_count, 0)
            self.assertEqual(self.db.query(models.NotificationLog).count(), 0)

            self.db.commit()

        self.assertEqual(mocked_enqueue.call_count, 1)
        payload = mocked_enqueue.call_args.args[0]
        self.assertEqual(payload["type"], "attendance_recovery_faculty_alert")
        self.assertEqual(payload["student_id"], 101)
        self.assertEqual(payload["recipient_email"], "faculty.one@example.com")
        self.assertEqual(payload["log_channel"], "attendance-recovery-faculty")
        self.assertEqual(self.db.query(models.NotificationLog).count(), 0)

    def test_critical_recovery_parent_alert_enqueues_on_commit_and_clears_on_rollback(self):
        self._seed_attendance(
            [
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.PRESENT,
                models.AttendanceStatus.ABSENT,
                models.AttendanceStatus.ABSENT,
            ],
            start_offset_days=8,
        )

        with mock.patch("app.workers.enqueue_notification") as mocked_enqueue:
            evaluate_attendance_recovery(self.db, student_id=101, course_id=301)
            self.assertEqual(mocked_enqueue.call_count, 0)

            self.db.rollback()
            self.assertEqual(mocked_enqueue.call_count, 0)

            evaluate_attendance_recovery(self.db, student_id=101, course_id=301)
            self.db.commit()

        notification_types = [call.args[0]["type"] for call in mocked_enqueue.call_args_list]
        self.assertEqual(notification_types.count("attendance_recovery_faculty_alert"), 1)
        self.assertEqual(notification_types.count("attendance_recovery_parent_alert"), 1)

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


if __name__ == "__main__":
    unittest.main()
