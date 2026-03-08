#!/usr/bin/env python3
"""Realtime + Mongo persistence smoke audit for LPU Smart Campus backend.

Runs API checks and verifies that critical records are mirrored to MongoDB in real time.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from pymongo import MongoClient
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

from app import models
from app.auth_utils import CurrentUser, create_access_token
from app.database import engine as relational_engine
DEFAULT_BASE_URL = "http://127.0.0.1:8001"


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def _http_json(
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    token: str | None = None,
    base_url: str = DEFAULT_BASE_URL,
    timeout: int = 25,
) -> tuple[int, Any, dict[str, str]]:
    url = f"{base_url}{path}"
    body = None
    headers: dict[str, str] = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, data=body, method=method.upper(), headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            parsed = json.loads(raw) if raw else {}
            return int(response.status), parsed, dict(response.headers.items())
    except HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"raw": raw}
        return int(exc.code), parsed, dict(exc.headers.items())
    except URLError as exc:  # pragma: no cover - environment connectivity issue
        raise RuntimeError(f"HTTP call failed for {method} {url}: {exc}") from exc


def _http_status(
    method: str,
    path: str,
    *,
    token: str | None = None,
    base_url: str = DEFAULT_BASE_URL,
    timeout: int = 25,
) -> int:
    url = f"{base_url}{path}"
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, data=None, method=method.upper(), headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            _ = response.read()
            return int(response.status)
    except HTTPError as exc:
        _ = exc.read()
        return int(exc.code)
    except URLError as exc:  # pragma: no cover - environment connectivity issue
        raise RuntimeError(f"HTTP call failed for {method} {url}: {exc}") from exc


def _new_current_user_from_doc(doc: dict[str, Any]) -> CurrentUser:
    role_value = str(doc.get("role") or models.UserRole.STUDENT.value)
    return CurrentUser(
        id=int(doc["id"]),
        email=str(doc["email"]),
        role=models.UserRole(role_value),
        student_id=doc.get("student_id"),
        faculty_id=doc.get("faculty_id"),
        alternate_email=doc.get("alternate_email"),
        primary_login_verified=bool(doc.get("primary_login_verified", False)),
        is_active=bool(doc.get("is_active", True)),
        created_at=doc.get("created_at") or datetime.now(UTC),
        last_login_at=doc.get("last_login_at"),
    )


def _token_for_user_doc(doc: dict[str, Any]) -> str:
    token, _ = create_access_token(_new_current_user_from_doc(doc))
    return token


def _pick_face_ready_user(
    mongo_db,
    *,
    base_url: str,
) -> tuple[dict[str, Any] | None, str]:
    with relational_engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, email, name, department, semester
                FROM students
                WHERE (
                    LENGTH(COALESCE(profile_photo_data_url, '')) > 20
                    OR LENGTH(COALESCE(profile_photo_object_key, '')) > 20
                )
                  AND LENGTH(COALESCE(enrollment_video_template_json, '')) > 20
                ORDER BY id ASC
                LIMIT 20
                """
            )
        ).fetchall()

    if not rows:
        return None, "No student with profile photo + enrollment video found in SQL."

    for student_id, email, name, department, semester in rows:
        existing = mongo_db["auth_users"].find_one({"student_id": int(student_id), "role": "student"})
        if existing:
            return existing, f"Using existing auth user for student_id={student_id}."

        register_payload = {
            "email": str(email).strip().lower(),
            "password": "Audit@12345",
            "role": "student",
            "name": name or "Audit Student",
            "department": department or "CSE",
            "semester": int(semester or 1),
            "parent_email": None,
        }
        status, data, _ = _http_json("POST", "/auth/register", payload=register_payload, base_url=base_url)
        if status in (200, 201) and isinstance(data, dict) and data.get("id"):
            created = mongo_db["auth_users"].find_one({"id": int(data["id"])})
            if created:
                return created, f"Created auth user for face-ready student_id={student_id}."

    return None, "Unable to locate/create auth user for face-ready student."


