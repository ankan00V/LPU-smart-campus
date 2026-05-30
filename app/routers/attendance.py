import base64
import datetime as datetime_lib
import hashlib
import hmac
import json
import logging
import math
import os
import re
import secrets
from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from typing import TypeVar
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pymongo.errors import DuplicateKeyError
from sqlalchemy import case, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from .. import models, schemas
from ..academic_policy import (
    ACADEMIC_END_DATE_DEFAULT,
    ACADEMIC_START_DATE_DEFAULT,
    ACADEMIC_TERM_CONFIG_KEY,
    academic_window,
    sync_faculty_sections_for_student,
    sync_student_academic_term,
)
from ..attendance_recovery import (
    evaluate_attendance_recovery,
    get_admin_recovery_plans,
    get_faculty_recovery_plans,
    get_student_recovery_plans,
    recompute_attendance_recovery_scope,
    retro_send_recovery_notifications,
    update_student_recovery_action,
)
from ..attendance_ledger import append_event_and_recompute, recompute_attendance_scope
from ..auth_utils import get_current_user, require_roles
from ..database import get_db
from ..default_timetable import DEFAULT_TIMETABLE_BLUEPRINT
from ..enterprise_controls import apply_pii_encryption_policy, resolve_secret
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
from ..saarthi_service import (
    is_saarthi_course,
    materialize_saarthi_attendance,
    should_materialize_saarthi_attendance,
)
from ..workers import enqueue_face_reverification, enqueue_recompute
from .auth import reissue_generated_profile_identifiers

