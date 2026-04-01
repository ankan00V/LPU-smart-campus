import logging
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth_utils import require_roles
from ..database import get_db
from ..mongo import get_mongo_db, mirror_document
from ..otp_delivery import send_notification_email
from ..realtime_bus import publish_domain_event
from ..workers import enqueue_notification
from .remedial import _normalize_sections, _faculty_allowed_sections, _student_section

router = APIRouter(prefix="/messages", tags=["Faculty Messages"])
logger = logging.getLogger(__name__)
SUPPORT_QUERY_CATEGORIES = [
    schemas.SupportQueryCategory.ATTENDANCE,
    schemas.SupportQueryCategory.ACADEMICS,
    schemas.SupportQueryCategory.DISCREPANCY,
    schemas.SupportQueryCategory.OTHER,
]

RMS_TRACKER_FIRST_RESPONSE_HOURS = 4.0
RMS_TRACKER_RESOLUTION_HOURS = 24.0


def _normalize_message_type(value: str) -> str:
    label = re.sub(r"\s+", " ", str(value or "").strip())
    if not label:
        return "Announcement"
    title = label.title()
    if title not in {"Announcement", "General", "Remedial"}:
        return "Announcement"
    return title


def _normalize_support_category(value: Any) -> schemas.SupportQueryCategory:
    if isinstance(value, schemas.SupportQueryCategory):
        return value
    raw = re.sub(r"\s+", " ", str(value or "").strip()).lower()
    if raw in {"attendance", "attendance issue"}:
        return schemas.SupportQueryCategory.ATTENDANCE
    if raw in {"academics", "academic", "academic issue"}:
        return schemas.SupportQueryCategory.ACADEMICS
    if raw in {"discrepancy", "discrepancies"}:
        return schemas.SupportQueryCategory.DISCREPANCY
    return schemas.SupportQueryCategory.OTHER


def _safe_student_section(student: models.Student | None) -> str:
    if not student:
        return "UNASSIGNED"
    token = re.sub(r"\s+", "", str(student.section or "").strip().upper())
    return token or "UNASSIGNED"


def _normalize_registration_number(value: str | None) -> str | None:
    normalized = re.sub(r"\s+", "", str(value or "").strip().upper())
    return normalized or None


def _resolve_student_for_direct_email(
    db: Session,
    *,
    student_id: int | None,
    registration_number: str | None,
    email: str | None,
) -> models.Student:
    if student_id:
        student = db.get(models.Student, int(student_id))
        if not student:
            raise HTTPException(status_code=404, detail="Student not found.")
        return student
    if registration_number:
        reg = _normalize_registration_number(registration_number)
        if reg:
            student = (
                db.query(models.Student)
                .filter(func.upper(models.Student.registration_number) == reg)
                .first()
            )
            if student:
                return student
        raise HTTPException(status_code=404, detail="Student not found for registration number.")
    if email:
        normalized = str(email or "").strip().lower()
        if normalized:
            student = (
                db.query(models.Student)
                .filter(func.lower(models.Student.email) == normalized)
                .first()
            )
            if student:
                return student
        raise HTTPException(status_code=404, detail="Student not found for email.")
    raise HTTPException(status_code=400, detail="Provide student_id, registration_number, or email.")


def _student_can_contact_faculty(db: Session, *, student_id: int, faculty_id: int) -> bool:
    teaches_student = (
        db.query(models.Enrollment.id)
        .join(models.Course, models.Course.id == models.Enrollment.course_id)
        .filter(
            models.Enrollment.student_id == int(student_id),
            models.Course.faculty_id == int(faculty_id),
        )
        .first()
        is not None
    )
    if teaches_student:
        return True
    has_support_thread = (
        db.query(models.SupportQueryMessage.id)
        .filter(
            models.SupportQueryMessage.student_id == int(student_id),
            models.SupportQueryMessage.faculty_id == int(faculty_id),
        )
        .first()
        is not None
    )
    if has_support_thread:
        return True
    has_prior_announcement = (
        db.query(models.FacultyMessage.id)
        .filter(
            models.FacultyMessage.student_id == int(student_id),
            models.FacultyMessage.faculty_id == int(faculty_id),
        )
        .first()
        is not None
    )
    return has_prior_announcement


def _faculty_can_contact_student(
    db: Session,
    *,
    faculty_id: int,
    student: models.Student | None,
) -> bool:
    if not student:
        return False
    faculty = db.get(models.Faculty, int(faculty_id))
    allowed_sections = _faculty_allowed_sections(faculty)
    student_section = _safe_student_section(student)
    if allowed_sections:
        return student_section in allowed_sections
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


