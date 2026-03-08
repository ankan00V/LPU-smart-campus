from __future__ import annotations

import json
import math
import re
from datetime import date, datetime, time, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth_utils import CurrentUser, require_roles
from ..database import get_db
from ..mongo import mirror_document, mirror_event
from .attendance import (
    _resolve_student_schedule_context,
    _window_flags,
    get_student_attendance_aggregate,
)
from .messages import _ensure_student_rms_cases
from .remedial import (
    _faculty_allowed_sections as remedial_faculty_allowed_sections,
    _normalize_sections,
    create_makeup_class,
    send_remedial_code_to_sections,
)

router = APIRouter(prefix="/copilot", tags=["Explainable Campus Copilot"])

REGISTRATION_PATTERN = re.compile(r"^[A-Z0-9/-]+$")
SCHEDULE_ID_RE = re.compile(r"\bschedule(?:\s*id)?\s*#?\s*(\d+)\b", re.IGNORECASE)
STUDENT_ID_RE = re.compile(r"\bstudent(?:\s*id)?\s*#?\s*(\d+)\b", re.IGNORECASE)
COURSE_ID_RE = re.compile(r"\bcourse\s*id\s*#?\s*(\d+)\b", re.IGNORECASE)
COURSE_CODE_RE = re.compile(r"\bcourse(?:\s*code)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9/_-]{1,19})\b", re.IGNORECASE)
SECTION_RE = re.compile(r"\bsection\s+([A-Z0-9/_-]{1,80})\b", re.IGNORECASE)
ROOM_RE = re.compile(r"\broom\s+([A-Z0-9][A-Z0-9\s/_-]{0,79})\b", re.IGNORECASE)
REGISTRATION_RE = re.compile(
    r"\b(?:registration(?:\s*number)?|reg(?:istration)?(?:\s*(?:number|no))?)\s*[:#-]?\s*([A-Z0-9/-]{3,40})\b",
    re.IGNORECASE,
)
DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
TIME_RE = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")


def _safe_json_dump(value: Any) -> str:
    return json.dumps(value, default=str, separators=(",", ":"), ensure_ascii=True)


