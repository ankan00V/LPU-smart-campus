from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models
from .attendance_ledger import append_event_and_recompute
from .enterprise_controls import resolve_secret
from .workers import enqueue_notification, enqueue_notification_after_commit

SAARTHI_COURSE_CODE = "CON111"
SAARTHI_COURSE_TITLE = "Councelling and Happiness"
SAARTHI_FACULTY_NAME = "Saarthi (AI Mentor)"
SAARTHI_FACULTY_EMAIL = "saarthi.ai.mentor@lpu.local"
SAARTHI_FACULTY_IDENTIFIER = "SAARTHI-AI-MENTOR"
SAARTHI_MANDATORY_WEEKDAY = 6  # Sunday
SAARTHI_ATTENDANCE_MINUTES = 60
SAARTHI_MISSED_STUDENT_ALERT = "saarthi_missed_student_alert"
SAARTHI_MISSED_ADMIN_ALERT = "saarthi_missed_admin_alert"
SAARTHI_MISSED_STUDENT_CHANNEL = "saarthi-missed-student"
SAARTHI_MISSED_ADMIN_CHANNEL = "saarthi-missed-admin"

logger = logging.getLogger(__name__)


@dataclass
class SaarthiBundle:
    faculty: models.Faculty
    course: models.Course
    enrollment: models.Enrollment | None


def _compact_email(value: str | None) -> str:
    return str(value or "").strip().lower()


def _notification_log_exists(
    db: Session,
    *,
    student_id: int,
    sent_to: str,
    channel: str,
    message: str,
) -> bool:
    return (
        db.query(models.NotificationLog.id)
        .filter(
            models.NotificationLog.student_id == int(student_id),
            models.NotificationLog.sent_to == str(sent_to),
            models.NotificationLog.channel == str(channel),
            models.NotificationLog.message == str(message),
        )
        .first()
        is not None
    )


def _saarthi_admin_recipient_emails(db: Session) -> list[str]:
    rows = (
        db.query(models.AuthUser.email)
        .filter(
            models.AuthUser.role == models.UserRole.ADMIN,
            models.AuthUser.is_active.is_(True),
        )
        .order_by(models.AuthUser.email.asc())
        .all()
    )
    seen: set[str] = set()
    recipients: list[str] = []
    for (email,) in rows:
        normalized = _compact_email(email)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        recipients.append(normalized)
    return recipients


def _build_saarthi_missed_notification_payloads(
    db: Session,
    *,
    student: models.Student,
    mandatory_date: date,
    week_start_date: date,
    message_count: int,
    last_message_at: datetime | None,
) -> list[dict[str, object]]:
    student_email = _compact_email(student.email)
    registration_number = str(student.registration_number or "").strip() or f"ST-{int(student.id)}"
    stable_message = f"saarthi-missed:{int(student.id)}:{mandatory_date.isoformat()}"
    base_payload = {
        "student_id": int(student.id),
        "student_name": str(student.name or "").strip() or "Student",
        "student_email": student_email,
        "registration_number": registration_number,
        "section": str(student.section or "").strip() or "Unknown",
        "department": str(student.department or "").strip() or "Unknown",
        "course_code": SAARTHI_COURSE_CODE,
        "course_title": SAARTHI_COURSE_TITLE,
        "faculty_name": SAARTHI_FACULTY_NAME,
        "mandatory_date": mandatory_date.isoformat(),
        "week_start_date": week_start_date.isoformat(),
        "message_count": max(0, int(message_count or 0)),
        "last_message_at": last_message_at.isoformat() if last_message_at is not None else "",
        "message": stable_message,
    }
    payloads: list[dict[str, object]] = []
    if student_email:
        payloads.append(
            {
                **base_payload,
                "type": SAARTHI_MISSED_STUDENT_ALERT,
                "recipient_email": student_email,
                "log_channel": SAARTHI_MISSED_STUDENT_CHANNEL,
            }
        )
    for admin_email in _saarthi_admin_recipient_emails(db):
        payloads.append(
            {
                **base_payload,
                "type": SAARTHI_MISSED_ADMIN_ALERT,
                "recipient_email": admin_email,
                "log_channel": SAARTHI_MISSED_ADMIN_CHANNEL,
            }
        )
    return payloads