def _serialize_support_query_message(row: models.SupportQueryMessage) -> schemas.SupportQueryMessageOut:
    return schemas.SupportQueryMessageOut(
        id=int(row.id),
        student_id=int(row.student_id),
        faculty_id=int(row.faculty_id),
        section=str(row.section or ""),
        category=_normalize_support_category(row.category),
        subject=str(row.subject or "").strip() or "General Query",
        message=str(row.message or "").strip(),
        sender_role=str(row.sender_role or "").strip().lower() or "student",
        created_at=row.created_at or datetime.utcnow(),
        read_at=row.read_at,
    )


def _safe_json_load_dict(raw_value: str | None) -> dict[str, Any]:
    raw = str(raw_value or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _serialize_rms_case_out_for_student(
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
        faculty_id=(int(case_row.faculty_id) if case_row.faculty_id else None),
        faculty_name=(str(getattr(faculty, "name", "") or "").strip() or None),
        section=str(case_row.section or ""),
        category=_normalize_support_category(case_row.category),
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


def _serialize_rms_case_audit(row: models.RMSCaseAuditLog) -> schemas.RMSCaseAuditOut:
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


def _status_from_action_marker(raw_message: str | None) -> models.RMSCaseStatus | None:
    message = str(raw_message or "").strip()
    if not message.startswith("[[RMS_ACTION]]"):
        return None
    raw_payload = message[len("[[RMS_ACTION]]"):].strip()
    if not raw_payload:
        return None
    try:
        payload = json.loads(raw_payload)
    except (TypeError, json.JSONDecodeError):
        return None
    action = str(payload.get("action", "")).strip().lower()
    if action == "approve":
        return models.RMSCaseStatus.APPROVED
    if action == "disapprove":
        return models.RMSCaseStatus.REJECTED
    if action == "schedule":
        return models.RMSCaseStatus.ASSIGNED
    return None


def _priority_from_category(category: schemas.SupportQueryCategory) -> models.RMSCasePriority:
    if category == schemas.SupportQueryCategory.DISCREPANCY:
        return models.RMSCasePriority.HIGH
    if category == schemas.SupportQueryCategory.ATTENDANCE:
        return models.RMSCasePriority.MEDIUM
    return models.RMSCasePriority.LOW


def _ensure_student_rms_cases(db: Session, *, student_id: int, limit: int = 800) -> int:
    rows = (
        db.query(models.SupportQueryMessage)
        .filter(models.SupportQueryMessage.student_id == int(student_id))
        .order_by(models.SupportQueryMessage.created_at.desc(), models.SupportQueryMessage.id.desc())
        .limit(max(80, min(int(limit), 2000)))
        .all()
    )
    if not rows:
        return 0

    now_dt = datetime.utcnow()
    created = 0
    grouped_latest: dict[tuple[int, str, str], models.SupportQueryMessage] = {}
    for row in rows:
        category = _normalize_support_category(row.category).value
        subject = str(row.subject or "").strip() or f"{category} Query"
        key = (int(row.faculty_id), category, subject)
        if key not in grouped_latest:
            grouped_latest[key] = row

    for (faculty_id, category, subject), latest in grouped_latest.items():
        existing = (
            db.query(models.RMSCase)
            .filter(
                models.RMSCase.student_id == int(student_id),
                models.RMSCase.faculty_id == int(faculty_id),
                models.RMSCase.category == category,
                models.RMSCase.subject == subject,
                models.RMSCase.status != models.RMSCaseStatus.CLOSED,
            )
            .order_by(models.RMSCase.updated_at.desc(), models.RMSCase.id.desc())
            .first()
        )
        if existing:
            if latest.created_at and (not existing.last_message_at or latest.created_at > existing.last_message_at):
                existing.last_message_at = latest.created_at
                existing.updated_at = now_dt
            continue

        category_enum = _normalize_support_category(category)
        marker_status = _status_from_action_marker(latest.message)
        case_row = models.RMSCase(
            student_id=int(student_id),
            faculty_id=int(faculty_id),
            section=str(latest.section or "UNASSIGNED"),
            category=category_enum.value,
            subject=subject,
            status=marker_status or models.RMSCaseStatus.NEW,
            priority=_priority_from_category(category_enum),
            assigned_to_user_id=None,
            created_from_message_id=int(latest.id),
            first_response_due_at=now_dt + timedelta(hours=RMS_TRACKER_FIRST_RESPONSE_HOURS),
            resolution_due_at=now_dt + timedelta(hours=RMS_TRACKER_RESOLUTION_HOURS),
            first_responded_at=(
                latest.created_at
                if str(latest.sender_role or "").strip().lower() != models.UserRole.STUDENT.value
                else None
            ),
            last_message_at=latest.created_at or now_dt,
            is_escalated=False,
            escalated_at=None,
            escalation_reason=None,
            closed_at=None,
            reopened_count=0,
            created_at=now_dt,
            updated_at=now_dt,
        )
        db.add(case_row)
        db.flush()
        db.add(
            models.RMSCaseAuditLog(
                case_id=int(case_row.id),
                actor_user_id=None,
                actor_role="system",
                action="case_created_from_thread",
                from_status=None,
                to_status=case_row.status,
                note="Case auto-created from support thread.",
                evidence_ref=None,
                metadata_json=json.dumps({"message_id": int(latest.id)}, separators=(",", ":"), ensure_ascii=True),
                created_at=now_dt,
            )
        )
        created += 1

    if created:
        db.commit()
    else:
        db.flush()
    return created


def _build_support_contacts_for_student(
    db: Session,
    *,
    student_id: int,
) -> tuple[list[schemas.SupportQueryContactOut], dict[int, models.Faculty]]:
    course_rows = (
        db.query(models.Course.faculty_id, models.Course.code)
        .join(models.Enrollment, models.Enrollment.course_id == models.Course.id)
        .filter(
            models.Enrollment.student_id == int(student_id),
            models.Course.faculty_id.isnot(None),
        )
        .all()
    )
    faculty_ids = {int(row.faculty_id) for row in course_rows if row.faculty_id}
    course_map: dict[int, set[str]] = defaultdict(set)
    for row in course_rows:
        if row.faculty_id:
            course_map[int(row.faculty_id)].add(str(row.code or "").strip().upper())

    prior_ids = {
        int(value)
        for (value,) in db.query(models.FacultyMessage.faculty_id)
        .filter(models.FacultyMessage.student_id == int(student_id))
        .distinct()
        .all()
        if value
    }
    thread_ids = {
        int(value)
        for (value,) in db.query(models.SupportQueryMessage.faculty_id)
        .filter(models.SupportQueryMessage.student_id == int(student_id))
        .distinct()
        .all()
        if value
    }
    faculty_ids.update(prior_ids)
    faculty_ids.update(thread_ids)

    faculty_rows = (
        db.query(models.Faculty)
        .filter(models.Faculty.id.in_(sorted(faculty_ids)))
        .all()
        if faculty_ids
        else []
    )
    faculty_map = {int(row.id): row for row in faculty_rows}
    contacts: list[schemas.SupportQueryContactOut] = []
    for faculty in sorted(faculty_rows, key=lambda row: (str(row.name or "").lower(), int(row.id))):
        tokens = sorted(course_map.get(int(faculty.id), set()))
        descriptor = f"Courses: {', '.join(tokens[:4])}" if tokens else "Message for attendance or academic query"
        if len(tokens) > 4:
            descriptor = f"{descriptor}, +{len(tokens) - 4} more"
        contacts.append(
            schemas.SupportQueryContactOut(
                id=int(faculty.id),
                name=str(faculty.name or f"Faculty #{faculty.id}"),
                section=(str(faculty.section or "").strip() or None),
                descriptor=descriptor,
            )
        )
    return contacts, faculty_map


def _build_support_contacts_for_faculty(
    db: Session,
    *,
    faculty_id: int,
) -> tuple[list[schemas.SupportQueryContactOut], dict[int, models.Student]]:
    faculty = db.get(models.Faculty, int(faculty_id))
    allowed_sections = _faculty_allowed_sections(faculty)
    student_rows: list[models.Student]
    if allowed_sections:
        student_rows = (
            db.query(models.Student)
            .filter(models.Student.section.in_(sorted(allowed_sections)))
            .all()
        )
    else:
        student_rows = (
            db.query(models.Student)
            .join(models.Enrollment, models.Enrollment.student_id == models.Student.id)
            .join(models.Course, models.Course.id == models.Enrollment.course_id)
            .filter(models.Course.faculty_id == int(faculty_id))
            .distinct()
            .all()
        )

    thread_student_ids = {
        int(value)
        for (value,) in db.query(models.SupportQueryMessage.student_id)
        .filter(models.SupportQueryMessage.faculty_id == int(faculty_id))
        .distinct()
        .all()
        if value
    }
    student_ids = {int(row.id) for row in student_rows}
    student_ids.update(thread_student_ids)
    if student_ids and len(student_ids) != len(student_rows):
        extra_rows = db.query(models.Student).filter(models.Student.id.in_(sorted(student_ids))).all()
        student_rows = extra_rows

    student_map = {int(row.id): row for row in student_rows}
    contacts: list[schemas.SupportQueryContactOut] = []
    for student in sorted(student_rows, key=lambda row: (str(row.name or "").lower(), int(row.id))):
        if not _faculty_can_contact_student(db, faculty_id=int(faculty_id), student=student):
            continue
        reg = str(student.registration_number or "").strip().upper()
        section = _safe_student_section(student)
        descriptor = f"Section {section}"
        if reg:
            descriptor = f"{descriptor} • {reg}"
        contacts.append(
            schemas.SupportQueryContactOut(
                id=int(student.id),
                name=str(student.name or f"Student #{student.id}"),
                section=section if section != "UNASSIGNED" else None,
                descriptor=descriptor,
            )
        )
    return contacts, student_map


def _build_support_threads(
    rows: list[models.SupportQueryMessage],
    *,
    current_user: models.AuthUser,
    faculty_map: dict[int, models.Faculty],
    student_map: dict[int, models.Student],
) -> list[schemas.SupportQueryThreadOut]:
    role_value = str(current_user.role.value)
    grouped: dict[tuple[int, str], dict[str, Any]] = {}
    for row in rows:
        category = _normalize_support_category(row.category)
        if current_user.role == models.UserRole.STUDENT:
            counterparty_id = int(row.faculty_id)
            counterparty = faculty_map.get(counterparty_id)
            counterparty_name = str(counterparty.name if counterparty else f"Faculty #{counterparty_id}")
            section = str(counterparty.section or "").strip() if counterparty else ""
        else:
            counterparty_id = int(row.student_id)
            counterparty = student_map.get(counterparty_id)
            counterparty_name = str(counterparty.name if counterparty else f"Student #{counterparty_id}")
            section = _safe_student_section(counterparty) if counterparty else ""
            if section == "UNASSIGNED":
                section = ""

        key = (counterparty_id, category.value)
        summary = grouped.get(key)
        if summary is None:
            summary = {
                "counterparty_id": counterparty_id,
                "counterparty_name": counterparty_name,
                "section": section or None,
                "category": category,
                "subject": str(row.subject or "").strip() or f"{category.value} Query",
                "last_message": str(row.message or "").strip(),
                "last_sender_role": str(row.sender_role or "").strip().lower() or role_value,
                "last_created_at": row.created_at or datetime.utcnow(),
                "unread_count": 0,
            }
            grouped[key] = summary
        if str(row.sender_role or "").strip().lower() != role_value and row.read_at is None:
            summary["unread_count"] += 1

    output = [
        schemas.SupportQueryThreadOut(**payload)
        for payload in sorted(
            grouped.values(),
            key=lambda item: item["last_created_at"],
            reverse=True,
        )
    ]
    return output


@router.post("/send", response_model=schemas.MessageResponse)
def send_faculty_message(
    payload: schemas.FacultyMessageSend,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    if current_user.role == models.UserRole.FACULTY and not current_user.faculty_id:
        raise HTTPException(status_code=403, detail="Faculty account is not linked correctly.")
    faculty_id = int(current_user.faculty_id or 0)
    if current_user.role == models.UserRole.ADMIN and not faculty_id:
        raise HTTPException(status_code=400, detail="Faculty context is required for announcements.")

    sections = _normalize_sections(payload.sections)
    if current_user.role == models.UserRole.FACULTY:
        faculty = db.get(models.Faculty, faculty_id)
        allowed_sections = _faculty_allowed_sections(faculty)
        if allowed_sections and not set(sections).issubset(allowed_sections):
            raise HTTPException(status_code=403, detail="Selected section(s) are outside your allocated scope.")

    message_type = _normalize_message_type(payload.message_type)
    message_text = str(payload.message or "").strip()
    if not message_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    students = db.query(models.Student).filter(models.Student.section.in_(sections)).all()
    if not students:
        return schemas.MessageResponse(message="No students found for target section(s).")

    now_dt = datetime.utcnow()
    created_rows = []
    for student in students:
        student_section = _student_section(student)
        if student_section not in sections:
            continue
        row = models.FacultyMessage(
            faculty_id=faculty_id,
            student_id=student.id,
            section=student_section,
            message_type=message_type,
            message=message_text,
            created_at=now_dt,
        )
        db.add(row)
        created_rows.append(row)

    db.commit()

    try:
        mongo_db = get_mongo_db(required=False)
        if mongo_db is not None:
            for row in created_rows:
                mirror_document(
                    "faculty_messages",
                    {
                        "id": row.id,
                        "faculty_id": row.faculty_id,
                        "student_id": row.student_id,
                        "section": row.section,
                        "message_type": row.message_type,
                        "message": row.message,
                        "created_at": row.created_at,
                        "read_at": row.read_at,
                        "source": "faculty-message-broadcast",
                    },
                    upsert_filter={"id": row.id},
                    required=False,
                )
    except Exception as exc:
        logger.warning("Non-blocking faculty message mirror failure: %s", exc)

    if created_rows:
        event_scopes = {
            "role:admin",
            f"faculty:{int(faculty_id)}",
        }
        event_scopes.update(
            f"student:{int(row.student_id)}"
            for row in created_rows
            if int(getattr(row, "student_id", 0) or 0) > 0
        )
        publish_domain_event(
            "messages.announcement.sent",
            payload={
                "faculty_id": int(faculty_id),
                "sections": sections,
                "message_type": message_type,
                "recipient_count": len(created_rows),
            },
            scopes=event_scopes,
            topics={"messages"},
            actor={
                "user_id": int(current_user.id),
                "faculty_id": int(faculty_id),
                "role": current_user.role.value,
            },
            source="messages",
        )
        enqueue_notification(
            {
                "type": "faculty_announcement",
                "faculty_id": int(faculty_id),
                "sections": sections,
                "recipient_student_ids": [int(row.student_id) for row in created_rows],
                "message_type": message_type,
            }
        )

    return schemas.MessageResponse(
        message=f"Message sent to {len(created_rows)} student(s)."
    )


@router.post("/direct-email", response_model=schemas.StudentDirectEmailOut)
def send_direct_student_email(
    payload: schemas.StudentDirectEmailRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    if current_user.role == models.UserRole.FACULTY and not current_user.faculty_id:
        raise HTTPException(status_code=403, detail="Faculty account is not linked correctly.")

    student = _resolve_student_for_direct_email(
        db,
        student_id=payload.student_id,
        registration_number=payload.registration_number,
        email=payload.email,
    )
    if current_user.role == models.UserRole.FACULTY:
        if not _faculty_can_contact_student(
            db,
            faculty_id=int(current_user.faculty_id),
            student=student,
        ):
            raise HTTPException(status_code=403, detail="This student is outside your allocated section(s).")

    student_email = str(student.email or "").strip()
    if not student_email:
        raise HTTPException(status_code=400, detail="Student email is missing.")

    actor_label = "Admin"
    if current_user.role == models.UserRole.FACULTY:
        faculty = db.get(models.Faculty, int(current_user.faculty_id))
        if faculty and str(faculty.name or "").strip():
            actor_label = str(faculty.name).strip()
        else:
            actor_label = "Faculty"
    if current_user.email:
        actor_label = f"{actor_label} ({str(current_user.email).strip().lower()})"

    message_text = str(payload.message or "").strip()
    subject_text = str(payload.subject or "").strip()
    body = "\n".join(
        [
            f"Message from {actor_label}:",
            "",
            message_text,
            "",
            "Please reply using the LPU Smart Campus portal if needed.",
        ]
    )
    try:
        delivery = send_notification_email(student_email, subject=subject_text, body=body)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    subject_line = str(delivery.get("subject") or subject_text).strip() or subject_text
    log_message = f"{subject_line} | {message_text}".strip()
    if len(log_message) > 500:
        log_message = f"{log_message[:497]}..."

    notification = models.NotificationLog(
        student_id=int(student.id),
        message=log_message,
        channel=str(delivery.get("channel") or "email"),
        sent_to=student_email,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    return schemas.StudentDirectEmailOut(
        message="Email sent to student.",
        student_id=int(student.id),
        delivered_to=student_email,
        subject=subject_line,
        channel=str(delivery.get("channel") or "email"),
        notification_id=int(notification.id),
    )


@router.get("/support/context", response_model=schemas.SupportQueryContextOut)
def get_support_query_context(
    limit: int = Query(default=120, ge=10, le=500),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT, models.UserRole.FACULTY)),
):
    if current_user.role == models.UserRole.STUDENT:
        if not current_user.student_id:
            raise HTTPException(status_code=403, detail="Student account is not linked correctly.")
        contacts, faculty_map = _build_support_contacts_for_student(db, student_id=int(current_user.student_id))
        student_map: dict[int, models.Student] = {}
        rows = (
            db.query(models.SupportQueryMessage)
            .filter(models.SupportQueryMessage.student_id == int(current_user.student_id))
            .order_by(models.SupportQueryMessage.created_at.desc(), models.SupportQueryMessage.id.desc())
            .limit(limit)
            .all()
        )
    else:
        if not current_user.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty account is not linked correctly.")
        contacts, student_map = _build_support_contacts_for_faculty(db, faculty_id=int(current_user.faculty_id))
        faculty = db.get(models.Faculty, int(current_user.faculty_id))
        faculty_map = {int(faculty.id): faculty} if faculty else {}
        rows = (
            db.query(models.SupportQueryMessage)
            .filter(models.SupportQueryMessage.faculty_id == int(current_user.faculty_id))
            .order_by(models.SupportQueryMessage.created_at.desc(), models.SupportQueryMessage.id.desc())
            .limit(limit)
            .all()
        )

    threads = _build_support_threads(
        rows,
        current_user=current_user,
        faculty_map=faculty_map,
        student_map=student_map,
    )
    unread_total = sum(max(0, int(item.unread_count or 0)) for item in threads)
    return schemas.SupportQueryContextOut(
        role=current_user.role.value,
        categories=SUPPORT_QUERY_CATEGORIES,
        contacts=contacts,
        threads=threads,
        unread_total=unread_total,
    )


@router.get("/support/thread", response_model=list[schemas.SupportQueryMessageOut])
def get_support_query_thread(
    counterparty_id: int = Query(..., ge=1),
    category: str = Query(default=schemas.SupportQueryCategory.ATTENDANCE.value),
    limit: int = Query(default=120, ge=10, le=300),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT, models.UserRole.FACULTY)),
):
    category_label = _normalize_support_category(category).value
    if current_user.role == models.UserRole.STUDENT:
        if not current_user.student_id:
            raise HTTPException(status_code=403, detail="Student account is not linked correctly.")
        student_id = int(current_user.student_id)
        if not _student_can_contact_faculty(db, student_id=student_id, faculty_id=int(counterparty_id)):
            raise HTTPException(status_code=403, detail="This faculty is outside your current academic scope.")
        thread_filter = (
            models.SupportQueryMessage.student_id == student_id,
            models.SupportQueryMessage.faculty_id == int(counterparty_id),
            models.SupportQueryMessage.category == category_label,
        )
        incoming_sender = models.UserRole.FACULTY.value
    else:
        if not current_user.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty account is not linked correctly.")
        faculty_id = int(current_user.faculty_id)
        student = db.get(models.Student, int(counterparty_id))
        if not _faculty_can_contact_student(db, faculty_id=faculty_id, student=student):
            raise HTTPException(status_code=403, detail="This student is outside your allocated section(s).")
        thread_filter = (
            models.SupportQueryMessage.student_id == int(counterparty_id),
            models.SupportQueryMessage.faculty_id == faculty_id,
            models.SupportQueryMessage.category == category_label,
        )
        incoming_sender = models.UserRole.STUDENT.value

    unread_filter = thread_filter + (
        models.SupportQueryMessage.sender_role == incoming_sender,
        models.SupportQueryMessage.read_at.is_(None),
    )
    unread_count = (
        db.query(models.SupportQueryMessage.id)
        .filter(*unread_filter)
        .count()
    )
    if unread_count:
        db.query(models.SupportQueryMessage).filter(*unread_filter).update(
            {"read_at": datetime.utcnow()},
            synchronize_session=False,
        )
        db.commit()

    rows = (
        db.query(models.SupportQueryMessage)
        .filter(*thread_filter)
        .order_by(models.SupportQueryMessage.created_at.asc(), models.SupportQueryMessage.id.asc())
        .limit(limit)
        .all()
    )
    return [_serialize_support_query_message(row) for row in rows]


@router.post("/support/send", response_model=schemas.SupportQueryMessageOut)
def send_support_query_message(
    payload: schemas.SupportQuerySend,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT, models.UserRole.FACULTY)),
):
    category = _normalize_support_category(payload.category)
    message_text = str(payload.message or "").strip()
    if not message_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    if current_user.role == models.UserRole.STUDENT:
        if not current_user.student_id:
            raise HTTPException(status_code=403, detail="Student account is not linked correctly.")
        student = db.get(models.Student, int(current_user.student_id))
        faculty = db.get(models.Faculty, int(payload.recipient_id))
        if not student:
            raise HTTPException(status_code=404, detail="Student profile not found.")
        if not faculty:
            raise HTTPException(status_code=404, detail="Faculty not found.")
        if not _student_can_contact_faculty(
            db,
            student_id=int(student.id),
            faculty_id=int(faculty.id),
        ):
            raise HTTPException(status_code=403, detail="This faculty is outside your current academic scope.")
        row = models.SupportQueryMessage(
            student_id=int(student.id),
            faculty_id=int(faculty.id),
            section=_safe_student_section(student),
            category=category.value,
            subject=(str(payload.subject or "").strip() or f"{category.value} Query"),
            message=message_text,
            sender_role=models.UserRole.STUDENT.value,
            created_at=datetime.utcnow(),
        )
    else:
        if not current_user.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty account is not linked correctly.")
        faculty_id = int(current_user.faculty_id)
        student = db.get(models.Student, int(payload.recipient_id))
        if not student:
            raise HTTPException(status_code=404, detail="Student not found.")
        if not _faculty_can_contact_student(db, faculty_id=faculty_id, student=student):
            raise HTTPException(status_code=403, detail="This student is outside your allocated section(s).")
        row = models.SupportQueryMessage(
            student_id=int(student.id),
            faculty_id=faculty_id,
            section=_safe_student_section(student),
            category=category.value,
            subject=(str(payload.subject or "").strip() or f"{category.value} Response"),
            message=message_text,
            sender_role=models.UserRole.FACULTY.value,
            created_at=datetime.utcnow(),
        )

    db.add(row)
    db.commit()
    db.refresh(row)

    try:
        mirror_document(
            "support_query_messages",
            {
                "id": row.id,
                "student_id": row.student_id,
                "faculty_id": row.faculty_id,
                "section": row.section,
                "category": row.category,
                "subject": row.subject,
                "message": row.message,
                "sender_role": row.sender_role,
                "created_at": row.created_at,
                "read_at": row.read_at,
                "source": "support-query-message",
            },
            upsert_filter={"id": row.id},
            required=False,
        )
    except Exception as exc:
        logger.warning("Non-blocking support query mirror failure: %s", exc)

    publish_domain_event(
        "messages.support.updated",
        payload={
            "message_id": int(row.id),
            "student_id": int(row.student_id),
            "faculty_id": int(row.faculty_id),
            "category": str(row.category or ""),
            "sender_role": str(row.sender_role or ""),
        },
        scopes={
            f"student:{int(row.student_id)}",
            f"faculty:{int(row.faculty_id)}",
            "role:admin",
        },
        topics={"messages", "rms"},
        actor={
            "user_id": int(current_user.id),
            "role": current_user.role.value,
        },
        source="messages",
    )
    enqueue_notification(
        {
            "type": "support_query_message",
            "message_id": int(row.id),
            "student_id": int(row.student_id),
            "faculty_id": int(row.faculty_id),
            "category": str(row.category or ""),
            "sender_role": str(row.sender_role or ""),
        }
    )

    return _serialize_support_query_message(row)