def _safe_json_load_list(raw_value: str | None) -> list[dict[str, Any]]:
    raw = str(raw_value or "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []
    return parsed if isinstance(parsed, list) else []


def _safe_json_load_dict(raw_value: str | None) -> dict[str, Any]:
    raw = str(raw_value or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _supported_queries_for_role(role: models.UserRole) -> list[str]:
    if role == models.UserRole.STUDENT:
        return [
            "Why can't I mark attendance?",
            "What do I need to fix before I lose eligibility?",
        ]
    if role in {models.UserRole.ADMIN, models.UserRole.FACULTY}:
        return [
            "Create a remedial plan for course CSE501 section P132 on 2026-03-10 at 15:00",
            "Show why student 22BCS777 is flagged",
        ]
    return []


def _unsupported_response(current_user: CurrentUser) -> schemas.CopilotQueryResponse:
    supported = _supported_queries_for_role(current_user.role)
    explanation = ["This copilot accepts only audited campus actions and explainable institutional checks."]
    if supported:
        explanation.append("Use one of the supported prompt patterns for your role.")
    else:
        explanation.append("No academic copilot actions are available for your role.")
    return schemas.CopilotQueryResponse(
        intent=schemas.CopilotIntent.UNSUPPORTED,
        outcome=schemas.CopilotOutcome.BLOCKED,
        title="Copilot Request Not Supported",
        explanation=explanation,
        next_steps=supported,
    )


def _extract_first_int(regex: re.Pattern[str], text: str) -> int | None:
    match = regex.search(text)
    if not match:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


def _extract_registration_candidate(text: str) -> str | None:
    explicit = REGISTRATION_RE.search(text)
    if explicit:
        candidate = re.sub(r"\s+", "", explicit.group(1).strip().upper())
        return candidate or None
    for token in re.findall(r"[A-Z0-9/-]{5,40}", text.upper()):
        if any(char.isalpha() for char in token) and any(char.isdigit() for char in token):
            return token
    return None


def _extract_section(text: str) -> str | None:
    match = SECTION_RE.search(text)
    if not match:
        return None
    try:
        return _normalize_sections([match.group(1)])[0]
    except HTTPException:
        return None


def _extract_course_code(text: str) -> str | None:
    match = COURSE_CODE_RE.search(text)
    if not match:
        return None
    return re.sub(r"\s+", "", match.group(1).strip().upper()) or None


def _extract_room_number(text: str) -> str | None:
    match = ROOM_RE.search(text)
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(1).strip()) or None


def _extract_date(text: str) -> date | None:
    match = DATE_RE.search(text)
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


def _extract_times(text: str) -> list[time]:
    out: list[time] = []
    for hour_raw, minute_raw in TIME_RE.findall(text):
        try:
            out.append(time(hour=int(hour_raw), minute=int(minute_raw)))
        except ValueError:
            continue
    return out


def _normalize_registration_number(value: str | None) -> str | None:
    normalized = re.sub(r"\s+", "", str(value or "").strip().upper())
    if not normalized:
        return None
    if len(normalized) < 3 or not REGISTRATION_PATTERN.fullmatch(normalized):
        return None
    return normalized


def _resolve_intent(query_text: str) -> schemas.CopilotIntent:
    normalized = re.sub(r"\s+", " ", str(query_text or "").strip().lower())
    if not normalized:
        return schemas.CopilotIntent.UNSUPPORTED
    if "remedial" in normalized and any(token in normalized for token in ("create", "plan", "schedule")):
        return schemas.CopilotIntent.CREATE_REMEDIAL_PLAN
    if "eligibility" in normalized or "lose eligibility" in normalized or "attendance shortage" in normalized:
        return schemas.CopilotIntent.ELIGIBILITY_RISK
    if "flagged" in normalized and any(token in normalized for token in ("student", "show", "why")):
        return schemas.CopilotIntent.STUDENT_FLAG_REASON
    if (
        "mark attendance" in normalized
        or ("attendance" in normalized and any(token in normalized for token in ("can't", "cannot", "unable", "why")))
    ):
        return schemas.CopilotIntent.ATTENDANCE_BLOCKER
    return schemas.CopilotIntent.UNSUPPORTED


def _evidence(label: str, value: str, status: str = "info") -> schemas.CopilotEvidenceItem:
    return schemas.CopilotEvidenceItem(label=label, value=value, status=status)


def _action(action: str, status: str, detail: str | None = None) -> schemas.CopilotActionItem:
    return schemas.CopilotActionItem(action=action, status=status, detail=detail)


def _serialize_audit_row(
    row: models.CopilotAuditLog,
    *,
    actor_email: str | None = None,
) -> schemas.CopilotAuditLogOut:
    return schemas.CopilotAuditLogOut(
        id=int(row.id),
        actor_user_id=int(row.actor_user_id),
        actor_role=str(row.actor_role or ""),
        actor_email=(str(actor_email or "").strip() or None),
        query_text=str(row.query_text or ""),
        intent=schemas.CopilotIntent(str(row.intent or schemas.CopilotIntent.UNSUPPORTED.value)),
        outcome=schemas.CopilotOutcome(str(row.outcome or schemas.CopilotOutcome.FAILED.value)),
        scope=(str(row.scope or "").strip() or None),
        target_student_id=(int(row.target_student_id) if row.target_student_id else None),
        target_course_id=(int(row.target_course_id) if row.target_course_id else None),
        target_section=(str(row.target_section or "").strip() or None),
        explanation=[str(item) for item in _safe_json_load_dict(row.result_json).get("explanation", []) if str(item).strip()],
        evidence=[schemas.CopilotEvidenceItem(**item) for item in _safe_json_load_list(row.evidence_json)],
        actions=[schemas.CopilotActionItem(**item) for item in _safe_json_load_list(row.actions_json)],
        result=_safe_json_load_dict(row.result_json),
        created_at=row.created_at or datetime.utcnow(),
    )


def _persist_audit(
    db: Session,
    *,
    current_user: CurrentUser,
    payload: schemas.CopilotQueryRequest,
    response: schemas.CopilotQueryResponse,
    scope: str | None,
    target_student_id: int | None = None,
    target_course_id: int | None = None,
    target_section: str | None = None,
) -> schemas.CopilotQueryResponse:
    row = models.CopilotAuditLog(
        actor_user_id=int(current_user.id),
        actor_role=current_user.role.value,
        session_id=(str(current_user.session_id or "").strip() or None),
        query_text=str(payload.query_text or "").strip(),
        intent=response.intent.value,
        outcome=response.outcome.value,
        scope=scope,
        target_student_id=target_student_id,
        target_course_id=target_course_id,
        target_section=target_section,
        explanation_json=_safe_json_dump(response.explanation),
        evidence_json=_safe_json_dump([item.model_dump() for item in response.evidence]),
        actions_json=_safe_json_dump([item.model_dump() for item in response.actions]),
        result_json=_safe_json_dump(
            {
                "title": response.title,
                "explanation": response.explanation,
                "next_steps": response.next_steps,
                "entities": response.entities,
            }
        ),
        created_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    mirror_document(
        "admin_audit_logs",
        {
            "action": "campus_copilot_query",
            "audit_id": int(row.id),
            "intent": response.intent.value,
            "outcome": response.outcome.value,
            "query_text": row.query_text,
            "scope": row.scope,
            "target_student_id": row.target_student_id,
            "target_course_id": row.target_course_id,
            "target_section": row.target_section,
            "created_at": row.created_at,
            "source": "copilot.query",
            "actor_user_id": current_user.id,
            "actor_role": current_user.role.value,
        },
        required=False,
    )
    mirror_event(
        "copilot.query.processed",
        {
            "audit_id": int(row.id),
            "intent": response.intent.value,
            "outcome": response.outcome.value,
            "scope": row.scope,
            "target_student_id": row.target_student_id,
            "target_course_id": row.target_course_id,
            "target_section": row.target_section,
        },
        actor={
            "user_id": int(current_user.id),
            "role": current_user.role.value,
            "student_id": current_user.student_id,
            "faculty_id": current_user.faculty_id,
        },
        source="copilot.query",
        required=False,
    )
    response.audit_id = int(row.id)
    return response


def _student_section_token(student: models.Student | None) -> str:
    if not student:
        return ""
    return re.sub(r"\s+", "", str(student.section or "").strip().upper())


def _faculty_can_manage_student_scope(db: Session, *, faculty_id: int, student: models.Student | None) -> bool:
    if not student:
        return False
    faculty = db.get(models.Faculty, int(faculty_id))
    allowed_sections = remedial_faculty_allowed_sections(faculty)
    student_section = _student_section_token(student)
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


def _student_today_regular_schedules(db: Session, *, student: models.Student) -> list[models.ClassSchedule]:
    today = date.today()
    enrollment_rows = (
        db.query(models.Enrollment.course_id)
        .filter(models.Enrollment.student_id == int(student.id))
        .all()
    )
    course_ids = sorted({int(row.course_id) for row in enrollment_rows if row and row.course_id})
    if not course_ids:
        return []

    schedules = (
        db.query(models.ClassSchedule)
        .filter(
            models.ClassSchedule.is_active.is_(True),
            models.ClassSchedule.course_id.in_(course_ids),
            models.ClassSchedule.weekday == int(today.weekday()),
        )
        .order_by(models.ClassSchedule.start_time.asc(), models.ClassSchedule.id.asc())
        .all()
    )
    student_section = _student_section_token(student)
    override_filters = [
        (
            (models.TimetableOverride.scope_type == schemas.TimetableOverrideScope.STUDENT.value)
            & (models.TimetableOverride.student_id == int(student.id))
        )
    ]
    if student_section:
        override_filters.append(
            (
                (models.TimetableOverride.scope_type == schemas.TimetableOverrideScope.SECTION.value)
                & (models.TimetableOverride.section == student_section)
            )
        )
    overrides = (
        db.query(models.TimetableOverride)
        .filter(models.TimetableOverride.is_active.is_(True), or_(*override_filters))
        .order_by(models.TimetableOverride.created_at.asc(), models.TimetableOverride.id.asc())
        .all()
    )
    override_schedule_ids = sorted({int(item.schedule_id) for item in overrides if item.schedule_id})
    override_schedules = (
        {
            int(row.id): row
            for row in db.query(models.ClassSchedule)
            .filter(models.ClassSchedule.id.in_(override_schedule_ids))
            .all()
        }
        if override_schedule_ids
        else {}
    )

    effective_overrides: dict[tuple[int, time], models.ClassSchedule] = {}
    for override in overrides:
        target_schedule = override_schedules.get(int(override.schedule_id))
        if not target_schedule or not target_schedule.is_active:
            continue
        effective_overrides[(int(override.source_weekday), override.source_start_time)] = target_schedule

    suppressed_slots = set(effective_overrides.keys())
    override_target_ids = {int(item.id) for item in effective_overrides.values()}
    visible: list[models.ClassSchedule] = []
    for schedule in schedules:
        slot_key = (int(schedule.weekday), schedule.start_time)
        if slot_key in suppressed_slots or int(schedule.id) in override_target_ids:
            continue
        visible.append(schedule)
    for schedule in effective_overrides.values():
        if int(schedule.weekday) == int(today.weekday()):
            visible.append(schedule)
    visible.sort(key=lambda row: (row.start_time, row.id))
    return visible


def _pick_target_schedule(
    db: Session,
    *,
    student: models.Student,
    schedule_id: int | None,
    course_code: str | None,
) -> tuple[models.ClassSchedule | None, models.Course | None, str | None]:
    today = date.today()
    if schedule_id:
        schedule = db.get(models.ClassSchedule, int(schedule_id))
        if not schedule or not schedule.is_active:
            return None, None, "Class schedule not found."
        course = db.get(models.Course, int(schedule.course_id))
        if not course:
            return None, None, "Course not found for the selected schedule."
        return schedule, course, None

    schedules = _student_today_regular_schedules(db, student=student)
    courses_by_id = {
        int(row.id): row
        for row in db.query(models.Course)
        .filter(models.Course.id.in_([int(item.course_id) for item in schedules]))
        .all()
    } if schedules else {}
    if course_code:
        schedules = [item for item in schedules if str(courses_by_id.get(int(item.course_id)).code or "").upper() == course_code]

    if not schedules:
        if course_code:
            return None, None, f"No active class for course {course_code} is scheduled today."
        return None, None, "No active class is scheduled for you today."

    now_dt = datetime.now()
    open_now = [row for row in schedules if _window_flags(row, now_dt, today)[0]]
    if len(open_now) == 1:
        chosen = open_now[0]
        return chosen, courses_by_id.get(int(chosen.course_id)), None
    if len(open_now) > 1:
        return None, None, "Multiple attendance windows are open. Specify schedule id to continue."

    active_now = [row for row in schedules if _window_flags(row, now_dt, today)[1]]
    if len(active_now) == 1:
        chosen = active_now[0]
        return chosen, courses_by_id.get(int(chosen.course_id)), None
    if len(active_now) > 1:
        return None, None, "Multiple classes are currently active. Specify schedule id to continue."

    if len(schedules) == 1:
        chosen = schedules[0]
        return chosen, courses_by_id.get(int(chosen.course_id)), None

    return None, None, "More than one class matches today. Specify schedule id or course code."


def _classes_needed_to_recover(attended: int, delivered: int) -> int:
    deficit = (3 * int(delivered)) - (4 * int(attended))
    return max(0, deficit)


def _safe_absences_remaining(attended: int, delivered: int) -> int:
    if delivered <= 0:
        return 0
    value = math.floor((float(attended) / 0.75) - float(delivered))
    return max(0, int(value))


def _faux_student_user(actor: CurrentUser, student_id: int) -> CurrentUser:
    return CurrentUser(
        id=int(actor.id),
        email=str(actor.email or ""),
        role=models.UserRole.STUDENT,
        student_id=int(student_id),
        faculty_id=None,
        alternate_email=None,
        primary_login_verified=True,
        is_active=True,
        mfa_enabled=False,
        mfa_authenticated=True,
        session_id=actor.session_id,
        token_jti=actor.token_jti,
        device_id=actor.device_id,
        created_at=actor.created_at,
        last_login_at=actor.last_login_at,
    )


def _attendance_blocker_response(
    payload: schemas.CopilotQueryRequest,
    *,
    db: Session,
    current_user: CurrentUser,
) -> tuple[schemas.CopilotQueryResponse, dict[str, Any]]:
    if current_user.role != models.UserRole.STUDENT:
        return (
            schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.ATTENDANCE_BLOCKER,
                outcome=schemas.CopilotOutcome.DENIED,
                title="Attendance Check Restricted",
                explanation=["Only student accounts can run self-service attendance blocker checks."],
                next_steps=_supported_queries_for_role(current_user.role),
            ),
            {"scope": f"role:{current_user.role.value}"},
        )

    evidence: list[schemas.CopilotEvidenceItem] = []
    blockers: list[str] = []
    course_code = payload.course_code or _extract_course_code(payload.query_text)
    schedule_id = payload.schedule_id or _extract_first_int(SCHEDULE_ID_RE, payload.query_text)

    if not current_user.student_id:
        blockers.append("Student account is not linked correctly.")
        response = schemas.CopilotQueryResponse(
            intent=schemas.CopilotIntent.ATTENDANCE_BLOCKER,
            outcome=schemas.CopilotOutcome.BLOCKED,
            title="Attendance Blocked",
            explanation=blockers,
            evidence=[_evidence("Account linkage", "Student account link missing", "fail")],
        )
        return response, {"scope": "student:unlinked"}

    student = db.get(models.Student, int(current_user.student_id))
    if not student:
        response = schemas.CopilotQueryResponse(
            intent=schemas.CopilotIntent.ATTENDANCE_BLOCKER,
            outcome=schemas.CopilotOutcome.BLOCKED,
            title="Attendance Blocked",
            explanation=["Student record was not found."],
            evidence=[_evidence("Student record", "Missing", "fail")],
        )
        return response, {"scope": f"student:{int(current_user.student_id)}", "target_student_id": int(current_user.student_id)}

    evidence.append(_evidence("Student", f"{student.name} ({student.email})"))
    has_registration = bool(str(student.registration_number or "").strip())
    evidence.append(
        _evidence(
            "Registration number",
            (str(student.registration_number or "").strip().upper() or "Missing"),
            "pass" if has_registration else "fail",
        )
    )
    if not has_registration:
        blockers.append("Complete profile setup with registration number before attendance.")

    has_profile_photo = bool(student.profile_photo_object_key or student.profile_photo_data_url)
    evidence.append(
        _evidence(
            "Profile photo",
            "On file" if has_profile_photo else "Missing",
            "pass" if has_profile_photo else "fail",
        )
    )
    if not has_profile_photo:
        blockers.append("Upload profile photo before marking attendance.")

    has_enrollment_video = bool(str(student.enrollment_video_template_json or "").strip())
    evidence.append(
        _evidence(
            "Enrollment video",
            "Completed" if has_enrollment_video else "Missing",
            "pass" if has_enrollment_video else "fail",
        )
    )
    if not has_enrollment_video:
        blockers.append("Complete one-time enrollment video before marking attendance.")

    schedule, course, pick_error = _pick_target_schedule(
        db,
        student=student,
        schedule_id=schedule_id,
        course_code=course_code,
    )
    if pick_error:
        blockers.append(pick_error)

    if schedule and course:
        evidence.append(
            _evidence(
                "Target class",
                f"{course.code} | schedule {int(schedule.id)} | {schedule.start_time.strftime('%H:%M')}-{schedule.end_time.strftime('%H:%M')}",
            )
        )
        if not blockers:
            try:
                _resolve_student_schedule_context(
                    db=db,
                    current_user=current_user,
                    schedule_id=int(schedule.id),
                )
                evidence.append(_evidence("Timetable scope", "Class is assigned in your active timetable", "pass"))
                evidence.append(_evidence("Enrollment", "You are enrolled in this class", "pass"))
            except HTTPException as exc:
                blockers.append(str(exc.detail))
                message = str(exc.detail or "")
                if "timetable" in message.lower():
                    evidence.append(_evidence("Timetable scope", message, "fail"))
                elif "enrolled" in message.lower():
                    evidence.append(_evidence("Enrollment", message, "fail"))
                else:
                    evidence.append(_evidence("Class access", message, "fail"))

        today = date.today()
        now_dt = datetime.now()
        if schedule.weekday != int(today.weekday()):
            blockers.append("This class is not scheduled for today.")
            evidence.append(_evidence("Class day", "Not scheduled today", "fail"))
        else:
            is_open_now, is_active_now, _ = _window_flags(schedule, now_dt, today, course=course)
            if is_open_now:
                evidence.append(_evidence("Attendance window", "Open now", "pass"))
            else:
                detail = "Attendance window is closed (only first 10 minutes)." if is_active_now else "Attendance is not open yet."
                blockers.append(detail)
                evidence.append(_evidence("Attendance window", detail, "fail"))

    if blockers:
        return (
            schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.ATTENDANCE_BLOCKER,
                outcome=schemas.CopilotOutcome.BLOCKED,
                title="Attendance Blocked",
                explanation=blockers,
                evidence=evidence,
                actions=[_action("attendance_mark_check", "blocked", blockers[0])],
                next_steps=[
                    "Fix the failed checks above, then retry attendance marking from the Attendance module.",
                    "If multiple classes are running today, include schedule id or course code in your prompt.",
                ],
                entities={
                    "student_id": int(student.id),
                    "schedule_id": int(schedule.id) if schedule else None,
                    "course_id": int(course.id) if course else None,
                    "course_code": (course.code if course else None),
                },
            ),
            {
                "scope": f"student:{int(student.id)}",
                "target_student_id": int(student.id),
                "target_course_id": int(course.id) if course else None,
            },
        )

    return (
        schemas.CopilotQueryResponse(
            intent=schemas.CopilotIntent.ATTENDANCE_BLOCKER,
            outcome=schemas.CopilotOutcome.COMPLETED,
            title="Attendance Ready",
            explanation=[
                f"You can mark attendance for {course.code} right now.",
                "No policy blocker is active. The remaining step is live face verification in the attendance capture flow.",
            ],
            evidence=evidence,
            actions=[_action("attendance_mark_check", "completed", "All pre-checks passed")],
            next_steps=["Open the live attendance flow and complete the selfie verification."],
            entities={
                "student_id": int(student.id),
                "schedule_id": int(schedule.id),
                "course_id": int(course.id),
                "course_code": course.code,
            },
        ),
        {
            "scope": f"student:{int(student.id)}",
            "target_student_id": int(student.id),
            "target_course_id": int(course.id),
        },
    )


