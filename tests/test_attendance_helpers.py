import unittest
from datetime import date, datetime, time

from app import models
from app.routers.attendance import _count_delivered_occurrences, _is_submission_credited


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


if __name__ == "__main__":
    unittest.main()
