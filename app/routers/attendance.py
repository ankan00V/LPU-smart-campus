import hashlib
import json
import logging
import math
import os
import re
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth_utils import get_current_user, require_roles
from ..database import get_db
from ..default_timetable import DEFAULT_TIMETABLE_BLUEPRINT
from ..face_verification import (
    build_enrollment_template_from_frames,
    build_profile_face_template,
    verify_face_sequence_opencv,
)
from ..mongo import get_mongo_db, mirror_document

router = APIRouter(prefix="/attendance", tags=["Attendance Management"])
logger = logging.getLogger(__name__)

PROFILE_PHOTO_LOCK_DAYS = 14
PROFILE_PHOTO_LOCK_MESSAGE = "Profile photo can only be changed once every 14 days. Please try again later."
ENROLLMENT_VIDEO_LOCK_DAYS = 14
ENROLLMENT_VIDEO_LOCK_MESSAGE = "Enrollment video can only be updated once every 14 days. Please try again later."
REGISTRATION_IMMUTABLE_MESSAGE = (
    "Registration number is permanent and can't be changed without admin permissions."
)
FACE_MATCH_PASS_THRESHOLD = max(
    0.80,
    min(0.99, float(os.getenv("FACE_MATCH_PASS_THRESHOLD", "0.80"))),
)
FACE_MULTI_FRAME_MIN = max(5, int(os.getenv("FACE_MATCH_MIN_FRAMES", "6")))
ACADEMIC_START_DATE_DEFAULT = "2026-01-21"


def _academic_start_date() -> date:
    raw = (os.getenv("ACADEMIC_START_DATE", ACADEMIC_START_DATE_DEFAULT) or "").strip()
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return date.fromisoformat(ACADEMIC_START_DATE_DEFAULT)


def _time_from_hhmm(value: str) -> time:
    parts = value.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid HH:MM time format: {value}")
    return time(hour=int(parts[0]), minute=int(parts[1]))


def _client_ai_verdict(payload: schemas.RealtimeAttendanceMarkRequest) -> dict | None:
    if payload.ai_match is None or payload.ai_confidence is None:
        return None
    confidence = max(0.0, min(1.0, float(payload.ai_confidence)))
    return {
        "available": True,
        "match": bool(payload.ai_match),
        "confidence": confidence,
        "engine": payload.ai_model or "ai-client",
        "reason": payload.ai_reason or "Client AI verdict",
    }


def _week_start_for(target_date: date) -> date:
    return target_date - timedelta(days=target_date.weekday())


def _class_datetime_bounds(schedule: models.ClassSchedule, class_date: date) -> tuple[datetime, datetime]:
    class_start = datetime.combine(class_date, schedule.start_time)
    class_end = datetime.combine(class_date, schedule.end_time)
    return class_start, class_end