def enqueue_saarthi_missed_notifications(
    db: Session,
    *,
    student: models.Student,
    mandatory_date: date,
    week_start_date: date,
    message_count: int = 0,
    last_message_at: datetime | None = None,
    after_commit: bool = False,
) -> int:
    if mandatory_date.weekday() != SAARTHI_MANDATORY_WEEKDAY:
        return 0

    payloads = _build_saarthi_missed_notification_payloads(
        db,
        student=student,
        mandatory_date=mandatory_date,
        week_start_date=week_start_date,
        message_count=message_count,
        last_message_at=last_message_at,
    )
    enqueued = 0
    for payload in payloads:
        recipient_email = _compact_email(str(payload.get("recipient_email") or ""))
        log_channel = str(payload.get("log_channel") or "").strip()
        log_message = str(payload.get("message") or "").strip()
        if not recipient_email or not log_channel or not log_message:
            continue
        if _notification_log_exists(
            db,
            student_id=int(student.id),
            sent_to=recipient_email,
            channel=log_channel,
            message=log_message,
        ):
            continue
        try:
            if after_commit:
                enqueue_notification_after_commit(db, payload)
            else:
                enqueue_notification(payload)
            enqueued += 1
        except Exception:  # noqa: BLE001
            logger.exception(
                "Saarthi missed notification enqueue failed",
                extra={
                    "student_id": int(student.id),
                    "mandatory_date": mandatory_date.isoformat(),
                    "recipient_email": recipient_email,
                    "after_commit": after_commit,
                },
            )
    return enqueued


def saarthi_week_start(target_date: date) -> date:
    return target_date - timedelta(days=target_date.weekday())


def saarthi_mandatory_date(target_date: date) -> date:
    return saarthi_week_start(target_date) + timedelta(days=SAARTHI_MANDATORY_WEEKDAY)


def saarthi_reporting_window(reference_date: date) -> tuple[date, date]:
    week_start_date = saarthi_week_start(reference_date)
    mandatory_date = week_start_date + timedelta(days=SAARTHI_MANDATORY_WEEKDAY)
    if reference_date < mandatory_date:
        week_start_date -= timedelta(days=7)
        mandatory_date -= timedelta(days=7)
    return week_start_date, mandatory_date


def is_saarthi_course(course: models.Course | None) -> bool:
    if course is None:
        return False
    return str(course.code or "").strip().upper() == SAARTHI_COURSE_CODE


def ensure_saarthi_bundle(db: Session, *, student_id: int | None = None) -> SaarthiBundle:
    faculty = (
        db.query(models.Faculty)
        .filter(models.Faculty.faculty_identifier == SAARTHI_FACULTY_IDENTIFIER)
        .first()
    )
    if faculty is None:
        faculty = (
            db.query(models.Faculty)
            .filter(models.Faculty.email == SAARTHI_FACULTY_EMAIL)
            .first()
        )
    if faculty is None:
        faculty = models.Faculty(
            name=SAARTHI_FACULTY_NAME,
            email=SAARTHI_FACULTY_EMAIL,
            faculty_identifier=SAARTHI_FACULTY_IDENTIFIER,
            section="ALL",
            department="Student Wellness",
            created_at=datetime.utcnow(),
        )
        db.add(faculty)
        db.flush()

    course = (
        db.query(models.Course)
        .filter(models.Course.code == SAARTHI_COURSE_CODE)
        .first()
    )
    if course is None:
        course = models.Course(
            code=SAARTHI_COURSE_CODE,
            title=SAARTHI_COURSE_TITLE,
            faculty_id=int(faculty.id),
        )
        db.add(course)
        db.flush()

    enrollment = None
    if student_id is not None:
        enrollment = (
            db.query(models.Enrollment)
            .filter(
                models.Enrollment.student_id == int(student_id),
                models.Enrollment.course_id == int(course.id),
            )
            .first()
        )
        if enrollment is None:
            enrollment = models.Enrollment(
                student_id=int(student_id),
                course_id=int(course.id),
                created_at=datetime.utcnow(),
            )
            db.add(enrollment)
            db.flush()

    return SaarthiBundle(faculty=faculty, course=course, enrollment=enrollment)


def _iter_mandatory_dates(academic_start: date, through_date: date) -> list[date]:
    if academic_start > through_date:
        return []
    start_week = saarthi_week_start(academic_start)
    end_week = saarthi_week_start(through_date)
    cursor = start_week
    out: list[date] = []
    while cursor <= end_week:
        mandatory_day = cursor + timedelta(days=SAARTHI_MANDATORY_WEEKDAY)
        if academic_start <= mandatory_day <= through_date:
            out.append(mandatory_day)
        cursor += timedelta(days=7)
    return out


