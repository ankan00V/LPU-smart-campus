import base64
from datetime import date, time, timedelta
import unittest
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.routers.attendance import (
    create_student_rectification_request,
    faculty_rectification_review,
    list_faculty_rectification_requests,
    list_student_rectification_requests,
)

VALID_PNG_DATA_URL = "data:image/png;base64," + base64.b64encode(
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
).decode("ascii")


class AttendanceRectificationFlowTests(unittest.TestCase):
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
        self.class_date = date.today() - timedelta(days=1)
        self.db.add_all(
            [
                models.Student(
                    id=1,
                    name="Rectify Student",
                    email="rectify.student@example.com",
                    registration_number="123",
                    section="P132",
                    department="CSE",
                    semester=6,
                ),
                models.Faculty(
                    id=11,
                    name="Rectify Faculty",
                    email="rectify.faculty@example.com",
                    department="CSE",
                    section="P132",
                ),
                models.Faculty(
                    id=12,
                    name="Other Faculty",
                    email="other.faculty@example.com",
                    department="CSE",
                    section="P132",
                ),
                models.Course(
                    id=21,
                    code="CSE321",
                    title="Compiler Design",
                    faculty_id=11,
                ),
                models.Course(
                    id=22,
                    code="CSE322",
                    title="Operating Systems",
                    faculty_id=11,
                ),
                models.Course(
                    id=23,
                    code="CSE323",
                    title="Database Systems",
                    faculty_id=12,
                ),
                models.Enrollment(
                    id=31,
                    student_id=1,
                    course_id=21,
                ),
                models.Enrollment(
                    id=32,
                    student_id=1,
                    course_id=22,
                ),
                models.Enrollment(
                    id=33,
                    student_id=1,
                    course_id=23,
                ),
                models.ClassSchedule(
                    id=41,
                    course_id=21,
                    faculty_id=11,
                    weekday=self.class_date.weekday(),
                    start_time=time(11, 0),
                    end_time=time(12, 0),
                    classroom_label="34-101",
                    is_active=True,
                ),
                models.ClassSchedule(
                    id=42,
                    course_id=22,
                    faculty_id=11,
                    weekday=self.class_date.weekday(),
                    start_time=time(13, 0),
                    end_time=time(14, 0),
                    classroom_label="34-102",
                    is_active=True,
                ),
                models.ClassSchedule(
                    id=43,
                    course_id=23,
                    faculty_id=12,
                    weekday=self.class_date.weekday(),
                    start_time=time(15, 0),
                    end_time=time(16, 0),
                    classroom_label="34-103",
                    is_active=True,
                ),
            ]
        )
        self.db.commit()

    def _student_user(self) -> models.AuthUser:
        return models.AuthUser(
            id=101,
            email="rectify.student@example.com",
            password_hash="x",
            role=models.UserRole.STUDENT,
            student_id=1,
            faculty_id=None,
            is_active=True,
        )

    def _faculty_user(self) -> models.AuthUser:
        return models.AuthUser(
            id=102,
            email="rectify.faculty@example.com",
            password_hash="x",
            role=models.UserRole.FACULTY,
            student_id=None,
            faculty_id=11,
            is_active=True,
        )

    @mock.patch("app.routers.attendance.publish_domain_event", autospec=True)
    @mock.patch("app.routers.attendance._upsert_mongo_by_id", autospec=True)
    def test_student_can_create_rectification_request(self, _mongo_upsert, publish_event):
        payload = schemas.AttendanceRectificationRequestCreate(
            course_id=21,
            class_date=self.class_date,
            start_time=time(11, 0),
            proof_note="I was in class and can share lab entry + notes.",
            proof_photo_data_url=VALID_PNG_DATA_URL,
        )

        out = create_student_rectification_request(
            payload=payload,
            db=self.db,
            current_user=self._student_user(),
        )

        self.assertEqual(out.status, models.AttendanceRectificationStatus.PENDING)
        self.assertEqual(out.course_id, 21)
        self.assertEqual(out.class_date, self.class_date)
        self.assertEqual(out.class_start_time, time(11, 0))

        listed = list_student_rectification_requests(
            limit=20,
            db=self.db,
            current_user=self._student_user(),
        )
        self.assertEqual(len(listed.requests), 1)
        self.assertEqual(listed.requests[0].status, models.AttendanceRectificationStatus.PENDING)
        publish_event.assert_called_once()
        self.assertEqual(publish_event.call_args.args[0], "attendance.rectification.requested")
        self.assertEqual(
            publish_event.call_args.kwargs["scopes"],
            {"student:1", "faculty:11"},
        )

    @mock.patch("app.routers.attendance.publish_domain_event", autospec=True)
    @mock.patch("app.routers.attendance._upsert_mongo_by_id", autospec=True)
    def test_student_rectification_requires_proof_image(self, _mongo_upsert, publish_event):
        payload = schemas.AttendanceRectificationRequestCreate(
            course_id=21,
            class_date=self.class_date,
            start_time=time(11, 0),
            proof_note="I was in class and have proof details ready.",
            proof_photo_data_url="not-an-image-data-url",
        )

        with self.assertRaisesRegex(Exception, "image data URL"):
            create_student_rectification_request(
                payload=payload,
                db=self.db,
                current_user=self._student_user(),
            )

        publish_event.assert_not_called()
        self.assertEqual(self.db.query(models.AttendanceRectificationRequest).count(), 0)

    @mock.patch("app.routers.attendance.enqueue_recompute", autospec=True)
    @mock.patch("app.routers.attendance.publish_domain_event", autospec=True)
    @mock.patch("app.routers.attendance.mirror_document", autospec=True)
    @mock.patch("app.routers.attendance._upsert_mongo_by_id", autospec=True)
    def test_faculty_approval_marks_present_and_updates_submission(
        self,
        _mongo_upsert,
        _mirror,
        _publish_event,
        _enqueue_recompute,
    ):
        create_payload = schemas.AttendanceRectificationRequestCreate(
            course_id=21,
            class_date=self.class_date,
            start_time=time(11, 0),
            proof_note="I attended but camera failed. Sharing class notes as proof.",
            proof_photo_data_url=VALID_PNG_DATA_URL,
        )
        created = create_student_rectification_request(
            payload=create_payload,
            db=self.db,
            current_user=self._student_user(),
        )

        review_payload = schemas.FacultyRectificationReviewRequest(
            request_id=created.id,
            action=schemas.FacultyRectificationReviewAction.APPROVE,
            note="Verified with class notes and in-class confirmation.",
        )
        review_out = faculty_rectification_review(
            payload=review_payload,
            db=self.db,
            current_user=self._faculty_user(),
        )

        self.assertEqual(review_out.updated, 1)
        self.assertEqual(review_out.approved, 1)
        self.assertEqual(review_out.rejected, 0)

        attendance_row = (
            self.db.query(models.AttendanceRecord)
            .filter(
                models.AttendanceRecord.student_id == 1,
                models.AttendanceRecord.course_id == 21,
                models.AttendanceRecord.attendance_date == self.class_date,
            )
            .first()
        )
        self.assertIsNotNone(attendance_row)
        self.assertEqual(attendance_row.status, models.AttendanceStatus.PRESENT)

        submission_row = (
            self.db.query(models.AttendanceSubmission)
            .filter(
                models.AttendanceSubmission.student_id == 1,
                models.AttendanceSubmission.schedule_id == 41,
                models.AttendanceSubmission.class_date == self.class_date,
            )
            .first()
        )
        self.assertIsNotNone(submission_row)
        self.assertEqual(submission_row.status, models.AttendanceSubmissionStatus.APPROVED)

        queue = list_faculty_rectification_requests(
            schedule_id=41,
            class_date=self.class_date,
            include_resolved=True,
            db=self.db,
            current_user=self._faculty_user(),
        )
        self.assertEqual(len(queue.requests), 1)
        self.assertEqual(queue.requests[0].status, models.AttendanceRectificationStatus.APPROVED)

    @mock.patch("app.routers.attendance.publish_domain_event", autospec=True)
    @mock.patch("app.routers.attendance._upsert_mongo_by_id", autospec=True)
    def test_faculty_queue_includes_assigned_ledger_requests_across_schedules(
        self,
        _mongo_upsert,
        _publish_event,
    ):
        first = schemas.AttendanceRectificationRequestCreate(
            course_id=21,
            class_date=self.class_date,
            start_time=time(11, 0),
            proof_note="I attended and have notes from this lecture as proof.",
            proof_photo_data_url=VALID_PNG_DATA_URL,
        )
        second = schemas.AttendanceRectificationRequestCreate(
            course_id=22,
            class_date=self.class_date,
            start_time=time(13, 0),
            proof_note="I attended the lab and can show a valid lab entry record.",
            proof_photo_data_url=VALID_PNG_DATA_URL,
        )
        other_faculty = schemas.AttendanceRectificationRequestCreate(
            course_id=23,
            class_date=self.class_date,
            start_time=time(15, 0),
            proof_note="I attended this class too and can share valid proof.",
            proof_photo_data_url=VALID_PNG_DATA_URL,
        )

        create_student_rectification_request(payload=first, db=self.db, current_user=self._student_user())
        create_student_rectification_request(payload=second, db=self.db, current_user=self._student_user())
        create_student_rectification_request(payload=other_faculty, db=self.db, current_user=self._student_user())

        queue = list_faculty_rectification_requests(
            schedule_id=None,
            class_date=None,
            include_resolved=False,
            db=self.db,
            current_user=self._faculty_user(),
        )

        self.assertEqual({item.course_code for item in queue.requests}, {"CSE321", "CSE322"})
        self.assertTrue(all(item.status == models.AttendanceRectificationStatus.PENDING for item in queue.requests))
        self.assertIsNone(queue.schedule_id)
        self.assertIsNone(queue.class_date)


if __name__ == "__main__":
    unittest.main()