router = APIRouter(prefix="/attendance", tags=["Attendance Management"])
logger = logging.getLogger(__name__)
_RowT = TypeVar("_RowT")

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
SYSTEM_ASSIGNED_STUDENT_ID_MESSAGE = (
    "Registration number is system-assigned from arrival order and cannot be entered manually."
)
SYSTEM_ASSIGNED_FACULTY_ID_MESSAGE = (
    "Faculty ID is system-assigned from arrival order and cannot be entered manually."
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
ATTENDANCE_TIMEZONE_DEFAULT = "Asia/Kolkata"
ATTENDANCE_LOCATION_DEFAULT_RADIUS_M = max(
    10.0,
    min(500.0, float(os.getenv("ATTENDANCE_LOCATION_DEFAULT_RADIUS_M", "75"))),
)
ATTENDANCE_LOCATION_MAX_DEVICE_ACCURACY_M = max(
    25.0,
    min(500.0, float(os.getenv("ATTENDANCE_LOCATION_MAX_DEVICE_ACCURACY_M", "150"))),
)
ATTENDANCE_LOCATION_ACCURACY_BUFFER_CAP_M = max(
    0.0,
    min(100.0, float(os.getenv("ATTENDANCE_LOCATION_ACCURACY_BUFFER_CAP_M", "35"))),
)
ATTENDANCE_SESSION_CODE_LENGTH = max(
    6,
    min(12, int(os.getenv("ATTENDANCE_SESSION_CODE_LENGTH", "8"))),
)
ATTENDANCE_SESSION_CODE_ROTATION_SECONDS = max(
    15,
    min(30, int(os.getenv("ATTENDANCE_SESSION_CODE_ROTATION_SECONDS", "20"))),
)
ATTENDANCE_SESSION_CODE_GRACE_SECONDS = max(
    0,
    min(10, int(os.getenv("ATTENDANCE_SESSION_CODE_GRACE_SECONDS", "5"))),
)
ATTENDANCE_ATTEMPT_TOKEN_TTL_SECONDS = max(
    30,
    min(180, int(os.getenv("ATTENDANCE_ATTEMPT_TOKEN_TTL_SECONDS", "90"))),
)
ATTENDANCE_ATTEMPT_MAX_SUBMISSIONS = max(
    1,
    min(10, int(os.getenv("ATTENDANCE_ATTEMPT_MAX_SUBMISSIONS", "10"))),
)
ATTENDANCE_ATTEMPT_MAX_TOKENS_PER_CLASS = max(
    1,
    min(5, int(os.getenv("ATTENDANCE_ATTEMPT_MAX_TOKENS_PER_CLASS", "3"))),
)
ATTENDANCE_LOCATION_MAX_TIMESTAMP_AGE_SECONDS = max(
    30,
    min(180, int(os.getenv("ATTENDANCE_LOCATION_MAX_TIMESTAMP_AGE_SECONDS", "90"))),
)


def _campus_timezone_name() -> str:
    zone_name = (os.getenv("APP_TIMEZONE", ATTENDANCE_TIMEZONE_DEFAULT) or "").strip() or ATTENDANCE_TIMEZONE_DEFAULT
    try:
        ZoneInfo(zone_name)
    except ZoneInfoNotFoundError:
        return ATTENDANCE_TIMEZONE_DEFAULT
    return zone_name


def _campus_zone() -> ZoneInfo:
    return ZoneInfo(_campus_timezone_name())


def _campus_now() -> datetime:
    return datetime.now(_campus_zone()).replace(tzinfo=None)


def _campus_today() -> date:
    return _campus_now().date()


def _campus_datetime_to_epoch_ms(value: datetime) -> float:
    if value.tzinfo is not None:
        return value.timestamp() * 1000.0
    return value.replace(tzinfo=_campus_zone()).timestamp() * 1000.0
ACADEMIC_START_DATE_ENV_FALLBACK = "2026-03-02"
STUDENT_SECTION_PATTERN = re.compile(r"^[A-Z0-9-_/]+$")


class AttendanceLocationError(HTTPException):
    def __init__(
        self,
        *,
        status_code: int,
        detail: str,
        auditable: bool,
        distance_m: float | None = None,
        allowed_radius_m: float | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail)
        self.auditable = bool(auditable)
        self.distance_m = distance_m
        self.allowed_radius_m = allowed_radius_m


class AttendanceSessionError(HTTPException):
    def __init__(
        self,
        *,
        status_code: int,
        detail: str,
        auditable: bool,
        session: models.ClassAttendanceSession | None = None,
        submitted_code_hash: str | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail)
        self.auditable = bool(auditable)
        self.session = session
        self.submitted_code_hash = submitted_code_hash


class AttendanceAttemptTokenError(HTTPException):
    def __init__(
        self,
        *,
        status_code: int,
        detail: str,
        auditable: bool,
        session: models.ClassAttendanceSession | None = None,
        token_hash: str | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail)
        self.auditable = bool(auditable)
        self.session = session
        self.token_hash = token_hash


def _demo_features_enabled() -> bool:
    override = (os.getenv("ALLOW_DEMO_FEATURES", "") or "").strip().lower()
    if override in {"1", "true", "yes", "on"}:
        return True
    app_env = (os.getenv("APP_ENV", "") or "").strip().lower()
    strict_mode = (os.getenv("APP_RUNTIME_STRICT", "true") or "").strip().lower() in {"1", "true", "yes", "on"}
    return app_env != "production" and not strict_mode


def _academic_start_date() -> date:
    raw = (os.getenv("ACADEMIC_START_DATE", ACADEMIC_START_DATE_ENV_FALLBACK) or "").strip()
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return date.fromisoformat(ACADEMIC_START_DATE_ENV_FALLBACK)


def _academic_class_window(db: Session) -> tuple[date, date]:
    start_date, end_date = academic_window(db)
    if end_date < start_date:
        return (
            date.fromisoformat(ACADEMIC_START_DATE_DEFAULT),
            date.fromisoformat(ACADEMIC_END_DATE_DEFAULT),
        )
    return start_date, end_date


def _student_saarthi_materialization_through_date(
    db: Session,
    *,
    student_id: int,
    academic_start: date,
    today: date,
) -> date:
    bundle_course = (
        db.query(models.Course.id)
        .filter(models.Course.code == "CON111")
        .first()
    )
    if bundle_course is None:
        return today

    course_id = int(bundle_course[0])
    evidence_dates: list[date] = []

    session_rows = (
        db.query(models.SaarthiSession.mandatory_date)
        .filter(
            models.SaarthiSession.student_id == int(student_id),
            models.SaarthiSession.course_id == course_id,
            models.SaarthiSession.mandatory_date >= academic_start,
            models.SaarthiSession.mandatory_date <= today,
        )
        .all()
    )
    evidence_dates.extend(
        row[0]
        for row in session_rows
        if row and row[0] is not None
    )

    attendance_rows = (
        db.query(models.AttendanceRecord.attendance_date)
        .filter(
            models.AttendanceRecord.student_id == int(student_id),
            models.AttendanceRecord.course_id == course_id,
            models.AttendanceRecord.attendance_date >= academic_start,
            models.AttendanceRecord.attendance_date <= today,
        )
        .all()
    )
    evidence_dates.extend(
        row[0]
        for row in attendance_rows
        if row and row[0] is not None
    )

    if evidence_dates:
        return min(today, max(evidence_dates))
    return today


def _enrolled_student_ids_for_course(db: Session, *, course_id: int) -> list[int]:
    return [
        int(row[0])
        for row in (
            db.query(models.Enrollment.student_id)
            .filter(models.Enrollment.course_id == int(course_id))
            .all()
        )
        if row and row[0] is not None
    ]


def _saarthi_missed_student_ids(
    db: Session,
    *,
    course_id: int,
    attendance_date: date,
    enrolled_student_ids: list[int] | None = None,
) -> set[int]:
    if attendance_date.weekday() != 6:  # Sunday
        return set()
    if attendance_date >= _campus_today():
        return set()

    normalized_enrolled_ids = {
        int(student_id)
        for student_id in (
            enrolled_student_ids
            if enrolled_student_ids is not None
            else _enrolled_student_ids_for_course(db, course_id=int(course_id))
        )
        if int(student_id) > 0
    }
    if not normalized_enrolled_ids:
        return set()

    credited_ids = {
        int(row[0])
        for row in (
            db.query(models.SaarthiSession.student_id)
            .filter(
                models.SaarthiSession.course_id == int(course_id),
                models.SaarthiSession.mandatory_date == attendance_date,
                models.SaarthiSession.attendance_marked_at.isnot(None),
                models.SaarthiSession.student_id.in_(sorted(normalized_enrolled_ids)),
            )
            .all()
        )
        if row and row[0] is not None
    }
    return normalized_enrolled_ids - credited_ids


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


def _attendance_session_secret() -> str:
    secret = str(resolve_secret("ATTENDANCE_SESSION_SECRET", default="") or "").strip()
    if not secret:
        secret = str(resolve_secret("APP_AUTH_SECRET", default="") or "").strip()
    if secret:
        return secret
    if (os.getenv("APP_ENV", "") or "").strip().lower() == "production":
        raise RuntimeError("ATTENDANCE_SESSION_SECRET or APP_AUTH_SECRET is required in production.")
    return "attendance-session-dev-secret"


def _normalize_attendance_session_code(raw_value: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(raw_value or "").strip().upper())


def _format_attendance_session_code(raw_code: str) -> str:
    code = _normalize_attendance_session_code(raw_code)
    if len(code) <= 4:
        return code
    return "-".join(code[index : index + 4] for index in range(0, len(code), 4))


def _attendance_session_window_end(schedule: models.ClassSchedule, class_date: date) -> datetime:
    class_start, _ = _class_datetime_bounds(schedule, class_date)
    return class_start + timedelta(minutes=10)


def _attendance_rotation_seconds(session: models.ClassAttendanceSession | None = None) -> int:
    raw_value = getattr(session, "code_rotation_seconds", None)
    try:
        value = int(raw_value or ATTENDANCE_SESSION_CODE_ROTATION_SECONDS)
    except (TypeError, ValueError):
        value = ATTENDANCE_SESSION_CODE_ROTATION_SECONDS
    return max(15, min(30, value))


def _attendance_code_slot(now_dt: datetime, rotation_seconds: int) -> int:
    return int(now_dt.timestamp()) // max(1, int(rotation_seconds))


def _attendance_code_slot_start(code_slot: int, rotation_seconds: int) -> datetime:
    return datetime_lib.datetime.fromtimestamp(int(code_slot) * max(1, int(rotation_seconds)))


def _attendance_code_slot_end(code_slot: int, rotation_seconds: int) -> datetime:
    return _attendance_code_slot_start(int(code_slot) + 1, rotation_seconds)


def _attendance_code_expires_at(
    *,
    now_dt: datetime,
    session_expires_at: datetime,
    rotation_seconds: int,
) -> datetime:
    current_slot = _attendance_code_slot(now_dt, rotation_seconds)
    slot_end = _attendance_code_slot_end(current_slot, rotation_seconds)
    return min(slot_end, session_expires_at)


def _attendance_session_code_message(
    schedule: models.ClassSchedule,
    class_date: date,
    *,
    code_slot: int,
) -> str:
    return "|".join(
        [
            "attendance-session-v1",
            str(int(schedule.id)),
            str(int(schedule.course_id)),
            str(int(schedule.faculty_id)),
            class_date.isoformat(),
            str(schedule.start_time),
            str(schedule.end_time),
            str(int(code_slot)),
        ]
    )


def _generate_attendance_session_code(
    schedule: models.ClassSchedule,
    class_date: date,
    *,
    now_dt: datetime | None = None,
    code_slot: int | None = None,
    rotation_seconds: int | None = None,
) -> str:
    effective_rotation = max(15, min(30, int(rotation_seconds or ATTENDANCE_SESSION_CODE_ROTATION_SECONDS)))
    effective_slot = int(code_slot) if code_slot is not None else _attendance_code_slot(now_dt or _campus_now(), effective_rotation)
    digest = hmac.new(
        _attendance_session_secret().encode("utf-8"),
        _attendance_session_code_message(
            schedule,
            class_date,
            code_slot=effective_slot,
        ).encode("utf-8"),
        hashlib.sha256,
    ).digest()
    raw_code = base64.b32encode(digest).decode("ascii").replace("=", "")[:ATTENDANCE_SESSION_CODE_LENGTH]
    return _format_attendance_session_code(raw_code)


def _attendance_session_code_hash(
    code: str,
    *,
    schedule: models.ClassSchedule,
    class_date: date,
    now_dt: datetime | None = None,
    code_slot: int | None = None,
    rotation_seconds: int | None = None,
) -> str:
    effective_rotation = max(15, min(30, int(rotation_seconds or ATTENDANCE_SESSION_CODE_ROTATION_SECONDS)))
    effective_slot = int(code_slot) if code_slot is not None else _attendance_code_slot(now_dt or _campus_now(), effective_rotation)
    normalized = _normalize_attendance_session_code(code)
    message = (
        "attendance-session-code-v1|"
        f"{_attendance_session_code_message(schedule, class_date, code_slot=effective_slot)}|{normalized}"
    )
    return hmac.new(
        _attendance_session_secret().encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _candidate_attendance_code_slots(now_dt: datetime, rotation_seconds: int) -> list[int]:
    current_slot = _attendance_code_slot(now_dt, rotation_seconds)
    candidates = [current_slot]
    seconds_into_slot = int(now_dt.timestamp()) - (current_slot * int(rotation_seconds))
    if ATTENDANCE_SESSION_CODE_GRACE_SECONDS and seconds_into_slot <= ATTENDANCE_SESSION_CODE_GRACE_SECONDS:
        candidates.append(current_slot - 1)
    return candidates


def _attendance_tracking_hash(value: str | None, *, purpose: str) -> str | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    message = f"attendance-tracking-v1|{purpose}|{normalized}"
    return hmac.new(
        _attendance_session_secret().encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _attendance_attempt_token_hash(token: str | None) -> str | None:
    return _attendance_tracking_hash(token, purpose="attempt-token")


def _request_client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    forwarded = str(request.headers.get("x-forwarded-for") or "").strip()
    if forwarded:
        first = forwarded.split(",", 1)[0].strip()
        if first:
            return first
    real_ip = str(request.headers.get("x-real-ip") or "").strip()
    if real_ip:
        return real_ip
    if request.client and request.client.host:
        return str(request.client.host)
    return None


def _request_user_agent(request: Request | None) -> str | None:
    if request is None:
        return None
    return str(request.headers.get("user-agent") or "").strip() or None


def _normalize_integrity_flags(raw_flags: list[str] | None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in raw_flags or []:
        token = re.sub(r"[^a-z0-9_.:-]+", "_", str(item or "").strip().lower())[:80]
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out[:20]


def _integrity_flags_json(flags: list[str]) -> str | None:
    normalized = _normalize_integrity_flags(flags)
    return json.dumps(normalized) if normalized else None


def _location_integrity_flags(payload: schemas.RealtimeAttendanceMarkRequest, now_dt: datetime) -> list[str]:
    flags = _normalize_integrity_flags(payload.client_integrity_flags)
    if payload.location_latitude == 0 and payload.location_longitude == 0:
        flags.append("gps_zero_coordinates")
    if payload.location_accuracy_m is None:
        flags.append("gps_accuracy_missing")
    elif float(payload.location_accuracy_m) <= 0:
        flags.append("gps_accuracy_zero")
    if payload.location_timestamp_ms is None:
        flags.append("gps_timestamp_missing")
    else:
        try:
            captured_at = datetime_lib.datetime.fromtimestamp(
                float(payload.location_timestamp_ms) / 1000.0,
                _campus_zone(),
            ).replace(tzinfo=None)
            age_seconds = abs((now_dt - captured_at).total_seconds())
            if age_seconds > ATTENDANCE_LOCATION_MAX_TIMESTAMP_AGE_SECONDS:
                flags.append("gps_timestamp_stale")
        except (OverflowError, OSError, ValueError):
            flags.append("gps_timestamp_invalid")
    return _normalize_integrity_flags(flags)


def _active_attendance_session(
    db: Session,
    *,
    schedule: models.ClassSchedule,
    class_date: date,
    now_dt: datetime,
) -> models.ClassAttendanceSession | None:
    session = (
        db.query(models.ClassAttendanceSession)
        .filter(
            models.ClassAttendanceSession.schedule_id == schedule.id,
            models.ClassAttendanceSession.class_date == class_date,
            models.ClassAttendanceSession.is_active.is_(True),
        )
        .first()
    )
    if not session or session.expires_at < now_dt:
        return None
    return session


def _open_attendance_session(
    db: Session,
    *,
    schedule: models.ClassSchedule,
    class_date: date,
    now_dt: datetime,
    opened_by_user_id: int,
) -> tuple[models.ClassAttendanceSession, str]:
    rotation_seconds = ATTENDANCE_SESSION_CODE_ROTATION_SECONDS
    code_slot = _attendance_code_slot(now_dt, rotation_seconds)
    session_expires_at = _attendance_session_window_end(schedule, class_date)
    code_expires_at = _attendance_code_expires_at(
        now_dt=now_dt,
        session_expires_at=session_expires_at,
        rotation_seconds=rotation_seconds,
    )
    session_code = _generate_attendance_session_code(
        schedule,
        class_date,
        code_slot=code_slot,
        rotation_seconds=rotation_seconds,
    )
    session_hash = _attendance_session_code_hash(
        session_code,
        schedule=schedule,
        class_date=class_date,
        code_slot=code_slot,
        rotation_seconds=rotation_seconds,
    )
    session = (
        db.query(models.ClassAttendanceSession)
        .filter(
            models.ClassAttendanceSession.schedule_id == schedule.id,
            models.ClassAttendanceSession.class_date == class_date,
        )
        .first()
    )
    if session is None:
        savepoint = db.begin_nested()
        session = models.ClassAttendanceSession(
            schedule_id=int(schedule.id),
            course_id=int(schedule.course_id),
            faculty_id=int(schedule.faculty_id),
            class_date=class_date,
            session_code_hash=session_hash,
            code_rotation_seconds=rotation_seconds,
            current_code_expires_at=code_expires_at,
            generated_at=now_dt,
            expires_at=session_expires_at,
            opened_by_user_id=int(opened_by_user_id),
            is_active=True,
            created_at=now_dt,
            updated_at=now_dt,
        )
        db.add(session)
        try:
            db.flush()
        except IntegrityError:
            savepoint.rollback()
            session = (
                db.query(models.ClassAttendanceSession)
                .filter(
                    models.ClassAttendanceSession.schedule_id == schedule.id,
                    models.ClassAttendanceSession.class_date == class_date,
                )
                .first()
            )
            if session is None:
                raise
        else:
            savepoint.commit()
            return session, session_code

    session.course_id = int(schedule.course_id)
    session.faculty_id = int(schedule.faculty_id)
    session.session_code_hash = session_hash
    session.code_rotation_seconds = rotation_seconds
    session.current_code_expires_at = code_expires_at
    session.generated_at = now_dt
    session.expires_at = session_expires_at
    session.opened_by_user_id = int(opened_by_user_id)
    session.is_active = True
    session.updated_at = now_dt
    db.flush()
    return session, session_code


def _verify_attendance_session_code(
    *,
    db: Session,
    schedule: models.ClassSchedule,
    class_date: date,
    now_dt: datetime,
    attendance_session_code: str | None,
) -> tuple[models.ClassAttendanceSession, str, datetime]:
    session = _active_attendance_session(
        db,
        schedule=schedule,
        class_date=class_date,
        now_dt=now_dt,
    )
    if session is None:
        raise AttendanceSessionError(
            status_code=400,
            detail=(
                "Faculty attendance code is not open for this class. "
                "Ask the faculty to open the attendance session during the first 10 minutes."
            ),
            auditable=False,
        )

    normalized_code = _normalize_attendance_session_code(attendance_session_code)
    if not normalized_code:
        raise AttendanceSessionError(
            status_code=400,
            detail="Attendance session code is required before facial attendance can start.",
            auditable=True,
            session=session,
        )

    rotation_seconds = _attendance_rotation_seconds(session)
    matched_hash: str | None = None
    matched_code_expires_at = _attendance_code_expires_at(
        now_dt=now_dt,
        session_expires_at=session.expires_at,
        rotation_seconds=rotation_seconds,
    )
    submitted_hash = _attendance_session_code_hash(
        normalized_code,
        schedule=schedule,
        class_date=class_date,
        now_dt=now_dt,
        rotation_seconds=rotation_seconds,
    )
    for candidate_slot in _candidate_attendance_code_slots(now_dt, rotation_seconds):
        expected_code = _generate_attendance_session_code(
            schedule,
            class_date,
            code_slot=candidate_slot,
            rotation_seconds=rotation_seconds,
        )
        candidate_hash = _attendance_session_code_hash(
            normalized_code,
            schedule=schedule,
            class_date=class_date,
            code_slot=candidate_slot,
            rotation_seconds=rotation_seconds,
        )
        if hmac.compare_digest(normalized_code, _normalize_attendance_session_code(expected_code)):
            matched_hash = candidate_hash
            if candidate_slot == _attendance_code_slot(now_dt, rotation_seconds):
                matched_code_expires_at = _attendance_code_expires_at(
                    now_dt=now_dt,
                    session_expires_at=session.expires_at,
                    rotation_seconds=rotation_seconds,
                )
            else:
                matched_code_expires_at = min(
                    now_dt + timedelta(seconds=ATTENDANCE_SESSION_CODE_GRACE_SECONDS),
                    session.expires_at,
                )
            break
    if matched_hash is None:
        raise AttendanceSessionError(
            status_code=403,
            detail="Attendance session code rejected for this class window.",
            auditable=True,
            session=session,
            submitted_code_hash=submitted_hash,
        )
    return session, matched_hash, matched_code_expires_at


def _issue_attendance_attempt_token(
    *,
    db: Session,
    session: models.ClassAttendanceSession,
    schedule: models.ClassSchedule,
    student: models.Student,
    class_date: date,
    now_dt: datetime,
    code_hash: str,
    request: Request | None,
    browser_fingerprint: str | None,
    client_integrity_flags: list[str] | None,
) -> tuple[models.AttendanceAttemptToken, str]:
    token_count = (
        db.query(models.AttendanceAttemptToken)
        .filter(
            models.AttendanceAttemptToken.schedule_id == schedule.id,
            models.AttendanceAttemptToken.student_id == student.id,
            models.AttendanceAttemptToken.class_date == class_date,
        )
        .count()
    )
    if token_count >= ATTENDANCE_ATTEMPT_MAX_TOKENS_PER_CLASS:
        raise HTTPException(
            status_code=429,
            detail="Too many attendance code validations for this class. Ask faculty to verify your attempt.",
        )

    raw_token = secrets.token_urlsafe(32)
    token_hash = _attendance_attempt_token_hash(raw_token)
    if not token_hash:
        raise HTTPException(status_code=500, detail="Unable to create attendance attempt token")
    expires_at = min(
        now_dt + timedelta(seconds=ATTENDANCE_ATTEMPT_TOKEN_TTL_SECONDS),
        session.expires_at,
    )
    attempt = models.AttendanceAttemptToken(
        attendance_session_id=int(session.id),
        schedule_id=int(schedule.id),
        student_id=int(student.id),
        class_date=class_date,
        token_hash=token_hash,
        session_code_hash=code_hash,
        browser_fingerprint_hash=_attendance_tracking_hash(browser_fingerprint, purpose="browser-fingerprint"),
        client_ip_hash=_attendance_tracking_hash(_request_client_ip(request), purpose="client-ip"),
        user_agent_hash=_attendance_tracking_hash(_request_user_agent(request), purpose="user-agent"),
        client_integrity_flags=_integrity_flags_json(_normalize_integrity_flags(client_integrity_flags)),
        issued_at=now_dt,
        expires_at=expires_at,
        attempt_count=0,
        max_attempts=ATTENDANCE_ATTEMPT_MAX_SUBMISSIONS,
        created_at=now_dt,
        updated_at=now_dt,
    )
    db.add(attempt)
    db.flush()
    return attempt, raw_token


def _verify_attendance_attempt_token(
    *,
    db: Session,
    schedule: models.ClassSchedule,
    student: models.Student,
    class_date: date,
    now_dt: datetime,
    request: Request | None,
    payload: schemas.RealtimeAttendanceMarkRequest,
) -> tuple[models.AttendanceAttemptToken, models.ClassAttendanceSession]:
    token_hash = _attendance_attempt_token_hash(payload.attendance_attempt_token)
    if not token_hash:
        raise AttendanceAttemptTokenError(
            status_code=400,
            detail="Validate the faculty attendance code before facial attendance can start.",
            auditable=True,
        )
    attempt = (
        db.query(models.AttendanceAttemptToken)
        .filter(
            models.AttendanceAttemptToken.token_hash == token_hash,
            models.AttendanceAttemptToken.schedule_id == schedule.id,
            models.AttendanceAttemptToken.student_id == student.id,
            models.AttendanceAttemptToken.class_date == class_date,
        )
        .first()
    )
    if attempt is None:
        raise AttendanceAttemptTokenError(
            status_code=403,
            detail="Attendance session token rejected. Re-enter the latest faculty code.",
            auditable=True,
            token_hash=token_hash,
        )
    session = db.get(models.ClassAttendanceSession, attempt.attendance_session_id)
    if not session or not session.is_active or session.expires_at < now_dt:
        raise AttendanceAttemptTokenError(
            status_code=400,
            detail="Attendance session token expired. Ask faculty to reopen the attendance code if the window is still open.",
            auditable=True,
            session=session,
            token_hash=token_hash,
        )
    if attempt.expires_at < now_dt:
        raise AttendanceAttemptTokenError(
            status_code=400,
            detail="Attendance session token expired. Re-enter the current faculty code.",
            auditable=True,
            session=session,
            token_hash=token_hash,
        )
    if attempt.consumed_at is not None:
        raise AttendanceAttemptTokenError(
            status_code=409,
            detail="Attendance is already submitted for this validated code.",
            auditable=False,
            session=session,
            token_hash=token_hash,
        )
    if int(attempt.attempt_count or 0) >= int(attempt.max_attempts or ATTENDANCE_ATTEMPT_MAX_SUBMISSIONS):
        raise AttendanceAttemptTokenError(
            status_code=429,
            detail="Too many facial verification attempts for this attendance token. Re-enter the latest faculty code.",
            auditable=True,
            session=session,
            token_hash=token_hash,
        )

    submitted_fingerprint_hash = _attendance_tracking_hash(payload.browser_fingerprint, purpose="browser-fingerprint")
    if attempt.browser_fingerprint_hash and submitted_fingerprint_hash != attempt.browser_fingerprint_hash:
        raise AttendanceAttemptTokenError(
            status_code=403,
            detail="Browser session changed after code validation. Re-enter the faculty code from this device.",
            auditable=True,
            session=session,
            token_hash=token_hash,
        )

    flags = _location_integrity_flags(payload, now_dt)
    current_ip_hash = _attendance_tracking_hash(_request_client_ip(request), purpose="client-ip")
    if attempt.client_ip_hash and current_ip_hash and current_ip_hash != attempt.client_ip_hash:
        flags.append("client_ip_changed_after_code_validation")
    if "browser_automation_detected" in set(flags):
        raise AttendanceAttemptTokenError(
            status_code=403,
            detail="Attendance cannot be marked from an automated browser session.",
            auditable=True,
            session=session,
            token_hash=token_hash,
        )
    if "gps_zero_coordinates" in set(flags):
        raise AttendanceAttemptTokenError(
            status_code=400,
            detail="Browser GPS returned invalid zero coordinates. Enable real device location and retry.",
            auditable=True,
            session=session,
            token_hash=token_hash,
        )

    attempt.attempt_count = int(attempt.attempt_count or 0) + 1
    attempt.last_seen_at = now_dt
    attempt.updated_at = now_dt
    attempt.client_integrity_flags = _integrity_flags_json(flags) or attempt.client_integrity_flags
    db.flush()
    return attempt, session


def _schedule_attendance_location_configured(schedule: models.ClassSchedule) -> bool:
    return schedule.attendance_latitude is not None and schedule.attendance_longitude is not None


def _schedule_attendance_radius_m(schedule: models.ClassSchedule) -> float:
    try:
        radius = float(schedule.attendance_radius_m or ATTENDANCE_LOCATION_DEFAULT_RADIUS_M)
    except (TypeError, ValueError):
        radius = ATTENDANCE_LOCATION_DEFAULT_RADIUS_M
    return max(10.0, min(500.0, radius))


def _haversine_distance_m(
    origin_latitude: float,
    origin_longitude: float,
    target_latitude: float,
    target_longitude: float,
) -> float:
    earth_radius_m = 6_371_000.0
    origin_lat_rad = math.radians(origin_latitude)
    target_lat_rad = math.radians(target_latitude)
    delta_lat = math.radians(target_latitude - origin_latitude)
    delta_lon = math.radians(target_longitude - origin_longitude)
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(origin_lat_rad) * math.cos(target_lat_rad) * math.sin(delta_lon / 2) ** 2
    )
    a = max(0.0, min(1.0, a))
    return earth_radius_m * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _verify_attendance_location(
    *,
    schedule: models.ClassSchedule,
    payload: schemas.RealtimeAttendanceMarkRequest,
) -> tuple[float, float]:
    if not _schedule_attendance_location_configured(schedule):
        raise AttendanceLocationError(
            status_code=400,
            detail=(
                "Attendance location is not configured for this class. "
                "Ask the faculty or admin to set the class GPS lock before marking attendance."
            ),
            auditable=False,
        )
    if payload.location_latitude is None or payload.location_longitude is None:
        raise AttendanceLocationError(
            status_code=400,
            detail="Browser location is required before facial attendance can start.",
            auditable=True,
        )

    accuracy_m: float | None = None
    if payload.location_accuracy_m is not None:
        accuracy_m = max(0.0, float(payload.location_accuracy_m))
        if accuracy_m > ATTENDANCE_LOCATION_MAX_DEVICE_ACCURACY_M:
            raise AttendanceLocationError(
                status_code=400,
                detail=(
                    f"Location accuracy is too low (±{round(accuracy_m)}m). "
                    "Move near the classroom, enable high-accuracy GPS, and retry."
                ),
                auditable=True,
            )

    distance_m = _haversine_distance_m(
        float(schedule.attendance_latitude),
        float(schedule.attendance_longitude),
        float(payload.location_latitude),
        float(payload.location_longitude),
    )
    base_radius_m = _schedule_attendance_radius_m(schedule)
    gps_buffer_m = min(float(accuracy_m or 0.0), ATTENDANCE_LOCATION_ACCURACY_BUFFER_CAP_M)
    allowed_radius_m = base_radius_m + gps_buffer_m
    if distance_m > allowed_radius_m:
        location_label = str(schedule.attendance_location_label or schedule.classroom_label or "the assigned classroom").strip()
        raise AttendanceLocationError(
            status_code=403,
            detail=(
                "Attendance location rejected: "
                f"you are {round(distance_m)}m away from {location_label}. "
                f"Allowed range is {round(allowed_radius_m)}m including GPS buffer."
            ),
            auditable=True,
            distance_m=distance_m,
            allowed_radius_m=allowed_radius_m,
        )
    return distance_m, allowed_radius_m


def _clean_location_label(raw_value: str | None) -> str | None:
    value = str(raw_value or "").strip()
    return value or None


def _apply_attendance_location_fields(
    schedule: models.ClassSchedule,
    payload: schemas.ClassScheduleCreate | schemas.TimetableOverrideUpsertRequest | schemas.ClassScheduleLocationUpdate,
) -> bool:
    latitude = getattr(payload, "attendance_latitude", None)
    longitude = getattr(payload, "attendance_longitude", None)
    if latitude is None or longitude is None:
        return False

    radius_m = getattr(payload, "attendance_radius_m", None)
    if radius_m is None:
        radius_m = ATTENDANCE_LOCATION_DEFAULT_RADIUS_M
    label = _clean_location_label(getattr(payload, "attendance_location_label", None))
    next_values = {
        "attendance_latitude": float(latitude),
        "attendance_longitude": float(longitude),
        "attendance_radius_m": max(10.0, min(500.0, float(radius_m))),
        "attendance_location_label": label,
    }
    changed = False
    for field_name, next_value in next_values.items():
        if getattr(schedule, field_name) != next_value:
            setattr(schedule, field_name, next_value)
            changed = True
    return changed


def _upsert_location_rejected_submission(
    *,
    db: Session,
    schedule: models.ClassSchedule,
    student_id: int,
    class_date: date,
    payload: schemas.RealtimeAttendanceMarkRequest,
    reason: str,
    distance_m: float | None,
    allowed_radius_m: float | None,
    existing_submission: models.AttendanceSubmission | None = None,
    attendance_session: models.ClassAttendanceSession | None = None,
    attendance_session_code_hash: str | None = None,
    attendance_attempt_token_hash: str | None = None,
    browser_fingerprint_hash: str | None = None,
    client_ip_hash: str | None = None,
    user_agent_hash: str | None = None,
    client_integrity_flags: str | None = None,
    ai_model: str = "gps-geofence-v1",
) -> models.AttendanceSubmission:
    submission = existing_submission
    if submission is None:
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
            selfie_photo_object_key=None,
            ai_match=False,
            ai_confidence=0.0,
            ai_model=ai_model,
            ai_reason=str(reason or "Attendance location rejected")[:600],
            location_latitude=payload.location_latitude,
            location_longitude=payload.location_longitude,
            location_accuracy_m=payload.location_accuracy_m,
            location_distance_m=distance_m,
            location_allowed_radius_m=allowed_radius_m,
            attendance_session_id=attendance_session.id if attendance_session else None,
            attendance_session_code_hash=attendance_session_code_hash
            or (attendance_session.session_code_hash if attendance_session else None),
            attendance_attempt_token_hash=attendance_attempt_token_hash,
            browser_fingerprint_hash=browser_fingerprint_hash,
            client_ip_hash=client_ip_hash,
            user_agent_hash=user_agent_hash,
            client_integrity_flags=client_integrity_flags,
            status=models.AttendanceSubmissionStatus.REJECTED,
            submitted_at=datetime.utcnow(),
        )
        db.add(submission)
    else:
        previous_selfie_key = str(submission.selfie_photo_object_key or "").strip() or None
        submission.selfie_photo_data_url = None
        submission.selfie_photo_object_key = None
        if previous_selfie_key:
            mark_media_deleted(db, previous_selfie_key)
        submission.ai_match = False
        submission.ai_confidence = 0.0
        submission.ai_model = ai_model
        submission.ai_reason = str(reason or "Attendance location rejected")[:600]
        submission.location_latitude = payload.location_latitude
        submission.location_longitude = payload.location_longitude
        submission.location_accuracy_m = payload.location_accuracy_m
        submission.location_distance_m = distance_m
        submission.location_allowed_radius_m = allowed_radius_m
        submission.attendance_session_id = attendance_session.id if attendance_session else None
        submission.attendance_session_code_hash = attendance_session_code_hash or (
            attendance_session.session_code_hash if attendance_session else None
        )
        submission.attendance_attempt_token_hash = attendance_attempt_token_hash
        submission.browser_fingerprint_hash = browser_fingerprint_hash
        submission.client_ip_hash = client_ip_hash
        submission.user_agent_hash = user_agent_hash
        submission.client_integrity_flags = client_integrity_flags
        submission.status = models.AttendanceSubmissionStatus.REJECTED
        submission.submitted_at = datetime.utcnow()
        submission.reviewed_at = None
        submission.reviewed_by_faculty_id = None
        submission.review_note = None

    db.flush()
    return submission


def _sync_location_rejected_submission_to_mongo(submission: models.AttendanceSubmission) -> None:
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
            "location_latitude": submission.location_latitude,
            "location_longitude": submission.location_longitude,
            "location_accuracy_m": submission.location_accuracy_m,
            "location_distance_m": submission.location_distance_m,
            "location_allowed_radius_m": submission.location_allowed_radius_m,
            "attendance_session_id": submission.attendance_session_id,
            "attendance_session_code_hash": submission.attendance_session_code_hash,
            "attendance_attempt_token_hash": submission.attendance_attempt_token_hash,
            "browser_fingerprint_hash": submission.browser_fingerprint_hash,
            "client_ip_hash": submission.client_ip_hash,
            "user_agent_hash": submission.user_agent_hash,
            "client_integrity_flags": submission.client_integrity_flags,
            "selfie_photo_object_key": None,
            "selfie_photo_fingerprint": None,
            "submitted_at": submission.submitted_at,
            "source": "attendance-location-gate",
        },
    )


