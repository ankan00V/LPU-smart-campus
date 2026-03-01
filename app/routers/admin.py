from __future__ import annotations

from copy import deepcopy
from collections import defaultdict
from datetime import date, datetime
import os
from typing import Iterable

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth_utils import require_roles
from ..database import get_db
from ..mongo import get_mongo_db, mirror_document, mongo_status

router = APIRouter(prefix="/admin", tags=["Administrative Realtime"])

STALE_AFTER_SECONDS = max(20, min(300, int(os.getenv("ADMIN_STALE_AFTER_SECONDS", "60"))))
FACULTY_TARGET_HOURS_DEFAULT = max(6.0, float(os.getenv("FACULTY_TARGET_HOURS_PER_WEEK", "18")))
OVERLOAD_UTILIZATION_PERCENT = max(75.0, min(120.0, float(os.getenv("ADMIN_ROOM_OVERLOAD_PERCENT", "90"))))
DEPARTMENT_CLASSROOM_LAYOUT: dict[str, dict] = {
    "CSE": {
        "school": "School of Computer Science and Engineering",
        "blocks": [
            {"block": "25", "floors": 8, "rooms_per_floor": 6},
            {"block": "26", "floors": 6, "rooms_per_floor": 10},
            {"block": "27", "floors": 6, "rooms_per_floor": 10},
            {"block": "28", "floors": 6, "rooms_per_floor": 10},
            {"block": "33", "floors": 6, "rooms_per_floor": 9},
            {"block": "34", "floors": 8, "rooms_per_floor": 11},
        ],
    },
    "ECE": {
        "school": "Electronics and Communication Engineering",
        "blocks": [
            {"block": "36", "floors": 9, "rooms_per_floor": 19},
            {"block": "37", "floors": 9, "rooms_per_floor": 19},
            {"block": "38", "floors": 9, "rooms_per_floor": 19},
        ],
    },
}
DEPARTMENT_CLASSROOM_DEFAULT_CAPACITY = max(
    20,
    min(250, int(os.getenv("ADMIN_DEPARTMENT_CLASSROOM_CAPACITY", "60"))),
)
ADMIN_REFERENCE_PROFILE_ID = "lpu-campus-baseline-v1"
ADMIN_REFERENCE_PROFILE: dict = {
    "institution": "Lovely Professional University",
    "active_students": {"min": 30000, "max": 35000, "estimated": 34700},
    "discipline_distribution": [
        {"discipline": "Engineering & Tech", "share_percent": 38, "students": 13000},
        {"discipline": "Management", "share_percent": 18, "students": 6200},
        {"discipline": "Computer Applications / IT", "share_percent": 12, "students": 4100},
        {"discipline": "Pharmacy", "share_percent": 8, "students": 2800},
        {"discipline": "Law", "share_percent": 6, "students": 2100},
        {"discipline": "Design / Architecture", "share_percent": 5, "students": 1700},
        {"discipline": "Agriculture", "share_percent": 5, "students": 1700},
        {"discipline": "Humanities & Social Science", "share_percent": 4, "students": 1400},
        {"discipline": "Hotel Management / Tourism", "share_percent": 2, "students": 700},
        {"discipline": "Others", "share_percent": 2, "students": 700},
    ],
    "year_distribution": [
        {"year": "1st Year", "share_percent": 32, "students": 11100},
        {"year": "2nd Year", "share_percent": 27, "students": 9400},
        {"year": "3rd Year", "share_percent": 23, "students": 8000},
        {"year": "4th Year", "share_percent": 18, "students": 6200},
    ],
    "gender_split": [
        {"category": "Male", "share_percent": 56, "students": 19500},
        {"category": "Female", "share_percent": 43, "students": 15000},
        {"category": "Others", "share_percent": 1, "students": 350},
    ],
    "residency_split": [
        {"category": "Hostel", "share_percent": 68, "students": 23800},
        {"category": "Day Scholar", "share_percent": 32, "students": 11200},
    ],
    "origin_split": [
        {"category": "Domestic", "share_percent": 85, "students": 29700},
        {"category": "International", "share_percent": 15, "students": 5200},
    ],
    "engineering_distribution": [
        {"department": "CSE", "students": 4800},
        {"department": "Mechanical", "students": 1900},
        {"department": "Civil", "students": 1300},
        {"department": "ECE", "students": 1600},
        {"department": "Electrical", "students": 1200},
        {"department": "IT", "students": 1400},
        {"department": "AI / DS", "students": 800},
    ],
    "management_distribution": [
        {"department": "MBA", "students": 2700},
        {"department": "BBA", "students": 2100},
        {"department": "Finance", "students": 600},
        {"department": "Marketing", "students": 500},
        {"department": "HR", "students": 300},
    ],
    "classroom_utilization_model": {
        "time_slots": [
            {"slot": "08:00-09:00", "utilization_percent": 45},
            {"slot": "09:00-10:00", "utilization_percent": 70},
            {"slot": "10:00-11:00", "utilization_percent": 88},
            {"slot": "11:00-12:00", "utilization_percent": 92},
            {"slot": "12:00-13:00", "utilization_percent": 75},
            {"slot": "13:00-14:00", "utilization_percent": 50},
            {"slot": "14:00-15:00", "utilization_percent": 65},
            {"slot": "15:00-16:00", "utilization_percent": 72},
            {"slot": "16:00-17:00", "utilization_percent": 40},
        ],
        "discipline_peak_usage": [
            {"discipline": "Engineering", "peak_percent": 95},
            {"discipline": "Management", "peak_percent": 80},
            {"discipline": "IT", "peak_percent": 85},
            {"discipline": "Law", "peak_percent": 70},
            {"discipline": "Pharmacy", "peak_percent": 75},
            {"discipline": "Design", "peak_percent": 60},
        ],
        "classroom_type_peak": [
            {"room_type": "Lecture Halls", "peak_percent": 93},
            {"room_type": "Labs", "peak_percent": 87},
            {"room_type": "Seminar Rooms", "peak_percent": 65},
            {"room_type": "Tutorial Rooms", "peak_percent": 78},
        ],
        "simultaneous_students_peak": 11500,
    },
    "placement_model": {
        "final_year_pool": 6200,
        "overall": {
            "placed": 4600,
            "higher_studies": 900,
            "startup_or_self": 300,
            "unplaced": 400,
            "placement_rate_percent": 74,
        },
        "discipline_rate": [
            {"discipline": "CSE / IT", "placement_percent": 88},
            {"discipline": "AI / DS", "placement_percent": 91},
            {"discipline": "Mechanical", "placement_percent": 62},
            {"discipline": "Civil", "placement_percent": 58},
            {"discipline": "MBA", "placement_percent": 79},
            {"discipline": "Law", "placement_percent": 65},
            {"discipline": "Pharmacy", "placement_percent": 72},
            {"discipline": "Design", "placement_percent": 69},
            {"discipline": "Agriculture", "placement_percent": 55},
        ],
        "salary_bands": [
            {"range": "3-5 LPA", "students": 2000},
            {"range": "5-8 LPA", "students": 1500},
            {"range": "8-12 LPA", "students": 700},
            {"range": "12-20 LPA", "students": 300},
            {"range": "20+ LPA", "students": 100},
        ],
    },
    "mobility_model": {
        "daily_shuttle_riders": 18000,
        "daily_usage_percent": 52,
        "hostel_usage_percent": 78,
        "day_scholar_usage_percent": 24,
        "peak_slots": [
            {"slot": "07:00-08:00", "riders": 3200},
            {"slot": "08:00-09:00", "riders": 4100},
            {"slot": "16:00-17:00", "riders": 2900},
            {"slot": "18:00-20:00", "riders": 3600},
        ],
    },
    "library_model": {
        "daily_usage_range": "9,000-11,000",
        "peak_slots": [
            {"slot": "14:00-15:00", "students": 2200},
            {"slot": "16:00-18:00", "students": 3100},
            {"slot": "20:00-22:00", "students": 2800},
        ],
        "exam_surge_midsem_percent": 38,
        "exam_surge_endterm_percent": 55,
        "peak_late_night_occupancy": 4200,
    },
}