def materialize_saarthi_attendance(
    db: Session,
    *,
    student_id: int,
    academic_start: date,
    today: date,
) -> SaarthiBundle:
    bundle = ensure_saarthi_bundle(db, student_id=int(student_id))
    student = db.get(models.Student, int(student_id))
    course_id = int(bundle.course.id)
    faculty_id = int(bundle.faculty.id)

    sessions = (
        db.query(models.SaarthiSession)
        .filter(
            models.SaarthiSession.student_id == int(student_id),
            models.SaarthiSession.course_id == course_id,
            models.SaarthiSession.mandatory_date >= academic_start,
            models.SaarthiSession.mandatory_date <= today,
        )
        .all()
    )
    credited_by_date = {
        session.mandatory_date: session
        for session in sessions
        if session.attendance_marked_at is not None
    }
    records = (
        db.query(models.AttendanceRecord)
        .filter(
            models.AttendanceRecord.student_id == int(student_id),
            models.AttendanceRecord.course_id == course_id,
            models.AttendanceRecord.attendance_date >= academic_start,
            models.AttendanceRecord.attendance_date <= today,
        )
        .all()
    )
    records_by_date = {row.attendance_date: row for row in records}

    for mandatory_day in _iter_mandatory_dates(academic_start, today):
        if mandatory_day == today and mandatory_day.weekday() == SAARTHI_MANDATORY_WEEKDAY:
            if mandatory_day not in credited_by_date and mandatory_day not in records_by_date:
                continue
        desired_status = (
            models.AttendanceStatus.PRESENT
            if mandatory_day in credited_by_date
            else models.AttendanceStatus.ABSENT
        )
        existing = records_by_date.get(mandatory_day)
        if existing is not None:
            source_value = str(existing.source or "").strip().lower()
            if desired_status == models.AttendanceStatus.ABSENT and source_value and not source_value.startswith("saarthi"):
                continue
            if existing.status == desired_status and source_value.startswith("saarthi"):
                continue

        event_key = (
            f"saarthi:{int(student_id)}:{mandatory_day.isoformat()}:"
            f"{'present' if desired_status == models.AttendanceStatus.PRESENT else 'absent'}"
        )
        note = (
            "Mandatory Saarthi counselling completed. Weekly 1-hour credit applied."
            if desired_status == models.AttendanceStatus.PRESENT
            else "Mandatory Saarthi counselling was missed for the weekly Sunday check-in."
        )
        _, record = append_event_and_recompute(
            db,
            student_id=int(student_id),
            course_id=course_id,
            attendance_date=mandatory_day,
            status=desired_status,
            source=(
                "saarthi-weekly-credit"
                if desired_status == models.AttendanceStatus.PRESENT
                else "saarthi-mandatory-missed"
            ),
            actor_faculty_id=faculty_id,
            actor_role=models.UserRole.FACULTY,
            note=note,
            event_key=event_key,
        )
        records_by_date[mandatory_day] = record
        if desired_status == models.AttendanceStatus.PRESENT:
            session = credited_by_date.get(mandatory_day)
            if session is not None and record is not None and session.attendance_record_id != int(record.id):
                session.attendance_record_id = int(record.id)
                session.updated_at = datetime.utcnow()
        elif existing is None and student is not None:
            week_start_date = saarthi_week_start(mandatory_day)
            session = (
                db.query(models.SaarthiSession)
                .filter(
                    models.SaarthiSession.student_id == int(student_id),
                    models.SaarthiSession.course_id == course_id,
                    models.SaarthiSession.week_start_date == week_start_date,
                )
                .first()
            )
            message_count = 0
            last_message_at = None
            if session is not None:
                message_count = (
                    db.query(models.SaarthiMessage.id)
                    .filter(models.SaarthiMessage.session_id == int(session.id))
                    .count()
                )
                last_message_at = session.last_message_at
            enqueue_saarthi_missed_notifications(
                db,
                student=student,
                mandatory_date=mandatory_day,
                week_start_date=week_start_date,
                message_count=message_count,
                last_message_at=last_message_at,
                after_commit=True,
            )

    db.flush()
    return bundle