def _count_delivered_occurrences(
    schedule: models.ClassSchedule,
    *,
    from_date: date,
    now_dt: datetime,
) -> int:
    if from_date > now_dt.date():
        return 0

    start_offset = (schedule.weekday - from_date.weekday()) % 7
    first_class_date = from_date + timedelta(days=start_offset)
    if first_class_date > now_dt.date():
        return 0

    total = ((now_dt.date() - first_class_date).days // 7) + 1
    if total <= 0:
        return 0

    # Count once class has started; only upcoming classes are excluded.
    if now_dt.date().weekday() == schedule.weekday and now_dt.time() < schedule.start_time:
        total -= 1

    return max(0, total)


def _window_flags(
    schedule: models.ClassSchedule,
    now_dt: datetime,
    class_date: date,
    *,
    course: models.Course | None = None,
) -> tuple[bool, bool, bool]:
    class_start, class_end = _class_datetime_bounds(schedule, class_date)
    window_end = class_start + timedelta(minutes=10)
    is_open = class_start <= now_dt <= window_end
    is_active = class_start <= now_dt <= class_end
    is_ended = now_dt > class_end
    return is_open, is_active, is_ended


def _normalize_registration_number(value: str) -> str:
    normalized = re.sub(r"\s+", "", value.strip().upper())
    if len(normalized) < 3:
        raise HTTPException(status_code=400, detail="registration_number must be at least 3 characters")
    if not re.fullmatch(r"[A-Z0-9/-]+", normalized):
        raise HTTPException(
            status_code=400,
            detail="registration_number can contain only letters, numbers, slash, and hyphen",
        )
    return normalized


def _sync_student_to_mongo(student: models.Student, *, source: str) -> None:
    _upsert_mongo_by_id(
        "students",
        student.id,
        {
            "name": student.name,
            "email": student.email,
            "registration_number": student.registration_number,
            "parent_email": student.parent_email,
            "profile_photo_data_url": student.profile_photo_data_url,
            "profile_photo_updated_at": student.profile_photo_updated_at,
            "profile_photo_locked_until": student.profile_photo_locked_until,
            "profile_face_template_json": student.profile_face_template_json,
            "profile_face_template_updated_at": student.profile_face_template_updated_at,
            "enrollment_video_template_json": student.enrollment_video_template_json,
            "enrollment_video_updated_at": student.enrollment_video_updated_at,
            "enrollment_video_locked_until": student.enrollment_video_locked_until,
            "department": student.department,
            "semester": student.semester,
            "created_at": student.created_at,
            "source": source,
        },
    )


def _student_profile_out(student: models.Student) -> schemas.StudentProfileOut:
    can_update_now, locked_until, lock_days_remaining = _photo_lock_state(student)
    return schemas.StudentProfileOut(
        student_id=student.id,
        name=student.name,
        email=student.email,
        registration_number=student.registration_number,
        parent_email=student.parent_email,
        department=student.department,
        semester=student.semester,
        has_profile_photo=bool(student.profile_photo_data_url),
        photo_data_url=student.profile_photo_data_url,
        can_update_photo_now=can_update_now,
        photo_locked_until=locked_until,
        photo_lock_days_remaining=lock_days_remaining,
    )


def _student_photo_out(student: models.Student) -> schemas.StudentProfilePhotoOut:
    can_update_now, locked_until, lock_days_remaining = _photo_lock_state(student)
    return schemas.StudentProfilePhotoOut(
        has_profile_photo=bool(student.profile_photo_data_url),
        photo_data_url=student.profile_photo_data_url,
        can_update_now=can_update_now,
        locked_until=locked_until,
        lock_days_remaining=lock_days_remaining,
        registration_number=student.registration_number,
    )


def _apply_student_profile_update(
    student: models.Student,
    payload: schemas.StudentProfileUpdateRequest,
    *,
    db: Session,
) -> tuple[bool, bool]:
    changed = False
    photo_changed = False
    now_dt = datetime.utcnow()

    if payload.registration_number is not None:
        registration_number = _normalize_registration_number(payload.registration_number)
        existing_registration = (student.registration_number or "").strip().upper()
        if existing_registration and registration_number != existing_registration:
            raise HTTPException(status_code=403, detail=REGISTRATION_IMMUTABLE_MESSAGE)
        if not existing_registration:
            student.registration_number = registration_number
            changed = True

    if payload.photo_data_url is not None:
        incoming_photo = payload.photo_data_url.strip()
        if not incoming_photo.startswith("data:image/"):
            raise HTTPException(status_code=400, detail="photo_data_url must be an image data URL")

        can_update_now, _, _ = _photo_lock_state(student, now_dt)
        existing_photo = (student.profile_photo_data_url or "").strip()
        if existing_photo and incoming_photo != existing_photo and not can_update_now:
            raise HTTPException(status_code=423, detail=PROFILE_PHOTO_LOCK_MESSAGE)

        if incoming_photo != existing_photo:
            if existing_photo:
                # Replace policy: drop the previous snapshot before persisting the new one.
                student.profile_photo_data_url = None
                db.flush()
            student.profile_photo_data_url = incoming_photo
            student.profile_photo_updated_at = now_dt
            student.profile_photo_locked_until = now_dt + timedelta(days=PROFILE_PHOTO_LOCK_DAYS)
            changed = True
            photo_changed = True

    return changed, photo_changed


def _photo_fingerprint(photo_data_url: str | None) -> str | None:
    if not photo_data_url:
        return None
    return hashlib.sha256(photo_data_url.encode("utf-8")).hexdigest()


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


def _rebuild_profile_face_template(student: models.Student) -> None:
    if not student.profile_photo_data_url:
        student.profile_face_template_json = None
        student.profile_face_template_updated_at = None
        return

    try:
        template = build_profile_face_template(student.profile_photo_data_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid enrollment face photo: {exc}") from exc

    student.profile_face_template_json = json.dumps(template)
    student.profile_face_template_updated_at = datetime.utcnow()


def _upsert_mongo_by_id(collection: str, doc_id: int, payload: dict) -> None:
    try:
        mongo_db = get_mongo_db(required=True)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    body = dict(payload)
    body["id"] = doc_id
    mongo_db[collection].update_one({"id": doc_id}, {"$set": body}, upsert=True)


def _upsert_present_attendance(
    db: Session,
    *,
    student_id: int,
    course_id: int,
    faculty_id: int,
    class_date: date,
    source: str,
) -> None:
    existing = (
        db.query(models.AttendanceRecord)
        .filter(
            models.AttendanceRecord.student_id == student_id,
            models.AttendanceRecord.course_id == course_id,
            models.AttendanceRecord.attendance_date == class_date,
        )
        .first()
    )

    if existing:
        existing.status = models.AttendanceStatus.PRESENT
        existing.source = source
        existing.marked_by_faculty_id = faculty_id
        return

    db.add(
        models.AttendanceRecord(
            student_id=student_id,
            course_id=course_id,
            marked_by_faculty_id=faculty_id,
            attendance_date=class_date,
            status=models.AttendanceStatus.PRESENT,
            source=source,
        )
    )


_CREDITED_SUBMISSION_STATUSES = (
    models.AttendanceSubmissionStatus.VERIFIED,
    models.AttendanceSubmissionStatus.APPROVED,
)


def _is_submission_credited(status_value: models.AttendanceSubmissionStatus | str | None) -> bool:
    if status_value is None:
        return False
    try:
        normalized = (
            status_value
            if isinstance(status_value, models.AttendanceSubmissionStatus)
            else models.AttendanceSubmissionStatus(str(status_value))
        )
    except ValueError:
        return False
    return normalized in _CREDITED_SUBMISSION_STATUSES


def _photo_lock_state(student: models.Student, now_dt: datetime | None = None) -> tuple[bool, datetime | None, int]:
    now_dt = now_dt or datetime.utcnow()
    locked_until = student.profile_photo_locked_until
    if not locked_until or now_dt >= locked_until:
        return True, locked_until, 0

    remaining_days = math.ceil((locked_until - now_dt).total_seconds() / 86400)
    return False, locked_until, max(0, remaining_days)


def _enrollment_lock_state(student: models.Student, now_dt: datetime | None = None) -> tuple[bool, datetime | None, int]:
    now_dt = now_dt or datetime.utcnow()
    locked_until = student.enrollment_video_locked_until
    if not locked_until or now_dt >= locked_until:
        return True, locked_until, 0

    remaining_days = math.ceil((locked_until - now_dt).total_seconds() / 86400)
    return False, locked_until, max(0, remaining_days)


def _student_enrollment_status_out(student: models.Student) -> schemas.StudentEnrollmentStatusOut:
    can_update_now, locked_until, lock_days_remaining = _enrollment_lock_state(student)
    return schemas.StudentEnrollmentStatusOut(
        has_enrollment_video=bool(student.enrollment_video_template_json),
        can_update_now=can_update_now,
        locked_until=locked_until,
        lock_days_remaining=lock_days_remaining,
        enrollment_updated_at=student.enrollment_video_updated_at,
    )


def _ensure_default_timetable_for_student(db: Session, student: models.Student) -> dict[str, int]:
    created = {
        "faculty": 0,
        "courses": 0,
        "classrooms": 0,
        "schedules": 0,
        "enrollments": 0,
        "total_classes": len(DEFAULT_TIMETABLE_BLUEPRINT),
    }
    default_course_ids: set[int] = set()

    for item in DEFAULT_TIMETABLE_BLUEPRINT:
        faculty = db.query(models.Faculty).filter(models.Faculty.email == item["faculty_email"]).first()
        if not faculty:
            faculty = models.Faculty(
                name=item["faculty_name"],
                email=item["faculty_email"],
                department=student.department,
            )
            db.add(faculty)
            db.flush()
            created["faculty"] += 1
        _upsert_mongo_by_id(
            "faculty",
            faculty.id,
            {
                "name": faculty.name,
                "email": faculty.email,
                "department": faculty.department,
                "created_at": faculty.created_at,
                "source": "default-timetable-loader",
            },
        )

        course = db.query(models.Course).filter(models.Course.code == item["course_code"]).first()
        if not course:
            course = models.Course(
                code=item["course_code"],
                title=item["course_title"],
                faculty_id=faculty.id,
            )
            db.add(course)
            db.flush()
            created["courses"] += 1
        else:
            course.title = item["course_title"]
            course.faculty_id = faculty.id
        _upsert_mongo_by_id(
            "courses",
            course.id,
            {
                "code": course.code,
                "title": course.title,
                "faculty_id": course.faculty_id,
                "source": "default-timetable-loader",
            },
        )
        default_course_ids.add(course.id)

        classroom = (
            db.query(models.Classroom)
            .filter(
                models.Classroom.block == item["classroom_block"],
                models.Classroom.room_number == item["classroom_room"],
            )
            .first()
        )
        if not classroom:
            classroom = models.Classroom(
                block=item["classroom_block"],
                room_number=item["classroom_room"],
                capacity=70,
            )
            db.add(classroom)
            db.flush()
            created["classrooms"] += 1
        _upsert_mongo_by_id(
            "classrooms",
            classroom.id,
            {
                "block": classroom.block,
                "room_number": classroom.room_number,
                "capacity": classroom.capacity,
                "source": "default-timetable-loader",
            },
        )

        assignment = (
            db.query(models.CourseClassroom)
            .filter(models.CourseClassroom.course_id == course.id)
            .first()
        )
        if not assignment:
            assignment = models.CourseClassroom(course_id=course.id, classroom_id=classroom.id)
            db.add(assignment)
            db.flush()
        else:
            assignment.classroom_id = classroom.id
        _upsert_mongo_by_id(
            "course_classrooms",
            assignment.id,
            {
                "course_id": assignment.course_id,
                "classroom_id": assignment.classroom_id,
                "source": "default-timetable-loader",
            },
        )

        start_t = _time_from_hhmm(item["start"])
        end_t = _time_from_hhmm(item["end"])
        schedule = (
            db.query(models.ClassSchedule)
            .filter(
                models.ClassSchedule.course_id == course.id,
                models.ClassSchedule.weekday == item["weekday"],
                models.ClassSchedule.start_time == start_t,
            )
            .first()
        )
        if not schedule:
            schedule = models.ClassSchedule(
                course_id=course.id,
                faculty_id=faculty.id,
                weekday=item["weekday"],
                start_time=start_t,
                end_time=end_t,
                classroom_label=item["classroom_label"],
                is_active=True,
            )
            db.add(schedule)
            db.flush()
            created["schedules"] += 1
        else:
            schedule.faculty_id = faculty.id
            schedule.end_time = end_t
            schedule.classroom_label = item["classroom_label"]
            schedule.is_active = True
        _upsert_mongo_by_id(
            "class_schedules",
            schedule.id,
            {
                "course_id": schedule.course_id,
                "faculty_id": schedule.faculty_id,
                "weekday": schedule.weekday,
                "start_time": str(schedule.start_time),
                "end_time": str(schedule.end_time),
                "classroom_label": schedule.classroom_label,
                "is_active": schedule.is_active,
                "created_at": schedule.created_at,
                "source": "default-timetable-loader",
            },
        )

        enrollment = (
            db.query(models.Enrollment)
            .filter(
                models.Enrollment.student_id == student.id,
                models.Enrollment.course_id == course.id,
            )
            .first()
        )
        if not enrollment:
            enrollment = models.Enrollment(student_id=student.id, course_id=course.id)
            db.add(enrollment)
            db.flush()
            created["enrollments"] += 1
        _upsert_mongo_by_id(
            "enrollments",
            enrollment.id,
            {
                "student_id": enrollment.student_id,
                "course_id": enrollment.course_id,
                "created_at": enrollment.created_at,
                "source": "default-timetable-loader",
            },
        )

    stale_enrollments = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.student_id == student.id)
        .filter(~models.Enrollment.course_id.in_(default_course_ids))
        .all()
    )
    for stale in stale_enrollments:
        db.delete(stale)
        mongo_db = get_mongo_db()
        if mongo_db is not None:
            mongo_db["enrollments"].delete_many(
                {
                    "student_id": student.id,
                    "course_id": stale.course_id,
                }
            )

    return created


