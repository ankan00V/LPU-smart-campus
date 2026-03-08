import unittest
from datetime import date, datetime, time, timedelta
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.routers.admin import (
    rms_apply_query_action,
    governance_break_glass_access,
    governance_break_glass_logs,
    governance_delegate_role,
    governance_upsert_policy,
    rms_case_audit_timeline,
    rms_create_attendance_correction,
    rms_escalate_expired_cases,
    rms_list_cases,
    rms_review_attendance_correction,
    rms_transition_case,
)
from app.routers.food import vendor_dashboard
from app.routers.food import vendor_reconciliation_list, vendor_reconciliation_resolve
from app.routers.messages import (
    get_student_support_case_timeline,
    get_student_support_case_tracker,
    reopen_student_support_case,
)


class RoleWiseEnhancementTests(unittest.TestCase):
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
        now_dt = datetime.utcnow()
        self.today = date.today()
        self.student_id = 101
        self.faculty_id = 11
        self.course_id = 501
        self.owner_user_id = 901
        self.admin_user_id = 1

        self.db.add_all(
            [
                models.Student(
                    id=self.student_id,
                    name="Student Lifecycle",
                    email="student.lifecycle@example.com",
                    registration_number="22BCS777",
                    section="P132",
                    department="CSE",
                    semester=4,
                ),
                models.Faculty(
                    id=self.faculty_id,
                    name="Faculty Lifecycle",
                    email="faculty.lifecycle@example.com",
                    section="P132",
                    department="CSE",
                ),
                models.Course(
                    id=self.course_id,
                    code="CSE501",
                    title="Operating Systems",
                    faculty_id=self.faculty_id,
                ),
                models.Enrollment(
                    id=1701,
                    student_id=self.student_id,
                    course_id=self.course_id,
                ),
                models.ClassSchedule(
                    id=1801,
                    course_id=self.course_id,
                    faculty_id=self.faculty_id,
                    weekday=self.today.weekday(),
                    start_time=time(10, 0),
                    end_time=time(11, 0),
                    classroom_label="34-101",
                    is_active=True,
                ),
                models.SupportQueryMessage(
                    id=1901,
                    student_id=self.student_id,
                    faculty_id=self.faculty_id,
                    section="P132",
                    category=schemas.SupportQueryCategory.ATTENDANCE.value,
                    subject="Attendance discrepancy",
                    message="I was marked absent but I attended class.",
                    sender_role=models.UserRole.STUDENT.value,
                    created_at=now_dt - timedelta(minutes=20),
                    read_at=None,
                ),
                models.AuthUser(
                    id=self.admin_user_id,
                    email="super.admin@example.com",
                    password_hash="x",
                    role=models.UserRole.ADMIN,
                    student_id=None,
                    faculty_id=None,
                    is_active=True,
                ),
                models.AuthUser(
                    id=2,
                    email="faculty.user@example.com",
                    password_hash="x",
                    role=models.UserRole.FACULTY,
                    student_id=None,
                    faculty_id=self.faculty_id,
                    is_active=True,
                ),
                models.AuthUser(
                    id=3,
                    email="student.user@example.com",
                    password_hash="x",
                    role=models.UserRole.STUDENT,
                    student_id=self.student_id,
                    faculty_id=None,
                    is_active=True,
                ),
                models.AuthUser(
                    id=self.owner_user_id,
                    email="owner.vendor@example.com",
                    password_hash="x",
                    role=models.UserRole.OWNER,
                    student_id=None,
                    faculty_id=None,
                    is_active=True,
                ),
                models.AuthUser(
                    id=99,
                    email="target.user@example.com",
                    password_hash="x",
                    role=models.UserRole.STUDENT,
                    student_id=None,
                    faculty_id=None,
                    is_active=True,
                ),
                models.FoodShop(
                    id=7001,
                    name="Crunch Corner",
                    block="B1",
                    owner_user_id=self.owner_user_id,
                    is_active=True,
                    is_popular=True,
                    rating=4.3,
                    average_prep_minutes=15,
                    created_at=now_dt - timedelta(days=40),
                    updated_at=now_dt - timedelta(days=1),
                ),
                models.FoodOrder(
                    id=7101,
                    student_id=self.student_id,
                    shop_id=7001,
                    menu_item_id=None,
                    food_item_id=1,
                    slot_id=1,
                    order_date=self.today,
                    quantity=1,
                    unit_price=80.0,
                    total_price=80.0,
                    status=models.FoodOrderStatus.DELIVERED,
                    shop_name="Crunch Corner",
                    shop_block="B1",
                    payment_status="paid",
                    payment_reference="PAY-7101",
                    location_verified=True,
                    preparing_at=now_dt - timedelta(minutes=50),
                    out_for_delivery_at=now_dt - timedelta(minutes=25),
                    delivered_at=now_dt - timedelta(minutes=5),
                    estimated_ready_at=now_dt - timedelta(minutes=10),
                    delivery_eta_minutes=20,
                    last_status_updated_at=now_dt - timedelta(minutes=5),
                    created_at=now_dt - timedelta(minutes=70),
                ),
                models.FoodOrder(
                    id=7102,
                    student_id=self.student_id,
                    shop_id=7001,
                    menu_item_id=None,
                    food_item_id=2,
                    slot_id=1,
                    order_date=self.today,
                    quantity=1,
                    unit_price=120.0,
                    total_price=120.0,
                    status=models.FoodOrderStatus.CANCELLED,
                    shop_name="Crunch Corner",
                    shop_block="B1",
                    payment_status="paid",
                    payment_reference="PAY-7102",
                    location_verified=False,
                    last_status_updated_at=now_dt - timedelta(minutes=10),
                    created_at=now_dt - timedelta(minutes=30),
                ),
                models.FoodPayment(
                    id=7201,
                    student_id=self.student_id,
                    amount=80.0,
                    currency="INR",
                    provider="sandbox",
                    payment_reference="PAY-7101",
                    order_state="captured",
                    payment_state="captured",
                    status="paid",
                    order_ids_json="[7101]",
                    created_at=now_dt - timedelta(minutes=50),
                    updated_at=now_dt - timedelta(minutes=5),
                ),
                models.FoodPayment(
                    id=7202,
                    student_id=self.student_id,
                    amount=120.0,
                    currency="INR",
                    provider="sandbox",
                    payment_reference="PAY-7102",
                    order_state="failed",
                    payment_state="failed",
                    status="failed",
                    failed_reason="gateway timeout",
                    order_ids_json="[7102]",
                    created_at=now_dt - timedelta(minutes=30),
                    updated_at=now_dt - timedelta(minutes=10),
                ),
            ]
        )
        self.db.commit()

    @staticmethod
    def _user(user_id: int, role: models.UserRole, *, student_id: int | None = None, faculty_id: int | None = None, email: str | None = None):
        return models.AuthUser(
            id=user_id,
            email=email or f"{role.value}.{user_id}@example.com",
            password_hash="x",
            role=role,
            student_id=student_id,
            faculty_id=faculty_id,
            is_active=True,
        )

    @patch("app.routers.admin.mirror_document", return_value=True)
    def test_rms_case_lifecycle_and_escalation(self, _mirror):
        admin = self._user(self.admin_user_id, models.UserRole.ADMIN, email="super.admin@example.com")

        listed = rms_list_cases(
            status="all",
            category="all",
            priority="all",
            escalated_only=False,
            queue_only=False,
            auto_sync=True,
            limit=200,
            db=self.db,
            current_user=admin,
        )
        self.assertGreaterEqual(listed.total, 1)
        case_id = listed.cases[0].id

        with self.assertRaises(HTTPException) as ctx:
            rms_transition_case(
                case_id=case_id,
                payload=schemas.RMSCaseTransitionRequest(action=schemas.RMSCaseAction.CLOSE, note="Invalid close"),
                db=self.db,
                current_user=admin,
            )
        self.assertEqual(ctx.exception.status_code, 409)

        triaged = rms_transition_case(
            case_id=case_id,
            payload=schemas.RMSCaseTransitionRequest(action=schemas.RMSCaseAction.TRIAGE, note="Triaged by admin"),
            db=self.db,
            current_user=admin,
        )
        self.assertEqual(triaged.status, models.RMSCaseStatus.TRIAGE)

        assigned = rms_transition_case(
            case_id=case_id,
            payload=schemas.RMSCaseTransitionRequest(
                action=schemas.RMSCaseAction.ASSIGN,
                note="Assigned to analyst",
                assign_to_user_id=self.admin_user_id,
            ),
            db=self.db,
            current_user=admin,
        )
        self.assertEqual(assigned.status, models.RMSCaseStatus.ASSIGNED)
        self.assertEqual(assigned.assigned_to_user_id, self.admin_user_id)

        row = self.db.get(models.RMSCase, case_id)
        row.first_response_due_at = datetime.utcnow() - timedelta(hours=1)
        row.resolution_due_at = datetime.utcnow() - timedelta(minutes=10)
        row.first_responded_at = None
        row.closed_at = None
        row.is_escalated = False
        self.db.commit()

        sweep = rms_escalate_expired_cases(
            limit=1000,
            db=self.db,
            current_user=admin,
        )
        self.assertGreaterEqual(int(sweep["escalated"]), 1)

        timeline = rms_case_audit_timeline(
            case_id=case_id,
            db=self.db,
            current_user=admin,
        )
        self.assertGreaterEqual(len(timeline.timeline), 3)

    @patch("app.routers.admin.mirror_document", return_value=True)
    def test_rms_assignment_requires_valid_assignee(self, _mirror):
        admin = self._user(self.admin_user_id, models.UserRole.ADMIN, email="super.admin@example.com")
        listed = rms_list_cases(
            status="all",
            category="all",
            priority="all",
            escalated_only=False,
            queue_only=False,
            auto_sync=True,
            limit=200,
            db=self.db,
            current_user=admin,
        )
        self.assertGreaterEqual(listed.total, 1)
        case_id = listed.cases[0].id

        rms_transition_case(
            case_id=case_id,
            payload=schemas.RMSCaseTransitionRequest(action=schemas.RMSCaseAction.TRIAGE, note="Triaged by admin"),
            db=self.db,
            current_user=admin,
        )
        with self.assertRaises(HTTPException) as ctx:
            rms_transition_case(
                case_id=case_id,
                payload=schemas.RMSCaseTransitionRequest(
                    action=schemas.RMSCaseAction.ASSIGN,
                    note="Invalid assignee id",
                    assign_to_user_id=999999,
                ),
                db=self.db,
                current_user=admin,
            )
        self.assertEqual(ctx.exception.status_code, 404)

    @patch("app.routers.admin.mirror_document", return_value=True)
    def test_faculty_cannot_assign_case_to_other_user(self, _mirror):
        faculty_user = self._user(2, models.UserRole.FACULTY, faculty_id=self.faculty_id)
        listed = rms_list_cases(
            status="all",
            category="all",
            priority="all",
            escalated_only=False,
            queue_only=False,
            auto_sync=True,
            limit=200,
            db=self.db,
            current_user=faculty_user,
        )
        self.assertGreaterEqual(listed.total, 1)
        case_id = listed.cases[0].id

        rms_transition_case(
            case_id=case_id,
            payload=schemas.RMSCaseTransitionRequest(action=schemas.RMSCaseAction.TRIAGE, note="Faculty triage"),
            db=self.db,
            current_user=faculty_user,
        )
        with self.assertRaises(HTTPException) as ctx:
            rms_transition_case(
                case_id=case_id,
                payload=schemas.RMSCaseTransitionRequest(
                    action=schemas.RMSCaseAction.ASSIGN,
                    note="Faculty cannot assign to admin",
                    assign_to_user_id=self.admin_user_id,
                ),
                db=self.db,
                current_user=faculty_user,
            )
        self.assertEqual(ctx.exception.status_code, 403)

    @patch("app.routers.admin.mirror_document", return_value=True)
    def test_legacy_query_action_updates_case_lifecycle(self, _mirror):
        admin = self._user(self.admin_user_id, models.UserRole.ADMIN, email="super.admin@example.com")
        action_out = rms_apply_query_action(
            payload=schemas.RMSQueryActionRequest(
                student_id=self.student_id,
                faculty_id=self.faculty_id,
                category=schemas.SupportQueryCategory.ATTENDANCE,
                action=schemas.RMSQueryWorkflowAction.SCHEDULE,
                note="Schedule review",
                scheduled_for=datetime.utcnow() + timedelta(hours=4),
            ),
            db=self.db,
            current_user=admin,
        )
        self.assertEqual(action_out.thread.action_state, schemas.RMSQueryActionState.SCHEDULED)

        cases = rms_list_cases(
            status="all",
            category="Attendance",
            priority="all",
            escalated_only=False,
            queue_only=False,
            auto_sync=False,
            limit=100,
            db=self.db,
            current_user=admin,
        )
        self.assertGreaterEqual(cases.total, 1)
        self.assertEqual(cases.cases[0].status, models.RMSCaseStatus.ASSIGNED)

    @patch("app.routers.admin.mirror_document", return_value=True)
    def test_attendance_correction_high_impact_approval_chain(self, _mirror):
        faculty_user = self._user(2, models.UserRole.FACULTY, faculty_id=self.faculty_id)
        admin_user = self._user(self.admin_user_id, models.UserRole.ADMIN, email="super.admin@example.com")

        created = rms_create_attendance_correction(
            payload=schemas.RMSAttendanceCorrectionCreateRequest(
                registration_number="22BCS777",
                course_code="CSE501",
                attendance_date=self.today,
                requested_status=models.AttendanceStatus.PRESENT,
                reason="Camera failed during class, class notes and witness attached.",
                evidence_ref="https://evidence.local/doc/12345",
            ),
            db=self.db,
            current_user=faculty_user,
        )
        self.assertEqual(created.status, models.RMSAttendanceCorrectionStatus.PENDING_ADMIN_APPROVAL)
        self.assertTrue(created.is_high_impact)

        reviewed = rms_review_attendance_correction(
            request_id=created.id,
            payload=schemas.RMSAttendanceCorrectionReviewRequest(
                action=schemas.RMSAttendanceCorrectionReviewAction.APPROVE,
                review_note="Validated evidence and approved.",
            ),
            db=self.db,
            current_user=admin_user,
        )
        self.assertEqual(reviewed.status, models.RMSAttendanceCorrectionStatus.APPLIED)
        self.assertIsNotNone(reviewed.applied_record_id)

        attendance_row = (
            self.db.query(models.AttendanceRecord)
            .filter(
                models.AttendanceRecord.student_id == self.student_id,
                models.AttendanceRecord.course_id == self.course_id,
                models.AttendanceRecord.attendance_date == self.today,
            )
            .first()
        )
        self.assertIsNotNone(attendance_row)
        self.assertEqual(attendance_row.status, models.AttendanceStatus.PRESENT)

    def test_student_request_tracker_timeline_and_reopen(self):
        student_user = self._user(3, models.UserRole.STUDENT, student_id=self.student_id)

        tracker = get_student_support_case_tracker(
            include_closed=True,
            limit=200,
            db=self.db,
            current_user=student_user,
        )
        self.assertGreaterEqual(tracker.total, 1)
        case_id = tracker.cases[0].id

        row = self.db.get(models.RMSCase, case_id)
        row.status = models.RMSCaseStatus.CLOSED
        row.closed_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
        self.db.commit()

        reopened = reopen_student_support_case(
            case_id=case_id,
            payload=schemas.RMSCaseReopenRequest(
                note="I dispute this closure because the issue persists.",
                evidence_ref="https://evidence.local/reopen/001",
            ),
            db=self.db,
            current_user=student_user,
        )
        self.assertEqual(reopened.status, models.RMSCaseStatus.NEW)
        self.assertGreaterEqual(reopened.reopened_count, 1)

        timeline = get_student_support_case_timeline(
            case_id=case_id,
            db=self.db,
            current_user=student_user,
        )
        self.assertTrue(any(item.action == "student_reopen" for item in timeline.timeline))

    @patch("app.routers.admin.SUPER_ADMIN_EMAILS", new={"super.admin@example.com"})
    @patch("app.routers.admin.mirror_document", return_value=True)
    def test_super_admin_governance_controls(self, _mirror):
        super_admin = self._user(self.admin_user_id, models.UserRole.ADMIN, email="super.admin@example.com")

        policy = governance_upsert_policy(
            policy_key="rms.case.sla",
            payload=schemas.GovernancePolicyUpsertRequest(value={"first_response_hours": 2, "resolution_hours": 12}),
            db=self.db,
            current_user=super_admin,
        )
        self.assertEqual(policy.key, "rms.case.sla")
        self.assertEqual(policy.value.get("first_response_hours"), 2)

        delegated = governance_delegate_role(
            payload=schemas.GovernanceRoleDelegationRequest(
                target_user_id=99,
                target_role=models.UserRole.OWNER,
                reason="Temporary ownership for reconciliation.",
            ),
            db=self.db,
            current_user=super_admin,
        )
        self.assertEqual(delegated.target_user_id, 99)
        self.assertEqual(delegated.to_role, models.UserRole.OWNER)
        target_user = self.db.get(models.AuthUser, 99)
        self.assertEqual(target_user.role, models.UserRole.OWNER)

        opened = governance_break_glass_access(
            payload=schemas.GovernanceBreakGlassRequest(
                reason="Emergency access to unblock SLA incident.",
                scope="rms-governance",
                expires_in_minutes=30,
                ticket_ref="INC-1001",
            ),
            db=self.db,
            current_user=super_admin,
        )
        self.assertEqual(opened.scope, "rms-governance")
        logs = governance_break_glass_logs(
            limit=50,
            active_only=False,
            db=self.db,
            current_user=super_admin,
        )
        self.assertGreaterEqual(logs.total, 1)

    def test_owner_vendor_dashboard(self):
        owner_user = self._user(self.owner_user_id, models.UserRole.OWNER)
        out = vendor_dashboard(
            start_date=self.today - timedelta(days=1),
            end_date=self.today,
            db=self.db,
            current_user=owner_user,
        )
        self.assertEqual(out.shops, 1)
        self.assertEqual(out.fulfillment.total_orders, 2)
        self.assertGreaterEqual(out.billing.gross_amount, 200.0)
        self.assertGreaterEqual(out.sla.monitored_orders, 1)
        self.assertIsInstance(out.compliance_flags, list)

    @patch("app.routers.food.mirror_event", return_value=True)
    @patch("app.routers.food.mirror_document", return_value=True)
    def test_vendor_reconciliation_controls(self, _mirror_document, _mirror_event):
        owner_user = self._user(self.owner_user_id, models.UserRole.OWNER)
        issues = vendor_reconciliation_list(
            start_date=self.today - timedelta(days=1),
            end_date=self.today,
            include_resolved=False,
            limit=200,
            db=self.db,
            current_user=owner_user,
        )
        self.assertGreaterEqual(issues.total_issues, 1)
        target_ids = [issues.items[0].order_id]

        resolved = vendor_reconciliation_resolve(
            payload=schemas.VendorReconciliationResolveRequest(
                order_ids=target_ids,
                note="Payment reconciled by vendor finance team.",
            ),
            db=self.db,
            current_user=owner_user,
        )
        self.assertEqual(resolved.resolved, 1)
        self.assertEqual(resolved.order_ids, target_ids)

    @patch("app.routers.food.mirror_event", return_value=True)
    @patch("app.routers.food.mirror_document", return_value=True)
    def test_vendor_reconciliation_resolve_rejects_non_issue_orders(self, _mirror_document, _mirror_event):
        owner_user = self._user(self.owner_user_id, models.UserRole.OWNER)
        with self.assertRaises(HTTPException) as ctx:
            vendor_reconciliation_resolve(
                payload=schemas.VendorReconciliationResolveRequest(
                    order_ids=[7101],
                    note="Attempting to resolve a clean order should fail.",
                ),
                db=self.db,
                current_user=owner_user,
            )
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertIn("do not have reconciliation issues", str(ctx.exception.detail))

    @patch("app.routers.food.mirror_event", side_effect=RuntimeError("broker down"))
    @patch("app.routers.food.mirror_document", side_effect=RuntimeError("mongo down"))
    def test_vendor_reconciliation_resolve_survives_audit_mirror_failures(self, _mirror_document, _mirror_event):
        owner_user = self._user(self.owner_user_id, models.UserRole.OWNER)
        issues = vendor_reconciliation_list(
            start_date=self.today - timedelta(days=1),
            end_date=self.today,
            include_resolved=False,
            limit=200,
            db=self.db,
            current_user=owner_user,
        )
        self.assertGreaterEqual(issues.total_issues, 1)

        resolved = vendor_reconciliation_resolve(
            payload=schemas.VendorReconciliationResolveRequest(
                order_ids=[issues.items[0].order_id],
                note="Resolve while mirror sinks are temporarily unavailable.",
            ),
            db=self.db,
            current_user=owner_user,
        )
        self.assertEqual(resolved.resolved, 1)


if __name__ == "__main__":
    unittest.main()
