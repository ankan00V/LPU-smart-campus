from __future__ import annotations

from copy import deepcopy
from collections import defaultdict
from datetime import date, datetime, timedelta
import json
import os
import re
from typing import Any, Iterable

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from .. import models, schemas
from ..attendance_recovery import evaluate_attendance_recovery, get_admin_recovery_plans
from ..attendance_ledger import append_event_and_recompute
from ..auth_utils import require_roles
from ..database import get_db
from ..media_storage import signed_url_for_object
from ..mongo import mirror_document, mongo_status
from ..redis_client import cache_get_json, cache_set_json
from ..realtime_bus import publish_domain_event
from ..workers import enqueue_notification, enqueue_recompute

router = APIRouter(prefix="/admin", tags=["Administrative Realtime"])

STALE_AFTER_SECONDS = max(20, min(300, int(os.getenv("ADMIN_STALE_AFTER_SECONDS", "60"))))
FACULTY_TARGET_HOURS_DEFAULT = max(6.0, float(os.getenv("FACULTY_TARGET_HOURS_PER_WEEK", "18")))
OVERLOAD_UTILIZATION_PERCENT = max(75.0, min(120.0, float(os.getenv("ADMIN_ROOM_OVERLOAD_PERCENT", "90"))))
DEPARTMENT_CLASSROOM_LAYOUT: dict[str, dict] = {
    "CSE": {
        "school": "School of Computer Science and Engineering",
        "blocks": [
            {"block": "25", "floors": 8, "rooms_per_floor": 6},
            {"block": "26", "floors": 6, "rooms_per_floor": 10},
            {"block": "27", "floors": 6, "rooms_per_floor": 10},
            {"block": "28", "floors": 6, "rooms_per_floor": 10},
            {"block": "33", "floors": 6, "rooms_per_floor": 9},
            {"block": "34", "floors": 8, "rooms_per_floor": 11},
        ],
    },
    "ECE": {
        "school": "Electronics and Communication Engineering",
        "blocks": [
            {"block": "36", "floors": 9, "rooms_per_floor": 19},
            {"block": "37", "floors": 9, "rooms_per_floor": 19},
            {"block": "38", "floors": 9, "rooms_per_floor": 19},
        ],
    },
}
DEPARTMENT_CLASSROOM_DEFAULT_CAPACITY = max(
    20,
    min(250, int(os.getenv("ADMIN_DEPARTMENT_CLASSROOM_CAPACITY", "60"))),
)
ADMIN_REFERENCE_PROFILE_ID = "lpu-campus-baseline-v1"
RMS_SECTION_PATTERN = re.compile(r"^[A-Z0-9-_/]+$")
RMS_REGISTRATION_PATTERN = re.compile(r"^[A-Z0-9/-]+$")
RMS_FACULTY_IDENTIFIER_PATTERN = re.compile(r"^[A-Z0-9/-]+$")
RMS_QUERY_CATEGORIES = [
    schemas.SupportQueryCategory.ATTENDANCE,
    schemas.SupportQueryCategory.ACADEMICS,
    schemas.SupportQueryCategory.DISCREPANCY,
    schemas.SupportQueryCategory.OTHER,
]
RMS_ACTION_MESSAGE_PREFIX = "[[RMS_ACTION]]"
RMS_ACTION_TO_STATE = {
    schemas.RMSQueryWorkflowAction.APPROVE.value: schemas.RMSQueryActionState.APPROVED,
    schemas.RMSQueryWorkflowAction.DISAPPROVE.value: schemas.RMSQueryActionState.DISAPPROVED,
    schemas.RMSQueryWorkflowAction.SCHEDULE.value: schemas.RMSQueryActionState.SCHEDULED,
}
ADMIN_GRADE_POINTS_BY_LETTER: dict[str, float] = {
    "A+": 10.0,
    "A": 9.0,
    "B+": 8.0,
    "B": 7.0,
    "C+": 6.0,
    "C": 5.0,
    "D": 4.0,
    "F": 0.0,
    "PASS": 4.0,
    "FAIL": 0.0,
    "I": 0.0,
}
RMS_CASE_FIRST_RESPONSE_HOURS = max(1.0, float(os.getenv("RMS_CASE_FIRST_RESPONSE_HOURS", "4")))
RMS_CASE_RESOLUTION_HOURS = max(2.0, float(os.getenv("RMS_CASE_RESOLUTION_HOURS", "24")))
RMS_CASE_ESCALATION_GRACE_MINUTES = max(0, int(os.getenv("RMS_CASE_ESCALATION_GRACE_MINUTES", "0")))
ADMIN_LIVE_CACHE_TTL_SECONDS = max(3, min(30, int(os.getenv("ADMIN_LIVE_CACHE_TTL_SECONDS", "8"))))
ADMIN_INSIGHTS_CACHE_TTL_SECONDS = max(5, min(60, int(os.getenv("ADMIN_INSIGHTS_CACHE_TTL_SECONDS", "15"))))
SUPER_ADMIN_EMAILS = {
    token
    for token in [
        str(item or "").strip().lower()
        for item in str(os.getenv("SUPER_ADMIN_EMAILS", "")).replace(";", ",").split(",")
    ]
    if token
}
ADMIN_REFERENCE_PROFILE: dict = {
    "institution": "Lovely Professional University",
    "active_students": {"min": 30000, "max": 35000, "estimated": 34700},
    "discipline_distribution": [
        {"discipline": "Engineering & Tech", "share_percent": 38, "students": 13000},
        {"discipline": "Management", "share_percent": 18, "students": 6200},
        {"discipline": "Computer Applications / IT", "share_percent": 12, "students": 4100},
        {"discipline": "Pharmacy", "share_percent": 8, "students": 2800},
        {"discipline": "Law", "share_percent": 6, "students": 2100},
        {"discipline": "Design / Architecture", "share_percent": 5, "students": 1700},
        {"discipline": "Agriculture", "share_percent": 5, "students": 1700},
        {"discipline": "Humanities & Social Science", "share_percent": 4, "students": 1400},
        {"discipline": "Hotel Management / Tourism", "share_percent": 2, "students": 700},
        {"discipline": "Others", "share_percent": 2, "students": 700},
    ],
    "year_distribution": [
        {"year": "1st Year", "share_percent": 32, "students": 11100},
        {"year": "2nd Year", "share_percent": 27, "students": 9400},
        {"year": "3rd Year", "share_percent": 23, "students": 8000},
        {"year": "4th Year", "share_percent": 18, "students": 6200},
    ],
    "gender_split": [
        {"category": "Male", "share_percent": 56, "students": 19500},
        {"category": "Female", "share_percent": 43, "students": 15000},
        {"category": "Others", "share_percent": 1, "students": 350},
    ],
    "residency_split": [
        {"category": "Hostel", "share_percent": 68, "students": 23800},
        {"category": "Day Scholar", "share_percent": 32, "students": 11200},
    ],
    "origin_split": [
        {"category": "Domestic", "share_percent": 85, "students": 29700},
        {"category": "International", "share_percent": 15, "students": 5200},
    ],
    "engineering_distribution": [
        {"department": "CSE", "students": 4800},
        {"department": "Mechanical", "students": 1900},
        {"department": "Civil", "students": 1300},
        {"department": "ECE", "students": 1600},
        {"department": "Electrical", "students": 1200},
        {"department": "IT", "students": 1400},
        {"department": "AI / DS", "students": 800},
    ],
    "management_distribution": [
        {"department": "MBA", "students": 2700},
        {"department": "BBA", "students": 2100},
        {"department": "Finance", "students": 600},
        {"department": "Marketing", "students": 500},
        {"department": "HR", "students": 300},
    ],
    "classroom_utilization_model": {
        "time_slots": [
            {"slot": "08:00-09:00", "utilization_percent": 45},
            {"slot": "09:00-10:00", "utilization_percent": 70},
            {"slot": "10:00-11:00", "utilization_percent": 88},
            {"slot": "11:00-12:00", "utilization_percent": 92},
            {"slot": "12:00-13:00", "utilization_percent": 75},
            {"slot": "13:00-14:00", "utilization_percent": 50},
            {"slot": "14:00-15:00", "utilization_percent": 65},
            {"slot": "15:00-16:00", "utilization_percent": 72},
            {"slot": "16:00-17:00", "utilization_percent": 40},
        ],
        "discipline_peak_usage": [
            {"discipline": "Engineering", "peak_percent": 95},
            {"discipline": "Management", "peak_percent": 80},
            {"discipline": "IT", "peak_percent": 85},
            {"discipline": "Law", "peak_percent": 70},
            {"discipline": "Pharmacy", "peak_percent": 75},
            {"discipline": "Design", "peak_percent": 60},
        ],
        "classroom_type_peak": [
            {"room_type": "Lecture Halls", "peak_percent": 93},
            {"room_type": "Labs", "peak_percent": 87},
            {"room_type": "Seminar Rooms", "peak_percent": 65},
            {"room_type": "Tutorial Rooms", "peak_percent": 78},
        ],
        "simultaneous_students_peak": 11500,
    },
    "placement_model": {
        "final_year_pool": 6200,
        "overall": {
            "placed": 4600,
            "higher_studies": 900,
            "startup_or_self": 300,
            "unplaced": 400,
            "placement_rate_percent": 74,
        },
        "discipline_rate": [
            {"discipline": "CSE / IT", "placement_percent": 88},
            {"discipline": "AI / DS", "placement_percent": 91},
            {"discipline": "Mechanical", "placement_percent": 62},
            {"discipline": "Civil", "placement_percent": 58},
            {"discipline": "MBA", "placement_percent": 79},
            {"discipline": "Law", "placement_percent": 65},
            {"discipline": "Pharmacy", "placement_percent": 72},
            {"discipline": "Design", "placement_percent": 69},
            {"discipline": "Agriculture", "placement_percent": 55},
        ],
        "salary_bands": [
            {"range": "3-5 LPA", "students": 2000},
            {"range": "5-8 LPA", "students": 1500},
            {"range": "8-12 LPA", "students": 700},
            {"range": "12-20 LPA", "students": 300},
            {"range": "20+ LPA", "students": 100},
        ],
    },
    "mobility_model": {
        "daily_shuttle_riders": 18000,
        "daily_usage_percent": 52,
        "hostel_usage_percent": 78,
        "day_scholar_usage_percent": 24,
        "peak_slots": [
            {"slot": "07:00-08:00", "riders": 3200},
            {"slot": "08:00-09:00", "riders": 4100},
            {"slot": "16:00-17:00", "riders": 2900},
            {"slot": "18:00-20:00", "riders": 3600},
        ],
    },
    "library_model": {
        "daily_usage_range": "9,000-11,000",
        "peak_slots": [
            {"slot": "14:00-15:00", "students": 2200},
            {"slot": "16:00-18:00", "students": 3100},
            {"slot": "20:00-22:00", "students": 2800},
        ],
        "exam_surge_midsem_percent": 38,
        "exam_surge_endterm_percent": 55,
        "peak_late_night_occupancy": 4200,
    },
}


def _time_overlap(a_start, a_end, b_start, b_end) -> bool:
    return (a_start < b_end) and (b_start < a_end)


def _to_classroom_label(classroom: models.Classroom) -> str:
    return f"{classroom.block}-{classroom.room_number}"


def _safe_round(value: float, places: int = 2) -> float:
    return round(float(value), places)


def _admin_cache_scope_key(current_user: models.AuthUser) -> str:
    role = current_user.role.value
    faculty_id = int(current_user.faculty_id or 0)
    return f"{role}:{faculty_id}"


def _normalize_rms_category_filter(raw_value: str | None) -> schemas.SupportQueryCategory | None:
    value = re.sub(r"\s+", " ", str(raw_value or "").strip()).lower()
    if not value or value == "all":
        return None
    if value in {"attendance", "attendance issue"}:
        return schemas.SupportQueryCategory.ATTENDANCE
    if value in {"academics", "academic", "academic issue"}:
        return schemas.SupportQueryCategory.ACADEMICS
    if value in {"discrepancy", "discrepancies"}:
        return schemas.SupportQueryCategory.DISCREPANCY
    if value in {"other", "general"}:
        return schemas.SupportQueryCategory.OTHER
    raise HTTPException(status_code=400, detail="Invalid RMS query category filter")


def _coerce_rms_category(raw_value: str | None) -> schemas.SupportQueryCategory:
    return _normalize_rms_category_filter(raw_value) or schemas.SupportQueryCategory.OTHER


def _normalize_rms_registration_number(raw_value: str) -> str:
    normalized = re.sub(r"\s+", "", str(raw_value or "").strip().upper())
    if len(normalized) < 3:
        raise HTTPException(status_code=400, detail="registration_number must be at least 3 characters")
    if len(normalized) > 40:
        raise HTTPException(status_code=400, detail="registration_number cannot exceed 40 characters")
    if not RMS_REGISTRATION_PATTERN.fullmatch(normalized):
        raise HTTPException(
            status_code=400,
            detail="registration_number can contain only letters, numbers, slash, and hyphen",
        )
    return normalized


def _normalize_rms_faculty_identifier(raw_value: str) -> str:
    normalized = re.sub(r"\s+", "", str(raw_value or "").strip().upper())
    if len(normalized) < 3:
        raise HTTPException(status_code=400, detail="faculty_identifier must be at least 3 characters")
    if len(normalized) > 40:
        raise HTTPException(status_code=400, detail="faculty_identifier cannot exceed 40 characters")
    if not RMS_FACULTY_IDENTIFIER_PATTERN.fullmatch(normalized):
        raise HTTPException(
            status_code=400,
            detail="faculty_identifier can contain only letters, numbers, slash, and hyphen",
        )
    return normalized


def _normalize_admin_search_query(raw_value: str) -> str:
    normalized = re.sub(r"\s+", " ", str(raw_value or "").strip())
    if len(normalized) < 2:
        raise HTTPException(status_code=400, detail="query must be at least 2 characters")
    if len(normalized) > 80:
        raise HTTPException(status_code=400, detail="query cannot exceed 80 characters")
    return normalized


def _normalize_admin_grade_letter(raw_value: str) -> str:
    token = re.sub(r"\s+", "", str(raw_value or "").strip().upper())
    if token not in ADMIN_GRADE_POINTS_BY_LETTER:
        allowed = ", ".join(sorted(ADMIN_GRADE_POINTS_BY_LETTER.keys()))
        raise HTTPException(status_code=400, detail=f"Unsupported grade_letter. Allowed: {allowed}")
    return token


def _normalize_admin_course_code(raw_value: str) -> str:
    token = re.sub(r"\s+", "", str(raw_value or "").strip().upper())
    if len(token) < 2 or len(token) > 20:
        raise HTTPException(status_code=400, detail="course_code must be 2 to 20 characters.")
    if not re.fullmatch(r"[A-Z0-9/_-]+", token):
        raise HTTPException(
            status_code=400,
            detail="course_code can contain only letters, numbers, slash, hyphen, and underscore.",
        )
    return token


def _submission_status_to_attendance_status(
    status_value: models.AttendanceSubmissionStatus | str | None,
) -> models.AttendanceStatus | None:
    if status_value is None:
        return None
    try:
        normalized = (
            status_value
            if isinstance(status_value, models.AttendanceSubmissionStatus)
            else models.AttendanceSubmissionStatus(str(status_value))
        )
    except ValueError:
        return None
    if normalized in (
        models.AttendanceSubmissionStatus.VERIFIED,
        models.AttendanceSubmissionStatus.APPROVED,
        models.AttendanceSubmissionStatus.PENDING_REVIEW,
    ):
        return models.AttendanceStatus.PRESENT
    if normalized == models.AttendanceSubmissionStatus.REJECTED:
        return models.AttendanceStatus.ABSENT
    return None


def _resolve_student_course_attendance_status(
    db: Session,
    *,
    student_id: int,
    course_id: int,
    attendance_date: date,
) -> models.AttendanceStatus | None:
    record = (
        db.query(models.AttendanceRecord)
        .filter(
            models.AttendanceRecord.student_id == int(student_id),
            models.AttendanceRecord.course_id == int(course_id),
            models.AttendanceRecord.attendance_date == attendance_date,
        )
        .first()
    )
    if record is not None:
        return record.status

    submission_rows = (
        db.query(models.AttendanceSubmission.status)
        .filter(
            models.AttendanceSubmission.student_id == int(student_id),
            models.AttendanceSubmission.course_id == int(course_id),
            models.AttendanceSubmission.class_date == attendance_date,
        )
        .all()
    )
    for row in submission_rows:
        status_out = _submission_status_to_attendance_status(getattr(row, "status", None))
        if status_out == models.AttendanceStatus.PRESENT:
            return status_out
    for row in submission_rows:
        status_out = _submission_status_to_attendance_status(getattr(row, "status", None))
        if status_out == models.AttendanceStatus.ABSENT:
            return status_out
    return None


def _resolve_student_schedule_attendance_status(
    db: Session,
    *,
    student_id: int,
    schedule_id: int,
    attendance_date: date,
    fallback_course_id: int | None = None,
) -> models.AttendanceStatus | None:
    submission = (
        db.query(models.AttendanceSubmission.status)
        .filter(
            models.AttendanceSubmission.student_id == int(student_id),
            models.AttendanceSubmission.schedule_id == int(schedule_id),
            models.AttendanceSubmission.class_date == attendance_date,
        )
        .first()
    )
    if submission is not None:
        status_out = _submission_status_to_attendance_status(getattr(submission, "status", None))
        if status_out is not None:
            return status_out
    if fallback_course_id is not None:
        return _resolve_student_course_attendance_status(
            db,
            student_id=int(student_id),
            course_id=int(fallback_course_id),
            attendance_date=attendance_date,
        )
    return None


def _derive_attendance_status_from_submissions(
    rows: list[models.AttendanceSubmission] | list[tuple[models.AttendanceSubmissionStatus]] | list[Any],
) -> models.AttendanceStatus | None:
    resolved: list[models.AttendanceStatus] = []
    for row in rows:
        status_value = getattr(row, "status", None)
        if status_value is None and isinstance(row, tuple) and row:
            status_value = row[0]
        resolved_status = _submission_status_to_attendance_status(status_value)
        if resolved_status is not None:
            resolved.append(resolved_status)
    if any(item == models.AttendanceStatus.PRESENT for item in resolved):
        return models.AttendanceStatus.PRESENT
    if any(item == models.AttendanceStatus.ABSENT for item in resolved):
        return models.AttendanceStatus.ABSENT
    return None


def _attendance_status_label(status_value: models.AttendanceStatus | None) -> str:
    if status_value == models.AttendanceStatus.PRESENT:
        return "Present"
    if status_value == models.AttendanceStatus.ABSENT:
        return "Absent"
    return "Not marked"


def _admin_student_search_out(student: models.Student) -> schemas.AdminStudentSearchOut:
    return schemas.AdminStudentSearchOut(
        student_id=int(student.id),
        name=str(student.name or f"Student #{student.id}"),
        email=str(student.email or ""),
        registration_number=(str(student.registration_number or "").strip().upper() or None),
        section=(re.sub(r"\s+", "", str(student.section or "").strip().upper()) or None),
        department=str(student.department or ""),
        semester=int(student.semester or 0),
        parent_email=(str(student.parent_email or "").strip() or None),
    )


def _admin_faculty_search_out(faculty: models.Faculty) -> schemas.AdminFacultySearchOut:
    return schemas.AdminFacultySearchOut(
        faculty_id=int(faculty.id),
        name=str(faculty.name or f"Faculty #{faculty.id}"),
        email=str(faculty.email or ""),
        faculty_identifier=(str(faculty.faculty_identifier or "").strip().upper() or None),
        section=(re.sub(r"\s+", "", str(faculty.section or "").strip().upper()) or None),
        department=str(faculty.department or ""),
    )


def _admin_course_search_out(
    course: models.Course,
    *,
    faculty_map: dict[int, models.Faculty] | None = None,
) -> schemas.AdminCourseSearchOut:
    instructor = (faculty_map or {}).get(int(course.faculty_id))
    return schemas.AdminCourseSearchOut(
        course_id=int(course.id),
        course_code=str(course.code or "").strip().upper(),
        course_title=str(course.title or ""),
        faculty_id=int(course.faculty_id),
        faculty_name=(str(instructor.name or "").strip() or None) if instructor else None,
    )


