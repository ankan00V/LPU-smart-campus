#!/usr/bin/env python3
"""CI migration gate for SQLite schema safety and idempotency."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from pathlib import Path


def _assert_columns(conn: sqlite3.Connection, table: str, required: set[str]) -> None:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    existing = {str(row[1]) for row in rows}
    missing = sorted(required - existing)
    if missing:
        raise RuntimeError(f"Missing columns in {table}: {', '.join(missing)}")


def _assert_tables(conn: sqlite3.Connection, required: set[str]) -> None:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    existing = {str(row[0]) for row in rows}
    missing = sorted(required - existing)
    if missing:
        raise RuntimeError(f"Missing tables: {', '.join(missing)}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="migration-gate-") as tmp_dir:
        db_path = Path(tmp_dir) / "ci-migration.db"

        os.environ["SQLALCHEMY_DATABASE_URL"] = f"sqlite:///{db_path}"
        os.environ.setdefault("MONGO_PERSISTENCE_REQUIRED", "false")
        os.environ.setdefault("REDIS_REQUIRED", "false")
        os.environ.setdefault("WORKER_REQUIRED", "false")
        os.environ.setdefault("APP_RUNTIME_STRICT", "false")

        # Import only after env injection so SQLAlchemy engine points to temp DB.
        from app.main import init_sql_schema  # noqa: PLC0415

        # Must be safe to run repeatedly from an empty database.
        init_sql_schema()
        init_sql_schema()

        conn = sqlite3.connect(db_path)
        try:
            _assert_tables(
                conn,
                {
                    "attendance_events",
                    "copilot_audit_logs",
                    "auth_sessions",
                    "auth_token_revocations",
                    "media_objects",
                    "outbox_events",
                },
            )
            _assert_columns(
                conn,
                "students",
                {"profile_photo_object_key"},
            )
            _assert_columns(
                conn,
                "faculty",
                {"profile_photo_object_key"},
            )
            _assert_columns(
                conn,
                "attendance_records",
                {"updated_at", "computed_from_event_id"},
            )
            _assert_columns(
                conn,
                "attendance_submissions",
                {
                    "selfie_photo_object_key",
                    "location_latitude",
                    "location_longitude",
                    "location_accuracy_m",
                    "location_distance_m",
                    "location_allowed_radius_m",
                    "attendance_session_id",
                    "attendance_session_code_hash",
                    "attendance_attempt_token_hash",
                    "browser_fingerprint_hash",
                    "client_ip_hash",
                    "user_agent_hash",
                    "client_integrity_flags",
                },
            )
            _assert_columns(
                conn,
                "class_attendance_sessions",
                {
                    "schedule_id",
                    "course_id",
                    "faculty_id",
                    "class_date",
                    "session_code_hash",
                    "code_rotation_seconds",
                    "current_code_expires_at",
                    "generated_at",
                    "expires_at",
                    "opened_by_user_id",
                    "is_active",
                    "created_at",
                    "updated_at",
                },
            )
            _assert_columns(
                conn,
                "attendance_attempt_tokens",
                {
                    "attendance_session_id",
                    "schedule_id",
                    "student_id",
                    "class_date",
                    "token_hash",
                    "session_code_hash",
                    "browser_fingerprint_hash",
                    "client_ip_hash",
                    "user_agent_hash",
                    "client_integrity_flags",
                    "issued_at",
                    "expires_at",
                    "consumed_at",
                    "attempt_count",
                    "max_attempts",
                    "last_seen_at",
                    "last_rejection_reason",
                    "created_at",
                    "updated_at",
                },
            )
            _assert_columns(
                conn,
                "class_schedules",
                {
                    "attendance_latitude",
                    "attendance_longitude",
                    "attendance_radius_m",
                    "attendance_location_label",
                },
            )
            _assert_columns(
                conn,
                "attendance_rectification_requests",
                {"proof_photo_object_key"},
            )
            _assert_columns(
                conn,
                "copilot_audit_logs",
                {"feedback_rating", "feedback_comment", "feedback_helpful", "feedback_at"},
            )
            _assert_columns(
                conn,
                "classroom_analyses",
                {"photo_object_key"},
            )
        finally:
            conn.close()

    print(json.dumps({"migration_gate": "pass"}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"migration_gate": "fail", "error": str(exc)}, indent=2))
        raise SystemExit(1)