@router.post("/schedules", response_model=schemas.ClassScheduleOut, status_code=status.HTTP_201_CREATED)
def create_schedule(
    payload: schemas.ClassScheduleCreate,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    course = db.get(models.Course, payload.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="end_time must be later than start_time")

    if current_user.role == models.UserRole.FACULTY:
        if current_user.faculty_id != payload.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty can only schedule classes for their own ID")

    if course.faculty_id != payload.faculty_id:
        raise HTTPException(status_code=400, detail="Faculty is not assigned to this course")

    existing = (
        db.query(models.ClassSchedule)
        .filter(
            models.ClassSchedule.course_id == payload.course_id,
            models.ClassSchedule.weekday == payload.weekday,
            models.ClassSchedule.start_time == payload.start_time,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Schedule already exists for this course and start time")

    schedule = models.ClassSchedule(**payload.model_dump())
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    _upsert_mongo_by_id(
        "class_schedules",
        schedule.id,
        {
            "course_id": schedule.course_id,
            "faculty_id": schedule.faculty_id,
            "weekday": schedule.weekday,
            "start_time": str(schedule.start_time),
            "end_time": str(schedule.end_time),
            "classroom_label": schedule.classroom_label,
            "is_active": schedule.is_active,
            "source": "api",
            "created_at": schedule.created_at,
        },
    )

    return schedule


@router.get("/schedules", response_model=list[schemas.ClassScheduleOut])
def list_schedules(
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.STUDENT)
    ),
):
    query = db.query(models.ClassSchedule).filter(models.ClassSchedule.is_active.is_(True))

    if current_user.role == models.UserRole.FACULTY:
        query = query.filter(models.ClassSchedule.faculty_id == current_user.faculty_id)

    if current_user.role == models.UserRole.STUDENT:
        if not current_user.student_id:
            raise HTTPException(status_code=403, detail="Student account is not linked correctly")
        course_ids = (
            db.query(models.Enrollment.course_id)
            .filter(models.Enrollment.student_id == current_user.student_id)
            .all()
        )
        enrolled_course_ids = [row.course_id for row in course_ids]
        if not enrolled_course_ids:
            return []
        query = query.filter(models.ClassSchedule.course_id.in_(enrolled_course_ids))

    return query.order_by(models.ClassSchedule.weekday.asc(), models.ClassSchedule.start_time.asc()).all()


@router.post("/student/default-timetable", response_model=schemas.DefaultTimetableLoadResponse)
def load_default_student_timetable(
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    student = db.get(models.Student, current_user.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    created = _ensure_default_timetable_for_student(db, student)
    db.commit()

    mirror_document(
        "student_default_timetable_loads",
        {
            "student_id": student.id,
            "student_email": student.email,
            "created_faculty": created["faculty"],
            "created_courses": created["courses"],
            "created_classrooms": created["classrooms"],
            "created_schedules": created["schedules"],
            "created_enrollments": created["enrollments"],
            "total_classes": created["total_classes"],
            "loaded_at": datetime.utcnow(),
            "source": "student-portal",
        },
    )

    return schemas.DefaultTimetableLoadResponse(
        message="Default timetable loaded",
        created_faculty=created["faculty"],
        created_courses=created["courses"],
        created_classrooms=created["classrooms"],
        created_schedules=created["schedules"],
        created_enrollments=created["enrollments"],
        total_classes=created["total_classes"],
    )


@router.get("/student/profile-photo", response_model=schemas.StudentProfilePhotoOut)
def get_student_profile_photo(
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    student = db.get(models.Student, current_user.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    return _student_photo_out(student)


@router.get("/student/profile", response_model=schemas.StudentProfileOut)
def get_student_profile(
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    student = db.get(models.Student, current_user.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    return _student_profile_out(student)


@router.put("/student/profile", response_model=schemas.StudentProfileOut)
def update_student_profile(
    payload: schemas.StudentProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    student = db.get(models.Student, current_user.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if payload.registration_number is None and payload.photo_data_url is None:
        raise HTTPException(status_code=400, detail="Provide registration_number and/or photo_data_url")

    changed, photo_changed = _apply_student_profile_update(student, payload, db=db)
    if photo_changed:
        _rebuild_profile_face_template(student)
        changed = True
    if changed:
        db.commit()
    else:
        db.flush()

    _sync_student_to_mongo(student, source="student-profile-update")

    mirror_document(
        "student_profile_faces",
        {
            "student_id": student.id,
            "registration_number": student.registration_number,
            "profile_photo_fingerprint": _photo_fingerprint(student.profile_photo_data_url),
            "profile_photo_size": len(student.profile_photo_data_url or ""),
            "profile_photo_updated_at": student.profile_photo_updated_at,
            "profile_photo_locked_until": student.profile_photo_locked_until,
            "profile_face_template_fingerprint": _photo_fingerprint(student.profile_face_template_json),
            "profile_face_template_updated_at": student.profile_face_template_updated_at,
            "source": "student-portal",
            "updated_at": datetime.utcnow(),
        },
        upsert_filter={"student_id": student.id},
    )

    return _student_profile_out(student)


@router.put("/student/profile-photo", response_model=schemas.StudentProfilePhotoOut)
def update_student_profile_photo(
    payload: schemas.StudentProfilePhotoUpdate,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    student = db.get(models.Student, current_user.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    changed, photo_changed = _apply_student_profile_update(
        student,
        schemas.StudentProfileUpdateRequest(photo_data_url=payload.photo_data_url),
        db=db,
    )
    if photo_changed:
        _rebuild_profile_face_template(student)
        changed = True
    if changed:
        db.commit()
    else:
        db.flush()

    _sync_student_to_mongo(student, source="student-profile-update")

    mirror_document(
        "student_profile_faces",
        {
            "student_id": student.id,
            "profile_photo_fingerprint": _photo_fingerprint(student.profile_photo_data_url),
            "profile_photo_size": len(student.profile_photo_data_url or ""),
            "profile_photo_updated_at": student.profile_photo_updated_at,
            "profile_photo_locked_until": student.profile_photo_locked_until,
            "profile_face_template_fingerprint": _photo_fingerprint(student.profile_face_template_json),
            "profile_face_template_updated_at": student.profile_face_template_updated_at,
            "source": "student-portal",
            "updated_at": datetime.utcnow(),
        },
        upsert_filter={"student_id": student.id},
    )

    return _student_photo_out(student)


@router.get("/student/enrollment-status", response_model=schemas.StudentEnrollmentStatusOut)
def get_student_enrollment_status(
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")
    student = db.get(models.Student, current_user.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return _student_enrollment_status_out(student)


@router.put("/student/enrollment-video", response_model=schemas.StudentEnrollmentVideoOut)
def upsert_student_enrollment_video(
    payload: schemas.StudentEnrollmentVideoRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")
    student = db.get(models.Student, current_user.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if not student.registration_number or not student.profile_photo_data_url:
        raise HTTPException(
            status_code=400,
            detail="Complete profile setup (registration number + face photo) before enrollment video",
        )

    can_update_now, _, lock_days_remaining = _enrollment_lock_state(student)
    if student.enrollment_video_template_json and not can_update_now:
        raise HTTPException(
            status_code=423,
            detail=f"Enrollment video can only be updated after {lock_days_remaining} day(s).",
        )

    now_dt = datetime.utcnow()
    try:
        template = build_enrollment_template_from_frames(payload.frames_data_urls)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    student.enrollment_video_template_json = json.dumps(template)
    student.enrollment_video_updated_at = now_dt
    student.enrollment_video_locked_until = now_dt + timedelta(days=ENROLLMENT_VIDEO_LOCK_DAYS)
    db.commit()

    _sync_student_to_mongo(student, source="student-enrollment-video-update")

    quality = template.get("quality", {}) if isinstance(template, dict) else {}
    valid_frames_used = int(quality.get("valid_frames_used", 0) or 0)
    total_frames_received = int(quality.get("frames_received", len(payload.frames_data_urls)) or len(payload.frames_data_urls))
    mirror_document(
        "student_enrollment_videos",
        {
            "student_id": student.id,
            "registration_number": student.registration_number,
            "enrollment_template_fingerprint": _photo_fingerprint(student.enrollment_video_template_json),
            "enrollment_updated_at": student.enrollment_video_updated_at,
            "enrollment_locked_until": student.enrollment_video_locked_until,
            "valid_frames_used": valid_frames_used,
            "total_frames_received": total_frames_received,
            "source": "student-portal-enrollment-video",
            "updated_at": datetime.utcnow(),
        },
        upsert_filter={"student_id": student.id},
    )

    status_out = _student_enrollment_status_out(student)
    return schemas.StudentEnrollmentVideoOut(
        message="Enrollment video saved successfully",
        valid_frames_used=valid_frames_used,
        total_frames_received=total_frames_received,
        **status_out.model_dump(),
    )


@router.get("/student/timetable", response_model=schemas.WeeklyTimetableOut)
def get_student_weekly_timetable(
    week_start: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    student = db.get(models.Student, current_user.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    created = _ensure_default_timetable_for_student(db, student)
    if any(
        created[key]
        for key in ("faculty", "courses", "classrooms", "schedules", "enrollments")
    ):
        db.commit()
    else:
        db.flush()

    today = date.today()
    academic_start = _academic_start_date()
    min_week_start = _week_start_for(academic_start)
    requested_week_start = _week_start_for(week_start or today)
    current_week_start = max(requested_week_start, min_week_start)

    enrollments = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.student_id == current_user.student_id)
        .all()
    )
    course_ids = [item.course_id for item in enrollments]
    if not course_ids:
        return schemas.WeeklyTimetableOut(
            week_start=current_week_start,
            min_navigable_date=academic_start,
            classes=[],
        )

    schedules = (
        db.query(models.ClassSchedule)
        .filter(
            models.ClassSchedule.is_active.is_(True),
            models.ClassSchedule.course_id.in_(course_ids),
        )
        .order_by(models.ClassSchedule.weekday.asc(), models.ClassSchedule.start_time.asc())
        .all()
    )

    now_dt = datetime.now()
    result: list[schemas.TimetableClassOut] = []

    for schedule in schedules:
        course = db.get(models.Course, schedule.course_id)
        if not course:
            continue

        class_date = current_week_start + timedelta(days=schedule.weekday)
        if class_date < academic_start:
            continue
        is_open_now, is_active_now, is_ended_now = _window_flags(
            schedule,
            now_dt,
            class_date,
            course=course,
        )

        submission = (
            db.query(models.AttendanceSubmission)
            .filter(
                models.AttendanceSubmission.schedule_id == schedule.id,
                models.AttendanceSubmission.student_id == current_user.student_id,
                models.AttendanceSubmission.class_date == class_date,
            )
            .first()
        )

        result.append(
            schemas.TimetableClassOut(
                schedule_id=schedule.id,
                course_id=schedule.course_id,
                course_code=course.code,
                course_title=course.title,
                weekday=schedule.weekday,
                start_time=schedule.start_time,
                end_time=schedule.end_time,
                classroom_label=schedule.classroom_label,
                class_date=class_date,
                is_open_now=is_open_now,
                is_active_now=is_active_now,
                is_ended_now=is_ended_now,
                attendance_status=submission.status.value if submission else None,
            )
        )

    return schemas.WeeklyTimetableOut(
        week_start=current_week_start,
        min_navigable_date=academic_start,
        classes=result,
    )


@router.get("/student/attendance-history", response_model=schemas.StudentAttendanceHistoryOut)
def get_student_attendance_history(
    limit: int = Query(default=40, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    fetch_limit = min(365, max(limit * 3, 80))
    submissions = (
        db.query(models.AttendanceSubmission)
        .filter(
            models.AttendanceSubmission.student_id == current_user.student_id,
            models.AttendanceSubmission.status.in_(_CREDITED_SUBMISSION_STATUSES),
        )
        .order_by(
            models.AttendanceSubmission.class_date.desc(),
            models.AttendanceSubmission.submitted_at.desc(),
            models.AttendanceSubmission.id.desc(),
        )
        .limit(fetch_limit)
        .all()
    )

    submission_course_day_keys = {(item.course_id, item.class_date) for item in submissions}
    records = (
        db.query(models.AttendanceRecord)
        .filter(models.AttendanceRecord.student_id == current_user.student_id)
        .order_by(models.AttendanceRecord.attendance_date.desc(), models.AttendanceRecord.id.desc())
        .limit(fetch_limit)
        .all()
    )
    fallback_records = [
        item
        for item in records
        if (item.course_id, item.attendance_date) not in submission_course_day_keys
    ]

    if not submissions and not fallback_records:
        return schemas.StudentAttendanceHistoryOut(records=[])

    course_ids = sorted(
        {
            *[item.course_id for item in submissions],
            *[item.course_id for item in fallback_records],
        }
    )
    courses = (
        {row.id: row for row in db.query(models.Course).filter(models.Course.id.in_(course_ids)).all()}
        if course_ids
        else {}
    )

    faculty_ids = sorted(
        {
            *[item.faculty_id for item in submissions if item.faculty_id is not None],
            *[item.marked_by_faculty_id for item in fallback_records if item.marked_by_faculty_id is not None],
            *[course.faculty_id for course in courses.values() if course.faculty_id is not None],
        }
    )
    faculties = (
        {row.id: row for row in db.query(models.Faculty).filter(models.Faculty.id.in_(faculty_ids)).all()}
        if faculty_ids
        else {}
    )

    schedule_ids = sorted({item.schedule_id for item in submissions})
    schedules_by_id = (
        {
            row.id: row
            for row in db.query(models.ClassSchedule).filter(models.ClassSchedule.id.in_(schedule_ids)).all()
        }
        if schedule_ids
        else {}
    )
    fallback_schedules = (
        db.query(models.ClassSchedule)
        .filter(models.ClassSchedule.course_id.in_(course_ids))
        .order_by(models.ClassSchedule.start_time.asc())
        .all()
        if course_ids
        else []
    )
    schedule_map: dict[tuple[int, int], models.ClassSchedule] = {}
    for schedule in fallback_schedules:
        schedule_map.setdefault((schedule.course_id, schedule.weekday), schedule)

    items: list[schemas.StudentAttendanceHistoryItemOut] = []
    for submission in submissions:
        course = courses.get(submission.course_id)
        schedule = schedules_by_id.get(submission.schedule_id)
        faculty = faculties.get(
            submission.faculty_id
            if submission.faculty_id is not None
            else (course.faculty_id if course else None)
        )
        start_t = schedule.start_time if schedule else time(0, 0)
        end_t = schedule.end_time if schedule else time(0, 0)

        items.append(
            schemas.StudentAttendanceHistoryItemOut(
                class_date=submission.class_date,
                start_time=start_t,
                end_time=end_t,
                course_code=course.code if course else f"C-{submission.course_id}",
                course_title=course.title if course else "Unknown Course",
                faculty_name=faculty.name if faculty else "Faculty",
                status=models.AttendanceStatus.PRESENT,
                source="attendance-management",
            )
        )

    for record in fallback_records:
        course = courses.get(record.course_id)
        faculty = faculties.get(record.marked_by_faculty_id)
        schedule = schedule_map.get((record.course_id, record.attendance_date.weekday()))
        items.append(
            schemas.StudentAttendanceHistoryItemOut(
                class_date=record.attendance_date,
                start_time=schedule.start_time if schedule else time(0, 0),
                end_time=schedule.end_time if schedule else time(0, 0),
                course_code=course.code if course else f"C-{record.course_id}",
                course_title=course.title if course else "Unknown Course",
                faculty_name=faculty.name if faculty else "Faculty",
                status=record.status,
                source=record.source,
            )
        )

    items.sort(
        key=lambda row: (
            row.class_date,
            row.start_time,
            row.end_time,
            row.course_code,
        ),
        reverse=True,
    )
    return schemas.StudentAttendanceHistoryOut(records=items[:limit])


@router.get("/student/attendance-aggregate", response_model=schemas.StudentAttendanceAggregateOut)
def get_student_attendance_aggregate(
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    enrollments = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.student_id == current_user.student_id)
        .all()
    )
    if not enrollments:
        return schemas.StudentAttendanceAggregateOut(
            aggregate_percent=0.0,
            attended_total=0,
            delivered_total=0,
            courses=[],
        )

    course_ids = [item.course_id for item in enrollments]
    courses = {row.id: row for row in db.query(models.Course).filter(models.Course.id.in_(course_ids)).all()}
    academic_start = _academic_start_date()
    now_dt = datetime.now()
    today = now_dt.date()

    faculty_ids = sorted({course.faculty_id for course in courses.values()})
    faculties = {row.id: row for row in db.query(models.Faculty).filter(models.Faculty.id.in_(faculty_ids)).all()}
    schedules = (
        db.query(models.ClassSchedule)
        .filter(
            models.ClassSchedule.is_active.is_(True),
            models.ClassSchedule.course_id.in_(course_ids),
        )
        .all()
    )
    schedules_by_course: dict[int, list[models.ClassSchedule]] = {}
    for schedule in schedules:
        schedules_by_course.setdefault(schedule.course_id, []).append(schedule)

    submission_rows = (
        db.query(
            models.AttendanceSubmission.course_id,
            models.AttendanceSubmission.schedule_id,
            models.AttendanceSubmission.class_date,
            models.AttendanceSubmission.status,
        )
        .filter(
            models.AttendanceSubmission.student_id == current_user.student_id,
            models.AttendanceSubmission.course_id.in_(course_ids),
            models.AttendanceSubmission.class_date >= academic_start,
            models.AttendanceSubmission.class_date <= today,
        )
        .all()
    )
    delivered_submission_keys: dict[int, set[tuple[int, date]]] = {}
    delivered_submission_dates: dict[int, set[date]] = {}
    credited_submission_keys: dict[int, set[tuple[int, date]]] = {}
    last_attended_map: dict[int, date] = {}
    for course_id, schedule_id, class_date, status_value in submission_rows:
        delivered_submission_keys.setdefault(course_id, set()).add((schedule_id, class_date))
        delivered_submission_dates.setdefault(course_id, set()).add(class_date)
        if _is_submission_credited(status_value):
            credited_submission_keys.setdefault(course_id, set()).add((schedule_id, class_date))
            prev_last = last_attended_map.get(course_id)
            if prev_last is None or class_date > prev_last:
                last_attended_map[course_id] = class_date

    record_rows = (
        db.query(
            models.AttendanceRecord.course_id,
            models.AttendanceRecord.status,
            models.AttendanceRecord.attendance_date,
        )
        .filter(
            models.AttendanceRecord.student_id == current_user.student_id,
            models.AttendanceRecord.course_id.in_(course_ids),
            models.AttendanceRecord.attendance_date >= academic_start,
            models.AttendanceRecord.attendance_date <= today,
        )
        .all()
    )
    delivered_record_dates: dict[int, set[date]] = {}
    attended_record_fallback_counts: dict[int, int] = {}
    for course_id, status_value, attendance_date in record_rows:
        delivered_record_dates.setdefault(course_id, set()).add(attendance_date)
        if status_value == models.AttendanceStatus.PRESENT:
            if attendance_date in delivered_submission_dates.get(course_id, set()):
                continue
            attended_record_fallback_counts[course_id] = attended_record_fallback_counts.get(course_id, 0) + 1
            prev_last = last_attended_map.get(course_id)
            if prev_last is None or attendance_date > prev_last:
                last_attended_map[course_id] = attendance_date

    course_rows: list[schemas.StudentCourseAttendanceAggregateOut] = []
    attended_total = 0
    delivered_total = 0

    for enrollment in enrollments:
        course = courses.get(enrollment.course_id)
        if not course:
            continue

        delivered_by_schedule = sum(
            _count_delivered_occurrences(schedule, from_date=academic_start, now_dt=now_dt)
            for schedule in schedules_by_course.get(course.id, [])
        )
        delivered_by_submissions = len(delivered_submission_keys.get(course.id, set()))
        delivered_by_records = len(delivered_record_dates.get(course.id, set()))
        delivered = max(delivered_by_schedule, delivered_by_submissions, delivered_by_records)

        attended = (
            len(credited_submission_keys.get(course.id, set()))
            + attended_record_fallback_counts.get(course.id, 0)
        )
        if delivered > 0 and attended > delivered:
            attended = delivered
        last_attended = last_attended_map.get(course.id)

        percent = round((attended / delivered) * 100, 2) if delivered else 0.0
        attended_total += attended
        delivered_total += delivered

        faculty = faculties.get(course.faculty_id)
        course_rows.append(
            schemas.StudentCourseAttendanceAggregateOut(
                course_id=course.id,
                course_code=course.code,
                course_title=course.title,
                faculty_name=faculty.name if faculty else "Faculty",
                attended_classes=attended,
                delivered_classes=delivered,
                attendance_percent=percent,
                last_attended_on=last_attended,
            )
        )

    aggregate_percent = round((attended_total / delivered_total) * 100, 2) if delivered_total else 0.0

    return schemas.StudentAttendanceAggregateOut(
        aggregate_percent=aggregate_percent,
        attended_total=attended_total,
        delivered_total=delivered_total,
        courses=sorted(course_rows, key=lambda row: row.course_code),
    )


def _resolve_student_schedule_context(
    *,
    db: Session,
    current_user: models.AuthUser,
    schedule_id: int,
) -> tuple[models.Student, models.ClassSchedule, models.Course]:
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    student = db.get(models.Student, current_user.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if not student.registration_number:
        raise HTTPException(status_code=400, detail="Complete profile setup with registration number before attendance")

    if not student.profile_photo_data_url:
        raise HTTPException(status_code=400, detail="Upload profile photo before marking attendance")
    if not student.enrollment_video_template_json:
        raise HTTPException(status_code=400, detail="Complete one-time enrollment video before marking attendance")

    schedule = db.get(models.ClassSchedule, schedule_id)
    if not schedule or not schedule.is_active:
        raise HTTPException(status_code=404, detail="Class schedule not found")
    course = db.get(models.Course, schedule.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found for schedule")

    is_enrolled = (
        db.query(models.Enrollment)
        .filter(
            models.Enrollment.student_id == current_user.student_id,
            models.Enrollment.course_id == schedule.course_id,
        )
        .first()
    )
    if not is_enrolled:
        raise HTTPException(status_code=403, detail="Student is not enrolled in this class")

    return student, schedule, course


def _verify_student_face_payload(
    *,
    student: models.Student,
    schedule: models.ClassSchedule,
    payload: schemas.RealtimeAttendanceMarkRequest,
) -> tuple[str, float, str, models.AttendanceSubmissionStatus, str]:
    selfie_frames = payload.selfie_frames_data_urls or []
    primary_selfie = payload.selfie_photo_data_url
    if not primary_selfie and selfie_frames:
        primary_selfie = selfie_frames[0]
    if not primary_selfie:
        raise HTTPException(status_code=400, detail="selfie_photo_data_url is required")
    if not selfie_frames:
        selfie_frames = [primary_selfie]

    if len(selfie_frames) < FACE_MULTI_FRAME_MIN:
        raise HTTPException(
            status_code=400,
            detail=f"Capture at least {FACE_MULTI_FRAME_MIN} frames for secure facial attendance verification",
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
        logger.warning(
            "profile_template_missing_or_invalid student=%s rebuilding-on-the-fly",
            student.email,
        )
        try:
            profile_template = build_profile_face_template(student.profile_photo_data_url)
        except ValueError:
            profile_template = None
        combined_template = _merge_face_templates(enrollment_template, profile_template)

    # Backend OpenCV verification is mandatory for attendance marking.
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
    final_match = bool(opencv_verdict.get("match")) and final_confidence >= FACE_MATCH_PASS_THRESHOLD

    ai_verdict = _client_ai_verdict(payload)
    if ai_verdict:
        logger.info(
            "attendance_client_ai_observation student=%s schedule_id=%s ai_match=%s ai_confidence=%.4f ai_reason=%s",
            student.email,
            schedule.id,
            bool(ai_verdict.get("match")),
            float(ai_verdict.get("confidence", 0.0)),
            str(ai_verdict.get("reason") or ""),
        )

    status_value = (
        models.AttendanceSubmissionStatus.VERIFIED
        if final_match and final_confidence >= FACE_MATCH_PASS_THRESHOLD
        else models.AttendanceSubmissionStatus.REJECTED
    )
    liveness_meta = opencv_verdict.get("liveness", {})
    liveness_ok = bool((liveness_meta or {}).get("ok"))
    required_frames = int(opencv_verdict.get("required_consecutive_frames", FACE_MULTI_FRAME_MIN))
    matched_frames = int(opencv_verdict.get("consecutive_frames_matched", 0))
    accepted_frames = int(opencv_verdict.get("accepted_frames", 0))
    total_frames = int(opencv_verdict.get("total_frames", len(selfie_frames)))
    logger.info(
        "attendance_security_audit ts=%s student=%s schedule_id=%s confidence=%.4f threshold=%.2f decision=%s "
        "engine=%s streak=%s/%s accepted=%s/%s liveness=%s reason=%s",
        datetime.utcnow().isoformat(),
        student.email,
        schedule.id,
        final_confidence,
        FACE_MATCH_PASS_THRESHOLD,
        status_value.value,
        final_engine,
        matched_frames,
        required_frames,
        accepted_frames,
        total_frames,
        liveness_ok,
        final_reason,
    )
    return primary_selfie, final_confidence, final_engine, status_value, final_reason


def _public_rejection_message(reason: str, confidence: float | None = None) -> str:
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
    if score < FACE_MATCH_PASS_THRESHOLD:
        return "Face almost matched. Move to brighter light, align straight, and retry."
    return "Face not recognized. Move to brighter light and retry."


@router.post("/realtime/mark", response_model=schemas.RealtimeAttendanceMarkResponse)
def mark_realtime_attendance(
    payload: schemas.RealtimeAttendanceMarkRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    student, schedule, course = _resolve_student_schedule_context(
        db=db,
        current_user=current_user,
        schedule_id=payload.schedule_id,
    )

    today = date.today()
    if schedule.weekday != today.weekday():
        raise HTTPException(status_code=400, detail="This class is not scheduled for today")

    now_dt = datetime.now()
    is_open_now, _, _ = _window_flags(schedule, now_dt, today, course=course)
    if not is_open_now:
        raise HTTPException(status_code=400, detail="Attendance window is closed (only first 10 minutes)")
    primary_selfie, final_confidence, final_engine, status_value, final_reason = _verify_student_face_payload(
        student=student,
        schedule=schedule,
        payload=payload,
    )
    final_match = status_value == models.AttendanceSubmissionStatus.VERIFIED

    submission = (
        db.query(models.AttendanceSubmission)
        .filter(
            models.AttendanceSubmission.schedule_id == schedule.id,
            models.AttendanceSubmission.student_id == current_user.student_id,
            models.AttendanceSubmission.class_date == today,
        )
        .first()
    )

    if not submission:
        submission = models.AttendanceSubmission(
            schedule_id=schedule.id,
            course_id=schedule.course_id,
            faculty_id=schedule.faculty_id,
            student_id=current_user.student_id,
            class_date=today,
            selfie_photo_data_url=primary_selfie,
            ai_match=final_match,
            ai_confidence=final_confidence,
            ai_model=final_engine,
            ai_reason=final_reason,
            status=status_value,
        )
        db.add(submission)
    else:
        if submission.status in (
            models.AttendanceSubmissionStatus.VERIFIED,
            models.AttendanceSubmissionStatus.APPROVED,
        ):
            return schemas.RealtimeAttendanceMarkResponse(
                submission_id=submission.id,
                status=submission.status,
                requires_faculty_review=False,
                message="Attendance already verified for this class",
                verification_engine=submission.ai_model or "previous-verification",
                verification_confidence=float(submission.ai_confidence or 0.0),
                verification_reason=submission.ai_reason,
            )

        submission.selfie_photo_data_url = primary_selfie
        submission.ai_match = final_match
        submission.ai_confidence = final_confidence
        submission.ai_model = final_engine
        submission.ai_reason = final_reason
        submission.status = status_value
        submission.submitted_at = datetime.utcnow()
        submission.reviewed_at = None
        submission.reviewed_by_faculty_id = None
        submission.review_note = None

    db.flush()

    if status_value == models.AttendanceSubmissionStatus.VERIFIED:
        _upsert_present_attendance(
            db,
            student_id=current_user.student_id,
            course_id=schedule.course_id,
            faculty_id=schedule.faculty_id,
            class_date=today,
            source="face-opencv-primary-verified",
        )

    db.commit()

    _upsert_mongo_by_id(
        "attendance_submissions",
        submission.id,
        {
            "schedule_id": submission.schedule_id,
            "course_id": submission.course_id,
            "faculty_id": submission.faculty_id,
            "student_id": submission.student_id,
            "class_date": submission.class_date.isoformat(),
            "status": submission.status.value,
            "ai_match": submission.ai_match,
            "ai_confidence": submission.ai_confidence,
            "ai_model": submission.ai_model,
            "ai_reason": submission.ai_reason,
            "selfie_photo_fingerprint": _photo_fingerprint(submission.selfie_photo_data_url),
            "submitted_at": submission.submitted_at,
            "source": "attendance-management",
        },
    )

    return schemas.RealtimeAttendanceMarkResponse(
        submission_id=submission.id,
        status=status_value,
        requires_faculty_review=False,
        message=(
            "Attendance verified automatically"
            if status_value == models.AttendanceSubmissionStatus.VERIFIED
            else _public_rejection_message(final_reason, final_confidence)
        ),
        verification_engine=final_engine,
        verification_confidence=final_confidence,
        verification_reason=final_reason,
    )


@router.get("/faculty/schedules", response_model=list[schemas.ClassScheduleOut])
def get_faculty_schedules(
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    query = db.query(models.ClassSchedule).filter(models.ClassSchedule.is_active.is_(True))
    if current_user.role == models.UserRole.FACULTY:
        if not current_user.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty account is not linked correctly")
        query = query.filter(models.ClassSchedule.faculty_id == current_user.faculty_id)

    return query.order_by(models.ClassSchedule.weekday.asc(), models.ClassSchedule.start_time.asc()).all()


@router.get("/faculty/dashboard", response_model=schemas.FacultyAttendanceDashboardOut)
def get_faculty_dashboard(
    schedule_id: int,
    class_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    class_date = class_date or date.today()

    schedule = db.get(models.ClassSchedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if current_user.role == models.UserRole.FACULTY and current_user.faculty_id != schedule.faculty_id:
        raise HTTPException(status_code=403, detail="Faculty can only access their own class dashboard")

    total_students = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.course_id == schedule.course_id)
        .count()
    )

    submissions = (
        db.query(models.AttendanceSubmission)
        .filter(
            models.AttendanceSubmission.schedule_id == schedule_id,
            models.AttendanceSubmission.class_date == class_date,
        )
        .order_by(models.AttendanceSubmission.submitted_at.asc())
        .all()
    )

    present = sum(
        1
        for item in submissions
        if item.status in (models.AttendanceSubmissionStatus.VERIFIED, models.AttendanceSubmissionStatus.APPROVED)
    )
    pending = sum(1 for item in submissions if item.status == models.AttendanceSubmissionStatus.PENDING_REVIEW)
    absent = max(total_students - present - pending, 0)

    response_items: list[schemas.AttendanceSubmissionOut] = []
    for item in submissions:
        student = db.get(models.Student, item.student_id)
        response_items.append(
            schemas.AttendanceSubmissionOut(
                id=item.id,
                student_id=item.student_id,
                student_name=student.name if student else f"Student #{item.student_id}",
                status=item.status,
                ai_confidence=item.ai_confidence,
                ai_reason=item.ai_reason,
                submitted_at=item.submitted_at,
            )
        )

    return schemas.FacultyAttendanceDashboardOut(
        schedule_id=schedule_id,
        class_date=class_date,
        total_students=total_students,
        present=present,
        pending_review=pending,
        absent=absent,
        submissions=response_items,
    )


@router.post("/faculty/review", response_model=schemas.FacultyBatchReviewResponse)
def faculty_batch_review(
    payload: schemas.FacultyBatchReviewRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    schedule = db.get(models.ClassSchedule, payload.schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if current_user.role == models.UserRole.FACULTY and current_user.faculty_id != schedule.faculty_id:
        raise HTTPException(status_code=403, detail="Faculty can only review their own class submissions")

    submissions = (
        db.query(models.AttendanceSubmission)
        .filter(
            models.AttendanceSubmission.id.in_(payload.submission_ids),
            models.AttendanceSubmission.schedule_id == payload.schedule_id,
            models.AttendanceSubmission.class_date == payload.class_date,
        )
        .all()
    )

    if not submissions:
        raise HTTPException(status_code=404, detail="No matching submissions found")

    approved = 0
    rejected = 0
    reviewer_faculty_id = schedule.faculty_id if current_user.role == models.UserRole.ADMIN else current_user.faculty_id

    pending_submissions = [
        item for item in submissions if item.status == models.AttendanceSubmissionStatus.PENDING_REVIEW
    ]
    if not pending_submissions:
        raise HTTPException(status_code=400, detail="Only pending submissions can be reviewed")

    for item in pending_submissions:
        item.reviewed_by_faculty_id = reviewer_faculty_id
        item.reviewed_at = datetime.utcnow()
        item.review_note = payload.note

        if payload.action == schemas.FacultyReviewAction.APPROVE:
            item.status = models.AttendanceSubmissionStatus.APPROVED
            _upsert_present_attendance(
                db,
                student_id=item.student_id,
                course_id=item.course_id,
                faculty_id=reviewer_faculty_id or item.faculty_id,
                class_date=item.class_date,
                source="faculty-approved-face",
            )
            approved += 1
        else:
            item.status = models.AttendanceSubmissionStatus.REJECTED
            rejected += 1

    db.commit()

    mirror_document(
        "attendance_reviews",
        {
            "schedule_id": payload.schedule_id,
            "class_date": payload.class_date.isoformat(),
            "action": payload.action.value,
            "review_note": payload.note,
            "updated_submission_ids": [item.id for item in pending_submissions],
            "approved": approved,
            "rejected": rejected,
            "reviewed_by_faculty_id": reviewer_faculty_id,
            "source": "faculty-review",
            "reviewed_at": datetime.utcnow(),
        },
    )

    return schemas.FacultyBatchReviewResponse(
        updated=len(pending_submissions),
        approved=approved,
        rejected=rejected,
    )


@router.post("/faculty/classroom-analysis", response_model=schemas.ClassroomAnalysisOut, status_code=status.HTTP_201_CREATED)
def create_classroom_analysis(
    payload: schemas.ClassroomAnalysisCreate,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    schedule = db.get(models.ClassSchedule, payload.schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if current_user.role == models.UserRole.FACULTY and current_user.faculty_id != schedule.faculty_id:
        raise HTTPException(status_code=403, detail="Faculty can only analyze their own classes")

    analysis = models.ClassroomAnalysis(
        schedule_id=payload.schedule_id,
        course_id=schedule.course_id,
        faculty_id=schedule.faculty_id,
        class_date=payload.class_date,
        photo_data_url=payload.photo_data_url,
        estimated_headcount=payload.estimated_headcount,
        engagement_level=payload.engagement_level,
        ai_summary=payload.ai_summary,
        ai_model=payload.ai_model,
    )

    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    _upsert_mongo_by_id(
        "classroom_analyses",
        analysis.id,
        {
            "schedule_id": analysis.schedule_id,
            "course_id": analysis.course_id,
            "faculty_id": analysis.faculty_id,
            "class_date": analysis.class_date.isoformat(),
            "estimated_headcount": analysis.estimated_headcount,
            "engagement_level": analysis.engagement_level,
            "ai_summary": analysis.ai_summary,
            "ai_model": analysis.ai_model,
            "photo_fingerprint": _photo_fingerprint(analysis.photo_data_url),
            "created_at": analysis.created_at,
            "source": "faculty-classroom-analysis",
        },
    )

    return analysis


@router.get("/faculty/classroom-analysis", response_model=list[schemas.ClassroomAnalysisOut])
def list_classroom_analysis(
    schedule_id: int | None = None,
    class_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    query = db.query(models.ClassroomAnalysis)

    if schedule_id:
        query = query.filter(models.ClassroomAnalysis.schedule_id == schedule_id)

    if class_date:
        query = query.filter(models.ClassroomAnalysis.class_date == class_date)

    if current_user.role == models.UserRole.FACULTY:
        query = query.filter(models.ClassroomAnalysis.faculty_id == current_user.faculty_id)

    return query.order_by(models.ClassroomAnalysis.created_at.desc()).limit(100).all()


@router.post("/mark-bulk", response_model=schemas.AttendanceBulkMarkResponse)
def mark_attendance_bulk(
    payload: schemas.AttendanceBulkMarkRequest,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    course = db.get(models.Course, payload.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if current_user.role == models.UserRole.FACULTY:
        if not current_user.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty account is not linked correctly")
        if payload.faculty_id != current_user.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty can only mark attendance for their own ID")

    if course.faculty_id != payload.faculty_id:
        raise HTTPException(status_code=400, detail="Faculty is not assigned to this course")

    enrollments = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.course_id == payload.course_id)
        .all()
    )
    if not enrollments:
        raise HTTPException(status_code=400, detail="No enrolled students found for this course")

    override_map = {item.student_id: item.status for item in payload.overrides}
    absent_student_ids: list[int] = []

    for enrollment in enrollments:
        student_id = enrollment.student_id
        status_value = override_map.get(student_id, payload.default_status)

        existing = (
            db.query(models.AttendanceRecord)
            .filter(
                models.AttendanceRecord.student_id == student_id,
                models.AttendanceRecord.course_id == payload.course_id,
                models.AttendanceRecord.attendance_date == payload.attendance_date,
            )
            .first()
        )

        if existing:
            existing.status = status_value
            existing.source = payload.source
            existing.marked_by_faculty_id = payload.faculty_id
        else:
            db.add(
                models.AttendanceRecord(
                    student_id=student_id,
                    course_id=payload.course_id,
                    marked_by_faculty_id=payload.faculty_id,
                    attendance_date=payload.attendance_date,
                    status=status_value,
                    source=payload.source,
                )
            )

        if status_value == models.AttendanceStatus.ABSENT:
            absent_student_ids.append(student_id)

    db.flush()

    notifications_sent = 0
    for student_id in absent_student_ids:
        student = db.get(models.Student, student_id)
        if not student:
            continue

        message = (
            f"Absence alert: {student.name} is marked absent on "
            f"{payload.attendance_date.isoformat()} for {course.code}."
        )

        db.add(
            models.NotificationLog(
                student_id=student_id,
                message=message,
                channel="simulated-student",
                sent_to=student.email,
            )
        )
        notifications_sent += 1

        if student.parent_email:
            db.add(
                models.NotificationLog(
                    student_id=student_id,
                    message=message,
                    channel="simulated-parent",
                    sent_to=student.parent_email,
                )
            )
            notifications_sent += 1

    db.commit()

    mirror_document(
        "attendance_bulk_marks",
        {
            "course_id": payload.course_id,
            "faculty_id": payload.faculty_id,
            "attendance_date": payload.attendance_date.isoformat(),
            "default_status": payload.default_status.value,
            "source": payload.source,
            "total_marked": len(enrollments),
            "absent_student_ids": absent_student_ids,
            "notifications_sent": notifications_sent,
            "marked_at": datetime.utcnow(),
        },
    )

    return schemas.AttendanceBulkMarkResponse(
        total_marked=len(enrollments),
        absent_student_ids=absent_student_ids,
        notifications_sent=notifications_sent,
    )


@router.get("/absentees", response_model=list[schemas.StudentOut])
def get_absentees(
    course_id: int,
    attendance_date: date = Query(...),
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    records = (
        db.query(models.AttendanceRecord)
        .filter(
            models.AttendanceRecord.course_id == course_id,
            models.AttendanceRecord.attendance_date == attendance_date,
            models.AttendanceRecord.status == models.AttendanceStatus.ABSENT,
        )
        .all()
    )
    if not records:
        return []

    student_ids = [r.student_id for r in records]
    return db.query(models.Student).filter(models.Student.id.in_(student_ids)).all()


@router.get("/summary", response_model=list[schemas.AttendanceSummaryItem])
def attendance_summary(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(get_current_user),
):
    course = db.get(models.Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    enrollments_query = db.query(models.Enrollment).filter(models.Enrollment.course_id == course_id)

    if current_user.role == models.UserRole.STUDENT:
        if not current_user.student_id:
            raise HTTPException(status_code=403, detail="Student account is not linked correctly")
        enrollments_query = enrollments_query.filter(models.Enrollment.student_id == current_user.student_id)

    enrollments = enrollments_query.all()

    summary: list[schemas.AttendanceSummaryItem] = []
    for enrollment in enrollments:
        student = db.get(models.Student, enrollment.student_id)
        if not student:
            continue

        present_count = (
            db.query(models.AttendanceRecord)
            .filter(
                models.AttendanceRecord.course_id == course_id,
                models.AttendanceRecord.student_id == enrollment.student_id,
                models.AttendanceRecord.status == models.AttendanceStatus.PRESENT,
            )
            .count()
        )
        absent_count = (
            db.query(models.AttendanceRecord)
            .filter(
                models.AttendanceRecord.course_id == course_id,
                models.AttendanceRecord.student_id == enrollment.student_id,
                models.AttendanceRecord.status == models.AttendanceStatus.ABSENT,
            )
            .count()
        )

        summary.append(
            schemas.AttendanceSummaryItem(
                student_id=student.id,
                student_name=student.name,
                present_count=present_count,
                absent_count=absent_count,
            )
        )

    return summary


@router.get("/notifications", response_model=list[schemas.NotificationOut])
def list_notifications(
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    return (
        db.query(models.NotificationLog)
        .order_by(models.NotificationLog.created_at.desc())
        .limit(200)
        .all()
    )