def _admin_student_grade_out(
    grade: models.StudentGrade,
    *,
    student: models.Student | None = None,
    course: models.Course | None = None,
    faculty: models.Faculty | None = None,
) -> schemas.AdminStudentGradeOut:
    return schemas.AdminStudentGradeOut(
        grade_id=int(grade.id),
        student_id=int(grade.student_id),
        student_name=str(getattr(student, "name", "") or f"Student #{grade.student_id}"),
        registration_number=(str(getattr(student, "registration_number", "") or "").strip().upper() or None),
        course_id=int(grade.course_id),
        course_code=str(getattr(course, "code", "") or f"C-{grade.course_id}").strip().upper(),
        course_title=str(getattr(course, "title", "") or "Unknown Course"),
        faculty_id=int(grade.faculty_id) if grade.faculty_id else None,
        faculty_name=(str(getattr(faculty, "name", "") or "").strip() or None),
        grade_letter=str(grade.grade_letter or "").strip().upper(),
        grade_points=float(grade.grade_points) if grade.grade_points is not None else None,
        marks_percent=float(grade.marks_percent) if grade.marks_percent is not None else None,
        remark=(str(grade.remark or "").strip() or None),
        graded_by_user_id=int(grade.graded_by_user_id) if grade.graded_by_user_id else None,
        graded_at=grade.graded_at or datetime.utcnow(),
        updated_at=grade.updated_at or grade.graded_at or datetime.utcnow(),
    )


def _normalize_rms_section(raw_value: str) -> str:
    token = re.sub(r"\s+", "", str(raw_value or "").strip().upper())
    if not token:
        raise HTTPException(status_code=400, detail="section cannot be empty")
    if len(token) > 80 or not RMS_SECTION_PATTERN.fullmatch(token):
        raise HTTPException(
            status_code=400,
            detail="section can contain only letters, numbers, slash, hyphen, and underscore",
        )
    return token


def _normalize_rms_action_note(raw_value: str | None) -> str | None:
    token = re.sub(r"\s+", " ", str(raw_value or "").strip())
    return token[:400] if token else None


def _coerce_rms_marker_datetime(raw_value: str | None) -> datetime | None:
    raw = str(raw_value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = f"{raw[:-1]}+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _encode_rms_action_marker(
    *,
    action: schemas.RMSQueryWorkflowAction,
    actor_role: models.UserRole,
    note: str | None,
    scheduled_for: datetime | None,
) -> str:
    payload: dict[str, str] = {
        "action": action.value,
        "actor_role": actor_role.value,
    }
    if note:
        payload["note"] = note
    if scheduled_for is not None:
        payload["scheduled_for"] = scheduled_for.isoformat()
    return f"{RMS_ACTION_MESSAGE_PREFIX}{json.dumps(payload, separators=(',', ':'), ensure_ascii=True)}"


