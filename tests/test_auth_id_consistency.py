import unittest
from datetime import datetime
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from app import models, schemas
from app.routers.attendance import get_faculty_profile, get_student_profile, update_student_profile
from app.routers.auth import _ensure_role_profile_link, register_auth_user, reissue_generated_profile_identifiers
from app.routers.enterprise import _upsert_federated_user


class _FixedDatetime(datetime):
    @classmethod
    def utcnow(cls):
        return cls(2026, 5, 13, 12, 0, 0)


class _UpdateResult:
    def __init__(self, *, matched_count: int = 0):
        self.matched_count = matched_count


class _Collection:
    def __init__(self):
        self._rows: list[dict] = []

    def insert_one(self, doc: dict):
        self._rows.append(dict(doc))

    def find_one(self, query: dict, projection: dict | None = None):
        for row in self._rows:
            if self._match(row, query):
                if not projection:
                    return dict(row)
                projected: dict = {}
                for key, include in projection.items():
                    if include and key in row:
                        projected[key] = row[key]
                return projected
        return None

    def update_one(self, query: dict, update: dict, upsert: bool = False):
        for idx, row in enumerate(self._rows):
            if not self._match(row, query):
                continue
            updated = dict(row)
            self._apply_update(updated, update)
            self._rows[idx] = updated
            return _UpdateResult(matched_count=1)

        if upsert:
            created: dict = {}
            for key, value in query.items():
                if not key.startswith("$") and not isinstance(value, dict):
                    created[key] = value
            self._apply_update(created, update)
            self._rows.append(created)
        return _UpdateResult(matched_count=0)

    @staticmethod
    def _apply_update(row: dict, update: dict) -> None:
        for key, payload in update.items():
            if key == "$set":
                row.update(payload)
            elif key == "$max":
                for field_name, value in payload.items():
                    current = row.get(field_name)
                    if current is None or current < value:
                        row[field_name] = value

    @staticmethod
    def _match(row: dict, query: dict) -> bool:
        for key, expected in query.items():
            if key == "$or":
                return any(_Collection._match(row, branch) for branch in expected)
            if isinstance(expected, dict):
                if "$exists" in expected:
                    exists = key in row
                    if exists != bool(expected["$exists"]):
                        return False
                    continue
            if row.get(key) != expected:
                return False
        return True


class _FakeMongo:
    def __init__(self):
        self._collections: dict[str, _Collection] = {}

    def __getitem__(self, name: str) -> _Collection:
        if name not in self._collections:
            self._collections[name] = _Collection()
        return self._collections[name]


def _request(path: str) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": path,
        "headers": [(b"user-agent", b"pytest")],
        "client": ("127.0.0.1", 9000),
        "query_string": b"",
    }
    return Request(scope)


class AuthIdConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()
        self.mongo = _FakeMongo()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_register_keeps_sql_and_mongo_auth_user_ids_aligned(self):
        payload = schemas.AuthRegisterRequest(
            email="aligned.student@gmail.com",
            password="Student@123",
            role=models.UserRole.STUDENT,
            name="Aligned Student",
            department="CSE",
            semester=3,
            section="K23AA",
            registration_number="MANUAL-OLD",
            parent_email="parent@example.com",
        )

        with (
            patch("app.routers.auth.datetime", _FixedDatetime),
            patch("app.routers.auth._mongo_db_or_503", return_value=self.mongo),
            patch("app.routers.auth._verify_student_auth_recaptcha", return_value=None),
            patch("app.routers.auth.assess_applicant_risk", return_value=None),
            patch("app.routers.auth.mirror_event", return_value=None),
        ):
            result = register_auth_user(payload, request=_request("/auth/register"), sql_db=self.db)

        sql_user = self.db.query(models.AuthUser).filter(models.AuthUser.email == payload.email).first()
        sql_student = self.db.query(models.Student).filter(models.Student.email == payload.email).first()
        mongo_user = self.mongo["auth_users"].find_one({"email": payload.email})

        self.assertIsNotNone(sql_user)
        self.assertIsNotNone(sql_student)
        self.assertIsNotNone(mongo_user)
        self.assertEqual(result.id, sql_user.id)
        self.assertEqual(mongo_user["id"], sql_user.id)
        self.assertEqual(mongo_user["student_id"], sql_student.id)
        self.assertEqual(sql_student.registration_number, "12600001")

    def test_ensure_role_profile_link_restores_missing_sql_student_profile_from_mongo(self):
        self.mongo["auth_users"].insert_one(
            {
                "id": 44,
                "email": "legacy.student@gmail.com",
                "role": models.UserRole.STUDENT.value,
                "student_id": 91,
                "is_active": True,
                "created_at": datetime.utcnow(),
            }
        )
        self.mongo["students"].insert_one(
            {
                "id": 91,
                "name": "LEGACY STUDENT",
                "email": "legacy.student@gmail.com",
                "registration_number": "12200091",
                "section": "K23AA",
                "department": "CSE",
                "semester": 4,
                "created_at": datetime.utcnow(),
            }
        )
        user_doc = self.mongo["auth_users"].find_one({"id": 44})

        _ensure_role_profile_link(
            self.mongo,
            self.db,
            user_doc=user_doc,
            role=models.UserRole.STUDENT,
            email="legacy.student@gmail.com",
        )

        sql_student = self.db.get(models.Student, 91)
        self.assertIsNotNone(sql_student)
        self.assertEqual(sql_student.email, "legacy.student@gmail.com")
        self.assertEqual(sql_student.department, "CSE")
        self.assertEqual(sql_student.semester, 4)
        self.assertEqual(user_doc["student_id"], 91)

    def test_register_normalizes_student_signup_text_fields_to_uppercase(self):
        payload = schemas.AuthRegisterRequest(
            email="case.student@gmail.com",
            password="Student@123",
            role=models.UserRole.STUDENT,
            name="case student",
            department="cse ai",
            semester=4,
            section="k23 aa",
            registration_number="22bcs101",
            parent_email="Parent@Example.com",
        )

        with (
            patch("app.routers.auth.datetime", _FixedDatetime),
            patch("app.routers.auth._mongo_db_or_503", return_value=self.mongo),
            patch("app.routers.auth._verify_student_auth_recaptcha", return_value=None),
            patch("app.routers.auth.assess_applicant_risk", return_value=None),
            patch("app.routers.auth.mirror_event", return_value=None),
        ):
            result = register_auth_user(payload, request=_request("/auth/register"), sql_db=self.db)

        sql_student = self.db.query(models.Student).filter(models.Student.email == "case.student@gmail.com").first()
        mongo_user = self.mongo["auth_users"].find_one({"email": "case.student@gmail.com"})

        self.assertIsNotNone(sql_student)
        self.assertIsNotNone(mongo_user)
        self.assertEqual(result.name, "CASE STUDENT")
        self.assertEqual(sql_student.name, "CASE STUDENT")
        self.assertEqual(sql_student.department, "CSE AI")
        self.assertEqual(sql_student.section, "K23AA")
        self.assertEqual(sql_student.registration_number, "12600001")
        self.assertEqual(sql_student.parent_email, "parent@example.com")
        self.assertEqual(mongo_user["name"], "CASE STUDENT")

    def test_register_generates_faculty_identifier_from_reversed_year_and_arrival_position(self):
        payload = schemas.AuthRegisterRequest(
            email="faculty.generated@gmail.com",
            password="Faculty@123",
            role=models.UserRole.FACULTY,
            name="Generated Faculty",
            department="CSE",
            faculty_identifier="FAC-MANUAL",
        )

        with (
            patch("app.routers.auth.datetime", _FixedDatetime),
            patch("app.routers.auth._mongo_db_or_503", return_value=self.mongo),
            patch("app.routers.auth.assess_applicant_risk", return_value=None),
            patch("app.routers.auth.mirror_event", return_value=None),
        ):
            register_auth_user(payload, request=_request("/auth/register"), sql_db=self.db)

        sql_faculty = self.db.query(models.Faculty).filter(models.Faculty.email == "faculty.generated@gmail.com").first()

        self.assertIsNotNone(sql_faculty)
        self.assertEqual(sql_faculty.faculty_identifier, "620001")

    def test_reissue_generated_profile_identifiers_replaces_manual_ids_by_arrival_order(self):
        self.db.add_all(
            [
                models.Student(
                    name="FIRST STUDENT",
                    email="first.student@gmail.com",
                    registration_number="22BCS101",
                    section="K23AA",
                    department="CSE",
                    semester=1,
                    created_at=datetime(2026, 1, 3, 9, 0, 0),
                ),
                models.Student(
                    name="SECOND STUDENT",
                    email="second.student@gmail.com",
                    registration_number="22BCS102",
                    section="K23AA",
                    department="CSE",
                    semester=1,
                    created_at=datetime(2026, 1, 4, 9, 0, 0),
                ),
                models.Faculty(
                    name="FIRST FACULTY",
                    email="first.faculty@gmail.com",
                    faculty_identifier="FAC-CSE-11",
                    department="CSE",
                    created_at=datetime(2026, 1, 2, 9, 0, 0),
                ),
            ]
        )
        self.db.commit()

        counts = reissue_generated_profile_identifiers(self.db)

        students = self.db.query(models.Student).order_by(models.Student.created_at).all()
        faculty = self.db.query(models.Faculty).one()
        self.assertEqual(counts, {"students": 2, "faculty": 1})
        self.assertEqual([student.registration_number for student in students], ["12600001", "12600002"])
        self.assertEqual(faculty.faculty_identifier, "620001")

    def test_student_profile_get_reissues_manual_registration_by_arrival_order(self):
        student = models.Student(
            name="MANUAL STUDENT",
            email="manual.student@gmail.com",
            registration_number="22BCS101",
            section="K23AA",
            department="CSE",
            semester=1,
            created_at=datetime(2026, 1, 3, 9, 0, 0),
        )
        self.db.add(student)
        self.db.commit()
        self.db.refresh(student)
        auth_user = models.AuthUser(
            email=student.email,
            password_hash="hash",
            role=models.UserRole.STUDENT,
            student_id=student.id,
            is_active=True,
        )
        self.db.add(auth_user)
        self.db.commit()
        self.db.refresh(auth_user)

        out = get_student_profile(db=self.db, current_user=auth_user)

        self.assertEqual(out.registration_number, "12600001")
        self.assertEqual(self.db.get(models.Student, student.id).registration_number, "12600001")

    def test_faculty_profile_get_reissues_manual_identifier_by_arrival_order(self):
        faculty = models.Faculty(
            name="MANUAL FACULTY",
            email="manual.faculty@gmail.com",
            faculty_identifier="FAC-CSE-11",
            department="CSE",
            created_at=datetime(2026, 1, 2, 9, 0, 0),
        )
        self.db.add(faculty)
        self.db.commit()
        self.db.refresh(faculty)
        auth_user = models.AuthUser(
            email=faculty.email,
            password_hash="hash",
            role=models.UserRole.FACULTY,
            faculty_id=faculty.id,
            is_active=True,
        )
        self.db.add(auth_user)
        self.db.commit()
        self.db.refresh(auth_user)

        out = get_faculty_profile(db=self.db, current_user=auth_user)

        self.assertEqual(out.faculty_identifier, "620001")
        self.assertEqual(self.db.get(models.Faculty, faculty.id).faculty_identifier, "620001")

    def test_student_profile_rejects_manual_registration_number_updates(self):
        student = models.Student(
            name="SYSTEM STUDENT",
            email="system.student@gmail.com",
            registration_number="12600001",
            section="K23AA",
            department="CSE",
            semester=1,
            created_at=datetime(2026, 1, 3, 9, 0, 0),
        )
        self.db.add(student)
        self.db.commit()
        self.db.refresh(student)
        auth_user = models.AuthUser(
            email=student.email,
            password_hash="hash",
            role=models.UserRole.STUDENT,
            student_id=student.id,
            is_active=True,
        )
        self.db.add(auth_user)
        self.db.commit()

        with self.assertRaises(HTTPException) as exc:
            update_student_profile(
                schemas.StudentProfileUpdateRequest(registration_number="22BCS101"),
                db=self.db,
                current_user=auth_user,
            )

        self.assertEqual(exc.exception.status_code, 400)
        self.assertIn("system-assigned", exc.exception.detail)

    def test_federated_upsert_reuses_existing_sql_auth_user_id(self):
        sql_user = models.AuthUser(
            email="aligned.faculty@gmail.com",
            password_hash="existing-hash",
            role=models.UserRole.FACULTY,
            is_active=True,
        )
        self.db.add(sql_user)
        self.db.commit()
        self.db.refresh(sql_user)

        self.mongo["auth_users"].insert_one(
            {
                "id": int(sql_user.id) + 77,
                "email": "aligned.faculty@gmail.com",
                "password_hash": "existing-hash",
                "role": models.UserRole.FACULTY.value,
                "student_id": None,
                "faculty_id": None,
                "is_active": True,
            }
        )

        user_doc = _upsert_federated_user(
            self.mongo,
            self.db,
            email="aligned.faculty@gmail.com",
            name="Aligned Faculty",
            role=models.UserRole.FACULTY,
            provider="oidc:okta",
            tenant="campus",
            subject="faculty-subject",
            idp_mfa_verified=False,
        )

        mongo_user = self.mongo["auth_users"].find_one({"email": "aligned.faculty@gmail.com"})
        self.assertEqual(user_doc["id"], sql_user.id)
        self.assertEqual(mongo_user["id"], sql_user.id)


if __name__ == "__main__":
    unittest.main()
