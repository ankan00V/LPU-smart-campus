import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.auth_utils import CurrentUser
from app.routers.attendance import faculty_update_student_section


class StudentSectionChangeFlowTests(unittest.TestCase):
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
        now_dt = datetime.utcnow()
        self.student = models.Student(
            id=100,
            name="Student One",
            email="student.one@example.com",
            section="P132",
            section_updated_at=now_dt - timedelta(hours=49),
            department="CSE",
            semester=6,
        )
        self.faculty = models.Faculty(
            id=200,
            name="Faculty One",
            email="faculty.one@example.com",
            section="P133",
            department="CSE",
        )
        self.db.add_all([self.student, self.faculty])
        self.db.commit()

    @staticmethod
    def _user(
        *,
        role: models.UserRole,
        user_id: int,
        faculty_id: int | None = None,
    ) -> CurrentUser:
        return CurrentUser(
            id=user_id,
            email=f"{role.value}{user_id}@example.com",
            role=role,
            student_id=None,
            faculty_id=faculty_id,
            alternate_email=None,
            primary_login_verified=True,
            is_active=True,
        )

    def _run_update(self, *, actor: CurrentUser, section: str):
        with patch("app.routers.attendance._sync_student_to_mongo", return_value=None), patch(
            "app.routers.attendance.mirror_document",
            return_value=None,
        ):
            return faculty_update_student_section(
                student_id=self.student.id,
                payload=schemas.FacultyStudentSectionUpdateRequest(section=section),
                db=self.db,
                current_user=actor,
            )

    def test_faculty_can_move_student_to_own_section_after_window(self):
        actor = self._user(role=models.UserRole.FACULTY, user_id=7, faculty_id=self.faculty.id)
        out = self._run_update(actor=actor, section="P133")

        self.assertEqual(out.section, "P133")
        refreshed = self.db.get(models.Student, self.student.id)
        self.assertEqual(refreshed.section, "P133")

    def test_faculty_cannot_assign_outside_scope(self):
        actor = self._user(role=models.UserRole.FACULTY, user_id=7, faculty_id=self.faculty.id)
        with self.assertRaises(HTTPException) as ctx:
            self._run_update(actor=actor, section="P200")
        self.assertEqual(ctx.exception.status_code, 403)

    def test_faculty_update_respects_student_lock_window(self):
        student = self.db.get(models.Student, self.student.id)
        student.section_updated_at = datetime.utcnow() - timedelta(hours=2)
        self.db.commit()

        actor = self._user(role=models.UserRole.FACULTY, user_id=7, faculty_id=self.faculty.id)
        with self.assertRaises(HTTPException) as ctx:
            self._run_update(actor=actor, section="P133")
        self.assertEqual(ctx.exception.status_code, 423)

    def test_admin_can_override_student_section_lock_window(self):
        student = self.db.get(models.Student, self.student.id)
        student.section_updated_at = datetime.utcnow() - timedelta(hours=2)
        self.db.commit()

        actor = self._user(role=models.UserRole.ADMIN, user_id=1, faculty_id=None)
        out = self._run_update(actor=actor, section="P200")

        self.assertEqual(out.section, "P200")
        refreshed = self.db.get(models.Student, self.student.id)
        self.assertEqual(refreshed.section, "P200")


if __name__ == "__main__":
    unittest.main()
