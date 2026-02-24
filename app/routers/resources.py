from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth_utils import require_roles
from ..database import get_db
from ..mongo import mongo_status

router = APIRouter(prefix="/resources", tags=["Campus Resources & Estimation"])


@router.get("/overview")
def resources_overview(
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.STUDENT)
    ),
):
    blocks_count = db.query(func.count(func.distinct(models.Classroom.block))).scalar() or 0
    return {
        "blocks": blocks_count,
        "classrooms": db.query(models.Classroom).count(),
        "courses": db.query(models.Course).count(),
        "faculty": db.query(models.Faculty).count(),
        "students": db.query(models.Student).count(),
    }


@router.get("/capacity-utilization", response_model=list[schemas.CapacityUtilizationItem])
def capacity_utilization(
    course_id: int | None = None,
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.STUDENT)
    ),
):
    query = db.query(models.CourseClassroom)
    if course_id:
        query = query.filter(models.CourseClassroom.course_id == course_id)

    assignments = query.all()
    results: list[schemas.CapacityUtilizationItem] = []

    for assignment in assignments:
        course = db.get(models.Course, assignment.course_id)
        classroom = db.get(models.Classroom, assignment.classroom_id)
        if not course or not classroom:
            continue

        enrolled_count = (
            db.query(models.Enrollment)
            .filter(models.Enrollment.course_id == assignment.course_id)
            .count()
        )
        utilization = (enrolled_count / classroom.capacity * 100.0) if classroom.capacity else 0.0

        results.append(
            schemas.CapacityUtilizationItem(
                course_id=course.id,
                course_code=course.code,
                classroom=f"{classroom.block}-{classroom.room_number}",
                enrolled_students=enrolled_count,
                capacity=classroom.capacity,
                utilization_percent=round(utilization, 2),
            )
        )

    return sorted(results, key=lambda x: x.utilization_percent, reverse=True)


@router.get("/workload-distribution", response_model=list[schemas.FacultyWorkloadItem])
def workload_distribution(
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    faculty_list = db.query(models.Faculty).all()
    distribution: list[schemas.FacultyWorkloadItem] = []

    for faculty in faculty_list:
        courses = db.query(models.Course).filter(models.Course.faculty_id == faculty.id).all()
        course_ids = [course.id for course in courses]

        total_enrolled = 0
        if course_ids:
            total_enrolled = (
                db.query(models.Enrollment)
                .filter(models.Enrollment.course_id.in_(course_ids))
                .count()
            )

        distribution.append(
            schemas.FacultyWorkloadItem(
                faculty_id=faculty.id,
                faculty_name=faculty.name,
                assigned_courses=len(courses),
                total_enrolled_students=total_enrolled,
            )
        )

    return sorted(distribution, key=lambda x: x.total_enrolled_students, reverse=True)


@router.get("/mongo/status")
def get_mongo_status(
    _: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    return mongo_status()
