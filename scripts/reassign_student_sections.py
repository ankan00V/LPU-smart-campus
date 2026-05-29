#!/usr/bin/env python3
"""Force existing students onto the current system-assigned section policy."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path

from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_env_file() -> None:
    for key, value in dotenv_values(PROJECT_ROOT / ".env").items():
        if value is not None:
            os.environ[key] = str(value)
    os.environ.setdefault("PYTHONPATH", str(PROJECT_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes without writing them.")
    parser.add_argument("--limit", type=int, default=0, help="Limit updated students for a controlled rollout.")
    args = parser.parse_args()

    _load_env_file()

    from app import models  # noqa: PLC0415
    from app.academic_policy import assign_student_section  # noqa: PLC0415
    from app.database import SessionLocal  # noqa: PLC0415
    from app.routers.attendance import _sync_student_to_mongo  # noqa: PLC0415

    now = datetime.now()
    session = SessionLocal()
    changed: list[dict[str, object]] = []
    before_counts: Counter[str] = Counter()
    after_counts: Counter[str] = Counter()
    try:
        students = (
            session.query(models.Student)
            .order_by(
                models.Student.semester.asc(),
                models.Student.department.asc(),
                models.Student.created_at.asc(),
                models.Student.id.asc(),
            )
            .all()
        )
        for student in students:
            before_section = str(student.section or "").strip() or "UNASSIGNED"
            before_counts[before_section] += 1
            before_semester = int(student.semester or 0)
            assign_student_section(session, student, now=now, force=True)
            after_section = str(student.section or "").strip() or "UNASSIGNED"
            after_counts[after_section] += 1
            if before_section == after_section and before_semester == int(student.semester or 0):
                continue
            changed.append(
                {
                    "student_id": int(student.id),
                    "registration_number": student.registration_number,
                    "email": student.email,
                    "from_section": before_section,
                    "to_section": after_section,
                    "from_semester": before_semester,
                    "to_semester": int(student.semester or 0),
                }
            )
            if args.limit and len(changed) >= args.limit:
                break

        if args.dry_run:
            session.rollback()
        else:
            session.flush()
            for row in changed:
                student = session.get(models.Student, int(row["student_id"]))
                if student is not None:
                    _sync_student_to_mongo(session, student, source="student-section-policy-reassignment")
            session.commit()

        print(
            json.dumps(
                {
                    "dry_run": bool(args.dry_run),
                    "total_students_seen": len(students),
                    "changed_students": len(changed),
                    "before_sections": dict(sorted(before_counts.items())),
                    "after_sections": dict(sorted(after_counts.items())),
                    "sample_changes": changed[:20],
                },
                indent=2,
                default=str,
            )
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
