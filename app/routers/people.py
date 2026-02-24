from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth_utils import CurrentUser, require_roles
from ..database import get_db
from ..mongo import get_mongo_db

router = APIRouter(prefix="/core", tags=["Core Setup"])


def _upsert_mongo_by_id(collection: str, doc_id: int, payload: dict) -> None:
    try:
        mongo_db = get_mongo_db(required=True)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    body = dict(payload)
    body["id"] = doc_id
    mongo_db[collection].update_one({"id": doc_id}, {"$set": body}, upsert=True)


@router.post("/students", response_model=schemas.StudentOut, status_code=status.HTTP_201_CREATED)
def create_student(
    payload: schemas.StudentCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(models.UserRole.FACULTY)),
):
    existing = db.query(models.Student).filter(models.Student.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Student email already exists")
    student = models.Student(**payload.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)

    _upsert_mongo_by_id(
        "students",
        student.id,
        {
            "name": student.name,
            "email": student.email,
            "parent_email": student.parent_email,
            "profile_photo_data_url": student.profile_photo_data_url,
            "profile_photo_updated_at": student.profile_photo_updated_at,
            "profile_photo_locked_until": student.profile_photo_locked_until,
            "department": student.department,
            "semester": student.semester,
            "created_at": student.created_at,
            "source": "core-api",
        },
    )

    return student


@router.get("/students", response_model=list[schemas.StudentOut])
def list_students(
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.STUDENT)
    ),
):
    return db.query(models.Student).order_by(models.Student.id.asc()).all()


@router.post("/faculty", response_model=schemas.FacultyOut, status_code=status.HTTP_201_CREATED)
def create_faculty(
    payload: schemas.FacultyCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(models.UserRole.FACULTY)),
):
    existing = db.query(models.Faculty).filter(models.Faculty.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Faculty email already exists")
    faculty = models.Faculty(**payload.model_dump())
    db.add(faculty)
    db.commit()
    db.refresh(faculty)

    _upsert_mongo_by_id(
        "faculty",
        faculty.id,
        {
            "name": faculty.name,
            "email": faculty.email,
            "department": faculty.department,
            "created_at": faculty.created_at,
            "source": "core-api",
        },
    )

    return faculty


@router.get("/faculty", response_model=list[schemas.FacultyOut])
def list_faculty(
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.STUDENT)
    ),
):
    return db.query(models.Faculty).order_by(models.Faculty.id.asc()).all()


@router.post("/courses", response_model=schemas.CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: schemas.CourseCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles(models.UserRole.FACULTY)),
):
    if not current_user.faculty_id or current_user.faculty_id != payload.faculty_id:
        raise HTTPException(status_code=403, detail="Faculty can only create courses for their own ID")

    if not db.get(models.Faculty, payload.faculty_id):
        raise HTTPException(status_code=404, detail="Faculty not found")
    existing = db.query(models.Course).filter(models.Course.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=409, detail="Course code already exists")
    course = models.Course(**payload.model_dump())
    db.add(course)
    db.commit()
    db.refresh(course)

    _upsert_mongo_by_id(
        "courses",
        course.id,
        {
            "code": course.code,
            "title": course.title,
            "faculty_id": course.faculty_id,
            "source": "core-api",
            "created_at": datetime.utcnow(),
        },
    )

    return course


@router.get("/courses", response_model=list[schemas.CourseOut])
def list_courses(
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.STUDENT)
    ),
):
    return db.query(models.Course).order_by(models.Course.id.asc()).all()


@router.post("/enroll", status_code=status.HTTP_201_CREATED)
def enroll_student(
    payload: schemas.EnrollmentCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles(models.UserRole.FACULTY)),
):
    if not db.get(models.Student, payload.student_id):
        raise HTTPException(status_code=404, detail="Student not found")
    course = db.get(models.Course, payload.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if not current_user.faculty_id or course.faculty_id != current_user.faculty_id:
        raise HTTPException(status_code=403, detail="Faculty can only enroll students in their own courses")

    exists = (
        db.query(models.Enrollment)
        .filter(
            models.Enrollment.student_id == payload.student_id,
            models.Enrollment.course_id == payload.course_id,
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="Enrollment already exists")

    enrollment = models.Enrollment(**payload.model_dump())
    db.add(enrollment)
    db.commit()

    _upsert_mongo_by_id(
        "enrollments",
        enrollment.id,
        {
            "student_id": enrollment.student_id,
            "course_id": enrollment.course_id,
            "created_at": enrollment.created_at,
            "source": "core-api",
        },
    )

    return {"message": "Enrollment created"}


@router.post("/classrooms", response_model=schemas.ClassroomOut, status_code=status.HTTP_201_CREATED)
def create_classroom(
    payload: schemas.ClassroomCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(models.UserRole.FACULTY)),
):
    existing = (
        db.query(models.Classroom)
        .filter(
            models.Classroom.block == payload.block,
            models.Classroom.room_number == payload.room_number,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Classroom already exists")

    classroom = models.Classroom(**payload.model_dump())
    db.add(classroom)
    db.commit()
    db.refresh(classroom)

    _upsert_mongo_by_id(
        "classrooms",
        classroom.id,
        {
            "block": classroom.block,
            "room_number": classroom.room_number,
            "capacity": classroom.capacity,
            "source": "core-api",
            "created_at": datetime.utcnow(),
        },
    )

    return classroom


@router.get("/classrooms", response_model=list[schemas.ClassroomOut])
def list_classrooms(
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.STUDENT)
    ),
):
    return db.query(models.Classroom).order_by(models.Classroom.id.asc()).all()


@router.post("/course-classroom", status_code=status.HTTP_201_CREATED)
def assign_course_classroom(
    payload: schemas.CourseClassroomCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles(models.UserRole.FACULTY)),
):
    course = db.get(models.Course, payload.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if not current_user.faculty_id or course.faculty_id != current_user.faculty_id:
        raise HTTPException(status_code=403, detail="Faculty can only assign classrooms to their own courses")
    if not db.get(models.Classroom, payload.classroom_id):
        raise HTTPException(status_code=404, detail="Classroom not found")

    existing = (
        db.query(models.CourseClassroom)
        .filter(models.CourseClassroom.course_id == payload.course_id)
        .first()
    )
    if existing:
        existing.classroom_id = payload.classroom_id
        db.commit()

        _upsert_mongo_by_id(
            "course_classrooms",
            existing.id,
            {
                "course_id": existing.course_id,
                "classroom_id": existing.classroom_id,
                "source": "core-api",
                "updated_at": datetime.utcnow(),
            },
        )

        return {"message": "Classroom assignment updated"}

    assignment = models.CourseClassroom(**payload.model_dump())
    db.add(assignment)
    db.commit()

    _upsert_mongo_by_id(
        "course_classrooms",
        assignment.id,
        {
            "course_id": assignment.course_id,
            "classroom_id": assignment.classroom_id,
            "source": "core-api",
            "created_at": datetime.utcnow(),
        },
    )

    return {"message": "Classroom assigned"}