def queue_saarthi_missed_notifications_for_reference(
    db: Session,
    *,
    reference_date: date,
) -> dict[str, object]:
    week_start_date, mandatory_date = saarthi_reporting_window(reference_date)
    bundle = ensure_saarthi_bundle(db)
    course_id = int(bundle.course.id)

    students = (
        db.query(models.Student)
        .order_by(models.Student.department.asc(), models.Student.registration_number.asc(), models.Student.id.asc())
        .all()
    )
    sessions = (
        db.query(models.SaarthiSession)
        .filter(
            models.SaarthiSession.course_id == course_id,
            models.SaarthiSession.week_start_date == week_start_date,
        )
        .all()
    )
    sessions_by_student = {int(row.student_id): row for row in sessions}
    session_ids = [int(row.id) for row in sessions]

    message_counts_by_session: dict[int, int] = {}
    last_message_by_session: dict[int, datetime] = {}
    if session_ids:
        for session_id, count_value, last_message_at in (
            db.query(
                models.SaarthiMessage.session_id,
                func.count(models.SaarthiMessage.id),
                func.max(models.SaarthiMessage.created_at),
            )
            .filter(models.SaarthiMessage.session_id.in_(session_ids))
            .group_by(models.SaarthiMessage.session_id)
            .all()
        ):
            message_counts_by_session[int(session_id)] = int(count_value or 0)
            if last_message_at is not None:
                last_message_by_session[int(session_id)] = last_message_at

    records = (
        db.query(models.AttendanceRecord)
        .filter(
            models.AttendanceRecord.course_id == course_id,
            models.AttendanceRecord.attendance_date == mandatory_date,
        )
        .all()
    )
    records_by_student = {int(row.student_id): row for row in records}

    missed_students = 0
    notified_students = 0
    enqueued_notifications = 0
    for student in students:
        session = sessions_by_student.get(int(student.id))
        record = records_by_student.get(int(student.id))
        completed = bool(
            (session is not None and session.attendance_marked_at is not None)
            or (record is not None and record.status == models.AttendanceStatus.PRESENT)
        )
        if completed or reference_date <= mandatory_date:
            continue
        missed_students += 1
        message_count = message_counts_by_session.get(int(session.id), 0) if session is not None else 0
        last_message_at = last_message_by_session.get(int(session.id)) if session is not None else None
        enqueued_now = enqueue_saarthi_missed_notifications(
            db,
            student=student,
            mandatory_date=mandatory_date,
            week_start_date=week_start_date,
            message_count=message_count,
            last_message_at=last_message_at,
            after_commit=False,
        )
        enqueued_notifications += enqueued_now
        if enqueued_now > 0:
            notified_students += 1

    return {
        "reference_date": reference_date.isoformat(),
        "week_start_date": week_start_date.isoformat(),
        "mandatory_date": mandatory_date.isoformat(),
        "students_scanned": len(students),
        "missed_students": missed_students,
        "notified_students": notified_students,
        "enqueued_notifications": enqueued_notifications,
    }


def get_or_create_saarthi_session(
    db: Session,
    *,
    student_id: int,
    current_dt: datetime,
) -> tuple[SaarthiBundle, models.SaarthiSession]:
    bundle = ensure_saarthi_bundle(db, student_id=int(student_id))
    week_start = saarthi_week_start(current_dt.date())
    mandatory_day = week_start + timedelta(days=SAARTHI_MANDATORY_WEEKDAY)
    session = (
        db.query(models.SaarthiSession)
        .filter(
            models.SaarthiSession.student_id == int(student_id),
            models.SaarthiSession.week_start_date == week_start,
        )
        .first()
    )
    if session is None:
        session = models.SaarthiSession(
            student_id=int(student_id),
            course_id=int(bundle.course.id),
            faculty_id=int(bundle.faculty.id),
            week_start_date=week_start,
            mandatory_date=mandatory_day,
            attendance_credit_minutes=0,
            created_at=current_dt,
            updated_at=current_dt,
            last_message_at=None,
        )
        db.add(session)
        db.flush()
    return bundle, session


def list_saarthi_messages(db: Session, *, session_id: int, limit: int = 80) -> list[models.SaarthiMessage]:
    rows = (
        db.query(models.SaarthiMessage)
        .filter(models.SaarthiMessage.session_id == int(session_id))
        .order_by(models.SaarthiMessage.created_at.asc(), models.SaarthiMessage.id.asc())
        .limit(max(1, int(limit)))
        .all()
    )
    return rows


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _saarthi_llm_provider() -> str:
    explicit = str(os.getenv("SAARTHI_LLM_PROVIDER") or "").strip().lower()
    if explicit:
        return explicit
    if _saarthi_gemini_api_keys():
        return "gemini"
    if _saarthi_openrouter_api_key():
        return "openrouter"
    return ""