def _time_overlap(a_start, a_end, b_start, b_end) -> bool:
    return (a_start < b_end) and (b_start < a_end)


def _to_classroom_label(classroom: models.Classroom) -> str:
    return f"{classroom.block}-{classroom.room_number}"


def _safe_round(value: float, places: int = 2) -> float:
    return round(float(value), places)


def _room_number_from_floor(floor_index: int, serial_index: int) -> str:
    return f"{int(floor_index)}{int(serial_index):02d}"


def _build_admin_insights(
    *,
    summary: schemas.AdminSummaryOut,
    capacity_rows: list[schemas.AdminCapacityItem],
    workload_rows: list[schemas.AdminWorkloadItem],
) -> schemas.AdminInsightsOut:
    now_dt = datetime.utcnow()
    profile = deepcopy(ADMIN_REFERENCE_PROFILE)
    model_total = int(profile.get("active_students", {}).get("estimated", 0) or 0)
    live_students = max(0, int(summary.students or 0))
    live_capacity = _safe_round(summary.capacity_utilization_percent)
    live_attendance = _safe_round(summary.attendance_rate_today)
    live_workload = _safe_round(summary.workload_distribution_percent)

    utilization_slots = profile.get("classroom_utilization_model", {}).get("time_slots", [])
    peak_slot = max(
        utilization_slots,
        key=lambda item: float(item.get("utilization_percent", 0)),
        default={"slot": "--", "utilization_percent": 0},
    )
    placement_rate = float(
        profile.get("placement_model", {}).get("overall", {}).get("placement_rate_percent", 0)
    )
    overloaded_faculty = sum(1 for row in workload_rows if str(row.status) == "overloaded")
    underloaded_faculty = sum(1 for row in workload_rows if str(row.status) == "underloaded")
    top_rooms = [
        {
            "classroom": row.classroom_label,
            "course": row.primary_course_code,
            "utilization_percent": _safe_round(row.utilization_percent),
            "occupied": int(row.occupied_students),
            "capacity": int(row.total_available_seats),
        }
        for row in sorted(capacity_rows, key=lambda item: item.utilization_percent, reverse=True)[:5]
    ]

    profile["live_comparison"] = {
        "students_recorded_now": live_students,
        "student_model_estimate": model_total,
        "capacity_utilization_now_percent": live_capacity,
        "attendance_rate_now_percent": live_attendance,
        "workload_distribution_now_percent": live_workload,
        "capacity_peak_benchmark_percent": float(peak_slot.get("utilization_percent", 0) or 0),
        "capacity_gap_to_peak_percent": _safe_round(
            live_capacity - float(peak_slot.get("utilization_percent", 0) or 0)
        ),
        "placement_rate_benchmark_percent": _safe_round(placement_rate),
        "attendance_target_percent": 85.0,
        "workload_target_percent": 85.0,
        "overloaded_faculty_count": int(overloaded_faculty),
        "underloaded_faculty_count": int(underloaded_faculty),
        "top_loaded_rooms": top_rooms,
        "work_date": summary.last_updated_at.date().isoformat(),
    }

    profile["model_metadata"] = {
        "profile_id": ADMIN_REFERENCE_PROFILE_ID,
        "generated_at": now_dt.isoformat(),
        "source": "provided-planning-dataset",
        "notes": "Baseline planning model for administrative decisions. Live telemetry overlays these baselines.",
    }

    highlights = [
        (
            f"Live student records: {live_students:,} vs model baseline {model_total:,} "
            f"({_safe_round((live_students / model_total * 100.0) if model_total else 0)}% coverage)."
        ),
        (
            f"Current classroom utilization is {live_capacity}% against peak model "
            f"{peak_slot.get('utilization_percent', 0)}% ({peak_slot.get('slot')})."
        ),
        (
            f"Attendance rate today is {live_attendance}% with {summary.present_today} present "
            f"and {summary.absent_today} absent."
        ),
        (
            f"Workload distribution is {live_workload}%; overloaded faculty={overloaded_faculty}, "
            f"underloaded faculty={underloaded_faculty}."
        ),
        (
            f"Placement benchmark remains {int(placement_rate)}% for a final-year pool of "
            f"{int(profile.get('placement_model', {}).get('final_year_pool', 0)):,}."
        ),
    ]

    mirror_document(
        "admin_reference_profiles",
        {
            "profile_id": ADMIN_REFERENCE_PROFILE_ID,
            "profile": profile,
            "highlights": highlights,
            "last_updated_at": now_dt,
            "source": "admin-insights",
        },
        required=False,
    )
    return schemas.AdminInsightsOut(
        profile=profile,
        highlights=highlights,
        last_updated_at=now_dt,
    )