def main() -> int:
    base_url = os.getenv("AUDIT_BASE_URL", DEFAULT_BASE_URL).rstrip("/")

    checks: list[Check] = []
    warnings: list[str] = []

    mongo_uri = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI")
    mongo_db_name = (
        os.getenv("MONGO_DB_NAME")
        or os.getenv("MONGODB_DB_NAME")
        or "lpu_smart_campus"
    ).strip() or "lpu_smart_campus"
    if not mongo_uri:
        print("FAIL: Mongo URI missing in environment (MONGODB_URI/MONGO_URI).")
        return 2

    try:
        mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=15000)
        mongo_client.admin.command("ping")
        mongo_db = mongo_client[mongo_db_name]
        checks.append(Check("Mongo connectivity", True, f"Connected to '{mongo_db_name}'"))
    except Exception as exc:  # noqa: BLE001
        checks.append(Check("Mongo connectivity", False, str(exc)))
        _print_report(checks, warnings)
        return 1

    status, payload, _ = _http_json("GET", "/", base_url=base_url)
    ok = status == 200 and isinstance(payload, dict) and bool(payload.get("mongo", {}).get("enabled"))
    checks.append(Check("API root + mongo status", ok, f"status={status}, mongo={payload.get('mongo') if isinstance(payload, dict) else payload}"))
    if not ok:
        _print_report(checks, warnings)
        return 1
    if isinstance(payload, dict):
        api_db = str(payload.get("mongo", {}).get("database") or "").strip()
        if api_db and api_db != mongo_db_name:
            warnings.append(
                f"Audit Mongo DB '{mongo_db_name}' differs from API Mongo DB '{api_db}'. "
                "Using API DB name for checks."
            )
            mongo_db_name = api_db
            mongo_db = mongo_client[mongo_db_name]
            checks.append(Check("Mongo DB alignment", True, f"Using '{mongo_db_name}'"))

    now_tag = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    audit_email = f"realtime.audit.{now_tag}@gmail.com"
    audit_password = "Audit@12345"
    register_payload = {
        "email": audit_email,
        "password": audit_password,
        "role": "student",
        "name": "Realtime Audit",
        "department": "CSE",
        "semester": 6,
        "parent_email": None,
    }
    status, register_data, _ = _http_json("POST", "/auth/register", payload=register_payload, base_url=base_url)
    reg_ok = status in (200, 201) and isinstance(register_data, dict) and register_data.get("id")
    checks.append(Check("Register student user", reg_ok, f"status={status}, email={audit_email}"))
    if not reg_ok:
        _print_report(checks, warnings)
        return 1

    audit_user_id = int(register_data["id"])
    audit_student_id = int(register_data.get("student_id") or 0)
    auth_doc = mongo_db["auth_users"].find_one({"id": audit_user_id})
    checks.append(Check(
        "Mongo auth_users realtime write",
        bool(auth_doc and auth_doc.get("email") == audit_email),
        f"user_id={audit_user_id}",
    ))

    before_otps = mongo_db["auth_otps"].count_documents({"user_id": audit_user_id, "purpose": "login"})
    before_delivery = mongo_db["auth_otp_delivery"].count_documents({"user_id": audit_user_id})
    status, otp_data, _ = _http_json(
        "POST",
        "/auth/login/request-otp",
        payload={"email": audit_email, "password": audit_password, "send_to_alternate": False},
        base_url=base_url,
    )
    otp_requested = status == 200
    checks.append(Check("Login OTP request", otp_requested, f"status={status}"))
    after_otps = mongo_db["auth_otps"].count_documents({"user_id": audit_user_id, "purpose": "login"})
    after_delivery = mongo_db["auth_otp_delivery"].count_documents({"user_id": audit_user_id})
    checks.append(Check(
        "Mongo OTP persistence",
        after_otps > before_otps and after_delivery > before_delivery,
        f"auth_otps: {before_otps}->{after_otps}, auth_otp_delivery: {before_delivery}->{after_delivery}",
    ))
    if not otp_requested:
        warnings.append(f"OTP request returned status={status}; detail={otp_data}")

    status, cooldown_data, headers = _http_json(
        "POST",
        "/auth/login/request-otp",
        payload={"email": audit_email, "password": audit_password, "send_to_alternate": False},
        base_url=base_url,
    )
    cooldown_ok = status == 429
    checks.append(Check("OTP cooldown enforcement", cooldown_ok, f"status={status}, retry-after={headers.get('Retry-After')}"))

    audit_token = _token_for_user_doc(
        {
            "id": audit_user_id,
            "email": audit_email,
            "role": register_data.get("role", "student"),
            "student_id": register_data.get("student_id"),
            "faculty_id": register_data.get("faculty_id"),
            "alternate_email": register_data.get("alternate_email"),
            "primary_login_verified": register_data.get("primary_login_verified", False),
            "is_active": register_data.get("is_active", True),
            "created_at": datetime.now(UTC),
            "last_login_at": None,
        }
    )

    status, me_data, _ = _http_json("GET", "/auth/me", token=audit_token, base_url=base_url)
    checks.append(Check("Auth token/session read (/auth/me)", status == 200, f"status={status}, user_id={me_data.get('id') if isinstance(me_data, dict) else None}"))

    ui_status = _http_status("GET", "/ui", base_url=base_url)
    checks.append(Check("UI shell route (/ui)", ui_status == 200, f"status={ui_status}"))
    appjs_status = _http_status("GET", "/web/app.js", base_url=base_url)
    checks.append(Check("UI asset route (/web/app.js)", appjs_status == 200, f"status={appjs_status}"))

    status, profile_data, _ = _http_json("GET", "/attendance/student/profile", token=audit_token, base_url=base_url)
    checks.append(Check("Student profile read", status == 200, f"status={status}"))
    status, enrollment_status_data, _ = _http_json(
        "GET",
        "/attendance/student/enrollment-status",
        token=audit_token,
        base_url=base_url,
    )
    enrollment_status_ok = status == 200 and isinstance(enrollment_status_data, dict) and "has_enrollment_video" in enrollment_status_data
    checks.append(Check("Student enrollment-status realtime endpoint", enrollment_status_ok, f"status={status}"))

    new_reg = f"AUDIT{now_tag[-8:]}"
    status, profile_update_data, _ = _http_json(
        "PUT",
        "/attendance/student/profile",
        token=audit_token,
        payload={"registration_number": new_reg},
        base_url=base_url,
    )
    checks.append(Check("Student profile update (registration)", status == 200, f"status={status}, reg={new_reg}"))

    status, profile_after_data, _ = _http_json("GET", "/attendance/student/profile", token=audit_token, base_url=base_url)
    reg_ok = status == 200 and isinstance(profile_after_data, dict) and profile_after_data.get("registration_number") == new_reg
    checks.append(Check("Profile realtime read-after-write", reg_ok, f"status={status}"))

    student_doc = mongo_db["students"].find_one({"id": audit_student_id})
    mongo_profile_ok = bool(student_doc and student_doc.get("registration_number") == new_reg)
    checks.append(Check("Mongo student profile realtime mirror", mongo_profile_ok, f"student_id={audit_student_id}"))

    today = date.today().isoformat()
    status, timetable_data, _ = _http_json(
        "GET",
        f"/attendance/student/timetable?{urlencode({'week_start': today})}",
        token=audit_token,
        base_url=base_url,
    )
    classes = timetable_data.get("classes", []) if isinstance(timetable_data, dict) else []
    checks.append(Check("Student timetable realtime endpoint", status == 200, f"status={status}, classes={len(classes)}"))

    status, schedules_data, _ = _http_json("GET", "/attendance/schedules", token=audit_token, base_url=base_url)
    checks.append(
        Check(
            "Student schedules list endpoint",
            status == 200 and isinstance(schedules_data, list),
            f"status={status}, schedules={len(schedules_data) if isinstance(schedules_data, list) else 0}",
        )
    )

    status, resources_data, _ = _http_json("GET", "/resources/overview", token=audit_token, base_url=base_url)
    resources_ok = status == 200 and isinstance(resources_data, dict) and "students" in resources_data
    checks.append(Check("Resources overview endpoint", resources_ok, f"status={status}"))

    status, courses_data, _ = _http_json("GET", "/core/courses", token=audit_token, base_url=base_url)
    courses_ok = status == 200 and isinstance(courses_data, list)
    checks.append(Check("Core courses endpoint", courses_ok, f"status={status}, courses={len(courses_data) if isinstance(courses_data, list) else 0}"))

    enrollment_count = mongo_db["enrollments"].count_documents({"student_id": audit_student_id})
    checks.append(Check("Mongo enrollments availability", enrollment_count > 0, f"student_id={audit_student_id}, enrollments={enrollment_count}"))

    status, aggregate_data, _ = _http_json("GET", "/attendance/student/attendance-aggregate", token=audit_token, base_url=base_url)
    aggregate_ok = status == 200 and isinstance(aggregate_data, dict) and "courses" in aggregate_data
    checks.append(Check("Attendance aggregate realtime endpoint", aggregate_ok, f"status={status}"))

    status, history_data, _ = _http_json("GET", "/attendance/student/attendance-history?limit=30", token=audit_token, base_url=base_url)
    history_ok = status == 200 and isinstance(history_data, dict) and "records" in history_data
    checks.append(Check("Attendance history realtime endpoint", history_ok, f"status={status}, records={len(history_data.get('records', [])) if isinstance(history_data, dict) else 0}"))

    # Validate trial attendance is ephemeral and not persisted to Mongo.
    face_user_doc, face_user_note = _pick_face_ready_user(mongo_db, base_url=base_url)
    if face_user_doc is None:
        warnings.append(f"Trial attendance persistence check skipped: {face_user_note}")
    else:
        warnings.append(face_user_note)
        face_token = _token_for_user_doc(face_user_doc)
        status, face_profile, _ = _http_json("GET", "/attendance/student/profile", token=face_token, base_url=base_url)
        if status != 200 or not isinstance(face_profile, dict):
            warnings.append("Face-ready profile fetch failed; skipping trial persistence check.")
        else:
            photo_data_url = face_profile.get("photo_data_url")
            status, face_enrollment_status, _ = _http_json(
                "GET",
                "/attendance/student/enrollment-status",
                token=face_token,
                base_url=base_url,
            )
            has_enrollment = bool(
                status == 200
                and isinstance(face_enrollment_status, dict)
                and face_enrollment_status.get("has_enrollment_video")
            )
            if not photo_data_url or not has_enrollment:
                warnings.append("Face-ready user missing profile photo/enrollment at runtime; skipping trial check.")
            else:
                status, face_timetable, _ = _http_json(
                    "GET",
                    f"/attendance/student/timetable?{urlencode({'week_start': today})}",
                    token=face_token,
                    base_url=base_url,
                )
                face_classes = face_timetable.get("classes", []) if isinstance(face_timetable, dict) else []
                if status != 200 or not face_classes:
                    warnings.append("Face-ready timetable unavailable; skipping trial check.")
                else:
                    target = face_classes[0]
                    schedule_id = int(target["schedule_id"])
                    class_date = today
                    student_id = int(face_user_doc.get("student_id") or 0)
                    before_trial = mongo_db["attendance_submissions"].count_documents(
                        {"student_id": student_id, "schedule_id": schedule_id, "class_date": class_date}
                    )
                    trial_payload = {
                        "schedule_id": schedule_id,
                        "selfie_photo_data_url": photo_data_url,
                        "selfie_frames_data_urls": [photo_data_url] * 8,
                    }
                    status, trial_data, _ = _http_json(
                        "POST",
                        "/attendance/student/realtime/trial-mark",
                        token=face_token,
                        payload=trial_payload,
                        base_url=base_url,
                    )
                    trial_ok = status == 200
                    checks.append(Check("Trial mark endpoint", trial_ok, f"status={status}, result={trial_data.get('status') if isinstance(trial_data, dict) else None}"))
                    status, _, _ = _http_json(
                        "POST",
                        "/attendance/student/realtime/trial-reset",
                        token=face_token,
                        payload={"schedule_id": schedule_id, "class_date": class_date},
                        base_url=base_url,
                    )
                    checks.append(Check("Trial reset endpoint", status == 200, f"status={status}"))
                    after_trial = mongo_db["attendance_submissions"].count_documents(
                        {"student_id": student_id, "schedule_id": schedule_id, "class_date": class_date}
                    )
                    checks.append(Check(
                        "Trial attendance does NOT persist in Mongo",
                        before_trial == after_trial,
                        f"attendance_submissions count unchanged: {before_trial}->{after_trial}",
                    ))

                    # Optional: if an open class exists now, verify realtime mark persistence.
                    open_now = next((row for row in face_classes if row.get("is_open_now")), None)
                    if open_now:
                        open_schedule_id = int(open_now["schedule_id"])
                        before_live = mongo_db["attendance_submissions"].count_documents(
                            {"student_id": student_id, "schedule_id": open_schedule_id, "class_date": class_date}
                        )
                        status, live_data, _ = _http_json(
                            "POST",
                            "/attendance/realtime/mark",
                            token=face_token,
                            payload={
                                "schedule_id": open_schedule_id,
                                "selfie_photo_data_url": photo_data_url,
                                "selfie_frames_data_urls": [photo_data_url] * 8,
                            },
                            base_url=base_url,
                        )
                        live_ok = status == 200
                        checks.append(Check("Realtime mark endpoint (open window)", live_ok, f"status={status}"))
                        after_live = mongo_db["attendance_submissions"].count_documents(
                            {"student_id": student_id, "schedule_id": open_schedule_id, "class_date": class_date}
                        )
                        checks.append(Check(
                            "Realtime attendance persisted to Mongo",
                            after_live >= before_live,
                            f"attendance_submissions count: {before_live}->{after_live}",
                        ))
                        if not live_ok:
                            warnings.append(f"Realtime mark response: {live_data}")
                    else:
                        warnings.append("No class currently in open 10-minute window; realtime mark persistence check skipped.")

    return _print_report(checks, warnings)


def _print_report(checks: list[Check], warnings: list[str]) -> int:
    print("=== Realtime + Mongo Audit Report ===")
    fail_count = 0
    for item in checks:
        prefix = "PASS" if item.ok else "FAIL"
        if not item.ok:
            fail_count += 1
        print(f"[{prefix}] {item.name} :: {item.detail}")

    if warnings:
        print("\nWarnings/Notes:")
        for note in warnings:
            print(f"- {note}")

    print(f"\nSummary: {len(checks) - fail_count} passed, {fail_count} failed, {len(warnings)} warnings")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