def _eligibility_risk_response(
    payload: schemas.CopilotQueryRequest,
    *,
    db: Session,
    current_user: CurrentUser,
) -> tuple[schemas.CopilotQueryResponse, dict[str, Any]]:
    if current_user.role != models.UserRole.STUDENT:
        return (
            schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.ELIGIBILITY_RISK,
                outcome=schemas.CopilotOutcome.DENIED,
                title="Eligibility Check Restricted",
                explanation=["Only student accounts can run self-service eligibility checks."],
                next_steps=_supported_queries_for_role(current_user.role),
            ),
            {"scope": f"role:{current_user.role.value}"},
        )

    aggregate = get_student_attendance_aggregate(db=db, current_user=current_user)
    requested_course_code = payload.course_code or _extract_course_code(payload.query_text)
    course_rows = aggregate.courses
    if requested_course_code:
        course_rows = [row for row in aggregate.courses if row.course_code == requested_course_code]
        if not course_rows:
            response = schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.ELIGIBILITY_RISK,
                outcome=schemas.CopilotOutcome.BLOCKED,
                title="Eligibility Scope Not Found",
                explanation=[f"No attendance aggregate was found for course {requested_course_code}."],
                next_steps=["Retry with a valid enrolled course code or remove the course filter."],
            )
            return response, {"scope": f"student:{int(current_user.student_id or 0)}"}

    evidence = [
        _evidence("Overall attendance", f"{aggregate.aggregate_percent:.2f}% ({aggregate.attended_total}/{aggregate.delivered_total})"),
    ]
    explanations = [f"Your current aggregate attendance is {aggregate.aggregate_percent:.2f}%."]
    next_steps: list[str] = []
    at_risk_lines: list[str] = []
    watch_lines: list[str] = []
    stable_lines: list[str] = []

    for row in course_rows:
        safe_misses = _safe_absences_remaining(row.attended_classes, row.delivered_classes)
        recover = _classes_needed_to_recover(row.attended_classes, row.delivered_classes)
        evidence.append(
            _evidence(
                f"{row.course_code}",
                f"{row.attendance_percent:.2f}% ({row.attended_classes}/{row.delivered_classes})",
                "fail" if row.delivered_classes >= 4 and row.attendance_percent < 75.0 else (
                    "warning" if row.attendance_percent < 80.0 else "pass"
                ),
            )
        )
        if row.delivered_classes >= 4 and row.attendance_percent < 75.0:
            at_risk_lines.append(
                f"{row.course_code} is below 75%. Attend the next {recover} class(es) in a row to recover eligibility."
            )
        elif row.delivered_classes > 0 and row.attendance_percent < 80.0:
            watch_lines.append(
                f"{row.course_code} is on watch at {row.attendance_percent:.2f}%. You can miss {safe_misses} more class(es) before dropping below 75%."
            )
        else:
            stable_lines.append(
                f"{row.course_code} is stable at {row.attendance_percent:.2f}%. Safe misses remaining before 75%: {safe_misses}."
            )

    if at_risk_lines:
        explanations.append(f"You are already below the 75% threshold in {len(at_risk_lines)} course(s).")
        explanations.extend(at_risk_lines)
        next_steps.append("Prioritize the flagged courses first; the recovery counts above assume no further absences.")
        title = "Eligibility At Risk"
    elif watch_lines:
        explanations.append("You are still eligible, but one or more courses are close to the 75% boundary.")
        explanations.extend(watch_lines)
        if stable_lines:
            explanations.extend(stable_lines[:2])
        next_steps.append("Do not miss the next scheduled class in the watchlisted course(s).")
        title = "Eligibility Watchlist"
    else:
        explanations.append("No course is currently below the 75% eligibility threshold.")
        explanations.extend(stable_lines[:3] or ["Keep maintaining your current attendance pace."])
        next_steps.append("Keep your attendance above 75% in every course, not just the aggregate.")
        title = "Eligibility Safe"

    return (
        schemas.CopilotQueryResponse(
            intent=schemas.CopilotIntent.ELIGIBILITY_RISK,
            outcome=schemas.CopilotOutcome.COMPLETED,
            title=title,
            explanation=explanations,
            evidence=evidence,
            actions=[_action("eligibility_risk_check", "completed", f"Reviewed {len(course_rows)} course aggregate(s)")],
            next_steps=next_steps,
            entities={
                "student_id": int(current_user.student_id or 0),
                "aggregate_percent": float(aggregate.aggregate_percent),
                "at_risk_courses": [row.course_code for row in course_rows if row.delivered_classes >= 4 and row.attendance_percent < 75.0],
            },
        ),
        {
            "scope": f"student:{int(current_user.student_id or 0)}",
            "target_student_id": int(current_user.student_id or 0),
        },
    )


