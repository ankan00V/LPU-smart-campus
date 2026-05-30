import unittest
from datetime import date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.academic_policy import assign_student_section, sync_faculty_sections_for_student, sync_student_academic_term
from app.auth_utils import CurrentUser
from app.routers.attendance import get_academic_term_config, update_academic_term_config
from app import schemas


class AcademicPolicyTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_assigns_expected_section_for_current_semester_year_and_stream(self):
        student = models.Student(
            name="Student",
            email="student@example.com",
            department="School of Computer Science Engineering",
            semester=4,
            created_at=datetime(2026, 5, 29, 9, 0, 0),
        )
        self.db.add(student)
        self.db.flush()

        section = assign_student_section(self.db, student, now=datetime(2026, 5, 29, 12, 0, 0))

        self.assertEqual(section, "426CSE")
        self.assertEqual(student.section, "426CSE")

    def test_rollover_advances_semester_and_reassigns_section_on_new_term(self):
        student = models.Student(
            name="Student",
            email="student@example.com",
            department="CSE",
            semester=4,
            section="426CSE",
            section_updated_at=datetime(2026, 5, 29, 9, 0, 0),
            created_at=datetime(2026, 5, 29, 9, 0, 0),
        )
        self.db.add(student)
        self.db.flush()

        changed = sync_student_academic_term(self.db, student, now=datetime(2026, 7, 1, 0, 1, 0))

        self.assertTrue(changed)
        self.assertEqual(student.semester, 5)
        self.assertEqual(student.section, "526CSE")

    def test_legacy_section_is_replaced_by_current_policy_section(self):
        student = models.Student(
            name="Student",
            email="student@example.com",
            department="CSE",
            semester=4,
            section="P132",
            section_updated_at=datetime(2026, 5, 29, 9, 0, 0),
            created_at=datetime(2026, 5, 29, 9, 0, 0),
        )
        self.db.add(student)
        self.db.flush()

        changed = sync_student_academic_term(self.db, student, now=datetime(2026, 5, 30, 9, 0, 0))

        self.assertTrue(changed)
        self.assertEqual(student.section, "426CSE")

    def test_syncs_enrolled_course_faculty_to_student_policy_section(self):
        student = models.Student(
            id=1,
            name="Student",
            email="student@example.com",
            department="CSE",
            semester=4,
            section="426CSE",
            section_updated_at=datetime(2026, 5, 29, 9, 0, 0),
            created_at=datetime(2026, 5, 29, 9, 0, 0),
        )
        faculty = models.Faculty(
            id=11,
            name="Faculty",
            email="faculty@example.com",
            department="CSE",
            section="423ZK",
        )
        course = models.Course(id=21, code="CSE101", title="Algorithms", faculty_id=11)
        enrollment = models.Enrollment(id=31, student_id=1, course_id=21)
        self.db.add_all([student, faculty, course, enrollment])
        self.db.flush()

        changed = sync_faculty_sections_for_student(self.db, student, now=datetime(2026, 5, 30, 9, 0, 0))

        self.assertEqual(changed, 1)
        self.assertEqual(faculty.section, "426CSE")

    def test_admin_can_update_academic_class_window(self):
        admin = CurrentUser(
            id=1,
            email="admin@example.com",
            role=models.UserRole.ADMIN,
            student_id=None,
            faculty_id=None,
            alternate_email=None,
            primary_login_verified=True,
            is_active=True,
        )

        payload = update_academic_term_config(
            schemas.AcademicTermConfigRequest(
                class_start_date=date(2025, 7, 1),
                class_end_date=date(2026, 7, 1),
            ),
            db=self.db,
            current_user=admin,
        )

        self.assertEqual(payload.class_start_date, date(2025, 7, 1))
        self.assertEqual(payload.class_end_date, date(2026, 7, 1))
        loaded = get_academic_term_config(db=self.db, current_user=admin)
        self.assertEqual(loaded.class_end_date, date(2026, 7, 1))


if __name__ == "__main__":
    unittest.main()