def _audit_realtime_gate_rejection(
    *,
    db: Session,
    schedule: models.ClassSchedule,
    student_id: int,
    current_user: models.AuthUser,
    class_date: date,
    payload: schemas.RealtimeAttendanceMarkRequest,
    existing_submission: models.AttendanceSubmission | None,
    reason: str,
    ai_model: str,
    event_type: str,
    distance_m: float | None = None,
    allowed_radius_m: float | None = None,
    attendance_session: models.ClassAttendanceSession | None = None,
    attendance_session_code_hash: str | None = None,
    attendance_attempt: models.AttendanceAttemptToken | None = None,
    request: Request | None = None,
) -> None:
    integrity_flags = _location_integrity_flags(payload, _campus_now())
    if attendance_attempt and attendance_attempt.client_integrity_flags:
        try:
            existing_flags = json.loads(attendance_attempt.client_integrity_flags)
        except json.JSONDecodeError:
            existing_flags = []
        if isinstance(existing_flags, list):
            integrity_flags = _normalize_integrity_flags([*existing_flags, *integrity_flags])
    rejected_submission = _upsert_location_rejected_submission(
        db=db,
        schedule=schedule,
        student_id=int(student_id),
        class_date=class_date,
        payload=payload,
        reason=reason,
        distance_m=distance_m,
        allowed_radius_m=allowed_radius_m,
        existing_submission=existing_submission,
        attendance_session=attendance_session,
        attendance_session_code_hash=attendance_session_code_hash,
        attendance_attempt_token_hash=attendance_attempt.token_hash if attendance_attempt else None,
        browser_fingerprint_hash=(
            attendance_attempt.browser_fingerprint_hash
            if attendance_attempt
            else _attendance_tracking_hash(payload.browser_fingerprint, purpose="browser-fingerprint")
        ),
        client_ip_hash=(
            attendance_attempt.client_ip_hash
            if attendance_attempt
            else _attendance_tracking_hash(_request_client_ip(request), purpose="client-ip")
        ),
        user_agent_hash=(
            attendance_attempt.user_agent_hash
            if attendance_attempt
            else _attendance_tracking_hash(_request_user_agent(request), purpose="user-agent")
        ),
        client_integrity_flags=_integrity_flags_json(integrity_flags),
        ai_model=ai_model,
    )
    db.commit()
    try:
        _sync_location_rejected_submission_to_mongo(rejected_submission)
        publish_domain_event(
            event_type,
            payload={
                "submission_id": int(rejected_submission.id),
                "student_id": int(rejected_submission.student_id),
                "faculty_id": int(rejected_submission.faculty_id),
                "schedule_id": int(rejected_submission.schedule_id),
                "course_id": int(rejected_submission.course_id),
                "class_date": rejected_submission.class_date.isoformat(),
                "status": rejected_submission.status.value,
                "ai_model": rejected_submission.ai_model,
                "location_distance_m": float(rejected_submission.location_distance_m or 0.0),
                "location_allowed_radius_m": float(rejected_submission.location_allowed_radius_m or 0.0),
                "attendance_session_id": rejected_submission.attendance_session_id,
                "attendance_attempt_token_hash": rejected_submission.attendance_attempt_token_hash,
                "client_integrity_flags": rejected_submission.client_integrity_flags,
            },
            scopes={
                f"student:{int(rejected_submission.student_id)}",
                f"faculty:{int(rejected_submission.faculty_id)}",
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
    except Exception as audit_exc:  # noqa: BLE001
        logger.warning(
            "attendance_realtime_gate_rejection_audit_side_effect_failed submission_id=%s event_type=%s error=%s",
            int(rejected_submission.id),
            event_type,
            audit_exc,
        )


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
    seen: set[str] = set()
    for item in parsed:
        normalized = re.sub(r"\s+", "", str(item or "").strip().upper())
        if not normalized:
            continue
        for token in normalized.split(","):
            if not token or token in seen:
                continue
            seen.add(token)
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


def _student_section_key(student: models.Student | None) -> str:
    return re.sub(r"\s+", "", str(student.section if student else "").strip().upper())


def _effective_student_schedules(
    db: Session,
    *,
    student_id: int,
    student_section: str,
    course_ids: list[int] | set[int] | tuple[int, ...],
) -> list[models.ClassSchedule]:
    normalized_course_ids = sorted({int(course_id) for course_id in course_ids if int(course_id or 0) > 0})
    if not normalized_course_ids:
        return []

    schedules = (
        db.query(models.ClassSchedule)
        .filter(
            models.ClassSchedule.is_active.is_(True),
            models.ClassSchedule.course_id.in_(normalized_course_ids),
        )
        .order_by(
            models.ClassSchedule.weekday.asc(),
            models.ClassSchedule.start_time.asc(),
            models.ClassSchedule.id.asc(),
        )
        .all()
    )

    override_filters = [
        (
            (models.TimetableOverride.scope_type == schemas.TimetableOverrideScope.STUDENT.value)
            & (models.TimetableOverride.student_id == student_id)
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
        if override_filters
        else []
    )
    if not applicable_overrides:
        return schedules

    override_schedule_ids = sorted({int(item.schedule_id) for item in applicable_overrides if item.schedule_id})
    override_schedules_by_id = (
        {
            int(row.id): row
            for row in db.query(models.ClassSchedule)
            .filter(
                models.ClassSchedule.id.in_(override_schedule_ids),
                models.ClassSchedule.is_active.is_(True),
            )
            .all()
        }
        if override_schedule_ids
        else {}
    )

    section_overrides = [
        row for row in applicable_overrides
        if row.scope_type == schemas.TimetableOverrideScope.SECTION.value
    ]
    student_overrides = [
        row for row in applicable_overrides
        if row.scope_type == schemas.TimetableOverrideScope.STUDENT.value
    ]
    effective_overrides_by_source: dict[tuple[int, time], tuple[models.TimetableOverride, models.ClassSchedule]] = {}
    for bucket in (section_overrides, student_overrides):
        for override in bucket:
            schedule = override_schedules_by_id.get(int(override.schedule_id))
            if not schedule:
                continue
            source_key = (int(override.source_weekday), override.source_start_time)
            effective_overrides_by_source[source_key] = (override, schedule)

    suppressed_regular_slots = set(effective_overrides_by_source.keys())
    effective_override_targets: dict[tuple[int, time], models.ClassSchedule] = {}
    for _, schedule in effective_overrides_by_source.values():
        target_key = (int(schedule.weekday), schedule.start_time)
        effective_override_targets[target_key] = schedule

    result: list[models.ClassSchedule] = []
    seen_schedule_ids: set[int] = set()
    for schedule in schedules:
        schedule_key = (int(schedule.weekday), schedule.start_time)
        if schedule_key in suppressed_regular_slots or schedule_key in effective_override_targets:
            continue
        seen_schedule_ids.add(int(schedule.id))
        result.append(schedule)

    for schedule in effective_override_targets.values():
        if int(schedule.id) in seen_schedule_ids:
            continue
        if int(schedule.course_id) not in normalized_course_ids:
            continue
        seen_schedule_ids.add(int(schedule.id))
        result.append(schedule)

    result.sort(key=lambda item: (int(item.weekday), item.start_time, int(item.id)))
    return result


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


def _display_media_reference(db: Session, *, object_key: str | None, legacy_data_url: str | None) -> str | None:
    key = str(object_key or "").strip()
    if key:
        # Local dev snapshots can retain object-key references after the metadata rows or
        # remote blob mirror are gone. In that case, fail soft instead of returning a
        # permanently broken image URL to the UI.
        if (os.getenv("APP_RUNTIME_STRICT", "true") or "").strip().lower() not in {"1", "true", "yes", "on"}:
            restored = data_url_for_object(db, key)
            if restored:
                return restored
            value = str(legacy_data_url or "").strip()
            return value or None
        return signed_url_for_object(key)
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


def _store_profile_media_or_503(
    db: Session,
    *,
    owner_table: str,
    owner_id: int,
    media_kind: str,
    data_url: str,
) -> models.MediaObject:
    try:
        return store_data_url_object(
            db,
            owner_table=owner_table,
            owner_id=int(owner_id),
            media_kind=media_kind,
            data_url=data_url,
            retention_days=PROFILE_MEDIA_RETENTION_DAYS,
        )
    except HTTPException:
        raise
    except RuntimeError as exc:
        logger.exception("profile_media_storage_unavailable owner_table=%s owner_id=%s", owner_table, owner_id)
        raise HTTPException(
            status_code=503,
            detail="Profile media storage is temporarily unavailable. Please retry shortly.",
        ) from exc


def _sync_student_to_mongo(db: Session, student: models.Student, *, source: str) -> None:
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
            "profile_photo_url": _display_media_reference(
                db,
                object_key=student.profile_photo_object_key,
                legacy_data_url=student.profile_photo_data_url,
            ),
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


def _sync_faculty_to_mongo(db: Session, faculty: models.Faculty, *, source: str) -> None:
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
            "profile_photo_url": _display_media_reference(
                db,
                object_key=faculty.profile_photo_object_key,
                legacy_data_url=faculty.profile_photo_data_url,
            ),
            "profile_photo_updated_at": faculty.profile_photo_updated_at,
            "profile_photo_locked_until": faculty.profile_photo_locked_until,
            "department": faculty.department,
            "created_at": faculty.created_at,
            "source": source,
        },
    )


def _student_profile_out(db: Session, student: models.Student) -> schemas.StudentProfileOut:
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
        photo_data_url=_display_media_reference(
            db,
            object_key=student.profile_photo_object_key,
            legacy_data_url=student.profile_photo_data_url,
        ),
        can_update_photo_now=can_update_now,
        photo_locked_until=locked_until,
        photo_lock_days_remaining=lock_days_remaining,
        can_update_section_now=not has_section,
        section_locked_until=section_locked_until,
        section_lock_minutes_remaining=section_lock_minutes_remaining,
        section_change_requires_faculty_approval=has_section and section_change_window_open,
    )


