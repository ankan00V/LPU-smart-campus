from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth_utils import require_roles
from ..database import get_db
from ..mongo import get_mongo_db, mongo_status

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


@router.get("/mongo/consistency")
def get_mongo_consistency(
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    mongo_db = get_mongo_db(required=False)
    checks: list[tuple[str, type]] = [
        ("students", models.Student),
        ("faculty", models.Faculty),
        ("courses", models.Course),
        ("enrollments", models.Enrollment),
        ("classrooms", models.Classroom),
        ("course_classrooms", models.CourseClassroom),
        ("attendance_records", models.AttendanceRecord),
        ("notification_logs", models.NotificationLog),
        ("food_items", models.FoodItem),
        ("food_shops", models.FoodShop),
        ("food_menu_items", models.FoodMenuItem),
        ("break_slots", models.BreakSlot),
        ("food_orders", models.FoodOrder),
        ("food_payments", models.FoodPayment),
        ("food_order_audit", models.FoodOrderAudit),
        ("makeup_classes", models.MakeUpClass),
        ("remedial_messages", models.RemedialMessage),
        ("remedial_attendance", models.RemedialAttendance),
        ("class_schedules", models.ClassSchedule),
        ("attendance_submissions", models.AttendanceSubmission),
        ("classroom_analyses", models.ClassroomAnalysis),
        ("auth_users", models.AuthUser),
        ("auth_otps", models.AuthOTP),
        ("auth_otp_delivery", models.AuthOTPDelivery),
    ]

    rows: list[dict] = []
    mismatches = 0
    for collection_name, model_cls in checks:
        sql_count = int(db.query(model_cls).count())
        mongo_count = (
            int(mongo_db[collection_name].count_documents({}))
            if mongo_db is not None
            else 0
        )
        in_sync = (mongo_db is not None) and (sql_count == mongo_count)
        if not in_sync:
            mismatches += 1
        rows.append(
            {
                "collection": collection_name,
                "sql_count": sql_count,
                "mongo_count": mongo_count,
                "in_sync": in_sync,
                "delta": mongo_count - sql_count,
            }
        )

    return {
        "generated_at": datetime.utcnow(),
        "mongo": mongo_status(),
        "mismatches": mismatches,
        "checks": rows,
    }