def _resolve_target_student(
    payload: schemas.CopilotQueryRequest,
    *,
    db: Session,
    current_user: CurrentUser,
) -> tuple[models.Student | None, str | None]:
    student_id = payload.student_id or _extract_first_int(STUDENT_ID_RE, payload.query_text)
    registration_number = _normalize_registration_number(payload.registration_number) or _normalize_registration_number(
        _extract_registration_candidate(payload.query_text)
    )
    student = None
    if student_id:
        student = db.get(models.Student, int(student_id))
    elif registration_number:
        student = (
            db.query(models.Student)
            .filter(func.upper(models.Student.registration_number) == registration_number)
            .first()
        )
    if not student:
        if student_id or registration_number:
            return None, "Student not found in the current campus record set."
        return None, "Provide a student id or registration number."

    if current_user.role == models.UserRole.FACULTY:
        if not current_user.faculty_id:
            return None, "Faculty account is not linked correctly."
        if not _faculty_can_manage_student_scope(db, faculty_id=int(current_user.faculty_id), student=student):
            return None, "Student is outside your allocated section(s) and teaching scope."
    return student, None


def _flag_reason_response(
    payload: schemas.CopilotQueryRequest,
    *,
    db: Session,
    current_user: CurrentUser,
) -> tuple[schemas.CopilotQueryResponse, dict[str, Any]]:
    if current_user.role not in {models.UserRole.ADMIN, models.UserRole.FACULTY}:
        return (
            schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.STUDENT_FLAG_REASON,
                outcome=schemas.CopilotOutcome.DENIED,
                title="Student Flag Review Restricted",
                explanation=["Only admin and faculty accounts can inspect another student's flag reasons."],
                next_steps=_supported_queries_for_role(current_user.role),
            ),
            {"scope": f"role:{current_user.role.value}"},
        )

    student, error = _resolve_target_student(payload, db=db, current_user=current_user)
    if error:
        outcome = schemas.CopilotOutcome.DENIED if "outside your allocated" in error.lower() else schemas.CopilotOutcome.BLOCKED
        return (
            schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.STUDENT_FLAG_REASON,
                outcome=outcome,
                title="Student Flag Review Blocked",
                explanation=[error],
                next_steps=["Retry with a valid in-scope student id or registration number."],
            ),
            {"scope": f"role:{current_user.role.value}"},
        )

    _ensure_student_rms_cases(db, student_id=int(student.id), limit=800)
    aggregate = get_student_attendance_aggregate(db=db, current_user=_faux_student_user(current_user, int(student.id)))
    at_risk_courses = [row for row in aggregate.courses if row.delivered_classes >= 4 and row.attendance_percent < 75.0]
    open_cases = (
        db.query(models.RMSCase)
        .filter(
            models.RMSCase.student_id == int(student.id),
            models.RMSCase.status != models.RMSCaseStatus.CLOSED,
        )
        .order_by(models.RMSCase.updated_at.desc(), models.RMSCase.id.desc())
        .all()
    )
    escalated_cases = [row for row in open_cases if bool(row.is_escalated)]
    pending_rectifications = int(
        db.query(func.count(models.AttendanceRectificationRequest.id))
        .filter(
            models.AttendanceRectificationRequest.student_id == int(student.id),
            models.AttendanceRectificationRequest.status == models.AttendanceRectificationStatus.PENDING,
        )
        .scalar()
        or 0
    )
    pending_corrections = int(
        db.query(func.count(models.RMSAttendanceCorrectionRequest.id))
        .filter(
            models.RMSAttendanceCorrectionRequest.student_id == int(student.id),
            models.RMSAttendanceCorrectionRequest.status
            == models.RMSAttendanceCorrectionStatus.PENDING_ADMIN_APPROVAL,
        )
        .scalar()
        or 0
    )
    missing_profile_flags: list[str] = []
    if not str(student.registration_number or "").strip():
        missing_profile_flags.append("registration number missing")
    if not _student_section_token(student):
        missing_profile_flags.append("section missing")
    if not (student.profile_photo_object_key or student.profile_photo_data_url):
        missing_profile_flags.append("profile photo missing")

    evidence = [
        _evidence("Student", f"{student.name} ({student.registration_number or 'No reg'})"),
        _evidence("Overall attendance", f"{aggregate.aggregate_percent:.2f}% ({aggregate.attended_total}/{aggregate.delivered_total})"),
        _evidence("Open RMS cases", str(len(open_cases)), "warning" if open_cases else "pass"),
        _evidence("Escalated RMS cases", str(len(escalated_cases)), "fail" if escalated_cases else "pass"),
        _evidence("Pending rectification requests", str(pending_rectifications), "warning" if pending_rectifications else "pass"),
        _evidence("Pending attendance corrections", str(pending_corrections), "warning" if pending_corrections else "pass"),
    ]
    if missing_profile_flags:
        evidence.append(_evidence("Profile completeness", ", ".join(missing_profile_flags), "warning"))

    reasons: list[str] = []
    next_steps: list[str] = []
    for row in at_risk_courses:
        recover = _classes_needed_to_recover(row.attended_classes, row.delivered_classes)
        reasons.append(
            f"{row.course_code} is below 75% at {row.attendance_percent:.2f}% and needs {recover} consecutive attended class(es) to recover."
        )
    if escalated_cases:
        reasons.append(f"{len(escalated_cases)} RMS case(s) are escalated and still unresolved.")
        next_steps.append("Review the escalated RMS case queue and transition or close the open case(s).")
    elif open_cases:
        reasons.append(f"{len(open_cases)} RMS case(s) are still open for this student.")
        next_steps.append("Triage the open RMS case(s) so the student exits the unresolved support queue.")
    if pending_rectifications:
        reasons.append(f"{pending_rectifications} attendance rectification request(s) are pending faculty review.")
        next_steps.append("Review the pending attendance rectification request(s).")
    if pending_corrections:
        reasons.append(f"{pending_corrections} RMS attendance correction request(s) are pending admin approval.")
        next_steps.append("Review the pending attendance correction request(s).")
    if missing_profile_flags:
        reasons.append("Profile completeness checks are failing: " + ", ".join(missing_profile_flags) + ".")
        next_steps.append("Update the missing profile attributes so identity checks stop failing.")

    if at_risk_courses:
        next_steps.append(
            f"Consider a remedial plan for {at_risk_courses[0].course_code} if the attendance deficit is not recoverable through the next regular classes."
        )

    if reasons:
        explanation = [f"{student.name} is flagged for {len(reasons)} active reason(s).", *reasons]
        title = "Student Flag Reasons"
    else:
        explanation = [f"No active flag reasons were found for {student.name}."]
        title = "Student Not Flagged"
        next_steps.append("No intervention is required right now.")

    return (
        schemas.CopilotQueryResponse(
            intent=schemas.CopilotIntent.STUDENT_FLAG_REASON,
            outcome=schemas.CopilotOutcome.COMPLETED,
            title=title,
            explanation=explanation,
            evidence=evidence,
            actions=[_action("student_flag_review", "completed", f"Reviewed student {int(student.id)}")],
            next_steps=next_steps,
            entities={
                "student_id": int(student.id),
                "registration_number": (str(student.registration_number or "").strip().upper() or None),
                "at_risk_courses": [row.course_code for row in at_risk_courses],
                "open_rms_cases": len(open_cases),
                "pending_rectifications": pending_rectifications,
                "pending_corrections": pending_corrections,
            },
        ),
        {
            "scope": f"student:{int(student.id)}",
            "target_student_id": int(student.id),
        },
    )


