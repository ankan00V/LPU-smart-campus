import hashlib
import json
import logging
import math
import os
import re
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pymongo.errors import DuplicateKeyError
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .. import models, schemas
from ..attendance_recovery import (
    evaluate_attendance_recovery,
    get_admin_recovery_plans,
    get_faculty_recovery_plans,
    get_student_recovery_plans,
    get_plan_actions,
    recompute_attendance_recovery_scope,
    update_student_recovery_action,
)
from ..attendance_ledger import append_event_and_recompute, recompute_attendance_scope
from ..auth_utils import get_current_user, require_roles
from ..database import get_db
from ..default_timetable import DEFAULT_TIMETABLE_BLUEPRINT
from ..enterprise_controls import apply_pii_encryption_policy
from ..face_verification import (
    build_enrollment_template_from_frames,
    build_profile_face_template,
    verify_face_sequence_opencv,
)
from ..identity_shield import run_student_enrollment_screening
from ..media_storage import (
    data_url_for_object,
    mark_media_deleted,
    signed_url_for_object,
    store_data_url_object,
)
from ..mongo import get_mongo_db, mirror_document
from ..realtime_bus import publish_domain_event
from ..saarthi_service import materialize_saarthi_attendance
from ..workers import enqueue_face_reverification, enqueue_recompute

router = APIRouter(prefix="/attendance", tags=["Attendance Management"])
logger = logging.getLogger(__name__)

PROFILE_PHOTO_LOCK_DAYS = 14
PROFILE_PHOTO_LOCK_MESSAGE = "Profile photo can only be changed once every 14 days. Please try again later."
ENROLLMENT_VIDEO_LOCK_DAYS = 14
ENROLLMENT_VIDEO_LOCK_MESSAGE = "Enrollment video can only be updated once every 14 days. Please try again later."
REGISTRATION_IMMUTABLE_MESSAGE = (
    "Registration number is permanent and can't be changed without admin permissions."
)
FACULTY_PHOTO_LOCK_DAYS = 14
FACULTY_PHOTO_LOCK_MESSAGE = "Faculty profile photo can only be changed once every 14 days. Please try again later."
FACULTY_SECTION_LOCK_MINUTES = 24 * 60
STUDENT_SECTION_LOCK_MINUTES = 48 * 60
FACULTY_ID_IMMUTABLE_MESSAGE = (
    "Faculty ID is permanent and can't be changed without admin permissions."
)
PROFILE_NAME_IMMUTABLE_MESSAGE = (
    "Full name can be set once from profile setup and then changed only by admin."
)
FACE_MATCH_PASS_THRESHOLD = max(
    0.80,
    min(0.99, float(os.getenv("FACE_MATCH_PASS_THRESHOLD", "0.80"))),
)
FACE_MULTI_FRAME_MIN = max(5, int(os.getenv("FACE_MATCH_MIN_FRAMES", "6")))
PROFILE_MEDIA_RETENTION_DAYS = max(30, int(os.getenv("PROFILE_MEDIA_RETENTION_DAYS", "365")))
ATTENDANCE_MEDIA_RETENTION_DAYS = max(7, int(os.getenv("ATTENDANCE_MEDIA_RETENTION_DAYS", "120")))
ACADEMIC_START_DATE_DEFAULT = "2026-03-02"
STUDENT_SECTION_PATTERN = re.compile(r"^[A-Z0-9-_/]+$")


def _academic_start_date() -> date:
    raw = (os.getenv("ACADEMIC_START_DATE", ACADEMIC_START_DATE_DEFAULT) or "").strip()
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return date.fromisoformat(ACADEMIC_START_DATE_DEFAULT)


def _parse_recovery_action_metadata(raw_value: str | None) -> dict[str, object]:
    if not raw_value:
        return {}
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _serialize_recovery_plan_rows(
    db: Session,
    plans: list[models.AttendanceRecoveryPlan],
) -> list[schemas.AttendanceRecoveryPlanOut]:
    if not plans:
        return []

    student_ids = {int(plan.student_id) for plan in plans}
    course_ids = {int(plan.course_id) for plan in plans}
    faculty_ids = {int(plan.faculty_id) for plan in plans if plan.faculty_id}
    makeup_class_ids = {int(plan.recommended_makeup_class_id) for plan in plans if plan.recommended_makeup_class_id}
    plan_ids = [int(plan.id) for plan in plans]

    students = {
        int(row.id): row
        for row in db.query(models.Student).filter(models.Student.id.in_(student_ids)).all()
    }
    courses = {
        int(row.id): row
        for row in db.query(models.Course).filter(models.Course.id.in_(course_ids)).all()
    }
    faculty_ids.update(int(course.faculty_id) for course in courses.values() if course.faculty_id)
    faculties = {
        int(row.id): row
        for row in db.query(models.Faculty).filter(models.Faculty.id.in_(faculty_ids)).all()
    } if faculty_ids else {}
    makeup_classes = {
        int(row.id): row
        for row in db.query(models.MakeUpClass).filter(models.MakeUpClass.id.in_(makeup_class_ids)).all()
    } if makeup_class_ids else {}
    actions_by_plan: dict[int, list[models.AttendanceRecoveryAction]] = {}
    if plan_ids:
        action_rows = (
            db.query(models.AttendanceRecoveryAction)
            .filter(models.AttendanceRecoveryAction.plan_id.in_(plan_ids))
            .order_by(
                models.AttendanceRecoveryAction.scheduled_for.asc(),
                models.AttendanceRecoveryAction.id.asc(),
            )
            .all()
        )
        for action in action_rows:
            actions_by_plan.setdefault(int(action.plan_id), []).append(action)

    out: list[schemas.AttendanceRecoveryPlanOut] = []
    for plan in plans:
        course = courses.get(int(plan.course_id))
        student = students.get(int(plan.student_id))
        faculty = faculties.get(int(plan.faculty_id or 0))
        if faculty is None and course is not None and course.faculty_id:
            faculty = faculties.get(int(course.faculty_id))
        makeup_class = makeup_classes.get(int(plan.recommended_makeup_class_id or 0))
        actions = [
            schemas.AttendanceRecoveryActionOut(
                id=int(action.id),
                action_type=action.action_type,
                status=action.status,
                title=action.title,
                description=action.description,
                recipient_role=action.recipient_role,
                recipient_user_id=action.recipient_user_id,
                recipient_email=action.recipient_email,
                target_makeup_class_id=action.target_makeup_class_id,
                scheduled_for=action.scheduled_for,
                completed_at=action.completed_at,
                outcome_note=action.outcome_note,
                metadata=_parse_recovery_action_metadata(action.metadata_json),
            )
            for action in actions_by_plan.get(int(plan.id), [])
        ]
        out.append(
            schemas.AttendanceRecoveryPlanOut(
                id=int(plan.id),
                student_id=int(plan.student_id),
                student_name=student.name if student else f"Student {plan.student_id}",
                registration_number=student.registration_number if student else None,
                section=student.section if student else None,
                course_id=int(plan.course_id),
                course_code=course.code if course else f"C-{plan.course_id}",
                course_title=course.title if course else "Unknown Course",
                faculty_id=int(plan.faculty_id) if plan.faculty_id else (int(course.faculty_id) if course and course.faculty_id else None),
                faculty_name=faculty.name if faculty else None,
                risk_level=plan.risk_level,
                status=plan.status,
                attendance_percent=float(plan.attendance_percent or 0.0),
                present_count=int(plan.present_count or 0),
                absent_count=int(plan.absent_count or 0),
                delivered_count=int(plan.delivered_count or 0),
                consecutive_absences=int(plan.consecutive_absences or 0),
                missed_remedials=int(plan.missed_remedials or 0),
                parent_alert_allowed=bool(plan.parent_alert_allowed),
                recovery_due_at=plan.recovery_due_at,
                summary=plan.summary,
                last_absent_on=plan.last_absent_on,
                last_evaluated_at=plan.last_evaluated_at,
                recommended_makeup_class=(
                    schemas.AttendanceRecoverySuggestedClassOut(
                        makeup_class_id=int(makeup_class.id),
                        class_date=makeup_class.class_date,
                        start_time=makeup_class.start_time,
                        end_time=makeup_class.end_time,
                        topic=makeup_class.topic,
                        class_mode=makeup_class.class_mode,
                        room_number=makeup_class.room_number,
                        online_link=makeup_class.online_link,
                    )
                    if makeup_class is not None
                    else None
                ),
                actions=actions,
            )
        )
    return out


def _time_from_hhmm(value: str) -> time:
    parts = value.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid HH:MM time format: {value}")
    return time(hour=int(parts[0]), minute=int(parts[1]))


def _client_ai_verdict(payload: schemas.RealtimeAttendanceMarkRequest) -> dict | None:
    if payload.ai_match is None or payload.ai_confidence is None:
        return None
    confidence = max(0.0, min(1.0, float(payload.ai_confidence)))
    return {
        "available": True,
        "match": bool(payload.ai_match),
        "confidence": confidence,
        "engine": payload.ai_model or "ai-client",
        "reason": payload.ai_reason or "Client AI verdict",
    }


def _week_start_for(target_date: date) -> date:
    return target_date - timedelta(days=target_date.weekday())


def _parse_remedial_sections(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    out: list[str] = []
    for item in parsed:
        token = re.sub(r"\s+", "", str(item or "").strip().upper())
        if token:
            out.append(token)
    return out


def _normalize_section_token(raw_value: str | None) -> str:
    token = re.sub(r"\s+", "", str(raw_value or "").strip().upper())
    if not token:
        raise HTTPException(status_code=400, detail="section cannot be empty")
    if len(token) > 80 or not STUDENT_SECTION_PATTERN.fullmatch(token):
        raise HTTPException(
            status_code=400,
            detail="section can contain only letters, numbers, slash, hyphen, and underscore",
        )
    return token


def _faculty_allowed_sections(raw_value: str | None) -> set[str]:
    if not raw_value:
        return set()
    tokens = re.split(r"[,\s]+", str(raw_value).strip().upper())
    return {token for token in tokens if token}


def _class_datetime_bounds(schedule: models.ClassSchedule, class_date: date) -> tuple[datetime, datetime]:
    class_start = datetime.combine(class_date, schedule.start_time)
    class_end = datetime.combine(class_date, schedule.end_time)
    return class_start, class_end


def _count_delivered_occurrences(
    schedule: models.ClassSchedule,
    *,
    from_date: date,
    now_dt: datetime,
) -> int:
    if from_date > now_dt.date():
        return 0

    start_offset = (schedule.weekday - from_date.weekday()) % 7
    first_class_date = from_date + timedelta(days=start_offset)
    if first_class_date > now_dt.date():
        return 0

    total = ((now_dt.date() - first_class_date).days // 7) + 1
    if total <= 0:
        return 0

    # Count once class has started; only upcoming classes are excluded.
    if now_dt.date().weekday() == schedule.weekday and now_dt.time() < schedule.start_time:
        total -= 1

    return max(0, total)


def _window_flags(
    schedule: models.ClassSchedule,
    now_dt: datetime,
    class_date: date,
    *,
    course: models.Course | None = None,
) -> tuple[bool, bool, bool]:
    class_start, class_end = _class_datetime_bounds(schedule, class_date)
    window_end = class_start + timedelta(minutes=10)
    is_open = class_start <= now_dt <= window_end
    is_active = class_start <= now_dt <= class_end
    is_ended = now_dt > class_end
    return is_open, is_active, is_ended


def _time_ranges_overlap(left_start: time, left_end: time, right_start: time, right_end: time) -> bool:
    return left_start < right_end and right_start < left_end


def _normalize_registration_number(value: str) -> str:
    normalized = re.sub(r"\s+", "", value.strip().upper())
    if len(normalized) < 3:
        raise HTTPException(status_code=400, detail="registration_number must be at least 3 characters")
    if not re.fullmatch(r"[A-Z0-9/-]+", normalized):
        raise HTTPException(
            status_code=400,
            detail="registration_number can contain only letters, numbers, slash, and hyphen",
        )
    return normalized


def _normalize_person_name(value: str) -> str:
    normalized = re.sub(r"\s+", " ", str(value or "").strip())
    if len(normalized) < 2:
        raise HTTPException(status_code=400, detail="name must be at least 2 characters")
    if len(normalized) > 100:
        raise HTTPException(status_code=400, detail="name cannot exceed 100 characters")
    return normalized


def _public_media_reference(object_key: str | None, legacy_data_url: str | None) -> str | None:
    if object_key:
        return signed_url_for_object(object_key)
    value = str(legacy_data_url or "").strip()
    return value or None


def _media_data_url_for_processing(db: Session, *, object_key: str | None, legacy_data_url: str | None) -> str | None:
    if object_key:
        restored = data_url_for_object(db, object_key)
        if restored:
            return restored
    value = str(legacy_data_url or "").strip()
    return value or None


def _student_profile_photo_data_url(db: Session, student: models.Student) -> str | None:
    return _media_data_url_for_processing(
        db,
        object_key=student.profile_photo_object_key,
        legacy_data_url=student.profile_photo_data_url,
    )


def _faculty_profile_photo_data_url(db: Session, faculty: models.Faculty) -> str | None:
    return _media_data_url_for_processing(
        db,
        object_key=faculty.profile_photo_object_key,
        legacy_data_url=faculty.profile_photo_data_url,
    )


def _sync_student_to_mongo(student: models.Student, *, source: str) -> None:
    _upsert_mongo_by_id(
        "students",
        student.id,
        {
            "name": student.name,
            "email": student.email,
            "registration_number": student.registration_number,
            "parent_email": student.parent_email,
            "profile_photo_data_url": None,
            "profile_photo_object_key": student.profile_photo_object_key,
            "profile_photo_url": _public_media_reference(student.profile_photo_object_key, student.profile_photo_data_url),
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
            "source": source,
        },
    )


def _sync_faculty_to_mongo(faculty: models.Faculty, *, source: str) -> None:
    _upsert_mongo_by_id(
        "faculty",
        faculty.id,
        {
            "name": faculty.name,
            "email": faculty.email,
            "faculty_identifier": faculty.faculty_identifier,
            "section": faculty.section,
            "section_updated_at": faculty.section_updated_at,
            "profile_photo_data_url": None,
            "profile_photo_object_key": faculty.profile_photo_object_key,
            "profile_photo_url": _public_media_reference(faculty.profile_photo_object_key, faculty.profile_photo_data_url),
            "profile_photo_updated_at": faculty.profile_photo_updated_at,
            "profile_photo_locked_until": faculty.profile_photo_locked_until,
            "department": faculty.department,
            "created_at": faculty.created_at,
            "source": source,
        },
    )


def _student_profile_out(student: models.Student) -> schemas.StudentProfileOut:
    can_update_now, locked_until, lock_days_remaining = _photo_lock_state(student)
    section_change_window_open, section_locked_until, section_lock_minutes_remaining = _student_section_lock_state(student)
    has_section = bool(re.sub(r"\s+", "", str(student.section or "").strip()))
    has_photo = bool(student.profile_photo_object_key or student.profile_photo_data_url)
    return schemas.StudentProfileOut(
        student_id=student.id,
        name=student.name,
        email=student.email,
        registration_number=student.registration_number,
        parent_email=student.parent_email,
        section=student.section,
        section_updated_at=student.section_updated_at,
        department=student.department,
        semester=student.semester,
        has_profile_photo=has_photo,
        photo_data_url=_public_media_reference(student.profile_photo_object_key, student.profile_photo_data_url),
        can_update_photo_now=can_update_now,
        photo_locked_until=locked_until,
        photo_lock_days_remaining=lock_days_remaining,
        can_update_section_now=not has_section,
        section_locked_until=section_locked_until,
        section_lock_minutes_remaining=section_lock_minutes_remaining,
        section_change_requires_faculty_approval=has_section and section_change_window_open,
    )


def _student_photo_out(student: models.Student) -> schemas.StudentProfilePhotoOut:
    can_update_now, locked_until, lock_days_remaining = _photo_lock_state(student)
    has_photo = bool(student.profile_photo_object_key or student.profile_photo_data_url)
    return schemas.StudentProfilePhotoOut(
        has_profile_photo=has_photo,
        photo_data_url=_public_media_reference(student.profile_photo_object_key, student.profile_photo_data_url),
        can_update_now=can_update_now,
        locked_until=locked_until,
        lock_days_remaining=lock_days_remaining,
        registration_number=student.registration_number,
    )


def _apply_student_profile_update(
    student: models.Student,
    payload: schemas.StudentProfileUpdateRequest,
    *,
    db: Session,
) -> tuple[bool, bool]:
    changed = False
    photo_changed = False
    now_dt = datetime.utcnow()

    if payload.name is not None:
        incoming_name = _normalize_person_name(payload.name)
        existing_name = re.sub(r"\s+", " ", (student.name or "").strip())
        if existing_name and incoming_name.casefold() != existing_name.casefold():
            raise HTTPException(status_code=403, detail=PROFILE_NAME_IMMUTABLE_MESSAGE)
        if not existing_name:
            student.name = incoming_name
            changed = True

    if payload.registration_number is not None:
        registration_number = _normalize_registration_number(payload.registration_number)
        existing_registration = (student.registration_number or "").strip().upper()
        if existing_registration and registration_number != existing_registration:
            raise HTTPException(status_code=403, detail=REGISTRATION_IMMUTABLE_MESSAGE)
        if not existing_registration:
            student.registration_number = registration_number
            changed = True

    if payload.section is not None:
        incoming_section = _normalize_section_token(payload.section)
        existing_section = re.sub(r"\s+", "", str(student.section or "").strip().upper())
        if incoming_section != existing_section:
            section_change_window_open, _, section_lock_minutes_remaining = _student_section_lock_state(student, now_dt)
            if existing_section and not section_change_window_open:
                raise HTTPException(
                    status_code=423,
                    detail=(
                        "Section can be changed only once every 48 hours. "
                        f"Try again in {section_lock_minutes_remaining} minute(s)."
                    ),
                )
            if existing_section and section_change_window_open:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Section change requires faculty permission after 48 hours. "
                        "Ask your section faculty to approve the update."
                    ),
                )
            student.section = incoming_section
            student.section_updated_at = now_dt
            changed = True

    if payload.photo_data_url is not None:
        incoming_photo = payload.photo_data_url.strip()
        if not incoming_photo.startswith("data:image/"):
            raise HTTPException(status_code=400, detail="photo_data_url must be an image data URL")

        can_update_now, _, _ = _photo_lock_state(student, now_dt)
        has_existing_photo = bool(student.profile_photo_object_key or student.profile_photo_data_url)
        if has_existing_photo and not can_update_now:
            raise HTTPException(status_code=423, detail=PROFILE_PHOTO_LOCK_MESSAGE)

        previous_key = str(student.profile_photo_object_key or "").strip() or None
        media = store_data_url_object(
            db,
            owner_table="students",
            owner_id=int(student.id),
            media_kind="student-profile-photo",
            data_url=incoming_photo,
            retention_days=PROFILE_MEDIA_RETENTION_DAYS,
        )
        student.profile_photo_object_key = media.object_key
        student.profile_photo_data_url = None
        student.profile_photo_updated_at = now_dt
        student.profile_photo_locked_until = now_dt + timedelta(days=PROFILE_PHOTO_LOCK_DAYS)
        if previous_key and previous_key != media.object_key:
            mark_media_deleted(db, previous_key)
        changed = True
        photo_changed = True

    return changed, photo_changed