def _saarthi_llm_required() -> bool:
    raw = (os.getenv("SAARTHI_LLM_REQUIRED", "false") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _saarthi_llm_model() -> str:
    provider = _saarthi_llm_provider()
    default = "google/gemini-2.5-flash" if provider == "openrouter" else "gemini-2.5-flash"
    return str(os.getenv("SAARTHI_LLM_MODEL") or default).strip() or default


def _saarthi_llm_timeout_seconds() -> float:
    raw = (os.getenv("SAARTHI_LLM_TIMEOUT_SECONDS", "20") or "").strip()
    try:
        value = float(raw)
    except ValueError:
        value = 20.0
    return max(5.0, min(60.0, value))


def _saarthi_gemini_api_key() -> str:
    return str(resolve_secret("GEMINI_API_KEY", default="") or "").strip()


def _parse_secret_list(raw: str) -> list[str]:
    cleaned = str(raw or "").strip()
    if not cleaned:
        return []
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    items: list[str] = []
    for line in cleaned.replace("\r", "\n").split("\n"):
        for part in line.split(","):
            token = str(part or "").strip()
            if token:
                items.append(token)
    return items


def _saarthi_gemini_api_keys() -> list[str]:
    configured = _parse_secret_list(str(resolve_secret("GEMINI_API_KEYS_JSON", default="") or ""))
    single = _saarthi_gemini_api_key()
    if single:
        configured.append(single)
    deduped: list[str] = []
    seen: set[str] = set()
    for token in configured:
        normalized = str(token or "").strip()
        if not normalized or normalized.startswith("sk-or-v1-") or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def _saarthi_openrouter_api_key() -> str:
    direct = str(resolve_secret("OPENROUTER_API_KEY", default="") or "").strip()
    if direct:
        return direct
    return ""


def _saarthi_gemini_base_url() -> str:
    raw = str(os.getenv("GEMINI_API_BASE_URL") or "https://generativelanguage.googleapis.com/v1beta").strip()
    return raw.rstrip("/")


def _saarthi_openrouter_base_url() -> str:
    raw = str(os.getenv("OPENROUTER_API_BASE_URL") or "https://openrouter.ai/api/v1").strip()
    return raw.rstrip("/")


def _saarthi_openrouter_site_url() -> str:
    return str(os.getenv("OPENROUTER_SITE_URL") or "").strip()


def _saarthi_openrouter_app_name() -> str:
    return str(os.getenv("OPENROUTER_APP_NAME") or "LPU Smart Campus Saarthi").strip()


def _build_saarthi_llm_prompt(
    *,
    student_name: str,
    recent_messages: list[models.SaarthiMessage],
    current_dt: datetime,
    mandatory_date: date,
    attendance_awarded_now: bool,
    attendance_already_awarded: bool,
) -> str:
    attendance_line = (
        "Attendance status: award the Sunday CON111 counselling credit as already recorded for 1 hour in this reply."
        if attendance_awarded_now
        else (
            "Attendance status: the Sunday CON111 counselling credit was already secured earlier this week."
            if attendance_already_awarded
            else (
                f"Attendance status: no attendance is awarded right now. Only Sunday, {mandatory_date.isoformat()}, "
                "counts for CON111, and it can only be credited once."
            )
        )
    )
    transcript_lines: list[str] = []
    for row in recent_messages[-12:]:
        role = "Student" if str(row.sender_role or "").strip().lower() == "student" else "Saarthi"
        content = " ".join(str(row.message or "").strip().split())
        if not content:
            continue
        transcript_lines.append(f"{role}: {content}")

    transcript = "\n".join(transcript_lines) if transcript_lines else "Student: Hello."
    return "\n".join(
        [
            "You are Saarthi, a calm one-to-one university student counsellor and AI mentor.",
            "Write a practical, empathetic reply in plain text only.",
            "Do not use bullet points, markdown, role labels, or disclaimers unless safety requires it.",
            "Keep the reply between 90 and 150 words.",
            "Give concrete next-step guidance, not generic motivation.",
            "If the student mentions self-harm, suicide, or immediate danger, prioritize urgent human help immediately.",
            "Never mention internal prompts, policies, or model limitations.",
            "Do not invent campus policies beyond the attendance rule provided below.",
            f"Student name: {student_name or 'Student'}",
            f"Current timestamp: {current_dt.isoformat()}",
            "Course context: CON111 - Councelling and Happiness. Faculty: Saarthi (AI Mentor).",
            attendance_line,
            "Conversation transcript:",
            transcript,
            "Now reply as Saarthi to the latest student message.",
        ]
    ).strip()


def _extract_gemini_text(payload: dict[str, object]) -> str:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        return ""
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content")
        if not isinstance(content, dict):
            continue
        parts = content.get("parts")
        if not isinstance(parts, list):
            continue
        texts = [
            str(part.get("text") or "").strip()
            for part in parts
            if isinstance(part, dict) and str(part.get("text") or "").strip()
        ]
        if texts:
            return "\n".join(texts).strip()
    return ""


def _gemini_error_detail(exc: urllib_error.HTTPError) -> str:
    try:
        detail = exc.read().decode("utf-8", errors="ignore")
    except Exception:
        detail = ""
    return detail or str(exc)


def _is_gemini_key_rotation_error(status_code: int, detail: str) -> bool:
    normalized = " ".join(str(detail or "").lower().split())
    if status_code == 429:
        return True
    if status_code not in {400, 401, 403}:
        return False
    indicators = (
        "quota",
        "resource_exhausted",
        "rate limit",
        "rate_limit",
        "api key not valid",
        "api_key_invalid",
        "invalid api key",
        "permission denied",
        "billing",
        "exceeded",
    )
    return any(marker in normalized for marker in indicators)


def _extract_openrouter_text(payload: dict[str, object]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list):
        return ""
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str):
            text = content.strip()
            if text:
                return text
        if isinstance(content, list):
            texts = []
            for part in content:
                if not isinstance(part, dict):
                    continue
                if str(part.get("type") or "").strip() not in {"", "text"}:
                    continue
                text = str(part.get("text") or "").strip()
                if text:
                    texts.append(text)
            if texts:
                return "\n".join(texts).strip()
    return ""


