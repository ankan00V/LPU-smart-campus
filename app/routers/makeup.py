import json
import logging
import os
import re
import secrets
import string
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth_utils import require_roles
from ..database import get_db
from ..face_verification import build_profile_face_template, verify_face_sequence_opencv
from ..mongo import get_mongo_db, mirror_document, mirror_event

router = APIRouter(prefix="/makeup", tags=["Make-Up & Remedial Code"])
logger = logging.getLogger(__name__)

REMEDIAL_ATTENDANCE_WINDOW_MINUTES = 15
REMEDIAL_MIN_SCHEDULE_LEAD_MINUTES = 60
REMEDIAL_REJECT_WINDOW_MINUTES = 30
REMEDIAL_ONLINE_CLASS_LINK = schemas.DEFAULT_REMEDIAL_ONLINE_LINK
REMEDIAL_FACE_MATCH_PASS_THRESHOLD = max(
    0.80,
    min(0.99, float(os.getenv("FACE_MATCH_PASS_THRESHOLD", "0.80"))),
)
REMEDIAL_FACE_MULTI_FRAME_MIN = max(5, int(os.getenv("FACE_MATCH_MIN_FRAMES", "6")))
SECTION_PATTERN = re.compile(r"^[A-Z0-9-_/]+$")


def _normalize_sections(raw_sections: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in raw_sections:
        value = re.sub(r"\s+", "", str(raw or "").strip().upper())
        if not value:
            continue
        if not SECTION_PATTERN.fullmatch(value):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid section '{raw}'. Use only letters, numbers, hyphen, underscore, and slash.",
            )
        if value in seen:
            continue
        seen.add(value)
        cleaned.append(value)
    if not cleaned:
        raise HTTPException(status_code=400, detail="At least one valid section is required.")
    return cleaned