def _student_photo_out(db: Session, student: models.Student) -> schemas.StudentProfilePhotoOut:
    can_update_now, locked_until, lock_days_remaining = _photo_lock_state(student)
    has_photo = bool(student.profile_photo_object_key or student.profile_photo_data_url)
    return schemas.StudentProfilePhotoOut(
        has_profile_photo=has_photo,
        photo_data_url=_display_media_reference(
            db,
            object_key=student.profile_photo_object_key,
            legacy_data_url=student.profile_photo_data_url,
        ),
        can_update_now=can_update_now,
        locked_until=locked_until,
        lock_days_remaining=lock_days_remaining,
        registration_number=student.registration_number,
    )


def _reissue_profile_identifiers_if_needed(db: Session) -> dict[str, int]:
    counts = reissue_generated_profile_identifiers(db)
    if counts["students"] or counts["faculty"]:
        db.commit()
    else:
        db.flush()
    return counts


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
        raise HTTPException(status_code=400, detail=SYSTEM_ASSIGNED_STUDENT_ID_MESSAGE)

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
        media = _store_profile_media_or_503(
            db,
            owner_table="students",
            owner_id=int(student.id),
            media_kind="student-profile-photo",
            data_url=incoming_photo,
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


def _faculty_profile_out(db: Session, faculty: models.Faculty) -> schemas.FacultyProfileOut:
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
        photo_data_url=_display_media_reference(
            db,
            object_key=faculty.profile_photo_object_key,
            legacy_data_url=faculty.profile_photo_data_url,
        ),
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
        raise HTTPException(status_code=400, detail=SYSTEM_ASSIGNED_FACULTY_ID_MESSAGE)

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
        media = _store_profile_media_or_503(
            db,
            owner_table="faculty",
            owner_id=int(faculty.id),
            media_kind="faculty-profile-photo",
            data_url=incoming_photo,
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
    normalized_embeddings: list[list[float]] = []
    for item in embeddings:
        if not isinstance(item, list) or not item:
            continue
        try:
            normalized = [float(value) for value in item]
        except (TypeError, ValueError):
            continue
        if all(math.isfinite(value) for value in normalized):
            normalized_embeddings.append(normalized)
    if not normalized_embeddings:
        return None
    parsed["embeddings"] = normalized_embeddings
    signature = parsed.get("signature")
    if isinstance(signature, list) and signature:
        try:
            normalized_signature = [float(value) for value in signature]
        except (TypeError, ValueError):
            normalized_signature = []
        parsed["signature"] = normalized_signature if all(math.isfinite(value) for value in normalized_signature) else []
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
            "attendance_latitude": schedule.attendance_latitude,
            "attendance_longitude": schedule.attendance_longitude,
            "attendance_radius_m": schedule.attendance_radius_m,
            "attendance_location_label": schedule.attendance_location_label,
            "attendance_location_configured": _schedule_attendance_location_configured(schedule),
            "is_active": schedule.is_active,
            "source": source,
            "created_at": schedule.created_at,
        },
    )