def _resolve_remedial_course(
    payload: schemas.CopilotQueryRequest,
    *,
    db: Session,
    current_user: CurrentUser,
) -> tuple[models.Course | None, str | None]:
    course_id = payload.course_id or _extract_first_int(COURSE_ID_RE, payload.query_text)
    course_code = payload.course_code or _extract_course_code(payload.query_text)
    query = db.query(models.Course)
    if current_user.role == models.UserRole.FACULTY:
        if not current_user.faculty_id:
            return None, "Faculty account is not linked correctly."
        query = query.filter(models.Course.faculty_id == int(current_user.faculty_id))

    if course_id:
        course = query.filter(models.Course.id == int(course_id)).first()
        return course, None if course else "Course was not found in your allowed scope."
    if course_code:
        course = query.filter(func.upper(models.Course.code) == course_code).first()
        return course, None if course else f"Course {course_code} was not found in your allowed scope."

    candidate_courses = query.order_by(models.Course.code.asc(), models.Course.id.asc()).all()
    if len(candidate_courses) == 1:
        return candidate_courses[0], None
    return None, "Specify course id or course code for the remedial plan."


def _resolve_target_section(
    payload: schemas.CopilotQueryRequest,
    *,
    db: Session,
    current_user: CurrentUser,
) -> tuple[str | None, str | None]:
    section = payload.section or _extract_section(payload.query_text)
    if current_user.role == models.UserRole.FACULTY:
        if not current_user.faculty_id:
            return None, "Faculty account is not linked correctly."
        faculty = db.get(models.Faculty, int(current_user.faculty_id))
        allowed_sections = sorted(remedial_faculty_allowed_sections(faculty))
        if section:
            if allowed_sections and section not in allowed_sections:
                return None, "Selected section is outside your allocated section scope."
            return section, None
        if len(allowed_sections) == 1:
            return allowed_sections[0], None
        return None, "Specify section for the remedial plan."
    if section:
        return section, None
    return None, "Specify section for the remedial plan."


