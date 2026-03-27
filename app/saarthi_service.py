from __future__ import annotations

import json
import os
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from sqlalchemy.orm import Session

from . import models
from .attendance_ledger import append_event_and_recompute
from .enterprise_controls import resolve_secret

SAARTHI_COURSE_CODE = "CON111"
SAARTHI_COURSE_TITLE = "Counselling and Happiness"
SAARTHI_FACULTY_NAME = "Saarthi (AI Mentor)"
SAARTHI_FACULTY_EMAIL = "saarthi.ai.mentor@lpu.local"
SAARTHI_FACULTY_IDENTIFIER = "SAARTHI-AI-MENTOR"
SAARTHI_MANDATORY_WEEKDAY = 6  # Sunday
SAARTHI_ATTENDANCE_MINUTES = 60
SAARTHI_IDENTITY_INTRO = "Hi, I'm Saarthi. I'm here to listen and support you. You can share anything that's on your mind."
SAARTHI_LLM_TEMPERATURE = 0.7
SAARTHI_LLM_TOP_P = 0.9
SAARTHI_LLM_PRESENCE_PENALTY = 0.6
SAARTHI_LLM_FREQUENCY_PENALTY = 0.3


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class SaarthiBundle:
    faculty: models.Faculty
    course: models.Course
    enrollment: models.Enrollment | None


def saarthi_week_start(target_date: date) -> date:
    return target_date - timedelta(days=target_date.weekday())


def saarthi_mandatory_date(target_date: date) -> date:
    return saarthi_week_start(target_date) + timedelta(days=SAARTHI_MANDATORY_WEEKDAY)


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
            created_at=_utcnow_naive(),
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
                created_at=_utcnow_naive(),
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
        if desired_status == models.AttendanceStatus.PRESENT:
            session = credited_by_date.get(mandatory_day)
            if session is not None and record is not None and session.attendance_record_id != int(record.id):
                session.attendance_record_id = int(record.id)
                session.updated_at = _utcnow_naive()

    db.flush()
    return bundle


def should_materialize_saarthi_attendance(
    db: Session,
    *,
    student_id: int,
    academic_start: date,
    today: date,
) -> bool:
    course_row = (
        db.query(models.Course.id)
        .filter(models.Course.code == SAARTHI_COURSE_CODE)
        .first()
    )
    if course_row is None:
        return False

    course_id = int(course_row[0])
    has_enrollment = (
        db.query(models.Enrollment.id)
        .filter(
            models.Enrollment.student_id == int(student_id),
            models.Enrollment.course_id == course_id,
        )
        .first()
        is not None
    )
    if has_enrollment:
        return True

    has_sessions = (
        db.query(models.SaarthiSession.id)
        .filter(
            models.SaarthiSession.student_id == int(student_id),
            models.SaarthiSession.mandatory_date >= academic_start,
            models.SaarthiSession.mandatory_date <= today,
        )
        .first()
        is not None
    )
    if has_sessions:
        return True

    has_saarthi_records = (
        db.query(models.AttendanceRecord.id)
        .filter(
            models.AttendanceRecord.student_id == int(student_id),
            models.AttendanceRecord.course_id == course_id,
            models.AttendanceRecord.attendance_date >= academic_start,
            models.AttendanceRecord.attendance_date <= today,
        )
        .first()
        is not None
    )
    return has_saarthi_records


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
        .order_by(models.SaarthiMessage.created_at.desc(), models.SaarthiMessage.id.desc())
        .limit(max(1, int(limit)))
        .all()
    )
    rows.reverse()
    return rows


def count_saarthi_messages(db: Session, *, session_id: int) -> int:
    return int(
        db.query(models.SaarthiMessage.id)
        .filter(models.SaarthiMessage.session_id == int(session_id))
        .count()
    )


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _normalize_saarthi_text(value: str | None) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _format_student_first_name(student_name: str | None) -> str:
    first = str(student_name or "").strip().split(" ", 1)[0].strip()
    if not first:
        return "there"
    if first.islower() or first.isupper():
        return first.capitalize()
    return first


def _student_indicates_topic_shift(normalized_message: str) -> bool:
    return _contains_any(
        normalized_message,
        (
            "something else",
            "something different",
            "not that",
            "not this",
            "another thing",
            "another issue",
            "other thing",
            "other issue",
        ),
    )


def _student_reports_improvement(normalized_message: str) -> bool:
    return _contains_any(
        normalized_message,
        (
            "feeling better",
            "feel better",
            "better now",
            "doing better",
            "im better",
            "i'm better",
            "i am better",
            "im okay",
            "i'm okay",
            "i am okay",
            "im good",
            "i'm good",
            "i am good",
            "im fine",
            "i'm fine",
            "i am fine",
            "a bit better",
            "getting better",
            "improved",
            "improvement",
        ),
    )


def _is_short_student_message(normalized_message: str, *, max_tokens: int = 4) -> bool:
    return len(normalized_message.split()) <= max_tokens


def _recent_student_topics(
    *,
    recent_messages: list[models.SaarthiMessage] | None = None,
) -> list[str]:
    return _detect_saarthi_support_topics("", recent_messages or [])


def _topic_label(topic: str) -> str:
    labels = {
        "study_focus": "academics",
        "anxiety_regulation": "anxiety",
        "sleep_recovery": "sleep",
        "burnout_recovery": "burnout",
        "mood_support": "how you’ve been feeling",
        "career_clarity": "career direction",
        "social_pressure": "comparison pressure",
    }
    return labels.get(topic, "")


def _should_ask_follow_up(
    student_message: str,
    *,
    recent_messages: list[models.SaarthiMessage] | None = None,
    first_turn: bool = False,
) -> bool:
    normalized = _normalize_saarthi_text(student_message)
    if not normalized:
        return False
    if _student_indicates_topic_shift(normalized):
        return True
    if "?" in str(student_message or ""):
        return False
    tokens = normalized.split()
    if len(tokens) <= 6:
        return True
    if _contains_any(
        normalized,
        (
            "not sure",
            "don't know",
            "dont know",
            "idk",
            "confused",
            "unclear",
            "unsure",
        ),
    ):
        return True
    if _contains_any(
        normalized,
        (
            "cannot focus",
            "can't focus",
            "cant focus",
            "unable to focus",
            "not able to focus",
            "hard to focus",
            "struggling to focus",
            "struggle to focus",
            "cannot concentrate",
            "can't concentrate",
            "cant concentrate",
            "unable to concentrate",
            "hard to concentrate",
        ),
    ):
        return True
    if _contains_any(
        normalized,
        (
            "thanks",
            "thank you",
            "ok",
            "okay",
            "got it",
            "that helps",
            "cool",
            "understood",
        ),
    ):
        return False
    return False


def _recent_assistant_text(
    recent_messages: list[models.SaarthiMessage] | None = None,
    *,
    limit: int = 3,
) -> str:
    recent: list[str] = []
    for row in reversed(list(recent_messages or [])):
        if str(getattr(row, "sender_role", "") or "").strip().lower() != "assistant":
            continue
        cleaned = " ".join(str(getattr(row, "message", "") or "").strip().lower().split())
        if cleaned:
            recent.append(cleaned)
        if len(recent) >= limit:
            break
    return " ".join(recent)


def _dedup_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in values:
        cleaned = str(item or "").strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        out.append(cleaned)
    return out


def _ordered_secret_pool(
    *,
    keyring_secret_name: str,
    active_secret_name: str,
) -> list[str]:
    ordered: list[str] = []
    keyring_raw = str(resolve_secret(keyring_secret_name, default="") or "").strip()
    active_key_id = str(resolve_secret(active_secret_name, default="") or "").strip()
    if not keyring_raw:
        return ordered
    try:
        parsed = json.loads(keyring_raw)
    except json.JSONDecodeError:
        return ordered
    if isinstance(parsed, dict):
        if active_key_id:
            active_value = str(parsed.get(active_key_id) or "").strip()
            if active_value:
                ordered.append(active_value)
        ordered.extend(str(value or "").strip() for value in parsed.values())
    elif isinstance(parsed, list):
        ordered.extend(str(value or "").strip() for value in parsed)
    elif isinstance(parsed, str):
        ordered.append(parsed.strip())
    return _dedup_preserve_order(ordered)


