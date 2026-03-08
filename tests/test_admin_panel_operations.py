import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.routers.admin import (
    admin_list_student_grades,
    admin_search_everything,
    admin_search_faculty_by_identifier,
    admin_search_student_by_registration,
    admin_upsert_student_grade,
)


class AdminPanelOpsTests(unittest.TestCase):
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
        faculty = models.Faculty(
            id=11,
            name="Faculty One",
            email="faculty.one@example.com",
            faculty_identifier="FAC-CSE-11",
            section="P132",
            department="CSE",
        )
        student = models.Student(
            id=101,
            name="Student One",
            email="student.one@example.com",
            registration_number="22BCS101",
            section="P132",
            department="CSE",
            semester=4,
        )
        course = models.Course(
            id=201,
            code="CSE101",
            title="Data Structures",
            faculty_id=11,
        )
        enrollment = models.Enrollment(
            id=301,
            student_id=101,
            course_id=201,
        )
        self.db.add_all([faculty, student, course, enrollment])
        self.db.commit()

    @staticmethod
    def _admin_user() -> models.AuthUser:
        return models.AuthUser(
            id=1,
            email="admin@example.com",
            password_hash="x",
            role=models.UserRole.ADMIN,
            student_id=None,
            faculty_id=None,
            is_active=True,
        )

    def test_admin_can_search_student_by_registration(self):
        out = admin_search_student_by_registration(
            registration_number="22BCS101",
            db=self.db,
            _=self._admin_user(),
        )
        self.assertEqual(out.student_id, 101)
        self.assertEqual(out.registration_number, "22BCS101")

    def test_admin_can_search_faculty_by_identifier(self):
        out = admin_search_faculty_by_identifier(
            faculty_identifier="FAC-CSE-11",
            db=self.db,
            _=self._admin_user(),
        )
        self.assertEqual(out.faculty_id, 11)
        self.assertEqual(out.faculty_identifier, "FAC-CSE-11")

    def test_admin_global_search_returns_students_faculty_and_courses(self):
        out = admin_search_everything(
            query="cse",
            limit=25,
            db=self.db,
            _=self._admin_user(),
        )
        self.assertGreaterEqual(out.total_matches, 3)
        self.assertTrue(any(item.registration_number == "22BCS101" for item in out.students))
        self.assertTrue(any(item.faculty_identifier == "FAC-CSE-11" for item in out.faculty))
        self.assertTrue(any(item.course_code == "CSE101" for item in out.courses))

    def test_admin_can_upsert_and_list_student_grades(self):
        first = admin_upsert_student_grade(
            payload=schemas.AdminStudentGradeUpsertRequest(
                registration_number="22BCS101",
                course_code="CSE101",
                grade_letter="A",
                marks_percent=91.25,
                remark="Excellent",
            ),
            db=self.db,
            current_user=self._admin_user(),
        )
        self.assertEqual(first.grade_letter, "A")
        self.assertEqual(first.course_code, "CSE101")
        self.assertEqual(first.registration_number, "22BCS101")

        second = admin_upsert_student_grade(
            payload=schemas.AdminStudentGradeUpsertRequest(
                registration_number="22BCS101",
                course_code="CSE101",
                grade_letter="A+",
                marks_percent=95.0,
                remark="Outstanding",
            ),
            db=self.db,
            current_user=self._admin_user(),
        )
        self.assertEqual(second.grade_letter, "A+")
        self.assertEqual(second.marks_percent, 95.0)

        history = admin_list_student_grades(
            registration_number="22BCS101",
            db=self.db,
            _=self._admin_user(),
        )
        self.assertEqual(history.student.registration_number, "22BCS101")
        self.assertEqual(len(history.grades), 1)
        self.assertEqual(history.grades[0].grade_letter, "A+")

    def test_grade_upsert_blocks_non_enrolled_student(self):
        extra_student = models.Student(
            id=102,
            name="Student Two",
            email="student.two@example.com",
            registration_number="22BCS102",
            section="P132",
            department="CSE",
            semester=4,
        )
        self.db.add(extra_student)
        self.db.commit()

        with self.assertRaises(HTTPException) as ctx:
            admin_upsert_student_grade(
                payload=schemas.AdminStudentGradeUpsertRequest(
                    registration_number="22BCS102",
                    course_code="CSE101",
                    grade_letter="B",
                    marks_percent=76.0,
                ),
                db=self.db,
                current_user=self._admin_user(),
            )
        self.assertEqual(ctx.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
