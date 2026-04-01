import os
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth_utils import require_roles
from ..database import get_db
from ..saarthi_service import (
    SAARTHI_ATTENDANCE_MINUTES,
    count_saarthi_messages,
    create_saarthi_turn,
    ensure_saarthi_bundle,
    get_or_create_saarthi_session,
    list_saarthi_messages,
    materialize_saarthi_attendance,
    saarthi_week_start,
)

router = APIRouter(prefix="/saarthi", tags=["Saarthi"])

ACADEMIC_START_DATE_DEFAULT = "2026-03-02"
SAARTHI_TIMEZONE_DEFAULT = "Asia/Kolkata"


def _academic_start_date() -> date:
    raw = (os.getenv("ACADEMIC_START_DATE", ACADEMIC_START_DATE_DEFAULT) or "").strip()
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return date.fromisoformat(ACADEMIC_START_DATE_DEFAULT)


def _saarthi_now() -> datetime:
    zone_name = (os.getenv("APP_TIMEZONE", SAARTHI_TIMEZONE_DEFAULT) or "").strip() or SAARTHI_TIMEZONE_DEFAULT
    try:
        zone = ZoneInfo(zone_name)
    except ZoneInfoNotFoundError:
        zone = ZoneInfo(SAARTHI_TIMEZONE_DEFAULT)
    return datetime.now(zone).replace(tzinfo=None)


def _serialize_message(row: models.SaarthiMessage) -> schemas.SaarthiMessageOut:
    return schemas.SaarthiMessageOut(
        id=int(row.id),
        sender_role=str(row.sender_role or "").strip().lower() or "assistant",
        message=str(row.message or "").strip(),
        created_at=row.created_at or datetime.now(timezone.utc).replace(tzinfo=None),
    )


def _require_linked_student(
    db: Session,
    *,
    current_user: models.AuthUser,
) -> models.Student:
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")
    student = db.get(models.Student, int(current_user.student_id))
    if student is None:
        raise HTTPException(status_code=404, detail="Student profile not found")
    return student


def _status_message(
    *,
    today: date,
    week_start_date: date,
    mandatory_date: date,
    completed_for_week: bool,
    last_attendance_status: models.AttendanceStatus | None,
    last_attendance_date: date | None,
) -> str:
    if completed_for_week:
        return (
            "This week's mandatory Saarthi counselling is complete. "
            "CON111 has been credited for 1 hour for this Sunday."
        )
    if today == mandatory_date:
        return (
            "Today is your mandatory Saarthi Sunday check-in. "
            "Send at least one message today to secure this week's CON111 attendance credit."
        )
    if (
        last_attendance_status == models.AttendanceStatus.ABSENT
        and last_attendance_date is not None
        and last_attendance_date < week_start_date
    ):
        return (
            f"Last Sunday's mandatory Saarthi check-in on {last_attendance_date.isoformat()} was missed. "
            f"This week, attendance can be credited only on Sunday, {mandatory_date.isoformat()}."
        )
    return (
        f"You can talk to Saarthi anytime this week. Attendance will be credited only once on Sunday, "
        f"{mandatory_date.isoformat()}, and it counts as a single 1-hour CON111 session."
    )


