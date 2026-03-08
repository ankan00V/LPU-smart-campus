import unittest
from datetime import datetime, timedelta
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, workers


class WorkerRecoveryNotificationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self._session_patch = mock.patch("app.workers.SessionLocal", self.SessionLocal)
        self._session_patch.start()
        self._seed_rows()

    def tearDown(self):
        self._session_patch.stop()
        self.engine.dispose()

    def _seed_rows(self):
        now_dt = datetime.utcnow()
        with self.SessionLocal() as db:
            db.add_all(
                [
                    models.Student(
                        id=101,
                        name="Student One",
                        email="student.one@example.com",
                        registration_number="22BCS101",
                        parent_email="parent.one@example.com",
                        section="P132",
                        department="CSE",
                        semester=4,
                    ),
                    models.Faculty(
                        id=201,
                        name="Faculty One",
                        email="faculty.one@example.com",
                        department="CSE",
                        section="P132",
                    ),
                    models.Course(
                        id=301,
                        code="CSE310",
                        title="Software Engineering",
                        faculty_id=201,
                    ),
                    models.AttendanceRecoveryPlan(
                        id=401,
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
                        recovery_due_at=now_dt + timedelta(days=2),
                        summary="Critical recovery plan is active.",
                        last_absent_on=now_dt.date(),
                        last_evaluated_at=now_dt,
                        created_at=now_dt,
                        updated_at=now_dt,
                    ),
                    models.AttendanceRecoveryAction(
                        id=501,
                        plan_id=401,
                        action_type=models.AttendanceRecoveryActionType.FACULTY_NUDGE,
                        status=models.AttendanceRecoveryActionStatus.PENDING,
                        title="Faculty intervention required",
                        description="Review the recovery plan and follow up with the student.",
                        recipient_role="faculty",
                        recipient_email="faculty.one@example.com",
                        scheduled_for=now_dt,
                        metadata_json="{}",
                        created_at=now_dt,
                        updated_at=now_dt,
                    ),
                ]
            )
            db.commit()

    def test_recovery_notification_delivery_marks_action_sent_and_writes_log(self):
        payload = {
            "type": "attendance_recovery_faculty_alert",
            "action_id": 501,
            "student_id": 101,
            "recipient_email": "faculty.one@example.com",
            "student_name": "Student One",
            "registration_number": "22BCS101",
            "course_code": "CSE310",
            "course_title": "Software Engineering",
            "risk_level": "critical",
            "attendance_percent": 49.0,
            "consecutive_absences": 4,
            "missed_remedials": 1,
            "summary": "Critical recovery plan is active.",
            "recovery_due_at": (datetime.utcnow() + timedelta(days=2)).isoformat(),
            "suggested_remedial": "2026-03-09 16:00-17:00 (offline)",
            "office_hour_at": "09 Mar 2026 02:00 PM",
            "message": "Review the recovery plan and follow up with the student.",
            "log_channel": "attendance-recovery-faculty",
        }

        with mock.patch(
            "app.workers.send_transactional_email",
            return_value={"channel": "smtp-email"},
        ) as mocked_send:
            result = workers._send_notification_task(payload)

        self.assertEqual(result["status"], "sent")
        self.assertEqual(result["channel"], "smtp-email")
        mocked_send.assert_called_once()

        with self.SessionLocal() as db:
            action = db.get(models.AttendanceRecoveryAction, 501)
            self.assertIsNotNone(action)
            self.assertEqual(action.status, models.AttendanceRecoveryActionStatus.SENT)

            logs = db.query(models.NotificationLog).all()
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0].student_id, 101)
            self.assertEqual(logs[0].sent_to, "faculty.one@example.com")
            self.assertEqual(logs[0].channel, "attendance-recovery-faculty")

            attempts = db.query(models.NotificationDeliveryAttempt).all()
            self.assertEqual(len(attempts), 1)
            self.assertEqual(attempts[0].status, "sent")
            self.assertEqual(attempts[0].attempt_number, 1)
            self.assertEqual(attempts[0].recipient_email, "faculty.one@example.com")

    def test_saarthi_student_notification_delivery_writes_log(self):
        payload = {
            "type": "saarthi_missed_student_alert",
            "student_id": 101,
            "recipient_email": "student.one@example.com",
            "student_name": "Student One",
            "registration_number": "22BCS101",
            "course_code": "CON111",
            "course_title": "Councelling and Happiness",
            "faculty_name": "Saarthi (AI Mentor)",
            "mandatory_date": "2026-03-08",
            "week_start_date": "2026-03-02",
            "section": "P132",
            "department": "CSE",
            "message_count": 2,
            "last_message_at": "2026-03-07T18:00:00",
            "message": "saarthi-missed:101:2026-03-08",
            "log_channel": "saarthi-missed-student",
        }

        with mock.patch(
            "app.workers.send_transactional_email",
            return_value={"channel": "smtp-email"},
        ) as mocked_send:
            result = workers._send_notification_task(payload)

        self.assertEqual(result["status"], "sent")
        self.assertEqual(result["channel"], "smtp-email")
        mocked_send.assert_called_once()

        with self.SessionLocal() as db:
            logs = db.query(models.NotificationLog).all()
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0].student_id, 101)
            self.assertEqual(logs[0].sent_to, "student.one@example.com")
            self.assertEqual(logs[0].channel, "saarthi-missed-student")

    def test_saarthi_admin_notification_dedupes_on_existing_log(self):
        payload = {
            "type": "saarthi_missed_admin_alert",
            "student_id": 101,
            "recipient_email": "admin@example.com",
            "student_name": "Student One",
            "registration_number": "22BCS101",
            "course_code": "CON111",
            "course_title": "Councelling and Happiness",
            "faculty_name": "Saarthi (AI Mentor)",
            "mandatory_date": "2026-03-08",
            "week_start_date": "2026-03-02",
            "section": "P132",
            "department": "CSE",
            "message_count": 0,
            "last_message_at": "",
            "message": "saarthi-missed:101:2026-03-08",
            "log_channel": "saarthi-missed-admin",
        }
        with self.SessionLocal() as db:
            db.add(
                models.NotificationLog(
                    student_id=101,
                    message="saarthi-missed:101:2026-03-08",
                    channel="saarthi-missed-admin",
                    sent_to="admin@example.com",
                )
            )
            db.commit()

        with mock.patch("app.workers.send_transactional_email") as mocked_send:
            result = workers._send_notification_task(payload)

        self.assertEqual(result["status"], "already_sent")
        mocked_send.assert_not_called()

        with self.SessionLocal() as db:
            attempts = db.query(models.NotificationDeliveryAttempt).all()
            self.assertEqual(len(attempts), 1)
            self.assertEqual(attempts[0].status, "already_sent")

    def test_unknown_notification_type_remains_non_delivery_noop(self):
        with mock.patch("app.workers.send_transactional_email") as mocked_send:
            result = workers._send_notification_task({"type": "support_query_message", "message_id": 1})

        self.assertEqual(result["status"], "accepted")
        mocked_send.assert_not_called()

    def test_recovery_notification_failure_writes_delivery_attempt(self):
        payload = {
            "type": "attendance_recovery_parent_alert",
            "action_id": 501,
            "student_id": 101,
            "recipient_email": "parent.one@example.com",
            "student_name": "Student One",
            "registration_number": "22BCS101",
            "course_code": "CSE310",
            "course_title": "Software Engineering",
            "risk_level": "critical",
            "attendance_percent": 49.0,
            "consecutive_absences": 4,
            "missed_remedials": 1,
            "summary": "Critical recovery plan is active.",
            "recovery_due_at": (datetime.utcnow() + timedelta(days=2)).isoformat(),
            "suggested_remedial": "2026-03-09 16:00-17:00 (offline)",
            "office_hour_at": "09 Mar 2026 02:00 PM",
            "message": "Critical plan requires immediate follow-up.",
            "log_channel": "attendance-recovery-parent",
        }

        with mock.patch(
            "app.workers.send_transactional_email",
            side_effect=RuntimeError("smtp provider down"),
        ):
            with self.assertRaisesRegex(RuntimeError, "smtp provider down"):
                workers._send_notification_task(payload, attempt_number=2)

        with self.SessionLocal() as db:
            action = db.get(models.AttendanceRecoveryAction, 501)
            self.assertIsNotNone(action)
            self.assertEqual(action.status, models.AttendanceRecoveryActionStatus.PENDING)

            logs = db.query(models.NotificationLog).all()
            self.assertEqual(len(logs), 0)

            attempts = db.query(models.NotificationDeliveryAttempt).all()
            self.assertEqual(len(attempts), 1)
            self.assertEqual(attempts[0].status, "failed")
            self.assertEqual(attempts[0].attempt_number, 2)
            self.assertIn("smtp provider down", attempts[0].error_message or "")


if __name__ == "__main__":
    unittest.main()