def _parse_sections_json(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    output: list[str] = []
    for item in parsed:
        value = str(item or "").strip().upper()
        if value:
            output.append(value)
    return output


def _mongo_read_preferred() -> bool:
    raw = (os.getenv("MONGO_READ_PREFERRED", "true") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _coerce_mongo_datetime(value) -> datetime | None:
    if isinstance(value, datetime):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _coerce_mongo_date(value) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    dt_value = _coerce_mongo_datetime(value)
    if dt_value is not None:
        return dt_value.date()
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _coerce_mongo_time(value):
    raw = str(value or "").strip()
    if not raw:
        return None
    if "." in raw:
        raw = raw.split(".", 1)[0]
    if "+" in raw:
        raw = raw.split("+", 1)[0]
    if raw.endswith("Z"):
        raw = raw[:-1]
    try:
        return datetime.strptime(raw, "%H:%M:%S").time()
    except ValueError:
        pass
    try:
        return datetime.strptime(raw, "%H:%M").time()
    except ValueError:
        return None


def _get_student_remedial_messages_from_mongo(*, mongo_db, student_id: int, limit: int) -> list[schemas.RemedialMessageOut]:
    fetch_limit = min(max(int(limit) * 4, int(limit)), 500)
    message_docs = list(
        mongo_db["remedial_messages"]
        .find({"student_id": int(student_id)})
        .sort([("created_at", -1), ("id", -1)])
        .limit(fetch_limit)
    )
    if not message_docs:
        return []

    class_ids: list[int] = []
    for doc in message_docs:
        class_value = doc.get("class_id", doc.get("makeup_class_id"))
        try:
            class_id = int(class_value)
        except (TypeError, ValueError):
            continue
        class_ids.append(class_id)
    if not class_ids:
        return []

    class_docs = {
        int(doc["id"]): doc
        for doc in mongo_db["makeup_classes"].find(
            {"id": {"$in": sorted(set(class_ids))}, "is_active": True}
        )
        if doc.get("id") is not None
    }
    if not class_docs:
        return []

    course_ids = sorted(
        {
            int(doc.get("course_id"))
            for doc in class_docs.values()
            if doc.get("course_id") is not None
        }
    )
    faculty_ids = sorted(
        {
            int(doc.get("faculty_id"))
            for doc in class_docs.values()
            if doc.get("faculty_id") is not None
        }
    )
    course_docs = {
        int(doc["id"]): doc
        for doc in mongo_db["courses"].find({"id": {"$in": course_ids}})
        if doc.get("id") is not None
    } if course_ids else {}
    faculty_docs = {
        int(doc["id"]): doc
        for doc in mongo_db["faculty"].find({"id": {"$in": faculty_ids}})
        if doc.get("id") is not None
    } if faculty_ids else {}

    now_dt = datetime.now()
    output: list[schemas.RemedialMessageOut] = []
    for msg in message_docs:
        class_value = msg.get("class_id", msg.get("makeup_class_id"))
        try:
            class_id = int(class_value)
        except (TypeError, ValueError):
            continue

        class_doc = class_docs.get(class_id)
        if not class_doc:
            continue

        class_date = _coerce_mongo_date(class_doc.get("class_date"))
        start_time = _coerce_mongo_time(class_doc.get("start_time"))
        end_time = _coerce_mongo_time(class_doc.get("end_time"))
        created_at = _coerce_mongo_datetime(msg.get("created_at"))
        if not class_date or not start_time or not end_time:
            continue
        if _class_is_finished(class_date=class_date, start_time=start_time, end_time=end_time, now_dt=now_dt):
            continue

        course_id = int(class_doc.get("course_id") or 0)
        faculty_id = int(class_doc.get("faculty_id") or 0)
        course_doc = course_docs.get(course_id, {})
        faculty_doc = faculty_docs.get(faculty_id, {})
        course_code = str(course_doc.get("code") or f"C-{course_id}")
        course_title = str(course_doc.get("title") or "Course")

        output.append(
            schemas.RemedialMessageOut(
                id=int(msg.get("id") or 0),
                class_id=class_id,
                course_id=course_id,
                course_code=course_code,
                course_title=course_title,
                faculty_name=(str(faculty_doc.get("name")).strip() if faculty_doc.get("name") else None),
                section=str(msg.get("section") or ""),
                message=str(msg.get("message") or ""),
                remedial_code=str(msg.get("remedial_code") or class_doc.get("remedial_code") or ""),
                message_type="Remedial",
                class_date=class_date,
                start_time=start_time,
                end_time=end_time,
                class_mode=str(class_doc.get("class_mode") or "offline"),
                room_number=(str(class_doc.get("room_number")).strip() if class_doc.get("room_number") else None),
                online_link=(str(class_doc.get("online_link")).strip() if class_doc.get("online_link") else None),
                created_at=created_at or datetime.utcnow(),
            )
        )
        if len(output) >= int(limit):
            break
    return output


def _faculty_allowed_sections(faculty: models.Faculty | None) -> set[str]:
    if not faculty or not faculty.section:
        return set()
    tokens = re.split(r"[,\s]+", str(faculty.section).strip().upper())
    return {token for token in tokens if token}


def _class_datetimes(class_row: models.MakeUpClass) -> tuple[datetime, datetime]:
    class_start = datetime.combine(class_row.class_date, class_row.start_time)
    class_end = datetime.combine(class_row.class_date, class_row.end_time)
    if class_end <= class_start:
        class_end += timedelta(days=1)
    return class_start, class_end


def _class_is_finished(*, class_date: date, start_time, end_time, now_dt: datetime | None = None) -> bool:
    class_start = datetime.combine(class_date, start_time)
    class_end = datetime.combine(class_date, end_time)
    if class_end <= class_start:
        class_end += timedelta(days=1)
    return (now_dt or datetime.now()) > class_end


def _attendance_window_close(class_row: models.MakeUpClass) -> datetime:
    class_start, _ = _class_datetimes(class_row)
    window_minutes = class_row.attendance_open_minutes or REMEDIAL_ATTENDANCE_WINDOW_MINUTES
    return class_start + timedelta(minutes=max(1, int(window_minutes)))


def _reject_window_close(class_row: models.MakeUpClass) -> datetime:
    base = class_row.scheduled_at or class_row.created_at or class_row.code_generated_at or datetime.utcnow()
    return base + timedelta(minutes=REMEDIAL_REJECT_WINDOW_MINUTES)


def _reject_window_open(class_row: models.MakeUpClass, *, now_utc: datetime | None = None) -> bool:
    now_dt = now_utc or datetime.utcnow()
    return now_dt <= _reject_window_close(class_row)


def _resolved_online_link(class_row: models.MakeUpClass) -> str | None:
    if str(class_row.class_mode or "").strip().lower() == "online":
        return REMEDIAL_ONLINE_CLASS_LINK
    return class_row.online_link


def _generate_remedial_code(db: Session, length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(30):
        code = "".join(secrets.choice(alphabet) for _ in range(length))
        exists = db.query(models.MakeUpClass).filter(models.MakeUpClass.remedial_code == code).first()
        if not exists:
            return code
    raise RuntimeError("Unable to generate unique remedial code")


def _serialize_makeup_class(class_row: models.MakeUpClass) -> schemas.MakeUpClassOut:
    return schemas.MakeUpClassOut(
        id=class_row.id,
        course_id=class_row.course_id,
        faculty_id=class_row.faculty_id,
        class_date=class_row.class_date,
        start_time=class_row.start_time,
        end_time=class_row.end_time,
        topic=class_row.topic,
        sections=_parse_sections_json(class_row.sections_json),
        class_mode=class_row.class_mode or "offline",
        room_number=class_row.room_number,
        online_link=_resolved_online_link(class_row),
        remedial_code=class_row.remedial_code,
        code_generated_at=class_row.code_generated_at or class_row.created_at,
        code_expires_at=class_row.code_expires_at or _attendance_window_close(class_row),
        attendance_open_minutes=class_row.attendance_open_minutes or REMEDIAL_ATTENDANCE_WINDOW_MINUTES,
        scheduled_at=class_row.scheduled_at or class_row.created_at,
        is_active=bool(class_row.is_active),
        can_reject=bool(class_row.is_active) and _reject_window_open(class_row),
    )


def _sync_makeup_class_to_mongo(class_row: models.MakeUpClass, *, source: str) -> None:
    mirror_document(
        "makeup_classes",
        {
            "id": class_row.id,
            "makeup_class_id": class_row.id,
            "course_id": class_row.course_id,
            "faculty_id": class_row.faculty_id,
            "class_date": class_row.class_date.isoformat(),
            "start_time": str(class_row.start_time),
            "end_time": str(class_row.end_time),
            "topic": class_row.topic,
            "sections": _parse_sections_json(class_row.sections_json),
            "class_mode": class_row.class_mode,
            "room_number": class_row.room_number,
            "online_link": _resolved_online_link(class_row),
            "remedial_code": class_row.remedial_code,
            "code_generated_at": class_row.code_generated_at,
            "code_expires_at": class_row.code_expires_at,
            "attendance_open_minutes": class_row.attendance_open_minutes,
            "scheduled_at": class_row.scheduled_at,
            "is_active": class_row.is_active,
            "created_at": class_row.created_at,
            "source": source,
        },
        upsert_filter={"id": class_row.id},
    )


def _ensure_faculty_can_manage_class(
    db: Session,
    *,
    current_user: models.AuthUser,
    class_row: models.MakeUpClass,
) -> None:
    if current_user.role != models.UserRole.FACULTY:
        return
    if not current_user.faculty_id or current_user.faculty_id != class_row.faculty_id:
        raise HTTPException(status_code=403, detail="Faculty can manage only their own remedial classes.")
    faculty = db.get(models.Faculty, current_user.faculty_id)
    allowed_sections = _faculty_allowed_sections(faculty)
    target_sections = set(_parse_sections_json(class_row.sections_json))
    if allowed_sections and not target_sections.issubset(allowed_sections):
        raise HTTPException(status_code=403, detail="You can message only your allocated section(s).")


def _student_section(student: models.Student) -> str:
    section = re.sub(r"\s+", "", str(student.section or "").strip().upper())
    if not section:
        raise HTTPException(
            status_code=400,
            detail="Student section is missing. Update section in profile before using remedial module.",
        )
    return section


def _normalized_section_token(raw_section: str | None) -> str:
    return re.sub(r"\s+", "", str(raw_section or "").strip().upper())


def _student_has_remedial_access(
    db: Session,
    *,
    student_id: int,
    class_row: models.MakeUpClass,
) -> bool:
    enrolled = (
        db.query(models.Enrollment.id)
        .filter(
            models.Enrollment.student_id == student_id,
            models.Enrollment.course_id == class_row.course_id,
        )
        .first()
        is not None
    )
    if enrolled:
        return True
    # Fallback for manual/faculty-created remedial courses where SQL enrollment linkage may lag:
    # if code was explicitly sent to this student for this class, allow validation/marking.
    targeted = (
        db.query(models.RemedialMessage.id)
        .filter(
            models.RemedialMessage.makeup_class_id == class_row.id,
            models.RemedialMessage.student_id == student_id,
        )
        .first()
        is not None
    )
    return targeted


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


def _public_face_rejection_message(reason: str, confidence: float | None = None) -> str:
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
    if score < REMEDIAL_FACE_MATCH_PASS_THRESHOLD:
        return "Face almost matched. Move to brighter light, align straight, and retry."
    return "Face not recognized. Move to brighter light and retry."


def _verify_remedial_face_payload(
    *,
    student: models.Student,
    payload: schemas.RemedialAttendanceMark,
    class_row: models.MakeUpClass,
) -> tuple[str, float, str, str]:
    selfie_frames = payload.selfie_frames_data_urls or []
    primary_selfie = payload.selfie_photo_data_url
    if not primary_selfie and selfie_frames:
        primary_selfie = selfie_frames[0]
    if not primary_selfie:
        raise HTTPException(status_code=400, detail="Capture selfie before marking attendance")
    if not selfie_frames:
        selfie_frames = [primary_selfie]
    if len(selfie_frames) < REMEDIAL_FACE_MULTI_FRAME_MIN:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Capture at least {REMEDIAL_FACE_MULTI_FRAME_MIN} frames "
                "for secure facial attendance verification"
            ),
        )

    if not student.registration_number:
        raise HTTPException(
            status_code=400,
            detail="Complete profile setup with registration number before attendance",
        )
    if not student.profile_photo_data_url:
        raise HTTPException(status_code=400, detail="Upload profile photo before marking attendance")
    if not student.enrollment_video_template_json:
        raise HTTPException(
            status_code=400,
            detail="Complete one-time enrollment video before marking attendance",
        )

    enrollment_template = _parse_face_template(student.enrollment_video_template_json)
    profile_template = _parse_face_template(student.profile_face_template_json)
    combined_template = _merge_face_templates(enrollment_template, profile_template)
    if combined_template is None:
        raise HTTPException(
            status_code=400,
            detail="Complete one-time enrollment video before marking attendance",
        )
    if profile_template is None and student.profile_photo_data_url:
        try:
            profile_template = build_profile_face_template(student.profile_photo_data_url)
        except ValueError:
            profile_template = None
        combined_template = _merge_face_templates(enrollment_template, profile_template)

    opencv_verdict = verify_face_sequence_opencv(
        student.profile_photo_data_url,
        selfie_frames,
        subject_label=student.email,
        profile_template=combined_template,
    )
    if not bool(opencv_verdict.get("available")):
        reason = str(opencv_verdict.get("reason", "OpenCV verification unavailable"))
        raise HTTPException(status_code=503, detail=f"OpenCV verification unavailable: {reason}")

    final_confidence = max(0.0, min(1.0, float(opencv_verdict.get("confidence", 0.0))))
    final_engine = str(opencv_verdict.get("engine") or "opencv-embedding")
    final_reason = str(opencv_verdict.get("reason") or "Face not recognized")
    final_match = bool(opencv_verdict.get("match")) and final_confidence >= REMEDIAL_FACE_MATCH_PASS_THRESHOLD
    if not final_match:
        raise HTTPException(
            status_code=403,
            detail=_public_face_rejection_message(final_reason, final_confidence),
        )

    logger.info(
        "remedial_face_verification_passed class_id=%s student_id=%s confidence=%.4f engine=%s reason=%s",
        class_row.id,
        student.id,
        final_confidence,
        final_engine,
        final_reason,
    )
    return primary_selfie, final_confidence, final_engine, final_reason


def _resolve_makeup_course(payload: schemas.MakeUpClassCreate, db: Session) -> tuple[models.Course, bool]:
    if payload.course_id:
        course = db.get(models.Course, int(payload.course_id))
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        return course, False

    code = str(payload.course_code or "").strip().upper()
    title = str(payload.course_title or "").strip()
    if not code or not title:
        raise HTTPException(status_code=400, detail="Enter both course code and course title.")

    existing = db.query(models.Course).filter(models.Course.code == code).first()
    if existing:
        if existing.faculty_id != payload.faculty_id:
            raise HTTPException(
                status_code=409,
                detail="Course code already belongs to another faculty. Use a unique course code.",
            )
        if existing.title != title:
            existing.title = title
        return existing, True

    course = models.Course(code=code, title=title, faculty_id=payload.faculty_id)
    db.add(course)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.query(models.Course).filter(models.Course.code == code).first()
        if existing and existing.faculty_id == payload.faculty_id:
            if existing.title != title:
                existing.title = title
            return existing, True
        raise HTTPException(
            status_code=409,
            detail="Course code already exists. Please use another code.",
        ) from None
    return course, True


@router.get("/faculty/eligible-courses", response_model=list[schemas.CourseOut])
def list_faculty_eligible_courses(
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    query = db.query(models.Course)
    if current_user.role == models.UserRole.FACULTY:
        if not current_user.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty account is not linked correctly")
        faculty_id = int(current_user.faculty_id)
        rows = (
            query.filter(models.Course.faculty_id == faculty_id)
            .order_by(models.Course.code.asc(), models.Course.id.asc())
            .all()
        )
        if rows:
            return rows

        schedule_course_ids = (
            db.query(models.ClassSchedule.course_id)
            .filter(models.ClassSchedule.faculty_id == faculty_id)
            .distinct()
            .all()
        )
        fallback_ids = [int(row[0]) for row in schedule_course_ids if row and row[0]]
        if not fallback_ids:
            return []
        return (
            db.query(models.Course)
            .filter(models.Course.id.in_(fallback_ids))
            .order_by(models.Course.code.asc(), models.Course.id.asc())
            .all()
        )

    return query.order_by(models.Course.code.asc(), models.Course.id.asc()).all()


@router.post("/classes", response_model=schemas.MakeUpClassOut, status_code=status.HTTP_201_CREATED)
def create_makeup_class(
    payload: schemas.MakeUpClassCreate,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    if current_user.role == models.UserRole.FACULTY:
        if not current_user.faculty_id or current_user.faculty_id != payload.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty can schedule only for their own ID.")

    course, used_manual_course_entry = _resolve_makeup_course(payload, db)

    if course.faculty_id != payload.faculty_id:
        raise HTTPException(status_code=400, detail="Faculty is not assigned to this course.")

    now_dt = datetime.now()
    if payload.class_date < now_dt.date():
        raise HTTPException(status_code=400, detail="Remedial class date cannot be in the past.")

    class_start = datetime.combine(payload.class_date, payload.start_time)
    class_end = datetime.combine(payload.class_date, payload.end_time)
    if class_end <= class_start:
        class_end += timedelta(days=1)
    effective_class_date = payload.class_date
    # If faculty selects a time earlier than current clock on the same date,
    # treat it as scheduling for the next day (common after-midnight use case).
    if payload.class_date == now_dt.date() and class_start <= now_dt:
        class_start += timedelta(days=1)
        class_end += timedelta(days=1)
        effective_class_date = class_start.date()
    if (
        (class_start - now_dt) < timedelta(minutes=REMEDIAL_MIN_SCHEDULE_LEAD_MINUTES)
        and not bool(payload.demo_bypass_lead_time)
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Remedial class must be scheduled at least 1 hour before start time. "
                "Please choose a later slot."
            ),
        )

    sections = _normalize_sections(payload.sections)
    if current_user.role == models.UserRole.FACULTY:
        faculty = db.get(models.Faculty, payload.faculty_id)
        allowed_sections = _faculty_allowed_sections(faculty)
        if allowed_sections and not set(sections).issubset(allowed_sections):
            raise HTTPException(
                status_code=403,
                detail="Selected section(s) are outside your allocated section scope.",
            )

    code = _generate_remedial_code(db)
    code_generated_at = datetime.utcnow()
    code_expires_at = class_start + timedelta(minutes=REMEDIAL_ATTENDANCE_WINDOW_MINUTES)

    class_row = models.MakeUpClass(
        course_id=course.id,
        faculty_id=payload.faculty_id,
        class_date=effective_class_date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        topic=payload.topic.strip(),
        sections_json=json.dumps(sections),
        class_mode=payload.class_mode,
        room_number=(payload.room_number or "").strip() or None,
        online_link=REMEDIAL_ONLINE_CLASS_LINK if payload.class_mode == "online" else None,
        remedial_code=code,
        code_generated_at=code_generated_at,
        code_expires_at=code_expires_at,
        attendance_open_minutes=REMEDIAL_ATTENDANCE_WINDOW_MINUTES,
        scheduled_at=datetime.utcnow(),
        is_active=True,
    )
    db.add(class_row)
    db.commit()
    db.refresh(class_row)

    if used_manual_course_entry:
        mirror_document(
            "courses",
            {
                "id": course.id,
                "code": course.code,
                "title": course.title,
                "faculty_id": course.faculty_id,
                "source": "faculty-remedial-manual-entry",
            },
            upsert_filter={"id": course.id},
        )
        mirror_event(
            "remedial.course_manual_bound",
            {
                "course_id": course.id,
                "course_code": course.code,
                "course_title": course.title,
                "faculty_id": course.faculty_id,
                "class_id": class_row.id,
            },
            actor={
                "user_id": current_user.id,
                "role": current_user.role.value,
                "faculty_id": current_user.faculty_id,
            },
        )

    _sync_makeup_class_to_mongo(class_row, source="faculty-remedial-scheduler")
    mirror_event(
        "remedial.class_scheduled",
        {
            "class_id": class_row.id,
            "course_id": class_row.course_id,
            "faculty_id": class_row.faculty_id,
            "sections": sections,
            "class_date": class_row.class_date.isoformat(),
            "start_time": str(class_row.start_time),
            "end_time": str(class_row.end_time),
            "mode": class_row.class_mode,
            "code_expires_at": class_row.code_expires_at,
            "demo_bypass_lead_time": bool(payload.demo_bypass_lead_time),
        },
        actor={
            "user_id": current_user.id,
            "role": current_user.role.value,
            "faculty_id": current_user.faculty_id,
        },
    )
    return _serialize_makeup_class(class_row)


@router.get("/classes", response_model=list[schemas.MakeUpClassOut])
def list_makeup_classes(
    week_start: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.STUDENT)
    ),
):
    query = db.query(models.MakeUpClass).filter(models.MakeUpClass.is_active.is_(True))
    if week_start:
        week_end = week_start + timedelta(days=6)
        query = query.filter(
            models.MakeUpClass.class_date >= week_start,
            models.MakeUpClass.class_date <= week_end,
        )

    if current_user.role == models.UserRole.FACULTY:
        if not current_user.faculty_id:
            return []
        query = query.filter(models.MakeUpClass.faculty_id == current_user.faculty_id)
        rows = query.order_by(models.MakeUpClass.class_date.desc(), models.MakeUpClass.start_time.asc()).all()
        return [_serialize_makeup_class(row) for row in rows]

    if current_user.role == models.UserRole.STUDENT:
        if not current_user.student_id:
            return []
        student = db.get(models.Student, current_user.student_id)
        if not student:
            return []
        student_section = _student_section(student)
        rows = query.order_by(models.MakeUpClass.class_date.asc(), models.MakeUpClass.start_time.asc()).all()
        matched: list[schemas.MakeUpClassOut] = []
        for row in rows:
            sections = _parse_sections_json(row.sections_json)
            if student_section in sections:
                matched.append(_serialize_makeup_class(row))
        return matched

    rows = query.order_by(models.MakeUpClass.class_date.desc(), models.MakeUpClass.start_time.asc()).all()
    return [_serialize_makeup_class(row) for row in rows]


