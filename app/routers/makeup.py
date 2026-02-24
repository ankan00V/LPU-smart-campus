import secrets
import string
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth_utils import require_roles
from ..database import get_db
from ..mongo import mirror_document

router = APIRouter(prefix="/makeup", tags=["Make-Up & Remedial Code"])


def generate_remedial_code(db: Session, length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(20):
        code = "".join(secrets.choice(alphabet) for _ in range(length))
        exists = (
            db.query(models.MakeUpClass)
            .filter(models.MakeUpClass.remedial_code == code)
            .first()
        )
        if not exists:
            return code
    raise RuntimeError("Unable to generate unique remedial code")


@router.post("/classes", response_model=schemas.MakeUpClassOut, status_code=status.HTTP_201_CREATED)
def create_makeup_class(
    payload: schemas.MakeUpClassCreate,
    db: Session = Depends(get_db),
    current_user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    course = db.get(models.Course, payload.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if current_user.role == models.UserRole.FACULTY:
        if current_user.faculty_id != payload.faculty_id:
            raise HTTPException(status_code=403, detail="Faculty can only create classes for their own ID")

    if course.faculty_id != payload.faculty_id:
        raise HTTPException(status_code=400, detail="Faculty is not assigned to this course")

    remedial_code = generate_remedial_code(db)
    makeup_class = models.MakeUpClass(**payload.model_dump(), remedial_code=remedial_code)
    db.add(makeup_class)
    db.commit()
    db.refresh(makeup_class)

    mirror_document(
        "makeup_classes",
        {
            "makeup_class_id": makeup_class.id,
            "course_id": makeup_class.course_id,
            "faculty_id": makeup_class.faculty_id,
            "class_date": makeup_class.class_date.isoformat(),
            "start_time": str(makeup_class.start_time),
            "end_time": str(makeup_class.end_time),
            "topic": makeup_class.topic,
            "remedial_code": makeup_class.remedial_code,
            "is_active": makeup_class.is_active,
            "created_at": makeup_class.created_at,
            "source": "faculty-scheduler",
        },
    )

    return makeup_class


@router.get("/classes", response_model=list[schemas.MakeUpClassOut])
def list_makeup_classes(
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    return db.query(models.MakeUpClass).order_by(models.MakeUpClass.class_date.desc()).all()


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

    makeup_class = (
        db.query(models.MakeUpClass)
        .filter(
            models.MakeUpClass.remedial_code == payload.remedial_code,
            models.MakeUpClass.is_active.is_(True),
        )
        .first()
    )
    if not makeup_class:
        raise HTTPException(status_code=404, detail="Invalid or inactive remedial code")

    student = db.get(models.Student, payload.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    is_enrolled = (
        db.query(models.Enrollment)
        .filter(
            models.Enrollment.student_id == payload.student_id,
            models.Enrollment.course_id == makeup_class.course_id,
        )
        .first()
    )
    if not is_enrolled:
        raise HTTPException(status_code=400, detail="Student is not enrolled in this course")

    existing = (
        db.query(models.RemedialAttendance)
        .filter(
            models.RemedialAttendance.makeup_class_id == makeup_class.id,
            models.RemedialAttendance.student_id == payload.student_id,
        )
        .first()
    )
    if existing:
        return {"message": "Attendance already marked", "makeup_class_id": makeup_class.id}

    attendance_row = models.RemedialAttendance(
        makeup_class_id=makeup_class.id,
        student_id=payload.student_id,
        source="remedial-code",
    )
    db.add(attendance_row)
    db.commit()
    db.refresh(attendance_row)

    mirror_document(
        "remedial_attendance",
        {
            "attendance_id": attendance_row.id,
            "makeup_class_id": attendance_row.makeup_class_id,
            "student_id": attendance_row.student_id,
            "source": attendance_row.source,
            "marked_at": attendance_row.marked_at,
            "recorded_at": datetime.utcnow(),
        },
    )

    return {"message": "Remedial attendance marked", "makeup_class_id": makeup_class.id}


@router.get("/classes/{class_id}/attendance")
def get_makeup_class_attendance(
    class_id: int,
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    makeup_class = db.get(models.MakeUpClass, class_id)
    if not makeup_class:
        raise HTTPException(status_code=404, detail="Make-up class not found")

    records = (
        db.query(models.RemedialAttendance)
        .filter(models.RemedialAttendance.makeup_class_id == class_id)
        .all()
    )

    students = []
    for record in records:
        student = db.get(models.Student, record.student_id)
        if not student:
            continue
        students.append(
            {
                "student_id": student.id,
                "student_name": student.name,
                "marked_at": record.marked_at,
                "source": record.source,
            }
        )

    return {
        "class_id": makeup_class.id,
        "course_id": makeup_class.course_id,
        "remedial_code": makeup_class.remedial_code,
        "attendance_count": len(students),
        "students": students,
    }
