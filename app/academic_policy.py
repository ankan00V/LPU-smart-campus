import os
import re
from datetime import date, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models

ACADEMIC_TERM_CONFIG_KEY = "default"
SECTION_CAPACITY = 60
ACADEMIC_START_DATE_DEFAULT = "2025-07-01"
ACADEMIC_END_DATE_DEFAULT = "2026-07-01"

_STREAM_ALIASES = (
    (("COMPUTER", "SCIENCE", "ENGINEERING"), "CSE"),
    (("COMPUTER", "SCIENCE"), "CSE"),
    (("CSE",), "CSE"),
    (("INFORMATION", "TECHNOLOGY"), "IT"),
    (("ELECTRONICS", "COMMUNICATION"), "ECE"),
    (("ELECTRICAL",), "EEE"),
    (("MECHANICAL",), "ME"),
    (("CIVIL",), "CE"),
)
_STOP_WORDS = {"SCHOOL", "OF", "AND", "THE", "DEPARTMENT", "DEPT", "ENGINEERING", "TECHNOLOGY"}


def parse_date_env(name: str, fallback: str) -> date:
    raw = (os.getenv(name, fallback) or fallback).strip()
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return date.fromisoformat(fallback)


def academic_window(db: Session | None = None) -> tuple[date, date]:
    if db is not None:
        config = db.get(models.AcademicTermConfig, ACADEMIC_TERM_CONFIG_KEY)
        if config is not None:
            return config.class_start_date, config.class_end_date
    return (
        parse_date_env("ACADEMIC_CLASS_START_DATE", ACADEMIC_START_DATE_DEFAULT),
        parse_date_env("ACADEMIC_CLASS_END_DATE", ACADEMIC_END_DATE_DEFAULT),
    )


def current_half_year_term(day: date) -> tuple[date, date]:
    if day.month <= 6:
        return date(day.year, 1, 1), date(day.year, 6, 30)
    return date(day.year, 7, 1), date(day.year, 12, 31)


def terms_elapsed(from_day: date, to_day: date) -> int:
    from_start, _ = current_half_year_term(from_day)
    to_start, _ = current_half_year_term(to_day)
    return max(0, ((to_start.year - from_start.year) * 2) + ((to_start.month - from_start.month) // 6))


def stream_initials(department: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", str(department or "").upper()).strip()
    words = [word for word in normalized.split() if word]
    if not words:
        return "GEN"
    word_set = set(words)
    for needles, alias in _STREAM_ALIASES:
        if all(needle in word_set for needle in needles):
            return alias
    initials = "".join(word[0] for word in words if word not in _STOP_WORDS and word[0].isalnum())
    return (initials or words[0][:3] or "GEN")[:6]


def section_base(*, semester: int, department: str, day: date) -> str:
    return f"{int(semester)}{day.year % 100:02d}{stream_initials(department)}"


def section_for_bucket(base: str, bucket_index: int) -> str:
    if bucket_index <= 0:
        return base
    return f"{base}{bucket_index + 1}"


def assign_student_section(
    db: Session,
    student: models.Student,
    *,
    now: datetime | None = None,
    force: bool = False,
) -> str:
    current_dt = now or datetime.utcnow()
    today = current_dt.date()
    marker = (student.section_updated_at or student.created_at or current_dt).date()
    elapsed = terms_elapsed(marker, today)
    if elapsed:
        student.semester = min(12, int(student.semester or 1) + elapsed)

    base = section_base(semester=int(student.semester or 1), department=student.department, day=today)
    if student.section and not elapsed and not force:
        return student.section

    existing_sections = [
        row[0]
        for row in (
            db.query(models.Student.section)
            .filter(
                models.Student.id != student.id,
                models.Student.semester == student.semester,
                models.Student.section.isnot(None),
                models.Student.section.like(f"{base}%"),
            )
            .all()
        )
        if row and row[0]
    ]
    if existing_sections:
        counts = {
            section: int(
                db.query(func.count(models.Student.id))
                .filter(
                    models.Student.id != student.id,
                    models.Student.semester == student.semester,
                    models.Student.section == section,
                )
                .scalar()
                or 0
            )
            for section in sorted(set(existing_sections), key=lambda item: (len(str(item)), str(item)))
        }
        for section, count in counts.items():
            if count < SECTION_CAPACITY:
                student.section = section
                break
        else:
            student.section = section_for_bucket(base, len(counts))
    else:
        student.section = base

    student.section_updated_at = current_dt
    return str(student.section)


def sync_student_academic_term(db: Session, student: models.Student, *, now: datetime | None = None) -> bool:
    previous_section = student.section
    previous_semester = int(student.semester or 0)
    assign_student_section(db, student, now=now)
    return previous_section != student.section or previous_semester != int(student.semester or 0)
