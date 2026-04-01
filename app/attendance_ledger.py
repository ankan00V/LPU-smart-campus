from __future__ import annotations

import secrets
from datetime import date, datetime, timezone

from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def append_attendance_event(
    db: Session,
    *,
    student_id: int,
    course_id: int,
    attendance_date: date,
    status: models.AttendanceStatus,
    source: str,
    actor_user_id: int | None = None,
    actor_faculty_id: int | None = None,
    actor_role: models.UserRole | str | None = None,
    note: str | None = None,
    event_key: str | None = None,
) -> models.AttendanceEvent:
    token = (event_key or secrets.token_urlsafe(18)).strip()
    existing = db.query(models.AttendanceEvent).filter(models.AttendanceEvent.event_key == token).first()
    if existing is not None:
        return existing

    role_value = None
    if actor_role is not None:
        role_value = actor_role.value if isinstance(actor_role, models.UserRole) else str(actor_role)

    row = models.AttendanceEvent(
        event_key=token,
        student_id=int(student_id),
        course_id=int(course_id),
        attendance_date=attendance_date,
        status=status,
        actor_user_id=int(actor_user_id) if actor_user_id else None,
        actor_faculty_id=int(actor_faculty_id) if actor_faculty_id else None,
        actor_role=role_value,
        source=(source or "attendance-event").strip() or "attendance-event",
        note=(note or "").strip() or None,
        created_at=_utcnow_naive(),
    )
    db.add(row)
    db.flush()
    return row


def _fallback_faculty_id(db: Session) -> int:
    first_faculty = db.query(models.Faculty.id).order_by(models.Faculty.id.asc()).first()
    if first_faculty and first_faculty[0] is not None:
        return int(first_faculty[0])
    raise RuntimeError("No faculty profile exists to attribute attendance aggregate")


def _resolve_marking_faculty_id(
    db: Session,
    *,
    latest_event: models.AttendanceEvent,
    existing_record: models.AttendanceRecord | None,
) -> int:
    if latest_event.actor_faculty_id:
        return int(latest_event.actor_faculty_id)

    course = db.get(models.Course, int(latest_event.course_id))
    if course and course.faculty_id:
        return int(course.faculty_id)

    if existing_record and existing_record.marked_by_faculty_id:
        return int(existing_record.marked_by_faculty_id)

    return _fallback_faculty_id(db)


def recompute_attendance_record(
    db: Session,
    *,
    student_id: int,
    course_id: int,
    attendance_date: date,
) -> models.AttendanceRecord | None:
    latest_event = (
        db.query(models.AttendanceEvent)
        .filter(
            models.AttendanceEvent.student_id == int(student_id),
            models.AttendanceEvent.course_id == int(course_id),
            models.AttendanceEvent.attendance_date == attendance_date,
        )
        .order_by(models.AttendanceEvent.created_at.desc(), models.AttendanceEvent.id.desc())
        .first()
    )

    existing = (
        db.query(models.AttendanceRecord)
        .filter(
            models.AttendanceRecord.student_id == int(student_id),
            models.AttendanceRecord.course_id == int(course_id),
            models.AttendanceRecord.attendance_date == attendance_date,
        )
        .first()
    )

    if latest_event is None:
        if existing is not None:
            db.delete(existing)
            db.flush()
        return None

    marked_by_faculty_id = _resolve_marking_faculty_id(db, latest_event=latest_event, existing_record=existing)
    now_dt = _utcnow_naive()

    if existing is None:
        created = models.AttendanceRecord(
            student_id=int(student_id),
            course_id=int(course_id),
            marked_by_faculty_id=marked_by_faculty_id,
            attendance_date=attendance_date,
            status=latest_event.status,
            source=str(latest_event.source or "attendance-ledger"),
            created_at=latest_event.created_at,
            updated_at=now_dt,
            computed_from_event_id=int(latest_event.id),
        )
        savepoint = db.begin_nested()
        db.add(created)
        try:
            db.flush()
        except IntegrityError:
            savepoint.rollback()
            existing = (
                db.query(models.AttendanceRecord)
                .filter(
                    models.AttendanceRecord.student_id == int(student_id),
                    models.AttendanceRecord.course_id == int(course_id),
                    models.AttendanceRecord.attendance_date == attendance_date,
                )
                .first()
            )
            if existing is None:
                raise
        else:
            savepoint.commit()
            return created

    existing.status = latest_event.status
    existing.source = str(latest_event.source or existing.source or "attendance-ledger")
    existing.marked_by_faculty_id = marked_by_faculty_id
    existing.updated_at = now_dt
    existing.computed_from_event_id = int(latest_event.id)
    db.flush()
    return existing


def append_event_and_recompute(
    db: Session,
    *,
    student_id: int,
    course_id: int,
    attendance_date: date,
    status: models.AttendanceStatus,
    source: str,
    actor_user_id: int | None = None,
    actor_faculty_id: int | None = None,
    actor_role: models.UserRole | str | None = None,
    note: str | None = None,
    event_key: str | None = None,
) -> tuple[models.AttendanceEvent, models.AttendanceRecord | None]:
    event = append_attendance_event(
        db,
        student_id=student_id,
        course_id=course_id,
        attendance_date=attendance_date,
        status=status,
        source=source,
        actor_user_id=actor_user_id,
        actor_faculty_id=actor_faculty_id,
        actor_role=actor_role,
        note=note,
        event_key=event_key,
    )
    record = recompute_attendance_record(
        db,
        student_id=student_id,
        course_id=course_id,
        attendance_date=attendance_date,
    )
    return event, record


def recompute_attendance_scope(
    db: Session,
    *,
    student_id: int | None = None,
    course_id: int | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    limit: int = 5000,
) -> dict[str, int]:
    query = db.query(
        models.AttendanceEvent.student_id,
        models.AttendanceEvent.course_id,
        models.AttendanceEvent.attendance_date,
    )
    filters = []
    if student_id is not None:
        filters.append(models.AttendanceEvent.student_id == int(student_id))
    if course_id is not None:
        filters.append(models.AttendanceEvent.course_id == int(course_id))
    if from_date is not None:
        filters.append(models.AttendanceEvent.attendance_date >= from_date)
    if to_date is not None:
        filters.append(models.AttendanceEvent.attendance_date <= to_date)
    if filters:
        query = query.filter(and_(*filters))

    tuples = (
        query.distinct()
        .order_by(
            models.AttendanceEvent.attendance_date.asc(),
            models.AttendanceEvent.course_id.asc(),
            models.AttendanceEvent.student_id.asc(),
        )
        .limit(max(1, int(limit)))
        .all()
    )

    recomputed = 0
    for sid, cid, day in tuples:
        recompute_attendance_record(
            db,
            student_id=int(sid),
            course_id=int(cid),
            attendance_date=day,
        )
        recomputed += 1

    return {
        "recomputed": recomputed,
        "scanned": len(tuples),
    }