def _upsert_class_attendance_session_document(
    session: models.ClassAttendanceSession,
    *,
    source: str,
) -> None:
    _upsert_mongo_by_id(
        "class_attendance_sessions",
        session.id,
        {
            "schedule_id": session.schedule_id,
            "course_id": session.course_id,
            "faculty_id": session.faculty_id,
            "class_date": session.class_date.isoformat(),
            "session_code_hash": session.session_code_hash,
            "code_rotation_seconds": session.code_rotation_seconds,
            "current_code_expires_at": session.current_code_expires_at,
            "generated_at": session.generated_at,
            "expires_at": session.expires_at,
            "opened_by_user_id": session.opened_by_user_id,
            "is_active": session.is_active,
            "source": source,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
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
        if payload.attendance_latitude is not None:
            schedule_changed = _apply_attendance_location_fields(existing, payload) or schedule_changed
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
        attendance_latitude=payload.attendance_latitude,
        attendance_longitude=payload.attendance_longitude,
        attendance_radius_m=payload.attendance_radius_m,
        attendance_location_label=_clean_location_label(payload.attendance_location_label),
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
            "attendance_location_configured": _schedule_attendance_location_configured(schedule),
            "attendance_radius_m": schedule.attendance_radius_m,
            "attendance_location_label": schedule.attendance_location_label,
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
    student_section: str,
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
        same_course_slots = (
            db.query(models.ClassSchedule.id)
            .filter(
                models.ClassSchedule.is_active.is_(True),
                models.ClassSchedule.course_id == schedule.course_id,
                models.ClassSchedule.weekday == schedule.weekday,
            )
            .all()
        )
        if len(same_course_slots) == 1:
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
        classroom_label=student_section or schedule.classroom_label,
        section=student_section or None,
        class_date=class_date,
        is_open_now=is_open_now,
        is_active_now=is_active_now,
        is_ended_now=is_ended_now,
        attendance_status=attendance_status,
        attendance_location_configured=_schedule_attendance_location_configured(schedule),
        attendance_location_label=schedule.attendance_location_label,
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


def _get_or_create_sql_row(
    db: Session,
    *,
    lookup: Callable[[], _RowT | None],
    factory: Callable[[], _RowT],
) -> tuple[_RowT, bool]:
    existing = lookup()
    if existing is not None:
        return existing, False

    savepoint = db.begin_nested()
    instance = factory()
    db.add(instance)
    try:
        db.flush()
    except IntegrityError:
        savepoint.rollback()
        existing = lookup()
        if existing is None:
            raise
        return existing, False

    savepoint.commit()
    return instance, True


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
        faculty, faculty_created = _get_or_create_sql_row(
            db,
            lookup=lambda: db.query(models.Faculty).filter(models.Faculty.email == item["faculty_email"]).first(),
            factory=lambda: models.Faculty(
                name=item["faculty_name"],
                email=item["faculty_email"],
                department=student.department,
            ),
        )
        if faculty_created:
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

        course, course_created = _get_or_create_sql_row(
            db,
            lookup=lambda: db.query(models.Course).filter(models.Course.code == item["course_code"]).first(),
            factory=lambda: models.Course(
                code=item["course_code"],
                title=item["course_title"],
                faculty_id=faculty.id,
            ),
        )
        if course_created:
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

        classroom, classroom_created = _get_or_create_sql_row(
            db,
            lookup=lambda: (
                db.query(models.Classroom)
                .filter(
                    models.Classroom.block == item["classroom_block"],
                    models.Classroom.room_number == item["classroom_room"],
                )
                .first()
            ),
            factory=lambda: models.Classroom(
                block=item["classroom_block"],
                room_number=item["classroom_room"],
                capacity=70,
            ),
        )
        if classroom_created:
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
            assignment, _ = _get_or_create_sql_row(
                db,
                lookup=lambda: (
                    db.query(models.CourseClassroom)
                    .filter(models.CourseClassroom.course_id == course.id)
                    .first()
                ),
                factory=lambda: models.CourseClassroom(course_id=course.id, classroom_id=classroom.id),
            )
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
            schedule, schedule_created = _get_or_create_sql_row(
                db,
                lookup=lambda: (
                    db.query(models.ClassSchedule)
                    .filter(
                        models.ClassSchedule.course_id == course.id,
                        models.ClassSchedule.weekday == item["weekday"],
                        models.ClassSchedule.start_time == start_t,
                    )
                    .first()
                ),
                factory=lambda: models.ClassSchedule(
                    course_id=course.id,
                    faculty_id=faculty.id,
                    weekday=item["weekday"],
                    start_time=start_t,
                    end_time=end_t,
                    classroom_label=item["classroom_label"],
                    is_active=True,
                ),
            )
        else:
            schedule_created = False
        if schedule_created:
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
            enrollment, enrollment_created = _get_or_create_sql_row(
                db,
                lookup=lambda: (
                    db.query(models.Enrollment)
                    .filter(
                        models.Enrollment.student_id == student.id,
                        models.Enrollment.course_id == course.id,
                    )
                    .first()
                ),
                factory=lambda: models.Enrollment(student_id=student.id, course_id=course.id),
            )
        else:
            enrollment_created = False
        if enrollment_created:
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


def _academic_term_config_out(config: models.AcademicTermConfig | None, db: Session) -> schemas.AcademicTermConfigOut:
    start_date, end_date = _academic_class_window(db)
    return schemas.AcademicTermConfigOut(
        class_start_date=config.class_start_date if config else start_date,
        class_end_date=config.class_end_date if config else end_date,
        updated_at=config.updated_at if config else None,
        updated_by_user_id=config.updated_by_user_id if config else None,
    )


@router.get("/admin/academic-term", response_model=schemas.AcademicTermConfigOut)
def get_academic_term_config(
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.OWNER)),
):
    config = db.get(models.AcademicTermConfig, ACADEMIC_TERM_CONFIG_KEY)
    return _academic_term_config_out(config, db)


@router.put("/admin/academic-term", response_model=schemas.AcademicTermConfigOut)
def update_academic_term_config(
    payload: schemas.AcademicTermConfigRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.OWNER)),
):
    config = db.get(models.AcademicTermConfig, ACADEMIC_TERM_CONFIG_KEY)
    if config is None:
        config = models.AcademicTermConfig(
            key=ACADEMIC_TERM_CONFIG_KEY,
            class_start_date=payload.class_start_date,
            class_end_date=payload.class_end_date,
            updated_by_user_id=current_user.id,
            updated_at=datetime.utcnow(),
        )
        db.add(config)
    else:
        config.class_start_date = payload.class_start_date
        config.class_end_date = payload.class_end_date
        config.updated_by_user_id = current_user.id
        config.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(config)
    mirror_document(
        "admin_audit_logs",
        {
            "action": "academic_term_updated",
            "class_start_date": payload.class_start_date.isoformat(),
            "class_end_date": payload.class_end_date.isoformat(),
            "updated_at": config.updated_at,
            "source": "attendance.academic_term",
            "actor_user_id": current_user.id,
            "actor_role": current_user.role.value,
        },
        required=False,
    )
    return _academic_term_config_out(config, db)


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

    schedule_data = payload.model_dump()
    schedule_data["attendance_location_label"] = _clean_location_label(payload.attendance_location_label)
    schedule = models.ClassSchedule(**(schedule_data | {"classroom_label": classroom_label}))
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    _upsert_class_schedule_document(schedule, source="api")
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
            "attendance_location_configured": _schedule_attendance_location_configured(schedule),
            "attendance_radius_m": schedule.attendance_radius_m,
            "attendance_location_label": schedule.attendance_location_label,
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

    schedules = query.order_by(models.ClassSchedule.weekday.asc(), models.ClassSchedule.start_time.asc()).all()
    if current_user.role == models.UserRole.STUDENT:
        return [
            schemas.ClassScheduleOut.model_validate(row).model_copy(
                update={
                    "attendance_latitude": None,
                    "attendance_longitude": None,
                    "attendance_radius_m": None,
                    "attendance_location_configured": _schedule_attendance_location_configured(row),
                }
            )
            for row in schedules
        ]
    return schedules


