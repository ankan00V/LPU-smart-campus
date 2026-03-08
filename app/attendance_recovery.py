from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from . import models
from .realtime_bus import publish_domain_event
from .saarthi_service import is_saarthi_course
from .workers import enqueue_notification_after_commit
ACTIVE_PLAN_STATUSES = (
    models.AttendanceRecoveryPlanStatus.ACTIVE,
    models.AttendanceRecoveryPlanStatus.ESCALATED,
)
ACTIVE_RMS_CASE_STATUSES = (
    models.RMSCaseStatus.NEW,
    models.RMSCaseStatus.TRIAGE,
    models.RMSCaseStatus.ASSIGNED,
)
STUDENT_FACING_ACTIONS = {
    models.AttendanceRecoveryActionType.REMEDIAL_SLOT,
    models.AttendanceRecoveryActionType.OFFICE_HOUR_INVITE,
    models.AttendanceRecoveryActionType.CATCH_UP_TASK,
}
AUTO_SENT_ACTIONS = {
    models.AttendanceRecoveryActionType.FACULTY_NUDGE,
    models.AttendanceRecoveryActionType.PARENT_ALERT,
}


def _bool_env(name: str, default: bool) -> bool:
    raw = (os.getenv(name, "true" if default else "false") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _float_env(name: str, default: float) -> float:
    raw = (os.getenv(name, str(default)) or "").strip()
    try:
        return float(raw)
    except ValueError:
        return float(default)


def _int_env(name: str, default: int) -> int:
    raw = (os.getenv(name, str(default)) or "").strip()
    try:
        return int(raw)
    except ValueError:
        return int(default)


def recovery_enabled() -> bool:
    return _bool_env("ATTENDANCE_RECOVERY_ENABLED", default=True)


def parent_alert_enabled() -> bool:
    return _bool_env("ATTENDANCE_RECOVERY_PARENT_ALERTS_ENABLED", default=True)


def recovery_watch_threshold() -> float:
    return max(1.0, min(100.0, _float_env("ATTENDANCE_RECOVERY_WATCH_THRESHOLD", 75.0)))


def recovery_high_threshold() -> float:
    return max(1.0, min(recovery_watch_threshold(), _float_env("ATTENDANCE_RECOVERY_HIGH_THRESHOLD", 65.0)))


def recovery_critical_threshold() -> float:
    return max(1.0, min(recovery_high_threshold(), _float_env("ATTENDANCE_RECOVERY_CRITICAL_THRESHOLD", 50.0)))


def recovery_due_days() -> int:
    return max(2, _int_env("ATTENDANCE_RECOVERY_DUE_DAYS", 5))


def recovery_watch_absences() -> int:
    return max(1, _int_env("ATTENDANCE_RECOVERY_WATCH_CONSECUTIVE_ABSENCES", 2))


def recovery_high_absences() -> int:
    return max(recovery_watch_absences(), _int_env("ATTENDANCE_RECOVERY_HIGH_CONSECUTIVE_ABSENCES", 3))


def recovery_critical_absences() -> int:
    return max(recovery_high_absences(), _int_env("ATTENDANCE_RECOVERY_CRITICAL_CONSECUTIVE_ABSENCES", 4))


def recovery_min_delivered_classes() -> int:
    return max(1, _int_env("ATTENDANCE_RECOVERY_MIN_DELIVERED_CLASSES", 2))


def _rms_first_response_hours() -> float:
    return max(1.0, _float_env("RMS_CASE_FIRST_RESPONSE_HOURS", 4.0))


def _rms_resolution_hours() -> float:
    return max(2.0, _float_env("RMS_CASE_RESOLUTION_HOURS", 24.0))


def _student_section(student: models.Student) -> str:
    return str(student.section or "").strip().upper()


def _parse_sections_json(raw_value: str | None) -> set[str]:
    if not raw_value:
        return set()
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return set()
    if not isinstance(parsed, list):
        return set()
    return {str(item or "").strip().upper() for item in parsed if str(item or "").strip()}


def _makeup_start(row: models.MakeUpClass) -> datetime:
    return datetime.combine(row.class_date, row.start_time)


def _makeup_end(row: models.MakeUpClass) -> datetime:
    return datetime.combine(row.class_date, row.end_time)


def _next_office_hour_slot(db: Session, *, course_id: int, now_dt: datetime) -> datetime | None:
    schedules = (
        db.query(models.ClassSchedule)
        .filter(
            models.ClassSchedule.course_id == int(course_id),
            models.ClassSchedule.is_active.is_(True),
        )
        .order_by(models.ClassSchedule.weekday.asc(), models.ClassSchedule.start_time.asc())
        .all()
    )
    if not schedules:
        return None
    for day_offset in range(0, 15):
        candidate_day = (now_dt + timedelta(days=day_offset)).date()
        weekday = candidate_day.weekday()
        for schedule in schedules:
            if int(schedule.weekday) != int(weekday):
                continue
            slot = datetime.combine(candidate_day, schedule.end_time) + timedelta(minutes=20)
            if slot > now_dt:
                return slot
    return None


def _recommended_makeup_class(
    db: Session,
    *,
    course_id: int,
    student_section: str,
    now_dt: datetime,
) -> models.MakeUpClass | None:
    rows = (
        db.query(models.MakeUpClass)
        .filter(
            models.MakeUpClass.course_id == int(course_id),
            models.MakeUpClass.is_active.is_(True),
        )
        .order_by(models.MakeUpClass.class_date.asc(), models.MakeUpClass.start_time.asc())
        .all()
    )
    for row in rows:
        if student_section and student_section not in _parse_sections_json(row.sections_json):
            continue
        if _makeup_start(row) < now_dt:
            continue
        return row
    return None


def _missed_remedials(
    db: Session,
    *,
    student_id: int,
    course_id: int,
    student_section: str,
    now_dt: datetime,
) -> tuple[int, set[int]]:
    rows = (
        db.query(models.MakeUpClass)
        .filter(
            models.MakeUpClass.course_id == int(course_id),
            models.MakeUpClass.is_active.is_(True),
        )
        .all()
    )
    if not rows:
        return 0, set()
    class_ids = [int(row.id) for row in rows]
    attended = {
        int(row[0])
        for row in (
            db.query(models.RemedialAttendance.makeup_class_id)
            .filter(
                models.RemedialAttendance.student_id == int(student_id),
                models.RemedialAttendance.makeup_class_id.in_(class_ids),
            )
            .all()
        )
        if row and row[0] is not None
    }
    missed = 0
    eligible_ids: set[int] = set()
    for row in rows:
        if student_section and student_section not in _parse_sections_json(row.sections_json):
            continue
        eligible_ids.add(int(row.id))
        if _makeup_end(row) > now_dt:
            continue
        if int(row.id) not in attended:
            missed += 1
    return missed, eligible_ids


def _consecutive_absences(records: list[models.AttendanceRecord]) -> int:
    streak = 0
    for row in records:
        if row.status == models.AttendanceStatus.ABSENT:
            streak += 1
            continue
        break
    return streak


def _last_absent_on(records: list[models.AttendanceRecord]) -> date | None:
    for row in records:
        if row.status == models.AttendanceStatus.ABSENT:
            return row.attendance_date
    return None


def _risk_level(
    *,
    attendance_percent: float,
    delivered_count: int,
    consecutive_absences: int,
) -> models.AttendanceRecoveryRiskLevel | None:
    if delivered_count < recovery_min_delivered_classes() and consecutive_absences < recovery_watch_absences():
        return None
    if attendance_percent <= recovery_critical_threshold() or consecutive_absences >= recovery_critical_absences():
        return models.AttendanceRecoveryRiskLevel.CRITICAL
    if attendance_percent <= recovery_high_threshold() or consecutive_absences >= recovery_high_absences():
        return models.AttendanceRecoveryRiskLevel.HIGH
    if attendance_percent <= recovery_watch_threshold() or consecutive_absences >= recovery_watch_absences():
        return models.AttendanceRecoveryRiskLevel.WATCH
    return None


def _recovery_summary(
    *,
    course: models.Course,
    attendance_percent: float,
    delivered_count: int,
    absent_count: int,
    consecutive_absences: int,
    next_makeup: models.MakeUpClass | None,
) -> str:
    base = (
        f"{course.code} attendance is {attendance_percent:.1f}% across {delivered_count} delivered classes, "
        f"with {absent_count} absences and {consecutive_absences} consecutive missed sessions."
    )
    if next_makeup is None:
        return f"{base} No remedial slot is scheduled yet, so the student should follow the catch-up task."
    return (
        f"{base} Next recovery slot: {next_makeup.class_date.isoformat()} "
        f"{next_makeup.start_time.strftime('%H:%M')}."
    )


def _recovery_due_at(
    *,
    now_dt: datetime,
    next_makeup: models.MakeUpClass | None,
    office_hour_slot: datetime | None,
) -> datetime:
    candidates = [now_dt + timedelta(days=recovery_due_days())]
    if next_makeup is not None:
        candidates.append(_makeup_start(next_makeup))
    if office_hour_slot is not None:
        candidates.append(office_hour_slot)
    return min(candidates)


def _auth_user_for_student(db: Session, student_id: int) -> models.AuthUser | None:
    return (
        db.query(models.AuthUser)
        .filter(models.AuthUser.student_id == int(student_id))
        .order_by(models.AuthUser.id.asc())
        .first()
    )


def _auth_user_for_faculty(db: Session, faculty_id: int | None) -> models.AuthUser | None:
    if not faculty_id:
        return None
    return (
        db.query(models.AuthUser)
        .filter(models.AuthUser.faculty_id == int(faculty_id))
        .order_by(models.AuthUser.id.asc())
        .first()
    )


def _active_plan(db: Session, *, student_id: int, course_id: int) -> models.AttendanceRecoveryPlan | None:
    return (
        db.query(models.AttendanceRecoveryPlan)
        .filter(
            models.AttendanceRecoveryPlan.student_id == int(student_id),
            models.AttendanceRecoveryPlan.course_id == int(course_id),
            models.AttendanceRecoveryPlan.status.in_(ACTIVE_PLAN_STATUSES),
        )
        .order_by(
            models.AttendanceRecoveryPlan.updated_at.desc(),
            models.AttendanceRecoveryPlan.id.desc(),
        )
        .first()
    )


def _plan_actions(db: Session, *, plan_id: int) -> list[models.AttendanceRecoveryAction]:
    return (
        db.query(models.AttendanceRecoveryAction)
        .filter(models.AttendanceRecoveryAction.plan_id == int(plan_id))
        .order_by(models.AttendanceRecoveryAction.id.asc())
        .all()
    )


def _find_action(
    actions: list[models.AttendanceRecoveryAction],
    *,
    action_type: models.AttendanceRecoveryActionType,
    target_makeup_class_id: int | None = None,
) -> models.AttendanceRecoveryAction | None:
    target_id = int(target_makeup_class_id or 0)
    for action in actions:
        if action.action_type != action_type:
            continue
        if action_type == models.AttendanceRecoveryActionType.REMEDIAL_SLOT:
            if int(action.target_makeup_class_id or 0) != target_id:
                continue
        return action
    return None


def _mirror_action(action: models.AttendanceRecoveryAction) -> None:
    return None


def _mirror_plan(plan: models.AttendanceRecoveryPlan) -> None:
    return None


def _recovery_case_subject(course: models.Course) -> str:
    return f"Attendance Recovery Autopilot - {course.code}"


def _recovery_case_note(
    *,
    student: models.Student,
    course: models.Course,
    attendance_percent: float,
    consecutive_absences: int,
    missed_remedials: int,
) -> str:
    return (
        f"Critical attendance recovery escalation for {student.name} in {course.code}. "
        f"Attendance is {attendance_percent:.1f}% with {consecutive_absences} consecutive absences "
        f"and {missed_remedials} missed remedial slots."
    )


def _log_rms_case_audit(
    db: Session,
    *,
    case_id: int,
    action: str,
    note: str,
    metadata: dict | None = None,
    from_status: models.RMSCaseStatus | None = None,
    to_status: models.RMSCaseStatus | None = None,
) -> models.RMSCaseAuditLog:
    row = models.RMSCaseAuditLog(
        case_id=int(case_id),
        actor_user_id=None,
        actor_role="system",
        action=str(action or "").strip()[:80] or "attendance_recovery",
        from_status=from_status,
        to_status=to_status,
        note=str(note or "").strip()[:600] or None,
        metadata_json=json.dumps(metadata or {}, separators=(",", ":"), sort_keys=True),
        created_at=datetime.utcnow(),
    )
    db.add(row)
    db.flush()
    return row


def _upsert_recovery_rms_case(
    db: Session,
    *,
    plan: models.AttendanceRecoveryPlan,
    student: models.Student,
    course: models.Course,
    faculty: models.Faculty | None,
) -> tuple[models.RMSCase, bool]:
    now_dt = datetime.utcnow()
    section = str(student.section or "UNASSIGNED").strip() or "UNASSIGNED"
    subject = _recovery_case_subject(course)
    note = _recovery_case_note(
        student=student,
        course=course,
        attendance_percent=float(plan.attendance_percent or 0.0),
        consecutive_absences=int(plan.consecutive_absences or 0),
        missed_remedials=int(plan.missed_remedials or 0),
    )

    query = db.query(models.RMSCase).filter(
        models.RMSCase.student_id == int(student.id),
        models.RMSCase.category == "Attendance",
        models.RMSCase.subject == subject,
        models.RMSCase.status.in_(ACTIVE_RMS_CASE_STATUSES),
    )
    if faculty is not None:
        query = query.filter(models.RMSCase.faculty_id == int(faculty.id))
    else:
        query = query.filter(models.RMSCase.faculty_id.is_(None))

    row = (
        query.order_by(models.RMSCase.updated_at.desc(), models.RMSCase.id.desc())
        .first()
    )
    if row is None:
        row = models.RMSCase(
            student_id=int(student.id),
            faculty_id=int(faculty.id) if faculty else None,
            section=section,
            category="Attendance",
            subject=subject,
            status=models.RMSCaseStatus.TRIAGE,
            priority=models.RMSCasePriority.CRITICAL,
            assigned_to_user_id=None,
            created_from_message_id=None,
            first_response_due_at=now_dt + timedelta(hours=_rms_first_response_hours()),
            resolution_due_at=now_dt + timedelta(hours=_rms_resolution_hours()),
            first_responded_at=None,
            last_message_at=now_dt,
            is_escalated=True,
            escalated_at=now_dt,
            escalation_reason=note,
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
            action="attendance_recovery_case_created",
            note=note,
            from_status=None,
            to_status=row.status,
            metadata={
                "plan_id": int(plan.id),
                "student_id": int(student.id),
                "course_id": int(course.id),
                "attendance_percent": float(plan.attendance_percent or 0.0),
                "risk_level": plan.risk_level.value,
            },
        )
        return row, True

    changed = False
    from_status = row.status
    if str(row.section or "") != section:
        row.section = section
        changed = True
    if row.priority != models.RMSCasePriority.CRITICAL:
        row.priority = models.RMSCasePriority.CRITICAL
        changed = True
    if row.status != models.RMSCaseStatus.TRIAGE:
        row.status = models.RMSCaseStatus.TRIAGE
        row.closed_at = None
        changed = True
    if not row.is_escalated:
        row.is_escalated = True
        changed = True
    if row.escalated_at is None:
        row.escalated_at = now_dt
        changed = True
    if str(row.escalation_reason or "") != note:
        row.escalation_reason = note
        changed = True
    if row.first_response_due_at is None:
        row.first_response_due_at = now_dt + timedelta(hours=_rms_first_response_hours())
        changed = True
    if row.resolution_due_at is None:
        row.resolution_due_at = now_dt + timedelta(hours=_rms_resolution_hours())
        changed = True
    row.last_message_at = now_dt
    row.updated_at = now_dt
    db.flush()

    if changed:
        _log_rms_case_audit(
            db,
            case_id=int(row.id),
            action="attendance_recovery_case_escalated",
            note=note,
            from_status=from_status,
            to_status=row.status,
            metadata={
                "plan_id": int(plan.id),
                "student_id": int(student.id),
                "course_id": int(course.id),
                "attendance_percent": float(plan.attendance_percent or 0.0),
                "risk_level": plan.risk_level.value,
            },
        )
    return row, False


def _recovery_event_scopes(*, student_id: int, faculty_id: int | None = None) -> set[str]:
    scopes = {
        f"student:{int(student_id)}",
        "role:admin",
    }
    if faculty_id:
        scopes.add(f"faculty:{int(faculty_id)}")
    return scopes


def _publish_recovery_plan_event(
    event_type: str,
    *,
    plan: models.AttendanceRecoveryPlan,
    rms_case_id: int | None = None,
) -> None:
    publish_domain_event(
        event_type,
        payload={
            "plan_id": int(plan.id),
            "student_id": int(plan.student_id),
            "course_id": int(plan.course_id),
            "faculty_id": int(plan.faculty_id) if plan.faculty_id else None,
            "risk_level": plan.risk_level.value,
            "status": plan.status.value,
            "attendance_percent": float(plan.attendance_percent or 0.0),
            "rms_case_id": int(rms_case_id) if rms_case_id else None,
        },
        scopes=_recovery_event_scopes(
            student_id=int(plan.student_id),
            faculty_id=int(plan.faculty_id) if plan.faculty_id else None,
        ),
        topics={"attendance", "admin"} if not rms_case_id else {"attendance", "admin", "rms"},
        source="attendance-recovery",
    )


def _publish_rms_case_event(event_type: str, *, case_row: models.RMSCase) -> None:
    publish_domain_event(
        event_type,
        payload={
            "case_id": int(case_row.id),
            "student_id": int(case_row.student_id),
            "faculty_id": int(case_row.faculty_id) if case_row.faculty_id else None,
            "status": case_row.status.value,
            "priority": case_row.priority.value,
            "category": case_row.category,
            "subject": case_row.subject,
        },
        scopes=_recovery_event_scopes(
            student_id=int(case_row.student_id),
            faculty_id=int(case_row.faculty_id) if case_row.faculty_id else None,
        ),
        topics={"rms", "admin"},
        source="attendance-recovery",
    )


def _format_notification_datetime(value: datetime | None) -> str:
    if value is None:
        return "Not scheduled"
    return value.strftime("%d %b %Y %I:%M %p")


def _makeup_notification_summary(row: models.MakeUpClass | None) -> str:
    if row is None:
        return "No remedial slot is currently assigned."
    return (
        f"{row.class_date.isoformat()} {row.start_time.strftime('%H:%M')}-{row.end_time.strftime('%H:%M')} "
        f"({row.class_mode or 'offline'})"
    )


def _build_recovery_notification_payload(
    *,
    action: models.AttendanceRecoveryAction,
    plan: models.AttendanceRecoveryPlan,
    student: models.Student,
    course: models.Course,
    notification_type: str,
    recipient_email: str,
    message: str,
    next_makeup: models.MakeUpClass | None,
    office_hour_slot: datetime | None,
) -> dict:
    return {
        "type": notification_type,
        "action_id": int(action.id),
        "student_id": int(student.id),
        "recipient_email": str(recipient_email or "").strip(),
        "student_name": str(student.name or "").strip() or f"Student #{student.id}",
        "registration_number": str(student.registration_number or "").strip(),
        "course_id": int(course.id),
        "course_code": str(course.code or "").strip(),
        "course_title": str(course.title or "").strip(),
        "risk_level": plan.risk_level.value,
        "attendance_percent": float(plan.attendance_percent or 0.0),
        "consecutive_absences": int(plan.consecutive_absences or 0),
        "missed_remedials": int(plan.missed_remedials or 0),
        "summary": str(plan.summary or "").strip(),
        "recovery_due_at": plan.recovery_due_at.isoformat() if plan.recovery_due_at else None,
        "suggested_remedial": _makeup_notification_summary(next_makeup),
        "office_hour_at": _format_notification_datetime(office_hour_slot),
        "message": str(message or "").strip(),
        "log_channel": (
            "attendance-recovery-faculty"
            if notification_type == "attendance_recovery_faculty_alert"
            else "attendance-recovery-parent"
        ),
    }


def _upsert_action(
    db: Session,
    *,
    plan: models.AttendanceRecoveryPlan,
    actions: list[models.AttendanceRecoveryAction],
    action_type: models.AttendanceRecoveryActionType,
    title: str,
    description: str,
    recipient_role: str,
    recipient_user_id: int | None = None,
    recipient_email: str | None = None,
    target_makeup_class_id: int | None = None,
    scheduled_for: datetime | None = None,
    metadata: dict | None = None,
    default_status: models.AttendanceRecoveryActionStatus = models.AttendanceRecoveryActionStatus.PENDING,
) -> models.AttendanceRecoveryAction:
    action = _find_action(
        actions,
        action_type=action_type,
        target_makeup_class_id=target_makeup_class_id,
    )
    now_dt = datetime.utcnow()
    payload = json.dumps(metadata or {}, separators=(",", ":"), sort_keys=True)
    if action is None:
        action = models.AttendanceRecoveryAction(
            plan_id=int(plan.id),
            action_type=action_type,
            status=default_status,
            title=title[:160],
            description=description[:900],
            recipient_role=recipient_role[:30],
            recipient_user_id=int(recipient_user_id) if recipient_user_id else None,
            recipient_email=(recipient_email or "").strip()[:120] or None,
            target_makeup_class_id=int(target_makeup_class_id) if target_makeup_class_id else None,
            scheduled_for=scheduled_for,
            metadata_json=payload,
            created_at=now_dt,
            updated_at=now_dt,
        )
        db.add(action)
        db.flush()
        actions.append(action)
    else:
        action.title = title[:160]
        action.description = description[:900]
        action.recipient_role = recipient_role[:30]
        action.recipient_user_id = int(recipient_user_id) if recipient_user_id else None
        action.recipient_email = (recipient_email or "").strip()[:120] or None
        action.target_makeup_class_id = int(target_makeup_class_id) if target_makeup_class_id else None
        action.scheduled_for = scheduled_for
        action.metadata_json = payload
        if action.status == models.AttendanceRecoveryActionStatus.CANCELLED:
            action.status = default_status
            action.completed_at = None
            action.outcome_note = None
        action.updated_at = now_dt
        db.flush()
    _mirror_action(action)
    return action


def _cancel_unused_actions(
    db: Session,
    *,
    plan: models.AttendanceRecoveryPlan,
    keep_action_ids: set[int],
) -> None:
    now_dt = datetime.utcnow()
    for action in _plan_actions(db, plan_id=int(plan.id)):
        if int(action.id) in keep_action_ids:
            continue
        if action.status in {
            models.AttendanceRecoveryActionStatus.COMPLETED,
            models.AttendanceRecoveryActionStatus.SKIPPED,
        }:
            continue
        action.status = models.AttendanceRecoveryActionStatus.CANCELLED
        action.updated_at = now_dt
        _mirror_action(action)


def _close_plan(
    db: Session,
    *,
    plan: models.AttendanceRecoveryPlan,
    summary: str,
) -> models.AttendanceRecoveryPlan:
    now_dt = datetime.utcnow()
    plan.status = models.AttendanceRecoveryPlanStatus.RECOVERED
    plan.summary = summary[:700]
    plan.last_evaluated_at = now_dt
    plan.updated_at = now_dt
    db.flush()
    for action in _plan_actions(db, plan_id=int(plan.id)):
        if action.status in {
            models.AttendanceRecoveryActionStatus.COMPLETED,
            models.AttendanceRecoveryActionStatus.SKIPPED,
        }:
            continue
        action.status = models.AttendanceRecoveryActionStatus.CANCELLED
        action.updated_at = now_dt
        _mirror_action(action)
    _mirror_plan(plan)
    return plan


def evaluate_attendance_recovery(
    db: Session,
    *,
    student_id: int,
    course_id: int,
) -> models.AttendanceRecoveryPlan | None:
    if not recovery_enabled():
        return None

    student = db.get(models.Student, int(student_id))
    course = db.get(models.Course, int(course_id))
    if student is None or course is None:
        return None
    if is_saarthi_course(course):
        return None

    now_dt = datetime.utcnow()
    faculty = db.get(models.Faculty, int(course.faculty_id)) if course.faculty_id else None
    records = (
        db.query(models.AttendanceRecord)
        .filter(
            models.AttendanceRecord.student_id == int(student_id),
            models.AttendanceRecord.course_id == int(course_id),
        )
        .order_by(
            models.AttendanceRecord.attendance_date.desc(),
            models.AttendanceRecord.updated_at.desc(),
            models.AttendanceRecord.id.desc(),
        )
        .all()
    )
    existing_plan = _active_plan(db, student_id=int(student_id), course_id=int(course_id))
    if not records:
        if existing_plan is not None:
            closed_plan = _close_plan(
                db,
                plan=existing_plan,
                summary=f"{course.code} attendance has no marked classes left in the ledger.",
            )
            _publish_recovery_plan_event("attendance.recovery.recovered", plan=closed_plan)
            return closed_plan
        return None

    delivered_count = len(records)
    present_count = sum(1 for row in records if row.status == models.AttendanceStatus.PRESENT)
    absent_count = sum(1 for row in records if row.status == models.AttendanceStatus.ABSENT)
    attendance_percent = round((present_count / delivered_count) * 100.0, 2) if delivered_count else 0.0
    consecutive_absences = _consecutive_absences(records)
    last_absent_on = _last_absent_on(records)
    student_section = _student_section(student)
    next_makeup = _recommended_makeup_class(
        db,
        course_id=int(course_id),
        student_section=student_section,
        now_dt=now_dt,
    )
    missed_remedials, _ = _missed_remedials(
        db,
        student_id=int(student_id),
        course_id=int(course_id),
        student_section=student_section,
        now_dt=now_dt,
    )
    office_hour_slot = _next_office_hour_slot(db, course_id=int(course_id), now_dt=now_dt)
    risk_level = _risk_level(
        attendance_percent=attendance_percent,
        delivered_count=delivered_count,
        consecutive_absences=consecutive_absences,
    )
    if risk_level is None:
        if existing_plan is None:
            return None
        closed_plan = _close_plan(
            db,
            plan=existing_plan,
            summary=(
                f"{course.code} attendance recovered to {attendance_percent:.1f}% "
                f"with no active intervention required."
            ),
        )
        _publish_recovery_plan_event("attendance.recovery.recovered", plan=closed_plan)
        return closed_plan

    faculty_user = _auth_user_for_faculty(db, int(course.faculty_id or 0))
    student_user = _auth_user_for_student(db, int(student_id))
    plan = existing_plan
    if plan is None:
        plan = models.AttendanceRecoveryPlan(
            student_id=int(student_id),
            course_id=int(course_id),
            faculty_id=int(course.faculty_id) if course.faculty_id else None,
            risk_level=risk_level,
            status=models.AttendanceRecoveryPlanStatus.ACTIVE,
            attendance_percent=attendance_percent,
            present_count=present_count,
            absent_count=absent_count,
            delivered_count=delivered_count,
            consecutive_absences=consecutive_absences,
            missed_remedials=missed_remedials,
            recommended_makeup_class_id=int(next_makeup.id) if next_makeup else None,
            parent_alert_allowed=False,
            recovery_due_at=None,
            summary="",
            last_absent_on=last_absent_on,
            last_evaluated_at=now_dt,
            created_at=now_dt,
            updated_at=now_dt,
        )
        db.add(plan)
        db.flush()

    parent_allowed = bool(
        student.parent_email
        and parent_alert_enabled()
        and risk_level == models.AttendanceRecoveryRiskLevel.CRITICAL
    )
    plan.risk_level = risk_level
    plan.status = (
        models.AttendanceRecoveryPlanStatus.ESCALATED
        if risk_level == models.AttendanceRecoveryRiskLevel.CRITICAL
        else models.AttendanceRecoveryPlanStatus.ACTIVE
    )
    plan.faculty_id = int(course.faculty_id) if course.faculty_id else None
    plan.attendance_percent = attendance_percent
    plan.present_count = present_count
    plan.absent_count = absent_count
    plan.delivered_count = delivered_count
    plan.consecutive_absences = consecutive_absences
    plan.missed_remedials = missed_remedials
    plan.recommended_makeup_class_id = int(next_makeup.id) if next_makeup else None
    plan.parent_alert_allowed = parent_allowed
    plan.recovery_due_at = _recovery_due_at(
        now_dt=now_dt,
        next_makeup=next_makeup,
        office_hour_slot=office_hour_slot,
    )
    plan.summary = _recovery_summary(
        course=course,
        attendance_percent=attendance_percent,
        delivered_count=delivered_count,
        absent_count=absent_count,
        consecutive_absences=consecutive_absences,
        next_makeup=next_makeup,
    )[:700]
    plan.last_absent_on = last_absent_on
    plan.last_evaluated_at = now_dt
    plan.updated_at = now_dt
    db.flush()

    actions = _plan_actions(db, plan_id=int(plan.id))
    keep_action_ids: set[int] = set()

    faculty_title = f"Optional faculty note for {student.name}"
    faculty_description = (
        f"{student.name} ({student.registration_number or 'unregistered'}) moved into attendance watch "
        f"status in {course.code} at {attendance_percent:.1f}%. Review the suggested remedial guidance."
    )
    if risk_level == models.AttendanceRecoveryRiskLevel.HIGH:
        faculty_title = f"Faculty intervention required for {student.name}"
        faculty_description = (
            f"{student.name} ({student.registration_number or 'unregistered'}) is below the safe attendance "
            f"threshold in {course.code} at {attendance_percent:.1f}%. Review the recovery plan and follow up."
        )
    elif risk_level == models.AttendanceRecoveryRiskLevel.CRITICAL:
        faculty_title = f"Escalated faculty intervention required for {student.name}"
        faculty_description = (
            f"{student.name} ({student.registration_number or 'unregistered'}) is at critical attendance risk "
            f"in {course.code} ({attendance_percent:.1f}%). Admin escalation and a structured recovery plan are active."
        )

    faculty_action = _upsert_action(
        db,
        plan=plan,
        actions=actions,
        action_type=models.AttendanceRecoveryActionType.FACULTY_NUDGE,
        title=faculty_title,
        description=faculty_description,
        recipient_role="faculty",
        recipient_user_id=int(faculty_user.id) if faculty_user else None,
        recipient_email=faculty.email if faculty else None,
        scheduled_for=now_dt,
        metadata={
            "student_id": int(student.id),
            "course_id": int(course.id),
            "risk_level": risk_level.value,
            "optional": risk_level == models.AttendanceRecoveryRiskLevel.WATCH,
        },
        default_status=models.AttendanceRecoveryActionStatus.PENDING,
    )
    keep_action_ids.add(int(faculty_action.id))
    if faculty_action.created_at == faculty_action.updated_at and faculty is not None:
        enqueue_notification_after_commit(
            db,
            _build_recovery_notification_payload(
                action=faculty_action,
                plan=plan,
                student=student,
                course=course,
                notification_type="attendance_recovery_faculty_alert",
                recipient_email=faculty.email,
                message=faculty_action.description,
                next_makeup=next_makeup,
                office_hour_slot=office_hour_slot,
            ),
        )

    if next_makeup is not None:
        remedial_mandatory = risk_level in {
            models.AttendanceRecoveryRiskLevel.HIGH,
            models.AttendanceRecoveryRiskLevel.CRITICAL,
        }
        remedial_action = _upsert_action(
            db,
            plan=plan,
            actions=actions,
            action_type=models.AttendanceRecoveryActionType.REMEDIAL_SLOT,
            title=(
                f"{'Mandatory remedial recovery slot' if remedial_mandatory else 'Suggested recovery slot'} "
                f"for {course.code}"
            ),
            description=(
                f"{'Attend' if remedial_mandatory else 'Consider attending'} the remedial session on "
                f"{next_makeup.class_date.isoformat()} at {next_makeup.start_time.strftime('%H:%M')} "
                f"to recover the missed learning window."
            ),
            recipient_role="student",
            recipient_user_id=int(student_user.id) if student_user else None,
            recipient_email=student.email,
            target_makeup_class_id=int(next_makeup.id),
            scheduled_for=_makeup_start(next_makeup),
            metadata={
                "course_id": int(course.id),
                "makeup_class_id": int(next_makeup.id),
                "class_mode": next_makeup.class_mode,
                "mandatory": remedial_mandatory,
            },
        )
        keep_action_ids.add(int(remedial_action.id))

    if risk_level in {
        models.AttendanceRecoveryRiskLevel.HIGH,
        models.AttendanceRecoveryRiskLevel.CRITICAL,
    }:
        office_action = _upsert_action(
            db,
            plan=plan,
            actions=actions,
            action_type=models.AttendanceRecoveryActionType.OFFICE_HOUR_INVITE,
            title=f"Faculty check-in for {course.code}",
            description=(
                "Use the suggested office-hour check-in to review missed concepts, identify blockers, "
                "and confirm the recovery plan."
            ),
            recipient_role="student",
            recipient_user_id=int(student_user.id) if student_user else None,
            recipient_email=student.email,
            scheduled_for=office_hour_slot,
            metadata={
                "course_id": int(course.id),
                "requires_acknowledgement": True,
            },
        )
        keep_action_ids.add(int(office_action.id))

        catchup_action = _upsert_action(
            db,
            plan=plan,
            actions=actions,
            action_type=models.AttendanceRecoveryActionType.CATCH_UP_TASK,
            title=(
                f"{'Complete structured catch-up plan' if risk_level == models.AttendanceRecoveryRiskLevel.CRITICAL else 'Acknowledge and complete recovery task'} "
                f"for {course.code}"
            ),
            description=(
                "Review the latest missed topic, collect notes from the last class, and confirm your next "
                "attendance/recovery step in the portal."
                if risk_level == models.AttendanceRecoveryRiskLevel.HIGH
                else "This critical plan requires a structured catch-up response: review the missed topic, collect notes, and confirm the recovery schedule."
            ),
            recipient_role="student",
            recipient_user_id=int(student_user.id) if student_user else None,
            recipient_email=student.email,
            scheduled_for=plan.recovery_due_at,
            metadata={
                "course_id": int(course.id),
                "due_at": plan.recovery_due_at.isoformat() if plan.recovery_due_at else None,
                "requires_acknowledgement": True,
                "structured": risk_level == models.AttendanceRecoveryRiskLevel.CRITICAL,
            },
        )
        keep_action_ids.add(int(catchup_action.id))

    escalated_case: models.RMSCase | None = None
    escalated_case_created = False
    if risk_level == models.AttendanceRecoveryRiskLevel.CRITICAL:
        escalated_case, escalated_case_created = _upsert_recovery_rms_case(
            db,
            plan=plan,
            student=student,
            course=course,
            faculty=faculty,
        )

    if parent_allowed and risk_level == models.AttendanceRecoveryRiskLevel.CRITICAL:
        parent_action = _upsert_action(
            db,
            plan=plan,
            actions=actions,
            action_type=models.AttendanceRecoveryActionType.PARENT_ALERT,
            title=f"Parent attendance alert for {student.name}",
            description=(
                f"{student.name} has dropped to {attendance_percent:.1f}% in {course.code}. "
                "The recovery plan is active and requires follow-up."
            ),
            recipient_role="parent",
            recipient_email=student.parent_email,
            scheduled_for=now_dt,
            metadata={"student_id": int(student.id), "course_id": int(course.id), "risk_level": risk_level.value},
            default_status=models.AttendanceRecoveryActionStatus.PENDING,
        )
        keep_action_ids.add(int(parent_action.id))
        if parent_action.created_at == parent_action.updated_at:
            enqueue_notification_after_commit(
                db,
                _build_recovery_notification_payload(
                    action=parent_action,
                    plan=plan,
                    student=student,
                    course=course,
                    notification_type="attendance_recovery_parent_alert",
                    recipient_email=student.parent_email or "",
                    message=parent_action.description,
                    next_makeup=next_makeup,
                    office_hour_slot=office_hour_slot,
                ),
            )

    _cancel_unused_actions(db, plan=plan, keep_action_ids=keep_action_ids)
    _mirror_plan(plan)
    _publish_recovery_plan_event(
        "attendance.recovery.updated",
        plan=plan,
        rms_case_id=int(escalated_case.id) if escalated_case else None,
    )
    if escalated_case is not None:
        _publish_rms_case_event(
            "rms.case.created" if escalated_case_created else "rms.case.escalated",
            case_row=escalated_case,
        )
    return plan


def recompute_attendance_recovery_scope(
    db: Session,
    *,
    student_id: int | None = None,
    course_id: int | None = None,
    limit: int = 500,
) -> dict[str, int]:
    query = db.query(models.AttendanceRecord.student_id, models.AttendanceRecord.course_id).distinct()
    if student_id is not None:
        query = query.filter(models.AttendanceRecord.student_id == int(student_id))
    if course_id is not None:
        query = query.filter(models.AttendanceRecord.course_id == int(course_id))

    pairs = (
        query.order_by(
            models.AttendanceRecord.student_id.asc(),
            models.AttendanceRecord.course_id.asc(),
        )
        .limit(max(1, int(limit)))
        .all()
    )
    evaluated = 0
    created_or_updated = 0
    for sid, cid in pairs:
        before_plan = _active_plan(db, student_id=int(sid), course_id=int(cid))
        before_id = int(before_plan.id) if before_plan else 0
        plan = evaluate_attendance_recovery(db, student_id=int(sid), course_id=int(cid))
        evaluated += 1
        if plan is not None and (before_id == 0 or int(plan.id) == before_id):
            created_or_updated += 1
    return {"evaluated": evaluated, "plans_touched": created_or_updated}


def get_student_recovery_plans(
    db: Session,
    *,
    student_id: int,
    include_resolved: bool = False,
    limit: int = 20,
) -> list[models.AttendanceRecoveryPlan]:
    severity_rank = {
        models.AttendanceRecoveryRiskLevel.CRITICAL: 0,
        models.AttendanceRecoveryRiskLevel.HIGH: 1,
        models.AttendanceRecoveryRiskLevel.WATCH: 2,
    }
    query = db.query(models.AttendanceRecoveryPlan).filter(
        models.AttendanceRecoveryPlan.student_id == int(student_id)
    )
    if not include_resolved:
        query = query.filter(models.AttendanceRecoveryPlan.status.in_(ACTIVE_PLAN_STATUSES))
    rows = query.all()
    ordered = sorted(
        rows,
        key=lambda row: (
            severity_rank.get(row.risk_level, 3),
            row.recovery_due_at or datetime.max,
            row.updated_at or datetime.min,
        ),
    )
    return ordered[: max(1, int(limit))]


def get_faculty_recovery_plans(
    db: Session,
    *,
    faculty_id: int,
    course_id: int | None = None,
    include_resolved: bool = False,
    limit: int = 50,
) -> list[models.AttendanceRecoveryPlan]:
    severity_rank = {
        models.AttendanceRecoveryRiskLevel.CRITICAL: 0,
        models.AttendanceRecoveryRiskLevel.HIGH: 1,
        models.AttendanceRecoveryRiskLevel.WATCH: 2,
    }
    query = db.query(models.AttendanceRecoveryPlan).filter(
        models.AttendanceRecoveryPlan.faculty_id == int(faculty_id)
    )
    if course_id is not None:
        query = query.filter(models.AttendanceRecoveryPlan.course_id == int(course_id))
    if not include_resolved:
        query = query.filter(models.AttendanceRecoveryPlan.status.in_(ACTIVE_PLAN_STATUSES))
    rows = query.all()
    ordered = sorted(
        rows,
        key=lambda row: (
            severity_rank.get(row.risk_level, 3),
            row.recovery_due_at or datetime.max,
            row.updated_at or datetime.min,
        ),
    )
    return ordered[: max(1, int(limit))]


def get_admin_recovery_plans(
    db: Session,
    *,
    include_resolved: bool = False,
    limit: int = 80,
) -> list[models.AttendanceRecoveryPlan]:
    severity_rank = {
        models.AttendanceRecoveryRiskLevel.CRITICAL: 0,
        models.AttendanceRecoveryRiskLevel.HIGH: 1,
        models.AttendanceRecoveryRiskLevel.WATCH: 2,
    }
    query = db.query(models.AttendanceRecoveryPlan)
    if not include_resolved:
        query = query.filter(models.AttendanceRecoveryPlan.status.in_(ACTIVE_PLAN_STATUSES))
    rows = query.all()
    ordered = sorted(
        rows,
        key=lambda row: (
            severity_rank.get(row.risk_level, 3),
            row.recovery_due_at or datetime.max,
            row.updated_at or datetime.min,
        ),
    )
    return ordered[: max(1, int(limit))]


def get_plan_actions(db: Session, *, plan_id: int) -> list[models.AttendanceRecoveryAction]:
    return _plan_actions(db, plan_id=int(plan_id))


def update_student_recovery_action(
    db: Session,
    *,
    action_id: int,
    student_id: int,
    new_status: models.AttendanceRecoveryActionStatus,
    note: str | None = None,
) -> models.AttendanceRecoveryAction:
    action = db.get(models.AttendanceRecoveryAction, int(action_id))
    if action is None:
        raise LookupError("Attendance recovery action not found.")
    plan = db.get(models.AttendanceRecoveryPlan, int(action.plan_id))
    if plan is None or int(plan.student_id) != int(student_id):
        raise PermissionError("Student cannot update this recovery action.")
    if action.action_type not in STUDENT_FACING_ACTIONS:
        raise PermissionError("Only student-facing recovery actions can be updated by the student.")
    if new_status not in {
        models.AttendanceRecoveryActionStatus.ACKNOWLEDGED,
        models.AttendanceRecoveryActionStatus.COMPLETED,
    }:
        raise ValueError("Unsupported recovery action status update.")
    if action.status in {
        models.AttendanceRecoveryActionStatus.CANCELLED,
        models.AttendanceRecoveryActionStatus.SKIPPED,
    }:
        raise ValueError("Recovery action is no longer active.")

    now_dt = datetime.utcnow()
    action.status = new_status
    if new_status == models.AttendanceRecoveryActionStatus.COMPLETED:
        action.completed_at = now_dt
    if note:
        action.outcome_note = str(note).strip()[:600]
    action.updated_at = now_dt
    db.flush()
    _mirror_action(action)
    return action


def complete_remedial_recovery_action(
    db: Session,
    *,
    student_id: int,
    makeup_class_id: int,
) -> int:
    plans = (
        db.query(models.AttendanceRecoveryPlan)
        .filter(
            models.AttendanceRecoveryPlan.student_id == int(student_id),
            models.AttendanceRecoveryPlan.status.in_(ACTIVE_PLAN_STATUSES),
        )
        .all()
    )
    if not plans:
        return 0
    plan_ids = [int(plan.id) for plan in plans]
    actions = (
        db.query(models.AttendanceRecoveryAction)
        .filter(
            models.AttendanceRecoveryAction.plan_id.in_(plan_ids),
            models.AttendanceRecoveryAction.action_type == models.AttendanceRecoveryActionType.REMEDIAL_SLOT,
            models.AttendanceRecoveryAction.target_makeup_class_id == int(makeup_class_id),
        )
        .all()
    )
    updated = 0
    now_dt = datetime.utcnow()
    for action in actions:
        if action.status == models.AttendanceRecoveryActionStatus.COMPLETED:
            continue
        action.status = models.AttendanceRecoveryActionStatus.COMPLETED
        action.completed_at = now_dt
        action.outcome_note = "Student attended the suggested remedial session."
        action.updated_at = now_dt
        _mirror_action(action)
        updated += 1
    return updated
