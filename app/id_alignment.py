from __future__ import annotations

import logging

from fastapi import HTTPException
from pymongo.errors import PyMongoError
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models
from .mongo import invalidate_mongo_connection

LOGGER = logging.getLogger(__name__)

_AUTH_USER_ID_COLLECTIONS = (
    "auth_sessions",
    "auth_otps",
    "auth_otp_delivery",
    "auth_token_revocations",
)

_STUDENT_ID_ARRAY_FIELDS = (
    "student_ids",
    "recipient_student_ids",
    "linked_student_ids",
)


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _raise_auth_datastore_unavailable(exc: Exception) -> None:
    invalidate_mongo_connection(exc)
    raise HTTPException(
        status_code=503,
        detail=(
            "Authentication datastore is temporarily unavailable for writes. "
            "Please retry in a few seconds."
        ),
    ) from exc


def bump_mongo_counter(db, name: str, target_id: int) -> None:
    if not target_id:
        return
    try:
        db["counters"].update_one({"_id": name}, {"$max": {"seq": int(target_id)}}, upsert=True)
    except Exception:
        return


def migrate_profile_id_references(
    db,
    *,
    field_name: str,
    old_id: int,
    new_id: int,
) -> None:
    if not old_id or not new_id or old_id == new_id:
        return
    for collection_name in db.list_collection_names():
        try:
            collection = db[collection_name]
            collection.update_many({field_name: int(old_id)}, {"$set": {field_name: int(new_id)}})
            if field_name == "student_id":
                for array_field in _STUDENT_ID_ARRAY_FIELDS:
                    collection.update_many(
                        {array_field: int(old_id)},
                        {"$set": {f"{array_field}.$[elem]": int(new_id)}},
                        array_filters=[{"elem": int(old_id)}],
                    )
        except Exception:
            continue


def align_auth_user_id_with_sql(db, sql_db: Session | None, user_doc: dict) -> int | None:
    if sql_db is None:
        return None

    email = _normalize_email(str(user_doc.get("email", "")))
    if not email:
        return None

    sql_user = (
        sql_db.query(models.AuthUser)
        .filter(func.lower(models.AuthUser.email) == email)
        .first()
    )
    if not sql_user:
        return None

    target_id = int(sql_user.id)
    try:
        current_id = int(user_doc.get("id") or 0)
    except (TypeError, ValueError):
        current_id = 0

    if current_id == target_id and target_id > 0:
        return target_id

    conflict = db["auth_users"].find_one({"id": target_id}, {"email": 1})
    if conflict and _normalize_email(str(conflict.get("email", ""))) != email:
        raise HTTPException(
            status_code=409,
            detail="Auth user id collision detected. Contact support to reconcile auth records.",
        )

    try:
        db["auth_users"].update_one({"email": email}, {"$set": {"id": target_id}})
        if current_id and current_id != target_id:
            for collection_name in _AUTH_USER_ID_COLLECTIONS:
                db[collection_name].update_many(
                    {"user_id": int(current_id)},
                    {"$set": {"user_id": int(target_id)}},
                )
        bump_mongo_counter(db, "auth_users", target_id)
    except PyMongoError as exc:
        _raise_auth_datastore_unavailable(exc)

    user_doc["id"] = target_id
    return target_id


def align_student_profile_id_with_sql(
    db,
    sql_db: Session,
    *,
    email: str,
    user_doc: dict | None = None,
) -> int | None:
    email_norm = _normalize_email(email)
    if not email_norm:
        return None

    sql_student = sql_db.query(models.Student).filter(func.lower(models.Student.email) == email_norm).first()
    if not sql_student:
        return None

    target_id = int(sql_student.id)
    mongo_student = db["students"].find_one({"email": email_norm}) or db["students"].find_one({"id": target_id})
    if mongo_student:
        current_id = int(mongo_student.get("id") or 0)
        if current_id != target_id:
            existing_target = db["students"].find_one({"id": target_id})
            if existing_target and _normalize_email(str(existing_target.get("email", ""))) != email_norm:
                raise HTTPException(status_code=409, detail="Student profile id collision detected")
            migrate_profile_id_references(db, field_name="student_id", old_id=current_id, new_id=target_id)
            if existing_target:
                db["students"].delete_one({"id": int(current_id)})
            else:
                db["students"].update_one({"id": int(current_id)}, {"$set": {"id": int(target_id)}})
            bump_mongo_counter(db, "students", target_id)

    if user_doc is not None:
        try:
            current_user_student_id = int(user_doc.get("student_id") or 0)
        except (TypeError, ValueError):
            current_user_student_id = 0
        if current_user_student_id != target_id:
            db["auth_users"].update_one({"id": user_doc.get("id")}, {"$set": {"student_id": target_id}})
            user_doc["student_id"] = target_id
    else:
        db["auth_users"].update_many({"email": email_norm}, {"$set": {"student_id": target_id}})

    return target_id


def align_faculty_profile_id_with_sql(
    db,
    sql_db: Session,
    *,
    email: str,
    user_doc: dict | None = None,
) -> int | None:
    email_norm = _normalize_email(email)
    if not email_norm:
        return None

    sql_faculty = sql_db.query(models.Faculty).filter(func.lower(models.Faculty.email) == email_norm).first()
    if not sql_faculty:
        return None

    target_id = int(sql_faculty.id)
    mongo_faculty = db["faculty"].find_one({"email": email_norm}) or db["faculty"].find_one({"id": target_id})
    if mongo_faculty:
        current_id = int(mongo_faculty.get("id") or 0)
        if current_id != target_id:
            existing_target = db["faculty"].find_one({"id": target_id})
            if existing_target and _normalize_email(str(existing_target.get("email", ""))) != email_norm:
                raise HTTPException(status_code=409, detail="Faculty profile id collision detected")
            migrate_profile_id_references(db, field_name="faculty_id", old_id=current_id, new_id=target_id)
            if existing_target:
                db["faculty"].delete_one({"id": int(current_id)})
            else:
                db["faculty"].update_one({"id": int(current_id)}, {"$set": {"id": int(target_id)}})
            bump_mongo_counter(db, "faculty", target_id)

    if user_doc is not None:
        try:
            current_user_faculty_id = int(user_doc.get("faculty_id") or 0)
        except (TypeError, ValueError):
            current_user_faculty_id = 0
        if current_user_faculty_id != target_id:
            db["auth_users"].update_one({"id": user_doc.get("id")}, {"$set": {"faculty_id": target_id}})
            user_doc["faculty_id"] = target_id
    else:
        db["auth_users"].update_many({"email": email_norm}, {"$set": {"faculty_id": target_id}})

    return target_id