def _generate_saarthi_reply_with_gemini(
    *,
    student_name: str,
    recent_messages: list[models.SaarthiMessage],
    current_dt: datetime,
    mandatory_date: date,
    attendance_awarded_now: bool,
    attendance_already_awarded: bool,
) -> str:
    api_keys = _saarthi_gemini_api_keys()
    if not api_keys:
        raise RuntimeError("GEMINI_API_KEY or GEMINI_API_KEYS_JSON is required when SAARTHI_LLM_PROVIDER=gemini.")
    model = _saarthi_llm_model()
    prompt = _build_saarthi_llm_prompt(
        student_name=student_name,
        recent_messages=recent_messages,
        current_dt=current_dt,
        mandatory_date=mandatory_date,
        attendance_awarded_now=attendance_awarded_now,
        attendance_already_awarded=attendance_already_awarded,
    )
    body = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "topP": 0.9,
            "maxOutputTokens": 320,
        },
    }
    last_rotation_error = ""
    for api_key in api_keys:
        endpoint = (
            f"{_saarthi_gemini_base_url()}/models/{urllib_parse.quote(model, safe='')}:generateContent"
            f"?key={urllib_parse.quote(api_key, safe='')}"
        )
        request = urllib_request.Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib_request.urlopen(request, timeout=_saarthi_llm_timeout_seconds()) as response:
                raw_payload = response.read().decode("utf-8")
        except urllib_error.HTTPError as exc:
            detail = _gemini_error_detail(exc)
            if _is_gemini_key_rotation_error(exc.code, detail):
                last_rotation_error = f"HTTP {exc.code}: {detail}"
                continue
            raise RuntimeError(f"Saarthi Gemini request failed with HTTP {exc.code}: {detail}") from exc
        except urllib_error.URLError as exc:
            raise RuntimeError(f"Saarthi Gemini network error: {exc.reason}") from exc

        try:
            parsed = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Saarthi Gemini returned non-JSON output.") from exc

        reply = _extract_gemini_text(parsed)
        if not reply:
            raise RuntimeError("Saarthi Gemini returned an empty reply.")
        return reply.strip()

    if _saarthi_openrouter_api_key():
        try:
            return _generate_saarthi_reply_with_openrouter(
                student_name=student_name,
                recent_messages=recent_messages,
                current_dt=current_dt,
                mandatory_date=mandatory_date,
                attendance_awarded_now=attendance_awarded_now,
                attendance_already_awarded=attendance_already_awarded,
            )
        except Exception as exc:
            if last_rotation_error:
                raise RuntimeError(
                    "All configured Gemini API keys were exhausted or rejected, "
                    f"and OpenRouter fallback failed: {exc}"
                ) from exc
            raise

    if last_rotation_error:
        raise RuntimeError(f"All configured Gemini API keys were exhausted or rejected. Last error: {last_rotation_error}")
    raise RuntimeError("Saarthi Gemini could not generate a reply with the configured key pool.")