def _normalize_faculty_identifier(value: str) -> str:
    normalized = re.sub(r"\s+", "", value.strip().upper())
    if len(normalized) < 3:
        raise HTTPException(status_code=400, detail="faculty_identifier must be at least 3 characters")
    if not re.fullmatch(r"[A-Z0-9/-]+", normalized):
        raise HTTPException(
            status_code=400,
            detail="faculty_identifier can contain only letters, numbers, slash, and hyphen",
        )
    return normalized


def _faculty_photo_lock_state(
    faculty: models.Faculty,
    now_dt: datetime | None = None,
) -> tuple[bool, datetime | None, int]:
    now_dt = now_dt or datetime.utcnow()
    locked_until = faculty.profile_photo_locked_until
    if not locked_until or now_dt >= locked_until:
        return True, locked_until, 0
    remaining_days = math.ceil((locked_until - now_dt).total_seconds() / 86400)
    return False, locked_until, max(0, remaining_days)


def _faculty_section_lock_state(
    faculty: models.Faculty,
    now_dt: datetime | None = None,
) -> tuple[bool, datetime | None, int]:
    now_dt = now_dt or datetime.utcnow()
    if not faculty.section or not faculty.section_updated_at:
        return True, None, 0
    locked_until = faculty.section_updated_at + timedelta(minutes=FACULTY_SECTION_LOCK_MINUTES)
    if now_dt >= locked_until:
        return True, locked_until, 0
    remaining_minutes = math.ceil((locked_until - now_dt).total_seconds() / 60)
    return False, locked_until, max(0, remaining_minutes)


def _student_section_lock_state(
    student: models.Student,
    now_dt: datetime | None = None,
) -> tuple[bool, datetime | None, int]:
    now_dt = now_dt or datetime.utcnow()
    if not student.section or not student.section_updated_at:
        return True, None, 0
    locked_until = student.section_updated_at + timedelta(minutes=STUDENT_SECTION_LOCK_MINUTES)
    if now_dt >= locked_until:
        return True, locked_until, 0
    remaining_minutes = math.ceil((locked_until - now_dt).total_seconds() / 60)
    return False, locked_until, max(0, remaining_minutes)


def _faculty_profile_out(faculty: models.Faculty) -> schemas.FacultyProfileOut:
    can_update_photo_now, photo_locked_until, photo_lock_days_remaining = _faculty_photo_lock_state(faculty)
    can_update_section_now, section_locked_until, section_lock_minutes_remaining = _faculty_section_lock_state(faculty)
    has_photo = bool(faculty.profile_photo_object_key or faculty.profile_photo_data_url)
    return schemas.FacultyProfileOut(
        faculty_id=faculty.id,
        name=faculty.name,
        email=faculty.email,
        department=faculty.department,
        faculty_identifier=faculty.faculty_identifier,
        section=faculty.section,
        section_updated_at=faculty.section_updated_at,
        has_profile_photo=has_photo,
        photo_data_url=_public_media_reference(faculty.profile_photo_object_key, faculty.profile_photo_data_url),
        can_update_photo_now=can_update_photo_now,
        photo_locked_until=photo_locked_until,
        photo_lock_days_remaining=photo_lock_days_remaining,
        can_update_section_now=can_update_section_now,
        section_locked_until=section_locked_until,
        section_lock_minutes_remaining=section_lock_minutes_remaining,
    )


def _apply_faculty_profile_update(
    faculty: models.Faculty,
    payload: schemas.FacultyProfileUpdateRequest,
    *,
    db: Session,
) -> tuple[bool, bool]:
    changed = False
    photo_changed = False
    now_dt = datetime.utcnow()

    if payload.name is not None:
        incoming_name = _normalize_person_name(payload.name)
        existing_name = re.sub(r"\s+", " ", (faculty.name or "").strip())
        if existing_name and incoming_name.casefold() != existing_name.casefold():
            raise HTTPException(status_code=403, detail=PROFILE_NAME_IMMUTABLE_MESSAGE)
        if not existing_name:
            faculty.name = incoming_name
            changed = True

    if payload.faculty_identifier is not None:
        faculty_identifier = _normalize_faculty_identifier(payload.faculty_identifier)
        existing_faculty_identifier = (faculty.faculty_identifier or "").strip().upper()
        if existing_faculty_identifier and faculty_identifier != existing_faculty_identifier:
            raise HTTPException(status_code=403, detail=FACULTY_ID_IMMUTABLE_MESSAGE)
        if not existing_faculty_identifier:
            conflict = (
                db.query(models.Faculty)
                .filter(
                    models.Faculty.faculty_identifier == faculty_identifier,
                    models.Faculty.id != faculty.id,
                )
                .first()
            )
            if conflict:
                raise HTTPException(status_code=409, detail="Faculty ID already exists")
            faculty.faculty_identifier = faculty_identifier
            changed = True

    if payload.section is not None:
        incoming_section = _normalize_section_token(payload.section)
        existing_section = re.sub(r"\s+", "", str(faculty.section or "").strip().upper())
        if incoming_section != existing_section:
            can_update_section_now, _, section_lock_minutes_remaining = _faculty_section_lock_state(faculty, now_dt)
            if existing_section and not can_update_section_now:
                raise HTTPException(
                    status_code=423,
                    detail=(
                        "Section can only be changed once every 24 hours. "
                        f"Try again in {section_lock_minutes_remaining} minute(s)."
                    ),
                )
            faculty.section = incoming_section
            faculty.section_updated_at = now_dt
            changed = True

    if payload.photo_data_url is not None:
        incoming_photo = payload.photo_data_url.strip()
        if not incoming_photo.startswith("data:image/"):
            raise HTTPException(status_code=400, detail="photo_data_url must be an image data URL")

        can_update_photo_now, _, _ = _faculty_photo_lock_state(faculty, now_dt)
        has_existing_photo = bool(faculty.profile_photo_object_key or faculty.profile_photo_data_url)
        if has_existing_photo and not can_update_photo_now:
            raise HTTPException(status_code=423, detail=FACULTY_PHOTO_LOCK_MESSAGE)

        previous_key = str(faculty.profile_photo_object_key or "").strip() or None
        media = store_data_url_object(
            db,
            owner_table="faculty",
            owner_id=int(faculty.id),
            media_kind="faculty-profile-photo",
            data_url=incoming_photo,
            retention_days=PROFILE_MEDIA_RETENTION_DAYS,
        )
        faculty.profile_photo_object_key = media.object_key
        faculty.profile_photo_data_url = None
        faculty.profile_photo_updated_at = now_dt
        faculty.profile_photo_locked_until = now_dt + timedelta(days=FACULTY_PHOTO_LOCK_DAYS)
        if previous_key and previous_key != media.object_key:
            mark_media_deleted(db, previous_key)
        changed = True
        photo_changed = True

    return changed, photo_changed


def _photo_fingerprint(photo_data_url: str | None) -> str | None:
    if not photo_data_url:
        return None
    return hashlib.sha256(photo_data_url.encode("utf-8")).hexdigest()


def _parse_face_template(raw_value: str | None) -> dict | None:
    if not raw_value:
        return None
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    embeddings = parsed.get("embeddings")
    if not isinstance(embeddings, list) or not embeddings:
        return None
    return parsed


def _merge_face_templates(primary: dict | None, secondary: dict | None) -> dict | None:
    if not primary and not secondary:
        return None
    base = dict(primary or secondary or {})
    merged_embeddings: list = []
    seen: set[str] = set()
    for source in (primary, secondary):
        if not isinstance(source, dict):
            continue
        for item in source.get("embeddings", []) or []:
            if not isinstance(item, list):
                continue
            key = ",".join(f"{float(v):.4f}" for v in item[:12])
            if key in seen:
                continue
            seen.add(key)
            merged_embeddings.append(item)
            if len(merged_embeddings) >= 16:
                break
        if len(merged_embeddings) >= 16:
            break
    if merged_embeddings:
        base["embeddings"] = merged_embeddings
    return base