def _compute_capacity_rows(
    db: Session,
    *,
    work_date: date,
    mode: str = "enrollment",
) -> list[schemas.AdminCapacityItem]:
    schedules = (
        db.query(models.ClassSchedule)
        .filter(models.ClassSchedule.is_active.is_(True))
        .all()
    )
    if not schedules:
        return []

    course_ids = sorted({int(s.course_id) for s in schedules})
    enroll_counts = {
        int(course_id): int(count)
        for course_id, count in (
            db.query(models.Enrollment.course_id, func.count(models.Enrollment.id))
            .filter(models.Enrollment.course_id.in_(course_ids))
            .group_by(models.Enrollment.course_id)
            .all()
        )
    }
    attendance_counts = {
        int(course_id): int(count)
        for course_id, count in (
            db.query(models.AttendanceRecord.course_id, func.count(models.AttendanceRecord.id))
            .filter(
                models.AttendanceRecord.course_id.in_(course_ids),
                models.AttendanceRecord.attendance_date == work_date,
                models.AttendanceRecord.status == models.AttendanceStatus.PRESENT,
            )
            .group_by(models.AttendanceRecord.course_id)
            .all()
        )
    }
    courses_by_id = {
        row.id: row
        for row in db.query(models.Course).filter(models.Course.id.in_(course_ids)).all()
    }
    assignments = (
        db.query(models.CourseClassroom)
        .filter(models.CourseClassroom.course_id.in_(course_ids))
        .all()
    )
    room_by_course = {int(a.course_id): int(a.classroom_id) for a in assignments}
    room_ids = sorted({int(a.classroom_id) for a in assignments})
    classrooms_by_id = {
        row.id: row
        for row in db.query(models.Classroom).filter(models.Classroom.id.in_(room_ids)).all()
    }

    now_dt = datetime.utcnow()
    agg: dict[int, dict] = {}
    for schedule in schedules:
        room_id = room_by_course.get(int(schedule.course_id))
        if not room_id:
            continue
        classroom = classrooms_by_id.get(room_id)
        if not classroom or classroom.capacity <= 0:
            continue
        course = courses_by_id.get(int(schedule.course_id))
        if not course:
            continue
        row = agg.setdefault(
            int(room_id),
            {
                "classroom_id": int(room_id),
                "block": classroom.block,
                "classroom": _to_classroom_label(classroom),
                "primary_course_code": course.code,
                "scheduled_slots": 0,
                "occupied_students": 0,
                "attendance_marked_students": 0,
                "total_available_seats": 0,
                "capacity": int(classroom.capacity),
            },
        )
        enrolled = int(enroll_counts.get(int(schedule.course_id), 0))
        marked = int(attendance_counts.get(int(schedule.course_id), 0))
        occupied = marked if mode == "attendance_marked" else enrolled
        row["scheduled_slots"] += 1
        row["occupied_students"] += max(0, occupied)
        row["attendance_marked_students"] += max(0, marked)
        row["total_available_seats"] += int(classroom.capacity)

    rows: list[schemas.AdminCapacityItem] = []
    for row in agg.values():
        available = max(0, int(row["total_available_seats"]))
        occupied = max(0, int(row["occupied_students"]))
        utilization = (occupied / available * 100.0) if available else 0.0
        rows.append(
            schemas.AdminCapacityItem(
                classroom_id=int(row["classroom_id"]),
                block=str(row["block"]),
                classroom=str(row["classroom"]),
                classroom_label=str(row["classroom"]),
                primary_course_code=str(row["primary_course_code"]),
                scheduled_slots=int(row["scheduled_slots"]),
                occupied_students=occupied,
                attendance_marked_students=max(0, int(row["attendance_marked_students"])),
                total_available_seats=available,
                capacity=max(0, int(row["capacity"])),
                utilization_percent=_safe_round(utilization),
                mode=mode,
                last_updated_at=now_dt,
            )
        )
    rows.sort(key=lambda item: item.utilization_percent, reverse=True)
    return rows