def _collect_indexed_keys(prefix: str) -> list[str]:
    indexed_keys: list[tuple[int, str]] = []
    for env_key, env_value in os.environ.items():
        if not env_key.startswith(prefix):
            continue
        suffix = env_key.split(prefix, 1)[1]
        try:
            index = int(suffix)
        except ValueError:
            continue
        cleaned = str(env_value or "").strip()
        if cleaned:
            indexed_keys.append((index, cleaned))
    return [value for _, value in sorted(indexed_keys, key=lambda item: item[0])]


def _partition_shared_pool(values: list[str], *, pick_even_indexes: bool) -> list[str]:
    return [
        value
        for index, value in enumerate(values)
        if ((index % 2) == 0) == bool(pick_even_indexes)
    ]


def _shared_gemini_api_keys() -> list[str]:
    collected: list[str] = []
    collected.extend(
        _ordered_secret_pool(
            keyring_secret_name="GEMINI_API_KEYRING_JSON",
            active_secret_name="GEMINI_ACTIVE_KEY_ID",
        )
    )

    json_blob = str(resolve_secret("GEMINI_API_KEYS_JSON", default="") or "").strip()
    if json_blob:
        try:
            parsed = json.loads(json_blob)
            if isinstance(parsed, list):
                collected.extend(str(item or "").strip() for item in parsed)
            elif isinstance(parsed, str):
                collected.append(parsed.strip())
        except json.JSONDecodeError:
            pass

    csv_blob = str(resolve_secret("GEMINI_API_KEYS", default="") or "").strip()
    if csv_blob:
        collected.extend(part.strip() for part in csv_blob.split(","))

    single_key = str(resolve_secret("GEMINI_API_KEY", default="") or "").strip()
    if single_key:
        collected.append(single_key)

    collected.extend(_collect_indexed_keys("GEMINI_API_KEY_"))
    return _dedup_preserve_order(collected)


def _saarthi_dedicated_gemini_api_keys() -> list[str]:
    collected: list[str] = []
    collected.extend(
        _ordered_secret_pool(
            keyring_secret_name="SAARTHI_GEMINI_API_KEYRING_JSON",
            active_secret_name="SAARTHI_GEMINI_ACTIVE_KEY_ID",
        )
    )

    json_blob = str(resolve_secret("SAARTHI_GEMINI_API_KEYS_JSON", default="") or "").strip()
    if json_blob:
        try:
            parsed = json.loads(json_blob)
            if isinstance(parsed, list):
                collected.extend(str(item or "").strip() for item in parsed)
            elif isinstance(parsed, str):
                collected.append(parsed.strip())
        except json.JSONDecodeError:
            pass

    csv_blob = str(resolve_secret("SAARTHI_GEMINI_API_KEYS", default="") or "").strip()
    if csv_blob:
        collected.extend(part.strip() for part in csv_blob.split(","))

    single_key = str(resolve_secret("SAARTHI_GEMINI_API_KEY", default="") or "").strip()
    if single_key:
        collected.append(single_key)

    collected.extend(_collect_indexed_keys("SAARTHI_GEMINI_API_KEY_"))
    return _dedup_preserve_order(collected)


def _saarthi_gemini_api_keys() -> list[str]:
    dedicated = _saarthi_dedicated_gemini_api_keys()
    if dedicated:
        return dedicated
    shared = _shared_gemini_api_keys()
    return _dedup_preserve_order(_partition_shared_pool(shared, pick_even_indexes=True))


def _saarthi_llm_provider() -> str:
    explicit = str(os.getenv("SAARTHI_LLM_PROVIDER") or "").strip().lower()
    if explicit:
        return explicit
    if _saarthi_gemini_api_keys():
        return "gemini"
    if _saarthi_openrouter_api_keys():
        return "openrouter"
    return ""


