#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_env() -> None:
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / ".env.local")


def _normalize_email(email: str | None) -> str:
    return (email or "").strip().lower()


def main() -> int:
    _load_env()

    from app import models
    from app.auth_utils import _ensure_sql_auth_user
    from app.database import SessionLocal
    from app.id_alignment import (
        align_auth_user_id_with_sql,
        align_faculty_profile_id_with_sql,
        align_student_profile_id_with_sql,
    )
    from app.mongo import get_mongo_db, init_mongo

    init_mongo(force=True)
    mongo_db = get_mongo_db(required=True)

    sql_db = SessionLocal()
    try:
        print("Aligning SQL auth users -> Mongo auth_users")
        for sql_user in sql_db.query(models.AuthUser).all():
            email = _normalize_email(sql_user.email)
            if not email:
                continue
            user_doc = mongo_db["auth_users"].find_one({"email": email})
            if user_doc:
                align_auth_user_id_with_sql(mongo_db, sql_db, user_doc)
            else:
                mongo_db["auth_users"].insert_one(
                    {
                        "id": int(sql_user.id),
                        "email": email,
                        "password_hash": str(sql_user.password_hash or ""),
                        "role": sql_user.role.value,
                        "student_id": int(sql_user.student_id) if sql_user.student_id else None,
                        "faculty_id": int(sql_user.faculty_id) if sql_user.faculty_id else None,
                        "alternate_email": None,
                        "alternate_email_encrypted": None,
                        "alternate_email_hash": None,
                        "primary_login_verified": False,
                        "mfa_enabled": False,
                        "is_active": bool(sql_user.is_active),
                        "created_at": sql_user.created_at,
                        "last_login_at": sql_user.last_login_at,
                    }
                )

        print("Aligning Mongo auth_users -> SQL auth_users")
        for user_doc in mongo_db["auth_users"].find({}):
            _ensure_sql_auth_user(user_doc)

        print("Aligning students (SQL -> Mongo)")
        for student in sql_db.query(models.Student).all():
            email = _normalize_email(student.email)
            if not email:
                continue
            align_student_profile_id_with_sql(mongo_db, sql_db, email=email, user_doc=None)

        print("Aligning faculty (SQL -> Mongo)")
        for faculty in sql_db.query(models.Faculty).all():
            email = _normalize_email(faculty.email)
            if not email:
                continue
            align_faculty_profile_id_with_sql(mongo_db, sql_db, email=email, user_doc=None)

        print("ID alignment completed.")
        return 0
    finally:
        sql_db.close()


if __name__ == "__main__":
    raise SystemExit(main())
