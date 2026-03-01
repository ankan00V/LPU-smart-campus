import unittest
from collections import defaultdict
from datetime import date, time
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.routers.attendance import _ensure_default_timetable_for_student


class DefaultTimetableLoaderCleanupTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()
        self._seed()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _seed(self):
        student = models.Student(
            id=1,
            name="Student One",
            email="student.one@example.com",
            department="CSE",
            semester=6,
            section="423ZK",
        )
        faculty_old = models.Faculty(
            id=10,
            name="Old Faculty",
            email="old.faculty@example.com",
            department="CSE",
        )
        faculty_new = models.Faculty(
            id=11,
            name="New Faculty",
            email="new.faculty@example.com",
            department="CSE",
        )

        classroom_old = models.Classroom(id=301, block="10", room_number="201", capacity=60)
        classroom_new = models.Classroom(id=302, block="20", room_number="305", capacity=70)

        course_new = models.Course(
            id=101,
            code="NEW101",
            title="Legacy Title",
            faculty_id=faculty_old.id,
        )
        course_old = models.Course(
            id=202,
            code="OLD202",
            title="Deprecated Subject",
            faculty_id=faculty_old.id,
        )

        schedule_stale = models.ClassSchedule(
            id=1001,
            course_id=course_new.id,
            faculty_id=faculty_old.id,
            weekday=0,  # Monday, stale for this test blueprint
            start_time=time(10, 0),
            end_time=time(11, 0),
            classroom_label="10-201 - Lecture - NEW101 | 423ZK",
            is_active=True,
        )
        schedule_old_course = models.ClassSchedule(
            id=1002,
            course_id=course_old.id,
            faculty_id=faculty_old.id,
            weekday=2,
            start_time=time(12, 0),
            end_time=time(13, 0),
            classroom_label="12-401 - Lecture - OLD202 | 423ZK",
            is_active=True,
        )

        self.db.add_all(
            [
                student,
                faculty_old,
                faculty_new,
                classroom_old,
                classroom_new,
                course_new,
                course_old,
                models.CourseClassroom(id=401, course_id=course_new.id, classroom_id=classroom_old.id),
                models.CourseClassroom(id=402, course_id=course_old.id, classroom_id=classroom_old.id),
                schedule_stale,
                schedule_old_course,
                models.Enrollment(id=501, student_id=student.id, course_id=course_new.id),
                models.Enrollment(id=502, student_id=student.id, course_id=course_old.id),
                models.AttendanceRecord(
                    id=601,
                    student_id=student.id,
                    course_id=course_new.id,
                    marked_by_faculty_id=faculty_old.id,
                    attendance_date=date(2026, 2, 23),  # Monday mismatches test blueprint weekday
                    status=models.AttendanceStatus.PRESENT,
                    source="faculty-web",
                ),
                models.AttendanceRecord(
                    id=602,
                    student_id=student.id,
                    course_id=course_old.id,
                    marked_by_faculty_id=faculty_old.id,
                    attendance_date=date(2026, 2, 25),
                    status=models.AttendanceStatus.PRESENT,
                    source="faculty-web",
                ),
                models.AttendanceSubmission(
                    id=701,
                    schedule_id=schedule_stale.id,
                    course_id=course_new.id,
                    faculty_id=faculty_old.id,
                    student_id=student.id,
                    class_date=date(2026, 2, 23),
                    status=models.AttendanceSubmissionStatus.APPROVED,
                ),
                models.AttendanceSubmission(
                    id=702,
                    schedule_id=schedule_old_course.id,
                    course_id=course_old.id,
                    faculty_id=faculty_old.id,
                    student_id=student.id,
                    class_date=date(2026, 2, 25),
                    status=models.AttendanceSubmissionStatus.APPROVED,
                ),
            ]
        )
        self.db.commit()
        self.student = self.db.get(models.Student, 1)

    def test_loader_deactivates_stale_schedule_and_cleans_old_attendance(self):
        blueprint = [
            {
                "course_code": "NEW101",
                "course_title": "New Timetable Subject",
                "faculty_name": "New Faculty",
                "faculty_email": "new.faculty@example.com",
                "weekday": 1,  # Tuesday
                "start": "10:00",
                "end": "11:00",
                "classroom_block": "20",
                "classroom_room": "305",
                "classroom_label": "20-305 - Practical - NEW101 | 423ZK",
            }
        ]

        mongo_db = defaultdict(mock.Mock)
        with (
            mock.patch("app.routers.attendance.DEFAULT_TIMETABLE_BLUEPRINT", blueprint),
            mock.patch("app.routers.attendance.get_mongo_db", side_effect=lambda required=False: mongo_db),
        ):
            summary = _ensure_default_timetable_for_student(self.db, self.student)
            self.db.commit()

        self.assertEqual(summary["removed_enrollments"], 1)
        self.assertEqual(summary["deactivated_schedules"], 1)
        self.assertGreaterEqual(summary["purged_attendance_records"], 2)
        self.assertGreaterEqual(summary["purged_attendance_submissions"], 2)

        active_new_schedule = (
            self.db.query(models.ClassSchedule)
            .filter(
                models.ClassSchedule.course_id == 101,
                models.ClassSchedule.weekday == 1,
                models.ClassSchedule.start_time == time(10, 0),
                models.ClassSchedule.is_active.is_(True),
            )
            .first()
        )
        self.assertIsNotNone(active_new_schedule)

        stale_schedule = self.db.get(models.ClassSchedule, 1001)
        self.assertIsNotNone(stale_schedule)
        self.assertFalse(stale_schedule.is_active)

        old_enrollment = (
            self.db.query(models.Enrollment)
            .filter(models.Enrollment.student_id == 1, models.Enrollment.course_id == 202)
            .first()
        )
        self.assertIsNone(old_enrollment)

        remaining_records = (
            self.db.query(models.AttendanceRecord)
            .filter(models.AttendanceRecord.student_id == 1)
            .count()
        )
        remaining_submissions = (
            self.db.query(models.AttendanceSubmission)
            .filter(models.AttendanceSubmission.student_id == 1)
            .count()
        )
        self.assertEqual(remaining_records, 0)
        self.assertEqual(remaining_submissions, 0)


if __name__ == "__main__":
    unittest.main()