def _compute_workload_rows(db: Session) -> list[schemas.AdminWorkloadItem]:
    faculty_rows = db.query(models.Faculty).all()
    if not faculty_rows:
        return []
    faculty_ids = [int(f.id) for f in faculty_rows]

    schedules = (
        db.query(models.ClassSchedule)
        .filter(
            models.ClassSchedule.is_active.is_(True),
            models.ClassSchedule.faculty_id.in_(faculty_ids),
        )
        .all()
    )
    by_faculty_schedules: dict[int, list[models.ClassSchedule]] = defaultdict(list)
    for schedule in schedules:
        by_faculty_schedules[int(schedule.faculty_id)].append(schedule)

    faculty_courses = (
        db.query(models.Course.id, models.Course.faculty_id)
        .filter(models.Course.faculty_id.in_(faculty_ids))
        .all()
    )
    by_faculty_course_ids: dict[int, set[int]] = defaultdict(set)
    all_course_ids: set[int] = set()
    for course_id, faculty_id in faculty_courses:
        by_faculty_course_ids[int(faculty_id)].add(int(course_id))
        all_course_ids.add(int(course_id))

    enroll_counts = {
        int(course_id): int(count)
        for course_id, count in (
            db.query(models.Enrollment.course_id, func.count(models.Enrollment.id))
            .filter(models.Enrollment.course_id.in_(all_course_ids or [0]))
            .group_by(models.Enrollment.course_id)
            .all()
        )
    }

    now_dt = datetime.utcnow()
    results: list[schemas.AdminWorkloadItem] = []
    for faculty in faculty_rows:
        schedule_list = by_faculty_schedules.get(int(faculty.id), [])
        assigned_hours = 0.0
        for schedule in schedule_list:
            start_minutes = int(schedule.start_time.hour) * 60 + int(schedule.start_time.minute)
            end_minutes = int(schedule.end_time.hour) * 60 + int(schedule.end_time.minute)
            assigned_hours += max(0, (end_minutes - start_minutes) / 60.0)
        target_hours = FACULTY_TARGET_HOURS_DEFAULT
        workload_percent = (assigned_hours / target_hours * 100.0) if target_hours > 0 else 0.0
        course_ids = by_faculty_course_ids.get(int(faculty.id), set())
        total_enrolled = sum(enroll_counts.get(course_id, 0) for course_id in course_ids)
        status = "balanced"
        if workload_percent > 100:
            status = "overloaded"
        elif workload_percent < 60:
            status = "underloaded"
        results.append(
            schemas.AdminWorkloadItem(
                faculty_id=int(faculty.id),
                faculty_name=str(faculty.name),
                department=str(faculty.department),
                assigned_courses=len(course_ids),
                assigned_hours=_safe_round(assigned_hours),
                target_hours=_safe_round(target_hours),
                workload_percent=_safe_round(workload_percent),
                total_enrolled_students=int(total_enrolled),
                status=status,
                last_updated_at=now_dt,
            )
        )
    results.sort(key=lambda item: item.workload_percent, reverse=True)
    return results


