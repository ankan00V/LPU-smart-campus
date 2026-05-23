"""Reissue student registration numbers and faculty IDs by arrival order."""

from __future__ import annotations

import argparse

from app.database import SessionLocal
from app.routers.auth import reissue_generated_profile_identifiers
from app import models
from app.mongo import get_mongo_db, init_mongo


def _sync_mongo_profiles(sql_db) -> None:
    if not init_mongo():
        return
    mongo_db = get_mongo_db(required=False)
    if mongo_db is None:
        return

    for student in sql_db.query(models.Student).all():
        mongo_db["students"].update_one(
            {"id": int(student.id)},
            {
                "$set": {
                    "registration_number": student.registration_number,
                    "email": student.email,
                    "source": "generated-profile-id-reissue",
                }
            },
            upsert=True,
        )
        mongo_db["auth_users"].update_one(
            {"student_id": int(student.id)},
            {
                "$set": {
                    "student_id": int(student.id),
                    "registration_number": student.registration_number,
                }
            },
        )

    for faculty in sql_db.query(models.Faculty).all():
        mongo_db["faculty"].update_one(
            {"id": int(faculty.id)},
            {
                "$set": {
                    "faculty_identifier": faculty.faculty_identifier,
                    "email": faculty.email,
                    "source": "generated-profile-id-reissue",
                }
            },
            upsert=True,
        )
        mongo_db["auth_users"].update_one(
            {"faculty_id": int(faculty.id)},
            {
                "$set": {
                    "faculty_id": int(faculty.id),
                    "faculty_identifier": faculty.faculty_identifier,
                }
            },
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replace manually entered student/faculty IDs with generated arrival-order IDs."
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview counts without committing changes.")
    parser.add_argument("--skip-mongo-sync", action="store_true", help="Do not update Mongo mirror collections.")
    args = parser.parse_args()

    sql_db = SessionLocal()
    try:
        counts = reissue_generated_profile_identifiers(sql_db)
        if args.dry_run:
            sql_db.rollback()
            print(f"dry_run=true students={counts['students']} faculty={counts['faculty']}")
            return 0

        sql_db.commit()
        if not args.skip_mongo_sync:
            _sync_mongo_profiles(sql_db)
        print(f"reissued students={counts['students']} faculty={counts['faculty']}")
        return 0
    except Exception:
        sql_db.rollback()
        raise
    finally:
        sql_db.close()


if __name__ == "__main__":
    raise SystemExit(main())