def _parse_rms_action_marker(raw_message: str | None) -> dict | None:
    message = str(raw_message or "").strip()
    if not message.startswith(RMS_ACTION_MESSAGE_PREFIX):
        return None
    encoded_payload = message[len(RMS_ACTION_MESSAGE_PREFIX):].strip()
    if not encoded_payload:
        return None
    try:
        payload = json.loads(encoded_payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None

    action = str(payload.get("action", "")).strip().lower()
    if action not in RMS_ACTION_TO_STATE:
        return None

    actor_role = str(payload.get("actor_role", "")).strip().lower() or None
    note = _normalize_rms_action_note(str(payload.get("note", "") or ""))
    scheduled_for = _coerce_rms_marker_datetime(str(payload.get("scheduled_for", "") or ""))
    return {
        "action": action,
        "actor_role": actor_role,
        "note": note,
        "scheduled_for": scheduled_for,
    }


def _rms_action_summary_text(
    *,
    action: str,
    note: str | None = None,
    scheduled_for: datetime | None = None,
) -> str:
    if action == schemas.RMSQueryWorkflowAction.APPROVE.value:
        base = "RMS action: approved."
    elif action == schemas.RMSQueryWorkflowAction.DISAPPROVE.value:
        base = "RMS action: disapproved."
    else:
        schedule_label = scheduled_for.isoformat(sep=" ", timespec="minutes") if scheduled_for else "TBD"
        base = f"RMS action: scheduled for {schedule_label}."

    if note:
        return f"{base} Note: {note}"
    return base


def _faculty_allowed_sections(faculty: models.Faculty | None) -> set[str]:
    if not faculty or not faculty.section:
        return set()
    tokens = re.split(r"[,\s]+", str(faculty.section).strip().upper())
    return {token for token in tokens if token}


def _faculty_can_manage_student_rms(
    db: Session,
    *,
    faculty_id: int,
    student: models.Student | None,
) -> bool:
    if not student:
        return False
    faculty = db.get(models.Faculty, int(faculty_id))
    allowed_sections = _faculty_allowed_sections(faculty)
    student_section = re.sub(r"\s+", "", str(student.section or "").strip().upper())
    if allowed_sections:
        return bool(student_section and student_section in allowed_sections)
    teaches_student = (
        db.query(models.Enrollment.id)
        .join(models.Course, models.Course.id == models.Enrollment.course_id)
        .filter(
            models.Enrollment.student_id == int(student.id),
            models.Course.faculty_id == int(faculty_id),
        )
        .first()
        is not None
    )
    return teaches_student


def _rms_student_lookup_out(
    db: Session,
    *,
    student: models.Student,
    faculty_scope_id: int | None = None,
) -> schemas.RMSStudentLookupOut:
    base_query = db.query(models.SupportQueryMessage).filter(
        models.SupportQueryMessage.student_id == int(student.id)
    )
    if faculty_scope_id is not None:
        base_query = base_query.filter(models.SupportQueryMessage.faculty_id == int(faculty_scope_id))

    recent_query_count = int(base_query.count())
    pending_query_count = int(
        base_query.filter(
            models.SupportQueryMessage.sender_role == models.UserRole.STUDENT.value,
            models.SupportQueryMessage.read_at.is_(None),
        ).count()
    )
    max_created_query = db.query(func.max(models.SupportQueryMessage.created_at)).filter(
        models.SupportQueryMessage.student_id == int(student.id)
    )
    if faculty_scope_id is not None:
        max_created_query = max_created_query.filter(models.SupportQueryMessage.faculty_id == int(faculty_scope_id))
    last_query_at = max_created_query.scalar()

    return schemas.RMSStudentLookupOut(
        student_id=int(student.id),
        name=str(student.name or f"Student #{student.id}"),
        email=str(student.email or ""),
        registration_number=(str(student.registration_number or "").strip().upper() or None),
        section=(re.sub(r"\s+", "", str(student.section or "").strip().upper()) or None),
        department=str(student.department or ""),
        semester=int(student.semester or 0),
        parent_email=(str(student.parent_email or "").strip() or None),
        recent_query_count=recent_query_count,
        pending_query_count=pending_query_count,
        last_query_at=last_query_at,
    )


def _room_number_from_floor(floor_index: int, serial_index: int) -> str:
    return f"{int(floor_index)}{int(serial_index):02d}"


def _build_admin_insights(
    *,
    summary: schemas.AdminSummaryOut,
    capacity_rows: list[schemas.AdminCapacityItem],
    workload_rows: list[schemas.AdminWorkloadItem],
) -> schemas.AdminInsightsOut:
    now_dt = datetime.utcnow()
    profile = deepcopy(ADMIN_REFERENCE_PROFILE)
    model_total = int(profile.get("active_students", {}).get("estimated", 0) or 0)
    live_students = max(0, int(summary.students or 0))
    live_capacity = _safe_round(summary.capacity_utilization_percent)
    live_attendance = _safe_round(summary.attendance_rate_today)
    live_workload = _safe_round(summary.workload_distribution_percent)

    utilization_slots = profile.get("classroom_utilization_model", {}).get("time_slots", [])
    peak_slot = max(
        utilization_slots,
        key=lambda item: float(item.get("utilization_percent", 0)),
        default={"slot": "--", "utilization_percent": 0},
    )
    placement_rate = float(
        profile.get("placement_model", {}).get("overall", {}).get("placement_rate_percent", 0)
    )
    overloaded_faculty = sum(1 for row in workload_rows if str(row.status) == "overloaded")
    underloaded_faculty = sum(1 for row in workload_rows if str(row.status) == "underloaded")
    top_rooms = [
        {
            "classroom": row.classroom_label,
            "course": row.primary_course_code,
            "utilization_percent": _safe_round(row.utilization_percent),
            "occupied": int(row.occupied_students),
            "capacity": int(row.total_available_seats),
        }
        for row in sorted(capacity_rows, key=lambda item: item.utilization_percent, reverse=True)[:5]
    ]

    profile["live_comparison"] = {
        "students_recorded_now": live_students,
        "student_model_estimate": model_total,
        "capacity_utilization_now_percent": live_capacity,
        "attendance_rate_now_percent": live_attendance,
        "workload_distribution_now_percent": live_workload,
        "capacity_peak_benchmark_percent": float(peak_slot.get("utilization_percent", 0) or 0),
        "capacity_gap_to_peak_percent": _safe_round(
            live_capacity - float(peak_slot.get("utilization_percent", 0) or 0)
        ),
        "placement_rate_benchmark_percent": _safe_round(placement_rate),
        "attendance_target_percent": 85.0,
        "workload_target_percent": 85.0,
        "overloaded_faculty_count": int(overloaded_faculty),
        "underloaded_faculty_count": int(underloaded_faculty),
        "top_loaded_rooms": top_rooms,
        "work_date": summary.last_updated_at.date().isoformat(),
    }

    profile["model_metadata"] = {
        "profile_id": ADMIN_REFERENCE_PROFILE_ID,
        "generated_at": now_dt.isoformat(),
        "source": "provided-planning-dataset",
        "notes": "Baseline planning model for administrative decisions. Live telemetry overlays these baselines.",
    }

    highlights = [
        (
            f"Live student records: {live_students:,} vs model baseline {model_total:,} "
            f"({_safe_round((live_students / model_total * 100.0) if model_total else 0)}% coverage)."
        ),
        (
            f"Current classroom utilization is {live_capacity}% against peak model "
            f"{peak_slot.get('utilization_percent', 0)}% ({peak_slot.get('slot')})."
        ),
        (
            f"Attendance rate today is {live_attendance}% with {summary.present_today} present "
            f"and {summary.absent_today} absent."
        ),
        (
            f"Workload distribution is {live_workload}%; overloaded faculty={overloaded_faculty}, "
            f"underloaded faculty={underloaded_faculty}."
        ),
        (
            f"Placement benchmark remains {int(placement_rate)}% for a final-year pool of "
            f"{int(profile.get('placement_model', {}).get('final_year_pool', 0)):,}."
        ),
    ]

    mirror_document(
        "admin_reference_profiles",
        {
            "profile_id": ADMIN_REFERENCE_PROFILE_ID,
            "profile": profile,
            "highlights": highlights,
            "last_updated_at": now_dt,
            "source": "admin-insights",
        },
        required=False,
    )
    return schemas.AdminInsightsOut(
        profile=profile,
        highlights=highlights,
        last_updated_at=now_dt,
    )


def _compute_capacity_rows(
    db: Session,
    *,
    work_date: date,
    mode: str = "enrollment",
) -> list[schemas.AdminCapacityItem]:
    schedules = (
        db.query(models.ClassSchedule)
        .filter(models.ClassSchedule.is_active.is_(True))
        .all()
    )
    if not schedules:
        return []

    course_ids = sorted({int(s.course_id) for s in schedules})
    enroll_counts = {
        int(course_id): int(count)
        for course_id, count in (
            db.query(models.Enrollment.course_id, func.count(models.Enrollment.id))
            .filter(models.Enrollment.course_id.in_(course_ids))
            .group_by(models.Enrollment.course_id)
            .all()
        )
    }
    attendance_counts = {
        int(course_id): int(count)
        for course_id, count in (
            db.query(models.AttendanceRecord.course_id, func.count(models.AttendanceRecord.id))
            .filter(
                models.AttendanceRecord.course_id.in_(course_ids),
                models.AttendanceRecord.attendance_date == work_date,
                models.AttendanceRecord.status == models.AttendanceStatus.PRESENT,
            )
            .group_by(models.AttendanceRecord.course_id)
            .all()
        )
    }
    courses_by_id = {
        row.id: row
        for row in db.query(models.Course).filter(models.Course.id.in_(course_ids)).all()
    }
    assignments = (
        db.query(models.CourseClassroom)
        .filter(models.CourseClassroom.course_id.in_(course_ids))
        .all()
    )
    room_by_course = {int(a.course_id): int(a.classroom_id) for a in assignments}
    room_ids = sorted({int(a.classroom_id) for a in assignments})
    classrooms_by_id = {
        row.id: row
        for row in db.query(models.Classroom).filter(models.Classroom.id.in_(room_ids)).all()
    }

    now_dt = datetime.utcnow()
    agg: dict[int, dict] = {}
    for schedule in schedules:
        room_id = room_by_course.get(int(schedule.course_id))
        if not room_id:
            continue
        classroom = classrooms_by_id.get(room_id)
        if not classroom or classroom.capacity <= 0:
            continue
        course = courses_by_id.get(int(schedule.course_id))
        if not course:
            continue
        row = agg.setdefault(
            int(room_id),
            {
                "classroom_id": int(room_id),
                "block": classroom.block,
                "classroom": _to_classroom_label(classroom),
                "primary_course_code": course.code,
                "scheduled_slots": 0,
                "occupied_students": 0,
                "attendance_marked_students": 0,
                "total_available_seats": 0,
                "capacity": int(classroom.capacity),
            },
        )
        enrolled = int(enroll_counts.get(int(schedule.course_id), 0))
        marked = int(attendance_counts.get(int(schedule.course_id), 0))
        occupied = marked if mode == "attendance_marked" else enrolled
        row["scheduled_slots"] += 1
        row["occupied_students"] += max(0, occupied)
        row["attendance_marked_students"] += max(0, marked)
        row["total_available_seats"] += int(classroom.capacity)

    rows: list[schemas.AdminCapacityItem] = []
    for row in agg.values():
        available = max(0, int(row["total_available_seats"]))
        occupied = max(0, int(row["occupied_students"]))
        utilization = (occupied / available * 100.0) if available else 0.0
        rows.append(
            schemas.AdminCapacityItem(
                classroom_id=int(row["classroom_id"]),
                block=str(row["block"]),
                classroom=str(row["classroom"]),
                classroom_label=str(row["classroom"]),
                primary_course_code=str(row["primary_course_code"]),
                scheduled_slots=int(row["scheduled_slots"]),
                occupied_students=occupied,
                attendance_marked_students=max(0, int(row["attendance_marked_students"])),
                total_available_seats=available,
                capacity=max(0, int(row["capacity"])),
                utilization_percent=_safe_round(utilization),
                mode=mode,
                last_updated_at=now_dt,
            )
        )
    rows.sort(key=lambda item: item.utilization_percent, reverse=True)
    return rows


def _compute_workload_rows(db: Session) -> list[schemas.AdminWorkloadItem]:
    faculty_rows = db.query(models.Faculty).all()
    if not faculty_rows:
        return []
    faculty_ids = [int(f.id) for f in faculty_rows]

    schedules = (
        db.query(models.ClassSchedule)
        .filter(
            models.ClassSchedule.is_active.is_(True),
            models.ClassSchedule.faculty_id.in_(faculty_ids),
        )
        .all()
    )
    by_faculty_schedules: dict[int, list[models.ClassSchedule]] = defaultdict(list)
    for schedule in schedules:
        by_faculty_schedules[int(schedule.faculty_id)].append(schedule)

    faculty_courses = (
        db.query(models.Course.id, models.Course.faculty_id)
        .filter(models.Course.faculty_id.in_(faculty_ids))
        .all()
    )
    by_faculty_course_ids: dict[int, set[int]] = defaultdict(set)
    all_course_ids: set[int] = set()
    for course_id, faculty_id in faculty_courses:
        by_faculty_course_ids[int(faculty_id)].add(int(course_id))
        all_course_ids.add(int(course_id))

    enroll_counts = {
        int(course_id): int(count)
        for course_id, count in (
            db.query(models.Enrollment.course_id, func.count(models.Enrollment.id))
            .filter(models.Enrollment.course_id.in_(all_course_ids or [0]))
            .group_by(models.Enrollment.course_id)
            .all()
        )
    }

    now_dt = datetime.utcnow()
    results: list[schemas.AdminWorkloadItem] = []
    for faculty in faculty_rows:
        schedule_list = by_faculty_schedules.get(int(faculty.id), [])
        assigned_hours = 0.0
        for schedule in schedule_list:
            start_minutes = int(schedule.start_time.hour) * 60 + int(schedule.start_time.minute)
            end_minutes = int(schedule.end_time.hour) * 60 + int(schedule.end_time.minute)
            assigned_hours += max(0, (end_minutes - start_minutes) / 60.0)
        target_hours = FACULTY_TARGET_HOURS_DEFAULT
        workload_percent = (assigned_hours / target_hours * 100.0) if target_hours > 0 else 0.0
        course_ids = by_faculty_course_ids.get(int(faculty.id), set())
        total_enrolled = sum(enroll_counts.get(course_id, 0) for course_id in course_ids)
        status = "balanced"
        if workload_percent > 100:
            status = "overloaded"
        elif workload_percent < 60:
            status = "underloaded"
        results.append(
            schemas.AdminWorkloadItem(
                faculty_id=int(faculty.id),
                faculty_name=str(faculty.name),
                department=str(faculty.department),
                assigned_courses=len(course_ids),
                assigned_hours=_safe_round(assigned_hours),
                target_hours=_safe_round(target_hours),
                workload_percent=_safe_round(workload_percent),
                total_enrolled_students=int(total_enrolled),
                status=status,
                last_updated_at=now_dt,
            )
        )
    results.sort(key=lambda item: item.workload_percent, reverse=True)
    return results


def _detect_timetable_conflicts(db: Session) -> list[dict]:
    schedules = (
        db.query(models.ClassSchedule)
        .filter(models.ClassSchedule.is_active.is_(True))
        .order_by(models.ClassSchedule.weekday.asc(), models.ClassSchedule.start_time.asc())
        .all()
    )
    if not schedules:
        return []
    course_rows = db.query(models.Course.id, models.Course.code).all()
    course_code_by_id = {int(c_id): str(code) for c_id, code in course_rows}
    assignments = db.query(models.CourseClassroom).all()
    room_by_course = {int(row.course_id): int(row.classroom_id) for row in assignments}
    classrooms = db.query(models.Classroom).all()
    room_label_by_id = {int(row.id): _to_classroom_label(row) for row in classrooms}

    conflicts: list[dict] = []
    by_weekday: dict[int, list[models.ClassSchedule]] = defaultdict(list)
    for schedule in schedules:
        by_weekday[int(schedule.weekday)].append(schedule)

    for weekday, day_rows in by_weekday.items():
        count = len(day_rows)
        for idx in range(count):
            left = day_rows[idx]
            for jdx in range(idx + 1, count):
                right = day_rows[jdx]
                if not _time_overlap(left.start_time, left.end_time, right.start_time, right.end_time):
                    if right.start_time >= left.end_time:
                        break
                    continue

                left_course = int(left.course_id)
                right_course = int(right.course_id)
                same_faculty = int(left.faculty_id) == int(right.faculty_id)
                same_room = (
                    room_by_course.get(left_course) is not None
                    and room_by_course.get(left_course) == room_by_course.get(right_course)
                )
                if not same_faculty and not same_room:
                    continue
                conflict_type = "faculty_time_overlap" if same_faculty else "classroom_time_overlap"
                room_id = room_by_course.get(left_course) if same_room else None
                conflicts.append(
                    {
                        "issue_type": conflict_type,
                        "severity": "high",
                        "weekday": int(weekday),
                        "schedule_a_id": int(left.id),
                        "schedule_b_id": int(right.id),
                        "faculty_id": int(left.faculty_id) if same_faculty else None,
                        "room_id": int(room_id) if room_id else None,
                        "room_label": room_label_by_id.get(int(room_id)) if room_id else None,
                        "window": f"{left.start_time.strftime('%H:%M')}-{left.end_time.strftime('%H:%M')}",
                        "course_a": course_code_by_id.get(left_course, f"#{left_course}"),
                        "course_b": course_code_by_id.get(right_course, f"#{right_course}"),
                    }
                )
    return conflicts


def _build_alerts(
    *,
    capacity_rows: Iterable[schemas.AdminCapacityItem],
    workload_rows: Iterable[schemas.AdminWorkloadItem],
    conflicts: Iterable[dict],
    now_dt: datetime,
) -> list[schemas.AdminAlertItem]:
    alerts: list[schemas.AdminAlertItem] = []
    for row in capacity_rows:
        if row.utilization_percent > OVERLOAD_UTILIZATION_PERCENT:
            alerts.append(
                schemas.AdminAlertItem(
                    id=f"room-overload-{row.classroom_id}",
                    issue_type="room_overload",
                    severity="high",
                    message=f"{row.classroom} at {row.utilization_percent:.1f}% utilization",
                    context={
                        "block": row.block,
                        "scheduled_slots": row.scheduled_slots,
                        "occupied_students": row.occupied_students,
                        "capacity": row.total_available_seats,
                    },
                    last_updated_at=now_dt,
                )
            )
    for row in workload_rows:
        if row.workload_percent > 100:
            alerts.append(
                schemas.AdminAlertItem(
                    id=f"faculty-overload-{row.faculty_id}",
                    issue_type="faculty_overload",
                    severity="high",
                    message=f"{row.faculty_name} at {row.workload_percent:.1f}% workload",
                    context={
                        "department": row.department,
                        "assigned_hours": row.assigned_hours,
                        "target_hours": row.target_hours,
                        "assigned_courses": row.assigned_courses,
                    },
                    last_updated_at=now_dt,
                )
            )
    for idx, conflict in enumerate(conflicts):
        alerts.append(
            schemas.AdminAlertItem(
                id=f"timetable-conflict-{idx + 1}",
                issue_type=str(conflict.get("issue_type") or "timetable_conflict"),
                severity=str(conflict.get("severity") or "high"),
                message=(
                    f"{conflict.get('course_a', 'N/A')} vs {conflict.get('course_b', 'N/A')} "
                    f"on weekday {int(conflict.get('weekday', 0))} ({conflict.get('window', '--')})"
                ),
                context=conflict,
                last_updated_at=now_dt,
            )
        )
    alerts.sort(key=lambda row: (row.severity != "high", row.issue_type, row.id))
    return alerts[:20]


def _build_recovery_alerts(
    db: Session,
    *,
    plans: Iterable[models.AttendanceRecoveryPlan],
    now_dt: datetime,
) -> list[schemas.AdminAlertItem]:
    plan_rows = list(plans)
    if not plan_rows:
        return []

    student_ids = {int(plan.student_id) for plan in plan_rows}
    course_ids = {int(plan.course_id) for plan in plan_rows}
    students = {
        int(row.id): row
        for row in db.query(models.Student).filter(models.Student.id.in_(student_ids)).all()
    }
    courses = {
        int(row.id): row
        for row in db.query(models.Course).filter(models.Course.id.in_(course_ids)).all()
    }

    severity_rank = {
        models.AttendanceRecoveryRiskLevel.CRITICAL: 0,
        models.AttendanceRecoveryRiskLevel.HIGH: 1,
        models.AttendanceRecoveryRiskLevel.WATCH: 2,
    }
    out: list[schemas.AdminAlertItem] = []
    for plan in sorted(
        plan_rows,
        key=lambda row: (
            severity_rank.get(row.risk_level, 3),
            row.recovery_due_at or datetime.max,
            row.attendance_percent or 0.0,
        ),
    ):
        if plan.risk_level == models.AttendanceRecoveryRiskLevel.WATCH:
            continue
        student = students.get(int(plan.student_id))
        course = courses.get(int(plan.course_id))
        severity = "critical" if plan.risk_level == models.AttendanceRecoveryRiskLevel.CRITICAL else "high"
        out.append(
            schemas.AdminAlertItem(
                id=f"attendance-recovery-{int(plan.id)}",
                issue_type="attendance_recovery",
                severity=severity,
                message=(
                    f"{student.name if student else f'Student {plan.student_id}'} | "
                    f"{course.code if course else f'C-{plan.course_id}'} at "
                    f"{float(plan.attendance_percent or 0.0):.1f}% attendance"
                ),
                context={
                    "plan_id": int(plan.id),
                    "student_id": int(plan.student_id),
                    "student_name": student.name if student else None,
                    "registration_number": student.registration_number if student else None,
                    "course_id": int(plan.course_id),
                    "course_code": course.code if course else None,
                    "risk_level": plan.risk_level.value,
                    "consecutive_absences": int(plan.consecutive_absences or 0),
                    "missed_remedials": int(plan.missed_remedials or 0),
                    "recovery_due_at": plan.recovery_due_at.isoformat() if plan.recovery_due_at else None,
                },
                last_updated_at=now_dt,
            )
        )
    return out[:10]


def _sync_admin_mongo(
    db: Session,
    *,
    now_dt: datetime,
    work_date: date,
    summary: schemas.AdminSummaryOut,
    capacity_rows: list[schemas.AdminCapacityItem],
    workload_rows: list[schemas.AdminWorkloadItem],
    alerts: list[schemas.AdminAlertItem],
) -> None:
    for block, classroom_count, total_capacity in (
        db.query(
            models.Classroom.block,
            func.count(models.Classroom.id),
            func.coalesce(func.sum(models.Classroom.capacity), 0),
        )
        .group_by(models.Classroom.block)
        .all()
    ):
        mirror_document(
            "blocks",
            {
                "block": str(block),
                "classroom_count": int(classroom_count or 0),
                "total_capacity": int(total_capacity or 0),
                "updated_at": now_dt,
                "source": "admin-live-sync",
            },
            upsert_filter={"block": str(block)},
            required=False,
        )

    schedules = (
        db.query(models.ClassSchedule)
        .filter(models.ClassSchedule.is_active.is_(True))
        .all()
    )
    assignments = db.query(models.CourseClassroom).all()
    room_by_course = {int(row.course_id): int(row.classroom_id) for row in assignments}
    room_rows = db.query(models.Classroom).all()
    room_label_by_id = {int(row.id): _to_classroom_label(row) for row in room_rows}
    for schedule in schedules:
        room_id = room_by_course.get(int(schedule.course_id))
        mirror_document(
            "timetable",
            {
                "schedule_id": int(schedule.id),
                "course_id": int(schedule.course_id),
                "faculty_id": int(schedule.faculty_id),
                "classroom_id": int(room_id) if room_id else None,
                "classroom_label": room_label_by_id.get(int(room_id)) if room_id else schedule.classroom_label,
                "weekday": int(schedule.weekday),
                "start_time": str(schedule.start_time),
                "end_time": str(schedule.end_time),
                "is_active": bool(schedule.is_active),
                "updated_at": now_dt,
                "source": "admin-live-sync",
            },
            upsert_filter={"schedule_id": int(schedule.id)},
            required=False,
        )

    mirror_document(
        "admin_summary_snapshots",
        {
            "work_date": work_date.isoformat(),
            "summary": summary.model_dump(),
            "capacity": [row.model_dump() for row in capacity_rows],
            "workload": [row.model_dump() for row in workload_rows],
            "alerts": [row.model_dump() for row in alerts],
            "created_at": now_dt,
            "source": "admin-live-sync",
        },
        required=False,
    )

    for alert in alerts:
        mirror_document(
            "admin_alerts",
            {
                **alert.model_dump(),
                "updated_at": now_dt,
                "work_date": work_date.isoformat(),
            },
            upsert_filter={"id": alert.id},
            required=False,
        )


def _build_admin_payload(db: Session, *, work_date: date, mode: str) -> tuple[
    schemas.AdminSummaryOut,
    list[schemas.AdminCapacityItem],
    list[schemas.AdminWorkloadItem],
    list[schemas.AdminAlertItem],
]:
    now_dt = datetime.utcnow()
    blocks_count = db.query(func.count(func.distinct(models.Classroom.block))).scalar() or 0
    classrooms_count = db.query(models.Classroom).count()
    courses_count = db.query(models.Course).count()
    faculty_count = db.query(models.Faculty).count()
    students_count = db.query(models.Student).count()

    work_weekday = int(work_date.weekday())
    active_course_ids = [
        int(row.course_id)
        for row in (
            db.query(models.ClassSchedule.course_id)
            .filter(
                models.ClassSchedule.is_active.is_(True),
                models.ClassSchedule.weekday == work_weekday,
            )
            .distinct()
            .all()
        )
    ]
    active_today = 0
    if active_course_ids:
        active_today = int(
            db.query(func.count(func.distinct(models.Enrollment.student_id)))
            .filter(models.Enrollment.course_id.in_(active_course_ids))
            .scalar()
            or 0
        )

    present_today = int(
        db.query(func.count(func.distinct(models.AttendanceRecord.student_id)))
        .filter(
            models.AttendanceRecord.attendance_date == work_date,
            models.AttendanceRecord.status == models.AttendanceStatus.PRESENT,
        )
        .scalar()
        or 0
    )
    absent_today_records = int(
        db.query(func.count(func.distinct(models.AttendanceRecord.student_id)))
        .filter(
            models.AttendanceRecord.attendance_date == work_date,
            models.AttendanceRecord.status == models.AttendanceStatus.ABSENT,
        )
        .scalar()
        or 0
    )
    absent_today = max(absent_today_records, max(0, active_today - present_today))
    attendance_denominator = active_today if active_today > 0 else (present_today + absent_today)
    attendance_rate_today = (
        _safe_round((present_today / attendance_denominator) * 100.0)
        if attendance_denominator > 0
        else 0.0
    )

    per_student_stats = (
        db.query(
            models.AttendanceRecord.student_id,
            func.count(models.AttendanceRecord.id).label("marked"),
            func.sum(
                case(
                    (models.AttendanceRecord.status == models.AttendanceStatus.PRESENT, 1),
                    else_=0,
                )
            ).label("present"),
        )
        .group_by(models.AttendanceRecord.student_id)
        .all()
    )
    at_risk_students = 0
    for student_id, marked, present in per_student_stats:
        marked_count = int(marked or 0)
        present_count = int(present or 0)
        if marked_count < 4:
            continue
        percent = (present_count / marked_count * 100.0) if marked_count else 0.0
        if percent < 75.0:
            at_risk_students += 1

    recovery_plans = get_admin_recovery_plans(db, include_resolved=False, limit=250)
    if recovery_plans:
        at_risk_students = max(
            at_risk_students,
            len({int(plan.student_id) for plan in recovery_plans}),
        )

    capacity_rows = _compute_capacity_rows(db, work_date=work_date, mode=mode)
    workload_rows = _compute_workload_rows(db)
    conflicts = _detect_timetable_conflicts(db)
    alerts = _build_alerts(
        capacity_rows=capacity_rows,
        workload_rows=workload_rows,
        conflicts=conflicts,
        now_dt=now_dt,
    )
    alerts.extend(_build_recovery_alerts(db, plans=recovery_plans, now_dt=now_dt))
    alerts.sort(key=lambda row: (row.severity not in {"critical", "high"}, row.issue_type, row.id))
    alerts = alerts[:20]

    avg_capacity_util = (
        _safe_round(sum(row.utilization_percent for row in capacity_rows) / len(capacity_rows))
        if capacity_rows
        else 0.0
    )
    avg_workload = (
        _safe_round(sum(row.workload_percent for row in workload_rows) / len(workload_rows))
        if workload_rows
        else 0.0
    )

    data_quality_score = 100.0
    if not capacity_rows:
        data_quality_score -= 18.0
    if not workload_rows:
        data_quality_score -= 18.0
    if not active_today:
        data_quality_score -= 10.0
    if conflicts:
        data_quality_score -= min(30.0, len(conflicts) * 4.0)
    data_quality_score = _safe_round(max(0.0, min(100.0, data_quality_score)))

    top_issues = [
        schemas.AdminTopIssueItem(
            issue_type=alert.issue_type,
            severity=alert.severity,
            message=alert.message,
            context=alert.context,
        )
        for alert in alerts[:8]
    ]

    summary = schemas.AdminSummaryOut(
        blocks=int(blocks_count),
        classrooms=int(classrooms_count),
        courses=int(courses_count),
        faculty=int(faculty_count),
        students=int(students_count),
        active_today=int(active_today),
        present_today=int(present_today),
        absent_today=int(absent_today),
        attendance_rate_today=float(attendance_rate_today),
        at_risk_students=int(at_risk_students),
        capacity_utilization_percent=float(avg_capacity_util),
        workload_distribution_percent=float(avg_workload),
        conflict_count=len(conflicts),
        data_quality_score=float(data_quality_score),
        top_issues=top_issues,
        mongo_status=mongo_status(),
        last_updated_at=now_dt,
        stale_after_seconds=STALE_AFTER_SECONDS,
    )

    _sync_admin_mongo(
        db,
        now_dt=now_dt,
        work_date=work_date,
        summary=summary,
        capacity_rows=capacity_rows,
        workload_rows=workload_rows,
        alerts=alerts,
    )
    return summary, capacity_rows, workload_rows, alerts


def _bootstrap_department_classrooms(
    db: Session,
    *,
    default_capacity: int,
    replace_existing: bool,
    actor_email: str,
) -> dict:
    created = 0
    existing = 0
    updated = 0
    block_total = 0
    room_total = 0
    now_dt = datetime.utcnow()

    block_department_map: dict[str, str] = {}
    block_school_map: dict[str, str] = {}
    block_specs: dict[str, dict] = {}

    for department, config in DEPARTMENT_CLASSROOM_LAYOUT.items():
        school = str(config.get("school") or department)
        blocks = config.get("blocks") or []
        for block_cfg in blocks:
            block = str(block_cfg.get("block"))
            floors = max(1, int(block_cfg.get("floors") or 1))
            rooms_per_floor = max(1, int(block_cfg.get("rooms_per_floor") or 1))
            planned_rooms = floors * rooms_per_floor
            block_total += 1
            room_total += planned_rooms
            block_department_map[block] = department
            block_school_map[block] = school
            block_specs[block] = {
                "department": department,
                "school": school,
                "floors": floors,
                "rooms_per_floor": rooms_per_floor,
                "planned_rooms": planned_rooms,
            }

            for floor in range(1, floors + 1):
                for serial in range(1, rooms_per_floor + 1):
                    room_number = _room_number_from_floor(floor, serial)
                    row = (
                        db.query(models.Classroom)
                        .filter(
                            models.Classroom.block == block,
                            models.Classroom.room_number == room_number,
                        )
                        .first()
                    )
                    if row:
                        existing += 1
                        if replace_existing and int(row.capacity) != int(default_capacity):
                            row.capacity = int(default_capacity)
                            updated += 1
                    else:
                        db.add(
                            models.Classroom(
                                block=block,
                                room_number=room_number,
                                capacity=int(default_capacity),
                            )
                        )
                        created += 1

    db.flush()
    all_blocks = sorted(block_specs.keys())
    room_rows = (
        db.query(models.Classroom)
        .filter(models.Classroom.block.in_(all_blocks))
        .all()
    )
    block_counts: dict[str, int] = defaultdict(int)
    block_capacity: dict[str, int] = defaultdict(int)
    for room in room_rows:
        block = str(room.block)
        block_counts[block] += 1
        block_capacity[block] += max(0, int(room.capacity or 0))
        mirror_document(
            "classrooms",
            {
                "id": int(room.id),
                "block": block,
                "room_number": str(room.room_number),
                "classroom_label": f"{block}-{room.room_number}",
                "capacity": int(room.capacity or 0),
                "department": block_department_map.get(block),
                "school": block_school_map.get(block),
                "updated_at": now_dt,
                "source": "department-bootstrap",
            },
            upsert_filter={"id": int(room.id)},
            required=False,
        )
    for block in all_blocks:
        spec = block_specs.get(block) or {}
        mirror_document(
            "blocks",
            {
                "block": block,
                "department": spec.get("department"),
                "school": spec.get("school"),
                "floors": int(spec.get("floors") or 0),
                "rooms_per_floor": int(spec.get("rooms_per_floor") or 0),
                "planned_rooms": int(spec.get("planned_rooms") or 0),
                "classroom_count": int(block_counts.get(block, 0)),
                "total_capacity": int(block_capacity.get(block, 0)),
                "updated_at": now_dt,
                "source": "department-bootstrap",
            },
            upsert_filter={"block": block},
            required=False,
        )

    mirror_document(
        "admin_audit_logs",
        {
            "action": "department_classroom_bootstrap",
            "actor_email": actor_email,
            "created": int(created),
            "existing": int(existing),
            "updated": int(updated),
            "blocks": int(block_total),
            "planned_rooms": int(room_total),
            "default_capacity": int(default_capacity),
            "replace_existing": bool(replace_existing),
            "created_at": now_dt,
            "source": "admin",
        },
        required=False,
    )
    return {
        "created": int(created),
        "existing": int(existing),
        "updated": int(updated),
        "blocks": int(block_total),
        "planned_rooms": int(room_total),
        "default_capacity": int(default_capacity),
        "replace_existing": bool(replace_existing),
        "departments": {
            dept: {
                "school": str(config.get("school") or dept),
                "blocks": [str(item.get("block")) for item in (config.get("blocks") or [])],
            }
            for dept, config in DEPARTMENT_CLASSROOM_LAYOUT.items()
        },
    }


@router.get("/summary", response_model=schemas.AdminSummaryOut)
def admin_summary(
    work_date: date | None = Query(default=None),
    mode: str = Query(default="enrollment", pattern="^(enrollment|attendance_marked)$"),
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)
    ),
):
    target_date = work_date or date.today()
    summary, _, _, _ = _build_admin_payload(db, work_date=target_date, mode=mode)
    return summary


@router.get("/capacity", response_model=list[schemas.AdminCapacityItem])
def admin_capacity(
    work_date: date | None = Query(default=None),
    mode: str = Query(default="enrollment", pattern="^(enrollment|attendance_marked)$"),
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)
    ),
):
    target_date = work_date or date.today()
    _, capacity_rows, _, _ = _build_admin_payload(db, work_date=target_date, mode=mode)
    return capacity_rows


@router.get("/workload", response_model=list[schemas.AdminWorkloadItem])
def admin_workload(
    work_date: date | None = Query(default=None),
    mode: str = Query(default="enrollment", pattern="^(enrollment|attendance_marked)$"),
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)
    ),
):
    target_date = work_date or date.today()
    _, _, workload_rows, _ = _build_admin_payload(db, work_date=target_date, mode=mode)
    return workload_rows


@router.get("/alerts", response_model=list[schemas.AdminAlertItem])
def admin_alerts(
    work_date: date | None = Query(default=None),
    mode: str = Query(default="enrollment", pattern="^(enrollment|attendance_marked)$"),
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)
    ),
):
    target_date = work_date or date.today()
    _, _, _, alerts = _build_admin_payload(db, work_date=target_date, mode=mode)
    return alerts


@router.get("/live", response_model=schemas.AdminLiveOut)
def admin_live(
    work_date: date | None = Query(default=None),
    mode: str = Query(default="enrollment", pattern="^(enrollment|attendance_marked)$"),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)
    ),
):
    target_date = work_date or date.today()
    cache_key = (
        f"admin:live:{_admin_cache_scope_key(current_user)}:"
        f"{target_date.isoformat()}:{mode}"
    )
    cached = cache_get_json(cache_key)
    if isinstance(cached, dict):
        try:
            return schemas.AdminLiveOut.model_validate(cached)
        except Exception:  # noqa: BLE001
            pass

    summary, capacity_rows, workload_rows, alerts = _build_admin_payload(db, work_date=target_date, mode=mode)
    payload = schemas.AdminLiveOut(
        summary=summary,
        capacity=capacity_rows,
        workload=workload_rows,
        alerts=alerts,
        last_updated_at=summary.last_updated_at,
        stale_after_seconds=STALE_AFTER_SECONDS,
    )
    cache_set_json(
        cache_key,
        payload.model_dump(mode="json"),
        ttl_seconds=ADMIN_LIVE_CACHE_TTL_SECONDS,
    )
    return payload