def _detect_timetable_conflicts(db: Session) -> list[dict]:
    schedules = (
        db.query(models.ClassSchedule)
        .filter(models.ClassSchedule.is_active.is_(True))
        .order_by(models.ClassSchedule.weekday.asc(), models.ClassSchedule.start_time.asc())
        .all()
    )
    if not schedules:
        return []
    course_rows = db.query(models.Course.id, models.Course.code).all()
    course_code_by_id = {int(c_id): str(code) for c_id, code in course_rows}
    assignments = db.query(models.CourseClassroom).all()
    room_by_course = {int(row.course_id): int(row.classroom_id) for row in assignments}
    classrooms = db.query(models.Classroom).all()
    room_label_by_id = {int(row.id): _to_classroom_label(row) for row in classrooms}

    conflicts: list[dict] = []
    by_weekday: dict[int, list[models.ClassSchedule]] = defaultdict(list)
    for schedule in schedules:
        by_weekday[int(schedule.weekday)].append(schedule)

    for weekday, day_rows in by_weekday.items():
        count = len(day_rows)
        for idx in range(count):
            left = day_rows[idx]
            for jdx in range(idx + 1, count):
                right = day_rows[jdx]
                if not _time_overlap(left.start_time, left.end_time, right.start_time, right.end_time):
                    if right.start_time >= left.end_time:
                        break
                    continue

                left_course = int(left.course_id)
                right_course = int(right.course_id)
                same_faculty = int(left.faculty_id) == int(right.faculty_id)
                same_room = (
                    room_by_course.get(left_course) is not None
                    and room_by_course.get(left_course) == room_by_course.get(right_course)
                )
                if not same_faculty and not same_room:
                    continue
                conflict_type = "faculty_time_overlap" if same_faculty else "classroom_time_overlap"
                room_id = room_by_course.get(left_course) if same_room else None
                conflicts.append(
                    {
                        "issue_type": conflict_type,
                        "severity": "high",
                        "weekday": int(weekday),
                        "schedule_a_id": int(left.id),
                        "schedule_b_id": int(right.id),
                        "faculty_id": int(left.faculty_id) if same_faculty else None,
                        "room_id": int(room_id) if room_id else None,
                        "room_label": room_label_by_id.get(int(room_id)) if room_id else None,
                        "window": f"{left.start_time.strftime('%H:%M')}-{left.end_time.strftime('%H:%M')}",
                        "course_a": course_code_by_id.get(left_course, f"#{left_course}"),
                        "course_b": course_code_by_id.get(right_course, f"#{right_course}"),
                    }
                )
    return conflicts


def _build_alerts(
    *,
    capacity_rows: Iterable[schemas.AdminCapacityItem],
    workload_rows: Iterable[schemas.AdminWorkloadItem],
    conflicts: Iterable[dict],
    now_dt: datetime,
) -> list[schemas.AdminAlertItem]:
    alerts: list[schemas.AdminAlertItem] = []
    for row in capacity_rows:
        if row.utilization_percent > OVERLOAD_UTILIZATION_PERCENT:
            alerts.append(
                schemas.AdminAlertItem(
                    id=f"room-overload-{row.classroom_id}",
                    issue_type="room_overload",
                    severity="high",
                    message=f"{row.classroom} at {row.utilization_percent:.1f}% utilization",
                    context={
                        "block": row.block,
                        "scheduled_slots": row.scheduled_slots,
                        "occupied_students": row.occupied_students,
                        "capacity": row.total_available_seats,
                    },
                    last_updated_at=now_dt,
                )
            )
    for row in workload_rows:
        if row.workload_percent > 100:
            alerts.append(
                schemas.AdminAlertItem(
                    id=f"faculty-overload-{row.faculty_id}",
                    issue_type="faculty_overload",
                    severity="high",
                    message=f"{row.faculty_name} at {row.workload_percent:.1f}% workload",
                    context={
                        "department": row.department,
                        "assigned_hours": row.assigned_hours,
                        "target_hours": row.target_hours,
                        "assigned_courses": row.assigned_courses,
                    },
                    last_updated_at=now_dt,
                )
            )
    for idx, conflict in enumerate(conflicts):
        alerts.append(
            schemas.AdminAlertItem(
                id=f"timetable-conflict-{idx + 1}",
                issue_type=str(conflict.get("issue_type") or "timetable_conflict"),
                severity=str(conflict.get("severity") or "high"),
                message=(
                    f"{conflict.get('course_a', 'N/A')} vs {conflict.get('course_b', 'N/A')} "
                    f"on weekday {int(conflict.get('weekday', 0))} ({conflict.get('window', '--')})"
                ),
                context=conflict,
                last_updated_at=now_dt,
            )
        )
    alerts.sort(key=lambda row: (row.severity != "high", row.issue_type, row.id))
    return alerts[:20]


