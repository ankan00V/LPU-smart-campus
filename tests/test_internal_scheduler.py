import unittest
from datetime import date, datetime, timedelta
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import internal_scheduler, models
from app.saarthi_service import ensure_saarthi_bundle, queue_saarthi_missed_notifications_for_reference


class InternalSchedulerTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self._session_patch = mock.patch("app.internal_scheduler.SessionLocal", self.SessionLocal)
        self._session_patch.start()
        with internal_scheduler._STATE_LOCK:
            internal_scheduler._JOB_STATE.clear()

    def tearDown(self):
        internal_scheduler.stop_internal_scheduler(timeout_seconds=0.2)
        self._session_patch.stop()
        self.engine.dispose()

    def test_run_due_scheduler_jobs_once_claims_once_per_interval(self):
        calls: list[datetime] = []

        def fake_runner(db, now_utc):
            calls.append(now_utc)
            return {"calls": len(calls)}

        job = internal_scheduler.SchedulerJob(
            name="unit_scheduler_job",
            interval_seconds=3600,
            runner=fake_runner,
        )

        with mock.patch("app.internal_scheduler._registered_jobs", return_value=[job]):
            first = internal_scheduler.run_due_scheduler_jobs_once()
            second = internal_scheduler.run_due_scheduler_jobs_once()

        self.assertEqual(first["ran_jobs"], 1)
        self.assertEqual(second["ran_jobs"], 0)
        self.assertEqual(len(calls), 1)

        with self.SessionLocal() as db:
            row = db.get(models.SchedulerLease, "unit_scheduler_job")
            self.assertIsNotNone(row)
            self.assertEqual(row.last_status, "success")
            row.next_due_at = datetime.utcnow() - timedelta(seconds=1)
            db.commit()

        with mock.patch("app.internal_scheduler._registered_jobs", return_value=[job]):
            third = internal_scheduler.run_due_scheduler_jobs_once()

        self.assertEqual(third["ran_jobs"], 1)
        self.assertEqual(len(calls), 2)

    def test_saarthi_sweep_enqueues_student_and_admin_notifications(self):
        with self.SessionLocal() as db:
            student = models.Student(
                id=1,
                name="Scheduler Student",
                email="scheduler.student@example.com",
                registration_number="22BCS7001",
                section="P132",
                department="CSE",
                semester=6,
            )
            admin = models.AuthUser(
                id=2,
                email="admin@example.com",
                password_hash="x",
                role=models.UserRole.ADMIN,
                student_id=None,
                faculty_id=None,
                is_active=True,
            )
            db.add_all([student, admin])
            db.flush()
            bundle = ensure_saarthi_bundle(db, student_id=int(student.id))
            session = models.SaarthiSession(
                id=11,
                student_id=int(student.id),
                course_id=int(bundle.course.id),
                faculty_id=int(bundle.faculty.id),
                week_start_date=date(2026, 3, 2),
                mandatory_date=date(2026, 3, 8),
                attendance_credit_minutes=0,
                attendance_marked_at=None,
                attendance_record_id=None,
                created_at=datetime(2026, 3, 7, 12, 0, 0),
                updated_at=datetime(2026, 3, 7, 12, 5, 0),
                last_message_at=datetime(2026, 3, 7, 12, 5, 0),
            )
            db.add(session)
            db.add(
                models.SaarthiMessage(
                    session_id=11,
                    sender_role="student",
                    message="I want to talk before Sunday.",
                    created_at=datetime(2026, 3, 7, 12, 0, 0),
                )
            )
            db.commit()

        with mock.patch("app.saarthi_service.enqueue_notification", return_value="inline-thread") as mocked_enqueue:
            with self.SessionLocal() as db:
                result = queue_saarthi_missed_notifications_for_reference(
                    db,
                    reference_date=date(2026, 3, 9),
                )

        self.assertEqual(result["missed_students"], 1)
        self.assertEqual(result["notified_students"], 1)
        self.assertEqual(result["enqueued_notifications"], 2)
        self.assertEqual(mocked_enqueue.call_count, 2)
        payloads = [call.args[0] for call in mocked_enqueue.call_args_list]
        self.assertCountEqual(
            [payload["type"] for payload in payloads],
            ["saarthi_missed_student_alert", "saarthi_missed_admin_alert"],
        )


if __name__ == "__main__":
    unittest.main()