def _rebuild_profile_face_template(db: Session, student: models.Student) -> None:
    profile_photo_data_url = _student_profile_photo_data_url(db, student)
    if not profile_photo_data_url:
        student.profile_face_template_json = None
        student.profile_face_template_updated_at = None
        return

    try:
        template = build_profile_face_template(profile_photo_data_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid enrollment face photo: {exc}") from exc

    student.profile_face_template_json = json.dumps(template)
    student.profile_face_template_updated_at = datetime.utcnow()


def _maybe_run_identity_screening_for_student(
    db: Session,
    student: models.Student,
    *,
    trigger: str,
) -> None:
    try:
        case = run_student_enrollment_screening(db, student_id=int(student.id))
    except Exception:
        logger.exception(
            "identity_enrollment_screening_failed student_id=%s trigger=%s",
            getattr(student, "id", None),
            trigger,
        )
        return
    logger.info(
        "identity_enrollment_screening_completed student_id=%s case_id=%s risk_level=%s trigger=%s",
        getattr(student, "id", None),
        case.id,
        case.risk_level.value,
        trigger,
    )


def _upsert_mongo_by_id(collection: str, doc_id: int, payload: dict) -> None:
    body = dict(payload)
    body["id"] = doc_id
    body = apply_pii_encryption_policy(collection, body)
    mongo_db = get_mongo_db(required=False)
    if mongo_db is None:
        mirror_document(
            collection,
            body,
            upsert_filter={"id": doc_id},
            required=False,
        )
        return
    try:
        mongo_db[collection].update_one({"id": doc_id}, {"$set": body}, upsert=True)
    except DuplicateKeyError as exc:
        details = getattr(exc, "details", {}) or {}
        key_value = details.get("keyValue")
        if not isinstance(key_value, dict) or not key_value:
            raise

        # If a secondary unique key (for example course_id) collides, refresh the
        # existing document by that key and keep its current id.
        conflict_filter = dict(key_value)
        fallback_body = dict(body)
        fallback_body.pop("id", None)
        result = mongo_db[collection].update_one(conflict_filter, {"$set": fallback_body}, upsert=False)
        if result.matched_count:
            logger.debug(
                "Resolved duplicate-key upsert for collection=%s id=%s via filter=%s",
                collection,
                doc_id,
                conflict_filter,
            )
            return
        logger.warning(
            "Skipping unresolved duplicate-key upsert for collection=%s id=%s filter=%s",
            collection,
            doc_id,
            conflict_filter,
        )
        mirror_document(
            collection,
            body,
            upsert_filter={"id": doc_id},
            required=False,
        )
        return
    except Exception:
        mirror_document(
            collection,
            body,
            upsert_filter={"id": doc_id},
            required=False,
        )
        return


def _upsert_class_schedule_document(schedule: models.ClassSchedule, *, source: str) -> None:
    _upsert_mongo_by_id(
        "class_schedules",
        schedule.id,
        {
            "course_id": schedule.course_id,
            "faculty_id": schedule.faculty_id,
            "weekday": schedule.weekday,
            "start_time": str(schedule.start_time),
            "end_time": str(schedule.end_time),
            "classroom_label": schedule.classroom_label,
            "is_active": schedule.is_active,
            "source": source,
            "created_at": schedule.created_at,
        },
    )


def _resolve_or_create_timetable_schedule(
    db: Session,
    *,
    payload: schemas.TimetableOverrideUpsertRequest,
    current_user: models.AuthUser,
) -> tuple[models.ClassSchedule, bool]:
    course = db.get(models.Course, payload.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.faculty_id != payload.faculty_id:
        raise HTTPException(status_code=400, detail="Faculty is not assigned to this course")

    existing = (
        db.query(models.ClassSchedule)
        .filter(
            models.ClassSchedule.course_id == payload.course_id,
            models.ClassSchedule.weekday == payload.weekday,
            models.ClassSchedule.start_time == payload.start_time,
        )
        .first()
    )
    if existing:
        schedule_changed = False
        if existing.faculty_id != payload.faculty_id:
            raise HTTPException(
                status_code=409,
                detail="A schedule already exists for this course/time with a different faculty assignment",
            )
        if existing.end_time != payload.end_time:
            raise HTTPException(
                status_code=409,
                detail="A schedule already exists for this course/time with a different end time",
            )
        incoming_room = str(payload.classroom_label or "").strip()
        existing_room = str(existing.classroom_label or "").strip()
        if incoming_room and existing_room and incoming_room != existing_room:
            raise HTTPException(
                status_code=409,
                detail="A schedule already exists for this course/time with a different classroom label",
            )
        if incoming_room and not existing_room:
            existing.classroom_label = incoming_room
            schedule_changed = True
        if not existing.is_active:
            existing.is_active = True
            schedule_changed = True
        if schedule_changed:
            _upsert_class_schedule_document(existing, source="attendance.timetable_override")
        return existing, False

    assignment = (
        db.query(models.CourseClassroom)
        .filter(models.CourseClassroom.course_id == payload.course_id)
        .first()
    )
    if not assignment and not payload.classroom_label:
        raise HTTPException(
            status_code=400,
            detail="Assign a classroom to this course or provide classroom_label before creating a timetable override",
        )

    classroom = db.get(models.Classroom, assignment.classroom_id) if assignment else None
    classroom_label = payload.classroom_label or (
        f"{classroom.block}-{classroom.room_number}" if classroom else None
    )

    weekday_schedules = (
        db.query(models.ClassSchedule)
        .filter(
            models.ClassSchedule.is_active.is_(True),
            models.ClassSchedule.weekday == payload.weekday,
        )
        .all()
    )
    room_by_course = {
        int(row.course_id): int(row.classroom_id)
        for row in db.query(models.CourseClassroom).all()
    }
    new_room_id = int(assignment.classroom_id) if assignment else None
    for row in weekday_schedules:
        if not _time_ranges_overlap(payload.start_time, payload.end_time, row.start_time, row.end_time):
            continue

        if int(row.faculty_id) == int(payload.faculty_id):
            raise HTTPException(
                status_code=409,
                detail=f"Timetable override failed: faculty has overlapping class (schedule {row.id})",
            )

        existing_room_id = room_by_course.get(int(row.course_id))
        if new_room_id and existing_room_id and existing_room_id == new_room_id:
            raise HTTPException(
                status_code=409,
                detail=f"Timetable override failed: classroom has overlapping class (schedule {row.id})",
            )

    schedule = models.ClassSchedule(
        course_id=payload.course_id,
        faculty_id=payload.faculty_id,
        weekday=payload.weekday,
        start_time=payload.start_time,
        end_time=payload.end_time,
        classroom_label=classroom_label,
        is_active=True,
    )
    db.add(schedule)
    db.flush()

    _upsert_class_schedule_document(schedule, source="attendance.timetable_override")
    if assignment:
        mirror_document(
            "resource_allocations",
            {
                "course_id": int(payload.course_id),
                "classroom_id": int(assignment.classroom_id),
                "classroom_label": classroom_label,
                "faculty_id": int(payload.faculty_id),
                "updated_at": datetime.utcnow(),
                "source": "attendance.timetable_override",
            },
            upsert_filter={"course_id": int(payload.course_id)},
            required=False,
        )
    mirror_document(
        "admin_audit_logs",
        {
            "action": "timetable_override_schedule_created",
            "schedule_id": int(schedule.id),
            "course_id": int(schedule.course_id),
            "faculty_id": int(schedule.faculty_id),
            "weekday": int(schedule.weekday),
            "start_time": str(schedule.start_time),
            "end_time": str(schedule.end_time),
            "classroom_label": schedule.classroom_label,
            "created_at": datetime.utcnow(),
            "source": "attendance.timetable_override",
            "actor_user_id": current_user.id,
            "actor_role": current_user.role.value,
        },
        required=False,
    )
    return schedule, True


def _serialize_timetable_override(
    override: models.TimetableOverride,
    schedule: models.ClassSchedule,
) -> schemas.TimetableOverrideOut:
    return schemas.TimetableOverrideOut(
        id=override.id,
        scope_type=schemas.TimetableOverrideScope(override.scope_type),
        student_id=override.student_id,
        section=override.section,
        source_weekday=override.source_weekday,
        source_start_time=override.source_start_time,
        schedule_id=override.schedule_id,
        course_id=schedule.course_id,
        faculty_id=schedule.faculty_id,
        weekday=schedule.weekday,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        classroom_label=schedule.classroom_label,
        is_active=override.is_active,
        created_at=override.created_at,
        updated_at=override.updated_at,
    )


def _build_timetable_class_item(
    db: Session,
    *,
    student_id: int,
    current_week_start: date,
    academic_start: date,
    now_dt: datetime,
    schedule: models.ClassSchedule,
) -> schemas.TimetableClassOut | None:
    course = db.get(models.Course, schedule.course_id)
    if not course:
        return None

    class_date = current_week_start + timedelta(days=schedule.weekday)
    if class_date < academic_start:
        return None

    is_open_now, is_active_now, is_ended_now = _window_flags(
        schedule,
        now_dt,
        class_date,
        course=course,
    )
    submission = (
        db.query(models.AttendanceSubmission)
        .filter(
            models.AttendanceSubmission.schedule_id == schedule.id,
            models.AttendanceSubmission.student_id == student_id,
            models.AttendanceSubmission.class_date == class_date,
        )
        .first()
    )
    attendance_status = submission.status.value if submission else None
    if not attendance_status:
        fallback_record = (
            db.query(models.AttendanceRecord)
            .filter(
                models.AttendanceRecord.student_id == student_id,
                models.AttendanceRecord.course_id == schedule.course_id,
                models.AttendanceRecord.attendance_date == class_date,
            )
            .first()
        )
        if fallback_record:
            attendance_status = fallback_record.status.value

    return schemas.TimetableClassOut(
        schedule_id=schedule.id,
        course_id=schedule.course_id,
        course_code=course.code,
        course_title=course.title,
        weekday=schedule.weekday,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        classroom_label=schedule.classroom_label,
        class_date=class_date,
        is_open_now=is_open_now,
        is_active_now=is_active_now,
        is_ended_now=is_ended_now,
        attendance_status=attendance_status,
    )


def _record_attendance_status(
    db: Session,
    *,
    student_id: int,
    course_id: int,
    faculty_id: int,
    class_date: date,
    status: models.AttendanceStatus,
    source: str,
) -> models.AttendanceRecord | None:
    _, aggregate = append_event_and_recompute(
        db,
        student_id=int(student_id),
        course_id=int(course_id),
        attendance_date=class_date,
        status=status,
        source=source,
        actor_faculty_id=int(faculty_id),
    )
    evaluate_attendance_recovery(
        db,
        student_id=int(student_id),
        course_id=int(course_id),
    )
    return aggregate


def _upsert_present_attendance(
    db: Session,
    *,
    student_id: int,
    course_id: int,
    faculty_id: int,
    class_date: date,
    source: str,
) -> models.AttendanceRecord | None:
    return _record_attendance_status(
        db,
        student_id=student_id,
        course_id=course_id,
        faculty_id=faculty_id,
        class_date=class_date,
        status=models.AttendanceStatus.PRESENT,
        source=source,
    )


def _resolve_schedule_for_rectification(
    *,
    db: Session,
    course_id: int,
    class_date: date,
    preferred_start_time: time | None = None,
) -> models.ClassSchedule:
    weekday = class_date.weekday()
    schedule_query = (
        db.query(models.ClassSchedule)
        .filter(
            models.ClassSchedule.course_id == course_id,
            models.ClassSchedule.weekday == weekday,
            models.ClassSchedule.is_active.is_(True),
        )
    )
    if preferred_start_time is not None:
        by_start = schedule_query.filter(models.ClassSchedule.start_time == preferred_start_time).first()
        if by_start:
            return by_start
    schedule = schedule_query.order_by(models.ClassSchedule.start_time.asc()).first()
    if schedule:
        return schedule
    raise HTTPException(status_code=400, detail="No active schedule found for this subject on selected date")


def _upsert_approved_submission_for_rectification(
    *,
    db: Session,
    schedule: models.ClassSchedule,
    student_id: int,
    class_date: date,
    faculty_id: int,
    review_note: str | None,
) -> models.AttendanceSubmission:
    submission = (
        db.query(models.AttendanceSubmission)
        .filter(
            models.AttendanceSubmission.schedule_id == schedule.id,
            models.AttendanceSubmission.student_id == student_id,
            models.AttendanceSubmission.class_date == class_date,
        )
        .first()
    )
    if submission is None:
        submission = models.AttendanceSubmission(
            schedule_id=schedule.id,
            course_id=schedule.course_id,
            faculty_id=schedule.faculty_id,
            student_id=student_id,
            class_date=class_date,
            selfie_photo_data_url=None,
            ai_match=True,
            ai_confidence=1.0,
            ai_model="faculty-rectification",
            ai_reason="Attendance rectified by faculty with proof verification",
            status=models.AttendanceSubmissionStatus.APPROVED,
            submitted_at=datetime.utcnow(),
            reviewed_by_faculty_id=faculty_id,
            reviewed_at=datetime.utcnow(),
            review_note=review_note,
        )
        db.add(submission)
        db.flush()
        return submission

    submission.status = models.AttendanceSubmissionStatus.APPROVED
    submission.ai_match = True
    if not submission.ai_model:
        submission.ai_model = "faculty-rectification"
    if not submission.ai_reason:
        submission.ai_reason = "Attendance rectified by faculty with proof verification"
    submission.reviewed_by_faculty_id = faculty_id
    submission.reviewed_at = datetime.utcnow()
    submission.review_note = review_note
    db.flush()
    return submission


def _sync_rectification_request_to_mongo(
    request: models.AttendanceRectificationRequest,
    *,
    source: str,
) -> None:
    _upsert_mongo_by_id(
        "attendance_rectification_requests",
        request.id,
        {
            "student_id": request.student_id,
            "faculty_id": request.faculty_id,
            "course_id": request.course_id,
            "schedule_id": request.schedule_id,
            "class_date": request.class_date.isoformat(),
            "class_start_time": request.class_start_time.isoformat(),
            "class_end_time": request.class_end_time.isoformat(),
            "proof_note": request.proof_note,
            "proof_photo_object_key": request.proof_photo_object_key,
            "proof_photo_fingerprint": _photo_fingerprint(
                request.proof_photo_object_key or request.proof_photo_data_url
            ),
            "status": request.status.value,
            "requested_at": request.requested_at,
            "reviewed_at": request.reviewed_at,
            "reviewed_by_faculty_id": request.reviewed_by_faculty_id,
            "review_note": request.review_note,
            "source": source,
        },
    )


def _student_rectification_out(
    request: models.AttendanceRectificationRequest,
    *,
    course: models.Course | None,
    faculty: models.Faculty | None,
) -> schemas.StudentAttendanceRectificationOut:
    return schemas.StudentAttendanceRectificationOut(
        id=request.id,
        course_id=request.course_id,
        course_code=course.code if course else f"C-{request.course_id}",
        course_title=course.title if course else "Unknown Course",
        faculty_name=faculty.name if faculty else "Faculty",
        schedule_id=request.schedule_id,
        class_date=request.class_date,
        class_start_time=request.class_start_time,
        class_end_time=request.class_end_time,
        proof_note=request.proof_note,
        proof_photo_data_url=_public_media_reference(
            request.proof_photo_object_key,
            request.proof_photo_data_url,
        ),
        status=request.status,
        requested_at=request.requested_at,
        reviewed_at=request.reviewed_at,
        review_note=request.review_note,
    )


def _faculty_rectification_out(
    request: models.AttendanceRectificationRequest,
    *,
    student: models.Student | None,
    course: models.Course | None,
) -> schemas.FacultyAttendanceRectificationOut:
    return schemas.FacultyAttendanceRectificationOut(
        id=request.id,
        student_id=request.student_id,
        student_name=student.name if student else f"Student #{request.student_id}",
        course_id=request.course_id,
        course_code=course.code if course else f"C-{request.course_id}",
        course_title=course.title if course else "Unknown Course",
        class_date=request.class_date,
        class_start_time=request.class_start_time,
        class_end_time=request.class_end_time,
        proof_note=request.proof_note,
        proof_photo_data_url=_public_media_reference(
            request.proof_photo_object_key,
            request.proof_photo_data_url,
        ),
        status=request.status,
        requested_at=request.requested_at,
        reviewed_at=request.reviewed_at,
        review_note=request.review_note,
    )


_CREDITED_SUBMISSION_STATUSES = (
    models.AttendanceSubmissionStatus.VERIFIED,
    models.AttendanceSubmissionStatus.APPROVED,
)


def _is_submission_credited(status_value: models.AttendanceSubmissionStatus | str | None) -> bool:
    if status_value is None:
        return False
    try:
        normalized = (
            status_value
            if isinstance(status_value, models.AttendanceSubmissionStatus)
            else models.AttendanceSubmissionStatus(str(status_value))
        )
    except ValueError:
        return False
    return normalized in _CREDITED_SUBMISSION_STATUSES


def _submission_to_attendance_status(
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


def _photo_lock_state(student: models.Student, now_dt: datetime | None = None) -> tuple[bool, datetime | None, int]:
    now_dt = now_dt or datetime.utcnow()
    locked_until = student.profile_photo_locked_until
    if not locked_until or now_dt >= locked_until:
        return True, locked_until, 0

    remaining_days = math.ceil((locked_until - now_dt).total_seconds() / 86400)
    return False, locked_until, max(0, remaining_days)


def _enrollment_lock_state(student: models.Student, now_dt: datetime | None = None) -> tuple[bool, datetime | None, int]:
    now_dt = now_dt or datetime.utcnow()
    locked_until = student.enrollment_video_locked_until
    if not locked_until or now_dt >= locked_until:
        return True, locked_until, 0

    remaining_days = math.ceil((locked_until - now_dt).total_seconds() / 86400)
    return False, locked_until, max(0, remaining_days)


def _student_enrollment_status_out(student: models.Student) -> schemas.StudentEnrollmentStatusOut:
    can_update_now, locked_until, lock_days_remaining = _enrollment_lock_state(student)
    return schemas.StudentEnrollmentStatusOut(
        has_enrollment_video=bool(student.enrollment_video_template_json),
        can_update_now=can_update_now,
        locked_until=locked_until,
        lock_days_remaining=lock_days_remaining,
        enrollment_updated_at=student.enrollment_video_updated_at,
    )


def _ensure_default_timetable_for_student(db: Session, student: models.Student) -> dict[str, int]:
    created = {
        "faculty": 0,
        "courses": 0,
        "classrooms": 0,
        "schedules": 0,
        "enrollments": 0,
        "updated_courses": 0,
        "updated_assignments": 0,
        "updated_schedules": 0,
        "deactivated_schedules": 0,
        "removed_enrollments": 0,
        "purged_attendance_records": 0,
        "purged_attendance_submissions": 0,
        "purged_attendance_events": 0,
        "total_classes": len(DEFAULT_TIMETABLE_BLUEPRINT),
    }
    default_course_ids: set[int] = set()
    desired_schedule_slots: set[tuple[int, int, time]] = set()
    allowed_weekdays_by_course: dict[int, set[int]] = {}

    for item in DEFAULT_TIMETABLE_BLUEPRINT:
        faculty = db.query(models.Faculty).filter(models.Faculty.email == item["faculty_email"]).first()
        if not faculty:
            faculty = models.Faculty(
                name=item["faculty_name"],
                email=item["faculty_email"],
                department=student.department,
            )
            db.add(faculty)
            db.flush()
            created["faculty"] += 1
        _upsert_mongo_by_id(
            "faculty",
            faculty.id,
            {
                "name": faculty.name,
                "email": faculty.email,
                "faculty_identifier": faculty.faculty_identifier,
                "section": faculty.section,
                "section_updated_at": faculty.section_updated_at,
                "profile_photo_data_url": None,
                "profile_photo_object_key": faculty.profile_photo_object_key,
                "profile_photo_url": _public_media_reference(
                    faculty.profile_photo_object_key,
                    faculty.profile_photo_data_url,
                ),
                "profile_photo_updated_at": faculty.profile_photo_updated_at,
                "profile_photo_locked_until": faculty.profile_photo_locked_until,
                "department": faculty.department,
                "created_at": faculty.created_at,
                "source": "default-timetable-loader",
            },
        )

        course = db.query(models.Course).filter(models.Course.code == item["course_code"]).first()
        if not course:
            course = models.Course(
                code=item["course_code"],
                title=item["course_title"],
                faculty_id=faculty.id,
            )
            db.add(course)
            db.flush()
            created["courses"] += 1
        else:
            course_changed = False
            if course.title != item["course_title"]:
                course.title = item["course_title"]
                course_changed = True
            if course.faculty_id != faculty.id:
                course.faculty_id = faculty.id
                course_changed = True
            if course_changed:
                created["updated_courses"] += 1
        _upsert_mongo_by_id(
            "courses",
            course.id,
            {
                "code": course.code,
                "title": course.title,
                "faculty_id": course.faculty_id,
                "source": "default-timetable-loader",
            },
        )
        default_course_ids.add(course.id)

        classroom = (
            db.query(models.Classroom)
            .filter(
                models.Classroom.block == item["classroom_block"],
                models.Classroom.room_number == item["classroom_room"],
            )
            .first()
        )
        if not classroom:
            classroom = models.Classroom(
                block=item["classroom_block"],
                room_number=item["classroom_room"],
                capacity=70,
            )
            db.add(classroom)
            db.flush()
            created["classrooms"] += 1
        _upsert_mongo_by_id(
            "classrooms",
            classroom.id,
            {
                "block": classroom.block,
                "room_number": classroom.room_number,
                "capacity": classroom.capacity,
                "source": "default-timetable-loader",
            },
        )

        assignment = (
            db.query(models.CourseClassroom)
            .filter(models.CourseClassroom.course_id == course.id)
            .first()
        )
        if not assignment:
            assignment = models.CourseClassroom(course_id=course.id, classroom_id=classroom.id)
            db.add(assignment)
            db.flush()
        else:
            if assignment.classroom_id != classroom.id:
                assignment.classroom_id = classroom.id
                created["updated_assignments"] += 1
        _upsert_mongo_by_id(
            "course_classrooms",
            assignment.id,
            {
                "course_id": assignment.course_id,
                "classroom_id": assignment.classroom_id,
                "source": "default-timetable-loader",
            },
        )

        start_t = _time_from_hhmm(item["start"])
        end_t = _time_from_hhmm(item["end"])
        schedule = (
            db.query(models.ClassSchedule)
            .filter(
                models.ClassSchedule.course_id == course.id,
                models.ClassSchedule.weekday == item["weekday"],
                models.ClassSchedule.start_time == start_t,
            )
            .first()
        )
        if not schedule:
            schedule = models.ClassSchedule(
                course_id=course.id,
                faculty_id=faculty.id,
                weekday=item["weekday"],
                start_time=start_t,
                end_time=end_t,
                classroom_label=item["classroom_label"],
                is_active=True,
            )
            db.add(schedule)
            db.flush()
            created["schedules"] += 1
        else:
            schedule_changed = False
            if schedule.faculty_id != faculty.id:
                schedule.faculty_id = faculty.id
                schedule_changed = True
            if schedule.end_time != end_t:
                schedule.end_time = end_t
                schedule_changed = True
            if (schedule.classroom_label or "") != item["classroom_label"]:
                schedule.classroom_label = item["classroom_label"]
                schedule_changed = True
            if not schedule.is_active:
                schedule.is_active = True
                schedule_changed = True
            if schedule_changed:
                created["updated_schedules"] += 1
        _upsert_mongo_by_id(
            "class_schedules",
            schedule.id,
            {
                "course_id": schedule.course_id,
                "faculty_id": schedule.faculty_id,
                "weekday": schedule.weekday,
                "start_time": str(schedule.start_time),
                "end_time": str(schedule.end_time),
                "classroom_label": schedule.classroom_label,
                "is_active": schedule.is_active,
                "created_at": schedule.created_at,
                "source": "default-timetable-loader",
            },
        )
        desired_schedule_slots.add((course.id, item["weekday"], start_t))
        allowed_weekdays_by_course.setdefault(course.id, set()).add(item["weekday"])

        enrollment = (
            db.query(models.Enrollment)
            .filter(
                models.Enrollment.student_id == student.id,
                models.Enrollment.course_id == course.id,
            )
            .first()
        )
        if not enrollment:
            enrollment = models.Enrollment(student_id=student.id, course_id=course.id)
            db.add(enrollment)
            db.flush()
            created["enrollments"] += 1
        _upsert_mongo_by_id(
            "enrollments",
            enrollment.id,
            {
                "student_id": enrollment.student_id,
                "course_id": enrollment.course_id,
                "created_at": enrollment.created_at,
                "source": "default-timetable-loader",
            },
        )

    mongo_db = get_mongo_db()

    stale_schedule_ids: list[int] = []
    if default_course_ids:
        all_default_schedules = (
            db.query(models.ClassSchedule)
            .filter(models.ClassSchedule.course_id.in_(sorted(default_course_ids)))
            .all()
        )
        for schedule in all_default_schedules:
            signature = (schedule.course_id, schedule.weekday, schedule.start_time)
            if signature in desired_schedule_slots:
                continue
            stale_schedule_ids.append(schedule.id)
            if schedule.is_active:
                schedule.is_active = False
                created["deactivated_schedules"] += 1
                _upsert_mongo_by_id(
                    "class_schedules",
                    schedule.id,
                    {
                        "course_id": schedule.course_id,
                        "faculty_id": schedule.faculty_id,
                        "weekday": schedule.weekday,
                        "start_time": str(schedule.start_time),
                        "end_time": str(schedule.end_time),
                        "classroom_label": schedule.classroom_label,
                        "is_active": False,
                        "created_at": schedule.created_at,
                        "source": "default-timetable-loader",
                    },
                )

    if created["deactivated_schedules"] > 0:
        reset_record_count = (
            db.query(models.AttendanceRecord)
            .filter(models.AttendanceRecord.student_id == student.id)
            .delete(synchronize_session=False)
        )
        reset_event_count = (
            db.query(models.AttendanceEvent)
            .filter(models.AttendanceEvent.student_id == student.id)
            .delete(synchronize_session=False)
        )
        reset_submission_count = (
            db.query(models.AttendanceSubmission)
            .filter(models.AttendanceSubmission.student_id == student.id)
            .delete(synchronize_session=False)
        )
        created["purged_attendance_records"] += int(reset_record_count or 0)
        created["purged_attendance_events"] += int(reset_event_count or 0)
        created["purged_attendance_submissions"] += int(reset_submission_count or 0)
        if mongo_db is not None:
            mongo_db["attendance_records"].delete_many({"student_id": student.id})
            mongo_db["attendance_events"].delete_many({"student_id": student.id})
            mongo_db["attendance_submissions"].delete_many({"student_id": student.id})
    elif stale_schedule_ids:
        stale_submission_count = (
            db.query(models.AttendanceSubmission)
            .filter(
                models.AttendanceSubmission.student_id == student.id,
                models.AttendanceSubmission.schedule_id.in_(stale_schedule_ids),
            )
            .delete(synchronize_session=False)
        )
        created["purged_attendance_submissions"] += int(stale_submission_count or 0)
        if mongo_db is not None:
            mongo_db["attendance_submissions"].delete_many(
                {
                    "student_id": student.id,
                    "schedule_id": {"$in": stale_schedule_ids},
                }
            )

    stale_enrollments = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.student_id == student.id)
        .filter(~models.Enrollment.course_id.in_(default_course_ids))
        .all()
    )
    stale_course_ids: list[int] = []
    for stale in stale_enrollments:
        stale_course_ids.append(stale.course_id)
        db.delete(stale)
    created["removed_enrollments"] += len(stale_enrollments)
    if stale_course_ids:
        stale_course_ids = sorted(set(stale_course_ids))
        stale_record_count = (
            db.query(models.AttendanceRecord)
            .filter(
                models.AttendanceRecord.student_id == student.id,
                models.AttendanceRecord.course_id.in_(stale_course_ids),
            )
            .delete(synchronize_session=False)
        )
        stale_event_count = (
            db.query(models.AttendanceEvent)
            .filter(
                models.AttendanceEvent.student_id == student.id,
                models.AttendanceEvent.course_id.in_(stale_course_ids),
            )
            .delete(synchronize_session=False)
        )
        stale_submission_count = (
            db.query(models.AttendanceSubmission)
            .filter(
                models.AttendanceSubmission.student_id == student.id,
                models.AttendanceSubmission.course_id.in_(stale_course_ids),
            )
            .delete(synchronize_session=False)
        )
        created["purged_attendance_records"] += int(stale_record_count or 0)
        created["purged_attendance_events"] += int(stale_event_count or 0)
        created["purged_attendance_submissions"] += int(stale_submission_count or 0)

        if mongo_db is not None:
            mongo_db["enrollments"].delete_many(
                {
                    "student_id": student.id,
                    "course_id": {"$in": stale_course_ids},
                }
            )
            mongo_db["attendance_records"].delete_many(
                {
                    "student_id": student.id,
                    "course_id": {"$in": stale_course_ids},
                }
            )
            mongo_db["attendance_events"].delete_many(
                {
                    "student_id": student.id,
                    "course_id": {"$in": stale_course_ids},
                }
            )
            mongo_db["attendance_submissions"].delete_many(
                {
                    "student_id": student.id,
                    "course_id": {"$in": stale_course_ids},
                }
            )

    if default_course_ids:
        default_course_ids_sorted = sorted(default_course_ids)
        candidate_records = (
            db.query(models.AttendanceRecord)
            .filter(
                models.AttendanceRecord.student_id == student.id,
                models.AttendanceRecord.course_id.in_(default_course_ids_sorted),
            )
            .all()
        )
        mismatched_record_ids: list[int] = []
        for record in candidate_records:
            allowed_weekdays = allowed_weekdays_by_course.get(record.course_id, set())
            if allowed_weekdays and record.attendance_date.weekday() not in allowed_weekdays:
                mismatched_record_ids.append(record.id)
                db.delete(record)

        if mismatched_record_ids:
            created["purged_attendance_records"] += len(mismatched_record_ids)
            if mongo_db is not None:
                mongo_db["attendance_records"].delete_many({"id": {"$in": mismatched_record_ids}})

        candidate_submissions = (
            db.query(models.AttendanceSubmission)
            .filter(
                models.AttendanceSubmission.student_id == student.id,
                models.AttendanceSubmission.course_id.in_(default_course_ids_sorted),
            )
            .all()
        )
        mismatched_submission_ids: list[int] = []
        for submission in candidate_submissions:
            allowed_weekdays = allowed_weekdays_by_course.get(submission.course_id, set())
            if allowed_weekdays and submission.class_date.weekday() not in allowed_weekdays:
                mismatched_submission_ids.append(submission.id)
                db.delete(submission)

        if mismatched_submission_ids:
            created["purged_attendance_submissions"] += len(mismatched_submission_ids)
            if mongo_db is not None:
                mongo_db["attendance_submissions"].delete_many({"id": {"$in": mismatched_submission_ids}})

    return created


@router.post("/schedules", response_model=schemas.ClassScheduleOut, status_code=status.HTTP_201_CREATED)
def create_schedule(
    payload: schemas.ClassScheduleCreate,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    course = db.get(models.Course, payload.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="end_time must be later than start_time")

    if current_user.role == models.UserRole.FACULTY:
        if current_user.faculty_id != payload.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty can only schedule classes for their own ID")

    if course.faculty_id != payload.faculty_id:
        raise HTTPException(status_code=400, detail="Faculty is not assigned to this course")

    existing = (
        db.query(models.ClassSchedule)
        .filter(
            models.ClassSchedule.course_id == payload.course_id,
            models.ClassSchedule.weekday == payload.weekday,
            models.ClassSchedule.start_time == payload.start_time,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Schedule already exists for this course and start time")

    assignment = (
        db.query(models.CourseClassroom)
        .filter(models.CourseClassroom.course_id == payload.course_id)
        .first()
    )
    if not assignment:
        raise HTTPException(
            status_code=400,
            detail="Linking engine check failed: assign a classroom to this course before scheduling",
        )

    classroom = db.get(models.Classroom, assignment.classroom_id)
    classroom_label = payload.classroom_label or (
        f"{classroom.block}-{classroom.room_number}" if classroom else None
    )

    weekday_schedules = (
        db.query(models.ClassSchedule)
        .filter(
            models.ClassSchedule.is_active.is_(True),
            models.ClassSchedule.weekday == payload.weekday,
        )
        .all()
    )
    room_by_course = {
        int(row.course_id): int(row.classroom_id)
        for row in db.query(models.CourseClassroom).all()
    }
    for row in weekday_schedules:
        if not _time_ranges_overlap(payload.start_time, payload.end_time, row.start_time, row.end_time):
            continue

        if int(row.faculty_id) == int(payload.faculty_id):
            mirror_document(
                "admin_audit_logs",
                {
                    "action": "schedule_create_rejected",
                    "reason": "faculty_time_overlap",
                    "payload": payload.model_dump(mode="json"),
                    "conflict_with_schedule_id": int(row.id),
                    "created_at": datetime.utcnow(),
                    "source": "attendance.create_schedule",
                    "actor_user_id": current_user.id,
                    "actor_role": current_user.role.value,
                },
                required=False,
            )
            raise HTTPException(
                status_code=409,
                detail=f"Linking engine check failed: faculty has overlapping class (schedule {row.id})",
            )

        existing_room_id = room_by_course.get(int(row.course_id))
        new_room_id = int(assignment.classroom_id)
        if existing_room_id and existing_room_id == new_room_id:
            mirror_document(
                "admin_audit_logs",
                {
                    "action": "schedule_create_rejected",
                    "reason": "classroom_time_overlap",
                    "payload": payload.model_dump(mode="json"),
                    "conflict_with_schedule_id": int(row.id),
                    "classroom_id": int(new_room_id),
                    "created_at": datetime.utcnow(),
                    "source": "attendance.create_schedule",
                    "actor_user_id": current_user.id,
                    "actor_role": current_user.role.value,
                },
                required=False,
            )
            raise HTTPException(
                status_code=409,
                detail=f"Linking engine check failed: classroom has overlapping class (schedule {row.id})",
            )

    schedule = models.ClassSchedule(**(payload.model_dump() | {"classroom_label": classroom_label}))
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    _upsert_mongo_by_id(
        "class_schedules",
        schedule.id,
        {
            "course_id": schedule.course_id,
            "faculty_id": schedule.faculty_id,
            "weekday": schedule.weekday,
            "start_time": str(schedule.start_time),
            "end_time": str(schedule.end_time),
            "classroom_label": schedule.classroom_label,
            "is_active": schedule.is_active,
            "source": "api",
            "created_at": schedule.created_at,
        },
    )
    mirror_document(
        "resource_allocations",
        {
            "course_id": int(payload.course_id),
            "classroom_id": int(assignment.classroom_id),
            "classroom_label": classroom_label,
            "faculty_id": int(payload.faculty_id),
            "updated_at": datetime.utcnow(),
            "source": "attendance.create_schedule",
        },
        upsert_filter={"course_id": int(payload.course_id)},
        required=False,
    )
    mirror_document(
        "admin_audit_logs",
        {
            "action": "schedule_created",
            "schedule_id": int(schedule.id),
            "course_id": int(schedule.course_id),
            "faculty_id": int(schedule.faculty_id),
            "classroom_id": int(assignment.classroom_id),
            "classroom_label": classroom_label,
            "weekday": int(schedule.weekday),
            "start_time": str(schedule.start_time),
            "end_time": str(schedule.end_time),
            "created_at": datetime.utcnow(),
            "source": "attendance.create_schedule",
            "actor_user_id": current_user.id,
            "actor_role": current_user.role.value,
        },
        required=False,
    )

    return schedule


@router.get("/schedules", response_model=list[schemas.ClassScheduleOut])
def list_schedules(
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.STUDENT)
    ),
):
    query = db.query(models.ClassSchedule).filter(models.ClassSchedule.is_active.is_(True))

    if current_user.role == models.UserRole.FACULTY:
        query = query.filter(models.ClassSchedule.faculty_id == current_user.faculty_id)

    if current_user.role == models.UserRole.STUDENT:
        if not current_user.student_id:
            raise HTTPException(status_code=403, detail="Student account is not linked correctly")
        course_ids = (
            db.query(models.Enrollment.course_id)
            .filter(models.Enrollment.student_id == current_user.student_id)
            .all()
        )
        enrolled_course_ids = [row.course_id for row in course_ids]
        if not enrolled_course_ids:
            return []
        query = query.filter(models.ClassSchedule.course_id.in_(enrolled_course_ids))

    return query.order_by(models.ClassSchedule.weekday.asc(), models.ClassSchedule.start_time.asc()).all()


@router.post("/timetable-overrides", response_model=schemas.TimetableOverrideOut, status_code=status.HTTP_201_CREATED)
def upsert_timetable_override(
    payload: schemas.TimetableOverrideUpsertRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    student_id: int | None = None
    section: str | None = None
    affected_student_ids: list[int] = []
    if payload.scope_type == schemas.TimetableOverrideScope.STUDENT:
        student = db.get(models.Student, payload.student_id)
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        student_id = int(student.id)
        affected_student_ids = [student_id]
        scope_key = f"student:{student_id}"
        scope_type = schemas.TimetableOverrideScope.STUDENT.value
    else:
        section = _normalize_section_token(payload.section)
        section_student_rows = (
            db.query(models.Student.id)
            .filter(models.Student.section == section)
            .all()
        )
        affected_student_ids = sorted({int(row.id) for row in section_student_rows if row and row.id})
        if not affected_student_ids:
            raise HTTPException(status_code=404, detail="No students found for the selected section")
        scope_key = f"section:{section}"
        scope_type = schemas.TimetableOverrideScope.SECTION.value

    schedule, _ = _resolve_or_create_timetable_schedule(
        db,
        payload=payload,
        current_user=current_user,
    )

    override = (
        db.query(models.TimetableOverride)
        .filter(
            models.TimetableOverride.scope_key == scope_key,
            models.TimetableOverride.source_weekday == payload.source_weekday,
            models.TimetableOverride.source_start_time == payload.source_start_time,
        )
        .first()
    )
    now_dt = datetime.utcnow()
    if override:
        override.scope_type = scope_type
        override.scope_key = scope_key
        override.student_id = student_id
        override.section = section
        override.schedule_id = schedule.id
        override.is_active = payload.is_active
        override.updated_by_user_id = current_user.id
        override.updated_at = now_dt
        status_code = status.HTTP_200_OK
    else:
        override = models.TimetableOverride(
            scope_type=scope_type,
            scope_key=scope_key,
            student_id=student_id,
            section=section,
            source_weekday=payload.source_weekday,
            source_start_time=payload.source_start_time,
            schedule_id=schedule.id,
            is_active=payload.is_active,
            updated_by_user_id=current_user.id,
            created_at=now_dt,
            updated_at=now_dt,
        )
        db.add(override)
        status_code = status.HTTP_201_CREATED

    db.commit()
    db.refresh(override)
    db.refresh(schedule)
    response.status_code = status_code

    _upsert_mongo_by_id(
        "timetable_overrides",
        override.id,
        {
            "scope_type": override.scope_type,
            "scope_key": override.scope_key,
            "student_id": override.student_id,
            "section": override.section,
            "source_weekday": override.source_weekday,
            "source_start_time": str(override.source_start_time),
            "schedule_id": override.schedule_id,
            "is_active": override.is_active,
            "updated_by_user_id": override.updated_by_user_id,
            "created_at": override.created_at,
            "updated_at": override.updated_at,
            "source": "attendance.timetable_override",
        },
    )
    mirror_document(
        "admin_audit_logs",
        {
            "action": "timetable_override_upserted",
            "override_id": int(override.id),
            "scope_type": override.scope_type,
            "scope_key": override.scope_key,
            "student_id": override.student_id,
            "section": override.section,
            "source_weekday": int(override.source_weekday),
            "source_start_time": str(override.source_start_time),
            "schedule_id": int(override.schedule_id),
            "course_id": int(schedule.course_id),
            "faculty_id": int(schedule.faculty_id),
            "weekday": int(schedule.weekday),
            "start_time": str(schedule.start_time),
            "end_time": str(schedule.end_time),
            "classroom_label": schedule.classroom_label,
            "created_at": now_dt,
            "source": "attendance.timetable_override",
            "actor_user_id": current_user.id,
            "actor_role": current_user.role.value,
            "write_mode": "update" if status_code == status.HTTP_200_OK else "create",
        },
        required=False,
    )
    event_scopes = {
        "role:admin",
        f"faculty:{int(schedule.faculty_id)}",
    }
    for sid in affected_student_ids:
        event_scopes.add(f"student:{int(sid)}")
    publish_domain_event(
        "attendance.timetable.updated",
        payload={
            "override_id": int(override.id),
            "scope_type": override.scope_type,
            "student_id": override.student_id,
            "section": override.section,
            "source_weekday": int(override.source_weekday),
            "source_start_time": str(override.source_start_time),
            "schedule_id": int(override.schedule_id),
            "course_id": int(schedule.course_id),
            "faculty_id": int(schedule.faculty_id),
            "weekday": int(schedule.weekday),
            "start_time": str(schedule.start_time),
            "end_time": str(schedule.end_time),
            "classroom_label": schedule.classroom_label,
            "affected_student_ids": affected_student_ids,
        },
        scopes=event_scopes,
        topics={"attendance"},
        actor={
            "user_id": int(current_user.id),
            "role": current_user.role.value,
        },
        source="attendance",
    )

    return _serialize_timetable_override(override, schedule)


@router.post("/student/default-timetable", response_model=schemas.DefaultTimetableLoadResponse)
def load_default_student_timetable(
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    student = db.get(models.Student, current_user.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    created = _ensure_default_timetable_for_student(db, student)
    db.commit()

    mirror_document(
        "student_default_timetable_loads",
        {
            "student_id": student.id,
            "student_email": student.email,
            "created_faculty": created["faculty"],
            "created_courses": created["courses"],
            "created_classrooms": created["classrooms"],
            "created_schedules": created["schedules"],
            "created_enrollments": created["enrollments"],
            "total_classes": created["total_classes"],
            "loaded_at": datetime.utcnow(),
            "source": "student-portal",
        },
    )

    return schemas.DefaultTimetableLoadResponse(
        message="Default timetable loaded",
        created_faculty=created["faculty"],
        created_courses=created["courses"],
        created_classrooms=created["classrooms"],
        created_schedules=created["schedules"],
        created_enrollments=created["enrollments"],
        total_classes=created["total_classes"],
    )


@router.get("/faculty/profile", response_model=schemas.FacultyProfileOut)
def get_faculty_profile(
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.FACULTY)),
):
    if not current_user.faculty_id:
        raise HTTPException(status_code=403, detail="Faculty account is not linked correctly")

    faculty = db.get(models.Faculty, current_user.faculty_id)
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")

    return _faculty_profile_out(faculty)


@router.put("/faculty/profile", response_model=schemas.FacultyProfileOut)
def update_faculty_profile(
    payload: schemas.FacultyProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.FACULTY)),
):
    if not current_user.faculty_id:
        raise HTTPException(status_code=403, detail="Faculty account is not linked correctly")

    faculty = db.get(models.Faculty, current_user.faculty_id)
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")

    if (
        payload.name is None
        and payload.faculty_identifier is None
        and payload.section is None
        and payload.photo_data_url is None
    ):
        raise HTTPException(status_code=400, detail="Provide name, faculty_identifier, section, and/or photo_data_url")

    changed, _ = _apply_faculty_profile_update(faculty, payload, db=db)
    if changed:
        db.commit()
    else:
        db.flush()

    _sync_faculty_to_mongo(faculty, source="faculty-profile-update")

    try:
        mongo_db = get_mongo_db(required=True)
        mongo_db["auth_users"].update_one(
            {"id": int(current_user.id)},
            {"$set": {"name": faculty.name}},
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    mirror_document(
        "faculty_profiles",
        {
            "faculty_id": faculty.id,
            "name": faculty.name,
            "faculty_identifier": faculty.faculty_identifier,
            "section": faculty.section,
            "section_updated_at": faculty.section_updated_at,
            "profile_photo_object_key": faculty.profile_photo_object_key,
            "profile_photo_fingerprint": _photo_fingerprint(
                faculty.profile_photo_object_key or faculty.profile_photo_data_url
            ),
            "profile_photo_size": len(faculty.profile_photo_object_key or faculty.profile_photo_data_url or ""),
            "profile_photo_updated_at": faculty.profile_photo_updated_at,
            "profile_photo_locked_until": faculty.profile_photo_locked_until,
            "source": "faculty-portal",
            "updated_at": datetime.utcnow(),
        },
        upsert_filter={"faculty_id": faculty.id},
    )

    return _faculty_profile_out(faculty)


@router.put("/faculty/students/{student_id}/section", response_model=schemas.StudentProfileOut)
def faculty_update_student_section(
    student_id: int,
    payload: schemas.FacultyStudentSectionUpdateRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    student = db.get(models.Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    target_section = _normalize_section_token(payload.section)
    current_section = re.sub(r"\s+", "", str(student.section or "").strip().upper())
    if target_section == current_section:
        return _student_profile_out(student)

    now_dt = datetime.utcnow()
    can_change_section_now, _, section_lock_minutes_remaining = _student_section_lock_state(student, now_dt)
    is_admin_actor = current_user.role == models.UserRole.ADMIN
    if current_section and not can_change_section_now and not is_admin_actor:
        raise HTTPException(
            status_code=423,
            detail=(
                "Student section can be changed only once every 48 hours. "
                f"Try again in {section_lock_minutes_remaining} minute(s)."
            ),
        )

    if current_user.role == models.UserRole.FACULTY:
        if not current_user.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty account is not linked correctly")
        faculty = db.get(models.Faculty, current_user.faculty_id)
        if not faculty:
            raise HTTPException(status_code=404, detail="Faculty not found")
        allowed_sections = _faculty_allowed_sections(faculty.section)
        if not allowed_sections:
            raise HTTPException(
                status_code=403,
                detail="Set your faculty section before approving student section updates.",
            )
        if target_section not in allowed_sections:
            raise HTTPException(
                status_code=403,
                detail="Faculty can update students only to their own section scope.",
            )

    student.section = target_section
    student.section_updated_at = now_dt
    db.commit()

    _sync_student_to_mongo(student, source="faculty-approved-section-update")
    mirror_document(
        "student_section_updates",
        {
            "student_id": student.id,
            "student_email": student.email,
            "previous_section": current_section or None,
            "new_section": target_section,
            "updated_at": now_dt,
            "approved_by_user_id": current_user.id,
            "approved_by_faculty_id": current_user.faculty_id,
            "source": "faculty-approval",
        },
        upsert_filter={"student_id": student.id},
    )

    return _student_profile_out(student)


@router.get("/student/profile-photo", response_model=schemas.StudentProfilePhotoOut)
def get_student_profile_photo(
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    student = db.get(models.Student, current_user.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    return _student_photo_out(student)


@router.get("/student/profile", response_model=schemas.StudentProfileOut)
def get_student_profile(
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    student = db.get(models.Student, current_user.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    return _student_profile_out(student)


@router.put("/student/profile", response_model=schemas.StudentProfileOut)
def update_student_profile(
    payload: schemas.StudentProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    student = db.get(models.Student, current_user.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    had_registration_number = bool((student.registration_number or "").strip())
    had_enrollment_video = bool(student.enrollment_video_template_json)

    if (
        payload.name is None
        and payload.registration_number is None
        and payload.photo_data_url is None
        and payload.section is None
    ):
        raise HTTPException(status_code=400, detail="Provide name, registration_number, section, and/or photo_data_url")

    changed, photo_changed = _apply_student_profile_update(student, payload, db=db)
    if photo_changed:
        _rebuild_profile_face_template(db, student)
        changed = True
    if changed:
        db.commit()
    else:
        db.flush()

    _sync_student_to_mongo(student, source="student-profile-update")

    try:
        mongo_db = get_mongo_db(required=True)
        mongo_db["auth_users"].update_one(
            {"id": int(current_user.id)},
            {"$set": {"name": student.name}},
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    mirror_document(
        "student_profile_faces",
        {
            "student_id": student.id,
            "name": student.name,
            "registration_number": student.registration_number,
            "profile_photo_object_key": student.profile_photo_object_key,
            "profile_photo_fingerprint": _photo_fingerprint(
                student.profile_photo_object_key or student.profile_photo_data_url
            ),
            "profile_photo_size": len(student.profile_photo_object_key or student.profile_photo_data_url or ""),
            "profile_photo_updated_at": student.profile_photo_updated_at,
            "profile_photo_locked_until": student.profile_photo_locked_until,
            "profile_face_template_fingerprint": _photo_fingerprint(student.profile_face_template_json),
            "profile_face_template_updated_at": student.profile_face_template_updated_at,
            "source": "student-portal",
            "updated_at": datetime.utcnow(),
        },
        upsert_filter={"student_id": student.id},
    )

    registration_completed_now = (not had_registration_number) and bool((student.registration_number or "").strip())
    if had_enrollment_video and (photo_changed or registration_completed_now):
        _maybe_run_identity_screening_for_student(
            db,
            student,
            trigger="student_profile_update",
        )

    return _student_profile_out(student)


@router.put("/student/profile-photo", response_model=schemas.StudentProfilePhotoOut)
def update_student_profile_photo(
    payload: schemas.StudentProfilePhotoUpdate,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    student = db.get(models.Student, current_user.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    had_enrollment_video = bool(student.enrollment_video_template_json)

    changed, photo_changed = _apply_student_profile_update(
        student,
        schemas.StudentProfileUpdateRequest(photo_data_url=payload.photo_data_url),
        db=db,
    )
    if photo_changed:
        _rebuild_profile_face_template(db, student)
        changed = True
    if changed:
        db.commit()
    else:
        db.flush()

    _sync_student_to_mongo(student, source="student-profile-update")

    mirror_document(
        "student_profile_faces",
        {
            "student_id": student.id,
            "profile_photo_object_key": student.profile_photo_object_key,
            "profile_photo_fingerprint": _photo_fingerprint(
                student.profile_photo_object_key or student.profile_photo_data_url
            ),
            "profile_photo_size": len(student.profile_photo_object_key or student.profile_photo_data_url or ""),
            "profile_photo_updated_at": student.profile_photo_updated_at,
            "profile_photo_locked_until": student.profile_photo_locked_until,
            "profile_face_template_fingerprint": _photo_fingerprint(student.profile_face_template_json),
            "profile_face_template_updated_at": student.profile_face_template_updated_at,
            "source": "student-portal",
            "updated_at": datetime.utcnow(),
        },
        upsert_filter={"student_id": student.id},
    )

    if had_enrollment_video and photo_changed:
        _maybe_run_identity_screening_for_student(
            db,
            student,
            trigger="student_profile_photo_update",
        )

    return _student_photo_out(student)


@router.put("/student/enrollment-video", response_model=schemas.StudentEnrollmentVideoOut)
def update_student_enrollment_video(
    payload: schemas.StudentEnrollmentVideoRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    student = db.get(models.Student, current_user.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if not student.registration_number or not _student_profile_photo_data_url(db, student):
        raise HTTPException(
            status_code=400,
            detail="Complete profile setup (registration number + face photo) before enrollment video",
        )

    now_dt = datetime.utcnow()
    can_update_now, locked_until, lock_days_remaining = _enrollment_lock_state(student, now_dt)
    if student.enrollment_video_template_json and not can_update_now:
        raise HTTPException(status_code=423, detail=ENROLLMENT_VIDEO_LOCK_MESSAGE)

    if len(payload.frames_data_urls) < 8:
        raise HTTPException(status_code=400, detail="At least 8 frames are required for enrollment")

    try:
        template = build_enrollment_template_from_frames(payload.frames_data_urls)
    except ValueError as exc:
        detail = str(exc).strip() or "Unable to process enrollment video"
        status_code = 503 if "opencv not installed" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    template_quality = template.get("quality", {}) if isinstance(template, dict) else {}
    valid_frames_total = int(
        template_quality.get("valid_frames_total")
        or template_quality.get("valid_frames_used")
        or len(template.get("embeddings", []))
    )
    valid_frames_used = int(
        template_quality.get("valid_frames_used")
        or min(valid_frames_total, len(template.get("embeddings", [])))
    )
    if valid_frames_total < 8:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Insufficient valid enrollment frames ({valid_frames_total}/8). "
                "Ensure one clear face with slight head movement."
            ),
        )

    student.enrollment_video_template_json = json.dumps(template)
    student.enrollment_video_updated_at = now_dt
    student.enrollment_video_locked_until = now_dt + timedelta(days=ENROLLMENT_VIDEO_LOCK_DAYS)

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("student_enrollment_video_persist_failed student_id=%s", student.id)
        raise HTTPException(
            status_code=500,
            detail="Enrollment video could not be persisted. Retry after checking database storage health.",
        ) from exc

    _sync_student_to_mongo(student, source="student-enrollment-video")

    mirror_document(
        "student_enrollment_videos",
        {
            "student_id": student.id,
            "valid_frames": valid_frames_total,
            "total_frames_received": len(payload.frames_data_urls),
            "enrollment_template_fingerprint": _photo_fingerprint(student.enrollment_video_template_json),
            "enrollment_video_updated_at": student.enrollment_video_updated_at,
            "enrollment_video_locked_until": student.enrollment_video_locked_until,
            "source": "student-portal",
            "updated_at": datetime.utcnow(),
        },
        upsert_filter={"student_id": student.id},
    )

    _maybe_run_identity_screening_for_student(
        db,
        student,
        trigger="student_enrollment_video_update",
    )

    return schemas.StudentEnrollmentVideoOut(
        has_enrollment_video=True,
        can_update_now=False,
        locked_until=student.enrollment_video_locked_until,
        lock_days_remaining=math.ceil((student.enrollment_video_locked_until - now_dt).total_seconds() / 86400),
        enrollment_updated_at=student.enrollment_video_updated_at,
        message="Enrollment video captured successfully",
        valid_frames_used=valid_frames_used,
        total_frames_received=len(payload.frames_data_urls),
    )


@router.get("/student/enrollment-status", response_model=schemas.StudentEnrollmentStatusOut)
def get_student_enrollment_status(
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    student = db.get(models.Student, current_user.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    can_update_now, locked_until, lock_days_remaining = _enrollment_lock_state(student)
    return schemas.StudentEnrollmentStatusOut(
        has_enrollment_video=bool(student.enrollment_video_template_json),
        can_update_now=can_update_now,
        locked_until=locked_until,
        lock_days_remaining=lock_days_remaining,
        enrollment_updated_at=student.enrollment_video_updated_at,
    )


@router.get("/student/timetable", response_model=schemas.WeeklyTimetableOut)
def get_student_weekly_timetable(
    week_start: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    student = db.get(models.Student, current_user.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    has_existing_enrollment = (
        db.query(models.Enrollment.id)
        .filter(models.Enrollment.student_id == current_user.student_id)
        .first()
        is not None
    )
    if not has_existing_enrollment:
        created = _ensure_default_timetable_for_student(db, student)
        has_default_timetable_changes = any(
            value for key, value in created.items() if key != "total_classes"
        )
        if has_default_timetable_changes:
            db.commit()
        else:
            db.flush()
    else:
        db.flush()

    today = date.today()
    academic_start = _academic_start_date()
    min_week_start = _week_start_for(academic_start)
    requested_week_start = _week_start_for(week_start or today)
    current_week_start = max(requested_week_start, min_week_start)
    current_week_end = current_week_start + timedelta(days=6)

    enrollments = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.student_id == current_user.student_id)
        .all()
    )
    course_ids = [item.course_id for item in enrollments]
    schedules: list[models.ClassSchedule] = []
    if course_ids:
        schedules = (
            db.query(models.ClassSchedule)
            .filter(
                models.ClassSchedule.is_active.is_(True),
                models.ClassSchedule.course_id.in_(course_ids),
            )
            .order_by(models.ClassSchedule.weekday.asc(), models.ClassSchedule.start_time.asc())
            .all()
        )

    now_dt = datetime.now()
    result: list[schemas.TimetableClassOut] = []
    student_section = re.sub(r"\s+", "", str(student.section or "").strip().upper())
    applicable_overrides: list[models.TimetableOverride] = []
    override_filters = [
        (
            (models.TimetableOverride.scope_type == schemas.TimetableOverrideScope.STUDENT.value)
            & (models.TimetableOverride.student_id == current_user.student_id)
        ),
    ]
    if student_section:
        override_filters.append(
            (
                (models.TimetableOverride.scope_type == schemas.TimetableOverrideScope.SECTION.value)
                & (models.TimetableOverride.section == student_section)
            )
        )
    if override_filters:
        applicable_overrides = (
            db.query(models.TimetableOverride)
            .filter(
                models.TimetableOverride.is_active.is_(True),
                or_(*override_filters),
            )
            .order_by(models.TimetableOverride.created_at.asc(), models.TimetableOverride.id.asc())
            .all()
        )

    override_schedule_ids = sorted({int(item.schedule_id) for item in applicable_overrides if item.schedule_id})
    override_schedules_by_id = (
        {
            int(row.id): row
            for row in db.query(models.ClassSchedule)
            .filter(models.ClassSchedule.id.in_(override_schedule_ids))
            .all()
        }
        if override_schedule_ids
        else {}
    )
    section_overrides = [row for row in applicable_overrides if row.scope_type == schemas.TimetableOverrideScope.SECTION.value]
    student_overrides = [row for row in applicable_overrides if row.scope_type == schemas.TimetableOverrideScope.STUDENT.value]
    effective_overrides_by_source: dict[tuple[int, time], tuple[models.TimetableOverride, models.ClassSchedule]] = {}
    for bucket in (section_overrides, student_overrides):
        for override in bucket:
            schedule = override_schedules_by_id.get(int(override.schedule_id))
            if not schedule or not schedule.is_active:
                continue
            source_key = (int(override.source_weekday), override.source_start_time)
            effective_overrides_by_source[source_key] = (override, schedule)

    suppressed_regular_slots = set(effective_overrides_by_source.keys())
    effective_override_targets: dict[tuple[int, time], tuple[models.TimetableOverride, models.ClassSchedule]] = {}
    for override, schedule in effective_overrides_by_source.values():
        target_key = (int(schedule.weekday), schedule.start_time)
        effective_override_targets[target_key] = (override, schedule)

    for schedule in schedules:
        schedule_key = (int(schedule.weekday), schedule.start_time)
        if schedule_key in suppressed_regular_slots or schedule_key in effective_override_targets:
            continue
        item = _build_timetable_class_item(
            db,
            student_id=current_user.student_id,
            current_week_start=current_week_start,
            academic_start=academic_start,
            now_dt=now_dt,
            schedule=schedule,
        )
        if item:
            result.append(item)

    for _, schedule in effective_override_targets.values():
        item = _build_timetable_class_item(
            db,
            student_id=current_user.student_id,
            current_week_start=current_week_start,
            academic_start=academic_start,
            now_dt=now_dt,
            schedule=schedule,
        )
        if item:
            result.append(item)

    targeted_remedial_class_ids = {
        int(row[0])
        for row in (
            db.query(models.RemedialMessage.makeup_class_id)
            .filter(models.RemedialMessage.student_id == current_user.student_id)
            .distinct()
            .all()
        )
        if row and row[0]
    }
    remedial_query = db.query(models.MakeUpClass).filter(
        models.MakeUpClass.is_active.is_(True),
        models.MakeUpClass.class_date >= current_week_start,
        models.MakeUpClass.class_date <= current_week_end,
    )
    if targeted_remedial_class_ids:
        remedial_query = remedial_query.filter(models.MakeUpClass.id.in_(sorted(targeted_remedial_class_ids)))
        remedial_classes = (
            remedial_query
            .order_by(models.MakeUpClass.class_date.asc(), models.MakeUpClass.start_time.asc())
            .all()
        )
    else:
        remedial_classes = []

    for remedial in remedial_classes:
        sections = set(_parse_remedial_sections(remedial.sections_json))
        if sections:
            if not student_section:
                continue
            if student_section not in sections:
                continue

        course = db.get(models.Course, remedial.course_id)
        if not course:
            continue

        class_start = datetime.combine(remedial.class_date, remedial.start_time)
        class_end = datetime.combine(remedial.class_date, remedial.end_time)
        window_minutes = max(1, int(remedial.attendance_open_minutes or 15))
        window_end = class_start + timedelta(minutes=window_minutes)
        is_open_now = class_start <= now_dt <= window_end
        is_active_now = class_start <= now_dt <= class_end
        is_ended_now = now_dt > class_end

        marked = (
            db.query(models.RemedialAttendance.id)
            .filter(
                models.RemedialAttendance.makeup_class_id == remedial.id,
                models.RemedialAttendance.student_id == current_user.student_id,
            )
            .first()
            is not None
        )

        if (remedial.class_mode or "offline") == "online":
            classroom_label = "MyClass Platform | Online"
        else:
            room = (remedial.room_number or "Room TBA").strip() or "Room TBA"
            classroom_label = f"{room} | Offline"

        result.append(
            schemas.TimetableClassOut(
                schedule_id=-int(remedial.id),
                course_id=remedial.course_id,
                course_code=course.code,
                course_title=f"{course.title} (Remedial)",
                weekday=remedial.class_date.weekday(),
                start_time=remedial.start_time,
                end_time=remedial.end_time,
                classroom_label=classroom_label,
                class_date=remedial.class_date,
                is_open_now=is_open_now,
                is_active_now=is_active_now,
                is_ended_now=is_ended_now,
                attendance_status="present" if marked else ("absent" if now_dt > window_end else None),
                class_kind="remedial",
                attendance_window_minutes=window_minutes,
                remedial_class_id=remedial.id,
                remedial_code_required=True,
            )
        )

    result.sort(
        key=lambda item: (
            item.class_date,
            item.start_time,
            item.course_code,
            item.class_kind,
            item.schedule_id,
        )
    )

    return schemas.WeeklyTimetableOut(
        week_start=current_week_start,
        min_navigable_date=academic_start,
        classes=result,
    )


@router.get("/student/attendance-history", response_model=schemas.StudentAttendanceHistoryOut)
def get_student_attendance_history(
    limit: int = Query(default=40, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    academic_start = _academic_start_date()
    now_dt = datetime.now()
    today = now_dt.date()
    materialize_saarthi_attendance(
        db,
        student_id=int(current_user.student_id),
        academic_start=academic_start,
        today=today,
    )
    db.commit()
    fetch_limit = min(365, max(limit * 3, 80))
    submissions = (
        db.query(models.AttendanceSubmission)
        .filter(
            models.AttendanceSubmission.student_id == current_user.student_id,
            models.AttendanceSubmission.class_date >= academic_start,
            models.AttendanceSubmission.class_date <= today,
        )
        .order_by(
            models.AttendanceSubmission.class_date.desc(),
            models.AttendanceSubmission.submitted_at.desc(),
            models.AttendanceSubmission.id.desc(),
        )
        .limit(fetch_limit)
        .all()
    )

    records = (
        db.query(models.AttendanceRecord)
        .filter(
            models.AttendanceRecord.student_id == current_user.student_id,
            models.AttendanceRecord.attendance_date >= academic_start,
            models.AttendanceRecord.attendance_date <= today,
        )
        .order_by(models.AttendanceRecord.attendance_date.desc(), models.AttendanceRecord.id.desc())
        .limit(fetch_limit)
        .all()
    )

    if not submissions and not records:
        return schemas.StudentAttendanceHistoryOut(records=[])

    course_ids = sorted(
        {
            *[item.course_id for item in submissions],
            *[item.course_id for item in records],
        }
    )
    courses = (
        {row.id: row for row in db.query(models.Course).filter(models.Course.id.in_(course_ids)).all()}
        if course_ids
        else {}
    )

    faculty_ids = sorted(
        {
            *[item.faculty_id for item in submissions if item.faculty_id is not None],
            *[item.marked_by_faculty_id for item in records if item.marked_by_faculty_id is not None],
            *[course.faculty_id for course in courses.values() if course.faculty_id is not None],
        }
    )
    faculties = (
        {row.id: row for row in db.query(models.Faculty).filter(models.Faculty.id.in_(faculty_ids)).all()}
        if faculty_ids
        else {}
    )

    schedule_ids = sorted({item.schedule_id for item in submissions})
    schedules_by_id = (
        {
            row.id: row
            for row in db.query(models.ClassSchedule).filter(models.ClassSchedule.id.in_(schedule_ids)).all()
        }
        if schedule_ids
        else {}
    )
    fallback_schedules = (
        db.query(models.ClassSchedule)
        .filter(models.ClassSchedule.course_id.in_(course_ids))
        .order_by(models.ClassSchedule.start_time.asc())
        .all()
        if course_ids
        else []
    )
    schedules_by_course_weekday: dict[tuple[int, int], list[models.ClassSchedule]] = {}
    for schedule in fallback_schedules:
        schedules_by_course_weekday.setdefault((schedule.course_id, schedule.weekday), []).append(schedule)
    for key in list(schedules_by_course_weekday.keys()):
        schedules_by_course_weekday[key].sort(key=lambda item: (item.start_time, item.id))

    submission_keys = {
        (int(item.course_id), item.class_date, int(item.schedule_id))
        for item in submissions
    }
    submission_course_date_keys = {(int(item.course_id), item.class_date) for item in submissions}

    items: list[schemas.StudentAttendanceHistoryItemOut] = []
    for submission in submissions:
        course = courses.get(submission.course_id)
        schedule = schedules_by_id.get(submission.schedule_id)
        faculty = faculties.get(
            submission.faculty_id
            if submission.faculty_id is not None
            else (course.faculty_id if course else None)
        )
        start_t = schedule.start_time if schedule else time(0, 0)
        end_t = schedule.end_time if schedule else time(0, 0)
        status_value = _submission_to_attendance_status(submission.status) or models.AttendanceStatus.ABSENT

        items.append(
            schemas.StudentAttendanceHistoryItemOut(
                schedule_id=submission.schedule_id,
                class_date=submission.class_date,
                start_time=start_t,
                end_time=end_t,
                course_code=course.code if course else f"C-{submission.course_id}",
                course_title=course.title if course else "Unknown Course",
                faculty_name=faculty.name if faculty else "Faculty",
                status=status_value,
                source="attendance-management",
            )
        )

    for record in records:
        course = courses.get(record.course_id)
        faculty = faculties.get(record.marked_by_faculty_id)
        candidate_schedules = [
            schedule
            for schedule in schedules_by_course_weekday.get(
                (int(record.course_id), int(record.attendance_date.weekday())),
                [],
            )
            if record.attendance_date < today
            or (record.attendance_date == today and now_dt.time() >= schedule.start_time)
        ]
        added_schedule_fallback = False
        for schedule in candidate_schedules:
            key = (int(record.course_id), record.attendance_date, int(schedule.id))
            if key in submission_keys:
                continue
            items.append(
                schemas.StudentAttendanceHistoryItemOut(
                    schedule_id=schedule.id,
                    class_date=record.attendance_date,
                    start_time=schedule.start_time,
                    end_time=schedule.end_time,
                    course_code=course.code if course else f"C-{record.course_id}",
                    course_title=course.title if course else "Unknown Course",
                    faculty_name=faculty.name if faculty else "Faculty",
                    status=record.status,
                    source=record.source,
                )
            )
            added_schedule_fallback = True

        if added_schedule_fallback:
            continue
        if (int(record.course_id), record.attendance_date) in submission_course_date_keys:
            continue

        items.append(
            schemas.StudentAttendanceHistoryItemOut(
                schedule_id=None,
                class_date=record.attendance_date,
                start_time=time(0, 0),
                end_time=time(0, 0),
                course_code=course.code if course else f"C-{record.course_id}",
                course_title=course.title if course else "Unknown Course",
                faculty_name=faculty.name if faculty else "Faculty",
                status=record.status,
                source=record.source,
            )
        )

    items.sort(
        key=lambda row: (
            row.class_date,
            row.start_time,
            row.end_time,
            row.course_code,
        ),
        reverse=True,
    )
    return schemas.StudentAttendanceHistoryOut(records=items[:limit])


@router.get("/student/attendance-aggregate", response_model=schemas.StudentAttendanceAggregateOut)
def get_student_attendance_aggregate(
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    academic_start = _academic_start_date()
    now_dt = datetime.now()
    today = now_dt.date()
    materialize_saarthi_attendance(
        db,
        student_id=int(current_user.student_id),
        academic_start=academic_start,
        today=today,
    )
    db.commit()

    enrollments = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.student_id == current_user.student_id)
        .all()
    )
    enrolled_course_ids = {item.course_id for item in enrollments}
    extra_submission_course_ids = {
        int(row[0])
        for row in (
            db.query(models.AttendanceSubmission.course_id)
            .filter(
                models.AttendanceSubmission.student_id == current_user.student_id,
                models.AttendanceSubmission.class_date >= academic_start,
                models.AttendanceSubmission.class_date <= today,
            )
            .distinct()
            .all()
        )
        if row and row[0]
    }
    extra_record_course_ids = {
        int(row[0])
        for row in (
            db.query(models.AttendanceRecord.course_id)
            .filter(
                models.AttendanceRecord.student_id == current_user.student_id,
                models.AttendanceRecord.attendance_date >= academic_start,
                models.AttendanceRecord.attendance_date <= today,
            )
            .distinct()
            .all()
        )
        if row and row[0]
    }
    course_ids = sorted(enrolled_course_ids | extra_submission_course_ids | extra_record_course_ids)
    if not course_ids:
        return schemas.StudentAttendanceAggregateOut(
            aggregate_percent=0.0,
            attended_total=0,
            delivered_total=0,
            courses=[],
        )

    courses = {row.id: row for row in db.query(models.Course).filter(models.Course.id.in_(course_ids)).all()}

    faculty_ids = sorted({course.faculty_id for course in courses.values()})
    faculties = {row.id: row for row in db.query(models.Faculty).filter(models.Faculty.id.in_(faculty_ids)).all()}
    schedules = (
        db.query(models.ClassSchedule)
        .filter(
            models.ClassSchedule.is_active.is_(True),
            models.ClassSchedule.course_id.in_(course_ids),
        )
        .all()
    )
    schedules_by_course: dict[int, list[models.ClassSchedule]] = {}
    for schedule in schedules:
        schedules_by_course.setdefault(schedule.course_id, []).append(schedule)

    submission_rows = (
        db.query(
            models.AttendanceSubmission.course_id,
            models.AttendanceSubmission.schedule_id,
            models.AttendanceSubmission.class_date,
            models.AttendanceSubmission.status,
        )
        .filter(
            models.AttendanceSubmission.student_id == current_user.student_id,
            models.AttendanceSubmission.course_id.in_(course_ids),
            models.AttendanceSubmission.class_date >= academic_start,
            models.AttendanceSubmission.class_date <= today,
        )
        .all()
    )
    delivered_submission_keys: dict[int, set[tuple[int, date]]] = {}
    credited_submission_keys: dict[int, set[tuple[int, date]]] = {}
    submission_schedule_ids_by_course_date: dict[tuple[int, date], set[int]] = {}
    last_attended_map: dict[int, date] = {}
    for course_id, schedule_id, class_date, status_value in submission_rows:
        normalized_course_id = int(course_id)
        normalized_schedule_id = int(schedule_id)
        delivered_submission_keys.setdefault(normalized_course_id, set()).add(
            (normalized_schedule_id, class_date)
        )
        submission_schedule_ids_by_course_date.setdefault(
            (normalized_course_id, class_date),
            set(),
        ).add(normalized_schedule_id)
        submission_status = _submission_to_attendance_status(status_value)
        if submission_status == models.AttendanceStatus.PRESENT:
            credited_submission_keys.setdefault(normalized_course_id, set()).add(
                (normalized_schedule_id, class_date)
            )
            prev_last = last_attended_map.get(normalized_course_id)
            if prev_last is None or class_date > prev_last:
                last_attended_map[normalized_course_id] = class_date

    record_rows = (
        db.query(
            models.AttendanceRecord.course_id,
            models.AttendanceRecord.status,
            models.AttendanceRecord.attendance_date,
        )
        .filter(
            models.AttendanceRecord.student_id == current_user.student_id,
            models.AttendanceRecord.course_id.in_(course_ids),
            models.AttendanceRecord.attendance_date >= academic_start,
            models.AttendanceRecord.attendance_date <= today,
        )
        .all()
    )
    delivered_record_dates: dict[int, set[date]] = {}
    attended_record_fallback_counts: dict[int, int] = {}
    delivered_schedule_ids_cache: dict[tuple[int, date], set[int]] = {}

    def delivered_schedule_ids(course_id: int, class_date: date) -> set[int]:
        key = (int(course_id), class_date)
        cached = delivered_schedule_ids_cache.get(key)
        if cached is not None:
            return cached
        out: set[int] = set()
        for schedule in schedules_by_course.get(int(course_id), []):
            if int(schedule.weekday) != int(class_date.weekday()):
                continue
            if class_date < today or (class_date == today and now_dt.time() >= schedule.start_time):
                out.add(int(schedule.id))
        delivered_schedule_ids_cache[key] = out
        return out

    for course_id, status_value, attendance_date in record_rows:
        normalized_course_id = int(course_id)
        delivered_record_dates.setdefault(normalized_course_id, set()).add(attendance_date)
        submission_schedule_ids = submission_schedule_ids_by_course_date.get(
            (normalized_course_id, attendance_date),
            set(),
        )
        delivered_schedule_ids_for_day = delivered_schedule_ids(normalized_course_id, attendance_date)
        missing_schedule_ids = delivered_schedule_ids_for_day.difference(submission_schedule_ids)
        fallback_slots = len(missing_schedule_ids)
        if not delivered_schedule_ids_for_day and not submission_schedule_ids:
            fallback_slots = 1

        if status_value == models.AttendanceStatus.PRESENT and fallback_slots > 0:
            attended_record_fallback_counts[normalized_course_id] = (
                attended_record_fallback_counts.get(normalized_course_id, 0) + fallback_slots
            )
            prev_last = last_attended_map.get(normalized_course_id)
            if prev_last is None or attendance_date > prev_last:
                last_attended_map[normalized_course_id] = attendance_date

    course_rows: list[schemas.StudentCourseAttendanceAggregateOut] = []
    attended_total = 0
    delivered_total = 0

    for course_id in course_ids:
        course = courses.get(course_id)
        if not course:
            continue

        delivered_by_schedule = sum(
            _count_delivered_occurrences(schedule, from_date=academic_start, now_dt=now_dt)
            for schedule in schedules_by_course.get(course_id, [])
        )
        delivered_by_submissions = len(delivered_submission_keys.get(course_id, set()))
        delivered_by_records = len(delivered_record_dates.get(course_id, set()))
        delivered = max(delivered_by_schedule, delivered_by_submissions, delivered_by_records)
        if delivered <= 0:
            continue

        attended = (
            len(credited_submission_keys.get(course_id, set()))
            + attended_record_fallback_counts.get(course_id, 0)
        )
        if delivered > 0 and attended > delivered:
            attended = delivered
        last_attended = last_attended_map.get(course_id)

        percent = round((attended / delivered) * 100, 2) if delivered else 0.0
        attended_total += attended
        delivered_total += delivered

        faculty = faculties.get(course.faculty_id)
        course_rows.append(
            schemas.StudentCourseAttendanceAggregateOut(
                course_id=course.id,
                course_code=course.code,
                course_title=course.title,
                faculty_name=faculty.name if faculty else "Faculty",
                attended_classes=attended,
                delivered_classes=delivered,
                attendance_percent=percent,
                last_attended_on=last_attended,
            )
        )

    aggregate_percent = round((attended_total / delivered_total) * 100, 2) if delivered_total else 0.0

    return schemas.StudentAttendanceAggregateOut(
        aggregate_percent=aggregate_percent,
        attended_total=attended_total,
        delivered_total=delivered_total,
        courses=sorted(course_rows, key=lambda row: row.course_code),
    )


@router.get("/student/recovery-plans", response_model=schemas.AttendanceRecoveryPlanListOut)
def get_student_recovery_plan_list(
    include_resolved: bool = Query(default=False),
    limit: int = Query(default=12, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    plans = get_student_recovery_plans(
        db,
        student_id=int(current_user.student_id),
        include_resolved=bool(include_resolved),
        limit=int(limit),
    )
    return schemas.AttendanceRecoveryPlanListOut(
        plans=_serialize_recovery_plan_rows(db, plans),
        last_updated_at=datetime.utcnow(),
    )


@router.post(
    "/student/recovery-actions/{action_id}/acknowledge",
    response_model=schemas.AttendanceRecoveryActionUpdateOut,
)
def acknowledge_student_recovery_action(
    action_id: int,
    payload: schemas.AttendanceRecoveryActionUpdateRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")
    try:
        action = update_student_recovery_action(
            db,
            action_id=int(action_id),
            student_id=int(current_user.student_id),
            new_status=models.AttendanceRecoveryActionStatus.ACKNOWLEDGED,
            note=payload.note,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.commit()
    publish_domain_event(
        "attendance.recovery.acknowledged",
        payload={
            "action_id": int(action.id),
            "plan_id": int(action.plan_id),
            "student_id": int(current_user.student_id),
        },
        scopes={
            f"student:{int(current_user.student_id)}",
            "role:admin",
        },
        topics={"attendance"},
        actor={
            "user_id": int(current_user.id),
            "role": current_user.role.value,
        },
        source="attendance",
    )
    return schemas.AttendanceRecoveryActionUpdateOut(
        action_id=int(action.id),
        status=action.status,
        completed_at=action.completed_at,
        outcome_note=action.outcome_note,
    )


@router.post(
    "/student/recovery-actions/{action_id}/complete",
    response_model=schemas.AttendanceRecoveryActionUpdateOut,
)
def complete_student_recovery_action(
    action_id: int,
    payload: schemas.AttendanceRecoveryActionUpdateRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")
    try:
        action = update_student_recovery_action(
            db,
            action_id=int(action_id),
            student_id=int(current_user.student_id),
            new_status=models.AttendanceRecoveryActionStatus.COMPLETED,
            note=payload.note,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.commit()
    publish_domain_event(
        "attendance.recovery.completed",
        payload={
            "action_id": int(action.id),
            "plan_id": int(action.plan_id),
            "student_id": int(current_user.student_id),
        },
        scopes={
            f"student:{int(current_user.student_id)}",
            "role:admin",
        },
        topics={"attendance"},
        actor={
            "user_id": int(current_user.id),
            "role": current_user.role.value,
        },
        source="attendance",
    )
    return schemas.AttendanceRecoveryActionUpdateOut(
        action_id=int(action.id),
        status=action.status,
        completed_at=action.completed_at,
        outcome_note=action.outcome_note,
    )


@router.get(
    "/student/rectification-requests",
    response_model=schemas.StudentAttendanceRectificationListOut,
)
def list_student_rectification_requests(
    limit: int = Query(default=80, ge=1, le=300),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    rows = (
        db.query(models.AttendanceRectificationRequest)
        .filter(models.AttendanceRectificationRequest.student_id == current_user.student_id)
        .order_by(
            models.AttendanceRectificationRequest.requested_at.desc(),
            models.AttendanceRectificationRequest.id.desc(),
        )
        .limit(limit)
        .all()
    )
    if not rows:
        return schemas.StudentAttendanceRectificationListOut(requests=[])

    course_ids = sorted({item.course_id for item in rows})
    courses = (
        {row.id: row for row in db.query(models.Course).filter(models.Course.id.in_(course_ids)).all()}
        if course_ids
        else {}
    )
    faculty_ids = sorted(
        {
            *[item.faculty_id for item in rows],
            *[course.faculty_id for course in courses.values()],
        }
    )
    faculties = (
        {row.id: row for row in db.query(models.Faculty).filter(models.Faculty.id.in_(faculty_ids)).all()}
        if faculty_ids
        else {}
    )

    requests: list[schemas.StudentAttendanceRectificationOut] = []
    for item in rows:
        course = courses.get(item.course_id)
        fallback_faculty_id = course.faculty_id if course else None
        faculty = faculties.get(item.faculty_id) or faculties.get(fallback_faculty_id)
        requests.append(
            _student_rectification_out(
                item,
                course=course,
                faculty=faculty,
            )
        )
    return schemas.StudentAttendanceRectificationListOut(requests=requests)


@router.post(
    "/student/rectification-requests",
    response_model=schemas.StudentAttendanceRectificationOut,
    status_code=status.HTTP_201_CREATED,
)
def create_student_rectification_request(
    payload: schemas.AttendanceRectificationRequestCreate,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    student = db.get(models.Student, current_user.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    course = db.get(models.Course, payload.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Subject not found")

    is_enrolled = (
        db.query(models.Enrollment.id)
        .filter(
            models.Enrollment.student_id == current_user.student_id,
            models.Enrollment.course_id == payload.course_id,
        )
        .first()
        is not None
    )
    if not is_enrolled:
        raise HTTPException(status_code=403, detail="Student is not enrolled in this subject")

    today = date.today()
    if payload.class_date > today:
        raise HTTPException(status_code=400, detail="Rectification request cannot be created for future classes")

    schedule = _resolve_schedule_for_rectification(
        db=db,
        course_id=payload.course_id,
        class_date=payload.class_date,
        preferred_start_time=payload.start_time,
    )

    already_present_submission = (
        db.query(models.AttendanceSubmission.id)
        .filter(
            models.AttendanceSubmission.student_id == current_user.student_id,
            models.AttendanceSubmission.course_id == payload.course_id,
            models.AttendanceSubmission.class_date == payload.class_date,
            models.AttendanceSubmission.status.in_(_CREDITED_SUBMISSION_STATUSES),
        )
        .first()
        is not None
    )
    already_present_record = (
        db.query(models.AttendanceRecord.id)
        .filter(
            models.AttendanceRecord.student_id == current_user.student_id,
            models.AttendanceRecord.course_id == payload.course_id,
            models.AttendanceRecord.attendance_date == payload.class_date,
            models.AttendanceRecord.status == models.AttendanceStatus.PRESENT,
        )
        .first()
        is not None
    )
    if already_present_submission or already_present_record:
        raise HTTPException(status_code=400, detail="Attendance is already marked present for this class")

    proof_note = str(payload.proof_note or "").strip()
    if len(proof_note) < 10:
        raise HTTPException(status_code=400, detail="Please provide proper proof details for rectification")
    proof_photo = (payload.proof_photo_data_url or "").strip() or None
    if proof_photo and not proof_photo.startswith("data:image/"):
        raise HTTPException(status_code=400, detail="proof_photo_data_url must be an image data URL")
    proof_photo_object_key: str | None = None
    if proof_photo:
        proof_media = store_data_url_object(
            db,
            owner_table="attendance_rectification_requests",
            owner_id=int(current_user.student_id),
            media_kind="attendance-rectification-proof",
            data_url=proof_photo,
            retention_days=ATTENDANCE_MEDIA_RETENTION_DAYS,
        )
        proof_photo_object_key = proof_media.object_key

    request = (
        db.query(models.AttendanceRectificationRequest)
        .filter(
            models.AttendanceRectificationRequest.student_id == current_user.student_id,
            models.AttendanceRectificationRequest.schedule_id == schedule.id,
            models.AttendanceRectificationRequest.class_date == payload.class_date,
        )
        .first()
    )

    source = "student-rectification-request-create"
    if request is None:
        request = models.AttendanceRectificationRequest(
            student_id=current_user.student_id,
            faculty_id=schedule.faculty_id,
            course_id=schedule.course_id,
            schedule_id=schedule.id,
            class_date=payload.class_date,
            class_start_time=schedule.start_time,
            class_end_time=schedule.end_time,
            proof_note=proof_note,
            proof_photo_data_url=None,
            proof_photo_object_key=proof_photo_object_key,
            status=models.AttendanceRectificationStatus.PENDING,
        )
        db.add(request)
    else:
        if request.status == models.AttendanceRectificationStatus.APPROVED:
            raise HTTPException(status_code=400, detail="Rectification already approved for this class")
        request.faculty_id = schedule.faculty_id
        request.course_id = schedule.course_id
        request.class_start_time = schedule.start_time
        request.class_end_time = schedule.end_time
        request.proof_note = proof_note
        previous_key = str(request.proof_photo_object_key or "").strip() or None
        request.proof_photo_data_url = None
        request.proof_photo_object_key = proof_photo_object_key
        if previous_key and previous_key != proof_photo_object_key:
            mark_media_deleted(db, previous_key)
        request.status = models.AttendanceRectificationStatus.PENDING
        request.requested_at = datetime.utcnow()
        request.reviewed_at = None
        request.reviewed_by_faculty_id = None
        request.review_note = None
        source = "student-rectification-request-refresh"

    db.commit()
    db.refresh(request)

    _sync_rectification_request_to_mongo(request, source=source)
    faculty = db.get(models.Faculty, request.faculty_id)

    return _student_rectification_out(
        request,
        course=course,
        faculty=faculty,
    )


def _resolve_student_schedule_context(
    *,
    db: Session,
    current_user: models.AuthUser,
    schedule_id: int,
) -> tuple[models.Student, models.ClassSchedule, models.Course]:
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    student = db.get(models.Student, current_user.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if not student.registration_number:
        raise HTTPException(status_code=400, detail="Complete profile setup with registration number before attendance")

    if not (student.profile_photo_object_key or student.profile_photo_data_url):
        raise HTTPException(status_code=400, detail="Upload profile photo before marking attendance")
    if not student.enrollment_video_template_json:
        raise HTTPException(status_code=400, detail="Complete one-time enrollment video before marking attendance")

    schedule = db.get(models.ClassSchedule, schedule_id)
    if not schedule or not schedule.is_active:
        raise HTTPException(status_code=404, detail="Class schedule not found")
    course = db.get(models.Course, schedule.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found for schedule")

    student_section = re.sub(r"\s+", "", str(student.section or "").strip().upper())
    override_filters = [
        (
            (models.TimetableOverride.scope_type == schemas.TimetableOverrideScope.STUDENT.value)
            & (models.TimetableOverride.student_id == current_user.student_id)
        ),
    ]
    if student_section:
        override_filters.append(
            (
                (models.TimetableOverride.scope_type == schemas.TimetableOverrideScope.SECTION.value)
                & (models.TimetableOverride.section == student_section)
            )
        )
    applicable_overrides = (
        db.query(models.TimetableOverride)
        .filter(
            models.TimetableOverride.is_active.is_(True),
            or_(*override_filters),
        )
        .order_by(models.TimetableOverride.created_at.asc(), models.TimetableOverride.id.asc())
        .all()
    )
    section_overrides = [row for row in applicable_overrides if row.scope_type == schemas.TimetableOverrideScope.SECTION.value]
    student_overrides = [row for row in applicable_overrides if row.scope_type == schemas.TimetableOverrideScope.STUDENT.value]
    effective_overrides_by_source: dict[tuple[int, time], models.TimetableOverride] = {}
    for bucket in (section_overrides, student_overrides):
        for override in bucket:
            effective_overrides_by_source[(int(override.source_weekday), override.source_start_time)] = override

    schedule_key = (int(schedule.weekday), schedule.start_time)
    slot_suppressed = False
    allowed_via_override = False
    for source_key, override in effective_overrides_by_source.items():
        target_schedule = db.get(models.ClassSchedule, override.schedule_id)
        if not target_schedule or not target_schedule.is_active:
            continue
        if source_key == schedule_key and int(target_schedule.id) != int(schedule.id):
            slot_suppressed = True
        if int(target_schedule.id) == int(schedule.id):
            allowed_via_override = True

    if slot_suppressed and not allowed_via_override:
        raise HTTPException(status_code=403, detail="This class slot is not assigned in the student's active timetable")

    is_enrolled = (
        db.query(models.Enrollment)
        .filter(
            models.Enrollment.student_id == current_user.student_id,
            models.Enrollment.course_id == schedule.course_id,
        )
        .first()
    )
    if not is_enrolled and not allowed_via_override:
        raise HTTPException(status_code=403, detail="Student is not enrolled in this class")

    return student, schedule, course


def _verify_student_face_payload(
    *,
    db: Session,
    student: models.Student,
    schedule: models.ClassSchedule,
    payload: schemas.RealtimeAttendanceMarkRequest,
) -> tuple[str, float, str, models.AttendanceSubmissionStatus, str]:
    selfie_frames = payload.selfie_frames_data_urls or []
    primary_selfie = payload.selfie_photo_data_url
    if not primary_selfie and selfie_frames:
        primary_selfie = selfie_frames[0]
    if not primary_selfie:
        raise HTTPException(status_code=400, detail="selfie_photo_data_url is required")
    if not selfie_frames:
        selfie_frames = [primary_selfie]

    if len(selfie_frames) < FACE_MULTI_FRAME_MIN:
        raise HTTPException(
            status_code=400,
            detail=f"Capture at least {FACE_MULTI_FRAME_MIN} frames for secure facial attendance verification",
        )

    enrollment_template = _parse_face_template(student.enrollment_video_template_json)
    profile_template = _parse_face_template(student.profile_face_template_json)
    combined_template = _merge_face_templates(enrollment_template, profile_template)
    profile_photo_data_url = _student_profile_photo_data_url(db, student)
    if not profile_photo_data_url:
        raise HTTPException(status_code=400, detail="Upload profile photo before marking attendance")
    if combined_template is None:
        raise HTTPException(
            status_code=400,
            detail="Complete one-time enrollment video before marking attendance",
        )
    if profile_template is None and profile_photo_data_url:
        logger.warning(
            "profile_template_missing_or_invalid student=%s rebuilding-on-the-fly",
            student.email,
        )
        try:
            profile_template = build_profile_face_template(profile_photo_data_url)
        except ValueError:
            profile_template = None
        combined_template = _merge_face_templates(enrollment_template, profile_template)

    # Backend OpenCV verification is mandatory for attendance marking.
    opencv_verdict = verify_face_sequence_opencv(
        profile_photo_data_url,
        selfie_frames,
        subject_label=student.email,
        profile_template=combined_template,
    )
    if not bool(opencv_verdict.get("available")):
        reason = str(opencv_verdict.get("reason", "OpenCV verification unavailable"))
        raise HTTPException(status_code=503, detail=f"OpenCV verification unavailable: {reason}")

    final_confidence = max(0.0, min(1.0, float(opencv_verdict.get("confidence", 0.0))))
    final_engine = str(opencv_verdict.get("engine") or "opencv-embedding")
    final_reason = str(opencv_verdict.get("reason") or "Face not recognized")
    final_match = bool(opencv_verdict.get("match")) and final_confidence >= FACE_MATCH_PASS_THRESHOLD

    ai_verdict = _client_ai_verdict(payload)
    if ai_verdict:
        logger.info(
            "attendance_client_ai_observation student=%s schedule_id=%s ai_match=%s ai_confidence=%.4f ai_reason=%s",
            student.email,
            schedule.id,
            bool(ai_verdict.get("match")),
            float(ai_verdict.get("confidence", 0.0)),
            str(ai_verdict.get("reason") or ""),
        )

    status_value = (
        models.AttendanceSubmissionStatus.VERIFIED
        if final_match and final_confidence >= FACE_MATCH_PASS_THRESHOLD
        else models.AttendanceSubmissionStatus.REJECTED
    )
    liveness_meta = opencv_verdict.get("liveness", {})
    liveness_ok = bool((liveness_meta or {}).get("ok"))
    required_frames = int(opencv_verdict.get("required_consecutive_frames", FACE_MULTI_FRAME_MIN))
    matched_frames = int(opencv_verdict.get("consecutive_frames_matched", 0))
    accepted_frames = int(opencv_verdict.get("accepted_frames", 0))
    total_frames = int(opencv_verdict.get("total_frames", len(selfie_frames)))
    logger.info(
        "attendance_security_audit ts=%s student=%s schedule_id=%s confidence=%.4f threshold=%.2f decision=%s "
        "engine=%s streak=%s/%s accepted=%s/%s liveness=%s reason=%s",
        datetime.utcnow().isoformat(),
        student.email,
        schedule.id,
        final_confidence,
        FACE_MATCH_PASS_THRESHOLD,
        status_value.value,
        final_engine,
        matched_frames,
        required_frames,
        accepted_frames,
        total_frames,
        liveness_ok,
        final_reason,
    )
    return primary_selfie, final_confidence, final_engine, status_value, final_reason


def _public_rejection_message(reason: str, confidence: float | None = None) -> str:
    text = str(reason or "").strip().lower()
    score = max(0.0, min(1.0, float(confidence or 0.0)))
    if not text:
        return "Face not recognized"
    if "multiple faces" in text:
        return "Multiple faces detected. Keep only one face in frame."
    if "centered" in text:
        return "Face not centered. Keep your face in the center."
    if "blurry" in text:
        return "Face is blurry. Hold still and improve lighting."
    if "resolution" in text:
        return "Camera quality is too low. Move closer and use a higher resolution frame."
    if "lighting" in text or "contrast" in text:
        return "Lighting is poor. Move to a brighter area and keep front light on face."
    if "covered" in text or "occluded" in text:
        return "Face appears covered. Keep full face visible."
    if "liveness" in text:
        return "Liveness check failed. Move head left/right/up/down and retry."
    if "landmark" in text or "eye" in text:
        return "Face landmarks not stable. Look straight at camera."
    if "spoof" in text:
        return "Unauthorized marking attempt detected. Live presence check failed."
    if "consistency failed" in text:
        return "Face verification consistency failed across live frames. Keep face centered and retry."
    if score < 0.35:
        return "Unauthorized marking attempt detected. Different person identified."
    if score < FACE_MATCH_PASS_THRESHOLD:
        return "Face almost matched. Move to brighter light, align straight, and retry."
    return "Face not recognized. Move to brighter light and retry."


@router.post("/realtime/mark", response_model=schemas.RealtimeAttendanceMarkResponse)
def mark_realtime_attendance(
    payload: schemas.RealtimeAttendanceMarkRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    student, schedule, course = _resolve_student_schedule_context(
        db=db,
        current_user=current_user,
        schedule_id=payload.schedule_id,
    )

    today = date.today()
    if schedule.weekday != today.weekday():
        raise HTTPException(status_code=400, detail="This class is not scheduled for today")

    now_dt = datetime.now()
    is_open_now, _, _ = _window_flags(schedule, now_dt, today, course=course)
    if not is_open_now:
        raise HTTPException(status_code=400, detail="Attendance window is closed (only first 10 minutes)")
    primary_selfie, final_confidence, final_engine, status_value, final_reason = _verify_student_face_payload(
        db=db,
        student=student,
        schedule=schedule,
        payload=payload,
    )
    final_match = status_value == models.AttendanceSubmissionStatus.VERIFIED

    submission = (
        db.query(models.AttendanceSubmission)
        .filter(
            models.AttendanceSubmission.schedule_id == schedule.id,
            models.AttendanceSubmission.student_id == current_user.student_id,
            models.AttendanceSubmission.class_date == today,
        )
        .first()
    )

    if not submission:
        selfie_media = store_data_url_object(
            db,
            owner_table="attendance_submissions",
            owner_id=int(current_user.student_id or 0),
            media_kind="attendance-selfie",
            data_url=primary_selfie,
            retention_days=ATTENDANCE_MEDIA_RETENTION_DAYS,
        )
        submission = models.AttendanceSubmission(
            schedule_id=schedule.id,
            course_id=schedule.course_id,
            faculty_id=schedule.faculty_id,
            student_id=current_user.student_id,
            class_date=today,
            selfie_photo_data_url=None,
            selfie_photo_object_key=selfie_media.object_key,
            ai_match=final_match,
            ai_confidence=final_confidence,
            ai_model=final_engine,
            ai_reason=final_reason,
            status=status_value,
        )
        db.add(submission)
    else:
        if submission.status in (
            models.AttendanceSubmissionStatus.VERIFIED,
            models.AttendanceSubmissionStatus.APPROVED,
        ):
            return schemas.RealtimeAttendanceMarkResponse(
                submission_id=submission.id,
                status=submission.status,
                requires_faculty_review=False,
                message="Attendance already verified for this class",
                verification_engine=submission.ai_model or "previous-verification",
                verification_confidence=float(submission.ai_confidence or 0.0),
                verification_reason=submission.ai_reason,
            )

        previous_selfie_key = str(submission.selfie_photo_object_key or "").strip() or None
        selfie_media = store_data_url_object(
            db,
            owner_table="attendance_submissions",
            owner_id=int(current_user.student_id or 0),
            media_kind="attendance-selfie",
            data_url=primary_selfie,
            retention_days=ATTENDANCE_MEDIA_RETENTION_DAYS,
        )
        submission.selfie_photo_data_url = None
        submission.selfie_photo_object_key = selfie_media.object_key
        if previous_selfie_key and previous_selfie_key != selfie_media.object_key:
            mark_media_deleted(db, previous_selfie_key)
        submission.ai_match = final_match
        submission.ai_confidence = final_confidence
        submission.ai_model = final_engine
        submission.ai_reason = final_reason
        submission.status = status_value
        submission.submitted_at = datetime.utcnow()
        submission.reviewed_at = None
        submission.reviewed_by_faculty_id = None
        submission.review_note = None

    db.flush()

    if status_value == models.AttendanceSubmissionStatus.VERIFIED:
        _upsert_present_attendance(
            db,
            student_id=current_user.student_id,
            course_id=schedule.course_id,
            faculty_id=schedule.faculty_id,
            class_date=today,
            source="face-opencv-primary-verified",
        )

    db.commit()

    _upsert_mongo_by_id(
        "attendance_submissions",
        submission.id,
        {
            "schedule_id": submission.schedule_id,
            "course_id": submission.course_id,
            "faculty_id": submission.faculty_id,
            "student_id": submission.student_id,
            "class_date": submission.class_date.isoformat(),
            "status": submission.status.value,
            "ai_match": submission.ai_match,
            "ai_confidence": submission.ai_confidence,
            "ai_model": submission.ai_model,
            "ai_reason": submission.ai_reason,
            "selfie_photo_object_key": submission.selfie_photo_object_key,
            "selfie_photo_fingerprint": _photo_fingerprint(
                submission.selfie_photo_object_key or submission.selfie_photo_data_url
            ),
            "submitted_at": submission.submitted_at,
            "source": "attendance-management",
        },
    )
    publish_domain_event(
        "attendance.marked",
        payload={
            "submission_id": int(submission.id),
            "student_id": int(submission.student_id),
            "faculty_id": int(submission.faculty_id),
            "schedule_id": int(submission.schedule_id),
            "course_id": int(submission.course_id),
            "class_date": submission.class_date.isoformat(),
            "status": submission.status.value,
            "ai_confidence": float(submission.ai_confidence or 0.0),
        },
        scopes={
            f"student:{int(submission.student_id)}",
            f"faculty:{int(submission.faculty_id)}",
            "role:admin",
        },
        topics={"attendance"},
        actor={
            "user_id": int(current_user.id),
            "student_id": int(current_user.student_id or 0),
            "role": current_user.role.value,
        },
        source="attendance",
    )
    enqueue_face_reverification(
        {
            "submission_id": int(submission.id),
            "student_id": int(submission.student_id),
            "schedule_id": int(submission.schedule_id),
            "class_date": submission.class_date.isoformat(),
        }
    )
    enqueue_recompute(
        {
            "entity": "student_attendance_aggregate",
            "student_id": int(submission.student_id),
            "source": "attendance.marked",
        }
    )

    return schemas.RealtimeAttendanceMarkResponse(
        submission_id=submission.id,
        status=status_value,
        requires_faculty_review=False,
        message=(
            "Attendance verified automatically"
            if status_value == models.AttendanceSubmissionStatus.VERIFIED
            else _public_rejection_message(final_reason, final_confidence)
        ),
        verification_engine=final_engine,
        verification_confidence=final_confidence,
        verification_reason=final_reason,
    )


@router.get("/faculty/schedules", response_model=list[schemas.ClassScheduleOut])
def get_faculty_schedules(
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    query = db.query(models.ClassSchedule).filter(models.ClassSchedule.is_active.is_(True))
    if current_user.role == models.UserRole.FACULTY:
        if not current_user.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty account is not linked correctly")
        query = query.filter(models.ClassSchedule.faculty_id == current_user.faculty_id)

    return query.order_by(models.ClassSchedule.weekday.asc(), models.ClassSchedule.start_time.asc()).all()


@router.get("/faculty/dashboard", response_model=schemas.FacultyAttendanceDashboardOut)
def get_faculty_dashboard(
    schedule_id: int,
    class_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    class_date = class_date or date.today()

    schedule = db.get(models.ClassSchedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if current_user.role == models.UserRole.FACULTY and current_user.faculty_id != schedule.faculty_id:
        raise HTTPException(status_code=403, detail="Faculty can only access their own class dashboard")

    enrolled_student_ids = [
        row[0]
        for row in (
            db.query(models.Enrollment.student_id)
            .filter(models.Enrollment.course_id == schedule.course_id)
            .all()
        )
    ]
    total_students = len(enrolled_student_ids)

    submissions = (
        db.query(models.AttendanceSubmission)
        .filter(
            models.AttendanceSubmission.schedule_id == schedule_id,
            models.AttendanceSubmission.class_date == class_date,
        )
        .order_by(models.AttendanceSubmission.submitted_at.asc())
        .all()
    )

    present_student_ids = {
        item.student_id
        for item in submissions
        if item.status in (models.AttendanceSubmissionStatus.VERIFIED, models.AttendanceSubmissionStatus.APPROVED)
    }
    pending_student_ids = {
        item.student_id
        for item in submissions
        if item.status == models.AttendanceSubmissionStatus.PENDING_REVIEW
    }
    if enrolled_student_ids:
        record_present_rows = (
            db.query(models.AttendanceRecord.student_id)
            .filter(
                models.AttendanceRecord.course_id == schedule.course_id,
                models.AttendanceRecord.attendance_date == class_date,
                models.AttendanceRecord.status == models.AttendanceStatus.PRESENT,
                models.AttendanceRecord.student_id.in_(enrolled_student_ids),
            )
            .all()
        )
        present_student_ids.update({row[0] for row in record_present_rows})
    pending_student_ids.difference_update(present_student_ids)

    present = len(present_student_ids)
    pending = len(pending_student_ids)
    absent = max(total_students - present - pending, 0)

    response_items: list[schemas.AttendanceSubmissionOut] = []
    for item in submissions:
        student = db.get(models.Student, item.student_id)
        response_items.append(
            schemas.AttendanceSubmissionOut(
                id=item.id,
                student_id=item.student_id,
                student_name=student.name if student else f"Student #{item.student_id}",
                status=item.status,
                ai_confidence=item.ai_confidence,
                ai_reason=item.ai_reason,
                submitted_at=item.submitted_at,
            )
        )

    return schemas.FacultyAttendanceDashboardOut(
        schedule_id=schedule_id,
        class_date=class_date,
        total_students=total_students,
        present=present,
        pending_review=pending,
        absent=absent,
        submissions=response_items,
    )


@router.get("/faculty/recovery-plans", response_model=schemas.AttendanceRecoveryPlanListOut)
def get_faculty_recovery_plan_list(
    schedule_id: int | None = Query(default=None),
    include_resolved: bool = Query(default=False),
    limit: int = Query(default=40, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    course_id: int | None = None
    if schedule_id is not None:
        schedule = db.get(models.ClassSchedule, int(schedule_id))
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        if current_user.role == models.UserRole.FACULTY and current_user.faculty_id != schedule.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty can only access their own class recovery queue")
        course_id = int(schedule.course_id)

    if current_user.role == models.UserRole.FACULTY:
        if not current_user.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty account is not linked correctly")
        plans = get_faculty_recovery_plans(
            db,
            faculty_id=int(current_user.faculty_id),
            course_id=course_id,
            include_resolved=bool(include_resolved),
            limit=int(limit),
        )
    else:
        plans = get_admin_recovery_plans(
            db,
            include_resolved=bool(include_resolved),
            limit=int(limit),
        )
        if course_id is not None:
            plans = [plan for plan in plans if int(plan.course_id) == int(course_id)]

    return schemas.AttendanceRecoveryPlanListOut(
        plans=_serialize_recovery_plan_rows(db, plans),
        last_updated_at=datetime.utcnow(),
    )


@router.get(
    "/faculty/rectification-requests",
    response_model=schemas.FacultyAttendanceRectificationListOut,
)
def list_faculty_rectification_requests(
    schedule_id: int,
    class_date: date | None = Query(default=None),
    include_resolved: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    class_date = class_date or date.today()

    schedule = db.get(models.ClassSchedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if current_user.role == models.UserRole.FACULTY and current_user.faculty_id != schedule.faculty_id:
        raise HTTPException(status_code=403, detail="Faculty can only access their own rectification queue")

    query = (
        db.query(models.AttendanceRectificationRequest)
        .filter(
            models.AttendanceRectificationRequest.schedule_id == schedule_id,
            models.AttendanceRectificationRequest.class_date == class_date,
        )
    )
    if not include_resolved:
        query = query.filter(
            models.AttendanceRectificationRequest.status == models.AttendanceRectificationStatus.PENDING
        )
    requests = query.order_by(
        models.AttendanceRectificationRequest.requested_at.desc(),
        models.AttendanceRectificationRequest.id.desc(),
    ).all()

    student_ids = sorted({item.student_id for item in requests})
    students = (
        {row.id: row for row in db.query(models.Student).filter(models.Student.id.in_(student_ids)).all()}
        if student_ids
        else {}
    )
    course = db.get(models.Course, schedule.course_id)

    payload = [
        _faculty_rectification_out(
            item,
            student=students.get(item.student_id),
            course=course,
        )
        for item in requests
    ]
    return schemas.FacultyAttendanceRectificationListOut(
        schedule_id=schedule_id,
        class_date=class_date,
        requests=payload,
    )


@router.post(
    "/faculty/rectification-review",
    response_model=schemas.FacultyRectificationReviewResponse,
)
def faculty_rectification_review(
    payload: schemas.FacultyRectificationReviewRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    request = db.get(models.AttendanceRectificationRequest, payload.request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Rectification request not found")

    schedule = db.get(models.ClassSchedule, request.schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found for rectification request")

    if current_user.role == models.UserRole.FACULTY and current_user.faculty_id != schedule.faculty_id:
        raise HTTPException(status_code=403, detail="Faculty can only review requests for their own subject")

    if request.status != models.AttendanceRectificationStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only pending rectification requests can be reviewed")

    reviewer_faculty_id = schedule.faculty_id if current_user.role == models.UserRole.ADMIN else current_user.faculty_id
    review_note = (payload.note or "").strip() or None
    approved = 0
    rejected = 0
    submission: models.AttendanceSubmission | None = None

    request.reviewed_by_faculty_id = reviewer_faculty_id
    request.reviewed_at = datetime.utcnow()
    request.review_note = review_note

    if payload.action == schemas.FacultyRectificationReviewAction.APPROVE:
        request.status = models.AttendanceRectificationStatus.APPROVED
        _upsert_present_attendance(
            db,
            student_id=request.student_id,
            course_id=request.course_id,
            faculty_id=reviewer_faculty_id or request.faculty_id,
            class_date=request.class_date,
            source="faculty-rectification-approved",
        )
        submission = _upsert_approved_submission_for_rectification(
            db=db,
            schedule=schedule,
            student_id=request.student_id,
            class_date=request.class_date,
            faculty_id=reviewer_faculty_id or request.faculty_id,
            review_note=review_note,
        )
        approved = 1
    else:
        request.status = models.AttendanceRectificationStatus.REJECTED
        rejected = 1

    db.commit()
    db.refresh(request)

    _sync_rectification_request_to_mongo(request, source="faculty-rectification-review")
    if submission is not None:
        _upsert_mongo_by_id(
            "attendance_submissions",
            submission.id,
            {
                "schedule_id": submission.schedule_id,
                "course_id": submission.course_id,
                "faculty_id": submission.faculty_id,
                "student_id": submission.student_id,
                "class_date": submission.class_date.isoformat(),
                "status": submission.status.value,
                "ai_match": submission.ai_match,
                "ai_confidence": submission.ai_confidence,
                "ai_model": submission.ai_model,
                "ai_reason": submission.ai_reason,
                "selfie_photo_object_key": submission.selfie_photo_object_key,
                "selfie_photo_fingerprint": _photo_fingerprint(
                    submission.selfie_photo_object_key or submission.selfie_photo_data_url
                ),
                "submitted_at": submission.submitted_at,
                "reviewed_at": submission.reviewed_at,
                "reviewed_by_faculty_id": submission.reviewed_by_faculty_id,
                "review_note": submission.review_note,
                "source": "faculty-rectification-review",
            },
        )
    mirror_document(
        "attendance_rectification_reviews",
        {
            "request_id": request.id,
            "schedule_id": request.schedule_id,
            "course_id": request.course_id,
            "student_id": request.student_id,
            "class_date": request.class_date.isoformat(),
            "action": payload.action.value,
            "review_note": review_note,
            "reviewed_by_faculty_id": reviewer_faculty_id,
            "reviewed_at": datetime.utcnow(),
            "source": "faculty-rectification-review",
        },
    )
    publish_domain_event(
        "attendance.rectification.updated",
        payload={
            "request_id": int(request.id),
            "student_id": int(request.student_id),
            "faculty_id": int(reviewer_faculty_id or request.faculty_id or 0),
            "schedule_id": int(request.schedule_id),
            "class_date": request.class_date.isoformat(),
            "action": payload.action.value,
        },
        scopes={
            f"student:{int(request.student_id)}",
            f"faculty:{int(reviewer_faculty_id or request.faculty_id or 0)}",
            "role:admin",
        },
        topics={"attendance", "messages"},
        actor={
            "user_id": int(current_user.id),
            "role": current_user.role.value,
        },
        source="attendance",
    )
    enqueue_recompute(
        {
            "entity": "student_attendance_aggregate",
            "student_id": int(request.student_id),
            "source": "attendance.rectification.updated",
        }
    )

    return schemas.FacultyRectificationReviewResponse(
        updated=1,
        approved=approved,
        rejected=rejected,
    )


@router.post("/faculty/review", response_model=schemas.FacultyBatchReviewResponse)
def faculty_batch_review(
    payload: schemas.FacultyBatchReviewRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    schedule = db.get(models.ClassSchedule, payload.schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if current_user.role == models.UserRole.FACULTY and current_user.faculty_id != schedule.faculty_id:
        raise HTTPException(status_code=403, detail="Faculty can only review their own class submissions")

    submissions = (
        db.query(models.AttendanceSubmission)
        .filter(
            models.AttendanceSubmission.id.in_(payload.submission_ids),
            models.AttendanceSubmission.schedule_id == payload.schedule_id,
            models.AttendanceSubmission.class_date == payload.class_date,
        )
        .all()
    )

    if not submissions:
        raise HTTPException(status_code=404, detail="No matching submissions found")

    approved = 0
    rejected = 0
    reviewer_faculty_id = schedule.faculty_id if current_user.role == models.UserRole.ADMIN else current_user.faculty_id

    pending_submissions = [
        item for item in submissions if item.status == models.AttendanceSubmissionStatus.PENDING_REVIEW
    ]
    if not pending_submissions:
        raise HTTPException(status_code=400, detail="Only pending submissions can be reviewed")

    for item in pending_submissions:
        item.reviewed_by_faculty_id = reviewer_faculty_id
        item.reviewed_at = datetime.utcnow()
        item.review_note = payload.note

        if payload.action == schemas.FacultyReviewAction.APPROVE:
            item.status = models.AttendanceSubmissionStatus.APPROVED
            _upsert_present_attendance(
                db,
                student_id=item.student_id,
                course_id=item.course_id,
                faculty_id=reviewer_faculty_id or item.faculty_id,
                class_date=item.class_date,
                source="faculty-approved-face",
            )
            approved += 1
        else:
            item.status = models.AttendanceSubmissionStatus.REJECTED
            rejected += 1

    db.commit()

    mirror_document(
        "attendance_reviews",
        {
            "schedule_id": payload.schedule_id,
            "class_date": payload.class_date.isoformat(),
            "action": payload.action.value,
            "review_note": payload.note,
            "updated_submission_ids": [item.id for item in pending_submissions],
            "approved": approved,
            "rejected": rejected,
            "reviewed_by_faculty_id": reviewer_faculty_id,
            "source": "faculty-review",
            "reviewed_at": datetime.utcnow(),
        },
    )
    publish_domain_event(
        "attendance.reviewed",
        payload={
            "schedule_id": int(payload.schedule_id),
            "class_date": payload.class_date.isoformat(),
            "action": payload.action.value,
            "updated_submission_ids": [int(item.id) for item in pending_submissions],
            "approved": int(approved),
            "rejected": int(rejected),
            "faculty_id": int(reviewer_faculty_id or 0),
        },
        scopes={
            f"faculty:{int(reviewer_faculty_id or 0)}",
            "role:admin",
            "role:student",
        },
        topics={"attendance"},
        actor={
            "user_id": int(current_user.id),
            "role": current_user.role.value,
        },
        source="attendance",
    )
    for submission in pending_submissions:
        enqueue_recompute(
            {
                "entity": "student_attendance_aggregate",
                "student_id": int(submission.student_id),
                "source": "attendance.reviewed",
            }
        )

    return schemas.FacultyBatchReviewResponse(
        updated=len(pending_submissions),
        approved=approved,
        rejected=rejected,
    )


@router.post("/faculty/classroom-analysis", response_model=schemas.ClassroomAnalysisOut, status_code=status.HTTP_201_CREATED)
def create_classroom_analysis(
    payload: schemas.ClassroomAnalysisCreate,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    schedule = db.get(models.ClassSchedule, payload.schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if current_user.role == models.UserRole.FACULTY and current_user.faculty_id != schedule.faculty_id:
        raise HTTPException(status_code=403, detail="Faculty can only analyze their own classes")

    analysis_photo_object_key: str | None = None
    if payload.photo_data_url:
        media = store_data_url_object(
            db,
            owner_table="classroom_analyses",
            owner_id=int(schedule.id),
            media_kind="classroom-analysis-photo",
            data_url=payload.photo_data_url,
            retention_days=ATTENDANCE_MEDIA_RETENTION_DAYS,
        )
        analysis_photo_object_key = media.object_key

    analysis = models.ClassroomAnalysis(
        schedule_id=payload.schedule_id,
        course_id=schedule.course_id,
        faculty_id=schedule.faculty_id,
        class_date=payload.class_date,
        photo_data_url=None,
        photo_object_key=analysis_photo_object_key,
        estimated_headcount=payload.estimated_headcount,
        engagement_level=payload.engagement_level,
        ai_summary=payload.ai_summary,
        ai_model=payload.ai_model,
    )

    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    _upsert_mongo_by_id(
        "classroom_analyses",
        analysis.id,
        {
            "schedule_id": analysis.schedule_id,
            "course_id": analysis.course_id,
            "faculty_id": analysis.faculty_id,
            "class_date": analysis.class_date.isoformat(),
            "estimated_headcount": analysis.estimated_headcount,
            "engagement_level": analysis.engagement_level,
            "ai_summary": analysis.ai_summary,
            "ai_model": analysis.ai_model,
            "photo_object_key": analysis.photo_object_key,
            "photo_fingerprint": _photo_fingerprint(analysis.photo_object_key or analysis.photo_data_url),
            "created_at": analysis.created_at,
            "source": "faculty-classroom-analysis",
        },
    )

    return analysis


@router.get("/faculty/classroom-analysis", response_model=list[schemas.ClassroomAnalysisOut])
def list_classroom_analysis(
    schedule_id: int | None = None,
    class_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    query = db.query(models.ClassroomAnalysis)

    if schedule_id:
        query = query.filter(models.ClassroomAnalysis.schedule_id == schedule_id)

    if class_date:
        query = query.filter(models.ClassroomAnalysis.class_date == class_date)

    if current_user.role == models.UserRole.FACULTY:
        query = query.filter(models.ClassroomAnalysis.faculty_id == current_user.faculty_id)

    return query.order_by(models.ClassroomAnalysis.created_at.desc()).limit(100).all()


@router.post("/mark-bulk", response_model=schemas.AttendanceBulkMarkResponse)
def mark_attendance_bulk(
    payload: schemas.AttendanceBulkMarkRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    course = db.get(models.Course, payload.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if current_user.role == models.UserRole.FACULTY:
        if not current_user.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty account is not linked correctly")
        if payload.faculty_id != current_user.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty can only mark attendance for their own ID")

    if course.faculty_id != payload.faculty_id:
        raise HTTPException(status_code=400, detail="Faculty is not assigned to this course")

    enrollments = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.course_id == payload.course_id)
        .all()
    )
    if not enrollments:
        raise HTTPException(status_code=400, detail="No enrolled students found for this course")

    override_map = {item.student_id: item.status for item in payload.overrides}
    absent_student_ids: list[int] = []

    for enrollment in enrollments:
        student_id = enrollment.student_id
        status_value = override_map.get(student_id, payload.default_status)
        _record_attendance_status(
            db,
            student_id=student_id,
            course_id=payload.course_id,
            faculty_id=payload.faculty_id,
            class_date=payload.attendance_date,
            status=status_value,
            source=payload.source,
        )

        if status_value == models.AttendanceStatus.ABSENT:
            absent_student_ids.append(student_id)

    db.flush()

    notifications_sent = 0
    for student_id in absent_student_ids:
        student = db.get(models.Student, student_id)
        if not student:
            continue

        message = (
            f"Absence alert: {student.name} is marked absent on "
            f"{payload.attendance_date.isoformat()} for {course.code}."
        )

        db.add(
            models.NotificationLog(
                student_id=student_id,
                message=message,
                channel="simulated-student",
                sent_to=student.email,
            )
        )
        notifications_sent += 1

        if student.parent_email:
            db.add(
                models.NotificationLog(
                    student_id=student_id,
                    message=message,
                    channel="simulated-parent",
                    sent_to=student.parent_email,
                )
            )
            notifications_sent += 1

    db.commit()

    mirror_document(
        "attendance_bulk_marks",
        {
            "course_id": payload.course_id,
            "faculty_id": payload.faculty_id,
            "attendance_date": payload.attendance_date.isoformat(),
            "default_status": payload.default_status.value,
            "source": payload.source,
            "total_marked": len(enrollments),
            "absent_student_ids": absent_student_ids,
            "notifications_sent": notifications_sent,
            "marked_at": datetime.utcnow(),
        },
    )

    return schemas.AttendanceBulkMarkResponse(
        total_marked=len(enrollments),
        absent_student_ids=absent_student_ids,
        notifications_sent=notifications_sent,
    )


@router.post(
    "/admin/recompute-aggregate",
    response_model=schemas.AttendanceAggregateRecomputeResponse,
)
def recompute_attendance_aggregate(
    payload: schemas.AttendanceAggregateRecomputeRequest,
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.OWNER)),
):
    if payload.from_date and payload.to_date and payload.from_date > payload.to_date:
        raise HTTPException(status_code=400, detail="from_date cannot be after to_date")
    result = recompute_attendance_scope(
        db,
        student_id=payload.student_id,
        course_id=payload.course_id,
        from_date=payload.from_date,
        to_date=payload.to_date,
        limit=payload.limit,
    )
    db.commit()
    return schemas.AttendanceAggregateRecomputeResponse(**result)


@router.get("/absentees", response_model=list[schemas.StudentOut])
def get_absentees(
    course_id: int,
    attendance_date: date = Query(...),
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    records = (
        db.query(models.AttendanceRecord)
        .filter(
            models.AttendanceRecord.course_id == course_id,
            models.AttendanceRecord.attendance_date == attendance_date,
            models.AttendanceRecord.status == models.AttendanceStatus.ABSENT,
        )
        .all()
    )
    if not records:
        return []

    student_ids = [r.student_id for r in records]
    return db.query(models.Student).filter(models.Student.id.in_(student_ids)).all()


@router.get("/summary", response_model=list[schemas.AttendanceSummaryItem])
def attendance_summary(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(get_current_user),
):
    course = db.get(models.Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    enrollments_query = db.query(models.Enrollment).filter(models.Enrollment.course_id == course_id)

    if current_user.role == models.UserRole.STUDENT:
        if not current_user.student_id:
            raise HTTPException(status_code=403, detail="Student account is not linked correctly")
        enrollments_query = enrollments_query.filter(models.Enrollment.student_id == current_user.student_id)

    enrollments = enrollments_query.all()

    summary: list[schemas.AttendanceSummaryItem] = []
    for enrollment in enrollments:
        student = db.get(models.Student, enrollment.student_id)
        if not student:
            continue

        present_count = (
            db.query(models.AttendanceRecord)
            .filter(
                models.AttendanceRecord.course_id == course_id,
                models.AttendanceRecord.student_id == enrollment.student_id,
                models.AttendanceRecord.status == models.AttendanceStatus.PRESENT,
            )
            .count()
        )
        absent_count = (
            db.query(models.AttendanceRecord)
            .filter(
                models.AttendanceRecord.course_id == course_id,
                models.AttendanceRecord.student_id == enrollment.student_id,
                models.AttendanceRecord.status == models.AttendanceStatus.ABSENT,
            )
            .count()
        )

        summary.append(
            schemas.AttendanceSummaryItem(
                student_id=student.id,
                student_name=student.name,
                present_count=present_count,
                absent_count=absent_count,
            )
        )

    return summary


@router.get("/notifications", response_model=list[schemas.NotificationOut])
def list_notifications(
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    return (
        db.query(models.NotificationLog)
        .order_by(models.NotificationLog.created_at.desc())
        .limit(200)
        .all()
    )


@router.get("/admin/recovery-plans", response_model=schemas.AttendanceRecoveryPlanListOut)
def get_admin_recovery_plan_list(
    include_resolved: bool = Query(default=False),
    limit: int = Query(default=80, ge=1, le=300),
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    plans = get_admin_recovery_plans(
        db,
        include_resolved=bool(include_resolved),
        limit=int(limit),
    )
    return schemas.AttendanceRecoveryPlanListOut(
        plans=_serialize_recovery_plan_rows(db, plans),
        last_updated_at=datetime.utcnow(),
    )


@router.post("/recovery/recompute", response_model=schemas.AttendanceRecoveryRecomputeOut)
def recompute_recovery_plans(
    payload: schemas.AttendanceRecoveryRecomputeRequest,
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    result = recompute_attendance_recovery_scope(
        db,
        student_id=payload.student_id,
        course_id=payload.course_id,
        limit=payload.limit,
    )
    db.commit()
    publish_domain_event(
        "attendance.recovery.recomputed",
        payload={
            "student_id": payload.student_id,
            "course_id": payload.course_id,
            "evaluated": int(result.get("evaluated", 0)),
            "plans_touched": int(result.get("plans_touched", 0)),
        },
        scopes={"role:admin"},
        topics={"attendance", "admin"},
        source="attendance",
    )
    return schemas.AttendanceRecoveryRecomputeOut(
        evaluated=int(result.get("evaluated", 0)),
        plans_touched=int(result.get("plans_touched", 0)),
    )