def _sync_admin_mongo(
    db: Session,
    *,
    now_dt: datetime,
    work_date: date,
    summary: schemas.AdminSummaryOut,
    capacity_rows: list[schemas.AdminCapacityItem],
    workload_rows: list[schemas.AdminWorkloadItem],
    alerts: list[schemas.AdminAlertItem],
) -> None:
    mongo_db = get_mongo_db()
    if mongo_db is None:
        return

    for block, classroom_count, total_capacity in (
        db.query(
            models.Classroom.block,
            func.count(models.Classroom.id),
            func.coalesce(func.sum(models.Classroom.capacity), 0),
        )
        .group_by(models.Classroom.block)
        .all()
    ):
        mongo_db["blocks"].update_one(
            {"block": str(block)},
            {
                "$set": {
                    "block": str(block),
                    "classroom_count": int(classroom_count or 0),
                    "total_capacity": int(total_capacity or 0),
                    "updated_at": now_dt,
                    "source": "admin-live-sync",
                }
            },
            upsert=True,
        )

    schedules = (
        db.query(models.ClassSchedule)
        .filter(models.ClassSchedule.is_active.is_(True))
        .all()
    )
    assignments = db.query(models.CourseClassroom).all()
    room_by_course = {int(row.course_id): int(row.classroom_id) for row in assignments}
    room_rows = db.query(models.Classroom).all()
    room_label_by_id = {int(row.id): _to_classroom_label(row) for row in room_rows}
    for schedule in schedules:
        room_id = room_by_course.get(int(schedule.course_id))
        mongo_db["timetable"].update_one(
            {"schedule_id": int(schedule.id)},
            {
                "$set": {
                    "schedule_id": int(schedule.id),
                    "course_id": int(schedule.course_id),
                    "faculty_id": int(schedule.faculty_id),
                    "classroom_id": int(room_id) if room_id else None,
                    "classroom_label": room_label_by_id.get(int(room_id)) if room_id else schedule.classroom_label,
                    "weekday": int(schedule.weekday),
                    "start_time": str(schedule.start_time),
                    "end_time": str(schedule.end_time),
                    "is_active": bool(schedule.is_active),
                    "updated_at": now_dt,
                    "source": "admin-live-sync",
                }
            },
            upsert=True,
        )

    mirror_document(
        "admin_summary_snapshots",
        {
            "work_date": work_date.isoformat(),
            "summary": summary.model_dump(),
            "capacity": [row.model_dump() for row in capacity_rows],
            "workload": [row.model_dump() for row in workload_rows],
            "alerts": [row.model_dump() for row in alerts],
            "created_at": now_dt,
            "source": "admin-live-sync",
        },
        required=False,
    )

    for alert in alerts:
        mongo_db["admin_alerts"].update_one(
            {"id": alert.id},
            {"$set": {**alert.model_dump(), "updated_at": now_dt, "work_date": work_date.isoformat()}},
            upsert=True,
        )


def _build_admin_payload(db: Session, *, work_date: date, mode: str) -> tuple[
    schemas.AdminSummaryOut,
    list[schemas.AdminCapacityItem],
    list[schemas.AdminWorkloadItem],
    list[schemas.AdminAlertItem],
]:
    now_dt = datetime.utcnow()
    blocks_count = db.query(func.count(func.distinct(models.Classroom.block))).scalar() or 0
    classrooms_count = db.query(models.Classroom).count()
    courses_count = db.query(models.Course).count()
    faculty_count = db.query(models.Faculty).count()
    students_count = db.query(models.Student).count()

    work_weekday = int(work_date.weekday())
    active_course_ids = [
        int(row.course_id)
        for row in (
            db.query(models.ClassSchedule.course_id)
            .filter(
                models.ClassSchedule.is_active.is_(True),
                models.ClassSchedule.weekday == work_weekday,
            )
            .distinct()
            .all()
        )
    ]
    active_today = 0
    if active_course_ids:
        active_today = int(
            db.query(func.count(func.distinct(models.Enrollment.student_id)))
            .filter(models.Enrollment.course_id.in_(active_course_ids))
            .scalar()
            or 0
        )

    present_today = int(
        db.query(func.count(func.distinct(models.AttendanceRecord.student_id)))
        .filter(
            models.AttendanceRecord.attendance_date == work_date,
            models.AttendanceRecord.status == models.AttendanceStatus.PRESENT,
        )
        .scalar()
        or 0
    )
    absent_today_records = int(
        db.query(func.count(func.distinct(models.AttendanceRecord.student_id)))
        .filter(
            models.AttendanceRecord.attendance_date == work_date,
            models.AttendanceRecord.status == models.AttendanceStatus.ABSENT,
        )
        .scalar()
        or 0
    )
    absent_today = max(absent_today_records, max(0, active_today - present_today))
    attendance_denominator = active_today if active_today > 0 else (present_today + absent_today)
    attendance_rate_today = (
        _safe_round((present_today / attendance_denominator) * 100.0)
        if attendance_denominator > 0
        else 0.0
    )

    per_student_stats = (
        db.query(
            models.AttendanceRecord.student_id,
            func.count(models.AttendanceRecord.id).label("marked"),
            func.sum(
                case(
                    (models.AttendanceRecord.status == models.AttendanceStatus.PRESENT, 1),
                    else_=0,
                )
            ).label("present"),
        )
        .group_by(models.AttendanceRecord.student_id)
        .all()
    )
    at_risk_students = 0
    for student_id, marked, present in per_student_stats:
        marked_count = int(marked or 0)
        present_count = int(present or 0)
        if marked_count < 4:
            continue
        percent = (present_count / marked_count * 100.0) if marked_count else 0.0
        if percent < 75.0:
            at_risk_students += 1

    capacity_rows = _compute_capacity_rows(db, work_date=work_date, mode=mode)
    workload_rows = _compute_workload_rows(db)
    conflicts = _detect_timetable_conflicts(db)
    alerts = _build_alerts(
        capacity_rows=capacity_rows,
        workload_rows=workload_rows,
        conflicts=conflicts,
        now_dt=now_dt,
    )

    avg_capacity_util = (
        _safe_round(sum(row.utilization_percent for row in capacity_rows) / len(capacity_rows))
        if capacity_rows
        else 0.0
    )
    avg_workload = (
        _safe_round(sum(row.workload_percent for row in workload_rows) / len(workload_rows))
        if workload_rows
        else 0.0
    )

    data_quality_score = 100.0
    if not capacity_rows:
        data_quality_score -= 18.0
    if not workload_rows:
        data_quality_score -= 18.0
    if not active_today:
        data_quality_score -= 10.0
    if conflicts:
        data_quality_score -= min(30.0, len(conflicts) * 4.0)
    data_quality_score = _safe_round(max(0.0, min(100.0, data_quality_score)))

    top_issues = [
        schemas.AdminTopIssueItem(
            issue_type=alert.issue_type,
            severity=alert.severity,
            message=alert.message,
            context=alert.context,
        )
        for alert in alerts[:8]
    ]

    summary = schemas.AdminSummaryOut(
        blocks=int(blocks_count),
        classrooms=int(classrooms_count),
        courses=int(courses_count),
        faculty=int(faculty_count),
        students=int(students_count),
        active_today=int(active_today),
        present_today=int(present_today),
        absent_today=int(absent_today),
        attendance_rate_today=float(attendance_rate_today),
        at_risk_students=int(at_risk_students),
        capacity_utilization_percent=float(avg_capacity_util),
        workload_distribution_percent=float(avg_workload),
        conflict_count=len(conflicts),
        data_quality_score=float(data_quality_score),
        top_issues=top_issues,
        mongo_status=mongo_status(),
        last_updated_at=now_dt,
        stale_after_seconds=STALE_AFTER_SECONDS,
    )

    _sync_admin_mongo(
        db,
        now_dt=now_dt,
        work_date=work_date,
        summary=summary,
        capacity_rows=capacity_rows,
        workload_rows=workload_rows,
        alerts=alerts,
    )
    return summary, capacity_rows, workload_rows, alerts