def _build_status_out(
    db: Session,
    *,
    student_id: int,
    current_dt: datetime,
    current_session: models.SaarthiSession | None,
) -> schemas.SaarthiStatusOut:
    bundle = ensure_saarthi_bundle(db, student_id=int(student_id))
    week_start_date = saarthi_week_start(current_dt.date())
    mandatory_date = week_start_date + timedelta(days=6)
    session = current_session
    if session is None:
        session = (
            db.query(models.SaarthiSession)
            .filter(
                models.SaarthiSession.student_id == int(student_id),
                models.SaarthiSession.week_start_date == week_start_date,
            )
            .first()
        )
    messages = list_saarthi_messages(db, session_id=int(session.id), limit=80) if session is not None else []
    message_count = count_saarthi_messages(db, session_id=int(session.id)) if session is not None else 0
    latest_record = (
        db.query(models.AttendanceRecord)
        .filter(
            models.AttendanceRecord.student_id == int(student_id),
            models.AttendanceRecord.course_id == int(bundle.course.id),
        )
        .order_by(models.AttendanceRecord.attendance_date.desc(), models.AttendanceRecord.id.desc())
        .first()
    )
    completed_for_week = bool(session is not None and session.attendance_marked_at is not None)
    return schemas.SaarthiStatusOut(
        course_code=str(bundle.course.code or ""),
        course_title=str(bundle.course.title or ""),
        faculty_name=str(bundle.faculty.name or ""),
        week_start_date=week_start_date,
        mandatory_date=mandatory_date,
        session_completed_for_week=completed_for_week,
        attendance_credit_minutes_for_week=(
            int(session.attendance_credit_minutes or SAARTHI_ATTENDANCE_MINUTES)
            if completed_for_week
            else 0
        ),
        attendance_awarded_on=(session.attendance_marked_at if session is not None else None),
        current_week_message_count=message_count,
        last_attendance_status=(latest_record.status if latest_record is not None else None),
        last_attendance_date=(latest_record.attendance_date if latest_record is not None else None),
        status_message=_status_message(
            today=current_dt.date(),
            week_start_date=week_start_date,
            mandatory_date=mandatory_date,
            completed_for_week=completed_for_week,
            last_attendance_status=(latest_record.status if latest_record is not None else None),
            last_attendance_date=(latest_record.attendance_date if latest_record is not None else None),
        ),
        messages=[_serialize_message(item) for item in messages],
    )


@router.get("/status", response_model=schemas.SaarthiStatusOut)
def get_saarthi_status(
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    student = _require_linked_student(db, current_user=current_user)

    now_dt = _saarthi_now()
    try:
        materialize_saarthi_attendance(
            db,
            student_id=int(student.id),
            academic_start=_academic_start_date(),
            today=now_dt.date(),
        )
        response = _build_status_out(
            db,
            student_id=int(student.id),
            current_dt=now_dt,
            current_session=None,
        )
        db.commit()
        return response
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Saarthi status could not be loaded.") from exc


@router.post("/chat", response_model=schemas.SaarthiChatResponse)
def send_saarthi_message(
    payload: schemas.SaarthiChatRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    student = _require_linked_student(db, current_user=current_user)

    now_dt = _saarthi_now()
    try:
        out = create_saarthi_turn(
            db,
            student=student,
            message=payload.message,
            current_dt=now_dt,
            academic_start=_academic_start_date(),
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except HTTPException:
        db.rollback()
        raise
    try:
        session = out["session"] if isinstance(out, dict) else None
        response = schemas.SaarthiChatResponse(
            reply=str(out.get("reply") or ""),
            attendance_awarded_now=bool(out.get("attendance_awarded_now")),
            session=_build_status_out(
                db,
                student_id=int(student.id),
                current_dt=now_dt,
                current_session=session if isinstance(session, models.SaarthiSession) else None,
            ),
        )
        db.commit()
        return response
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Saarthi message could not be processed.") from exc


@router.post("/new-chat", response_model=schemas.SaarthiStatusOut)
def reset_saarthi_chat(
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    student = _require_linked_student(db, current_user=current_user)

    now_dt = _saarthi_now()
    try:
        materialize_saarthi_attendance(
            db,
            student_id=int(student.id),
            academic_start=_academic_start_date(),
            today=now_dt.date(),
        )
        _, session = get_or_create_saarthi_session(
            db,
            student_id=int(student.id),
            current_dt=now_dt,
        )
        (
            db.query(models.SaarthiMessage)
            .filter(models.SaarthiMessage.session_id == int(session.id))
            .delete(synchronize_session=False)
        )
        session.last_message_at = None
        session.updated_at = now_dt
        response = _build_status_out(
            db,
            student_id=int(student.id),
            current_dt=now_dt,
            current_session=session,
        )
        db.commit()
        return response
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Saarthi chat could not be reset.") from exc
