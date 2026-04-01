from datetime import date, datetime, time, timedelta
import unittest
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.routers.admin import rms_update_student_profile
from app.routers.attendance import faculty_batch_review
from app.routers.messages import send_faculty_message
from app.routers.remedial import create_makeup_class


class RealtimeEventScopeTargetTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    @staticmethod
    def _auth_user(
        *,
        user_id: int,
        role: models.UserRole,
        faculty_id: int | None = None,
        student_id: int | None = None,
    ) -> models.AuthUser:
        return models.AuthUser(
            id=user_id,
            email=f"{role.value}.{user_id}@example.com",
            password_hash="hash",
            role=role,
            faculty_id=faculty_id,
            student_id=student_id,
            is_active=True,
        )

    def test_faculty_announcement_event_targets_recipients_not_global_student_scope(self):
        self.db.add_all(
            [
                models.Faculty(
                    id=11,
                    name="Faculty One",
                    email="faculty.one@example.com",
                    department="CSE",
                    section="P132",
                ),
                models.Student(
                    id=1,
                    name="Student One",
                    email="student.one@example.com",
                    department="CSE",
                    semester=6,
                    section="P132",
                ),
                models.Student(
                    id=2,
                    name="Student Two",
                    email="student.two@example.com",
                    department="CSE",
                    semester=6,
                    section="P999",
                ),
            ]
        )
        self.db.commit()

        payload = schemas.FacultyMessageSend(
            sections=["P132"],
            message_type="Announcement",
            message="Tomorrow's class is shifted to Lab 5.",
        )

        with mock.patch("app.routers.messages.get_mongo_db", return_value=None), mock.patch(
            "app.routers.messages.publish_domain_event"
        ) as publish_patch, mock.patch("app.routers.messages.enqueue_notification"):
            send_faculty_message(
                payload=payload,
                db=self.db,
                current_user=self._auth_user(
                    user_id=701,
                    role=models.UserRole.FACULTY,
                    faculty_id=11,
                ),
            )

        scopes = publish_patch.call_args.kwargs["scopes"]
        self.assertEqual(scopes, {"role:admin", "faculty:11", "student:1"})
        self.assertNotIn("role:student", scopes)

    def test_attendance_review_event_targets_affected_students_only(self):
        class_date = date(2026, 3, 30)
        self.db.add_all(
            [
                models.Faculty(
                    id=11,
                    name="Faculty One",
                    email="faculty.one@example.com",
                    department="CSE",
                    section="P132",
                ),
                models.Course(
                    id=101,
                    code="CSE310",
                    title="Distributed Systems",
                    faculty_id=11,
                ),
                models.ClassSchedule(
                    id=301,
                    course_id=101,
                    faculty_id=11,
                    weekday=0,
                    start_time=time(9, 0),
                    end_time=time(10, 0),
                    classroom_label="34-201",
                    is_active=True,
                ),
                models.Student(
                    id=1,
                    name="Student One",
                    email="student.one@example.com",
                    department="CSE",
                    semester=6,
                    section="P132",
                ),
                models.Student(
                    id=2,
                    name="Student Two",
                    email="student.two@example.com",
                    department="CSE",
                    semester=6,
                    section="P132",
                ),
                models.AttendanceSubmission(
                    id=501,
                    schedule_id=301,
                    course_id=101,
                    faculty_id=11,
                    student_id=1,
                    class_date=class_date,
                    status=models.AttendanceSubmissionStatus.PENDING_REVIEW,
                ),
                models.AttendanceSubmission(
                    id=502,
                    schedule_id=301,
                    course_id=101,
                    faculty_id=11,
                    student_id=2,
                    class_date=class_date,
                    status=models.AttendanceSubmissionStatus.PENDING_REVIEW,
                ),
            ]
        )
        self.db.commit()

        payload = schemas.FacultyBatchReviewRequest(
            schedule_id=301,
            class_date=class_date,
            submission_ids=[501, 502],
            action=schemas.FacultyReviewAction.REJECT,
            note="Faces do not match the profile on record.",
        )

        with mock.patch("app.routers.attendance.mirror_document"), mock.patch(
            "app.routers.attendance.publish_domain_event"
        ) as publish_patch, mock.patch("app.routers.attendance.enqueue_recompute"):
            faculty_batch_review(
                payload=payload,
                db=self.db,
                current_user=self._auth_user(
                    user_id=711,
                    role=models.UserRole.FACULTY,
                    faculty_id=11,
                ),
            )

        scopes = publish_patch.call_args.kwargs["scopes"]
        event_payload = publish_patch.call_args.kwargs["payload"]
        self.assertEqual(scopes, {"role:admin", "faculty:11", "student:1", "student:2"})
        self.assertEqual(event_payload["affected_student_ids"], [1, 2])
        self.assertNotIn("role:student", scopes)

    def test_rms_student_update_targets_related_faculties_without_global_faculty_scope(self):
        self.db.add_all(
            [
                models.Student(
                    id=1,
                    name="Student One",
                    email="student.one@example.com",
                    registration_number="22BCS101",
                    department="CSE",
                    semester=6,
                    section="P132",
                ),
                models.Faculty(
                    id=11,
                    name="Section Faculty Old",
                    email="faculty.old@example.com",
                    department="CSE",
                    section="P132",
                ),
                models.Faculty(
                    id=12,
                    name="Section Faculty New",
                    email="faculty.new@example.com",
                    department="CSE",
                    section="P133",
                ),
                models.Faculty(
                    id=13,
                    name="Teaching Faculty",
                    email="faculty.teach@example.com",
                    department="CSE",
                    section=None,
                ),
                models.Faculty(
                    id=14,
                    name="Unrelated Faculty",
                    email="faculty.other@example.com",
                    department="ECE",
                    section="P999",
                ),
                models.Course(
                    id=101,
                    code="CSE420",
                    title="Machine Learning",
                    faculty_id=13,
                ),
                models.Enrollment(
                    id=201,
                    student_id=1,
                    course_id=101,
                ),
            ]
        )
        self.db.commit()

        payload = schemas.RMSStudentUpdateRequest(section="P133")

        with mock.patch("app.routers.admin.mirror_document"), mock.patch(
            "app.routers.admin.signed_url_for_object",
            return_value=None,
        ), mock.patch("app.routers.admin.publish_domain_event") as publish_patch, mock.patch(
            "app.routers.admin.enqueue_recompute"
        ):
            rms_update_student_profile(
                student_id=1,
                payload=payload,
                db=self.db,
                current_user=self._auth_user(
                    user_id=901,
                    role=models.UserRole.ADMIN,
                ),
            )

        scopes = publish_patch.call_args.kwargs["scopes"]
        self.assertEqual(
            scopes,
            {
                "role:admin",
                "student:1",
                "faculty:11",
                "faculty:12",
                "faculty:13",
            },
        )
        self.assertNotIn("role:faculty", scopes)
        self.assertNotIn("faculty:14", scopes)

    def test_remedial_class_scheduled_targets_enrolled_section_students(self):
        tomorrow = date.today() + timedelta(days=1)
        self.db.add_all(
            [
                models.Faculty(
                    id=11,
                    name="Faculty One",
                    email="faculty.one@example.com",
                    department="CSE",
                    section="P132",
                ),
                models.Course(
                    id=101,
                    code="CSE550",
                    title="Cloud Computing",
                    faculty_id=11,
                ),
                models.Student(
                    id=1,
                    name="Student Enrolled",
                    email="student.one@example.com",
                    department="CSE",
                    semester=6,
                    section="P132",
                ),
                models.Student(
                    id=2,
                    name="Student Same Section",
                    email="student.two@example.com",
                    department="CSE",
                    semester=6,
                    section="P132",
                ),
                models.Student(
                    id=3,
                    name="Student Other Section",
                    email="student.three@example.com",
                    department="CSE",
                    semester=6,
                    section="P999",
                ),
                models.Enrollment(
                    id=301,
                    student_id=1,
                    course_id=101,
                ),
                models.Enrollment(
                    id=302,
                    student_id=3,
                    course_id=101,
                ),
            ]
        )
        self.db.commit()

        payload = schemas.MakeUpClassCreate(
            course_id=101,
            faculty_id=11,
            class_date=tomorrow,
            start_time=time(15, 0),
            end_time=time(16, 0),
            topic="Remedial session on deployment pipelines",
            sections=["P132"],
            class_mode="offline",
            room_number="27-402",
            demo_bypass_lead_time=False,
        )

        with mock.patch("app.routers.remedial._safe_sync_makeup_class_to_mongo"), mock.patch(
            "app.routers.remedial.mirror_event"
        ) as mirror_event_patch:
            create_makeup_class(
                payload=payload,
                db=self.db,
                current_user=self._auth_user(
                    user_id=801,
                    role=models.UserRole.FACULTY,
                    faculty_id=11,
                ),
            )

        self.assertEqual(mirror_event_patch.call_count, 1)
        args, kwargs = mirror_event_patch.call_args
        self.assertEqual(args[0], "remedial.class_scheduled")
        scopes = kwargs["scopes"]
        self.assertEqual(scopes, {"role:admin", "faculty:11", "student:1"})
        self.assertNotIn("student:2", scopes)
        self.assertNotIn("student:3", scopes)


if __name__ == "__main__":
    unittest.main()