def _generate_saarthi_reply_with_openrouter(
    *,
    student_name: str,
    recent_messages: list[models.SaarthiMessage],
    current_dt: datetime,
    mandatory_date: date,
    attendance_awarded_now: bool,
    attendance_already_awarded: bool,
) -> str:
    api_key = _saarthi_openrouter_api_key()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required when SAARTHI_LLM_PROVIDER=openrouter.")

    model = _saarthi_llm_model()
    prompt = _build_saarthi_llm_prompt(
        student_name=student_name,
        recent_messages=recent_messages,
        current_dt=current_dt,
        mandatory_date=mandatory_date,
        attendance_awarded_now=attendance_awarded_now,
        attendance_already_awarded=attendance_already_awarded,
    )
    endpoint = f"{_saarthi_openrouter_base_url()}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Title": _saarthi_openrouter_app_name(),
    }
    site_url = _saarthi_openrouter_site_url()
    if site_url:
        headers["HTTP-Referer"] = site_url
    body = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 320,
    }
    request = urllib_request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib_request.urlopen(request, timeout=_saarthi_llm_timeout_seconds()) as response:
            raw_payload = response.read().decode("utf-8")
    except urllib_error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore") if hasattr(exc, "read") else str(exc)
        raise RuntimeError(f"Saarthi OpenRouter request failed with HTTP {exc.code}: {detail}") from exc
    except urllib_error.URLError as exc:
        raise RuntimeError(f"Saarthi OpenRouter network error: {exc.reason}") from exc

    try:
        parsed = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Saarthi OpenRouter returned non-JSON output.") from exc

    reply = _extract_openrouter_text(parsed)
    if not reply:
        raise RuntimeError("Saarthi OpenRouter returned an empty reply.")
    return reply.strip()


def _generate_saarthi_reply_deterministic(
    *,
    student_name: str,
    student_message: str,
    current_dt: datetime,
    mandatory_date: date,
    attendance_awarded_now: bool,
    attendance_already_awarded: bool,
) -> str:
    message = str(student_message or "").strip()
    normalized = message.lower()
    first_name = str(student_name or "there").strip().split(" ", 1)[0] or "there"

    if _contains_any(normalized, ("suicide", "kill myself", "self harm", "hurt myself", "end my life")):
        return (
            f"{first_name}, I am very concerned about your safety. Please contact a trusted person right now, "
            "reach your campus support team immediately, or call local emergency help if you may act on this. "
            "Stay with someone while you get real human support."
        )

    opening = f"{first_name}, thanks for opening up."
    guidance = (
        "Let us slow this down together. Tell me the main pressure point right now, what is under your control today, "
        "and what is the smallest next step you can take in the next hour."
    )
    if _contains_any(normalized, ("stress", "stressed", "anxious", "anxiety", "overwhelmed", "panic")):
        guidance = (
            "You sound overloaded. For the next 10 minutes, reduce the problem to three lines: what is urgent, "
            "what can wait, and who can help. Then pick only one task for the next hour."
        )
    elif _contains_any(normalized, ("exam", "tests", "assignment", "deadline", "study", "backlog")):
        guidance = (
            "Academic pressure feels heavier when everything looks equally urgent. Split today into one recovery block, "
            "one revision block, and one break. If you want, send me the subjects troubling you and I will help you order them."
        )
    elif _contains_any(normalized, ("sleep", "tired", "insomnia", "burnout", "burned out")):
        guidance = (
            "Your energy needs protecting first. Today, avoid stacking work into late night hours, drink water, "
            "take one short screen break, and aim for a fixed shutdown time before sleep."
        )
    elif _contains_any(normalized, ("lonely", "alone", "friend", "friends", "isolated", "homesick")):
        guidance = (
            "Feeling disconnected can quietly drain motivation. Try one low-pressure reach-out today: message one friend, "
            "join one familiar space, or sit with one safe group instead of staying isolated."
        )
    elif _contains_any(normalized, ("attendance", "shortage", "aggregate", "proxy", "missed class")):
        guidance = (
            "Let us keep this practical. Review the subjects pulling your aggregate down, protect upcoming classes first, "
            "and use remedial or recovery actions early instead of waiting for the shortage to grow."
        )
    elif _contains_any(normalized, ("family", "home", "parents", "financial", "money")):
        guidance = (
            "That is a real load to carry. Focus on what needs immediate action today, what can be discussed with a trusted adult, "
            "and what campus support or faculty flexibility may help you stabilize this week."
        )

    attendance_line = (
        "Your weekly CON111 counselling credit for this Sunday is now recorded as 1 hour."
        if attendance_awarded_now
        else (
            "Your weekly CON111 counselling credit for this Sunday is already secured."
            if attendance_already_awarded
            else (
                f"Attendance for CON111 is awarded only once on Sunday, {mandatory_date.isoformat()}, "
                "no matter how long you chat."
            )
        )
    )
    closing = (
        "Reply with how you are feeling in one word right now, or tell me the single issue you want to solve first."
    )
    return " ".join([opening, guidance, attendance_line, closing]).strip()