def _resolve_remedial_schedule_inputs(payload: schemas.CopilotQueryRequest) -> tuple[date | None, time | None, time | None, str, str | None, list[str]]:
    class_date = payload.class_date or _extract_date(payload.query_text)
    query_times = _extract_times(payload.query_text)
    start_time = payload.start_time or (query_times[0] if query_times else None)
    end_time = payload.end_time or (query_times[1] if len(query_times) > 1 else None)
    mode = payload.class_mode or ("offline" if "offline" in payload.query_text.lower() else "online")
    room_number = payload.room_number or _extract_room_number(payload.query_text)
    missing: list[str] = []
    if class_date is None:
        missing.append("class_date")
    if start_time is None:
        missing.append("start_time")
    if end_time is None and start_time is not None:
        start_dt = datetime.combine(date.today(), start_time)
        end_dt = start_dt + timedelta(minutes=60)
        if end_dt.date() == start_dt.date():
            end_time = end_dt.time()
    if end_time is None:
        missing.append("end_time")
    if mode == "offline" and not room_number:
        missing.append("room_number")
    return class_date, start_time, end_time, mode, room_number, missing


def _remedial_plan_response(
    payload: schemas.CopilotQueryRequest,
    *,
    db: Session,
    current_user: CurrentUser,
) -> tuple[schemas.CopilotQueryResponse, dict[str, Any]]:
    if current_user.role not in {models.UserRole.ADMIN, models.UserRole.FACULTY}:
        return (
            schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.CREATE_REMEDIAL_PLAN,
                outcome=schemas.CopilotOutcome.DENIED,
                title="Remedial Planning Restricted",
                explanation=["Only admin and faculty accounts can create remedial plans."],
                next_steps=_supported_queries_for_role(current_user.role),
            ),
            {"scope": f"role:{current_user.role.value}"},
        )

    course, course_error = _resolve_remedial_course(payload, db=db, current_user=current_user)
    if course_error:
        return (
            schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.CREATE_REMEDIAL_PLAN,
                outcome=schemas.CopilotOutcome.BLOCKED,
                title="Remedial Plan Blocked",
                explanation=[course_error],
                next_steps=["Retry with a valid course code or course id."],
            ),
            {"scope": f"role:{current_user.role.value}"},
        )
    if not course:
        return (
            schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.CREATE_REMEDIAL_PLAN,
                outcome=schemas.CopilotOutcome.BLOCKED,
                title="Remedial Plan Blocked",
                explanation=["Course was not found."],
            ),
            {"scope": f"role:{current_user.role.value}"},
        )

    section, section_error = _resolve_target_section(payload, db=db, current_user=current_user)
    if section_error:
        return (
            schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.CREATE_REMEDIAL_PLAN,
                outcome=schemas.CopilotOutcome.BLOCKED,
                title="Remedial Plan Blocked",
                explanation=[section_error],
                next_steps=["Retry with a valid in-scope section token."],
            ),
            {"scope": f"course:{int(course.id)}", "target_course_id": int(course.id)},
        )
    if not section:
        return (
            schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.CREATE_REMEDIAL_PLAN,
                outcome=schemas.CopilotOutcome.BLOCKED,
                title="Remedial Plan Blocked",
                explanation=["Section was not resolved for the remedial scope."],
            ),
            {"scope": f"course:{int(course.id)}", "target_course_id": int(course.id)},
        )

    students = (
        db.query(models.Student)
        .join(models.Enrollment, models.Enrollment.student_id == models.Student.id)
        .filter(
            models.Enrollment.course_id == int(course.id),
            models.Student.section == section,
        )
        .order_by(models.Student.name.asc(), models.Student.id.asc())
        .all()
    )
    if not students:
        return (
            schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.CREATE_REMEDIAL_PLAN,
                outcome=schemas.CopilotOutcome.BLOCKED,
                title="Remedial Plan Blocked",
                explanation=[f"No enrolled students were found for section {section} in {course.code}."],
            ),
            {
                "scope": f"course:{int(course.id)}|section:{section}",
                "target_course_id": int(course.id),
                "target_section": section,
            },
        )

    student_ids = [int(student.id) for student in students]
    attendance_rows = (
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
        .filter(
            models.AttendanceRecord.course_id == int(course.id),
            models.AttendanceRecord.student_id.in_(student_ids),
        )
        .group_by(models.AttendanceRecord.student_id)
        .all()
    )
    attendance_map = {
        int(student_id): {
            "marked": int(marked or 0),
            "present": int(present or 0),
        }
        for student_id, marked, present in attendance_rows
    }
    at_risk_names: list[str] = []
    watchlist_names: list[str] = []
    percents: list[float] = []
    for student in students:
        stats = attendance_map.get(int(student.id), {"marked": 0, "present": 0})
        marked_count = int(stats["marked"])
        present_count = int(stats["present"])
        percent = round((present_count / marked_count) * 100.0, 2) if marked_count else 0.0
        if marked_count:
            percents.append(percent)
        if marked_count >= 4 and percent < 75.0:
            at_risk_names.append(student.name)
        elif marked_count > 0 and percent < 80.0:
            watchlist_names.append(student.name)

    average_percent = round(sum(percents) / len(percents), 2) if percents else 0.0
    evidence = [
        _evidence("Course", f"{course.code} | {course.title}"),
        _evidence("Section", section),
        _evidence("Students in scope", str(len(students))),
        _evidence("At-risk students", str(len(at_risk_names)), "warning" if at_risk_names else "pass"),
        _evidence("Watchlist students", str(len(watchlist_names)), "warning" if watchlist_names else "pass"),
        _evidence("Average recorded attendance", f"{average_percent:.2f}%"),
    ]
    explanation = [
        f"Prepared a remedial recovery plan for {course.code} section {section}.",
        f"{len(students)} student(s) are in scope; {len(at_risk_names)} are already below the 75% threshold.",
        "Recommended 60-minute structure: 15 min recap, 20 min guided correction, 15 min targeted practice, 10 min exit check.",
    ]
    if at_risk_names:
        explanation.append("Priority students: " + ", ".join(at_risk_names[:6]) + ("." if len(at_risk_names) <= 6 else ", ..."))

    class_date, start_time, end_time, class_mode, room_number, missing = _resolve_remedial_schedule_inputs(payload)
    actions = [_action("prepare_remedial_scope", "completed", f"Scoped {len(students)} student(s)")]
    next_steps: list[str] = []
    entities: dict[str, Any] = {
        "course_id": int(course.id),
        "course_code": course.code,
        "section": section,
        "students_in_scope": len(students),
        "at_risk_students": len(at_risk_names),
    }

    if missing:
        actions.append(_action("schedule_makeup_class", "blocked", "Missing required scheduling fields"))
        next_steps.append(
            f"Retry with date and time, for example: Create a remedial plan for course {course.code} section {section} on 2026-03-10 at 15:00"
        )
        if class_mode == "offline":
            next_steps.append("Include a room number because offline remedial classes require room assignment.")
        return (
            schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.CREATE_REMEDIAL_PLAN,
                outcome=schemas.CopilotOutcome.BLOCKED,
                title="Remedial Plan Prepared",
                explanation=explanation + [f"Execution is blocked until these fields are provided: {', '.join(missing)}."],
                evidence=evidence,
                actions=actions,
                next_steps=next_steps,
                entities=entities,
            ),
            {
                "scope": f"course:{int(course.id)}|section:{section}",
                "target_course_id": int(course.id),
                "target_section": section,
            },
        )

    faculty_id = int(current_user.faculty_id) if current_user.role == models.UserRole.FACULTY else int(course.faculty_id)
    topic = f"Attendance recovery | {course.code} | Section {section}"
    try:
        class_out = create_makeup_class(
            schemas.MakeUpClassCreate(
                course_id=int(course.id),
                faculty_id=faculty_id,
                class_date=class_date,
                start_time=start_time,
                end_time=end_time,
                topic=topic,
                sections=[section],
                class_mode=class_mode,
                room_number=room_number if class_mode == "offline" else None,
            ),
            db=db,
            current_user=current_user,
        )
    except HTTPException as exc:
        actions.append(_action("schedule_makeup_class", "failed", str(exc.detail)))
        return (
            schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.CREATE_REMEDIAL_PLAN,
                outcome=schemas.CopilotOutcome.BLOCKED,
                title="Remedial Scheduling Failed",
                explanation=explanation + [str(exc.detail)],
                evidence=evidence,
                actions=actions,
                next_steps=["Adjust the date, time, or section scope and retry."],
                entities=entities,
            ),
            {
                "scope": f"course:{int(course.id)}|section:{section}",
                "target_course_id": int(course.id),
                "target_section": section,
            },
        )

    actions.append(_action("schedule_makeup_class", "completed", f"Scheduled class {int(class_out.id)}"))
    explanation.append(
        f"Scheduled the remedial class for {class_out.class_date.isoformat()} {class_out.start_time.strftime('%H:%M')}-{class_out.end_time.strftime('%H:%M')} ({class_out.class_mode})."
    )
    entities.update(
        {
            "class_id": int(class_out.id),
            "remedial_code": class_out.remedial_code,
        }
    )

    if payload.send_message:
        try:
            send_out = send_remedial_code_to_sections(
                int(class_out.id),
                schemas.RemedialSendMessageRequest(custom_message=None),
                db=db,
                current_user=current_user,
            )
            actions.append(_action("send_remedial_code", "completed", send_out.message))
            explanation.append(f"Sent the remedial code to {int(send_out.recipients)} student(s).")
            entities["message_recipients"] = int(send_out.recipients)
        except HTTPException as exc:
            actions.append(_action("send_remedial_code", "failed", str(exc.detail)))
            explanation.append(f"Class was scheduled, but notification dispatch failed: {exc.detail}")
            next_steps.append("Open the Remedial module and resend the code manually if needed.")

    return (
        schemas.CopilotQueryResponse(
            intent=schemas.CopilotIntent.CREATE_REMEDIAL_PLAN,
            outcome=schemas.CopilotOutcome.COMPLETED,
            title="Remedial Plan Scheduled",
            explanation=explanation,
            evidence=evidence,
            actions=actions,
            next_steps=next_steps or ["Track attendance from the Remedial module once the class starts."],
            entities=entities,
        ),
        {
            "scope": f"course:{int(course.id)}|section:{section}",
            "target_course_id": int(course.id),
            "target_section": section,
        },
    )