@router.post("/classes/{class_id}/generate-code", response_model=schemas.RemedialCodeGenerateOut)
def regenerate_remedial_code(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    class_row = db.get(models.MakeUpClass, class_id)
    if not class_row or not class_row.is_active:
        raise HTTPException(status_code=404, detail="Remedial class not found")
    _ensure_faculty_can_manage_class(db, current_user=current_user, class_row=class_row)

    class_start, _ = _class_datetimes(class_row)
    now_dt = datetime.now()
    if now_dt > class_start + timedelta(minutes=class_row.attendance_open_minutes or REMEDIAL_ATTENDANCE_WINDOW_MINUTES):
        raise HTTPException(status_code=400, detail="Cannot regenerate code after attendance window has ended.")

    class_row.remedial_code = _generate_remedial_code(db)
    class_row.code_generated_at = datetime.utcnow()
    class_row.code_expires_at = class_start + timedelta(
        minutes=class_row.attendance_open_minutes or REMEDIAL_ATTENDANCE_WINDOW_MINUTES
    )
    db.commit()
    db.refresh(class_row)

    _sync_makeup_class_to_mongo(class_row, source="faculty-remedial-code-regenerated")
    mirror_event(
        "remedial.code_regenerated",
        {
            "class_id": class_row.id,
            "course_id": class_row.course_id,
            "faculty_id": class_row.faculty_id,
            "remedial_code": class_row.remedial_code,
            "code_expires_at": class_row.code_expires_at,
        },
        actor={
            "user_id": current_user.id,
            "role": current_user.role.value,
            "faculty_id": current_user.faculty_id,
        },
    )

    return schemas.RemedialCodeGenerateOut(
        class_id=class_row.id,
        remedial_code=class_row.remedial_code,
        code_generated_at=class_row.code_generated_at,
        code_expires_at=class_row.code_expires_at,
    )


@router.post("/classes/{class_id}/send-message", response_model=schemas.RemedialSendMessageOut)
def send_remedial_code_to_sections(
    class_id: int,
    payload: schemas.RemedialSendMessageRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    class_row = db.get(models.MakeUpClass, class_id)
    if not class_row or not class_row.is_active:
        raise HTTPException(status_code=404, detail="Remedial class not found")
    _ensure_faculty_can_manage_class(db, current_user=current_user, class_row=class_row)

    course = db.get(models.Course, class_row.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    sections = _parse_sections_json(class_row.sections_json)
    if not sections:
        raise HTTPException(status_code=400, detail="No target sections configured on remedial class.")
    section_set = set(sections)
    students = (
        db.query(models.Student)
        .filter(models.Student.section.in_(section_set))
        .all()
    )
    if not students:
        return schemas.RemedialSendMessageOut(
            class_id=class_row.id,
            remedial_code=class_row.remedial_code,
            sections=sections,
            recipients=0,
            message="No students found for target section(s).",
        )

    class_mode_label = "Online (MyClass Platform)" if class_row.class_mode == "online" else f"Offline • Room {class_row.room_number or 'TBA'}"
    custom = (payload.custom_message or "").strip()
    default_message = (
        f"Remedial class scheduled for {class_row.class_date.isoformat()} "
        f"{str(class_row.start_time)}-{str(class_row.end_time)} | "
        f"{course.code} - {course.title} | {class_mode_label}. "
        f"Code: {class_row.remedial_code}. Attendance open for first {class_row.attendance_open_minutes} minutes."
    )
    message_text = custom or default_message

    now_dt = datetime.utcnow()
    recipients = 0
    for student in students:
        student_section = re.sub(r"\s+", "", str(student.section or "").strip().upper())
        if not student_section or student_section not in section_set:
            continue

        existing = (
            db.query(models.RemedialMessage)
            .filter(
                models.RemedialMessage.makeup_class_id == class_row.id,
                models.RemedialMessage.student_id == student.id,
            )
            .first()
        )
        if existing:
            existing.section = student_section
            existing.remedial_code = class_row.remedial_code
            existing.message = message_text
            existing.created_at = now_dt
            existing.read_at = None
            message_row = existing
        else:
            message_row = models.RemedialMessage(
                makeup_class_id=class_row.id,
                faculty_id=class_row.faculty_id,
                student_id=student.id,
                section=student_section,
                remedial_code=class_row.remedial_code,
                message=message_text,
                created_at=now_dt,
            )
            db.add(message_row)
        recipients += 1

    db.commit()

    mirror_errors = 0
    message_rows = (
        db.query(models.RemedialMessage)
        .filter(models.RemedialMessage.makeup_class_id == class_row.id)
        .all()
    )
    for row in message_rows:
        try:
            mirror_document(
                "remedial_messages",
                {
                    "id": row.id,
                    "class_id": row.makeup_class_id,
                    "faculty_id": row.faculty_id,
                    "student_id": row.student_id,
                    "section": row.section,
                    "remedial_code": row.remedial_code,
                    "message": row.message,
                    "created_at": row.created_at,
                    "read_at": row.read_at,
                    "source": "faculty-remedial-message",
                },
                upsert_filter={"id": row.id},
                required=False,
            )
        except Exception as exc:
            mirror_errors += 1
            logger.warning(
                "Non-blocking remedial message mirror failure for class_id=%s row_id=%s: %s",
                class_row.id,
                row.id,
                exc,
            )

    try:
        mirror_event(
            "remedial.code_message_sent",
            {
                "class_id": class_row.id,
                "course_id": class_row.course_id,
                "sections": sections,
                "recipients": recipients,
                "remedial_code": class_row.remedial_code,
                "mirror_errors": mirror_errors,
            },
            actor={
                "user_id": current_user.id,
                "role": current_user.role.value,
                "faculty_id": current_user.faculty_id,
            },
            required=False,
        )
    except Exception as exc:
        logger.warning(
            "Non-blocking remedial event mirror failure for class_id=%s: %s",
            class_row.id,
            exc,
        )
    return schemas.RemedialSendMessageOut(
        class_id=class_row.id,
        remedial_code=class_row.remedial_code,
        sections=sections,
        recipients=recipients,
        message=f"Message sent to {recipients} student(s).",
    )


@router.post("/classes/{class_id}/cancel", response_model=schemas.MakeUpClassOut)
def cancel_makeup_class(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.FACULTY)),
):
    if current_user.role != models.UserRole.FACULTY:
        raise HTTPException(status_code=403, detail="Only faculty can reject remedial classes.")
    class_row = db.get(models.MakeUpClass, class_id)
    if not class_row:
        raise HTTPException(status_code=404, detail="Remedial class not found")
    _ensure_faculty_can_manage_class(db, current_user=current_user, class_row=class_row)
    if not class_row.is_active:
        return _serialize_makeup_class(class_row)
    if not _reject_window_open(class_row):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Reject window closed. Faculty can reject a remedial class only within "
                f"{REMEDIAL_REJECT_WINDOW_MINUTES} minutes of scheduling."
            ),
        )

    linked_messages = (
        db.query(models.RemedialMessage.id, models.RemedialMessage.student_id)
        .filter(models.RemedialMessage.makeup_class_id == class_row.id)
        .all()
    )

    class_row.is_active = False
    db.query(models.RemedialMessage).filter(
        models.RemedialMessage.makeup_class_id == class_row.id
    ).delete(synchronize_session=False)
    db.commit()
    db.refresh(class_row)

    _sync_makeup_class_to_mongo(class_row, source="faculty-remedial-cancel")
    try:
        mongo_db = get_mongo_db(required=False)
        if mongo_db is not None:
            mongo_db["remedial_messages"].delete_many({"class_id": class_row.id})
    except Exception as exc:
        logger.warning(
            "Non-blocking remedial message cleanup mirror failure for cancelled class_id=%s: %s",
            class_row.id,
            exc,
        )
    mirror_event(
        "remedial.class_cancelled",
        {
            "class_id": class_row.id,
            "course_id": class_row.course_id,
            "faculty_id": class_row.faculty_id,
            "sections": _parse_sections_json(class_row.sections_json),
            "class_date": class_row.class_date.isoformat(),
            "start_time": str(class_row.start_time),
            "end_time": str(class_row.end_time),
            "remedial_code": class_row.remedial_code,
            "revoked_message_count": len(linked_messages),
        },
        actor={
            "user_id": current_user.id,
            "role": current_user.role.value,
            "faculty_id": current_user.faculty_id,
        },
        required=False,
    )

    return _serialize_makeup_class(class_row)