def _bootstrap_department_classrooms(
    db: Session,
    *,
    default_capacity: int,
    replace_existing: bool,
    actor_email: str,
) -> dict:
    created = 0
    existing = 0
    updated = 0
    block_total = 0
    room_total = 0
    now_dt = datetime.utcnow()

    block_department_map: dict[str, str] = {}
    block_school_map: dict[str, str] = {}
    block_specs: dict[str, dict] = {}

    for department, config in DEPARTMENT_CLASSROOM_LAYOUT.items():
        school = str(config.get("school") or department)
        blocks = config.get("blocks") or []
        for block_cfg in blocks:
            block = str(block_cfg.get("block"))
            floors = max(1, int(block_cfg.get("floors") or 1))
            rooms_per_floor = max(1, int(block_cfg.get("rooms_per_floor") or 1))
            planned_rooms = floors * rooms_per_floor
            block_total += 1
            room_total += planned_rooms
            block_department_map[block] = department
            block_school_map[block] = school
            block_specs[block] = {
                "department": department,
                "school": school,
                "floors": floors,
                "rooms_per_floor": rooms_per_floor,
                "planned_rooms": planned_rooms,
            }

            for floor in range(1, floors + 1):
                for serial in range(1, rooms_per_floor + 1):
                    room_number = _room_number_from_floor(floor, serial)
                    row = (
                        db.query(models.Classroom)
                        .filter(
                            models.Classroom.block == block,
                            models.Classroom.room_number == room_number,
                        )
                        .first()
                    )
                    if row:
                        existing += 1
                        if replace_existing and int(row.capacity) != int(default_capacity):
                            row.capacity = int(default_capacity)
                            updated += 1
                    else:
                        db.add(
                            models.Classroom(
                                block=block,
                                room_number=room_number,
                                capacity=int(default_capacity),
                            )
                        )
                        created += 1

    db.flush()
    mongo_db = get_mongo_db()
    if mongo_db is not None:
        all_blocks = sorted(block_specs.keys())
        room_rows = (
            db.query(models.Classroom)
            .filter(models.Classroom.block.in_(all_blocks))
            .all()
        )
        block_counts: dict[str, int] = defaultdict(int)
        block_capacity: dict[str, int] = defaultdict(int)
        for room in room_rows:
            block = str(room.block)
            block_counts[block] += 1
            block_capacity[block] += max(0, int(room.capacity or 0))
            mongo_db["classrooms"].update_one(
                {"id": int(room.id)},
                {
                    "$set": {
                        "id": int(room.id),
                        "block": block,
                        "room_number": str(room.room_number),
                        "classroom_label": f"{block}-{room.room_number}",
                        "capacity": int(room.capacity or 0),
                        "department": block_department_map.get(block),
                        "school": block_school_map.get(block),
                        "updated_at": now_dt,
                        "source": "department-bootstrap",
                    }
                },
                upsert=True,
            )
        for block in all_blocks:
            spec = block_specs.get(block) or {}
            mongo_db["blocks"].update_one(
                {"block": block},
                {
                    "$set": {
                        "block": block,
                        "department": spec.get("department"),
                        "school": spec.get("school"),
                        "floors": int(spec.get("floors") or 0),
                        "rooms_per_floor": int(spec.get("rooms_per_floor") or 0),
                        "planned_rooms": int(spec.get("planned_rooms") or 0),
                        "classroom_count": int(block_counts.get(block, 0)),
                        "total_capacity": int(block_capacity.get(block, 0)),
                        "updated_at": now_dt,
                        "source": "department-bootstrap",
                    }
                },
                upsert=True,
            )

    mirror_document(
        "admin_audit_logs",
        {
            "action": "department_classroom_bootstrap",
            "actor_email": actor_email,
            "created": int(created),
            "existing": int(existing),
            "updated": int(updated),
            "blocks": int(block_total),
            "planned_rooms": int(room_total),
            "default_capacity": int(default_capacity),
            "replace_existing": bool(replace_existing),
            "created_at": now_dt,
            "source": "admin",
        },
        required=False,
    )
    return {
        "created": int(created),
        "existing": int(existing),
        "updated": int(updated),
        "blocks": int(block_total),
        "planned_rooms": int(room_total),
        "default_capacity": int(default_capacity),
        "replace_existing": bool(replace_existing),
        "departments": {
            dept: {
                "school": str(config.get("school") or dept),
                "blocks": [str(item.get("block")) for item in (config.get("blocks") or [])],
            }
            for dept, config in DEPARTMENT_CLASSROOM_LAYOUT.items()
        },
    }