def _saarthi_llm_required() -> bool:
    raw = (os.getenv("SAARTHI_LLM_REQUIRED", "false") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _saarthi_llm_model() -> str:
    return str(os.getenv("SAARTHI_LLM_MODEL") or "gemini-2.5-flash").strip() or "gemini-2.5-flash"


def _saarthi_openrouter_model() -> str:
    explicit = str(os.getenv("SAARTHI_OPENROUTER_MODEL") or "").strip()
    if explicit:
        return explicit
    shared_model = _saarthi_llm_model()
    normalized = shared_model.strip()
    if not normalized:
        return "google/gemini-2.5-flash"
    if "/" in normalized:
        return normalized
    # OpenRouter expects provider-prefixed model ids (for example: google/gemini-2.5-flash).
    if normalized.lower().startswith("gemini-"):
        return f"google/{normalized}"
    return normalized


def _saarthi_llm_timeout_seconds() -> float:
    raw = (os.getenv("SAARTHI_LLM_TIMEOUT_SECONDS", "20") or "").strip()
    try:
        value = float(raw)
    except ValueError:
        value = 20.0
    return max(5.0, min(60.0, value))


def _saarthi_gemini_base_url() -> str:
    raw = str(
        resolve_secret("GEMINI_API_BASE_URL", default="https://generativelanguage.googleapis.com/v1beta")
        or "https://generativelanguage.googleapis.com/v1beta"
    ).strip()
    return raw.rstrip("/")


def _shared_openrouter_api_keys() -> list[str]:
    collected: list[str] = []
    collected.extend(
        _ordered_secret_pool(
            keyring_secret_name="OPENROUTER_API_KEYRING_JSON",
            active_secret_name="OPENROUTER_ACTIVE_KEY_ID",
        )
    )

    json_blob = str(resolve_secret("OPENROUTER_API_KEYS_JSON", default="") or "").strip()
    if json_blob:
        try:
            parsed = json.loads(json_blob)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            collected.extend(str(item or "").strip() for item in parsed)
        elif isinstance(parsed, str):
            collected.append(parsed.strip())

    csv_blob = str(resolve_secret("OPENROUTER_API_KEYS", default="") or "").strip()
    if csv_blob:
        collected.extend(part.strip() for part in csv_blob.split(","))

    single = str(resolve_secret("OPENROUTER_API_KEY", default="") or "").strip()
    if single:
        collected.append(single)
    return _dedup_preserve_order(collected)


def _saarthi_dedicated_openrouter_api_keys() -> list[str]:
    collected: list[str] = []
    collected.extend(
        _ordered_secret_pool(
            keyring_secret_name="SAARTHI_OPENROUTER_API_KEYRING_JSON",
            active_secret_name="SAARTHI_OPENROUTER_ACTIVE_KEY_ID",
        )
    )

    json_blob = str(resolve_secret("SAARTHI_OPENROUTER_API_KEYS_JSON", default="") or "").strip()
    if json_blob:
        try:
            parsed = json.loads(json_blob)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            collected.extend(str(item or "").strip() for item in parsed)
        elif isinstance(parsed, str):
            collected.append(parsed.strip())

    csv_blob = str(resolve_secret("SAARTHI_OPENROUTER_API_KEYS", default="") or "").strip()
    if csv_blob:
        collected.extend(part.strip() for part in csv_blob.split(","))

    single = str(resolve_secret("SAARTHI_OPENROUTER_API_KEY", default="") or "").strip()
    if single:
        collected.append(single)
    return _dedup_preserve_order(collected)


def _saarthi_openrouter_api_keys() -> list[str]:
    dedicated = _saarthi_dedicated_openrouter_api_keys()
    if dedicated:
        return dedicated
    shared = _shared_openrouter_api_keys()
    return _dedup_preserve_order(_partition_shared_pool(shared, pick_even_indexes=True))


def _saarthi_openrouter_api_key() -> str:
    keys = _saarthi_openrouter_api_keys()
    if not keys:
        return ""
    return keys[0]


def _saarthi_openrouter_base_url() -> str:
    raw = str(resolve_secret("OPENROUTER_API_BASE_URL", default="https://openrouter.ai/api/v1") or "https://openrouter.ai/api/v1").strip()
    return raw.rstrip("/")


def _saarthi_openrouter_site_url() -> str:
    return str(resolve_secret("OPENROUTER_SITE_URL", default="") or "").strip()


def _saarthi_openrouter_app_name() -> str:
    return str(resolve_secret("OPENROUTER_APP_NAME", default="LPU Smart Campus Saarthi") or "LPU Smart Campus Saarthi").strip()


def _detect_saarthi_emotion(
    student_message: str,
    recent_messages: list[models.SaarthiMessage] | None = None,
) -> str:
    latest_normalized = _normalize_saarthi_text(student_message)
    snippets = [latest_normalized]
    for row in (recent_messages or [])[-4:]:
        if str(row.sender_role or "").strip().lower() != "student":
            continue
        snippets.append(_normalize_saarthi_text(str(row.message or "")))
    combined = " ".join(part for part in snippets if part).strip()
    if not combined:
        return "curiosity"

    buckets: tuple[tuple[str, tuple[str, ...]], ...] = (
        (
            "stress",
            (
                "stress",
                "stressed",
                "overwhelmed",
                "overload",
                "pressure",
                "deadline",
                "academic",
                "academics",
                "study",
                "studying",
                "exam",
                "tests",
                "grade",
                "grades",
                "gpa",
                "cgpa",
                "too much",
                "can't focus",
                "cannot focus",
                "burnout",
            ),
        ),
        (
            "anxiety",
            (
                "anxiety",
                "anxious",
                "panic",
                "panic attack",
                "worried",
                "worry",
                "fear",
                "scared",
                "nervous",
                "restless",
            ),
        ),
        (
            "confusion",
            (
                "confused",
                "confusing",
                "unclear",
                "don't know",
                "dont know",
                "unsure",
                "uncertain",
                "lost",
                "stuck",
                "which path",
                "career",
            ),
        ),
        (
            "sadness",
            (
                "sad",
                "depress",
                "depressed",
                "depression",
                "low",
                "down",
                "lonely",
                "alone",
                "cry",
                "crying",
                "hurt",
                "hopeless",
                "empty",
                "heartbroken",
                "breakup",
            ),
        ),
        (
            "frustration",
            (
                "frustrated",
                "frustrating",
                "angry",
                "annoyed",
                "fed up",
                "irritated",
                "sick of",
                "tired of",
                "unfair",
            ),
        ),
        (
            "motivation_loss",
            (
                "no motivation",
                "motivation",
                "demotivated",
                "unmotivated",
                "procrast",
                "can't start",
                "cannot start",
                "lazy",
                "drained",
                "exhausted",
            ),
        ),
        (
            "curiosity",
            (
                "how",
                "what",
                "why",
                "tips",
                "advice",
                "can you help",
                "should i",
                "curious",
            ),
        ),
    )
    def _score(text: str) -> dict[str, int]:
        return {
            emotion: sum(1 for keyword in keywords if keyword in text)
            for emotion, keywords in buckets
        }

    latest_scores = _score(latest_normalized)
    latest_ranked = sorted(latest_scores.items(), key=lambda item: item[1], reverse=True)
    if latest_ranked and latest_ranked[0][1] > 0:
        return latest_ranked[0][0]

    scores = _score(combined)
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    if ranked and ranked[0][1] > 0:
        return ranked[0][0]
    if "?" in student_message:
        return "curiosity"
    return "curiosity"


def _saarthi_tone_guidance(emotion: str) -> str:
    guidance = {
        "stress": "Respond extra gently and help the student make the problem feel smaller and manageable.",
        "anxiety": "Stay calming and steady, reduce uncertainty, and suggest grounding or low-pressure next steps.",
        "confusion": "Bring clarity without sounding forceful, and help the student sort thoughts into smaller decisions.",
        "sadness": "Be especially warm and reassuring, and avoid sounding rushed or solution-heavy.",
        "frustration": "Stay calm, non-judgmental, and help turn the feeling into one useful next step.",
        "motivation_loss": "Be encouraging without shaming, and suggest tiny actions that feel possible right now.",
        "curiosity": "Stay warm and clear, answer simply, and still end by inviting reflection.",
    }
    return guidance.get(emotion, "Stay warm, thoughtful, and emotionally present before moving into advice.")


def _saarthi_follow_up_question(emotion: str) -> str:
    return _saarthi_follow_up_question_variant(emotion, recent_messages=None)


def _extract_tail_question(text: str) -> str:
    cleaned = str(text or "").strip()
    if "?" not in cleaned:
        return ""
    q_idx = cleaned.rfind("?")
    if q_idx < 0:
        return ""
    boundary = max(
        cleaned.rfind(".", 0, q_idx),
        cleaned.rfind("!", 0, q_idx),
        cleaned.rfind("?", 0, max(0, q_idx - 1)),
    )
    question = cleaned[boundary + 1 : q_idx + 1].strip() if boundary >= 0 else cleaned[: q_idx + 1].strip()
    return " ".join(question.split()).lower()


def _saarthi_follow_up_question_variant(
    emotion: str,
    *,
    recent_messages: list[models.SaarthiMessage] | None = None,
) -> str:
    bank = {
        "stress": [
            "What part of this feels heaviest right now?",
            "Which task is creating the most pressure at this moment?",
            "If we made this 10% lighter today, what would change first?",
        ],
        "anxiety": [
            "What thought keeps pulling your mind back the most?",
            "When this anxious feeling spikes, what are you usually thinking about?",
            "What feels most uncertain to you right now?",
        ],
        "confusion": [
            "Which part of this feels the most unclear to you right now?",
            "If you had to choose one piece to understand first, what would it be?",
            "What decision feels the hardest to make at this stage?",
        ],
        "sadness": [
            "What has been hurting the most lately?",
            "When did you start feeling this heaviness more strongly?",
            "What kind of support would feel most comforting right now?",
        ],
        "frustration": [
            "What part of this situation feels the most draining?",
            "What keeps repeating that makes this so frustrating for you?",
            "What small boundary could make this feel less exhausting?",
        ],
        "motivation_loss": [
            "What usually makes it hardest for you to begin?",
            "At what time of day do you feel even slightly more focused?",
            "What is one tiny step that feels realistic right now?",
        ],
        "curiosity": [
            "What part would you like to explore more deeply?",
            "What outcome are you hoping for if this improves?",
            "Which area should we break down first together?",
        ],
    }
    options = list(bank.get(emotion) or ["What part of this would help to talk through next?"])
    if len(options) == 1:
        return options[0]

    last_assistant_question = ""
    for row in reversed(list(recent_messages or [])):
        if str(row.sender_role or "").strip().lower() != "assistant":
            continue
        last_assistant_question = _extract_tail_question(str(row.message or ""))
        if last_assistant_question:
            break
    for candidate in options:
        if _extract_tail_question(candidate) != last_assistant_question:
            return candidate
    return options[0]


def _saarthi_is_first_turn(recent_messages: list[models.SaarthiMessage] | None = None) -> bool:
    for row in recent_messages or []:
        if str(row.sender_role or "").strip().lower() == "assistant":
            return False
    return True


def _saarthi_attendance_context_line(
    *,
    student_message: str,
    student_name: str,
    recent_messages: list[models.SaarthiMessage],
    current_dt: datetime,
    mandatory_date: date,
    attendance_awarded_now: bool,
    attendance_already_awarded: bool,
) -> str:
    normalized = _normalize_saarthi_text(student_message)
    mentions_attendance = _contains_any(
        normalized,
        (
            "attendance",
            "aggregate",
            "con111",
            "sunday",
            "credit",
            "shortage",
            "missed class",
            "proxy",
        ),
    )
    if attendance_awarded_now:
        return "Attendance context: this week's Sunday CON111 counselling credit was awarded just now. Acknowledge it briefly once, then continue support."
    if attendance_already_awarded and mentions_attendance:
        return "Attendance context: this week's Sunday CON111 credit is already secured. Clarify it briefly if needed."
    if current_dt.date() == mandatory_date or mentions_attendance:
        return (
            f"Attendance context: only Sunday, {mandatory_date.isoformat()}, counts for the weekly CON111 credit, "
            "and it is credited only once regardless of chat duration."
        )
    return "Attendance context: do not mention attendance unless the student asks or it changed this turn."


def _detect_saarthi_support_topics(
    student_message: str,
    recent_messages: list[models.SaarthiMessage] | None = None,
) -> list[str]:
    snippets = [_normalize_saarthi_text(student_message)]
    for row in (recent_messages or [])[-5:]:
        if str(row.sender_role or "").strip().lower() != "student":
            continue
        snippets.append(_normalize_saarthi_text(str(row.message or "")))
    combined = " ".join(part for part in snippets if part).strip()
    if not combined:
        return []

    topic_keywords: tuple[tuple[str, tuple[str, ...]], ...] = (
        (
            "study_focus",
            (
                "focus",
                "concentrate",
                "exam",
                "study",
                "academics",
                "academic",
                "grades",
                "grade",
                "gpa",
                "cgpa",
                "deadline",
                "syllabus",
                "assignment",
                "backlog",
                "procrast",
            ),
        ),
        (
            "anxiety_regulation",
            (
                "anxiety",
                "panic",
                "nervous",
                "overthinking",
                "worry",
                "worried",
                "restless",
                "fear",
            ),
        ),
        (
            "sleep_recovery",
            (
                "sleep",
                "insomnia",
                "late night",
                "awake",
                "can't sleep",
                "cannot sleep",
                "sleep cycle",
            ),
        ),
        (
            "burnout_recovery",
            (
                "burnout",
                "drained",
                "exhausted",
                "too tired",
                "no energy",
                "fatigue",
                "overwhelmed",
            ),
        ),
        (
            "mood_support",
            (
                "sad",
                "depress",
                "depressed",
                "depression",
                "low",
                "lonely",
                "alone",
                "empty",
                "hopeless",
                "down",
            ),
        ),
        (
            "career_clarity",
            (
                "career",
                "placement",
                "job",
                "internship",
                "future",
                "path",
                "stream",
                "branch",
            ),
        ),
        (
            "social_pressure",
            (
                "comparison",
                "compare",
                "left behind",
                "falling behind",
                "family pressure",
                "parent pressure",
                "peer pressure",
            ),
        ),
    )
    scored: list[tuple[str, int]] = []
    for topic, keywords in topic_keywords:
        score = sum(1 for keyword in keywords if keyword in combined)
        if score > 0:
            scored.append((topic, score))
    scored.sort(key=lambda item: item[1], reverse=True)
    return [topic for topic, _ in scored[:2]]


def _student_requested_research_backing(
    student_message: str,
    recent_messages: list[models.SaarthiMessage] | None = None,
) -> bool:
    snippets = [_normalize_saarthi_text(student_message)]
    for row in (recent_messages or [])[-2:]:
        if str(row.sender_role or "").strip().lower() != "student":
            continue
        snippets.append(_normalize_saarthi_text(str(row.message or "")))
    combined = " ".join(part for part in snippets if part).strip()
    return _contains_any(
        combined,
        (
            "research",
            "scientific",
            "science based",
            "evidence",
            "proven",
            "real world",
            "real-world",
            "data backed",
        ),
    )


def _saarthi_research_options_by_topic(topic: str) -> list[str]:
    library = {
        "study_focus": [
            "A research-backed approach for study stress is short time-boxed focus cycles with breaks, which often improves consistency when tasks feel too big.",
            "Another evidence-based method is retrieval practice with spaced revision, where you test yourself across smaller sessions instead of long cramming blocks.",
        ],
        "anxiety_regulation": [
            "A well-supported strategy for anxiety spikes is slow diaphragmatic breathing for a few minutes before you restart work.",
            "A CBT-style thought reframe can also help: write the fear, then write one more balanced thought based on facts, not just pressure.",
        ],
        "sleep_recovery": [
            "Sleep research often supports fixed sleep and wake windows, with reduced late-night screen stimulation, to stabilize mood and concentration.",
            "A simple evidence-backed step is winding down with low-light and no heavy study right before bed, then studying earlier in the day.",
        ],
        "burnout_recovery": [
            "Burnout recovery is usually stronger with recovery blocks, not nonstop effort, so alternating deep work with deliberate rest can protect performance.",
            "Behavioral activation research also supports starting with very small achievable tasks to rebuild momentum when energy is low.",
        ],
        "mood_support": [
            "For low mood, evidence-based approaches often include regular routine, movement, and talking to trusted people instead of isolating.",
            "Journaling one difficult thought and one realistic coping action can reduce emotional load and improve clarity over time.",
        ],
        "career_clarity": [
            "Career decision research often works best with small experiments, such as one project, one informational conversation, and one skill sprint before big decisions.",
            "A practical evidence-backed approach is values plus data: list what matters to you, then compare options against real exposure and outcomes.",
        ],
        "social_pressure": [
            "Comparison stress is often reduced by self-referenced goals, where you track your own weekly progress instead of others’ timelines.",
            "Setting one boundary around social comparison triggers and replacing it with one action step is a behaviorally grounded coping pattern.",
        ],
    }
    return list(library.get(topic) or [])


def _saarthi_research_source_by_topic(topic: str) -> str:
    source_map = {
        "study_focus": "Learning-science findings on spaced practice and retrieval learning.",
        "anxiety_regulation": "Cognitive behavioral therapy and breathing regulation approaches used in mainstream mental health practice.",
        "sleep_recovery": "Sleep hygiene guidance used in student wellness and behavioral sleep programs.",
        "burnout_recovery": "Behavioral activation and workload-recovery balance recommendations from wellbeing research.",
        "mood_support": "Behavioral activation and social support findings in student mental health literature.",
        "career_clarity": "Career development research on exploration, values mapping, and iterative decision-making.",
        "social_pressure": "Self-comparison and self-regulation research in educational psychology.",
    }
    return source_map.get(topic, "")


def _saarthi_research_prompt_context_lines(
    student_message: str,
    recent_messages: list[models.SaarthiMessage] | None = None,
) -> list[str]:
    topics = _detect_saarthi_support_topics(student_message, recent_messages)
    if not topics:
        return []
    lines: list[str] = [
        "Use practical, evidence-informed suggestions that fit the detected concern and keep them small and non-commanding."
    ]
    for topic in topics[:2]:
        options = _saarthi_research_options_by_topic(topic)
        if options:
            lines.append(f"Evidence-backed option ({topic}): {options[0]}")
        source_note = _saarthi_research_source_by_topic(topic)
        if source_note:
            lines.append(f"Grounding note ({topic}): {source_note}")
    return lines


_SAARTHI_MEMORY_STOPWORDS = {
    "about",
    "again",
    "also",
    "always",
    "and",
    "because",
    "been",
    "before",
    "being",
    "between",
    "could",
    "didn't",
    "doesn't",
    "don't",
    "from",
    "have",
    "haven't",
    "just",
    "like",
    "maybe",
    "much",
    "need",
    "really",
    "should",
    "still",
    "that",
    "their",
    "them",
    "then",
    "there",
    "they",
    "this",
    "those",
    "very",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
    "would",
    "your",
}


def _saarthi_compact_excerpt(text: str, *, max_chars: int = 120) -> str:
    cleaned = " ".join(str(text or "").strip().split())
    if len(cleaned) <= max_chars:
        return cleaned
    return f"{cleaned[: max_chars - 3].rstrip()}..."


def _latest_question_excerpt(text: str) -> str:
    cleaned = " ".join(str(text or "").strip().split())
    if "?" not in cleaned:
        return ""
    q_idx = cleaned.rfind("?")
    if q_idx < 0:
        return ""
    boundary = max(
        cleaned.rfind(".", 0, q_idx),
        cleaned.rfind("!", 0, q_idx),
        cleaned.rfind("?", 0, max(0, q_idx - 1)),
    )
    question = cleaned[boundary + 1 : q_idx + 1].strip() if boundary >= 0 else cleaned[: q_idx + 1].strip()
    return _saarthi_compact_excerpt(question)


def _student_history_messages_for_memory(
    *,
    student_message: str,
    recent_messages: list[models.SaarthiMessage] | None = None,
) -> list[str]:
    student_messages: list[str] = []
    for row in recent_messages or []:
        if str(getattr(row, "sender_role", "") or "").strip().lower() != "student":
            continue
        raw = " ".join(str(getattr(row, "message", "") or "").strip().split())
        if raw:
            student_messages.append(raw)
    if not student_messages:
        return []
    normalized_current = _normalize_saarthi_text(student_message)
    if normalized_current and _normalize_saarthi_text(student_messages[-1]) == normalized_current:
        return student_messages[:-1]
    return student_messages


def _extract_recurring_student_terms(
    prior_student_messages: list[str],
    *,
    limit: int = 3,
) -> list[str]:
    if not prior_student_messages:
        return []
    per_message_terms: list[set[str]] = []
    for message in prior_student_messages[-6:]:
        terms: set[str] = set()
        for token in re.findall(r"[a-z0-9']+", message.lower()):
            normalized = token.strip("'")
            if len(normalized) < 4 or normalized in _SAARTHI_MEMORY_STOPWORDS:
                continue
            if normalized.endswith("s") and len(normalized) > 4:
                singular = normalized[:-1]
                if len(singular) >= 4 and singular not in _SAARTHI_MEMORY_STOPWORDS:
                    normalized = singular
            if normalized.isdigit():
                continue
            terms.add(normalized)
        if terms:
            per_message_terms.append(terms)
    if not per_message_terms:
        return []
    counts: Counter[str] = Counter()
    for terms in per_message_terms:
        counts.update(terms)
    recurring = [term for term, count in counts.most_common() if count >= 2]
    return recurring[: max(1, int(limit))]


def _extract_prior_student_intention(prior_student_messages: list[str]) -> str:
    if not prior_student_messages:
        return ""
    markers = (
        "i will",
        "i'll",
        "i am going to",
        "i'm going to",
        "i plan to",
        "i'll try",
        "i will try",
        "i can",
        "i want to",
    )
    for message in reversed(prior_student_messages[-6:]):
        segments = [seg.strip() for seg in re.split(r"[.!?]\s*", message) if seg.strip()]
        for segment in reversed(segments):
            normalized = _normalize_saarthi_text(segment)
            if _contains_any(normalized, markers):
                return _saarthi_compact_excerpt(segment)
    return ""


def _extract_prior_open_question(prior_student_messages: list[str]) -> str:
    if not prior_student_messages:
        return ""
    for message in reversed(prior_student_messages[-6:]):
        question = _latest_question_excerpt(message)
        if question:
            return question
    return ""


def _saarthi_conversation_memory_lines(
    *,
    student_message: str,
    recent_messages: list[models.SaarthiMessage] | None = None,
) -> list[str]:
    # Keep memory extraction deterministic and transcript-grounded so prompts do not hallucinate context.
    prior_student_messages = _student_history_messages_for_memory(
        student_message=student_message,
        recent_messages=recent_messages,
    )
    if not prior_student_messages:
        return []

    lines: list[str] = []
    recurring_terms = _extract_recurring_student_terms(prior_student_messages, limit=3)
    if recurring_terms:
        lines.append(f"Recurring student context: {', '.join(recurring_terms)}.")

    prior_intention = _extract_prior_student_intention(prior_student_messages)
    if prior_intention:
        lines.append(f"Prior student intention to acknowledge naturally: \"{prior_intention}\".")

    prior_question = _extract_prior_open_question(prior_student_messages)
    if prior_question:
        lines.append(f"Earlier unresolved question to keep continuity if relevant: \"{prior_question}\".")
    return lines[:3]


def _saarthi_context_bridge_line(
    *,
    student_message: str,
    recent_messages: list[models.SaarthiMessage] | None = None,
) -> str:
    prior_student_messages = _student_history_messages_for_memory(
        student_message=student_message,
        recent_messages=recent_messages,
    )
    if not prior_student_messages:
        return ""

    prior_intention = _extract_prior_student_intention(prior_student_messages)
    if prior_intention:
        return (
            f"You mentioned earlier \"{prior_intention}\", and we can build on that gently instead of forcing everything at once."
        )

    recurring_terms = _extract_recurring_student_terms(prior_student_messages, limit=2)
    if recurring_terms:
        topic_phrase = " and ".join(recurring_terms[:2])
        return f"I can see this thread has been repeating around {topic_phrase}, so we can keep today's next step clear and realistic."

    prior_question = _extract_prior_open_question(prior_student_messages)
    if prior_question:
        return f"I still remember your earlier question \"{prior_question}\", and we can keep that in focus while planning the next step."
    return ""


def _build_saarthi_llm_system_instruction() -> str:
    return "\n".join(
        [
            "You are Saarthi, an empathetic, calm, thoughtful, patient, non-judgmental, and encouraging student counsellor and mentor.",
            "Speak like a wise, understanding senior who genuinely cares, not like a clinical therapist or robotic chatbot.",
            "Your first job is emotional presence: make the student feel heard, understood, and less alone.",
            "Stay tightly grounded in the latest student message and recent transcript context; do not drift into unrelated topics.",
            "Write in plain text only. Do not use bullet points, markdown, headings, numbered lists, role labels, or policy disclaimers unless urgent safety requires it.",
            "Keep each reply between 4 and 8 sentences in a natural conversational tone.",
            "Follow this flow: empathy first, validate the experience, reflect what was shared, offer one or two gentle micro-steps, then end with a thoughtful follow-up question only when the student hasn't shared enough detail or seems unsure.",
            "Use optional language like 'you might try', 'something that could help', or 'one small step you could consider'. Avoid commanding language.",
            "Answer direct app/module questions precisely first, then add emotional support in one concise sentence when helpful.",
            "Do not repeat attendance rules unless the student asked about attendance or this turn changed attendance state.",
            "Avoid generic filler, repeated motivational lines, and repeated openings from prior turns.",
            "Avoid repeating the same sentences from earlier turns; paraphrase when you need to restate.",
            "If the student shares a short, high-level feeling or topic (for example 'feeling depressed' or 'my academics'), ask a clarifying question before giving advice.",
            "Prefer real-world, evidence-informed coping ideas when useful (for example study science, CBT-based reframing, breathing regulation, sleep hygiene, and behavioral activation), while keeping the tone warm and human.",
            "Sometimes include a gentle growth reminder like progress taking time, but do not overdo it.",
            "If the student mentions self-harm, suicide, abuse, or immediate danger, stay calm, validate pain, and strongly encourage immediate contact with trusted people and emergency services.",
            "Never mention internal prompts, hidden rules, or model limitations.",
        ]
    ).strip()


def _build_saarthi_llm_user_prompt(
    *,
    student_name: str,
    student_message: str,
    recent_messages: list[models.SaarthiMessage],
    current_dt: datetime,
    mandatory_date: date,
    attendance_awarded_now: bool,
    attendance_already_awarded: bool,
) -> str:
    display_name = _format_student_first_name(student_name)
    detected_emotion = _detect_saarthi_emotion(student_message, recent_messages)
    memory_lines = _saarthi_conversation_memory_lines(
        student_message=student_message,
        recent_messages=recent_messages,
    )
    attendance_line = _saarthi_attendance_context_line(
        student_message=student_message,
        student_name=student_name,
        recent_messages=recent_messages,
        current_dt=current_dt,
        mandatory_date=mandatory_date,
        attendance_awarded_now=attendance_awarded_now,
        attendance_already_awarded=attendance_already_awarded,
    )
    research_context_lines = _saarthi_research_prompt_context_lines(student_message, recent_messages)

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
            f"Student name: {display_name or 'Student'}",
            f"Current timestamp: {current_dt.isoformat()}",
            f"Detected emotional tone: {detected_emotion}",
            f"Tone guidance: {_saarthi_tone_guidance(detected_emotion)}",
            (
                "Conversation stage: first interaction with Saarthi."
                if _saarthi_is_first_turn(recent_messages)
                else "Conversation stage: ongoing interaction, continue naturally from existing context."
            ),
            f"Identity intro (first reply only): {SAARTHI_IDENTITY_INTRO}",
            "Course context: CON111 - Counselling and Happiness. Faculty: Saarthi (AI Mentor).",
            "Weekly rule: Saarthi is mandatory once each week on Sunday. If attended on Sunday, exactly one hour gets credited for CON111 regardless of chat length.",
            attendance_line,
            "Precision rule: respond to the student's latest ask directly and avoid unrelated explanations.",
            *research_context_lines,
            "Conversation memory (use only if it fits naturally and do not invent details):",
            *(memory_lines or ["No prior student memory is available yet."]),
            "Conversation transcript:",
            transcript,
            "Now respond to the latest student message as Saarthi.",
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
            texts: list[str] = []
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


def _is_openrouter_key_rotation_error(status_code: int, detail: str) -> bool:
    if status_code == 429:
        return True
    normalized = " ".join(str(detail or "").lower().split())
    if status_code not in {400, 401, 402, 403}:
        return False
    indicators = (
        "invalid",
        "quota",
        "credit",
        "insufficient",
        "rate limit",
        "rate_limit",
        "expired",
        "revoked",
    )
    return any(token in normalized for token in indicators)


def _reply_self_introduces_as_saarthi(reply: str) -> bool:
    normalized = _normalize_saarthi_text(reply)
    if not normalized:
        return False
    return bool(re.search(r"\b(?:i am|i'm)\s+saarthi\b", normalized))


def _looks_like_incomplete_tail_fragment(fragment: str, *, after_terminal: bool) -> bool:
    cleaned = " ".join(str(fragment or "").split()).strip()
    if not cleaned:
        return False

    if re.search(r"\b(?:i|you|we|they|he|she|it|that|there|who|what|where|when|why|how)'(?:\s|$)", cleaned.lower()):
        return True
    if cleaned[-1] in {"'", '"', "`", "(", "[", "{", "-", "/", ":", ","}:
        return True
    if cleaned.count('"') % 2 == 1 or cleaned.count("(") > cleaned.count(")"):
        return True

    tokens = [token.strip("'") for token in re.findall(r"[A-Za-z0-9']+", cleaned) if token.strip("'")]
    if not tokens:
        return True

    connector_tokens = {
        "and",
        "because",
        "but",
        "if",
        "so",
        "that",
        "then",
        "though",
        "to",
        "when",
        "while",
        "which",
        "who",
    }
    lead_token = tokens[0].lower()
    tail_token = tokens[-1].lower()

    if len(tokens) == 1 and not re.search(r"[.!?]$", cleaned):
        return True
    if tail_token in connector_tokens:
        return True
    if after_terminal and len(tokens) <= 2 and lead_token in {"i", "you", "we", "they", "he", "she", "it", "this", "that"}:
        return True
    return False


def _sanitize_saarthi_reply_text(reply: str) -> str:
    cleaned = " ".join(str(reply or "").split()).strip()
    if not cleaned:
        return ""

    last_terminal_idx = max(cleaned.rfind("."), cleaned.rfind("!"), cleaned.rfind("?"))
    if 0 <= last_terminal_idx < (len(cleaned) - 1):
        tail = cleaned[last_terminal_idx + 1 :].strip()
        if _looks_like_incomplete_tail_fragment(tail, after_terminal=True):
            cleaned = cleaned[: last_terminal_idx + 1].strip()
    elif _looks_like_incomplete_tail_fragment(cleaned, after_terminal=False):
        return ""
    return cleaned


def _finalize_saarthi_reply(
    reply: str,
    *,
    student_message: str | None = None,
    detected_emotion: str,
    first_turn: bool,
    recent_messages: list[models.SaarthiMessage] | None = None,
) -> str:
    cleaned = _sanitize_saarthi_reply_text(reply)
    if not cleaned:
        cleaned = "I'm here with you."
    if (
        first_turn
        and not _reply_self_introduces_as_saarthi(cleaned)
        and SAARTHI_IDENTITY_INTRO.lower() not in cleaned.lower()
    ):
        cleaned = f"{SAARTHI_IDENTITY_INTRO} {cleaned}".strip()

    last_assistant_question = ""
    for row in reversed(list(recent_messages or [])):
        if str(row.sender_role or "").strip().lower() != "assistant":
            continue
        last_assistant_question = _extract_tail_question(str(row.message or ""))
        if last_assistant_question:
            break
    current_tail_question = _extract_tail_question(cleaned)
    if current_tail_question and current_tail_question == last_assistant_question:
        replacement = _saarthi_follow_up_question_variant(detected_emotion, recent_messages=recent_messages)
        if _extract_tail_question(replacement) != current_tail_question:
            q_idx = cleaned.rfind("?")
            if q_idx >= 0:
                boundary = max(
                    cleaned.rfind(".", 0, q_idx),
                    cleaned.rfind("!", 0, q_idx),
                    cleaned.rfind("?", 0, max(0, q_idx - 1)),
                )
                prefix = cleaned[: boundary + 1].strip() if boundary >= 0 else ""
                cleaned = f"{prefix} {replacement}".strip() if prefix else replacement

    if "?" not in cleaned:
        ending = cleaned[-1] if cleaned else ""
        if ending not in {".", "!", "?"}:
            cleaned = f"{cleaned}."
        if student_message is not None and _should_ask_follow_up(
            student_message,
            recent_messages=recent_messages,
            first_turn=first_turn,
        ):
            cleaned = f"{cleaned} {_saarthi_follow_up_question_variant(detected_emotion, recent_messages=recent_messages)}"
    return cleaned.strip()


def _tokenize_saarthi_text(value: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", str(value or "").lower())


def _looks_like_low_quality_reply(
    reply: str,
    *,
    student_message: str,
    first_turn: bool,
) -> bool:
    cleaned = " ".join(str(reply or "").split()).strip()
    if not cleaned:
        return True

    word_count = len(_tokenize_saarthi_text(cleaned))
    sentence_count = len([chunk for chunk in re.split(r"[.!?]+", cleaned) if chunk.strip()])
    normalized = cleaned.lower()
    if cleaned != _sanitize_saarthi_reply_text(cleaned):
        return True
    if word_count < 24 or sentence_count < 4:
        return True
    if "?" not in cleaned:
        return True
    if re.search(r"\b[A-Za-z]\.\s*$", cleaned):
        return True
    if "i hear you when you say" in normalized:
        return True
    if not first_turn and normalized.startswith(("hi ", "hello ")):
        return True
    if re.search(r"\b(?:don't|doesn't|cant|can't|cannot|won't|isn't|aren't|wasn't|weren't)\s+[a-z]+\.$", normalized):
        return True
    if not first_turn and SAARTHI_IDENTITY_INTRO.lower() in normalized:
        return True

    student_tokens = set(_tokenize_saarthi_text(student_message))
    if len(student_tokens) >= 2:
        overlap = len(student_tokens.intersection(set(_tokenize_saarthi_text(cleaned))))
        overlap_ratio = overlap / max(1, len(student_tokens))
        if overlap_ratio >= 0.8 and word_count < 55:
            return True

    guidance_markers = (
        "you might try",
        "something that could help",
        "one small step you could consider",
        "a small step",
        "try",
        "could consider",
        "helpful",
    )
    if not any(marker in normalized for marker in guidance_markers):
        return True
    return False


def _generate_saarthi_reply_with_gemini(
    *,
    student_name: str,
    student_message: str,
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
    system_instruction = _build_saarthi_llm_system_instruction()
    user_prompt = _build_saarthi_llm_user_prompt(
        student_name=student_name,
        student_message=student_message,
        recent_messages=recent_messages,
        current_dt=current_dt,
        mandatory_date=mandatory_date,
        attendance_awarded_now=attendance_awarded_now,
        attendance_already_awarded=attendance_already_awarded,
    )
    body = {
        "system_instruction": {
            "parts": [{"text": system_instruction}],
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_prompt}],
            }
        ],
        "generationConfig": {
            "temperature": SAARTHI_LLM_TEMPERATURE,
            "topP": SAARTHI_LLM_TOP_P,
            "maxOutputTokens": 360,
        },
    }
    last_rotation_error = ""
    for api_key in api_keys:
        endpoint = f"{_saarthi_gemini_base_url()}/models/{urllib_parse.quote(model, safe='')}:generateContent"
        request = urllib_request.Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key,
            },
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

    if _saarthi_openrouter_api_keys():
        try:
            return _generate_saarthi_reply_with_openrouter(
                student_name=student_name,
                student_message=student_message,
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
    student_message: str,
    recent_messages: list[models.SaarthiMessage],
    current_dt: datetime,
    mandatory_date: date,
    attendance_awarded_now: bool,
    attendance_already_awarded: bool,
) -> str:
    api_keys = _saarthi_openrouter_api_keys()
    if not api_keys:
        raise RuntimeError("OPENROUTER_API_KEY is required when SAARTHI_LLM_PROVIDER=openrouter.")

    model = _saarthi_openrouter_model()
    system_instruction = _build_saarthi_llm_system_instruction()
    user_prompt = _build_saarthi_llm_user_prompt(
        student_name=student_name,
        student_message=student_message,
        recent_messages=recent_messages,
        current_dt=current_dt,
        mandatory_date=mandatory_date,
        attendance_awarded_now=attendance_awarded_now,
        attendance_already_awarded=attendance_already_awarded,
    )
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": SAARTHI_LLM_TEMPERATURE,
        "top_p": SAARTHI_LLM_TOP_P,
        "presence_penalty": SAARTHI_LLM_PRESENCE_PENALTY,
        "frequency_penalty": SAARTHI_LLM_FREQUENCY_PENALTY,
        "max_tokens": 360,
    }
    last_rotation_error = ""
    for api_key in api_keys:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        site_url = _saarthi_openrouter_site_url()
        if site_url:
            headers["HTTP-Referer"] = site_url
        app_name = _saarthi_openrouter_app_name()
        if app_name:
            headers["X-Title"] = app_name

        request = urllib_request.Request(
            f"{_saarthi_openrouter_base_url()}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib_request.urlopen(request, timeout=_saarthi_llm_timeout_seconds()) as response:
                raw_payload = response.read().decode("utf-8")
        except urllib_error.HTTPError as exc:
            detail = _gemini_error_detail(exc)
            if _is_openrouter_key_rotation_error(exc.code, detail):
                last_rotation_error = f"HTTP {exc.code}: {detail}"
                continue
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

    if last_rotation_error:
        raise RuntimeError(f"All configured OpenRouter API keys were exhausted or rejected. Last error: {last_rotation_error}")
    raise RuntimeError("Saarthi OpenRouter could not generate a reply with the configured key pool.")


def _generate_saarthi_reply_deterministic(
    *,
    student_name: str,
    student_message: str,
    current_dt: datetime,
    mandatory_date: date,
    attendance_awarded_now: bool,
    attendance_already_awarded: bool,
    recent_messages: list[models.SaarthiMessage] | None = None,
) -> str:
    message = str(student_message or "").strip()
    normalized = _normalize_saarthi_text(message)
    first_turn = _saarthi_is_first_turn(recent_messages)
    first_name = _format_student_first_name(student_name)
    if _student_indicates_topic_shift(normalized):
        lines: list[str] = []
        if first_turn:
            lines.append(SAARTHI_IDENTITY_INTRO)
        lines.append(f"{first_name}, thanks for telling me.")
        lines.append("We can set aside the earlier thread and focus on what you meant instead.")
        lines.append("What is it about, and what part feels the heaviest right now?")
        return " ".join(lines).strip()
    if _student_reports_improvement(normalized):
        prior_topics = _recent_student_topics(recent_messages=recent_messages)
        topic_label = _topic_label(prior_topics[0]) if prior_topics else ""
        lines = []
        if first_turn:
            lines.append(SAARTHI_IDENTITY_INTRO)
        lines.append(f"{first_name}, I’m glad you’re feeling a bit better.")
        if topic_label:
            lines.append(f"Is the {topic_label} situation feeling lighter, or is something else helping?")
        else:
            lines.append("What helped the most?")
        return " ".join(lines).strip()
    emotion = _detect_saarthi_emotion(student_message, recent_messages)
    assistant_turns = sum(
        1
        for row in list(recent_messages or [])
        if str(getattr(row, "sender_role", "") or "").strip().lower() == "assistant"
    )
    recent_assistant_text = _recent_assistant_text(recent_messages)
    academic_context = _contains_any(
        normalized,
        (
            "academic",
            "academics",
            "study",
            "studying",
            "exam",
            "tests",
            "grade",
            "grades",
            "gpa",
            "cgpa",
            "assignment",
            "backlog",
        ),
    )
    short_message = _is_short_student_message(normalized)
    if emotion == "sadness" and short_message and not academic_context:
        lines = []
        if first_turn:
            lines.append(SAARTHI_IDENTITY_INTRO)
        lines.append(f"{first_name}, I’m really sorry you’re feeling this low.")
        lines.append("Do you want to share what’s been weighing on you the most?")
        return " ".join(lines).strip()
    if academic_context and short_message:
        lines = []
        if first_turn:
            lines.append(SAARTHI_IDENTITY_INTRO)
        lines.append(f"{first_name}, thanks for telling me.")
        lines.append("Academics can feel heavy when deadlines and expectations stack up.")
        lines.append("Is it workload, grades, or difficulty focusing that’s hurting the most?")
        return " ".join(lines).strip()
    support_topics = _detect_saarthi_support_topics(student_message, recent_messages)
    research_requested = _student_requested_research_backing(student_message, recent_messages)
    emotion_topic_map = {
        "stress": "study_focus",
        "anxiety": "anxiety_regulation",
        "confusion": "career_clarity",
        "sadness": "mood_support",
        "frustration": "study_focus",
        "motivation_loss": "burnout_recovery",
        "curiosity": "study_focus",
    }
    primary_topic = emotion_topic_map.get(emotion, "")
    topic_priority: list[str] = []
    if primary_topic:
        topic_priority.append(primary_topic)
    for topic in support_topics:
        if topic not in topic_priority:
            topic_priority.append(topic)

    def _pick_variant(value: str | list[str], *, avoid_recent: bool = True) -> str:
        if isinstance(value, list):
            options = [item for item in value if str(item or "").strip()]
            if not options:
                return ""
            if avoid_recent and recent_assistant_text:
                for offset in range(len(options)):
                    candidate = options[(assistant_turns + offset) % len(options)]
                    if candidate.lower() not in recent_assistant_text:
                        return candidate
            return options[assistant_turns % len(options)]
        text = str(value or "").strip()
        if not text:
            return ""
        if avoid_recent and recent_assistant_text and text.lower() in recent_assistant_text:
            return ""
        return text

    def _pick_research_option() -> str:
        if not (research_requested or assistant_turns % 3 == 0):
            return ""
        for topic in topic_priority:
            options = _saarthi_research_options_by_topic(topic)
            if not options:
                continue
            if recent_assistant_text:
                for offset in range(len(options)):
                    candidate = options[(assistant_turns + offset) % len(options)]
                    if candidate.lower() not in recent_assistant_text:
                        return candidate
            return options[assistant_turns % len(options)]
        return ""

    def _pick_research_source_note() -> str:
        if not research_requested:
            return ""
        for topic in topic_priority:
            source_note = _saarthi_research_source_by_topic(topic)
            if source_note:
                cleaned_note = str(source_note).strip().rstrip(".")
                return f"This is grounded in {cleaned_note}."
        return ""

    if _contains_any(normalized, ("suicide", "kill myself", "self harm", "hurt myself", "end my life")):
        urgent = (
            f"{first_name}, I'm really glad you shared this, and I want you to stay safe right now. "
            "You don't have to carry this alone. Please reach out immediately to a trusted person nearby, "
            "your campus counselor, or local emergency support if you might act on these thoughts. "
            "Can you message or call someone you trust right now while we stay with this together?"
        )
        return urgent

    empathy_map = {
        "stress": [
            "that sounds like a lot to carry at once.",
            "I can hear how heavy this academic pressure feels for you right now.",
        ],
        "anxiety": "it makes sense that this is feeling heavy and uncertain.",
        "confusion": "it sounds like you're feeling stuck and unsure about the next direction.",
        "sadness": "I'm really sorry you're going through this right now.",
        "frustration": "that sounds frustrating, especially when you're trying your best.",
        "motivation_loss": "it can be really hard when your energy and motivation feel low.",
        "curiosity": "I'm glad you brought this up.",
    }
    validate_map = {
        "stress": [
            "A lot of students feel this way when pressure builds up.",
            "You're not overreacting, this kind of pressure can feel intense for anyone.",
        ],
        "anxiety": "You're not weak for feeling this way; it's a normal response to uncertainty.",
        "confusion": "It's completely normal to feel unclear when you are making important decisions.",
        "sadness": "Your feelings are valid, and it is okay to say this out loud.",
        "frustration": "Anyone in your position could feel this way.",
        "motivation_loss": "Many students go through this phase, and it does get lighter with small steps.",
        "curiosity": "Asking this is a strong first step.",
    }
    micro_step_map = {
        "stress": [
            "One small step you could consider is listing just three tasks: urgent, can-wait, and optional, then doing only the first one for 20 minutes.",
            "Something that could help is choosing one subject for a short 20-minute deep-focus block, then taking a 5-minute break before deciding the next step.",
        ],
        "anxiety": "Something that could help is a short grounding reset: slow breathing for one minute, then write one action you can control today.",
        "confusion": "You might try breaking this into two choices only, then asking what evidence supports each one before deciding.",
        "sadness": "A gentle step could be reaching out to one trusted person today and letting them know you've been feeling low.",
        "frustration": "You might try pausing for a few minutes, then choosing one action that moves you forward instead of trying to solve everything at once.",
        "motivation_loss": "One small step you could consider is a 20-minute focus block with no distractions, followed by a short break.",
        "curiosity": "You might try applying one idea today in a very small way and then reflecting on what changed.",
    }
    reflect_map = {
        "stress": [
            "It seems like academic load and expectations are piling up at the same time, and your mind has had little room to breathe.",
            "It sounds like you're trying to keep up with everything at once, and that constant pressure is draining your energy.",
            "Academics can feel all-consuming when results and deadlines stack up, and that weight adds up fast.",
        ],
        "anxiety": "It sounds like uncertainty is making everything feel louder than usual, even small decisions.",
        "confusion": "It seems you're trying to do the right thing but the path ahead still feels foggy.",
        "sadness": "From what you're sharing, this has been emotionally heavy for a while and not easy to carry alone.",
        "frustration": "It sounds like you are putting in effort but not getting the progress you hoped for yet.",
        "motivation_loss": "It seems the pressure has drained your energy, so starting tasks now feels harder than it used to.",
        "curiosity": "It seems you're honestly trying to understand yourself better, and that is already a strong step.",
    }

    lines: list[str] = []
    if first_turn:
        lines.append(SAARTHI_IDENTITY_INTRO)
    empathy_line = _pick_variant(empathy_map.get(emotion, "thanks for opening up."))
    if empathy_line:
        lines.append(f"{first_name}, {empathy_line}")
    validate_line = _pick_variant(validate_map.get(emotion, "What you're feeling is valid."))
    if validate_line:
        lines.append(validate_line)
    reflect_line = _pick_variant(
        reflect_map.get(
            emotion,
            "From what you shared, this has been weighing on you and you want clarity, not just quick answers.",
        )
    )
    if reflect_line:
        lines.append(reflect_line)
    context_bridge = _saarthi_context_bridge_line(
        student_message=student_message,
        recent_messages=recent_messages,
    )
    if context_bridge:
        lines.append(context_bridge)
    if academic_context:
        micro_step_line = "One small step could be picking one subject and listing the next two doable tasks, then doing just the first for 20 minutes."
    else:
        micro_step_line = _pick_variant(
            micro_step_map.get(emotion, "One small step you could consider is choosing one manageable action for today.")
        )
    if micro_step_line and (micro_step_line.lower() not in recent_assistant_text):
        lines.append(micro_step_line)
    if "?" in message:
        lines.append("If your question is about where to begin right now, start with one small action for the next 20 minutes and let that be enough for today.")
    research_tip = _pick_research_option()
    if research_tip:
        lines.append(research_tip)
    research_source_note = _pick_research_source_note()
    if research_source_note:
        lines.append(research_source_note)

    attendance_context = _saarthi_attendance_context_line(
        student_message=student_message,
        student_name=student_name,
        recent_messages=list(recent_messages or []),
        current_dt=current_dt,
        mandatory_date=mandatory_date,
        attendance_awarded_now=attendance_awarded_now,
        attendance_already_awarded=attendance_already_awarded,
    )
    if "awarded just now" in attendance_context:
        lines.append("Your Sunday CON111 check-in is now credited for this week.")
    elif "already secured" in attendance_context and _contains_any(normalized, ("attendance", "con111", "credit", "sunday")):
        lines.append("Your Sunday CON111 credit is already secured for this week.")

    growth_line = "Growth takes time, and small steady steps can create real change."
    if growth_line.lower() not in recent_assistant_text and assistant_turns % 2 == 0:
        lines.append(growth_line)
    if _should_ask_follow_up(student_message, recent_messages=recent_messages, first_turn=first_turn):
        if academic_context:
            lines.append("Is it workload, grades, or difficulty focusing that’s weighing on you most right now?")
        else:
            lines.append(_saarthi_follow_up_question_variant(emotion, recent_messages=recent_messages))
    return " ".join(lines).strip()


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
    llm_required = _saarthi_llm_required()
    recent_rows = list(recent_messages or [])
    detected_emotion = _detect_saarthi_emotion(student_message, recent_rows)
    first_turn = _saarthi_is_first_turn(recent_rows)
    provider_error: Exception | None = None

    if provider == "gemini":
        try:
            raw = _generate_saarthi_reply_with_gemini(
                student_name=student_name,
                student_message=student_message,
                recent_messages=recent_rows,
                current_dt=current_dt,
                mandatory_date=mandatory_date,
                attendance_awarded_now=attendance_awarded_now,
                attendance_already_awarded=attendance_already_awarded,
            )
            candidate = _finalize_saarthi_reply(
                raw,
                student_message=student_message,
                detected_emotion=detected_emotion,
                first_turn=first_turn,
                recent_messages=recent_rows,
            )
            if not _looks_like_low_quality_reply(
                candidate,
                student_message=student_message,
                first_turn=first_turn,
            ):
                return candidate
        except Exception as exc:
            provider_error = exc
    elif provider == "openrouter":
        try:
            raw = _generate_saarthi_reply_with_openrouter(
                student_name=student_name,
                student_message=student_message,
                recent_messages=recent_rows,
                current_dt=current_dt,
                mandatory_date=mandatory_date,
                attendance_awarded_now=attendance_awarded_now,
                attendance_already_awarded=attendance_already_awarded,
            )
            candidate = _finalize_saarthi_reply(
                raw,
                student_message=student_message,
                detected_emotion=detected_emotion,
                first_turn=first_turn,
                recent_messages=recent_rows,
            )
            if not _looks_like_low_quality_reply(
                candidate,
                student_message=student_message,
                first_turn=first_turn,
            ):
                return candidate
        except Exception as exc:
            provider_error = exc
    elif provider and llm_required:
        raise RuntimeError(f"Unsupported Saarthi LLM provider: {provider}")

    if provider_error is not None and llm_required:
        raise RuntimeError(str(provider_error)) from provider_error

    raw = _generate_saarthi_reply_deterministic(
        student_name=student_name,
        student_message=student_message,
        current_dt=current_dt,
        mandatory_date=mandatory_date,
        attendance_awarded_now=attendance_awarded_now,
        attendance_already_awarded=attendance_already_awarded,
        recent_messages=recent_rows,
    )
    return _finalize_saarthi_reply(
        raw,
        student_message=student_message,
        detected_emotion=detected_emotion,
        first_turn=first_turn,
        recent_messages=recent_rows,
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