@router.get("/insights", response_model=schemas.AdminInsightsOut)
def admin_insights(
    work_date: date | None = Query(default=None),
    mode: str = Query(default="enrollment", pattern="^(enrollment|attendance_marked)$"),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)
    ),
):
    target_date = work_date or date.today()
    cache_key = (
        f"admin:insights:{_admin_cache_scope_key(current_user)}:"
        f"{target_date.isoformat()}:{mode}"
    )
    cached = cache_get_json(cache_key)
    if isinstance(cached, dict):
        try:
            return schemas.AdminInsightsOut.model_validate(cached)
        except Exception:  # noqa: BLE001
            pass

    summary, capacity_rows, workload_rows, _ = _build_admin_payload(
        db,
        work_date=target_date,
        mode=mode,
    )
    payload = _build_admin_insights(
        summary=summary,
        capacity_rows=capacity_rows,
        workload_rows=workload_rows,
    )
    cache_set_json(
        cache_key,
        payload.model_dump(mode="json"),
        ttl_seconds=ADMIN_INSIGHTS_CACHE_TTL_SECONDS,
    )
    return payload


@router.get("/rms/queries", response_model=schemas.RMSQueryDashboardOut)
def rms_queries_dashboard(
    category: str = Query(default="all"),
    status: str = Query(default="all", pattern="^(all|pending|resolved)$"),
    limit: int = Query(default=250, ge=20, le=1000),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    role = current_user.role
    faculty_scope_id: int | None = None
    if role == models.UserRole.FACULTY:
        if not current_user.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty account is not linked correctly.")
        faculty_scope_id = int(current_user.faculty_id)

    category_filter = _normalize_rms_category_filter(category)
    query = db.query(models.SupportQueryMessage)
    if faculty_scope_id is not None:
        query = query.filter(models.SupportQueryMessage.faculty_id == faculty_scope_id)
    if category_filter is not None:
        query = query.filter(models.SupportQueryMessage.category == category_filter.value)

    rows = (
        query.order_by(models.SupportQueryMessage.created_at.desc(), models.SupportQueryMessage.id.desc())
        .limit(min(max(int(limit) * 8, int(limit)), 5000))
        .all()
    )

    if not rows:
        return schemas.RMSQueryDashboardOut(
            total_threads=0,
            total_pending=0,
            categories=[
                schemas.RMSQueryCategoryBucketOut(category=cat, total_threads=0, pending_threads=0, threads=[])
                for cat in RMS_QUERY_CATEGORIES
            ],
        )

    student_ids = sorted({int(row.student_id) for row in rows})
    faculty_ids = sorted({int(row.faculty_id) for row in rows})
    students = (
        db.query(models.Student).filter(models.Student.id.in_(student_ids)).all()
        if student_ids
        else []
    )
    faculties = (
        db.query(models.Faculty).filter(models.Faculty.id.in_(faculty_ids)).all()
        if faculty_ids
        else []
    )
    student_map = {int(item.id): item for item in students}
    faculty_map = {int(item.id): item for item in faculties}

    aggregated: dict[tuple[int, int, str], dict] = {}
    for row in rows:
        row_category = _coerce_rms_category(row.category)
        key = (int(row.student_id), int(row.faculty_id), row_category.value)
        entry = aggregated.get(key)
        if entry is None:
            student = student_map.get(int(row.student_id))
            faculty = faculty_map.get(int(row.faculty_id))
            last_sender_role = str(row.sender_role or "").strip().lower() or models.UserRole.STUDENT.value
            last_message_raw = str(row.message or "").strip()
            action_marker = _parse_rms_action_marker(last_message_raw)
            action_state = schemas.RMSQueryActionState.NONE
            action_note = None
            scheduled_for = None
            action_by_role = None
            last_message = last_message_raw
            if action_marker:
                action_state = RMS_ACTION_TO_STATE.get(action_marker["action"], schemas.RMSQueryActionState.NONE)
                action_note = action_marker["note"]
                scheduled_for = action_marker["scheduled_for"]
                action_by_role = action_marker["actor_role"] or last_sender_role
                last_message = _rms_action_summary_text(
                    action=action_marker["action"],
                    note=action_note,
                    scheduled_for=scheduled_for,
                )
            entry = {
                "student_id": int(row.student_id),
                "student_name": str(getattr(student, "name", "") or f"Student #{row.student_id}"),
                "student_email": str(getattr(student, "email", "") or "") or None,
                "student_registration_number": (
                    str(getattr(student, "registration_number", "") or "").strip().upper() or None
                ),
                "faculty_id": int(row.faculty_id),
                "faculty_name": str(getattr(faculty, "name", "") or f"Faculty #{row.faculty_id}"),
                "section": str(row.section or ""),
                "category": row_category,
                "subject": str(row.subject or "").strip() or f"{row_category.value} Query",
                "last_message": last_message or "No message body.",
                "last_sender_role": last_sender_role,
                "last_created_at": row.created_at or datetime.utcnow(),
                "unread_from_student": 0,
                "action_state": action_state,
                "action_note": action_note,
                "scheduled_for": scheduled_for,
                "action_by_role": action_by_role,
                "action_updated_at": (row.created_at or datetime.utcnow()) if action_marker else None,
            }
            aggregated[key] = entry

        sender_role = str(row.sender_role or "").strip().lower()
        if sender_role == models.UserRole.STUDENT.value and row.read_at is None:
            entry["unread_from_student"] = int(entry["unread_from_student"]) + 1

    threads: list[schemas.RMSQueryThreadOut] = []
    for item in aggregated.values():
        pending_action = bool(item["unread_from_student"]) or item["last_sender_role"] == models.UserRole.STUDENT.value
        if (
            item["action_state"] != schemas.RMSQueryActionState.NONE
            and item["last_sender_role"] != models.UserRole.STUDENT.value
        ):
            pending_action = False
        if status == "pending" and not pending_action:
            continue
        if status == "resolved" and pending_action:
            continue
        threads.append(
            schemas.RMSQueryThreadOut(
                student_id=int(item["student_id"]),
                student_name=str(item["student_name"]),
                student_email=item["student_email"],
                student_registration_number=item["student_registration_number"],
                faculty_id=int(item["faculty_id"]),
                faculty_name=str(item["faculty_name"]),
                section=str(item["section"]),
                category=item["category"],
                subject=str(item["subject"]),
                last_message=str(item["last_message"]),
                last_sender_role=str(item["last_sender_role"]),
                last_created_at=item["last_created_at"],
                unread_from_student=int(item["unread_from_student"]),
                pending_action=pending_action,
                action_state=item["action_state"],
                action_note=item["action_note"],
                scheduled_for=item["scheduled_for"],
                action_by_role=item["action_by_role"],
                action_updated_at=item["action_updated_at"],
            )
        )

    threads.sort(key=lambda item: (item.last_created_at, item.student_id), reverse=True)
    threads = threads[: int(limit)]

    buckets = {
        cat: schemas.RMSQueryCategoryBucketOut(category=cat, total_threads=0, pending_threads=0, threads=[])
        for cat in RMS_QUERY_CATEGORIES
    }
    for thread in threads:
        bucket = buckets.get(thread.category)
        if bucket is None:
            bucket = buckets[schemas.SupportQueryCategory.OTHER]
        bucket.threads.append(thread)
        bucket.total_threads += 1
        if thread.pending_action:
            bucket.pending_threads += 1

    total_pending = sum(1 for thread in threads if thread.pending_action)
    return schemas.RMSQueryDashboardOut(
        total_threads=len(threads),
        total_pending=total_pending,
        categories=[buckets[cat] for cat in RMS_QUERY_CATEGORIES],
    )


@router.post("/rms/queries/action", response_model=schemas.RMSQueryActionOut)
def rms_apply_query_action(
    payload: schemas.RMSQueryActionRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    student = db.get(models.Student, int(payload.student_id))
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    faculty = db.get(models.Faculty, int(payload.faculty_id))
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found.")

    category = _coerce_rms_category(payload.category.value)
    action = payload.action
    note = _normalize_rms_action_note(payload.note)
    scheduled_for = payload.scheduled_for
    if action == schemas.RMSQueryWorkflowAction.SCHEDULE and scheduled_for is None:
        raise HTTPException(status_code=400, detail="scheduled_for is required when action is schedule.")
    if action != schemas.RMSQueryWorkflowAction.SCHEDULE and scheduled_for is not None:
        raise HTTPException(status_code=400, detail="scheduled_for is allowed only for schedule action.")

    if current_user.role == models.UserRole.FACULTY:
        if not current_user.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty account is not linked correctly.")
        if int(current_user.faculty_id) != int(payload.faculty_id):
            raise HTTPException(status_code=403, detail="Faculty can update only their own RMS threads.")
        if not _faculty_can_manage_student_rms(db, faculty_id=int(current_user.faculty_id), student=student):
            raise HTTPException(
                status_code=403,
                detail="Student is outside your allocated section(s) and teaching scope.",
            )

    latest_thread_row = (
        db.query(models.SupportQueryMessage)
        .filter(
            models.SupportQueryMessage.student_id == int(student.id),
            models.SupportQueryMessage.faculty_id == int(faculty.id),
            models.SupportQueryMessage.category == category.value,
        )
        .order_by(models.SupportQueryMessage.created_at.desc(), models.SupportQueryMessage.id.desc())
        .first()
    )
    if not latest_thread_row:
        raise HTTPException(status_code=404, detail="No RMS query thread found for this student/faculty/category.")

    now_dt = datetime.utcnow()
    db.query(models.SupportQueryMessage).filter(
        models.SupportQueryMessage.student_id == int(student.id),
        models.SupportQueryMessage.faculty_id == int(faculty.id),
        models.SupportQueryMessage.category == category.value,
        models.SupportQueryMessage.sender_role == models.UserRole.STUDENT.value,
        models.SupportQueryMessage.read_at.is_(None),
    ).update(
        {models.SupportQueryMessage.read_at: now_dt},
        synchronize_session=False,
    )

    section_token = re.sub(r"\s+", "", str(student.section or latest_thread_row.section or "").strip().upper())
    if not section_token:
        section_token = "UNASSIGNED"
    section_token = _normalize_rms_section(section_token)
    subject = str(latest_thread_row.subject or "").strip() or f"{category.value} Query"
    action_message = _encode_rms_action_marker(
        action=action,
        actor_role=current_user.role,
        note=note,
        scheduled_for=scheduled_for,
    )
    action_row = models.SupportQueryMessage(
        student_id=int(student.id),
        faculty_id=int(faculty.id),
        section=section_token,
        category=category.value,
        subject=subject,
        message=action_message,
        sender_role=current_user.role.value,
        created_at=now_dt,
        read_at=None,
    )
    db.add(action_row)
    db.flush()

    case_row = _get_or_create_rms_case_for_thread(
        db,
        student=student,
        faculty=faculty,
        category=category,
        section=section_token,
        subject=subject,
        actor=current_user,
        source_message_id=int(action_row.id),
    )
    faculty_assignee = (
        db.query(models.AuthUser)
        .filter(
            models.AuthUser.faculty_id == int(faculty.id),
            models.AuthUser.role == models.UserRole.FACULTY,
        )
        .order_by(models.AuthUser.id.asc())
        .first()
    )
    assignee_id = int(faculty_assignee.id) if faculty_assignee else int(current_user.id)
    _apply_legacy_query_action_to_case(
        db,
        case_row=case_row,
        query_action=action,
        actor=current_user,
        note=note,
        assign_to_user_id=assignee_id,
    )
    db.commit()

    summary_text = _rms_action_summary_text(
        action=action.value,
        note=note,
        scheduled_for=scheduled_for,
    )
    mirror_document(
        "admin_audit_logs",
        {
            "action": "rms_query_workflow_action",
            "student_id": int(student.id),
            "faculty_id": int(faculty.id),
            "category": category.value,
            "workflow_action": action.value,
            "note": note,
            "scheduled_for": scheduled_for,
            "actor": {
                "user_id": int(current_user.id),
                "faculty_id": int(current_user.faculty_id) if current_user.faculty_id else None,
                "email": str(current_user.email or ""),
                "role": current_user.role.value,
            },
            "created_at": now_dt,
            "source": "rms",
        },
        required=False,
    )

    thread_dashboard = rms_queries_dashboard(
        category=category.value,
        status="all",
        limit=500,
        db=db,
        current_user=current_user,
    )
    selected_thread: schemas.RMSQueryThreadOut | None = None
    for bucket in thread_dashboard.categories:
        for thread in bucket.threads:
            if (
                int(thread.student_id) == int(student.id)
                and int(thread.faculty_id) == int(faculty.id)
                and thread.category == category
            ):
                selected_thread = thread
                break
        if selected_thread is not None:
            break

    if selected_thread is None:
        selected_thread = schemas.RMSQueryThreadOut(
            student_id=int(student.id),
            student_name=str(student.name or f"Student #{student.id}"),
            student_email=(str(student.email or "").strip() or None),
            student_registration_number=(str(student.registration_number or "").strip().upper() or None),
            faculty_id=int(faculty.id),
            faculty_name=str(faculty.name or f"Faculty #{faculty.id}"),
            section=section_token,
            category=category,
            subject=subject,
            last_message=summary_text,
            last_sender_role=current_user.role.value,
            last_created_at=now_dt,
            unread_from_student=0,
            pending_action=False,
            action_state=RMS_ACTION_TO_STATE[action.value],
            action_note=note,
            scheduled_for=scheduled_for,
            action_by_role=current_user.role.value,
            action_updated_at=now_dt,
        )

    publish_domain_event(
        "rms.thread.updated",
        payload={
            "student_id": int(student.id),
            "faculty_id": int(faculty.id),
            "category": category.value,
            "action": action.value,
            "note": note,
            "scheduled_for": scheduled_for.isoformat() if scheduled_for else None,
            "updated_at": now_dt.isoformat(),
        },
        scopes={
            f"student:{int(student.id)}",
            f"faculty:{int(faculty.id)}",
            "role:admin",
        },
        topics={"rms", "messages"},
        actor={
            "user_id": int(current_user.id),
            "role": current_user.role.value,
        },
        source="rms",
    )
    enqueue_notification(
        {
            "type": "rms_query_action",
            "student_id": int(student.id),
            "faculty_id": int(faculty.id),
            "category": category.value,
            "action": action.value,
            "scheduled_for": scheduled_for.isoformat() if scheduled_for else None,
        }
    )
    enqueue_recompute(
        {
            "entity": "rms_dashboard",
            "faculty_id": int(faculty.id),
            "student_id": int(student.id),
            "source": "rms.thread.updated",
        }
    )

    return schemas.RMSQueryActionOut(
        thread=selected_thread,
        message=summary_text,
    )


@router.get("/rms/students/search", response_model=schemas.RMSStudentLookupOut)
def rms_search_student_by_registration(
    registration_number: str = Query(..., min_length=3, max_length=40),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    normalized_registration = _normalize_rms_registration_number(registration_number)
    student = (
        db.query(models.Student)
        .filter(func.upper(models.Student.registration_number) == normalized_registration)
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found for this registration number.")

    faculty_scope_id: int | None = None
    if current_user.role == models.UserRole.FACULTY:
        if not current_user.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty account is not linked correctly.")
        faculty_scope_id = int(current_user.faculty_id)
        if not _faculty_can_manage_student_rms(db, faculty_id=faculty_scope_id, student=student):
            raise HTTPException(
                status_code=403,
                detail="Student is outside your allocated section(s) and teaching scope.",
            )

    return _rms_student_lookup_out(
        db,
        student=student,
        faculty_scope_id=faculty_scope_id,
    )


@router.put("/rms/students/{student_id}", response_model=schemas.RMSStudentUpdateOut)
def rms_update_student_profile(
    student_id: int,
    payload: schemas.RMSStudentUpdateRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    if payload.registration_number is None and payload.section is None:
        raise HTTPException(status_code=400, detail="Provide registration_number and/or section.")

    student = db.get(models.Student, int(student_id))
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    faculty_scope_id: int | None = None
    if current_user.role == models.UserRole.FACULTY:
        if not current_user.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty account is not linked correctly.")
        faculty_scope_id = int(current_user.faculty_id)
        if not _faculty_can_manage_student_rms(db, faculty_id=faculty_scope_id, student=student):
            raise HTTPException(
                status_code=403,
                detail="Student is outside your allocated section(s) and teaching scope.",
            )

    changed_fields: list[str] = []
    now_dt = datetime.utcnow()

    if payload.registration_number is not None:
        registration_number = _normalize_rms_registration_number(payload.registration_number)
        existing_registration = str(student.registration_number or "").strip().upper()
        if registration_number != existing_registration:
            duplicate = (
                db.query(models.Student)
                .filter(
                    models.Student.id != int(student.id),
                    func.upper(models.Student.registration_number) == registration_number,
                )
                .first()
            )
            if duplicate:
                raise HTTPException(status_code=409, detail="Registration number is already assigned to another student.")
            student.registration_number = registration_number
            changed_fields.append("registration_number")

    if payload.section is not None:
        section = _normalize_rms_section(payload.section)
        existing_section = re.sub(r"\s+", "", str(student.section or "").strip().upper())
        if section != existing_section:
            if current_user.role == models.UserRole.FACULTY:
                faculty = db.get(models.Faculty, int(faculty_scope_id))
                allowed_sections = _faculty_allowed_sections(faculty)
                if not allowed_sections:
                    raise HTTPException(
                        status_code=403,
                        detail="Set your faculty section before approving student section updates.",
                    )
                if section not in allowed_sections:
                    raise HTTPException(
                        status_code=403,
                        detail="Faculty can update students only to their own section scope.",
                    )
            student.section = section
            student.section_updated_at = now_dt
            changed_fields.append("section")

    if changed_fields:
        db.commit()
        mirror_document(
            "students",
            {
                "id": int(student.id),
                "name": student.name,
                "email": student.email,
                "registration_number": student.registration_number,
                "parent_email": student.parent_email,
                "profile_photo_data_url": None,
                "profile_photo_object_key": student.profile_photo_object_key,
                "profile_photo_url": signed_url_for_object(student.profile_photo_object_key),
                "profile_photo_updated_at": student.profile_photo_updated_at,
                "profile_photo_locked_until": student.profile_photo_locked_until,
                "profile_face_template_json": student.profile_face_template_json,
                "profile_face_template_updated_at": student.profile_face_template_updated_at,
                "enrollment_video_template_json": student.enrollment_video_template_json,
                "enrollment_video_updated_at": student.enrollment_video_updated_at,
                "enrollment_video_locked_until": student.enrollment_video_locked_until,
                "section": student.section,
                "section_updated_at": student.section_updated_at,
                "department": student.department,
                "semester": student.semester,
                "created_at": student.created_at,
                "source": "rms-student-update",
                "updated_at": now_dt,
            },
            upsert_filter={"id": int(student.id)},
            required=False,
        )
        mirror_document(
            "admin_audit_logs",
            {
                "action": "rms_student_profile_update",
                "student_id": int(student.id),
                "changed_fields": changed_fields,
                "updated_values": {
                    "registration_number": student.registration_number,
                    "section": student.section,
                },
                "actor": {
                    "user_id": int(current_user.id),
                    "faculty_id": int(current_user.faculty_id) if current_user.faculty_id else None,
                    "email": str(current_user.email or ""),
                    "role": current_user.role.value,
                },
                "created_at": now_dt,
                "source": "rms",
            },
            required=False,
        )
    else:
        db.flush()

    student_out = _rms_student_lookup_out(
        db,
        student=student,
        faculty_scope_id=faculty_scope_id,
    )
    message = "No profile changes were needed."
    if changed_fields:
        message = f"Student profile updated: {', '.join(changed_fields)}."
        publish_domain_event(
            "rms.student.updated",
            payload={
                "student_id": int(student.id),
                "changed_fields": changed_fields,
                "registration_number": str(student.registration_number or "").strip().upper() or None,
                "section": str(student.section or "").strip().upper() or None,
                "updated_at": now_dt.isoformat(),
            },
            scopes={f"student:{int(student.id)}", "role:admin", "role:faculty"},
            topics={"rms", "attendance"},
            actor={
                "user_id": int(current_user.id),
                "role": current_user.role.value,
            },
            source="rms",
        )
        enqueue_recompute(
            {
                "entity": "student_profile_sync",
                "student_id": int(student.id),
                "source": "rms.student.updated",
            }
        )
    return schemas.RMSStudentUpdateOut(
        student=student_out,
        changed_fields=changed_fields,
        message=message,
    )


@router.get("/rms/attendance/student-context", response_model=schemas.RMSAttendanceStudentContextOut)
def rms_attendance_student_context(
    registration_number: str = Query(..., min_length=3, max_length=40),
    attendance_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    target_date = attendance_date or date.today()
    normalized_registration = _normalize_rms_registration_number(registration_number)
    student = (
        db.query(models.Student)
        .filter(func.upper(models.Student.registration_number) == normalized_registration)
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found for this registration number.")

    faculty_scope_id: int | None = None
    if current_user.role == models.UserRole.FACULTY:
        if not current_user.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty account is not linked correctly.")
        faculty_scope_id = int(current_user.faculty_id)
        if not _faculty_can_manage_student_rms(db, faculty_id=faculty_scope_id, student=student):
            raise HTTPException(
                status_code=403,
                detail="Student is outside your allocated section(s) and teaching scope.",
            )

    schedule_query = (
        db.query(models.ClassSchedule, models.Course)
        .join(models.Course, models.Course.id == models.ClassSchedule.course_id)
        .join(models.Enrollment, models.Enrollment.course_id == models.Course.id)
        .filter(
            models.Enrollment.student_id == int(student.id),
            models.ClassSchedule.weekday == int(target_date.weekday()),
            models.ClassSchedule.is_active.is_(True),
        )
    )
    if faculty_scope_id is not None:
        schedule_query = schedule_query.filter(models.Course.faculty_id == faculty_scope_id)
    schedule_rows = (
        schedule_query
        .order_by(
            models.Course.code.asc(),
            models.ClassSchedule.start_time.asc(),
            models.ClassSchedule.id.asc(),
        )
        .all()
    )

    schedule_ids = sorted({int(schedule.id) for schedule, _ in schedule_rows})
    course_ids = sorted({int(course.id) for _, course in schedule_rows})
    submission_rows = (
        db.query(models.AttendanceSubmission.schedule_id, models.AttendanceSubmission.status)
        .filter(
            models.AttendanceSubmission.student_id == int(student.id),
            models.AttendanceSubmission.class_date == target_date,
            models.AttendanceSubmission.schedule_id.in_(schedule_ids),
        )
        .all()
        if schedule_ids
        else []
    )
    submission_status_by_schedule_id: dict[int, models.AttendanceStatus] = {}
    for schedule_id_value, submission_status in submission_rows:
        mapped_status = _submission_status_to_attendance_status(submission_status)
        if mapped_status is not None:
            submission_status_by_schedule_id[int(schedule_id_value)] = mapped_status

    record_rows = (
        db.query(models.AttendanceRecord.course_id, models.AttendanceRecord.status)
        .filter(
            models.AttendanceRecord.student_id == int(student.id),
            models.AttendanceRecord.attendance_date == target_date,
            models.AttendanceRecord.course_id.in_(course_ids),
        )
        .all()
        if course_ids
        else []
    )
    record_status_by_course_id = {
        int(course_id_value): status_value
        for course_id_value, status_value in record_rows
    }

    faculty_ids = sorted({int(course.faculty_id) for _, course in schedule_rows if course.faculty_id})
    faculty_map = (
        {int(row.id): row for row in db.query(models.Faculty).filter(models.Faculty.id.in_(faculty_ids)).all()}
        if faculty_ids
        else {}
    )

    grouped_subjects: dict[int, dict[str, Any]] = {}
    for schedule, course in schedule_rows:
        course_id = int(course.id)
        subject_entry = grouped_subjects.get(course_id)
        if subject_entry is None:
            faculty = faculty_map.get(int(course.faculty_id)) if course.faculty_id else None
            subject_entry = {
                "course_id": course_id,
                "course_code": str(course.code or "").strip().upper(),
                "course_title": str(course.title or ""),
                "faculty_id": int(course.faculty_id),
                "faculty_name": (str(faculty.name or "").strip() or None) if faculty else None,
                "slots": [],
            }
            grouped_subjects[course_id] = subject_entry

        slot_status = submission_status_by_schedule_id.get(int(schedule.id))
        if slot_status is None:
            slot_status = record_status_by_course_id.get(course_id)
        subject_entry["slots"].append(
            schemas.RMSAttendanceSubjectSlotOut(
                schedule_id=int(schedule.id),
                weekday=int(schedule.weekday),
                start_time=schedule.start_time,
                end_time=schedule.end_time,
                classroom_label=(str(schedule.classroom_label or "").strip() or None),
                current_status=slot_status,
                current_status_label=_attendance_status_label(slot_status),
            )
        )

    subjects: list[schemas.RMSAttendanceStudentSubjectOut] = []
    for subject_entry in grouped_subjects.values():
        slot_models = list(subject_entry.get("slots") or [])
        slot_statuses = [item.current_status for item in slot_models if item.current_status is not None]
        current_status: models.AttendanceStatus | None = None
        if any(status == models.AttendanceStatus.PRESENT for status in slot_statuses):
            current_status = models.AttendanceStatus.PRESENT
        elif any(status == models.AttendanceStatus.ABSENT for status in slot_statuses):
            current_status = models.AttendanceStatus.ABSENT
        subjects.append(
            schemas.RMSAttendanceStudentSubjectOut(
                course_id=int(subject_entry["course_id"]),
                course_code=str(subject_entry["course_code"]),
                course_title=str(subject_entry["course_title"]),
                faculty_id=int(subject_entry["faculty_id"]),
                faculty_name=subject_entry["faculty_name"],
                current_status=current_status,
                current_status_label=_attendance_status_label(current_status),
                slots=slot_models,
            )
        )
    subjects.sort(key=lambda item: (item.course_code, item.course_id))

    student_out = _rms_student_lookup_out(
        db,
        student=student,
        faculty_scope_id=faculty_scope_id,
    )
    slot_count = sum(len(item.slots) for item in subjects)
    message = (
        f"Loaded {len(subjects)} subject(s) and {slot_count} class slot(s) for {target_date.isoformat()}."
        if subjects
        else "No class slot found for this student on the selected date in your scope."
    )
    return schemas.RMSAttendanceStudentContextOut(
        student=student_out,
        attendance_date=target_date,
        subjects=subjects,
        message=message,
    )


@router.put("/rms/attendance/status", response_model=schemas.RMSAttendanceStatusUpdateOut)
def rms_update_attendance_status(
    payload: schemas.RMSAttendanceStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    registration_number = _normalize_rms_registration_number(payload.registration_number)
    student = (
        db.query(models.Student)
        .filter(func.upper(models.Student.registration_number) == registration_number)
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found for this registration number.")

    normalized_course_code = (
        _normalize_admin_course_code(payload.course_code)
        if payload.course_code
        else ""
    )
    course = (
        db.query(models.Course)
        .filter(func.upper(models.Course.code) == normalized_course_code)
        .first()
        if normalized_course_code
        else None
    )
    if payload.course_code and not course:
        raise HTTPException(status_code=404, detail="Course not found for this course code.")

    target_schedule: models.ClassSchedule | None = None
    if payload.schedule_id:
        target_schedule = db.get(models.ClassSchedule, int(payload.schedule_id))
        if not target_schedule or not target_schedule.is_active:
            raise HTTPException(status_code=404, detail="Schedule not found for selected slot.")
        if int(target_schedule.weekday) != int(payload.attendance_date.weekday()):
            raise HTTPException(
                status_code=400,
                detail="Selected schedule is not configured on the chosen attendance date.",
            )
        schedule_course = db.get(models.Course, int(target_schedule.course_id))
        if not schedule_course:
            raise HTTPException(status_code=404, detail="Course not found for selected schedule.")
        if course is not None and int(course.id) != int(schedule_course.id):
            raise HTTPException(
                status_code=409,
                detail="Selected schedule does not belong to the provided subject.",
            )
        course = schedule_course
    else:
        if course is None:
            raise HTTPException(
                status_code=400,
                detail="course_code or schedule_id is required for attendance update.",
            )
        candidate_schedules = (
            db.query(models.ClassSchedule)
            .filter(
                models.ClassSchedule.course_id == int(course.id),
                models.ClassSchedule.weekday == int(payload.attendance_date.weekday()),
                models.ClassSchedule.is_active.is_(True),
            )
            .order_by(models.ClassSchedule.start_time.asc(), models.ClassSchedule.id.asc())
            .all()
        )
        if not candidate_schedules:
            raise HTTPException(
                status_code=409,
                detail="No active class slot configured for this subject on the selected date.",
            )
        target_schedule = candidate_schedules[0]

    if course is None or target_schedule is None:
        raise HTTPException(status_code=500, detail="Unable to resolve course and schedule for attendance update.")
    course_code = str(course.code or "").strip().upper()

    if current_user.role == models.UserRole.FACULTY:
        if not current_user.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty account is not linked correctly.")
        if int(course.faculty_id) != int(current_user.faculty_id):
            raise HTTPException(
                status_code=403,
                detail="Faculty can update attendance only for courses assigned to them.",
            )
        if not _faculty_can_manage_student_rms(db, faculty_id=int(current_user.faculty_id), student=student):
            raise HTTPException(
                status_code=403,
                detail="Student is outside your allocated section(s) and teaching scope.",
            )

    enrollment = (
        db.query(models.Enrollment)
        .filter(
            models.Enrollment.student_id == int(student.id),
            models.Enrollment.course_id == int(course.id),
        )
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=409, detail="Student is not enrolled in this course.")

    acting_faculty_id = int(course.faculty_id)
    now_dt = datetime.utcnow()
    source = "rms-admin-attendance-override"
    if current_user.role == models.UserRole.FACULTY:
        acting_faculty_id = int(current_user.faculty_id or course.faculty_id)
        source = "rms-faculty-attendance-override"

    previous_status = _resolve_student_schedule_attendance_status(
        db,
        student_id=int(student.id),
        schedule_id=int(target_schedule.id),
        attendance_date=payload.attendance_date,
        fallback_course_id=int(course.id),
    )

    note = _normalize_rms_action_note(payload.note)
    slot_label = f"{target_schedule.start_time.strftime('%H:%M')}-{target_schedule.end_time.strftime('%H:%M')}"
    review_note = (
        note
        or (
            f"Attendance {payload.status.value} override via RMS by "
            f"{current_user.role.value} for slot {slot_label}."
        )
    )
    submission_status = (
        models.AttendanceSubmissionStatus.APPROVED
        if payload.status == models.AttendanceStatus.PRESENT
        else models.AttendanceSubmissionStatus.REJECTED
    )
    target_submission = (
        db.query(models.AttendanceSubmission)
        .filter(
            models.AttendanceSubmission.student_id == int(student.id),
            models.AttendanceSubmission.course_id == int(course.id),
            models.AttendanceSubmission.class_date == payload.attendance_date,
            models.AttendanceSubmission.schedule_id == int(target_schedule.id),
        )
        .order_by(models.AttendanceSubmission.id.asc())
        .first()
    )
    if target_submission is None:
        target_submission = models.AttendanceSubmission(
            schedule_id=int(target_schedule.id),
            course_id=int(course.id),
            faculty_id=int(target_schedule.faculty_id),
            student_id=int(student.id),
            class_date=payload.attendance_date,
            selfie_photo_data_url=None,
            submitted_at=now_dt,
        )
        db.add(target_submission)

    target_submission.status = submission_status
    target_submission.ai_match = payload.status == models.AttendanceStatus.PRESENT
    target_submission.ai_confidence = 1.0 if payload.status == models.AttendanceStatus.PRESENT else 0.0
    target_submission.ai_model = "rms-attendance-override"
    target_submission.ai_reason = review_note
    target_submission.reviewed_by_faculty_id = int(acting_faculty_id)
    target_submission.reviewed_at = now_dt
    target_submission.review_note = review_note
    if not target_submission.submitted_at:
        target_submission.submitted_at = now_dt

    db.flush()
    submission_rows = (
        db.query(models.AttendanceSubmission.status)
        .filter(
            models.AttendanceSubmission.student_id == int(student.id),
            models.AttendanceSubmission.course_id == int(course.id),
            models.AttendanceSubmission.class_date == payload.attendance_date,
        )
        .all()
    )
    aggregate_status = _derive_attendance_status_from_submissions(submission_rows) or payload.status
    _, record = append_event_and_recompute(
        db,
        student_id=int(student.id),
        course_id=int(course.id),
        attendance_date=payload.attendance_date,
        status=aggregate_status,
        source=source,
        actor_user_id=int(current_user.id),
        actor_faculty_id=int(acting_faculty_id),
        actor_role=current_user.role,
        note=review_note,
    )
    if record is None:
        raise HTTPException(status_code=500, detail="Failed to recompute attendance aggregate")
    evaluate_attendance_recovery(
        db,
        student_id=int(student.id),
        course_id=int(course.id),
    )

    submissions_for_sync: list[models.AttendanceSubmission] = [target_submission]

    section_token = re.sub(r"\s+", "", str(student.section or "").strip().upper()) or "UNASSIGNED"
    notification_text = (
        f"Your attendance has been updated for subject {str(course.title or '').strip()} "
        f"({str(course.code or '').strip().upper()}) on {payload.attendance_date.isoformat()} "
        f"for slot {slot_label}. "
        f"Updated at {now_dt.strftime('%Y-%m-%d %H:%M:%S')} (server time). "
        "Please check your attendance module for more information."
    )
    student_notification = models.FacultyMessage(
        faculty_id=int(course.faculty_id),
        student_id=int(student.id),
        section=section_token,
        message_type="Announcement",
        message=notification_text,
        created_at=now_dt,
        read_at=None,
    )
    db.add(student_notification)

    db.commit()
    db.refresh(record)
    db.refresh(student_notification)
    for submission in submissions_for_sync:
        db.refresh(submission)
    faculty = db.get(models.Faculty, int(course.faculty_id))

    mirror_document(
        "attendance_records",
        {
            "id": int(record.id),
            "student_id": int(record.student_id),
            "course_id": int(record.course_id),
            "marked_by_faculty_id": int(record.marked_by_faculty_id),
            "attendance_date": record.attendance_date.isoformat(),
            "status": record.status.value,
            "source": record.source,
            "created_at": record.created_at,
            "updated_at": now_dt,
        },
        upsert_filter={"id": int(record.id)},
        required=False,
    )
    for submission in submissions_for_sync:
        mirror_document(
            "attendance_submissions",
            {
                "id": int(submission.id),
                "schedule_id": int(submission.schedule_id),
                "course_id": int(submission.course_id),
                "faculty_id": int(submission.faculty_id),
                "student_id": int(submission.student_id),
                "class_date": submission.class_date.isoformat(),
                "status": submission.status.value,
                "ai_match": bool(submission.ai_match),
                "ai_confidence": float(submission.ai_confidence or 0.0),
                "ai_model": submission.ai_model,
                "ai_reason": submission.ai_reason,
                "submitted_at": submission.submitted_at,
                "reviewed_at": submission.reviewed_at,
                "reviewed_by_faculty_id": submission.reviewed_by_faculty_id,
                "review_note": submission.review_note,
                "source": source,
            },
            upsert_filter={"id": int(submission.id)},
            required=False,
        )
    mirror_document(
        "faculty_messages",
        {
            "id": int(student_notification.id),
            "faculty_id": int(student_notification.faculty_id),
            "student_id": int(student_notification.student_id),
            "section": str(student_notification.section or ""),
            "message_type": str(student_notification.message_type or "Announcement"),
            "message": str(student_notification.message or ""),
            "created_at": student_notification.created_at,
            "read_at": student_notification.read_at,
            "source": "rms-attendance-update",
        },
        upsert_filter={"id": int(student_notification.id)},
        required=False,
    )
    mirror_document(
        "admin_audit_logs",
        {
            "action": "rms_attendance_status_override",
            "record_id": int(record.id),
            "student_id": int(student.id),
            "registration_number": registration_number,
            "course_id": int(course.id),
            "course_code": course_code,
            "schedule_id": int(target_schedule.id),
            "class_start_time": str(target_schedule.start_time),
            "class_end_time": str(target_schedule.end_time),
            "attendance_date": payload.attendance_date.isoformat(),
            "previous_status": previous_status.value if previous_status else None,
            "updated_status": payload.status.value,
            "note": note,
            "notification_message_id": int(student_notification.id),
            "attendance_submission_ids": [int(item.id) for item in submissions_for_sync],
            "actor": {
                "user_id": int(current_user.id),
                "faculty_id": int(current_user.faculty_id) if current_user.faculty_id else None,
                "email": str(current_user.email or ""),
                "role": current_user.role.value,
            },
            "created_at": now_dt,
            "source": "rms",
        },
        required=False,
    )

    status_label = str(payload.status.value).upper()
    message = (
        f"Attendance status set to {status_label} for {registration_number} "
        f"in {course_code} on {payload.attendance_date.isoformat()} for slot {slot_label}."
    )
    if previous_status and previous_status == payload.status:
        message = (
            f"Attendance status already {status_label} for {registration_number} "
            f"in {course_code} on {payload.attendance_date.isoformat()} for slot {slot_label}."
        )

    publish_domain_event(
        "rms.attendance.updated",
        payload={
            "record_id": int(record.id),
            "schedule_id": int(target_schedule.id),
            "student_id": int(student.id),
            "course_id": int(course.id),
            "course_code": course_code,
            "attendance_date": payload.attendance_date.isoformat(),
            "previous_status": previous_status.value if previous_status else None,
            "updated_status": payload.status.value,
            "aggregate_status": record.status.value,
            "updated_at": now_dt.isoformat(),
        },
        scopes={
            f"student:{int(student.id)}",
            f"faculty:{int(course.faculty_id)}",
            "role:admin",
        },
        topics={"rms", "attendance", "messages"},
        actor={
            "user_id": int(current_user.id),
            "role": current_user.role.value,
        },
        source="rms",
    )
    enqueue_notification(
        {
            "type": "rms_attendance_override",
            "student_id": int(student.id),
            "course_id": int(course.id),
            "course_code": course_code,
            "schedule_id": int(target_schedule.id),
            "attendance_date": payload.attendance_date.isoformat(),
            "status": payload.status.value,
            "aggregate_status": record.status.value,
            "message_id": int(student_notification.id),
        }
    )
    enqueue_recompute(
        {
            "entity": "student_attendance_aggregate",
            "student_id": int(student.id),
            "source": "rms.attendance.updated",
        }
    )

    return schemas.RMSAttendanceStatusUpdateOut(
        record_id=int(record.id),
        schedule_id=int(target_schedule.id),
        class_start_time=target_schedule.start_time,
        class_end_time=target_schedule.end_time,
        classroom_label=(str(target_schedule.classroom_label or "").strip() or None),
        student_id=int(student.id),
        student_name=str(student.name or f"Student #{student.id}"),
        registration_number=(str(student.registration_number or "").strip().upper() or None),
        course_id=int(course.id),
        course_code=str(course.code or "").strip().upper(),
        course_title=str(course.title or ""),
        faculty_id=int(course.faculty_id),
        faculty_name=(str(faculty.name or "").strip() or None) if faculty else None,
        attendance_date=record.attendance_date,
        previous_status=previous_status,
        updated_status=payload.status,
        source=str(record.source or source),
        note=note,
        updated_at=now_dt,
        message_sent=bool(student_notification.id),
        message=message,
    )


@router.get("/search/students/by-registration", response_model=schemas.AdminStudentSearchOut)
def admin_search_student_by_registration(
    registration_number: str = Query(..., min_length=3, max_length=40),
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    normalized_registration = _normalize_rms_registration_number(registration_number)
    student = (
        db.query(models.Student)
        .filter(func.upper(models.Student.registration_number) == normalized_registration)
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found for this registration number.")
    return _admin_student_search_out(student)


@router.get("/search/faculty/by-identifier", response_model=schemas.AdminFacultySearchOut)
def admin_search_faculty_by_identifier(
    faculty_identifier: str = Query(..., min_length=3, max_length=40),
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    normalized_identifier = _normalize_rms_faculty_identifier(faculty_identifier)
    faculty = (
        db.query(models.Faculty)
        .filter(func.upper(models.Faculty.faculty_identifier) == normalized_identifier)
        .first()
    )
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found for this faculty identifier.")
    return _admin_faculty_search_out(faculty)


@router.get("/search/everything", response_model=schemas.AdminGlobalSearchOut)
def admin_search_everything(
    query: str = Query(..., min_length=2, max_length=80),
    limit: int = Query(default=25, ge=5, le=100),
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    normalized_query = _normalize_admin_search_query(query)
    needle_lower = normalized_query.lower()
    needle_upper = re.sub(r"\s+", "", normalized_query).upper()

    students = (
        db.query(models.Student)
        .filter(
            or_(
                func.upper(models.Student.registration_number).like(f"%{needle_upper}%"),
                func.lower(models.Student.name).like(f"%{needle_lower}%"),
                func.lower(models.Student.email).like(f"%{needle_lower}%"),
                func.lower(models.Student.department).like(f"%{needle_lower}%"),
            )
        )
        .order_by(models.Student.name.asc(), models.Student.id.asc())
        .limit(int(limit))
        .all()
    )

    faculty_rows = (
        db.query(models.Faculty)
        .filter(
            or_(
                func.upper(models.Faculty.faculty_identifier).like(f"%{needle_upper}%"),
                func.lower(models.Faculty.name).like(f"%{needle_lower}%"),
                func.lower(models.Faculty.email).like(f"%{needle_lower}%"),
                func.lower(models.Faculty.department).like(f"%{needle_lower}%"),
            )
        )
        .order_by(models.Faculty.name.asc(), models.Faculty.id.asc())
        .limit(int(limit))
        .all()
    )

    courses = (
        db.query(models.Course)
        .filter(
            or_(
                func.upper(models.Course.code).like(f"%{needle_upper}%"),
                func.lower(models.Course.title).like(f"%{needle_lower}%"),
            )
        )
        .order_by(models.Course.code.asc(), models.Course.id.asc())
        .limit(int(limit))
        .all()
    )
    faculty_map = (
        {
            int(row.id): row
            for row in db.query(models.Faculty)
            .filter(models.Faculty.id.in_({int(course.faculty_id) for course in courses}))
            .all()
        }
        if courses
        else {}
    )

    student_out = [_admin_student_search_out(row) for row in students]
    faculty_out = [_admin_faculty_search_out(row) for row in faculty_rows]
    course_out = [_admin_course_search_out(row, faculty_map=faculty_map) for row in courses]

    return schemas.AdminGlobalSearchOut(
        query=normalized_query,
        students=student_out,
        faculty=faculty_out,
        courses=course_out,
        total_matches=len(student_out) + len(faculty_out) + len(course_out),
    )


@router.post("/grades/upsert", response_model=schemas.AdminStudentGradeOut)
def admin_upsert_student_grade(
    payload: schemas.AdminStudentGradeUpsertRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    registration_number = _normalize_rms_registration_number(payload.registration_number)
    student = (
        db.query(models.Student)
        .filter(func.upper(models.Student.registration_number) == registration_number)
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found for this registration number.")

    course_code = _normalize_admin_course_code(payload.course_code)

    course = (
        db.query(models.Course)
        .filter(func.upper(models.Course.code) == course_code)
        .first()
    )
    if not course:
        raise HTTPException(status_code=404, detail="Course not found for this course code.")

    enrollment = (
        db.query(models.Enrollment)
        .filter(
            models.Enrollment.student_id == int(student.id),
            models.Enrollment.course_id == int(course.id),
        )
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=409, detail="Student is not enrolled in this course.")

    grade_letter = _normalize_admin_grade_letter(payload.grade_letter)
    marks_percent = float(round(float(payload.marks_percent), 2)) if payload.marks_percent is not None else None
    remark = _normalize_rms_action_note(payload.remark)
    grade_points = float(ADMIN_GRADE_POINTS_BY_LETTER[grade_letter])
    now_dt = datetime.utcnow()

    grade = (
        db.query(models.StudentGrade)
        .filter(
            models.StudentGrade.student_id == int(student.id),
            models.StudentGrade.course_id == int(course.id),
        )
        .first()
    )
    if grade:
        grade.grade_letter = grade_letter
        grade.grade_points = grade_points
        grade.marks_percent = marks_percent
        grade.remark = remark
        grade.faculty_id = int(course.faculty_id)
        grade.graded_by_user_id = int(current_user.id)
        grade.graded_at = now_dt
        grade.updated_at = now_dt
    else:
        grade = models.StudentGrade(
            student_id=int(student.id),
            course_id=int(course.id),
            faculty_id=int(course.faculty_id),
            grade_letter=grade_letter,
            grade_points=grade_points,
            marks_percent=marks_percent,
            remark=remark,
            graded_by_user_id=int(current_user.id),
            graded_at=now_dt,
            updated_at=now_dt,
        )
        db.add(grade)

    db.commit()
    db.refresh(grade)

    faculty = db.get(models.Faculty, int(course.faculty_id)) if course.faculty_id else None
    mirror_document(
        "student_grades",
        {
            "id": int(grade.id),
            "student_id": int(grade.student_id),
            "course_id": int(grade.course_id),
            "faculty_id": int(grade.faculty_id) if grade.faculty_id else None,
            "grade_letter": grade.grade_letter,
            "grade_points": grade.grade_points,
            "marks_percent": grade.marks_percent,
            "remark": grade.remark,
            "graded_by_user_id": grade.graded_by_user_id,
            "graded_at": grade.graded_at,
            "updated_at": grade.updated_at,
            "source": "admin-grade-upsert",
        },
        upsert_filter={"id": int(grade.id)},
        required=False,
    )
    mirror_document(
        "admin_audit_logs",
        {
            "action": "admin_student_grade_upsert",
            "grade_id": int(grade.id),
            "student_id": int(student.id),
            "registration_number": registration_number,
            "course_id": int(course.id),
            "course_code": course_code,
            "grade_letter": grade_letter,
            "grade_points": grade_points,
            "marks_percent": marks_percent,
            "remark": remark,
            "actor": {
                "user_id": int(current_user.id),
                "email": str(current_user.email or ""),
                "role": current_user.role.value,
            },
            "created_at": now_dt,
            "source": "admin",
        },
        required=False,
    )

    return _admin_student_grade_out(
        grade,
        student=student,
        course=course,
        faculty=faculty,
    )


@router.get("/grades/students/{registration_number}", response_model=schemas.AdminStudentGradeListOut)
def admin_list_student_grades(
    registration_number: str,
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    normalized_registration = _normalize_rms_registration_number(registration_number)
    student = (
        db.query(models.Student)
        .filter(func.upper(models.Student.registration_number) == normalized_registration)
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found for this registration number.")

    rows = (
        db.query(models.StudentGrade)
        .filter(models.StudentGrade.student_id == int(student.id))
        .order_by(models.StudentGrade.updated_at.desc(), models.StudentGrade.id.desc())
        .all()
    )
    if not rows:
        return schemas.AdminStudentGradeListOut(student=_admin_student_search_out(student), grades=[])

    course_ids = sorted({int(row.course_id) for row in rows})
    faculty_ids = sorted({int(row.faculty_id) for row in rows if row.faculty_id})
    courses = (
        db.query(models.Course)
        .filter(models.Course.id.in_(course_ids))
        .all()
        if course_ids
        else []
    )
    faculty_rows = (
        db.query(models.Faculty)
        .filter(models.Faculty.id.in_(faculty_ids))
        .all()
        if faculty_ids
        else []
    )
    course_map = {int(row.id): row for row in courses}
    faculty_map = {int(row.id): row for row in faculty_rows}
    grade_out = [
        _admin_student_grade_out(
            row,
            student=student,
            course=course_map.get(int(row.course_id)),
            faculty=faculty_map.get(int(row.faculty_id)) if row.faculty_id else None,
        )
        for row in rows
    ]
    return schemas.AdminStudentGradeListOut(
        student=_admin_student_search_out(student),
        grades=grade_out,
    )


@router.post("/bootstrap/departments/classrooms")
def bootstrap_department_classrooms(
    default_capacity: int = Query(
        default=DEPARTMENT_CLASSROOM_DEFAULT_CAPACITY,
        ge=20,
        le=250,
    ),
    replace_existing: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    payload = _bootstrap_department_classrooms(
        db,
        default_capacity=default_capacity,
        replace_existing=replace_existing,
        actor_email=str(getattr(user, "email", "") or "unknown"),
    )
    db.commit()
    return {
        "message": "Department classroom blueprint applied successfully.",
        **payload,
        "last_updated_at": datetime.utcnow(),
    }


def _coerce_case_status(raw_value: str | None) -> models.RMSCaseStatus | None:
    token = str(raw_value or "").strip().lower()
    if not token or token == "all":
        return None
    try:
        return models.RMSCaseStatus(token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid RMS case status filter.") from exc


def _coerce_case_priority(raw_value: str | None) -> models.RMSCasePriority | None:
    token = str(raw_value or "").strip().lower()
    if not token or token == "all":
        return None
    try:
        return models.RMSCasePriority(token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid RMS case priority filter.") from exc


def _safe_json_load_dict(raw_value: str | None) -> dict[str, Any]:
    raw = str(raw_value or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _safe_json_dump(value: dict[str, Any] | None) -> str:
    payload = value if isinstance(value, dict) else {}
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def _is_super_admin(current_user: models.AuthUser) -> bool:
    if current_user.role != models.UserRole.ADMIN:
        return False
    if not SUPER_ADMIN_EMAILS:
        return True
    return str(current_user.email or "").strip().lower() in SUPER_ADMIN_EMAILS


def _require_super_admin(current_user: models.AuthUser) -> None:
    if _is_super_admin(current_user):
        return
    raise HTTPException(
        status_code=403,
        detail="Super-admin privileges are required for governance operations.",
    )


def _load_policy(
    db: Session,
    *,
    key: str,
    default_value: dict[str, Any],
) -> tuple[models.AdminPolicySetting | None, dict[str, Any]]:
    row = db.query(models.AdminPolicySetting).filter(models.AdminPolicySetting.key == key).first()
    if not row:
        return None, dict(default_value)
    parsed = _safe_json_load_dict(row.value_json)
    if not parsed:
        return row, dict(default_value)
    merged = dict(default_value)
    merged.update(parsed)
    return row, merged


def _upsert_policy(
    db: Session,
    *,
    key: str,
    value: dict[str, Any],
    actor: models.AuthUser,
) -> models.AdminPolicySetting:
    now_dt = datetime.utcnow()
    row = db.query(models.AdminPolicySetting).filter(models.AdminPolicySetting.key == key).first()
    if row:
        row.value_json = _safe_json_dump(value)
        row.updated_by_user_id = int(actor.id)
        row.updated_at = now_dt
    else:
        row = models.AdminPolicySetting(
            key=key,
            value_json=_safe_json_dump(value),
            updated_by_user_id=int(actor.id),
            updated_at=now_dt,
        )
        db.add(row)
    db.flush()
    return row


def _rms_sla_policy(db: Session) -> dict[str, float]:
    _, policy = _load_policy(
        db,
        key="rms.case.sla",
        default_value={
            "first_response_hours": RMS_CASE_FIRST_RESPONSE_HOURS,
            "resolution_hours": RMS_CASE_RESOLUTION_HOURS,
        },
    )
    try:
        first_response_hours = max(1.0, float(policy.get("first_response_hours", RMS_CASE_FIRST_RESPONSE_HOURS)))
    except (TypeError, ValueError):
        first_response_hours = RMS_CASE_FIRST_RESPONSE_HOURS
    try:
        resolution_hours = max(2.0, float(policy.get("resolution_hours", RMS_CASE_RESOLUTION_HOURS)))
    except (TypeError, ValueError):
        resolution_hours = RMS_CASE_RESOLUTION_HOURS
    return {
        "first_response_hours": first_response_hours,
        "resolution_hours": resolution_hours,
    }


def _attendance_high_impact_policy(db: Session) -> dict[str, Any]:
    _, policy = _load_policy(
        db,
        key="rms.attendance.high_impact",
        default_value={
            "enabled": True,
            "retro_days": 3,
            "status_flip_to_present": True,
        },
    )
    enabled = bool(policy.get("enabled", True))
    try:
        retro_days = max(0, int(policy.get("retro_days", 3)))
    except (TypeError, ValueError):
        retro_days = 3
    status_flip = bool(policy.get("status_flip_to_present", True))
    return {
        "enabled": enabled,
        "retro_days": retro_days,
        "status_flip_to_present": status_flip,
    }


def _status_from_rms_action_marker(action: str | None) -> models.RMSCaseStatus | None:
    token = str(action or "").strip().lower()
    if token == schemas.RMSQueryWorkflowAction.APPROVE.value:
        return models.RMSCaseStatus.APPROVED
    if token == schemas.RMSQueryWorkflowAction.DISAPPROVE.value:
        return models.RMSCaseStatus.REJECTED
    if token == schemas.RMSQueryWorkflowAction.SCHEDULE.value:
        return models.RMSCaseStatus.ASSIGNED
    return None


def _priority_from_category(category: schemas.SupportQueryCategory) -> models.RMSCasePriority:
    if category == schemas.SupportQueryCategory.DISCREPANCY:
        return models.RMSCasePriority.HIGH
    if category == schemas.SupportQueryCategory.ATTENDANCE:
        return models.RMSCasePriority.MEDIUM
    return models.RMSCasePriority.LOW


def _log_rms_case_audit(
    db: Session,
    *,
    case_id: int,
    actor: models.AuthUser | None,
    action: str,
    from_status: models.RMSCaseStatus | None = None,
    to_status: models.RMSCaseStatus | None = None,
    note: str | None = None,
    evidence_ref: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> models.RMSCaseAuditLog:
    row = models.RMSCaseAuditLog(
        case_id=int(case_id),
        actor_user_id=int(actor.id) if actor else None,
        actor_role=(actor.role.value if actor else "system"),
        action=str(action),
        from_status=from_status,
        to_status=to_status,
        note=(str(note or "").strip() or None),
        evidence_ref=(str(evidence_ref or "").strip() or None),
        metadata_json=_safe_json_dump(metadata),
        created_at=datetime.utcnow(),
    )
    db.add(row)
    db.flush()
    return row


def _serialize_rms_case_out(
    case_row: models.RMSCase,
    *,
    student: models.Student | None = None,
    faculty: models.Faculty | None = None,
) -> schemas.RMSCaseOut:
    now_dt = datetime.utcnow()
    first_response_sla = None
    resolution_sla = None
    if case_row.first_response_due_at and case_row.first_responded_at is None:
        first_response_sla = int((case_row.first_response_due_at - now_dt).total_seconds())
    if case_row.resolution_due_at and case_row.closed_at is None:
        resolution_sla = int((case_row.resolution_due_at - now_dt).total_seconds())
    return schemas.RMSCaseOut(
        id=int(case_row.id),
        student_id=int(case_row.student_id),
        student_name=str(getattr(student, "name", "") or f"Student #{case_row.student_id}"),
        student_registration_number=(str(getattr(student, "registration_number", "") or "").strip().upper() or None),
        faculty_id=int(case_row.faculty_id) if case_row.faculty_id else None,
        faculty_name=(str(getattr(faculty, "name", "") or "").strip() or None),
        section=str(case_row.section or ""),
        category=_coerce_rms_category(case_row.category),
        subject=str(case_row.subject or "").strip() or "General Query",
        status=case_row.status,
        priority=case_row.priority,
        assigned_to_user_id=(int(case_row.assigned_to_user_id) if case_row.assigned_to_user_id else None),
        first_response_due_at=case_row.first_response_due_at,
        resolution_due_at=case_row.resolution_due_at,
        first_responded_at=case_row.first_responded_at,
        is_escalated=bool(case_row.is_escalated),
        escalated_at=case_row.escalated_at,
        escalation_reason=(str(case_row.escalation_reason or "").strip() or None),
        reopened_count=int(case_row.reopened_count or 0),
        last_message_at=case_row.last_message_at,
        closed_at=case_row.closed_at,
        sla_seconds_to_first_response=first_response_sla,
        sla_seconds_to_resolution=resolution_sla,
        updated_at=case_row.updated_at or now_dt,
        created_at=case_row.created_at or now_dt,
    )


def _serialize_rms_case_audit_out(row: models.RMSCaseAuditLog) -> schemas.RMSCaseAuditOut:
    return schemas.RMSCaseAuditOut(
        id=int(row.id),
        case_id=int(row.case_id),
        action=str(row.action or ""),
        actor_user_id=(int(row.actor_user_id) if row.actor_user_id else None),
        actor_role=(str(row.actor_role or "").strip() or None),
        from_status=row.from_status,
        to_status=row.to_status,
        note=(str(row.note or "").strip() or None),
        evidence_ref=(str(row.evidence_ref or "").strip() or None),
        metadata=_safe_json_load_dict(row.metadata_json),
        created_at=row.created_at or datetime.utcnow(),
    )


def _sync_rms_cases_from_threads(
    db: Session,
    *,
    student_id: int | None = None,
    limit: int = 1000,
) -> tuple[int, int]:
    query = db.query(models.SupportQueryMessage)
    if student_id is not None:
        query = query.filter(models.SupportQueryMessage.student_id == int(student_id))
    rows = (
        query.order_by(models.SupportQueryMessage.created_at.desc(), models.SupportQueryMessage.id.desc())
        .limit(max(50, min(int(limit), 5000)))
        .all()
    )
    if not rows:
        return 0, 0

    grouped_latest: dict[tuple[int, int, str, str], models.SupportQueryMessage] = {}
    for row in rows:
        category = _coerce_rms_category(row.category).value
        subject = str(row.subject or "").strip() or f"{category} Query"
        key = (int(row.student_id), int(row.faculty_id), category, subject)
        if key not in grouped_latest:
            grouped_latest[key] = row

    sla_policy = _rms_sla_policy(db)
    now_dt = datetime.utcnow()
    created = 0
    updated = 0
    for (student_key, faculty_key, category, subject), latest in grouped_latest.items():
        existing = (
            db.query(models.RMSCase)
            .filter(
                models.RMSCase.student_id == int(student_key),
                models.RMSCase.faculty_id == int(faculty_key),
                models.RMSCase.category == category,
                models.RMSCase.subject == subject,
                models.RMSCase.status != models.RMSCaseStatus.CLOSED,
            )
            .order_by(models.RMSCase.updated_at.desc(), models.RMSCase.id.desc())
            .first()
        )
        latest_action = _parse_rms_action_marker(str(latest.message or "").strip())
        marker_status = _status_from_rms_action_marker(latest_action["action"]) if latest_action else None

        if existing:
            has_change = False
            if latest.created_at and (not existing.last_message_at or latest.created_at > existing.last_message_at):
                existing.last_message_at = latest.created_at
                has_change = True
            if existing.section != str(latest.section or ""):
                existing.section = str(latest.section or "")
                has_change = True
            if marker_status and existing.status != marker_status:
                existing.status = marker_status
                if marker_status in {models.RMSCaseStatus.APPROVED, models.RMSCaseStatus.REJECTED}:
                    existing.closed_at = None
                has_change = True
            if has_change:
                existing.updated_at = now_dt
                if existing.first_responded_at is None and str(latest.sender_role or "").strip().lower() != models.UserRole.STUDENT.value:
                    existing.first_responded_at = latest.created_at or now_dt
                updated += 1
            continue

        category_enum = _coerce_rms_category(category)
        status_value = marker_status or models.RMSCaseStatus.NEW
        case_row = models.RMSCase(
            student_id=int(student_key),
            faculty_id=int(faculty_key),
            section=str(latest.section or "UNASSIGNED"),
            category=category_enum.value,
            subject=subject,
            status=status_value,
            priority=_priority_from_category(category_enum),
            assigned_to_user_id=None,
            created_from_message_id=int(latest.id),
            first_response_due_at=now_dt + timedelta(hours=float(sla_policy["first_response_hours"])),
            resolution_due_at=now_dt + timedelta(hours=float(sla_policy["resolution_hours"])),
            first_responded_at=(
                (latest.created_at or now_dt)
                if str(latest.sender_role or "").strip().lower() != models.UserRole.STUDENT.value
                else None
            ),
            last_message_at=latest.created_at or now_dt,
            is_escalated=False,
            closed_at=(now_dt if status_value == models.RMSCaseStatus.CLOSED else None),
            reopened_count=0,
            created_at=now_dt,
            updated_at=now_dt,
        )
        db.add(case_row)
        db.flush()
        _log_rms_case_audit(
            db,
            case_id=int(case_row.id),
            actor=None,
            action="case_created_from_thread",
            from_status=None,
            to_status=case_row.status,
            note="RMS case auto-created from support thread.",
            metadata={
                "message_id": int(latest.id),
                "category": category_enum.value,
            },
        )
        created += 1
    if created or updated:
        db.commit()
    return created, updated


def _assert_rms_case_scope(
    db: Session,
    *,
    case_row: models.RMSCase,
    current_user: models.AuthUser,
) -> None:
    if current_user.role != models.UserRole.FACULTY:
        return
    if not current_user.faculty_id:
        raise HTTPException(status_code=403, detail="Faculty account is not linked correctly.")
    faculty_id = int(current_user.faculty_id)
    if case_row.faculty_id and int(case_row.faculty_id) != faculty_id:
        raise HTTPException(status_code=403, detail="Faculty can only operate RMS cases in their own scope.")
    student = db.get(models.Student, int(case_row.student_id))
    if not _faculty_can_manage_student_rms(db, faculty_id=faculty_id, student=student):
        raise HTTPException(status_code=403, detail="Student is outside your allocated section(s) and teaching scope.")


def _apply_rms_case_transition(
    db: Session,
    *,
    case_row: models.RMSCase,
    action: schemas.RMSCaseAction,
    actor: models.AuthUser,
    note: str | None = None,
    evidence_ref: str | None = None,
    assign_to_user_id: int | None = None,
) -> bool:
    now_dt = datetime.utcnow()
    from_status = case_row.status
    to_status = case_row.status
    changed = False
    normalized_note = _normalize_rms_action_note(note)
    normalized_evidence = str(evidence_ref or "").strip() or None

    if action == schemas.RMSCaseAction.ESCALATE:
        if from_status == models.RMSCaseStatus.CLOSED:
            raise HTTPException(status_code=409, detail="Closed cases cannot be escalated.")
        if not case_row.is_escalated:
            case_row.is_escalated = True
            case_row.escalated_at = now_dt
            case_row.escalation_reason = normalized_note or "Manual escalation"
            changed = True
        _log_rms_case_audit(
            db,
            case_id=int(case_row.id),
            actor=actor,
            action="escalate",
            from_status=from_status,
            to_status=case_row.status,
            note=normalized_note,
            evidence_ref=normalized_evidence,
        )
        if changed:
            case_row.updated_at = now_dt
        return changed

    allowed_from: dict[schemas.RMSCaseAction, set[models.RMSCaseStatus]] = {
        schemas.RMSCaseAction.TRIAGE: {models.RMSCaseStatus.NEW},
        schemas.RMSCaseAction.ASSIGN: {models.RMSCaseStatus.TRIAGE},
        schemas.RMSCaseAction.APPROVE: {models.RMSCaseStatus.ASSIGNED},
        schemas.RMSCaseAction.REJECT: {models.RMSCaseStatus.ASSIGNED},
        schemas.RMSCaseAction.CLOSE: {models.RMSCaseStatus.APPROVED, models.RMSCaseStatus.REJECTED},
        schemas.RMSCaseAction.REOPEN: {
            models.RMSCaseStatus.CLOSED,
            models.RMSCaseStatus.APPROVED,
            models.RMSCaseStatus.REJECTED,
        },
    }
    if action in allowed_from and from_status not in allowed_from[action]:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Invalid lifecycle transition: cannot '{action.value}' "
                f"when case status is '{from_status.value}'."
            ),
        )

    if action == schemas.RMSCaseAction.ASSIGN:
        if assign_to_user_id is None:
            raise HTTPException(status_code=400, detail="assign_to_user_id is required for assign action.")
        normalized_assignee_id = int(assign_to_user_id)
        assignee = db.get(models.AuthUser, normalized_assignee_id)
        if (
            assignee is None
            and normalized_assignee_id == int(actor.id)
            and actor.role in {models.UserRole.ADMIN, models.UserRole.FACULTY}
            and bool(actor.is_active)
        ):
            assignee_is_active = True
            assignee_role = actor.role
            assignee_faculty_id = actor.faculty_id
            assignee_id = int(actor.id)
        else:
            if not assignee:
                raise HTTPException(status_code=404, detail="Assignee user was not found.")
            assignee_is_active = bool(assignee.is_active)
            assignee_role = assignee.role
            assignee_faculty_id = assignee.faculty_id
            assignee_id = int(assignee.id)

        if not assignee_is_active:
            raise HTTPException(status_code=409, detail="Assignee user is inactive.")
        if assignee_role not in {models.UserRole.ADMIN, models.UserRole.FACULTY}:
            raise HTTPException(status_code=400, detail="Assignee must be an admin or faculty user.")
        if actor.role == models.UserRole.FACULTY and assignee_id != int(actor.id):
            raise HTTPException(status_code=403, detail="Faculty can assign RMS cases only to themselves.")
        if assignee_role == models.UserRole.FACULTY and case_row.faculty_id:
            if not assignee_faculty_id or int(assignee_faculty_id) != int(case_row.faculty_id):
                raise HTTPException(
                    status_code=400,
                    detail="Faculty assignee must match the case's faculty ownership.",
                )
        case_row.assigned_to_user_id = assignee_id
        to_status = models.RMSCaseStatus.ASSIGNED
    elif action == schemas.RMSCaseAction.TRIAGE:
        to_status = models.RMSCaseStatus.TRIAGE
    elif action == schemas.RMSCaseAction.APPROVE:
        to_status = models.RMSCaseStatus.APPROVED
    elif action == schemas.RMSCaseAction.REJECT:
        to_status = models.RMSCaseStatus.REJECTED
    elif action == schemas.RMSCaseAction.CLOSE:
        to_status = models.RMSCaseStatus.CLOSED
    elif action == schemas.RMSCaseAction.REOPEN:
        to_status = models.RMSCaseStatus.NEW
    else:
        raise HTTPException(status_code=400, detail="Unsupported RMS case action.")

    if action == schemas.RMSCaseAction.REOPEN:
        case_row.closed_at = None
        case_row.reopened_count = int(case_row.reopened_count or 0) + 1
        case_row.is_escalated = False
        case_row.escalated_at = None
        case_row.escalation_reason = None
    elif to_status == models.RMSCaseStatus.CLOSED:
        case_row.closed_at = now_dt
    elif to_status in {models.RMSCaseStatus.APPROVED, models.RMSCaseStatus.REJECTED}:
        case_row.closed_at = None

    if case_row.status != to_status:
        case_row.status = to_status
        changed = True
    if case_row.first_responded_at is None and actor.role in {models.UserRole.ADMIN, models.UserRole.FACULTY}:
        case_row.first_responded_at = now_dt
    case_row.updated_at = now_dt
    _log_rms_case_audit(
        db,
        case_id=int(case_row.id),
        actor=actor,
        action=action.value,
        from_status=from_status,
        to_status=case_row.status,
        note=normalized_note,
        evidence_ref=normalized_evidence,
        metadata={"assign_to_user_id": int(assign_to_user_id) if assign_to_user_id else None},
    )
    return changed


def _get_or_create_rms_case_for_thread(
    db: Session,
    *,
    student: models.Student,
    faculty: models.Faculty,
    category: schemas.SupportQueryCategory,
    section: str,
    subject: str,
    actor: models.AuthUser,
    source_message_id: int | None = None,
) -> models.RMSCase:
    now_dt = datetime.utcnow()
    row = (
        db.query(models.RMSCase)
        .filter(
            models.RMSCase.student_id == int(student.id),
            models.RMSCase.faculty_id == int(faculty.id),
            models.RMSCase.category == category.value,
            models.RMSCase.subject == subject,
            models.RMSCase.status != models.RMSCaseStatus.CLOSED,
        )
        .order_by(models.RMSCase.updated_at.desc(), models.RMSCase.id.desc())
        .first()
    )
    if row:
        row.section = section
        row.last_message_at = now_dt
        row.updated_at = now_dt
        return row

    sla_policy = _rms_sla_policy(db)
    row = models.RMSCase(
        student_id=int(student.id),
        faculty_id=int(faculty.id),
        section=section,
        category=category.value,
        subject=subject,
        status=models.RMSCaseStatus.NEW,
        priority=_priority_from_category(category),
        assigned_to_user_id=None,
        created_from_message_id=int(source_message_id) if source_message_id else None,
        first_response_due_at=now_dt + timedelta(hours=float(sla_policy["first_response_hours"])),
        resolution_due_at=now_dt + timedelta(hours=float(sla_policy["resolution_hours"])),
        first_responded_at=None,
        last_message_at=now_dt,
        is_escalated=False,
        escalated_at=None,
        escalation_reason=None,
        closed_at=None,
        reopened_count=0,
        created_at=now_dt,
        updated_at=now_dt,
    )
    db.add(row)
    db.flush()
    _log_rms_case_audit(
        db,
        case_id=int(row.id),
        actor=actor,
        action="case_created",
        from_status=None,
        to_status=models.RMSCaseStatus.NEW,
        note="Case created from RMS thread action.",
        metadata={"source_message_id": int(source_message_id) if source_message_id else None},
    )
    return row


def _apply_legacy_query_action_to_case(
    db: Session,
    *,
    case_row: models.RMSCase,
    query_action: schemas.RMSQueryWorkflowAction,
    actor: models.AuthUser,
    note: str | None = None,
    assign_to_user_id: int | None = None,
) -> None:
    if query_action == schemas.RMSQueryWorkflowAction.SCHEDULE:
        if case_row.status == models.RMSCaseStatus.NEW:
            _apply_rms_case_transition(
                db,
                case_row=case_row,
                action=schemas.RMSCaseAction.TRIAGE,
                actor=actor,
                note="Auto-triage before scheduling from legacy RMS action.",
            )
        if case_row.status == models.RMSCaseStatus.TRIAGE:
            _apply_rms_case_transition(
                db,
                case_row=case_row,
                action=schemas.RMSCaseAction.ASSIGN,
                actor=actor,
                note=note,
                assign_to_user_id=assign_to_user_id or int(actor.id),
            )
        return

    decision_action = (
        schemas.RMSCaseAction.APPROVE
        if query_action == schemas.RMSQueryWorkflowAction.APPROVE
        else schemas.RMSCaseAction.REJECT
    )
    if case_row.status == models.RMSCaseStatus.NEW:
        _apply_rms_case_transition(
            db,
            case_row=case_row,
            action=schemas.RMSCaseAction.TRIAGE,
            actor=actor,
            note="Auto-triage before decision from legacy RMS action.",
        )
    if case_row.status == models.RMSCaseStatus.TRIAGE:
        _apply_rms_case_transition(
            db,
            case_row=case_row,
            action=schemas.RMSCaseAction.ASSIGN,
            actor=actor,
            note="Auto-assign before decision from legacy RMS action.",
            assign_to_user_id=assign_to_user_id or int(actor.id),
        )
    if case_row.status != models.RMSCaseStatus.ASSIGNED:
        return
    _apply_rms_case_transition(
        db,
        case_row=case_row,
        action=decision_action,
        actor=actor,
        note=note,
    )


def _serialize_correction_out(
    correction: models.RMSAttendanceCorrectionRequest,
    *,
    student: models.Student | None = None,
    course: models.Course | None = None,
    faculty: models.Faculty | None = None,
) -> schemas.RMSAttendanceCorrectionOut:
    return schemas.RMSAttendanceCorrectionOut(
        id=int(correction.id),
        student_id=int(correction.student_id),
        student_name=str(getattr(student, "name", "") or f"Student #{correction.student_id}"),
        registration_number=(str(getattr(student, "registration_number", "") or "").strip().upper() or None),
        course_id=int(correction.course_id),
        course_code=str(getattr(course, "code", "") or f"C-{correction.course_id}").strip().upper(),
        course_title=str(getattr(course, "title", "") or "Unknown Course"),
        faculty_id=int(correction.faculty_id),
        faculty_name=(str(getattr(faculty, "name", "") or "").strip() or None),
        attendance_date=correction.attendance_date,
        previous_status=correction.previous_status,
        requested_status=correction.requested_status,
        reason=str(correction.reason or "").strip(),
        evidence_ref=str(correction.evidence_ref or "").strip(),
        requested_by_user_id=int(correction.requested_by_user_id),
        requested_by_role=str(correction.requested_by_role or "").strip().lower(),
        status=correction.status,
        is_high_impact=bool(correction.is_high_impact),
        review_note=(str(correction.review_note or "").strip() or None),
        reviewed_by_user_id=(int(correction.reviewed_by_user_id) if correction.reviewed_by_user_id else None),
        reviewed_at=correction.reviewed_at,
        applied_record_id=(int(correction.applied_record_id) if correction.applied_record_id else None),
        applied_at=correction.applied_at,
        created_at=correction.created_at or datetime.utcnow(),
        updated_at=correction.updated_at or correction.created_at or datetime.utcnow(),
    )


def _is_high_impact_attendance_change(
    *,
    db: Session,
    previous_status: models.AttendanceStatus | None,
    requested_status: models.AttendanceStatus,
    attendance_date: date,
) -> bool:
    policy = _attendance_high_impact_policy(db)
    if not bool(policy.get("enabled", True)):
        return False
    if bool(policy.get("status_flip_to_present", True)):
        if requested_status == models.AttendanceStatus.PRESENT and previous_status != models.AttendanceStatus.PRESENT:
            return True
    retro_days = max(0, int(policy.get("retro_days", 3)))
    if retro_days > 0 and attendance_date < (date.today() - timedelta(days=retro_days)):
        return True
    return False


@router.get("/rms/cases", response_model=schemas.RMSCaseListOut)
def rms_list_cases(
    status: str = Query(default="all"),
    category: str = Query(default="all"),
    priority: str = Query(default="all"),
    escalated_only: bool = Query(default=False),
    queue_only: bool = Query(default=False),
    auto_sync: bool = Query(default=True),
    limit: int = Query(default=250, ge=20, le=1000),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    if auto_sync:
        _sync_rms_cases_from_threads(db, limit=max(500, int(limit) * 4))

    status_filter = _coerce_case_status(status)
    category_filter = _normalize_rms_category_filter(category)
    priority_filter = _coerce_case_priority(priority)

    query = db.query(models.RMSCase)
    if current_user.role == models.UserRole.FACULTY:
        if not current_user.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty account is not linked correctly.")
        query = query.filter(models.RMSCase.faculty_id == int(current_user.faculty_id))
    if status_filter is not None:
        query = query.filter(models.RMSCase.status == status_filter)
    if category_filter is not None:
        query = query.filter(models.RMSCase.category == category_filter.value)
    if priority_filter is not None:
        query = query.filter(models.RMSCase.priority == priority_filter)
    if escalated_only:
        query = query.filter(models.RMSCase.is_escalated.is_(True))
    if queue_only:
        query = query.filter(
            models.RMSCase.status.in_([models.RMSCaseStatus.NEW, models.RMSCaseStatus.TRIAGE]),
            models.RMSCase.assigned_to_user_id.is_(None),
        )

    rows = (
        query.order_by(models.RMSCase.is_escalated.desc(), models.RMSCase.updated_at.desc(), models.RMSCase.id.desc())
        .limit(int(limit))
        .all()
    )
    if not rows:
        return schemas.RMSCaseListOut(total=0, pending_queue=0, escalated=0, cases=[])

    student_ids = sorted({int(row.student_id) for row in rows})
    faculty_ids = sorted({int(row.faculty_id) for row in rows if row.faculty_id})
    student_map = (
        {int(row.id): row for row in db.query(models.Student).filter(models.Student.id.in_(student_ids)).all()}
        if student_ids
        else {}
    )
    faculty_map = (
        {int(row.id): row for row in db.query(models.Faculty).filter(models.Faculty.id.in_(faculty_ids)).all()}
        if faculty_ids
        else {}
    )

    payload = [
        _serialize_rms_case_out(
            row,
            student=student_map.get(int(row.student_id)),
            faculty=faculty_map.get(int(row.faculty_id)) if row.faculty_id else None,
        )
        for row in rows
    ]
    pending_queue = sum(
        1
        for row in rows
        if row.status in {models.RMSCaseStatus.NEW, models.RMSCaseStatus.TRIAGE}
        and row.assigned_to_user_id is None
    )
    escalated = sum(1 for row in rows if row.is_escalated)
    return schemas.RMSCaseListOut(
        total=len(payload),
        pending_queue=pending_queue,
        escalated=escalated,
        cases=payload,
    )


@router.get("/rms/cases/assignment-queue", response_model=schemas.RMSCaseListOut)
def rms_assignment_queue(
    limit: int = Query(default=250, ge=20, le=1000),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    return rms_list_cases(
        status="all",
        category="all",
        priority="all",
        escalated_only=False,
        queue_only=True,
        auto_sync=True,
        limit=limit,
        db=db,
        current_user=current_user,
    )


@router.post("/rms/cases/{case_id}/transition", response_model=schemas.RMSCaseOut)
def rms_transition_case(
    case_id: int,
    payload: schemas.RMSCaseTransitionRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    row = db.get(models.RMSCase, int(case_id))
    if not row:
        raise HTTPException(status_code=404, detail="RMS case not found.")
    _assert_rms_case_scope(db, case_row=row, current_user=current_user)

    changed = _apply_rms_case_transition(
        db,
        case_row=row,
        action=payload.action,
        actor=current_user,
        note=payload.note,
        evidence_ref=payload.evidence_ref,
        assign_to_user_id=payload.assign_to_user_id,
    )
    db.commit()
    db.refresh(row)

    mirror_document(
        "admin_audit_logs",
        {
            "action": "rms_case_transition",
            "case_id": int(row.id),
            "workflow_action": payload.action.value,
            "changed": bool(changed),
            "status": row.status.value,
            "assigned_to_user_id": int(row.assigned_to_user_id) if row.assigned_to_user_id else None,
            "actor": {
                "user_id": int(current_user.id),
                "faculty_id": int(current_user.faculty_id) if current_user.faculty_id else None,
                "email": str(current_user.email or ""),
                "role": current_user.role.value,
            },
            "created_at": datetime.utcnow(),
            "source": "rms-case",
        },
        required=False,
    )

    student = db.get(models.Student, int(row.student_id))
    faculty = db.get(models.Faculty, int(row.faculty_id)) if row.faculty_id else None
    return _serialize_rms_case_out(row, student=student, faculty=faculty)


@router.post("/rms/cases/bulk-transition", response_model=schemas.RMSCaseBulkTransitionOut)
def rms_bulk_transition_cases(
    payload: schemas.RMSCaseBulkTransitionRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    case_ids = sorted({int(item) for item in payload.case_ids if int(item) > 0})
    if not case_ids:
        raise HTTPException(status_code=400, detail="No valid case IDs provided.")

    rows = db.query(models.RMSCase).filter(models.RMSCase.id.in_(case_ids)).all()
    by_id = {int(row.id): row for row in rows}
    updated_ids: list[int] = []
    skipped = 0

    for case_id in case_ids:
        row = by_id.get(int(case_id))
        if row is None:
            skipped += 1
            continue
        try:
            _assert_rms_case_scope(db, case_row=row, current_user=current_user)
            changed = _apply_rms_case_transition(
                db,
                case_row=row,
                action=payload.action,
                actor=current_user,
                note=payload.note,
                assign_to_user_id=payload.assign_to_user_id,
            )
            if changed or payload.action == schemas.RMSCaseAction.ESCALATE:
                updated_ids.append(int(row.id))
            else:
                skipped += 1
        except HTTPException:
            skipped += 1

    db.commit()
    return schemas.RMSCaseBulkTransitionOut(
        requested=len(case_ids),
        updated=len(updated_ids),
        skipped=skipped,
        updated_case_ids=updated_ids,
    )


@router.post("/rms/cases/escalate-expired")
def rms_escalate_expired_cases(
    limit: int = Query(default=1000, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    now_dt = datetime.utcnow() - timedelta(minutes=RMS_CASE_ESCALATION_GRACE_MINUTES)
    rows = (
        db.query(models.RMSCase)
        .filter(
            models.RMSCase.status != models.RMSCaseStatus.CLOSED,
            models.RMSCase.is_escalated.is_(False),
        )
        .order_by(models.RMSCase.updated_at.asc(), models.RMSCase.id.asc())
        .limit(int(limit))
        .all()
    )

    updated_ids: list[int] = []
    for row in rows:
        first_response_breached = bool(
            row.first_response_due_at and row.first_responded_at is None and row.first_response_due_at < now_dt
        )
        resolution_breached = bool(row.resolution_due_at and row.resolution_due_at < now_dt and row.closed_at is None)
        if not first_response_breached and not resolution_breached:
            continue
        reason = "SLA breach: first response overdue." if first_response_breached else "SLA breach: resolution overdue."
        row.is_escalated = True
        row.escalated_at = datetime.utcnow()
        row.escalation_reason = reason
        row.updated_at = datetime.utcnow()
        _log_rms_case_audit(
            db,
            case_id=int(row.id),
            actor=current_user,
            action="auto_escalate",
            from_status=row.status,
            to_status=row.status,
            note=reason,
        )
        updated_ids.append(int(row.id))

    db.commit()
    return {
        "escalated": len(updated_ids),
        "case_ids": updated_ids,
        "checked": len(rows),
        "message": "Escalation sweep completed.",
        "created_at": datetime.utcnow(),
    }


@router.get("/rms/cases/{case_id}/audit", response_model=schemas.RMSCaseTimelineOut)
def rms_case_audit_timeline(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    row = db.get(models.RMSCase, int(case_id))
    if not row:
        raise HTTPException(status_code=404, detail="RMS case not found.")
    _assert_rms_case_scope(db, case_row=row, current_user=current_user)

    student = db.get(models.Student, int(row.student_id))
    faculty = db.get(models.Faculty, int(row.faculty_id)) if row.faculty_id else None
    case_out = _serialize_rms_case_out(row, student=student, faculty=faculty)
    logs = (
        db.query(models.RMSCaseAuditLog)
        .filter(models.RMSCaseAuditLog.case_id == int(row.id))
        .order_by(models.RMSCaseAuditLog.created_at.asc(), models.RMSCaseAuditLog.id.asc())
        .all()
    )
    return schemas.RMSCaseTimelineOut(
        case=case_out,
        timeline=[_serialize_rms_case_audit_out(item) for item in logs],
    )


@router.post("/rms/attendance/corrections", response_model=schemas.RMSAttendanceCorrectionOut)
def rms_create_attendance_correction(
    payload: schemas.RMSAttendanceCorrectionCreateRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    registration_number = _normalize_rms_registration_number(payload.registration_number)
    student = (
        db.query(models.Student)
        .filter(func.upper(models.Student.registration_number) == registration_number)
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found for this registration number.")

    course_code = _normalize_admin_course_code(payload.course_code)
    course = db.query(models.Course).filter(func.upper(models.Course.code) == course_code).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found for this course code.")
    if not course.faculty_id:
        raise HTTPException(status_code=409, detail="Course does not have an assigned faculty.")

    if current_user.role == models.UserRole.FACULTY:
        if not current_user.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty account is not linked correctly.")
        if int(course.faculty_id) != int(current_user.faculty_id):
            raise HTTPException(status_code=403, detail="Faculty can create corrections only for their assigned course.")
        if not _faculty_can_manage_student_rms(db, faculty_id=int(current_user.faculty_id), student=student):
            raise HTTPException(status_code=403, detail="Student is outside your allocated section(s) and teaching scope.")

    enrollment = (
        db.query(models.Enrollment)
        .filter(
            models.Enrollment.student_id == int(student.id),
            models.Enrollment.course_id == int(course.id),
        )
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=409, detail="Student is not enrolled in this course.")

    reason = str(payload.reason or "").strip()
    evidence_ref = str(payload.evidence_ref or "").strip()
    if len(reason) < 10:
        raise HTTPException(status_code=400, detail="reason must be at least 10 characters.")
    if len(evidence_ref) < 10:
        raise HTTPException(status_code=400, detail="evidence_ref must be at least 10 characters.")

    previous_status = _resolve_student_course_attendance_status(
        db,
        student_id=int(student.id),
        course_id=int(course.id),
        attendance_date=payload.attendance_date,
    )
    is_high_impact = _is_high_impact_attendance_change(
        db=db,
        previous_status=previous_status,
        requested_status=payload.requested_status,
        attendance_date=payload.attendance_date,
    )
    status_value = models.RMSAttendanceCorrectionStatus.PENDING_ADMIN_APPROVAL
    if current_user.role == models.UserRole.ADMIN or not is_high_impact:
        status_value = models.RMSAttendanceCorrectionStatus.APPROVED

    now_dt = datetime.utcnow()
    correction = models.RMSAttendanceCorrectionRequest(
        student_id=int(student.id),
        faculty_id=int(course.faculty_id),
        course_id=int(course.id),
        attendance_date=payload.attendance_date,
        requested_status=payload.requested_status,
        previous_status=previous_status,
        reason=reason,
        evidence_ref=evidence_ref,
        requested_by_user_id=int(current_user.id),
        requested_by_role=current_user.role.value,
        status=status_value,
        review_note=None,
        reviewed_by_user_id=None,
        reviewed_at=None,
        applied_record_id=None,
        applied_at=None,
        is_high_impact=is_high_impact,
        created_at=now_dt,
        updated_at=now_dt,
    )
    db.add(correction)
    db.commit()
    db.refresh(correction)

    if correction.status == models.RMSAttendanceCorrectionStatus.APPROVED:
        attendance_out = rms_update_attendance_status(
            payload=schemas.RMSAttendanceStatusUpdateRequest(
                registration_number=registration_number,
                course_code=course_code,
                attendance_date=payload.attendance_date,
                status=payload.requested_status,
                note=reason,
            ),
            db=db,
            current_user=current_user,
        )
        correction.status = models.RMSAttendanceCorrectionStatus.APPLIED
        correction.review_note = reason
        correction.reviewed_by_user_id = int(current_user.id)
        correction.reviewed_at = datetime.utcnow()
        correction.applied_record_id = int(attendance_out.record_id)
        correction.applied_at = datetime.utcnow()
        correction.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(correction)

    mirror_document(
        "rms_attendance_corrections",
        {
            "id": int(correction.id),
            "student_id": int(correction.student_id),
            "faculty_id": int(correction.faculty_id),
            "course_id": int(correction.course_id),
            "attendance_date": correction.attendance_date.isoformat(),
            "previous_status": correction.previous_status.value if correction.previous_status else None,
            "requested_status": correction.requested_status.value,
            "reason": correction.reason,
            "evidence_ref": correction.evidence_ref[:300],
            "requested_by_user_id": int(correction.requested_by_user_id),
            "requested_by_role": correction.requested_by_role,
            "status": correction.status.value,
            "is_high_impact": bool(correction.is_high_impact),
            "review_note": correction.review_note,
            "reviewed_by_user_id": correction.reviewed_by_user_id,
            "reviewed_at": correction.reviewed_at,
            "applied_record_id": correction.applied_record_id,
            "applied_at": correction.applied_at,
            "created_at": correction.created_at,
            "updated_at": correction.updated_at,
            "source": "rms-attendance-correction",
        },
        upsert_filter={"id": int(correction.id)},
        required=False,
    )
    faculty = db.get(models.Faculty, int(correction.faculty_id))
    return _serialize_correction_out(correction, student=student, course=course, faculty=faculty)


@router.get("/rms/attendance/corrections", response_model=schemas.RMSAttendanceCorrectionListOut)
def rms_list_attendance_corrections(
    status: str = Query(default="all"),
    limit: int = Query(default=200, ge=10, le=1000),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    token = str(status or "").strip().lower()
    status_filter = None
    if token and token != "all":
        try:
            status_filter = models.RMSAttendanceCorrectionStatus(token)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid correction status filter.") from exc

    query = db.query(models.RMSAttendanceCorrectionRequest)
    if current_user.role == models.UserRole.FACULTY:
        if not current_user.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty account is not linked correctly.")
        query = query.filter(models.RMSAttendanceCorrectionRequest.faculty_id == int(current_user.faculty_id))
    if status_filter is not None:
        query = query.filter(models.RMSAttendanceCorrectionRequest.status == status_filter)

    rows = (
        query.order_by(
            models.RMSAttendanceCorrectionRequest.created_at.desc(),
            models.RMSAttendanceCorrectionRequest.id.desc(),
        )
        .limit(int(limit))
        .all()
    )
    if not rows:
        return schemas.RMSAttendanceCorrectionListOut(total=0, pending=0, requests=[])

    student_ids = sorted({int(row.student_id) for row in rows})
    course_ids = sorted({int(row.course_id) for row in rows})
    faculty_ids = sorted({int(row.faculty_id) for row in rows})
    student_map = (
        {int(row.id): row for row in db.query(models.Student).filter(models.Student.id.in_(student_ids)).all()}
        if student_ids
        else {}
    )
    course_map = (
        {int(row.id): row for row in db.query(models.Course).filter(models.Course.id.in_(course_ids)).all()}
        if course_ids
        else {}
    )
    faculty_map = (
        {int(row.id): row for row in db.query(models.Faculty).filter(models.Faculty.id.in_(faculty_ids)).all()}
        if faculty_ids
        else {}
    )
    request_out = [
        _serialize_correction_out(
            row,
            student=student_map.get(int(row.student_id)),
            course=course_map.get(int(row.course_id)),
            faculty=faculty_map.get(int(row.faculty_id)),
        )
        for row in rows
    ]
    pending = sum(1 for row in rows if row.status == models.RMSAttendanceCorrectionStatus.PENDING_ADMIN_APPROVAL)
    return schemas.RMSAttendanceCorrectionListOut(total=len(rows), pending=pending, requests=request_out)


@router.post("/rms/attendance/corrections/{request_id}/review", response_model=schemas.RMSAttendanceCorrectionOut)
def rms_review_attendance_correction(
    request_id: int,
    payload: schemas.RMSAttendanceCorrectionReviewRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    correction = db.get(models.RMSAttendanceCorrectionRequest, int(request_id))
    if not correction:
        raise HTTPException(status_code=404, detail="Attendance correction request not found.")
    if correction.status != models.RMSAttendanceCorrectionStatus.PENDING_ADMIN_APPROVAL:
        raise HTTPException(status_code=409, detail="Only pending correction requests can be reviewed.")

    review_note = _normalize_rms_action_note(payload.review_note) or correction.reason
    correction.review_note = review_note
    correction.reviewed_by_user_id = int(current_user.id)
    correction.reviewed_at = datetime.utcnow()
    correction.updated_at = datetime.utcnow()

    student = db.get(models.Student, int(correction.student_id))
    course = db.get(models.Course, int(correction.course_id))
    if not student or not course:
        raise HTTPException(status_code=404, detail="Student or course linked to correction no longer exists.")

    if payload.action == schemas.RMSAttendanceCorrectionReviewAction.REJECT:
        correction.status = models.RMSAttendanceCorrectionStatus.REJECTED
        db.commit()
        db.refresh(correction)
    else:
        attendance_out = rms_update_attendance_status(
            payload=schemas.RMSAttendanceStatusUpdateRequest(
                registration_number=(str(student.registration_number or "").strip().upper()),
                course_code=(str(course.code or "").strip().upper()),
                attendance_date=correction.attendance_date,
                status=correction.requested_status,
                note=review_note,
            ),
            db=db,
            current_user=current_user,
        )
        correction.status = models.RMSAttendanceCorrectionStatus.APPLIED
        correction.applied_record_id = int(attendance_out.record_id)
        correction.applied_at = datetime.utcnow()
        correction.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(correction)

    mirror_document(
        "admin_audit_logs",
        {
            "action": "rms_attendance_correction_review",
            "request_id": int(correction.id),
            "decision": payload.action.value,
            "status": correction.status.value,
            "review_note": review_note,
            "actor": {
                "user_id": int(current_user.id),
                "email": str(current_user.email or ""),
                "role": current_user.role.value,
            },
            "created_at": datetime.utcnow(),
            "source": "rms-attendance-correction",
        },
        required=False,
    )
    faculty = db.get(models.Faculty, int(correction.faculty_id))
    return _serialize_correction_out(correction, student=student, course=course, faculty=faculty)


@router.get("/governance/policies", response_model=list[schemas.GovernancePolicyOut])
def governance_list_policies(
    key: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    _require_super_admin(current_user)
    query = db.query(models.AdminPolicySetting)
    if key:
        query = query.filter(models.AdminPolicySetting.key == str(key).strip())
    rows = query.order_by(models.AdminPolicySetting.key.asc()).all()
    return [
        schemas.GovernancePolicyOut(
            key=str(row.key),
            value=_safe_json_load_dict(row.value_json),
            updated_by_user_id=(int(row.updated_by_user_id) if row.updated_by_user_id else None),
            updated_at=row.updated_at or datetime.utcnow(),
        )
        for row in rows
    ]


@router.put("/governance/policies/{policy_key}", response_model=schemas.GovernancePolicyOut)
def governance_upsert_policy(
    policy_key: str,
    payload: schemas.GovernancePolicyUpsertRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    _require_super_admin(current_user)
    key = re.sub(r"\s+", "", str(policy_key or "").strip().lower())
    if len(key) < 3:
        raise HTTPException(status_code=400, detail="policy_key must be at least 3 characters.")
    row = _upsert_policy(
        db,
        key=key,
        value=dict(payload.value or {}),
        actor=current_user,
    )
    db.commit()
    db.refresh(row)
    mirror_document(
        "admin_audit_logs",
        {
            "action": "governance_policy_upsert",
            "policy_key": key,
            "value": dict(payload.value or {}),
            "actor": {
                "user_id": int(current_user.id),
                "email": str(current_user.email or ""),
                "role": current_user.role.value,
            },
            "created_at": datetime.utcnow(),
            "source": "governance",
        },
        required=False,
    )
    return schemas.GovernancePolicyOut(
        key=str(row.key),
        value=_safe_json_load_dict(row.value_json),
        updated_by_user_id=(int(row.updated_by_user_id) if row.updated_by_user_id else None),
        updated_at=row.updated_at or datetime.utcnow(),
    )


@router.post("/governance/roles/delegate", response_model=schemas.GovernanceRoleDelegationOut)
def governance_delegate_role(
    payload: schemas.GovernanceRoleDelegationRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    _require_super_admin(current_user)
    target_user = db.get(models.AuthUser, int(payload.target_user_id))
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found.")

    from_role = target_user.role
    target_user.role = payload.target_role
    log_row = models.RoleDelegationLog(
        target_user_id=int(target_user.id),
        from_role=from_role,
        to_role=payload.target_role,
        delegated_by_user_id=int(current_user.id),
        reason=(str(payload.reason or "").strip() or None),
        created_at=datetime.utcnow(),
    )
    db.add(log_row)
    db.commit()
    db.refresh(log_row)

    mirror_document(
        "admin_audit_logs",
        {
            "action": "governance_role_delegation",
            "target_user_id": int(target_user.id),
            "from_role": from_role.value if from_role else None,
            "to_role": payload.target_role.value,
            "reason": str(payload.reason or "").strip() or None,
            "actor": {
                "user_id": int(current_user.id),
                "email": str(current_user.email or ""),
                "role": current_user.role.value,
            },
            "created_at": datetime.utcnow(),
            "source": "governance",
        },
        required=False,
    )
    return schemas.GovernanceRoleDelegationOut(
        target_user_id=int(log_row.target_user_id),
        from_role=log_row.from_role,
        to_role=log_row.to_role,
        delegated_by_user_id=int(log_row.delegated_by_user_id),
        reason=(str(log_row.reason or "").strip() or None),
        created_at=log_row.created_at or datetime.utcnow(),
    )


@router.post("/governance/break-glass", response_model=schemas.GovernanceBreakGlassLogOut)
def governance_break_glass_access(
    payload: schemas.GovernanceBreakGlassRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    _require_super_admin(current_user)
    now_dt = datetime.utcnow()
    expires_at = None
    if payload.expires_in_minutes:
        expires_at = now_dt + timedelta(minutes=int(payload.expires_in_minutes))
    row = models.BreakGlassAccessLog(
        actor_user_id=int(current_user.id),
        actor_email=str(current_user.email or ""),
        scope=str(payload.scope or "global").strip(),
        reason=str(payload.reason or "").strip(),
        ticket_ref=(str(payload.ticket_ref or "").strip() or None),
        expires_at=expires_at,
        resolved_at=None,
        created_at=now_dt,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    mirror_document(
        "admin_audit_logs",
        {
            "action": "governance_break_glass_opened",
            "break_glass_id": int(row.id),
            "scope": row.scope,
            "reason": row.reason,
            "ticket_ref": row.ticket_ref,
            "expires_at": row.expires_at,
            "actor": {
                "user_id": int(current_user.id),
                "email": str(current_user.email or ""),
                "role": current_user.role.value,
            },
            "created_at": now_dt,
            "source": "governance",
        },
        required=False,
    )
    return schemas.GovernanceBreakGlassLogOut(
        id=int(row.id),
        actor_user_id=int(row.actor_user_id),
        actor_email=str(row.actor_email or ""),
        reason=str(row.reason or ""),
        scope=str(row.scope or "global"),
        ticket_ref=(str(row.ticket_ref or "").strip() or None),
        expires_at=row.expires_at,
        resolved_at=row.resolved_at,
        created_at=row.created_at or now_dt,
    )


@router.get("/governance/break-glass/logs", response_model=schemas.GovernanceBreakGlassListOut)
def governance_break_glass_logs(
    limit: int = Query(default=200, ge=10, le=1000),
    active_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    _require_super_admin(current_user)
    query = db.query(models.BreakGlassAccessLog)
    if active_only:
        query = query.filter(models.BreakGlassAccessLog.resolved_at.is_(None))
    rows = (
        query.order_by(models.BreakGlassAccessLog.created_at.desc(), models.BreakGlassAccessLog.id.desc())
        .limit(int(limit))
        .all()
    )
    logs = [
        schemas.GovernanceBreakGlassLogOut(
            id=int(row.id),
            actor_user_id=int(row.actor_user_id),
            actor_email=str(row.actor_email or ""),
            reason=str(row.reason or ""),
            scope=str(row.scope or "global"),
            ticket_ref=(str(row.ticket_ref or "").strip() or None),
            expires_at=row.expires_at,
            resolved_at=row.resolved_at,
            created_at=row.created_at or datetime.utcnow(),
        )
        for row in rows
    ]
    return schemas.GovernanceBreakGlassListOut(total=len(logs), logs=logs)
