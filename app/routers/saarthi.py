import os
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth_utils import require_roles
from ..database import get_db
from ..saarthi_service import (
    SAARTHI_ATTENDANCE_MINUTES,
    create_saarthi_turn,
    ensure_saarthi_bundle,
    list_active_saarthi_messages,
    materialize_saarthi_attendance,
    saarthi_week_start,
    start_new_saarthi_chat,
)

router = APIRouter(prefix="/saarthi", tags=["Saarthi"])

ACADEMIC_START_DATE_DEFAULT = "2026-03-02"


def _academic_start_date() -> date:
    raw = (os.getenv("ACADEMIC_START_DATE", ACADEMIC_START_DATE_DEFAULT) or "").strip()
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return date.fromisoformat(ACADEMIC_START_DATE_DEFAULT)


def _serialize_message(row: models.SaarthiMessage) -> schemas.SaarthiMessageOut:
    return schemas.SaarthiMessageOut(
        id=int(row.id),
        sender_role=str(row.sender_role or "").strip().lower() or "assistant",
        message=str(row.message or "").strip(),
        created_at=row.created_at or datetime.utcnow(),
    )


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
            "This week's Saarthi check-in is complete. You can still continue the conversation anytime you need."
        )
    if today == mandatory_date:
        return (
            "Today is your Saarthi Sunday check-in. Take a moment to talk, reflect, or ask for support."
        )
    if (
        last_attendance_status == models.AttendanceStatus.ABSENT
        and last_attendance_date is not None
        and last_attendance_date < week_start_date
    ):
        return (
            f"Last Sunday's Saarthi check-in on {last_attendance_date.isoformat()} was missed. "
            f"This week's guided check-in opens again on Sunday, {mandatory_date.isoformat()}."
        )
    return "Saarthi is here for you through the week. Reach out whenever you want to talk."


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
    messages = list_active_saarthi_messages(db, session_id=int(session.id), limit=80) if session is not None else []
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
        current_week_message_count=len(messages),
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
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    now_dt = datetime.now()
    materialize_saarthi_attendance(
        db,
        student_id=int(current_user.student_id),
        academic_start=_academic_start_date(),
        today=now_dt.date(),
    )
    db.commit()
    return _build_status_out(
        db,
        student_id=int(current_user.student_id),
        current_dt=now_dt,
        current_session=None,
    )


@router.post("/chat", response_model=schemas.SaarthiChatResponse)
def send_saarthi_message(
    payload: schemas.SaarthiChatRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    student = db.get(models.Student, int(current_user.student_id))
    if student is None:
        raise HTTPException(status_code=404, detail="Student profile not found")

    now_dt = datetime.now()
    try:
        out = create_saarthi_turn(
            db,
            student=student,
            message=payload.message,
            current_dt=now_dt,
            academic_start=_academic_start_date(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    db.commit()
    session = out["session"] if isinstance(out, dict) else None
    return schemas.SaarthiChatResponse(
        reply=str(out.get("reply") or ""),
        attendance_awarded_now=bool(out.get("attendance_awarded_now")),
        session=_build_status_out(
            db,
            student_id=int(current_user.student_id),
            current_dt=now_dt,
            current_session=session if isinstance(session, models.SaarthiSession) else None,
        ),
    )


@router.post("/new-chat", response_model=schemas.SaarthiStatusOut)
def reset_saarthi_chat(
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    now_dt = datetime.now()
    materialize_saarthi_attendance(
        db,
        student_id=int(current_user.student_id),
        academic_start=_academic_start_date(),
        today=now_dt.date(),
    )
    _, session = start_new_saarthi_chat(
        db,
        student_id=int(current_user.student_id),
        current_dt=now_dt,
    )
    db.commit()
    return _build_status_out(
        db,
        student_id=int(current_user.student_id),
        current_dt=now_dt,
        current_session=session,
    )