@router.post("/query", response_model=schemas.CopilotQueryResponse)
def copilot_query(
    payload: schemas.CopilotQueryRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_roles(
            models.UserRole.ADMIN,
            models.UserRole.FACULTY,
            models.UserRole.STUDENT,
            models.UserRole.OWNER,
        )
    ),
):
    intent = _resolve_intent(payload.query_text)
    if intent == schemas.CopilotIntent.UNSUPPORTED:
        response = _unsupported_response(current_user)
        return _persist_audit(
            db,
            current_user=current_user,
            payload=payload,
            response=response,
            scope=f"role:{current_user.role.value}",
        )

    handler_map = {
        schemas.CopilotIntent.ATTENDANCE_BLOCKER: _attendance_blocker_response,
        schemas.CopilotIntent.ELIGIBILITY_RISK: _eligibility_risk_response,
        schemas.CopilotIntent.CREATE_REMEDIAL_PLAN: _remedial_plan_response,
        schemas.CopilotIntent.STUDENT_FLAG_REASON: _flag_reason_response,
    }
    handler = handler_map[intent]
    response, audit_meta = handler(payload, db=db, current_user=current_user)
    return _persist_audit(
        db,
        current_user=current_user,
        payload=payload,
        response=response,
        scope=audit_meta.get("scope"),
        target_student_id=audit_meta.get("target_student_id"),
        target_course_id=audit_meta.get("target_course_id"),
        target_section=audit_meta.get("target_section"),
    )