@router.patch("/schedules/{schedule_id}/location", response_model=schemas.ClassScheduleOut)
def update_schedule_attendance_location(
    schedule_id: int,
    payload: schemas.ClassScheduleLocationUpdate,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    schedule = db.get(models.ClassSchedule, schedule_id)
    if not schedule or not schedule.is_active:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if current_user.role == models.UserRole.FACULTY and int(current_user.faculty_id or 0) != int(schedule.faculty_id):
        raise HTTPException(status_code=403, detail="Faculty can only update GPS locks for their own classes")

    _apply_attendance_location_fields(schedule, payload)
    db.commit()
    db.refresh(schedule)

    _upsert_class_schedule_document(schedule, source="attendance.schedule_location_update")
    mirror_document(
        "admin_audit_logs",
        {
            "action": "schedule_attendance_location_updated",
            "schedule_id": int(schedule.id),
            "course_id": int(schedule.course_id),
            "faculty_id": int(schedule.faculty_id),
            "attendance_radius_m": float(schedule.attendance_radius_m or 0.0),
            "attendance_location_label": schedule.attendance_location_label,
            "updated_at": datetime.utcnow(),
            "source": "attendance.schedule_location_update",
            "actor_user_id": current_user.id,
            "actor_role": current_user.role.value,
        },
        required=False,
    )
    enrolled_student_ids = _enrolled_student_ids_for_course(db, course_id=int(schedule.course_id))
    publish_domain_event(
        "attendance.schedule.location.updated",
        payload={
            "schedule_id": int(schedule.id),
            "course_id": int(schedule.course_id),
            "faculty_id": int(schedule.faculty_id),
            "weekday": int(schedule.weekday),
            "start_time": str(schedule.start_time),
            "end_time": str(schedule.end_time),
            "attendance_location_configured": _schedule_attendance_location_configured(schedule),
            "attendance_location_label": schedule.attendance_location_label,
        },
        scopes={
            "role:admin",
            f"faculty:{int(schedule.faculty_id)}",
            *(f"student:{int(student_id)}" for student_id in enrolled_student_ids),
        },
        topics={"attendance"},
        actor={
            "user_id": int(current_user.id),
            "role": current_user.role.value,
        },
        source="attendance",
    )
    return schedule


@router.post("/schedules/{schedule_id}/session", response_model=schemas.ClassAttendanceSessionOut)
def open_schedule_attendance_session(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    schedule = db.get(models.ClassSchedule, schedule_id)
    if not schedule or not schedule.is_active:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if current_user.role == models.UserRole.FACULTY and int(current_user.faculty_id or 0) != int(schedule.faculty_id):
        raise HTTPException(status_code=403, detail="Faculty can only open attendance sessions for their own classes")
    if not _schedule_attendance_location_configured(schedule):
        raise HTTPException(status_code=400, detail="Set the class GPS lock before opening the attendance code.")

    course = db.get(models.Course, schedule.course_id)
    now_dt = _campus_now()
    class_date = now_dt.date()
    if int(schedule.weekday) != int(class_date.weekday()):
        raise HTTPException(status_code=400, detail="Attendance code can only be opened on the scheduled class day.")

    is_open_now, _, _ = _window_flags(schedule, now_dt, class_date, course=course)
    if not is_open_now:
        raise HTTPException(status_code=400, detail="Attendance code can only be opened during the first 10 minutes.")

    try:
        session, session_code = _open_attendance_session(
            db,
            schedule=schedule,
            class_date=class_date,
            now_dt=now_dt,
            opened_by_user_id=int(current_user.id),
        )
        db.commit()
        db.refresh(session)
    except RuntimeError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        _upsert_class_attendance_session_document(session, source="attendance.session.opened")
        publish_domain_event(
            "attendance.session.opened",
            payload={
                "attendance_session_id": int(session.id),
                "schedule_id": int(schedule.id),
                "course_id": int(schedule.course_id),
                "faculty_id": int(schedule.faculty_id),
                "class_date": class_date.isoformat(),
                "expires_at": session.expires_at.isoformat(),
            },
            scopes={
                "role:admin",
                f"faculty:{int(schedule.faculty_id)}",
                *(f"student:{int(student_id)}" for student_id in _enrolled_student_ids_for_course(db, course_id=int(schedule.course_id))),
            },
            topics={"attendance"},
            actor={
                "user_id": int(current_user.id),
                "role": current_user.role.value,
            },
            source="attendance",
        )
    except Exception as audit_exc:  # noqa: BLE001
        logger.warning(
            "attendance_session_opened_side_effect_failed session_id=%s error=%s",
            int(session.id),
            audit_exc,
        )

    return schemas.ClassAttendanceSessionOut(
        schedule_id=int(schedule.id),
        class_date=class_date,
        session_code=session_code,
        generated_at=session.generated_at,
        expires_at=session.expires_at,
        code_expires_at=session.current_code_expires_at or session.expires_at,
        code_rotation_seconds=_attendance_rotation_seconds(session),
        server_time=now_dt,
        attendance_window_open=True,
        message="Attendance code is open and refreshes automatically for this class window.",
    )


@router.post("/schedules/{schedule_id}/session/validate", response_model=schemas.AttendanceCodeValidateResponse)
def validate_schedule_attendance_session_code(
    schedule_id: int,
    payload: schemas.AttendanceCodeValidateRequest,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    student, schedule, course = _resolve_student_schedule_context(
        db=db,
        current_user=current_user,
        schedule_id=int(schedule_id),
    )
    now_dt = _campus_now()
    class_date = now_dt.date()
    if int(schedule.weekday) != int(class_date.weekday()):
        raise HTTPException(status_code=400, detail="This class is not scheduled for today.")
    is_open_now, _, _ = _window_flags(schedule, now_dt, class_date, course=course)
    if not is_open_now:
        raise HTTPException(status_code=400, detail="Attendance window is closed (only first 10 minutes).")
    if not _schedule_attendance_location_configured(schedule):
        raise HTTPException(
            status_code=400,
            detail="Class GPS lock is not configured yet. Ask the faculty or admin to set it before marking attendance.",
        )
    existing_submission = (
        db.query(models.AttendanceSubmission)
        .filter(
            models.AttendanceSubmission.schedule_id == schedule.id,
            models.AttendanceSubmission.student_id == student.id,
            models.AttendanceSubmission.class_date == class_date,
        )
        .first()
    )
    if existing_submission and existing_submission.status in (
        models.AttendanceSubmissionStatus.VERIFIED,
        models.AttendanceSubmissionStatus.APPROVED,
    ):
        raise HTTPException(status_code=409, detail="Attendance already verified for this class.")

    session, code_hash, code_expires_at = _verify_attendance_session_code(
        db=db,
        schedule=schedule,
        class_date=class_date,
        now_dt=now_dt,
        attendance_session_code=payload.attendance_session_code,
    )
    try:
        attempt, raw_token = _issue_attendance_attempt_token(
            db=db,
            session=session,
            schedule=schedule,
            student=student,
            class_date=class_date,
            now_dt=now_dt,
            code_hash=code_hash,
            request=request,
            browser_fingerprint=payload.browser_fingerprint,
            client_integrity_flags=payload.client_integrity_flags,
        )
        db.commit()
        db.refresh(attempt)
    except HTTPException:
        db.rollback()
        raise

    try:
        publish_domain_event(
            "attendance.session.code_validated",
            payload={
                "attendance_session_id": int(session.id),
                "schedule_id": int(schedule.id),
                "course_id": int(schedule.course_id),
                "student_id": int(student.id),
                "class_date": class_date.isoformat(),
                "token_expires_at": attempt.expires_at.isoformat(),
            },
            scopes={
                f"student:{int(student.id)}",
                f"faculty:{int(schedule.faculty_id)}",
                "role:admin",
            },
            topics={"attendance"},
            actor={
                "user_id": int(current_user.id),
                "student_id": int(student.id),
                "role": current_user.role.value,
            },
            source="attendance",
        )
    except Exception as audit_exc:  # noqa: BLE001
        logger.warning(
            "attendance_code_validation_side_effect_failed attempt_id=%s error=%s",
            int(attempt.id),
            audit_exc,
        )
    return schemas.AttendanceCodeValidateResponse(
        schedule_id=int(schedule.id),
        class_date=class_date,
        attendance_attempt_token=raw_token,
        token_expires_at=attempt.expires_at,
        attendance_session_id=int(session.id),
        code_expires_at=code_expires_at,
        attendance_window_expires_at=session.expires_at,
        code_rotation_seconds=_attendance_rotation_seconds(session),
        room=schedule.attendance_location_label or schedule.classroom_label,
        allowed_radius_m=_schedule_attendance_radius_m(schedule),
        message="Code verified. Continue with browser GPS and facial attendance.",
    )


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
            "attendance_location_configured": _schedule_attendance_location_configured(schedule),
            "attendance_radius_m": schedule.attendance_radius_m,
            "attendance_location_label": schedule.attendance_location_label,
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
            "attendance_location_configured": _schedule_attendance_location_configured(schedule),
            "attendance_location_label": schedule.attendance_location_label,
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
    raise HTTPException(
        status_code=410,
        detail="Default timetable loading is disabled. Faculty or admin must assign stream and section-specific courses.",
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

    _reissue_profile_identifiers_if_needed(db)
    db.refresh(faculty)
    _sync_faculty_to_mongo(db, faculty, source="faculty-profile-read")
    return _faculty_profile_out(db, faculty)


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

    _reissue_profile_identifiers_if_needed(db)
    db.refresh(faculty)

    if (
        payload.name is None
        and payload.section is None
        and payload.photo_data_url is None
    ):
        if payload.faculty_identifier is not None:
            raise HTTPException(status_code=400, detail=SYSTEM_ASSIGNED_FACULTY_ID_MESSAGE)
        raise HTTPException(status_code=400, detail="Provide name, section, and/or photo_data_url")

    changed, _ = _apply_faculty_profile_update(faculty, payload, db=db)
    if changed:
        db.commit()
    else:
        db.flush()

    _sync_faculty_to_mongo(db, faculty, source="faculty-profile-update")

    try:
        mongo_db = get_mongo_db(required=False)
        if mongo_db is not None:
            mongo_db["auth_users"].update_one(
                {"id": int(current_user.id)},
                {"$set": {"name": faculty.name}},
            )
    except RuntimeError:
        logger.warning("faculty_profile_auth_mirror_skipped user_id=%s", int(current_user.id))

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

    return _faculty_profile_out(db, faculty)


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
        return _student_profile_out(db, student)

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

    _sync_student_to_mongo(db, student, source="faculty-approved-section-update")
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

    return _student_profile_out(db, student)


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

    _sync_student_to_mongo(db, student, source="student-profile-photo-read")
    return _student_photo_out(db, student)


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

    _reissue_profile_identifiers_if_needed(db)
    db.refresh(student)
    sync_time = _campus_now()
    changed = sync_student_academic_term(db, student, now=sync_time)
    changed = sync_faculty_sections_for_student(db, student, now=sync_time) > 0 or changed
    if changed:
        db.commit()
        db.refresh(student)
    _sync_student_to_mongo(db, student, source="student-profile-read")
    return _student_profile_out(db, student)


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

    _reissue_profile_identifiers_if_needed(db)
    db.refresh(student)
    if payload.section is not None:
        raise HTTPException(status_code=400, detail="Section is system-assigned from semester, stream, and cohort capacity.")
    if sync_student_academic_term(db, student, now=_campus_now()):
        db.commit()
        db.refresh(student)

    had_registration_number = bool((student.registration_number or "").strip())
    had_enrollment_video = bool(student.enrollment_video_template_json)

    if (
        payload.name is None
        and payload.photo_data_url is None
        and payload.section is None
    ):
        if payload.registration_number is not None:
            raise HTTPException(status_code=400, detail=SYSTEM_ASSIGNED_STUDENT_ID_MESSAGE)
        raise HTTPException(status_code=400, detail="Provide name, section, and/or photo_data_url")

    changed, photo_changed = _apply_student_profile_update(student, payload, db=db)
    if photo_changed:
        _rebuild_profile_face_template(db, student)
        changed = True
    try:
        if changed:
            db.commit()
        else:
            db.flush()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("student_profile_photo_persist_failed student_id=%s", student.id)
        raise HTTPException(
            status_code=503,
            detail="Profile photo could not be saved. Please retry after database storage recovers.",
        ) from exc

    _sync_student_to_mongo(db, student, source="student-profile-update")

    try:
        mongo_db = get_mongo_db(required=False)
        if mongo_db is not None:
            mongo_db["auth_users"].update_one(
                {"id": int(current_user.id)},
                {"$set": {"name": student.name}},
            )
    except RuntimeError:
        logger.warning("student_profile_auth_mirror_skipped user_id=%s", int(current_user.id))

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

    return _student_profile_out(db, student)


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

    _sync_student_to_mongo(db, student, source="student-profile-update")

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

    return _student_photo_out(db, student)


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

    _sync_student_to_mongo(db, student, source="student-enrollment-video")

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
    if sync_student_academic_term(db, student, now=_campus_now()):
        db.commit()
        db.refresh(student)

    db.flush()

    now_dt = _campus_now()
    today = now_dt.date()
    class_start_date, class_end_date = _academic_class_window(db)
    academic_start = max(_academic_start_date(), class_start_date)
    min_week_start = _week_start_for(academic_start)
    requested_week_start = _week_start_for(week_start or today)
    current_week_start = max(requested_week_start, min_week_start)
    current_week_end = current_week_start + timedelta(days=6)
    if current_week_start > class_end_date or current_week_end < class_start_date:
        return schemas.WeeklyTimetableOut(
            week_start=current_week_start,
            min_navigable_date=academic_start,
            server_time=now_dt,
            server_epoch_ms=_campus_datetime_to_epoch_ms(now_dt),
            server_date=today,
            campus_timezone=_campus_timezone_name(),
            classes=[],
        )

    enrollments = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.student_id == current_user.student_id)
        .all()
    )
    course_ids = [item.course_id for item in enrollments]

    result: list[schemas.TimetableClassOut] = []
    student_section = _student_section_key(student)
    effective_schedules = _effective_student_schedules(
        db,
        student_id=int(current_user.student_id),
        student_section=student_section,
        course_ids=course_ids,
    )

    for schedule in effective_schedules:
        item = _build_timetable_class_item(
            db,
            student_id=current_user.student_id,
            student_section=student_section,
            current_week_start=current_week_start,
            academic_start=academic_start,
            now_dt=now_dt,
            schedule=schedule,
        )
        if item and class_start_date <= item.class_date <= class_end_date:
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
        models.MakeUpClass.class_date >= max(current_week_start, class_start_date),
        models.MakeUpClass.class_date <= min(current_week_end, class_end_date),
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
        if sections and int(remedial.id) not in targeted_remedial_class_ids:
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
        server_time=now_dt,
        server_epoch_ms=_campus_datetime_to_epoch_ms(now_dt),
        server_date=today,
        campus_timezone=_campus_timezone_name(),
        classes=result,
    )


@router.get("/student/attendance-history", response_model=schemas.StudentAttendanceHistoryOut)
def get_student_attendance_history(
    limit: int = Query(default=1000, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    academic_start = _academic_start_date()
    now_dt = _campus_now()
    today = now_dt.date()
    saarthi_today = _student_saarthi_materialization_through_date(
        db,
        student_id=int(current_user.student_id),
        academic_start=academic_start,
        today=today,
    )
    if should_materialize_saarthi_attendance(
        db,
        student_id=int(current_user.student_id),
        academic_start=academic_start,
        today=saarthi_today,
    ):
        materialize_saarthi_attendance(
            db,
            student_id=int(current_user.student_id),
            academic_start=academic_start,
            today=saarthi_today,
        )
        db.commit()
    fetch_limit = min(3000, max(limit * 3, 80))
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

    enrollments = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.student_id == current_user.student_id)
        .all()
    )
    enrolled_course_ids = {int(item.course_id) for item in enrollments}
    student = db.get(models.Student, current_user.student_id)

    if not submissions and not records and not enrolled_course_ids:
        return schemas.StudentAttendanceHistoryOut(records=[])

    course_ids = sorted(
        {
            *enrolled_course_ids,
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

    fallback_schedules = _effective_student_schedules(
        db,
        student_id=int(current_user.student_id),
        student_section=_student_section_key(student),
        course_ids=course_ids,
    )
    schedule_ids = sorted({
        *[item.schedule_id for item in submissions],
        *[item.id for item in fallback_schedules],
    })
    schedules_by_id = (
        {
            row.id: row
            for row in db.query(models.ClassSchedule).filter(models.ClassSchedule.id.in_(schedule_ids)).all()
        }
        if schedule_ids
        else {}
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
        if len(candidate_schedules) == 1:
            schedule = candidate_schedules[0]
            key = (int(record.course_id), record.attendance_date, int(schedule.id))
            if key not in submission_keys:
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

    keyed_items = {
        (int(schedules_by_id[int(row.schedule_id)].course_id), row.class_date, int(row.schedule_id))
        for row in items
        if row.schedule_id is not None and int(row.schedule_id) in schedules_by_id
    }
    for schedule in fallback_schedules:
        course = courses.get(schedule.course_id)
        faculty = faculties.get(schedule.faculty_id if schedule.faculty_id is not None else (course.faculty_id if course else None))
        start_offset = (int(schedule.weekday) - int(academic_start.weekday())) % 7
        class_date = academic_start + timedelta(days=start_offset)
        while class_date <= today:
            if class_date == today and now_dt.time() < schedule.start_time:
                break
            key = (int(schedule.course_id), class_date, int(schedule.id))
            if key not in keyed_items:
                items.append(
                    schemas.StudentAttendanceHistoryItemOut(
                        schedule_id=schedule.id,
                        class_date=class_date,
                        start_time=schedule.start_time,
                        end_time=schedule.end_time,
                        course_code=course.code if course else f"C-{schedule.course_id}",
                        course_title=course.title if course else "Unknown Course",
                        faculty_name=faculty.name if faculty else "Faculty",
                        status=models.AttendanceStatus.ABSENT,
                        source="scheduled-absence",
                    )
                )
                keyed_items.add(key)
            class_date += timedelta(days=7)

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
    now_dt = _campus_now()
    today = now_dt.date()
    saarthi_today = _student_saarthi_materialization_through_date(
        db,
        student_id=int(current_user.student_id),
        academic_start=academic_start,
        today=today,
    )
    if should_materialize_saarthi_attendance(
        db,
        student_id=int(current_user.student_id),
        academic_start=academic_start,
        today=saarthi_today,
    ):
        materialize_saarthi_attendance(
            db,
            student_id=int(current_user.student_id),
            academic_start=academic_start,
            today=saarthi_today,
        )
        db.commit()

    enrollments = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.student_id == current_user.student_id)
        .all()
    )
    enrolled_course_ids = {item.course_id for item in enrollments}
    student = db.get(models.Student, current_user.student_id)
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
    schedules = _effective_student_schedules(
        db,
        student_id=int(current_user.student_id),
        student_section=_student_section_key(student),
        course_ids=course_ids,
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
    delivered_record_fallback_counts: dict[int, int] = {}
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
        fallback_slots = 0
        if len(delivered_schedule_ids_for_day) <= 1:
            fallback_slots = len(missing_schedule_ids)
        if not delivered_schedule_ids_for_day and not submission_schedule_ids:
            fallback_slots = 1

        if fallback_slots > 0:
            delivered_record_fallback_counts[normalized_course_id] = (
                delivered_record_fallback_counts.get(normalized_course_id, 0) + fallback_slots
            )

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
        delivered_by_record_fallback = delivered_record_fallback_counts.get(course_id, 0)
        delivered_from_evidence = delivered_by_submissions + delivered_by_record_fallback
        delivered = max(delivered_by_schedule, delivered_from_evidence, delivered_by_records)
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

    today = _campus_today()
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
    proof_photo = str(payload.proof_photo_data_url or "").strip()
    if not proof_photo:
        raise HTTPException(status_code=400, detail="Supporting proof image is required for rectification")
    if not proof_photo.startswith("data:image/"):
        raise HTTPException(status_code=400, detail="proof_photo_data_url must be an image data URL")
    proof_photo_object_key: str | None = None
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
    publish_domain_event(
        "attendance.rectification.requested",
        payload={
            "request_id": int(request.id),
            "student_id": int(request.student_id),
            "faculty_id": int(request.faculty_id or 0),
            "schedule_id": int(request.schedule_id),
            "course_id": int(request.course_id),
            "class_date": request.class_date.isoformat(),
            "status": request.status.value,
        },
        scopes={
            f"student:{int(request.student_id)}",
            f"faculty:{int(request.faculty_id or 0)}",
        },
        topics={"attendance"},
        actor={
            "user_id": int(current_user.id),
            "student_id": int(current_user.student_id or 0),
            "role": current_user.role.value,
        },
        source="attendance",
    )
    faculty = db.get(models.Faculty, request.faculty_id)

    return _student_rectification_out(
        request,
        course=course,
        faculty=faculty,
    )


def _resolve_student_face_context(
    *,
    db: Session,
    current_user: models.AuthUser,
) -> models.Student:
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
    return student


def _resolve_student_schedule_context(
    *,
    db: Session,
    current_user: models.AuthUser,
    schedule_id: int,
) -> tuple[models.Student, models.ClassSchedule, models.Course]:
    student = _resolve_student_face_context(db=db, current_user=current_user)

    schedule = db.get(models.ClassSchedule, schedule_id)
    if not schedule or not schedule.is_active:
        raise HTTPException(status_code=404, detail="Class schedule not found")
    course = db.get(models.Course, schedule.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found for schedule")
    if sync_student_academic_term(db, student, now=_campus_now()):
        db.flush()

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
    schedule: models.ClassSchedule | None,
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
    profile_photo_data_url = _student_profile_photo_data_url(db, student)
    if not profile_photo_data_url:
        raise HTTPException(status_code=400, detail="Upload profile photo before marking attendance")
    if enrollment_template is None:
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
    if profile_template is None:
        raise HTTPException(
            status_code=400,
            detail="Upload a valid profile face photo before marking attendance",
        )

    def _run_reference_verification(template: dict, reference_name: str) -> tuple[dict, bool, float, str, str]:
        verdict = verify_face_sequence_opencv(
            profile_photo_data_url,
            selfie_frames,
            subject_label=f"{student.email}:{reference_name}",
            profile_template=template,
            require_dnn=True,
        )
        if not bool(verdict.get("available")):
            reason = str(verdict.get("reason", "OpenCV verification unavailable"))
            raise HTTPException(status_code=503, detail=f"OpenCV verification unavailable: {reason}")
        confidence = max(0.0, min(1.0, float(verdict.get("confidence", 0.0))))
        engine = str(verdict.get("engine") or "opencv-dnn-yunet-sface-v1")
        reason = str(verdict.get("reason") or "Face not recognized")
        matched = bool(verdict.get("match")) and confidence >= FACE_MATCH_PASS_THRESHOLD
        return verdict, matched, confidence, engine, reason

    enrollment_verdict, enrollment_match, enrollment_confidence, enrollment_engine, enrollment_reason = (
        _run_reference_verification(enrollment_template, "enrollment")
    )
    profile_verdict, profile_match, profile_confidence, profile_engine, profile_reason = _run_reference_verification(
        profile_template,
        "profile",
    )

    final_match = bool(enrollment_match and profile_match)
    final_confidence = min(enrollment_confidence, profile_confidence)
    final_engine = enrollment_engine if enrollment_engine == profile_engine else f"{enrollment_engine}+{profile_engine}"
    if final_match:
        final_reason = (
            "Verified against enrollment and profile templates "
            f"(enrollment={enrollment_confidence:.3f}, profile={profile_confidence:.3f})."
        )
    elif not enrollment_match and not profile_match:
        final_reason = (
            f"Enrollment mismatch: {enrollment_reason} | "
            f"Profile mismatch: {profile_reason}"
        )
    elif not enrollment_match:
        final_reason = f"Enrollment mismatch: {enrollment_reason}"
    else:
        final_reason = f"Profile mismatch: {profile_reason}"

    ai_verdict = _client_ai_verdict(payload)
    schedule_log_value = int(schedule.id) if schedule is not None else 0
    if ai_verdict:
        logger.info(
            "attendance_client_ai_observation student=%s schedule_id=%s ai_match=%s ai_confidence=%.4f ai_reason=%s",
            student.email,
            schedule_log_value,
            bool(ai_verdict.get("match")),
            float(ai_verdict.get("confidence", 0.0)),
            str(ai_verdict.get("reason") or ""),
        )

    status_value = (
        models.AttendanceSubmissionStatus.VERIFIED
        if final_match and final_confidence >= FACE_MATCH_PASS_THRESHOLD
        else models.AttendanceSubmissionStatus.REJECTED
    )
    enrollment_liveness_ok = bool((enrollment_verdict.get("liveness") or {}).get("ok"))
    profile_liveness_ok = bool((profile_verdict.get("liveness") or {}).get("ok"))
    liveness_ok = bool(enrollment_liveness_ok and profile_liveness_ok)
    required_frames = max(
        int(enrollment_verdict.get("required_consecutive_frames", FACE_MULTI_FRAME_MIN)),
        int(profile_verdict.get("required_consecutive_frames", FACE_MULTI_FRAME_MIN)),
    )
    matched_frames = min(
        int(enrollment_verdict.get("consecutive_frames_matched", 0)),
        int(profile_verdict.get("consecutive_frames_matched", 0)),
    )
    accepted_frames = min(
        int(enrollment_verdict.get("accepted_frames", 0)),
        int(profile_verdict.get("accepted_frames", 0)),
    )
    total_frames = max(
        int(enrollment_verdict.get("total_frames", len(selfie_frames))),
        int(profile_verdict.get("total_frames", len(selfie_frames))),
    )
    logger.info(
        "attendance_security_audit ts=%s student=%s schedule_id=%s confidence=%.4f threshold=%.2f decision=%s "
        "engine=%s streak=%s/%s accepted=%s/%s liveness=%s reason=%s",
        datetime.utcnow().isoformat(),
        student.email,
        schedule_log_value,
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
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if payload.demo_mode and not _demo_features_enabled():
        raise HTTPException(status_code=403, detail="Demo attendance mode is disabled in production.")

    location_distance_m: float | None = None
    location_allowed_radius_m: float | None = None
    submission: models.AttendanceSubmission | None = None
    attendance_session: models.ClassAttendanceSession | None = None
    attendance_attempt: models.AttendanceAttemptToken | None = None
    if payload.demo_mode:
        student = _resolve_student_face_context(
            db=db,
            current_user=current_user,
        )
        schedule = None
        today = _campus_today()
    else:
        if not payload.schedule_id:
            raise HTTPException(status_code=400, detail="schedule_id is required")
        student, schedule, course = _resolve_student_schedule_context(
            db=db,
            current_user=current_user,
            schedule_id=int(payload.schedule_id),
        )

        now_dt = _campus_now()
        today = now_dt.date()
        if schedule.weekday != today.weekday():
            raise HTTPException(status_code=400, detail="This class is not scheduled for today")
        class_start_date, class_end_date = _academic_class_window(db)
        if today < class_start_date or today > class_end_date:
            raise HTTPException(status_code=403, detail="Attendance is outside the active academic class date window")

        is_open_now, _, _ = _window_flags(schedule, now_dt, today, course=course)
        if not is_open_now:
            raise HTTPException(status_code=400, detail="Attendance window is closed (only first 10 minutes)")
        submission = (
            db.query(models.AttendanceSubmission)
            .filter(
                models.AttendanceSubmission.schedule_id == schedule.id,
                models.AttendanceSubmission.student_id == current_user.student_id,
                models.AttendanceSubmission.class_date == today,
            )
            .first()
        )
        if submission and submission.status in (
            models.AttendanceSubmissionStatus.VERIFIED,
            models.AttendanceSubmissionStatus.APPROVED,
        ):
            return schemas.RealtimeAttendanceMarkResponse(
                submission_id=submission.id,
                status=submission.status,
                requires_faculty_review=False,
                message="Attendance already verified for this class",
                demo_mode=False,
                persistence_skipped=False,
                verification_engine=submission.ai_model or "previous-verification",
                verification_confidence=float(submission.ai_confidence or 0.0),
                verification_reason=submission.ai_reason,
                location_distance_m=submission.location_distance_m,
                location_allowed_radius_m=submission.location_allowed_radius_m,
            )
        try:
            attendance_attempt, attendance_session = _verify_attendance_attempt_token(
                db=db,
                schedule=schedule,
                student=student,
                class_date=today,
                now_dt=now_dt,
                request=request,
                payload=payload,
            )
        except AttendanceAttemptTokenError as exc:
            if exc.auditable:
                _audit_realtime_gate_rejection(
                    db=db,
                    schedule=schedule,
                    student_id=int(current_user.student_id or student.id),
                    current_user=current_user,
                    class_date=today,
                    payload=payload,
                    existing_submission=submission,
                    reason=str(exc.detail or "Attendance session code rejected"),
                    ai_model="attendance-session-token-v1",
                    event_type="attendance.session.rejected",
                    attendance_session=exc.session,
                    attendance_session_code_hash=exc.session.session_code_hash if exc.session else None,
                    request=request,
                )
            raise

        try:
            location_distance_m, location_allowed_radius_m = _verify_attendance_location(
                schedule=schedule,
                payload=payload,
            )
        except AttendanceLocationError as exc:
            if exc.auditable:
                _audit_realtime_gate_rejection(
                    db=db,
                    schedule=schedule,
                    student_id=int(current_user.student_id or student.id),
                    current_user=current_user,
                    class_date=today,
                    payload=payload,
                    existing_submission=submission,
                    reason=str(exc.detail or "Attendance location rejected"),
                    distance_m=exc.distance_m,
                    allowed_radius_m=exc.allowed_radius_m,
                    attendance_session=attendance_session,
                    attendance_session_code_hash=attendance_attempt.session_code_hash if attendance_attempt else None,
                    attendance_attempt=attendance_attempt,
                    request=request,
                    ai_model="gps-geofence-v1",
                    event_type="attendance.location.rejected",
                )
            raise

    primary_selfie, final_confidence, final_engine, status_value, final_reason = _verify_student_face_payload(
        db=db,
        student=student,
        schedule=schedule,
        payload=payload,
    )
    final_match = status_value == models.AttendanceSubmissionStatus.VERIFIED

    if payload.demo_mode:
        message = (
            "Demo face verification succeeded. Demo mode did not save any attendance data."
            if status_value == models.AttendanceSubmissionStatus.VERIFIED
            else f"{_public_rejection_message(final_reason, final_confidence)} Demo mode did not save any attendance data."
        )
        return schemas.RealtimeAttendanceMarkResponse(
            submission_id=0,
            status=status_value,
            requires_faculty_review=False,
            message=message,
            demo_mode=True,
            persistence_skipped=True,
            verification_engine=final_engine,
            verification_confidence=final_confidence,
            verification_reason=final_reason,
            location_distance_m=None,
            location_allowed_radius_m=None,
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
            location_latitude=payload.location_latitude,
            location_longitude=payload.location_longitude,
            location_accuracy_m=payload.location_accuracy_m,
            location_distance_m=location_distance_m,
            location_allowed_radius_m=location_allowed_radius_m,
            attendance_session_id=attendance_session.id if attendance_session else None,
            attendance_session_code_hash=attendance_attempt.session_code_hash if attendance_attempt else (
                attendance_session.session_code_hash if attendance_session else None
            ),
            attendance_attempt_token_hash=attendance_attempt.token_hash if attendance_attempt else None,
            browser_fingerprint_hash=attendance_attempt.browser_fingerprint_hash if attendance_attempt else None,
            client_ip_hash=attendance_attempt.client_ip_hash if attendance_attempt else None,
            user_agent_hash=attendance_attempt.user_agent_hash if attendance_attempt else None,
            client_integrity_flags=attendance_attempt.client_integrity_flags if attendance_attempt else None,
            status=status_value,
        )
        db.add(submission)
    else:
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
        submission.location_latitude = payload.location_latitude
        submission.location_longitude = payload.location_longitude
        submission.location_accuracy_m = payload.location_accuracy_m
        submission.location_distance_m = location_distance_m
        submission.location_allowed_radius_m = location_allowed_radius_m
        submission.attendance_session_id = attendance_session.id if attendance_session else None
        submission.attendance_session_code_hash = attendance_attempt.session_code_hash if attendance_attempt else (
            attendance_session.session_code_hash if attendance_session else None
        )
        submission.attendance_attempt_token_hash = attendance_attempt.token_hash if attendance_attempt else None
        submission.browser_fingerprint_hash = attendance_attempt.browser_fingerprint_hash if attendance_attempt else None
        submission.client_ip_hash = attendance_attempt.client_ip_hash if attendance_attempt else None
        submission.user_agent_hash = attendance_attempt.user_agent_hash if attendance_attempt else None
        submission.client_integrity_flags = attendance_attempt.client_integrity_flags if attendance_attempt else None
        submission.status = status_value
        submission.submitted_at = datetime.utcnow()
        submission.reviewed_at = None
        submission.reviewed_by_faculty_id = None
        submission.review_note = None

    db.flush()

    if status_value == models.AttendanceSubmissionStatus.VERIFIED:
        if attendance_attempt is not None:
            attendance_attempt.consumed_at = datetime.utcnow()
            attendance_attempt.updated_at = datetime.utcnow()
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
            "location_latitude": submission.location_latitude,
            "location_longitude": submission.location_longitude,
            "location_accuracy_m": submission.location_accuracy_m,
            "location_distance_m": submission.location_distance_m,
            "location_allowed_radius_m": submission.location_allowed_radius_m,
            "attendance_session_id": submission.attendance_session_id,
            "attendance_session_code_hash": submission.attendance_session_code_hash,
            "attendance_attempt_token_hash": submission.attendance_attempt_token_hash,
            "browser_fingerprint_hash": submission.browser_fingerprint_hash,
            "client_ip_hash": submission.client_ip_hash,
            "user_agent_hash": submission.user_agent_hash,
            "client_integrity_flags": submission.client_integrity_flags,
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
            "location_distance_m": float(submission.location_distance_m or 0.0),
            "location_allowed_radius_m": float(submission.location_allowed_radius_m or 0.0),
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
        demo_mode=False,
        persistence_skipped=False,
        verification_engine=final_engine,
        verification_confidence=final_confidence,
        verification_reason=final_reason,
        location_distance_m=location_distance_m,
        location_allowed_radius_m=location_allowed_radius_m,
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
    class_date = class_date or _campus_today()

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
                location_distance_m=item.location_distance_m,
                location_allowed_radius_m=item.location_allowed_radius_m,
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
    schedule_id: int | None = Query(default=None, gt=0),
    class_date: date | None = Query(default=None),
    include_resolved: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    schedule: models.ClassSchedule | None = None
    query = db.query(models.AttendanceRectificationRequest)

    if schedule_id is not None:
        schedule = db.get(models.ClassSchedule, int(schedule_id))
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")

        if current_user.role == models.UserRole.FACULTY and current_user.faculty_id != schedule.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty can only access their own rectification queue")

        query = query.filter(models.AttendanceRectificationRequest.schedule_id == int(schedule_id))
    elif current_user.role == models.UserRole.FACULTY:
        if not current_user.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty account is not linked correctly")
        query = query.filter(
            models.AttendanceRectificationRequest.faculty_id == int(current_user.faculty_id)
        )

    if class_date is not None:
        query = query.filter(models.AttendanceRectificationRequest.class_date == class_date)

    if not include_resolved:
        query = query.filter(
            models.AttendanceRectificationRequest.status == models.AttendanceRectificationStatus.PENDING
        )
    requests = query.order_by(
        case(
            (models.AttendanceRectificationRequest.status == models.AttendanceRectificationStatus.PENDING, 0),
            else_=1,
        ),
        models.AttendanceRectificationRequest.requested_at.desc(),
        models.AttendanceRectificationRequest.id.desc(),
    ).all()

    student_ids = sorted({item.student_id for item in requests})
    course_ids = sorted({item.course_id for item in requests})
    students = (
        {row.id: row for row in db.query(models.Student).filter(models.Student.id.in_(student_ids)).all()}
        if student_ids
        else {}
    )
    courses = (
        {row.id: row for row in db.query(models.Course).filter(models.Course.id.in_(course_ids)).all()}
        if course_ids
        else {}
    )

    payload = [
        _faculty_rectification_out(
            item,
            student=students.get(item.student_id),
            course=courses.get(item.course_id),
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
    affected_student_ids = sorted({int(item.student_id) for item in pending_submissions})
    event_scopes = {
        "role:admin",
        f"faculty:{int(reviewer_faculty_id or 0)}",
        *(f"student:{sid}" for sid in affected_student_ids),
    }
    publish_domain_event(
        "attendance.reviewed",
        payload={
            "schedule_id": int(payload.schedule_id),
            "class_date": payload.class_date.isoformat(),
            "action": payload.action.value,
            "updated_submission_ids": [int(item.id) for item in pending_submissions],
            "affected_student_ids": affected_student_ids,
            "approved": int(approved),
            "rejected": int(rejected),
            "faculty_id": int(reviewer_faculty_id or 0),
        },
        scopes=event_scopes,
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

    notification_student_ids = list(absent_student_ids)
    if is_saarthi_course(course) and payload.attendance_date.weekday() == 6:
        missed_student_ids = _saarthi_missed_student_ids(
            db,
            course_id=int(course.id),
            attendance_date=payload.attendance_date,
            enrolled_student_ids=[int(item.student_id) for item in enrollments],
        )
        notification_student_ids = [
            int(student_id)
            for student_id in absent_student_ids
            if int(student_id) in missed_student_ids
        ]

    notifications_sent = 0
    for student_id in notification_student_ids:
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
    course = db.get(models.Course, int(course_id))
    if course is not None and is_saarthi_course(course) and attendance_date.weekday() == 6:
        missed_student_ids = _saarthi_missed_student_ids(
            db,
            course_id=int(course.id),
            attendance_date=attendance_date,
        )
        if not missed_student_ids:
            return []
        return (
            db.query(models.Student)
            .filter(models.Student.id.in_(sorted(missed_student_ids)))
            .all()
        )

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


@router.post("/recovery/retro-notify", response_model=schemas.AttendanceRecoveryRetroDispatchOut)
def retro_dispatch_recovery_notifications(
    payload: schemas.AttendanceRecoveryRetroDispatchRequest,
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    result = retro_send_recovery_notifications(
        db,
        student_id=payload.student_id,
        course_id=payload.course_id,
        limit=payload.limit,
        force_resend=bool(payload.force_resend),
        dry_run=bool(payload.dry_run),
        cooldown_minutes=payload.cooldown_minutes,
        refresh_scope=bool(payload.refresh_scope),
    )
    if not payload.dry_run:
        db.commit()
    publish_domain_event(
        "attendance.recovery.retro_notified",
        payload={
            "student_id": payload.student_id,
            "course_id": payload.course_id,
            "limit": int(payload.limit),
            "dry_run": bool(payload.dry_run),
            "force_resend": bool(payload.force_resend),
            "evaluated": int(result.get("evaluated", 0)),
            "eligible": int(result.get("eligible", 0)),
            "dispatched": int(result.get("dispatched", 0)),
            "skipped_cooldown": int(result.get("skipped_cooldown", 0)),
            "failed": int(result.get("failed", 0)),
        },
        scopes={"role:admin"},
        topics={"attendance", "admin"},
        source="attendance",
    )
    return schemas.AttendanceRecoveryRetroDispatchOut(
        evaluated=int(result.get("evaluated", 0)),
        eligible=int(result.get("eligible", 0)),
        dispatched=int(result.get("dispatched", 0)),
        skipped_cooldown=int(result.get("skipped_cooldown", 0)),
        failed=int(result.get("failed", 0)),
        forced=bool(result.get("forced", False)),
        dry_run=bool(result.get("dry_run", False)),
        triggered_at=datetime.utcnow(),
    )