def generate_saarthi_reply(
    *,
    student_name: str,
    student_message: str,
    current_dt: datetime,
    mandatory_date: date,
    attendance_awarded_now: bool,
    attendance_already_awarded: bool,
    recent_messages: list[models.SaarthiMessage] | None = None,
) -> str:
    provider = _saarthi_llm_provider()
    recent_rows = list(recent_messages or [])
    if provider == "openrouter":
        try:
            return _generate_saarthi_reply_with_openrouter(
                student_name=student_name,
                recent_messages=recent_rows,
                current_dt=current_dt,
                mandatory_date=mandatory_date,
                attendance_awarded_now=attendance_awarded_now,
                attendance_already_awarded=attendance_already_awarded,
            )
        except Exception:
            if _saarthi_llm_required():
                raise
    elif provider == "gemini":
        try:
            return _generate_saarthi_reply_with_gemini(
                student_name=student_name,
                recent_messages=recent_rows,
                current_dt=current_dt,
                mandatory_date=mandatory_date,
                attendance_awarded_now=attendance_awarded_now,
                attendance_already_awarded=attendance_already_awarded,
            )
        except Exception:
            if _saarthi_llm_required():
                raise
    elif provider and _saarthi_llm_required():
        raise RuntimeError(f"Unsupported Saarthi LLM provider: {provider}")

    return _generate_saarthi_reply_deterministic(
        student_name=student_name,
        student_message=student_message,
        current_dt=current_dt,
        mandatory_date=mandatory_date,
        attendance_awarded_now=attendance_awarded_now,
        attendance_already_awarded=attendance_already_awarded,
    )


def create_saarthi_turn(
    db: Session,
    *,
    student: models.Student,
    message: str,
    current_dt: datetime,
    academic_start: date,
) -> dict[str, object]:
    cleaned_message = str(message or "").strip()
    if not cleaned_message:
        raise ValueError("Message cannot be empty.")

    bundle = materialize_saarthi_attendance(
        db,
        student_id=int(student.id),
        academic_start=academic_start,
        today=current_dt.date(),
    )
    _, session = get_or_create_saarthi_session(
        db,
        student_id=int(student.id),
        current_dt=current_dt,
    )
    attendance_already_awarded = bool(session.attendance_marked_at is not None)
    attendance_awarded_now = False

    user_row = models.SaarthiMessage(
        session_id=int(session.id),
        sender_role="student",
        message=cleaned_message,
        created_at=current_dt,
    )
    db.add(user_row)
    session.last_message_at = current_dt
    session.updated_at = current_dt

    if current_dt.date() == session.mandatory_date and not attendance_already_awarded:
        _, record = append_event_and_recompute(
            db,
            student_id=int(student.id),
            course_id=int(bundle.course.id),
            attendance_date=session.mandatory_date,
            status=models.AttendanceStatus.PRESENT,
            source="saarthi-weekly-credit",
            actor_faculty_id=int(bundle.faculty.id),
            actor_role=models.UserRole.FACULTY,
            note="Mandatory Saarthi counselling completed. Weekly 1-hour credit applied.",
            event_key=f"saarthi:{int(student.id)}:{session.mandatory_date.isoformat()}:present",
        )
        session.attendance_credit_minutes = SAARTHI_ATTENDANCE_MINUTES
        session.attendance_marked_at = current_dt
        session.attendance_record_id = int(record.id) if record is not None else None
        session.updated_at = current_dt
        attendance_awarded_now = True
        attendance_already_awarded = True

    db.flush()
    recent_messages = list_saarthi_messages(db, session_id=int(session.id), limit=12)
    reply = generate_saarthi_reply(
        student_name=str(student.name or "").strip(),
        student_message=cleaned_message,
        current_dt=current_dt,
        mandatory_date=session.mandatory_date,
        attendance_awarded_now=attendance_awarded_now,
        attendance_already_awarded=attendance_already_awarded,
        recent_messages=recent_messages,
    )
    assistant_row = models.SaarthiMessage(
        session_id=int(session.id),
        sender_role="assistant",
        message=reply,
        created_at=current_dt,
    )
    db.add(assistant_row)
    session.last_message_at = current_dt
    session.updated_at = current_dt
    db.flush()

    return {
        "bundle": bundle,
        "session": session,
        "reply": reply,
        "attendance_awarded_now": attendance_awarded_now,
    }