@router.get("/audit", response_model=list[schemas.CopilotAuditLogOut])
def list_copilot_audit(
    limit: int = Query(default=50, ge=1, le=200),
    actor_user_id: int | None = Query(default=None, ge=1),
    q: str | None = Query(default=None, min_length=1, max_length=120),
    intent: schemas.CopilotIntent | None = Query(default=None),
    outcome: schemas.CopilotOutcome | None = Query(default=None),
    actor_role: models.UserRole | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_roles(
            models.UserRole.ADMIN,
            models.UserRole.FACULTY,
            models.UserRole.STUDENT,
            models.UserRole.OWNER,
        )
    ),
):
    query = db.query(models.CopilotAuditLog, models.AuthUser.email).outerjoin(
        models.AuthUser,
        models.AuthUser.id == models.CopilotAuditLog.actor_user_id,
    )
    if current_user.role != models.UserRole.ADMIN:
        query = query.filter(models.CopilotAuditLog.actor_user_id == int(current_user.id))
    elif actor_user_id is not None:
        query = query.filter(models.CopilotAuditLog.actor_user_id == int(actor_user_id))

    if intent is not None:
        query = query.filter(models.CopilotAuditLog.intent == intent.value)
    if outcome is not None:
        query = query.filter(models.CopilotAuditLog.outcome == outcome.value)
    if actor_role is not None:
        query = query.filter(models.CopilotAuditLog.actor_role == actor_role.value)
    if q is not None:
        search_text = str(q).strip().lower()
        if search_text:
            pattern = f"%{search_text}%"
            filters = [
                func.lower(models.CopilotAuditLog.query_text).like(pattern),
                func.lower(func.coalesce(models.CopilotAuditLog.scope, "")).like(pattern),
                func.lower(func.coalesce(models.CopilotAuditLog.target_section, "")).like(pattern),
                func.lower(models.CopilotAuditLog.actor_role).like(pattern),
                func.lower(models.CopilotAuditLog.intent).like(pattern),
                func.lower(models.CopilotAuditLog.outcome).like(pattern),
                func.lower(func.coalesce(models.AuthUser.email, "")).like(pattern),
            ]
            if search_text.isdigit():
                numeric_id = int(search_text)
                filters.extend(
                    [
                        models.CopilotAuditLog.id == numeric_id,
                        models.CopilotAuditLog.actor_user_id == numeric_id,
                        models.CopilotAuditLog.target_student_id == numeric_id,
                        models.CopilotAuditLog.target_course_id == numeric_id,
                    ]
                )
            query = query.filter(or_(*filters))

    rows = (
        query.order_by(models.CopilotAuditLog.created_at.desc(), models.CopilotAuditLog.id.desc())
        .limit(int(limit))
        .all()
    )
    return [
        _serialize_audit_row(row, actor_email=actor_email)
        for row, actor_email in rows
    ]
