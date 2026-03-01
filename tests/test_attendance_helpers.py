import unittest
from datetime import date, datetime, time
from unittest import mock

from pymongo.errors import DuplicateKeyError

from app import models
from app.routers.attendance import (
    _count_delivered_occurrences,
    _faculty_section_lock_state,
    _is_submission_credited,
    _upsert_mongo_by_id,
    _student_section_lock_state,
)


class AttendanceHelpersTests(unittest.TestCase):
    def test_count_delivered_occurrences_counts_ongoing_class(self):
        schedule = models.ClassSchedule(
            course_id=1,
            faculty_id=1,
            weekday=3,  # Thursday
            start_time=time(15, 0),
            end_time=time(16, 0),
            is_active=True,
        )
        delivered = _count_delivered_occurrences(
            schedule,
            from_date=date(2026, 2, 19),
            now_dt=datetime(2026, 2, 19, 15, 9),
        )
        self.assertEqual(delivered, 1)

    def test_count_delivered_occurrences_excludes_upcoming_class(self):
        schedule = models.ClassSchedule(
            course_id=1,
            faculty_id=1,
            weekday=3,  # Thursday
            start_time=time(15, 0),
            end_time=time(16, 0),
            is_active=True,
        )
        delivered = _count_delivered_occurrences(
            schedule,
            from_date=date(2026, 2, 19),
            now_dt=datetime(2026, 2, 19, 14, 40),
        )
        self.assertEqual(delivered, 0)

    def test_submission_credited_status(self):
        self.assertTrue(_is_submission_credited(models.AttendanceSubmissionStatus.VERIFIED))
        self.assertTrue(_is_submission_credited(models.AttendanceSubmissionStatus.APPROVED))
        self.assertFalse(_is_submission_credited(models.AttendanceSubmissionStatus.REJECTED))
        self.assertFalse(_is_submission_credited(None))

    def test_student_section_lock_window_is_48_hours(self):
        now_dt = datetime(2026, 2, 28, 10, 0)
        student = models.Student(
            name="Test Student",
            email="student@example.com",
            department="CSE",
            semester=6,
            section="P132",
            section_updated_at=now_dt,
        )
        can_change, _, remaining_minutes = _student_section_lock_state(student, now_dt=now_dt)
        self.assertFalse(can_change)
        self.assertEqual(remaining_minutes, 48 * 60)

    def test_faculty_section_lock_window_is_24_hours(self):
        now_dt = datetime(2026, 2, 28, 10, 0)
        faculty = models.Faculty(
            name="Test Faculty",
            email="faculty@example.com",
            department="CSE",
            section="P132",
            section_updated_at=now_dt,
        )
        can_change, _, remaining_minutes = _faculty_section_lock_state(faculty, now_dt=now_dt)
        self.assertFalse(can_change)
        self.assertEqual(remaining_minutes, 24 * 60)

    def test_upsert_mongo_by_id_retries_on_secondary_unique_collision(self):
        collection = mock.Mock()
        duplicate_error = DuplicateKeyError(
            "duplicate course_id",
            11000,
            {"keyValue": {"course_id": 4}},
        )
        collection.update_one.side_effect = [duplicate_error, mock.Mock(matched_count=1)]
        mongo_db = {"course_classrooms": collection}

        with mock.patch("app.routers.attendance.get_mongo_db", return_value=mongo_db):
            _upsert_mongo_by_id(
                "course_classrooms",
                99,
                {
                    "course_id": 4,
                    "classroom_id": 12,
                    "source": "test",
                },
            )

        collection.update_one.assert_has_calls(
            [
                mock.call(
                    {"id": 99},
                    {
                        "$set": {
                            "course_id": 4,
                            "classroom_id": 12,
                            "source": "test",
                            "id": 99,
                        }
                    },
                    upsert=True,
                ),
                mock.call(
                    {"course_id": 4},
                    {
                        "$set": {
                            "course_id": 4,
                            "classroom_id": 12,
                            "source": "test",
                        }
                    },
                    upsert=False,
                ),
            ]
        )

    def test_upsert_mongo_by_id_ignores_unresolved_duplicate_collision(self):
        collection = mock.Mock()
        duplicate_error = DuplicateKeyError(
            "duplicate course_id",
            11000,
            {"keyValue": {"course_id": 4}},
        )
        collection.update_one.side_effect = [duplicate_error, mock.Mock(matched_count=0)]
        mongo_db = {"course_classrooms": collection}

        with mock.patch("app.routers.attendance.get_mongo_db", return_value=mongo_db):
            _upsert_mongo_by_id(
                "course_classrooms",
                99,
                {
                    "course_id": 4,
                    "classroom_id": 12,
                    "source": "test",
                },
            )


if __name__ == "__main__":
    unittest.main()
