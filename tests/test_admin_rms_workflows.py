import unittest
from datetime import date, datetime, time, timedelta
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.routers.admin import (
    rms_apply_query_action,
    rms_attendance_student_context,
    rms_update_attendance_status,
    rms_queries_dashboard,
    rms_search_student_by_registration,
    rms_update_student_profile,
)


class AdminRmsFlowTests(unittest.TestCase):
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
        self.db.add_all(
            [
                models.Faculty(
                    id=11,
                    name="Faculty One",
                    email="faculty.one@example.com",
                    section="P132",
                    department="CSE",
                ),
                models.Faculty(
                    id=12,
                    name="Faculty Two",
                    email="faculty.two@example.com",
                    section="P200",
                    department="CSE",
                ),
                models.Student(
                    id=101,
                    name="Student One",
                    email="student.one@example.com",
                    registration_number="22BCS101",
                    section="P132",
                    department="CSE",
                    semester=4,
                ),
                models.Student(
                    id=102,
                    name="Student Two",
                    email="student.two@example.com",
                    registration_number="22BCS102",
                    section="P200",
                    department="CSE",
                    semester=4,
                ),
                models.Course(
                    id=501,
                    code="CSE101",
                    title="Data Structures",
                    faculty_id=11,
                ),
                models.Course(
                    id=502,
                    code="ECE210",
                    title="Signals",
                    faculty_id=12,
                ),
                models.Enrollment(
                    id=1501,
                    student_id=101,
                    course_id=501,
                ),
                models.Enrollment(
                    id=1502,
                    student_id=101,
                    course_id=502,
                ),
                models.ClassSchedule(
                    id=1701,
                    course_id=501,
                    faculty_id=11,
                    weekday=date.today().weekday(),
                    start_time=time(10, 0),
                    end_time=time(11, 0),
                    classroom_label="34-101",
                    is_active=True,
                ),
                models.ClassSchedule(
                    id=1702,
                    course_id=502,
                    faculty_id=12,
                    weekday=date.today().weekday(),
                    start_time=time(11, 0),
                    end_time=time(12, 0),
                    classroom_label="34-102",
                    is_active=True,
                ),
                models.AttendanceRecord(
                    id=2201,
                    student_id=101,
                    course_id=501,
                    marked_by_faculty_id=11,
                    attendance_date=date.today(),
                    status=models.AttendanceStatus.PRESENT,
                    source="seed",
                ),
                models.SupportQueryMessage(
                    id=1001,
                    student_id=101,
                    faculty_id=11,
                    section="P132",
                    category=schemas.SupportQueryCategory.ATTENDANCE.value,
                    subject="Attendance Query",
                    message="Marked absent incorrectly.",
                    sender_role=models.UserRole.STUDENT.value,
                    created_at=now_dt - timedelta(minutes=15),
                    read_at=None,
                ),
                models.SupportQueryMessage(
                    id=1002,
                    student_id=101,
                    faculty_id=11,
                    section="P132",
                    category=schemas.SupportQueryCategory.ATTENDANCE.value,
                    subject="Attendance Query",
                    message="Will review it now.",
                    sender_role=models.UserRole.FACULTY.value,
                    created_at=now_dt - timedelta(minutes=10),
                    read_at=now_dt - timedelta(minutes=9),
                ),
                models.SupportQueryMessage(
                    id=1003,
                    student_id=102,
                    faculty_id=12,
                    section="P200",
                    category=schemas.SupportQueryCategory.DISCREPANCY.value,
                    subject="Registration mismatch",
                    message="Registration number is wrong in profile.",
                    sender_role=models.UserRole.STUDENT.value,
                    created_at=now_dt - timedelta(minutes=5),
                    read_at=None,
                ),
            ]
        )
        self.db.commit()

    @staticmethod
    def _user(role: models.UserRole, *, user_id: int, faculty_id: int | None = None) -> models.AuthUser:
        return models.AuthUser(
            id=user_id,
            email=f"{role.value}{user_id}@example.com",
            password_hash="x",
            role=role,
            student_id=None,
            faculty_id=faculty_id,
            is_active=True,
        )

    def test_admin_gets_rms_queries_segregated_by_category(self):
        out = rms_queries_dashboard(
            category="all",
            status="all",
            limit=200,
            db=self.db,
            current_user=self._user(models.UserRole.ADMIN, user_id=1),
        )
        self.assertEqual(out.total_threads, 2)
        self.assertGreaterEqual(out.total_pending, 1)

        by_category = {bucket.category.value: bucket for bucket in out.categories}
        self.assertEqual(by_category["Attendance"].total_threads, 1)
        self.assertEqual(by_category["Discrepancy"].total_threads, 1)

    def test_faculty_scope_limited_in_rms_queries(self):
        out = rms_queries_dashboard(
            category="all",
            status="all",
            limit=200,
            db=self.db,
            current_user=self._user(models.UserRole.FACULTY, user_id=2, faculty_id=11),
        )
        self.assertEqual(out.total_threads, 1)
        attendance_bucket = next((bucket for bucket in out.categories if bucket.category.value == "Attendance"), None)
        self.assertIsNotNone(attendance_bucket)
        self.assertEqual(attendance_bucket.total_threads, 1)

    def test_faculty_search_blocks_student_outside_scope(self):
        with self.assertRaises(HTTPException) as ctx:
            rms_search_student_by_registration(
                registration_number="22BCS102",
                db=self.db,
                current_user=self._user(models.UserRole.FACULTY, user_id=3, faculty_id=11),
            )
        self.assertEqual(ctx.exception.status_code, 403)

    def test_admin_search_and_update_registration_and_section(self):
        with patch("app.routers.admin.mirror_document", return_value=True):
            out = rms_update_student_profile(
                student_id=101,
                payload=schemas.RMSStudentUpdateRequest(
                    registration_number="22BCS555",
                    section="P300",
                ),
                db=self.db,
                current_user=self._user(models.UserRole.ADMIN, user_id=4),
            )
        self.assertIn("registration_number", out.changed_fields)
        self.assertIn("section", out.changed_fields)

        refreshed = self.db.get(models.Student, 101)
        self.assertEqual(refreshed.registration_number, "22BCS555")
        self.assertEqual(refreshed.section, "P300")

    def test_faculty_cannot_update_section_outside_own_scope(self):
        with self.assertRaises(HTTPException) as ctx:
            rms_update_student_profile(
                student_id=101,
                payload=schemas.RMSStudentUpdateRequest(section="P200"),
                db=self.db,
                current_user=self._user(models.UserRole.FACULTY, user_id=5, faculty_id=11),
            )
        self.assertEqual(ctx.exception.status_code, 403)

    def test_admin_can_schedule_thread_and_dashboard_reflects_action_state(self):
        scheduled_for = datetime.utcnow() + timedelta(days=1)
        out = rms_apply_query_action(
            payload=schemas.RMSQueryActionRequest(
                student_id=101,
                faculty_id=11,
                category=schemas.SupportQueryCategory.ATTENDANCE,
                action=schemas.RMSQueryWorkflowAction.SCHEDULE,
                note="Meet in admin office",
                scheduled_for=scheduled_for,
            ),
            db=self.db,
            current_user=self._user(models.UserRole.ADMIN, user_id=10),
        )
        self.assertEqual(out.thread.action_state, schemas.RMSQueryActionState.SCHEDULED)
        self.assertFalse(out.thread.pending_action)
        self.assertIsNotNone(out.thread.scheduled_for)

        dashboard = rms_queries_dashboard(
            category="Attendance",
            status="all",
            limit=50,
            db=self.db,
            current_user=self._user(models.UserRole.ADMIN, user_id=10),
        )
        bucket = next((item for item in dashboard.categories if item.category == schemas.SupportQueryCategory.ATTENDANCE), None)
        self.assertIsNotNone(bucket)
        self.assertEqual(len(bucket.threads), 1)
        thread = bucket.threads[0]
        self.assertEqual(thread.action_state, schemas.RMSQueryActionState.SCHEDULED)
        self.assertFalse(thread.pending_action)

    def test_faculty_cannot_action_other_faculty_thread(self):
        with self.assertRaises(HTTPException) as ctx:
            rms_apply_query_action(
                payload=schemas.RMSQueryActionRequest(
                    student_id=102,
                    faculty_id=12,
                    category=schemas.SupportQueryCategory.DISCREPANCY,
                    action=schemas.RMSQueryWorkflowAction.APPROVE,
                ),
                db=self.db,
                current_user=self._user(models.UserRole.FACULTY, user_id=11, faculty_id=11),
            )
        self.assertEqual(ctx.exception.status_code, 403)

    def test_admin_can_fetch_rms_attendance_student_context(self):
        out = rms_attendance_student_context(
            registration_number="22BCS101",
            attendance_date=date.today(),
            db=self.db,
            current_user=self._user(models.UserRole.ADMIN, user_id=24),
        )
        self.assertEqual(out.student.registration_number, "22BCS101")
        self.assertEqual(out.attendance_date, date.today())
        self.assertEqual(len(out.subjects), 2)
        by_code = {row.course_code: row for row in out.subjects}
        self.assertEqual(by_code["CSE101"].current_status, models.AttendanceStatus.PRESENT)
        self.assertEqual(by_code["CSE101"].current_status_label, "Present")
        self.assertIsNone(by_code["ECE210"].current_status)

    def test_faculty_attendance_context_is_limited_to_assigned_subjects(self):
        out = rms_attendance_student_context(
            registration_number="22BCS101",
            attendance_date=date.today(),
            db=self.db,
            current_user=self._user(models.UserRole.FACULTY, user_id=25, faculty_id=11),
        )
        self.assertEqual(len(out.subjects), 1)
        self.assertEqual(out.subjects[0].course_code, "CSE101")

    def test_admin_can_override_rms_attendance_status(self):
        with patch("app.routers.admin.mirror_document", return_value=True):
            out = rms_update_attendance_status(
                payload=schemas.RMSAttendanceStatusUpdateRequest(
                    registration_number="22BCS101",
                    course_code="CSE101",
                    attendance_date=date.today(),
                    status=models.AttendanceStatus.ABSENT,
                    note="Approved in RMS",
                ),
                db=self.db,
                current_user=self._user(models.UserRole.ADMIN, user_id=21),
            )
        self.assertEqual(out.registration_number, "22BCS101")
        self.assertEqual(out.course_code, "CSE101")
        self.assertEqual(out.previous_status, models.AttendanceStatus.PRESENT)
        self.assertEqual(out.updated_status, models.AttendanceStatus.ABSENT)
        self.assertTrue(out.message_sent)

        updated = (
            self.db.query(models.AttendanceRecord)
            .filter(
                models.AttendanceRecord.student_id == 101,
                models.AttendanceRecord.course_id == 501,
                models.AttendanceRecord.attendance_date == date.today(),
            )
            .first()
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated.status, models.AttendanceStatus.ABSENT)

        submission = (
            self.db.query(models.AttendanceSubmission)
            .filter(
                models.AttendanceSubmission.student_id == 101,
                models.AttendanceSubmission.course_id == 501,
                models.AttendanceSubmission.class_date == date.today(),
            )
            .first()
        )
        self.assertIsNotNone(submission)
        self.assertEqual(submission.status, models.AttendanceSubmissionStatus.REJECTED)

        notification = (
            self.db.query(models.FacultyMessage)
            .filter(models.FacultyMessage.student_id == 101)
            .order_by(models.FacultyMessage.created_at.desc(), models.FacultyMessage.id.desc())
            .first()
        )
        self.assertIsNotNone(notification)
        self.assertIn("Your attendance has been updated for subject", notification.message)
        self.assertIn("CSE101", notification.message)

    def test_faculty_can_override_rms_attendance_status_for_own_course(self):
        with patch("app.routers.admin.mirror_document", return_value=True):
            out = rms_update_attendance_status(
                payload=schemas.RMSAttendanceStatusUpdateRequest(
                    registration_number="22BCS101",
                    course_code="CSE101",
                    attendance_date=date.today(),
                    status=models.AttendanceStatus.ABSENT,
                ),
                db=self.db,
                current_user=self._user(models.UserRole.FACULTY, user_id=22, faculty_id=11),
            )
        self.assertEqual(out.updated_status, models.AttendanceStatus.ABSENT)
        self.assertEqual(out.faculty_id, 11)

    def test_faculty_cannot_override_rms_attendance_for_other_faculty_course(self):
        with self.assertRaises(HTTPException) as ctx:
            rms_update_attendance_status(
                payload=schemas.RMSAttendanceStatusUpdateRequest(
                    registration_number="22BCS101",
                    course_code="ECE210",
                    attendance_date=date.today(),
                    status=models.AttendanceStatus.PRESENT,
                ),
                db=self.db,
                current_user=self._user(models.UserRole.FACULTY, user_id=23, faculty_id=11),
            )
        self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