@router.get("/summary", response_model=schemas.AdminSummaryOut)
def admin_summary(
    work_date: date | None = Query(default=None),
    mode: str = Query(default="enrollment", pattern="^(enrollment|attendance_marked)$"),
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.STUDENT)
    ),
):
    target_date = work_date or date.today()
    summary, _, _, _ = _build_admin_payload(db, work_date=target_date, mode=mode)
    return summary


@router.get("/capacity", response_model=list[schemas.AdminCapacityItem])
def admin_capacity(
    work_date: date | None = Query(default=None),
    mode: str = Query(default="enrollment", pattern="^(enrollment|attendance_marked)$"),
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.STUDENT)
    ),
):
    target_date = work_date or date.today()
    _, capacity_rows, _, _ = _build_admin_payload(db, work_date=target_date, mode=mode)
    return capacity_rows


@router.get("/workload", response_model=list[schemas.AdminWorkloadItem])
def admin_workload(
    work_date: date | None = Query(default=None),
    mode: str = Query(default="enrollment", pattern="^(enrollment|attendance_marked)$"),
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.STUDENT)
    ),
):
    target_date = work_date or date.today()
    _, _, workload_rows, _ = _build_admin_payload(db, work_date=target_date, mode=mode)
    return workload_rows


@router.get("/alerts", response_model=list[schemas.AdminAlertItem])
def admin_alerts(
    work_date: date | None = Query(default=None),
    mode: str = Query(default="enrollment", pattern="^(enrollment|attendance_marked)$"),
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.STUDENT)
    ),
):
    target_date = work_date or date.today()
    _, _, _, alerts = _build_admin_payload(db, work_date=target_date, mode=mode)
    return alerts


@router.get("/live", response_model=schemas.AdminLiveOut)
def admin_live(
    work_date: date | None = Query(default=None),
    mode: str = Query(default="enrollment", pattern="^(enrollment|attendance_marked)$"),
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.STUDENT)
    ),
):
    target_date = work_date or date.today()
    summary, capacity_rows, workload_rows, alerts = _build_admin_payload(
        db,
        work_date=target_date,
        mode=mode,
    )
    return schemas.AdminLiveOut(
        summary=summary,
        capacity=capacity_rows,
        workload=workload_rows,
        alerts=alerts,
        last_updated_at=summary.last_updated_at,
        stale_after_seconds=STALE_AFTER_SECONDS,
    )


@router.get("/insights", response_model=schemas.AdminInsightsOut)
def admin_insights(
    work_date: date | None = Query(default=None),
    mode: str = Query(default="enrollment", pattern="^(enrollment|attendance_marked)$"),
    db: Session = Depends(get_db),
    _: models.AuthUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.STUDENT)
    ),
):
    target_date = work_date or date.today()
    summary, capacity_rows, workload_rows, _ = _build_admin_payload(
        db,
        work_date=target_date,
        mode=mode,
    )
    return _build_admin_insights(
        summary=summary,
        capacity_rows=capacity_rows,
        workload_rows=workload_rows,
    )


@router.post("/bootstrap/departments/classrooms")
def bootstrap_department_classrooms(
    default_capacity: int = Query(
        default=DEPARTMENT_CLASSROOM_DEFAULT_CAPACITY,
        ge=20,
        le=250,
    ),
    replace_existing: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: models.AuthUser = Depends(require_roles(models.UserRole.ADMIN)),
):
    payload = _bootstrap_department_classrooms(
        db,
        default_capacity=default_capacity,
        replace_existing=replace_existing,
        actor_email=str(getattr(user, "email", "") or "unknown"),
    )
    db.commit()
    return {
        "message": "Department classroom blueprint applied successfully.",
        **payload,
        "last_updated_at": datetime.utcnow(),
    }
