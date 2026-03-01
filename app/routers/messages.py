import logging
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth_utils import require_roles
from ..database import get_db
from ..mongo import get_mongo_db, mirror_document
from .makeup import _normalize_sections, _faculty_allowed_sections, _student_section

router = APIRouter(prefix="/messages", tags=["Faculty Messages"])
logger = logging.getLogger(__name__)


def _normalize_message_type(value: str) -> str:
    label = re.sub(r"\s+", " ", str(value or "").strip())
    if not label:
        return "Announcement"
    title = label.title()
    if title not in {"Announcement", "General", "Remedial"}:
        return "Announcement"
    return title


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

    return schemas.MessageResponse(
        message=f"Message sent to {len(created_rows)} student(s)."
    )


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
