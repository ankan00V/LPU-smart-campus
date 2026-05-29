import unittest
from datetime import date, datetime, time
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.routers.attendance import (
    get_student_attendance_aggregate,
    get_student_attendance_history,
    get_student_weekly_timetable,
)


class StudentAttendanceSlotFallbackAlignmentTests(unittest.TestCase):
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
        self.class_date = date(2026, 3, 3)  # Tuesday
        self.db.add_all(
            [
                models.Student(
                    id=1,
                    name="Student One",
                    email="student.one@example.com",
                    registration_number="22BCS101",
                    section="P132",
                    department="CSE",
                    semester=4,
                ),
                models.Faculty(
                    id=11,
                    name="Faculty One",
                    email="faculty.one@example.com",
                    department="CSE",
                    section="P132",
                ),
                models.Course(
                    id=101,
                    code="CSE357",
                    title="Combinatorial Studies",
                    faculty_id=11,
                ),
                models.Enrollment(
                    id=201,
                    student_id=1,
                    course_id=101,
                ),
                models.ClassSchedule(
                    id=301,
                    course_id=101,
                    faculty_id=11,
                    weekday=self.class_date.weekday(),
                    start_time=time(9, 0),
                    end_time=time(10, 0),
                    classroom_label="37-101",
                    is_active=True,
                ),
                models.ClassSchedule(
                    id=302,
                    course_id=101,
                    faculty_id=11,
                    weekday=self.class_date.weekday(),
                    start_time=time(10, 0),
                    end_time=time(11, 0),
                    classroom_label="37-101",
                    is_active=True,
                ),
                models.AttendanceSubmission(
                    id=401,
                    schedule_id=301,
                    course_id=101,
                    faculty_id=11,
                    student_id=1,
                    class_date=self.class_date,
                    selfie_photo_data_url=None,
                    ai_match=True,
                    ai_confidence=1.0,
                    ai_model="opencv-test",
                    ai_reason="verified",
                    status=models.AttendanceSubmissionStatus.VERIFIED,
                ),
                models.AttendanceRecord(
                    id=501,
                    student_id=1,
                    course_id=101,
                    marked_by_faculty_id=11,
                    attendance_date=self.class_date,
                    status=models.AttendanceStatus.PRESENT,
                    source="rms-admin-attendance-override",
                ),
            ]
        )
        self.db.commit()

    @staticmethod
    def _student_user() -> models.AuthUser:
        return models.AuthUser(
            id=9001,
            email="student.one@example.com",
            password_hash="x",
            role=models.UserRole.STUDENT,
            student_id=1,
            faculty_id=None,
            is_active=True,
        )

    def test_aggregate_does_not_spread_record_fallback_across_multiple_same_day_slots(self):
        with (
            patch("app.routers.attendance._academic_start_date", return_value=self.class_date),
            patch("app.routers.attendance.datetime") as datetime_mock,
            patch("app.routers.attendance.recompute_attendance_recovery_scope") as recompute_scope,
        ):
            datetime_mock.now.return_value = datetime.combine(self.class_date, time(11, 5))
            datetime_mock.combine.side_effect = datetime.combine
            datetime_mock.utcnow.side_effect = datetime.utcnow
            payload = get_student_attendance_aggregate(
                db=self.db,
                current_user=self._student_user(),
            )

        recompute_scope.assert_not_called()
        self.assertEqual(payload.attended_total, 1)
        self.assertEqual(payload.delivered_total, 2)
        self.assertEqual(payload.aggregate_percent, 50.0)
        self.assertEqual(len(payload.courses), 1)
        self.assertEqual(payload.courses[0].course_code, "CSE357")
        self.assertEqual(payload.courses[0].attended_classes, 1)
        self.assertEqual(payload.courses[0].delivered_classes, 2)

    def test_history_does_not_expand_record_fallback_to_missing_same_day_slot(self):
        with (
            patch("app.routers.attendance._academic_start_date", return_value=self.class_date),
            patch("app.routers.attendance.datetime") as datetime_mock,
        ):
            datetime_mock.now.return_value = datetime.combine(self.class_date, time(11, 5))
            datetime_mock.combine.side_effect = datetime.combine
            datetime_mock.utcnow.side_effect = datetime.utcnow
            payload = get_student_attendance_history(
                limit=20,
                db=self.db,
                current_user=self._student_user(),
            )

        rows = [row for row in payload.records if row.course_code == "CSE357"]
        self.assertEqual(len(rows), 2)
        rows_by_schedule = {int(row.schedule_id or 0): row for row in rows}
        self.assertEqual(rows_by_schedule[301].status, models.AttendanceStatus.PRESENT)
        self.assertEqual(rows_by_schedule[302].status, models.AttendanceStatus.ABSENT)
        self.assertEqual(rows_by_schedule[302].source, "scheduled-absence")

    def test_history_can_return_all_delivered_rows_for_subject_details(self):
        current_dt = datetime(2026, 8, 18, 11, 5)
        with (
            patch("app.routers.attendance._academic_start_date", return_value=self.class_date),
            patch("app.routers.attendance.datetime") as datetime_mock,
            patch("app.routers.attendance.recompute_attendance_recovery_scope") as recompute_scope,
        ):
            datetime_mock.now.return_value = current_dt
            datetime_mock.combine.side_effect = datetime.combine
            datetime_mock.utcnow.side_effect = datetime.utcnow
            aggregate = get_student_attendance_aggregate(
                db=self.db,
                current_user=self._student_user(),
            )
            history = get_student_attendance_history(
                limit=1000,
                db=self.db,
                current_user=self._student_user(),
            )

        recompute_scope.assert_not_called()
        course = aggregate.courses[0]
        rows = [row for row in history.records if row.course_code == "CSE357"]
        self.assertEqual(course.delivered_classes, 50)
        self.assertEqual(len(rows), course.delivered_classes)
        self.assertEqual(rows[0].status, models.AttendanceStatus.ABSENT)
        self.assertEqual(rows[-1].status, models.AttendanceStatus.PRESENT)

    def test_history_uses_effective_timetable_overrides_for_real_class_rows(self):
        self.db.query(models.AttendanceSubmission).delete()
        self.db.query(models.AttendanceRecord).delete()
        moved_class_date = date(2026, 3, 4)  # Wednesday
        self.db.add(
            models.ClassSchedule(
                id=303,
                course_id=101,
                faculty_id=11,
                weekday=moved_class_date.weekday(),
                start_time=time(14, 0),
                end_time=time(15, 0),
                classroom_label="37-202",
                is_active=True,
            )
        )
        self.db.add(
            models.TimetableOverride(
                id=601,
                scope_type="section",
                scope_key="P132",
                section="P132",
                source_weekday=self.class_date.weekday(),
                source_start_time=time(9, 0),
                schedule_id=303,
                is_active=True,
            )
        )
        self.db.commit()

        with (
            patch("app.routers.attendance._academic_start_date", return_value=self.class_date),
            patch("app.routers.attendance.datetime") as datetime_mock,
            patch("app.routers.attendance.recompute_attendance_recovery_scope") as recompute_scope,
        ):
            datetime_mock.now.return_value = datetime.combine(moved_class_date, time(15, 5))
            datetime_mock.combine.side_effect = datetime.combine
            datetime_mock.utcnow.side_effect = datetime.utcnow
            aggregate = get_student_attendance_aggregate(
                db=self.db,
                current_user=self._student_user(),
            )
            history = get_student_attendance_history(
                limit=100,
                db=self.db,
                current_user=self._student_user(),
            )

        recompute_scope.assert_not_called()
        rows = [row for row in history.records if row.course_code == "CSE357"]
        rows_by_schedule = {int(row.schedule_id or 0): row for row in rows}
        self.assertEqual(aggregate.courses[0].delivered_classes, 2)
        self.assertNotIn(301, rows_by_schedule)
        self.assertIn(302, rows_by_schedule)
        self.assertIn(303, rows_by_schedule)
        self.assertEqual(rows_by_schedule[303].class_date, moved_class_date)
        self.assertEqual(rows_by_schedule[303].start_time, time(14, 0))

    def test_timetable_does_not_show_previous_same_course_slot_present_from_later_submission(self):
        self.db.query(models.AttendanceSubmission).delete()
        self.db.query(models.AttendanceRecord).delete()
        self.db.add(
            models.AttendanceSubmission(
                id=402,
                schedule_id=302,
                course_id=101,
                faculty_id=11,
                student_id=1,
                class_date=self.class_date,
                selfie_photo_data_url=None,
                ai_match=True,
                ai_confidence=1.0,
                ai_model="opencv-test",
                ai_reason="verified",
                status=models.AttendanceSubmissionStatus.VERIFIED,
            )
        )
        self.db.add(
            models.AttendanceRecord(
                id=502,
                student_id=1,
                course_id=101,
                marked_by_faculty_id=11,
                attendance_date=self.class_date,
                status=models.AttendanceStatus.PRESENT,
                source="face-opencv-primary-verified",
            )
        )
        self.db.commit()

        with (
            patch("app.routers.attendance._academic_start_date", return_value=self.class_date),
            patch("app.routers.attendance.date") as date_mock,
            patch("app.routers.attendance.datetime") as datetime_mock,
        ):
            date_mock.today.return_value = self.class_date
            date_mock.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
            datetime_mock.now.return_value = datetime.combine(self.class_date, time(11, 5))
            datetime_mock.combine.side_effect = datetime.combine
            datetime_mock.utcnow.side_effect = datetime.utcnow
            payload = get_student_weekly_timetable(
                week_start=self.class_date,
                db=self.db,
                current_user=self._student_user(),
            )

        rows = {int(row.schedule_id): row for row in payload.classes if row.course_code == "CSE357"}
        self.assertEqual(rows[301].attendance_status, None)
        self.assertEqual(rows[302].attendance_status, "verified")

    def test_timetable_open_window_uses_server_campus_clock(self):
        campus_now = datetime.combine(self.class_date, time(10, 5))
        with (
            patch("app.routers.attendance._academic_start_date", return_value=self.class_date),
            patch("app.routers.attendance._campus_now", return_value=campus_now),
        ):
            payload = get_student_weekly_timetable(
                week_start=self.class_date,
                db=self.db,
                current_user=self._student_user(),
            )

        rows = {int(row.schedule_id): row for row in payload.classes if row.course_code == "CSE357"}
        self.assertEqual(payload.server_time, campus_now)
        self.assertEqual(payload.server_date, self.class_date)
        self.assertTrue(rows[302].is_open_now)
        self.assertFalse(rows[301].is_open_now)


if __name__ == "__main__":
    unittest.main()