@router.get("/messages", response_model=list[schemas.RemedialMessageOut])
def get_student_remedial_messages(
    limit: int = Query(default=50, ge=1, le=300),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    if _mongo_read_preferred():
        mongo_db = get_mongo_db(required=False)
        if mongo_db is not None:
            try:
                mongo_rows = _get_student_remedial_messages_from_mongo(
                    mongo_db=mongo_db,
                    student_id=int(current_user.student_id),
                    limit=limit,
                )
                if mongo_rows:
                    return mongo_rows
            except Exception as exc:
                logger.warning("Mongo remedial message read fallback to SQL: %s", exc)

    fetch_limit = min(max(int(limit) * 4, int(limit)), 500)
    rows = (
        db.query(models.RemedialMessage)
        .join(
            models.MakeUpClass,
            models.MakeUpClass.id == models.RemedialMessage.makeup_class_id,
        )
        .filter(models.RemedialMessage.student_id == current_user.student_id)
        .filter(models.MakeUpClass.is_active.is_(True))
        .order_by(models.RemedialMessage.created_at.desc(), models.RemedialMessage.id.desc())
        .limit(fetch_limit)
        .all()
    )
    if not rows:
        return []

    class_ids = sorted({row.makeup_class_id for row in rows})
    class_rows = (
        db.query(models.MakeUpClass)
        .filter(models.MakeUpClass.id.in_(class_ids))
        .all()
    )
    class_map = {row.id: row for row in class_rows}
    faculty_ids = sorted({row.faculty_id for row in class_rows if row.faculty_id})
    faculty_rows = (
        db.query(models.Faculty)
        .filter(models.Faculty.id.in_(faculty_ids))
        .all()
        if faculty_ids
        else []
    )
    faculty_map = {row.id: row for row in faculty_rows}
    course_ids = sorted({row.course_id for row in class_rows})
    courses = (
        db.query(models.Course)
        .filter(models.Course.id.in_(course_ids))
        .all()
        if course_ids
        else []
    )
    course_map = {row.id: row for row in courses}

    now_dt = datetime.now()
    out: list[schemas.RemedialMessageOut] = []
    for row in rows:
        class_row = class_map.get(row.makeup_class_id)
        if not class_row:
            continue
        if _class_is_finished(
            class_date=class_row.class_date,
            start_time=class_row.start_time,
            end_time=class_row.end_time,
            now_dt=now_dt,
        ):
            continue
        course = course_map.get(class_row.course_id)
        out.append(
            schemas.RemedialMessageOut(
                id=row.id,
                class_id=class_row.id,
                course_id=class_row.course_id,
                course_code=course.code if course else f"C-{class_row.course_id}",
                course_title=course.title if course else "Course",
                faculty_name=(faculty_map.get(class_row.faculty_id).name if faculty_map.get(class_row.faculty_id) else None),
                section=row.section,
                message=row.message,
                remedial_code=row.remedial_code,
                message_type="Remedial",
                class_date=class_row.class_date,
                start_time=class_row.start_time,
                end_time=class_row.end_time,
                class_mode=class_row.class_mode,
                room_number=class_row.room_number,
                online_link=_resolved_online_link(class_row),
                created_at=row.created_at,
            )
        )
        if len(out) >= int(limit):
            break
    return out


@router.post("/code/validate", response_model=schemas.RemedialCodeValidateOut)
def validate_remedial_code(
    payload: schemas.RemedialCodeValidateRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")
    student = db.get(models.Student, current_user.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    student_section = _student_section(student)

    code = str(payload.remedial_code or "").strip().upper()
    if not code:
        raise HTTPException(status_code=400, detail="Enter remedial code")

    class_row = (
        db.query(models.MakeUpClass)
        .filter(
            models.MakeUpClass.remedial_code == code,
            models.MakeUpClass.is_active.is_(True),
        )
        .first()
    )
    if not class_row:
        raise HTTPException(status_code=404, detail="Invalid remedial code")

    sections = set(_parse_sections_json(class_row.sections_json))
    if student_section not in sections:
        raise HTTPException(status_code=403, detail="Code is not valid for your section")

    if not _student_has_remedial_access(db, student_id=student.id, class_row=class_row):
        raise HTTPException(status_code=403, detail="You are not enrolled in this course")

    class_start, _ = _class_datetimes(class_row)
    window_close = _attendance_window_close(class_row)
    now_dt = datetime.now()
    if class_row.code_expires_at and now_dt > class_row.code_expires_at:
        raise HTTPException(status_code=400, detail="Remedial code has expired")

    course = db.get(models.Course, class_row.course_id)
    attendance_open = class_start <= now_dt <= window_close
    return schemas.RemedialCodeValidateOut(
        valid=True,
        message="Remedial code validated successfully.",
        class_id=class_row.id,
        course_id=class_row.course_id,
        course_code=(course.code if course else None),
        course_title=(course.title if course else None),
        class_date=class_row.class_date,
        start_time=class_row.start_time,
        end_time=class_row.end_time,
        class_mode=class_row.class_mode,
        room_number=class_row.room_number,
        online_link=_resolved_online_link(class_row),
        attendance_window_open=attendance_open,
        attendance_window_minutes=class_row.attendance_open_minutes or REMEDIAL_ATTENDANCE_WINDOW_MINUTES,
    )


@router.post("/attendance/mark")
def mark_remedial_attendance(
    payload: schemas.RemedialAttendanceMark,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.STUDENT)),
):
    if current_user.role == models.UserRole.STUDENT:
        if not current_user.student_id:
            raise HTTPException(status_code=403, detail="Student account is not linked correctly")
        if current_user.student_id != payload.student_id:
            raise HTTPException(status_code=403, detail="Students can only mark their own attendance")

    class_row = (
        db.query(models.MakeUpClass)
        .filter(
            models.MakeUpClass.remedial_code == str(payload.remedial_code or "").strip().upper(),
            models.MakeUpClass.is_active.is_(True),
        )
        .first()
    )
    if not class_row:
        raise HTTPException(status_code=404, detail="Invalid or inactive remedial code")

    student = db.get(models.Student, payload.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    student_section = _student_section(student)

    sections = set(_parse_sections_json(class_row.sections_json))
    if student_section not in sections:
        raise HTTPException(status_code=403, detail="Unauthorized section for this remedial class")

    if not _student_has_remedial_access(db, student_id=payload.student_id, class_row=class_row):
        raise HTTPException(status_code=400, detail="Student is not enrolled in this course")

    class_start, _ = _class_datetimes(class_row)
    now_dt = datetime.now()
    if now_dt < class_start:
        raise HTTPException(status_code=400, detail="Attendance is not open yet for this remedial class")

    window_close = _attendance_window_close(class_row)
    if now_dt > window_close:
        raise HTTPException(status_code=400, detail="Attendance window closed (only first 15 minutes)")

    if class_row.code_expires_at and now_dt > class_row.code_expires_at:
        raise HTTPException(status_code=400, detail="Remedial code expired")

    existing = (
        db.query(models.RemedialAttendance)
        .filter(
            models.RemedialAttendance.makeup_class_id == class_row.id,
            models.RemedialAttendance.student_id == payload.student_id,
        )
        .first()
    )
    if existing:
        return {"message": "Attendance already marked", "makeup_class_id": class_row.id}

    verification_confidence = None
    verification_engine = None
    verification_reason = None
    source = "remedial-code"
    if current_user.role == models.UserRole.STUDENT:
        _, verification_confidence, verification_engine, verification_reason = _verify_remedial_face_payload(
            student=student,
            payload=payload,
            class_row=class_row,
        )
        source = "remedial-face-opencv-verified"

    attendance_row = models.RemedialAttendance(
        makeup_class_id=class_row.id,
        student_id=payload.student_id,
        source=source,
    )
    db.add(attendance_row)
    db.commit()
    db.refresh(attendance_row)

    mirror_document(
        "remedial_attendance",
        {
            "id": attendance_row.id,
            "attendance_id": attendance_row.id,
            "makeup_class_id": attendance_row.makeup_class_id,
            "student_id": attendance_row.student_id,
            "source": attendance_row.source,
            "marked_at": attendance_row.marked_at,
            "verification_confidence": verification_confidence,
            "verification_engine": verification_engine,
            "verification_reason": verification_reason,
            "recorded_at": datetime.utcnow(),
        },
        upsert_filter={"id": attendance_row.id},
    )
    mirror_event(
        "remedial.attendance_marked",
        {
            "class_id": class_row.id,
            "course_id": class_row.course_id,
            "student_id": payload.student_id,
            "section": student_section,
            "marked_at": attendance_row.marked_at,
            "verification_confidence": verification_confidence,
            "verification_engine": verification_engine,
            "verification_reason": verification_reason,
        },
        actor={
            "user_id": current_user.id,
            "role": current_user.role.value,
            "student_id": current_user.student_id,
        },
    )

    return {
        "message": "Remedial attendance marked",
        "makeup_class_id": class_row.id,
        "class_mode": class_row.class_mode,
        "online_link": _resolved_online_link(class_row),
        "verification_confidence": verification_confidence,
        "verification_engine": verification_engine,
        "verification_reason": verification_reason,
    }


@router.get("/attendance/history", response_model=list[schemas.RemedialAttendanceHistoryItemOut])
def get_student_remedial_attendance_history(
    limit: int = Query(default=80, ge=1, le=300),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    query_limit = min(max(int(limit) * 4, int(limit)), 1200)
    rows = (
        db.query(models.MakeUpClass, models.Course, models.RemedialAttendance, models.RemedialMessage)
        .outerjoin(
            models.Course,
            models.Course.id == models.MakeUpClass.course_id,
        )
        .outerjoin(
            models.RemedialAttendance,
            (models.RemedialAttendance.makeup_class_id == models.MakeUpClass.id)
            & (models.RemedialAttendance.student_id == current_user.student_id),
        )
        .outerjoin(
            models.RemedialMessage,
            (models.RemedialMessage.makeup_class_id == models.MakeUpClass.id)
            & (models.RemedialMessage.student_id == current_user.student_id),
        )
        .filter(
            (models.RemedialAttendance.id.isnot(None))
            | (models.RemedialMessage.id.isnot(None))
        )
        .order_by(
            models.MakeUpClass.class_date.desc(),
            models.MakeUpClass.start_time.desc(),
            models.MakeUpClass.id.desc(),
        )
        .limit(query_limit)
        .all()
    )

    now_dt = datetime.now()
    out: list[schemas.RemedialAttendanceHistoryItemOut] = []
    for class_row, course_row, attendance_row, _message_row in rows:
        if not bool(class_row.is_active) and attendance_row is None:
            continue
        if attendance_row:
            status_value = "present"
            marked_at_value = attendance_row.marked_at
            source_value = attendance_row.source or "remedial-code"
        else:
            # Show classes as absent only after the attendance window has closed.
            class_start, _ = _class_datetimes(class_row)
            window_minutes = max(1, int(class_row.attendance_open_minutes or REMEDIAL_ATTENDANCE_WINDOW_MINUTES))
            window_end = class_start + timedelta(minutes=window_minutes)
            if now_dt <= window_end:
                continue
            status_value = "absent"
            marked_at_value = None
            source_value = None

        out.append(
            schemas.RemedialAttendanceHistoryItemOut(
                class_id=class_row.id,
                course_id=class_row.course_id,
                course_code=(course_row.code if course_row else f"C-{class_row.course_id}"),
                course_title=(course_row.title if course_row else "Course"),
                class_date=class_row.class_date,
                start_time=class_row.start_time,
                end_time=class_row.end_time,
                class_mode=class_row.class_mode or "offline",
                room_number=class_row.room_number,
                online_link=_resolved_online_link(class_row),
                status=status_value,
                marked_at=marked_at_value,
                source=source_value,
            )
        )
        if len(out) >= int(limit):
            break
    return out

@router.get("/classes/{class_id}/attendance")
def get_makeup_class_attendance(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    class_row = db.get(models.MakeUpClass, class_id)
    if not class_row:
        raise HTTPException(status_code=404, detail="Make-up class not found")
    _ensure_faculty_can_manage_class(db, current_user=current_user, class_row=class_row)

    records = (
        db.query(models.RemedialAttendance)
        .filter(models.RemedialAttendance.makeup_class_id == class_id)
        .all()
    )

    target_sections = [_normalized_section_token(item) for item in _parse_sections_json(class_row.sections_json) if item]
    target_section_set = set(target_sections)
    if target_section_set:
        target_students = (
            db.query(models.Student)
            .filter(models.Student.section.in_(target_section_set))
            .order_by(models.Student.section.asc(), models.Student.name.asc(), models.Student.id.asc())
            .all()
        )
        # Fallback for legacy section values that may include spacing/casing differences.
        if not target_students:
            all_students = (
                db.query(models.Student)
                .filter(models.Student.section.is_not(None))
                .order_by(models.Student.name.asc(), models.Student.id.asc())
                .all()
            )
            target_students = [
                row for row in all_students if _normalized_section_token(row.section) in target_section_set
            ]
    else:
        target_students = []

    attendance_by_student_id: dict[int, models.RemedialAttendance] = {}
    for record in records:
        attendance_by_student_id[int(record.student_id)] = record

    section_students_map: dict[str, list[dict]] = {section: [] for section in target_sections}
    all_students: list[dict] = []
    marked_students: list[dict] = []
    for student in target_students:
        section_token = _normalized_section_token(student.section)
        if not section_token:
            continue
        attendance_row = attendance_by_student_id.get(int(student.id))
        student_payload = {
            "student_id": student.id,
            "student_name": student.name,
            "student_section": section_token,
            "marked": attendance_row is not None,
            "status": "marked" if attendance_row else "not_marked",
            "marked_at": attendance_row.marked_at if attendance_row else None,
            "source": attendance_row.source if attendance_row else None,
        }
        section_students_map.setdefault(section_token, []).append(student_payload)
        all_students.append(student_payload)
        if attendance_row is not None:
            marked_students.append(student_payload)

    section_summaries: list[dict] = []
    for section in target_sections:
        section_students = section_students_map.get(section, [])
        marked_count = sum(1 for item in section_students if item.get("marked"))
        section_summaries.append(
            {
                "section": section,
                "total_students": len(section_students),
                "marked_students": marked_count,
                "not_marked_students": len(section_students) - marked_count,
                "students": section_students,
            }
        )

    return {
        "class_id": class_row.id,
        "course_id": class_row.course_id,
        "sections": target_sections,
        "remedial_code": class_row.remedial_code,
        "attendance_count": len(marked_students),
        "student_count": len(all_students),
        "not_marked_count": max(0, len(all_students) - len(marked_students)),
        "section_summaries": section_summaries,
        "students": marked_students,
        "all_students": all_students,
    }