@router.get("", response_model=list[schemas.StudentMessageOut])
def get_student_messages(
    limit: int = Query(default=50, ge=1, le=300),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly.")

    student_id = int(current_user.student_id)
    faculty_rows = (
        db.query(models.FacultyMessage)
        .filter(models.FacultyMessage.student_id == student_id)
        .order_by(models.FacultyMessage.created_at.desc(), models.FacultyMessage.id.desc())
        .limit(limit)
        .all()
    )

    remedial_rows = (
        db.query(models.RemedialMessage)
        .filter(models.RemedialMessage.student_id == student_id)
        .order_by(models.RemedialMessage.created_at.desc(), models.RemedialMessage.id.desc())
        .limit(limit)
        .all()
    )

    class_ids = sorted({row.makeup_class_id for row in remedial_rows})
    class_rows = (
        db.query(models.MakeUpClass)
        .filter(models.MakeUpClass.id.in_(class_ids))
        .all()
        if class_ids
        else []
    )
    class_map = {row.id: row for row in class_rows}
    faculty_ids = sorted(
        {row.faculty_id for row in class_rows if row.faculty_id}
        | {row.faculty_id for row in faculty_rows if row.faculty_id}
    )
    faculty_rows_all = (
        db.query(models.Faculty)
        .filter(models.Faculty.id.in_(faculty_ids))
        .all()
        if faculty_ids
        else []
    )
    faculty_map = {row.id: row for row in faculty_rows_all}

    output: list[schemas.StudentMessageOut] = []
    for row in faculty_rows:
        faculty = faculty_map.get(row.faculty_id)
        output.append(
            schemas.StudentMessageOut(
                id=row.id,
                faculty_id=row.faculty_id,
                faculty_name=faculty.name if faculty else None,
                section=row.section,
                message_type=row.message_type or "Announcement",
                message=row.message,
                created_at=row.created_at,
            )
        )

    for row in remedial_rows:
        class_row = class_map.get(row.makeup_class_id)
        if not class_row:
            continue
        course = db.get(models.Course, class_row.course_id)
        faculty = faculty_map.get(class_row.faculty_id)
        output.append(
            schemas.StudentMessageOut(
                id=row.id + 1000000,
                faculty_id=class_row.faculty_id,
                faculty_name=faculty.name if faculty else None,
                section=row.section,
                message_type="Remedial",
                message=row.message,
                created_at=row.created_at,
                class_id=class_row.id,
                course_id=class_row.course_id,
                course_code=course.code if course else None,
                course_title=course.title if course else None,
                remedial_code=row.remedial_code,
                class_date=class_row.class_date,
                start_time=class_row.start_time,
                end_time=class_row.end_time,
                class_mode=class_row.class_mode,
                room_number=class_row.room_number,
                online_link=class_row.online_link,
            )
        )

    output.sort(key=lambda item: item.created_at, reverse=True)
    return output[:limit]


@router.get("/support/cases", response_model=schemas.RMSCaseListOut)
def get_student_support_case_tracker(
    include_closed: bool = Query(default=True),
    limit: int = Query(default=300, ge=20, le=1000),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly.")

    student_id = int(current_user.student_id)
    _ensure_student_rms_cases(db, student_id=student_id, limit=max(200, int(limit)))
    query = db.query(models.RMSCase).filter(models.RMSCase.student_id == student_id)
    if not include_closed:
        query = query.filter(models.RMSCase.status != models.RMSCaseStatus.CLOSED)
    rows = (
        query.order_by(models.RMSCase.updated_at.desc(), models.RMSCase.id.desc())
        .limit(int(limit))
        .all()
    )
    if not rows:
        return schemas.RMSCaseListOut(total=0, pending_queue=0, escalated=0, cases=[])

    student = db.get(models.Student, student_id)
    faculty_ids = sorted({int(row.faculty_id) for row in rows if row.faculty_id})
    faculty_map = (
        {int(row.id): row for row in db.query(models.Faculty).filter(models.Faculty.id.in_(faculty_ids)).all()}
        if faculty_ids
        else {}
    )
    cases = [
        _serialize_rms_case_out_for_student(
            row,
            student=student,
            faculty=faculty_map.get(int(row.faculty_id)) if row.faculty_id else None,
        )
        for row in rows
    ]
    pending_queue = sum(
        1
        for row in rows
        if row.status in {models.RMSCaseStatus.NEW, models.RMSCaseStatus.TRIAGE, models.RMSCaseStatus.ASSIGNED}
    )
    escalated = sum(1 for row in rows if row.is_escalated)
    return schemas.RMSCaseListOut(
        total=len(cases),
        pending_queue=pending_queue,
        escalated=escalated,
        cases=cases,
    )


@router.get("/support/cases/{case_id}/timeline", response_model=schemas.RMSCaseTimelineOut)
def get_student_support_case_timeline(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly.")

    case_row = db.get(models.RMSCase, int(case_id))
    if not case_row or int(case_row.student_id) != int(current_user.student_id):
        raise HTTPException(status_code=404, detail="RMS case not found for this student.")

    student = db.get(models.Student, int(current_user.student_id))
    faculty = db.get(models.Faculty, int(case_row.faculty_id)) if case_row.faculty_id else None
    case_out = _serialize_rms_case_out_for_student(case_row, student=student, faculty=faculty)
    timeline = (
        db.query(models.RMSCaseAuditLog)
        .filter(models.RMSCaseAuditLog.case_id == int(case_row.id))
        .order_by(models.RMSCaseAuditLog.created_at.asc(), models.RMSCaseAuditLog.id.asc())
        .all()
    )
    return schemas.RMSCaseTimelineOut(
        case=case_out,
        timeline=[_serialize_rms_case_audit(row) for row in timeline],
    )


@router.post("/support/cases/{case_id}/reopen", response_model=schemas.RMSCaseOut)
def reopen_student_support_case(
    case_id: int,
    payload: schemas.RMSCaseReopenRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly.")

    case_row = db.get(models.RMSCase, int(case_id))
    if not case_row or int(case_row.student_id) != int(current_user.student_id):
        raise HTTPException(status_code=404, detail="RMS case not found for this student.")
    if case_row.status not in {
        models.RMSCaseStatus.CLOSED,
        models.RMSCaseStatus.REJECTED,
        models.RMSCaseStatus.APPROVED,
    }:
        raise HTTPException(status_code=409, detail="Case can be disputed/reopened only after decision or closure.")

    now_dt = datetime.utcnow()
    from_status = case_row.status
    case_row.status = models.RMSCaseStatus.NEW
    case_row.closed_at = None
    case_row.reopened_count = int(case_row.reopened_count or 0) + 1
    case_row.updated_at = now_dt
    case_row.is_escalated = False
    case_row.escalated_at = None
    case_row.escalation_reason = None
    db.add(
        models.RMSCaseAuditLog(
            case_id=int(case_row.id),
            actor_user_id=int(current_user.id),
            actor_role=current_user.role.value,
            action="student_reopen",
            from_status=from_status,
            to_status=case_row.status,
            note=str(payload.note or "").strip(),
            evidence_ref=(str(payload.evidence_ref or "").strip() or None),
            metadata_json=json.dumps({"reason": "student_dispute"}, separators=(",", ":"), ensure_ascii=True),
            created_at=now_dt,
        )
    )
    db.commit()
    db.refresh(case_row)

    student = db.get(models.Student, int(current_user.student_id))
    faculty = db.get(models.Faculty, int(case_row.faculty_id)) if case_row.faculty_id else None
    return _serialize_rms_case_out_for_student(case_row, student=student, faculty=faculty)
