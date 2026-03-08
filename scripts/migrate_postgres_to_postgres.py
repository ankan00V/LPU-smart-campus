#!/usr/bin/env python3
"""Copy application data from one PostgreSQL database into another."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app import models  # noqa: F401
from app.database import Base
from app.postgres_tools import require_postgres_command


def _normalized_postgres_url(raw: str) -> str:
    value = str(raw or "").strip()
    if value.startswith("postgres://"):
        return f"postgresql+psycopg://{value[len('postgres://'):]}"
    if value.startswith("postgresql://") and not value.startswith("postgresql+"):
        return f"postgresql+psycopg://{value[len('postgresql://'):]}"
    return value


def _libpq_url(raw: str) -> str:
    value = _normalized_postgres_url(raw)
    if value.startswith("postgresql+"):
        prefix, remainder = value.split("://", 1)
        backend = prefix.split("+", 1)[0]
        return f"{backend}://{remainder}"
    return value


def _sanitized_url(raw: str) -> str:
    return make_url(_normalized_postgres_url(raw)).render_as_string(hide_password=True)


def _ensure_postgres_url(raw: str, flag_name: str) -> str:
    normalized = _normalized_postgres_url(raw)
    if not normalized.startswith("postgresql"):
        raise SystemExit(f"{flag_name} must be a PostgreSQL SQLAlchemy URL")
    return normalized


def _ensure_required_tools() -> None:
    for name in ("pg_dump", "psql"):
        require_postgres_command(name)


def _assert_distinct_databases(source_url: str, target_url: str) -> None:
    source = make_url(source_url)
    target = make_url(target_url)

    def signature(url) -> tuple[str, int, str, str]:
        return (
            str(url.host or "").strip().lower(),
            int(url.port or 5432),
            str(url.database or "").strip().lower(),
            str(url.username or "").strip().lower(),
        )

    if signature(source) == signature(target):
        raise SystemExit("Source and target PostgreSQL URLs resolve to the same database")


def _run(command: list[str]) -> None:
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"Command failed: {' '.join(command[:2])}") from exc


def _count_rows(engine) -> dict[str, int]:
    counts: dict[str, int] = {}
    with engine.connect() as connection:
        for table in Base.metadata.sorted_tables:
            count = connection.execute(text(f'SELECT COUNT(*) FROM "{table.name}"')).scalar_one()
            counts[table.name] = int(count)
    return counts


def _compare_counts(source_counts: dict[str, int], target_counts: dict[str, int]) -> dict[str, dict[str, int]]:
    mismatches: dict[str, dict[str, int]] = {}
    for table_name in sorted(set(source_counts) | set(target_counts)):
        source_count = int(source_counts.get(table_name, 0))
        target_count = int(target_counts.get(table_name, 0))
        if source_count != target_count:
            mismatches[table_name] = {"source": source_count, "target": target_count}
    return mismatches


def _default_source_url() -> str:
    return os.getenv("SQLALCHEMY_DATABASE_URL", "")


def _default_target_url() -> str:
    return (
        os.getenv("POSTGRES_ADMIN_DATABASE_URL")
        or os.getenv("POSTGRES_TARGET_DATABASE_URL")
        or ""
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate application data from one PostgreSQL database to another.")
    parser.add_argument(
        "--source-url",
        default=_default_source_url(),
        help="Source PostgreSQL URL (default: SQLALCHEMY_DATABASE_URL)",
    )
    parser.add_argument(
        "--target-url",
        default=_default_target_url(),
        help="Target PostgreSQL URL (default: POSTGRES_ADMIN_DATABASE_URL)",
    )
    parser.add_argument(
        "--dump-file",
        default="",
        help="Optional path to keep the generated SQL dump; otherwise a temporary file is used",
    )
    parser.add_argument(
        "--skip-verify-counts",
        action="store_true",
        help="Skip post-restore row count verification",
    )
    args = parser.parse_args()

    source_url = _ensure_postgres_url(args.source_url, "--source-url")
    target_url = _ensure_postgres_url(args.target_url, "--target-url")
    _ensure_required_tools()
    _assert_distinct_databases(source_url, target_url)

    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    if args.dump_file:
        dump_path = Path(args.dump_file).expanduser().resolve()
        dump_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        temp_dir = tempfile.TemporaryDirectory(prefix="lpu-pg-migrate-")
        dump_path = Path(temp_dir.name).resolve() / "postgres-transfer.sql"

    dump_cmd = [
        require_postgres_command("pg_dump"),
        "--dbname",
        _libpq_url(source_url),
        "--file",
        str(dump_path),
        "--format=plain",
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
    ]
    restore_cmd = [
        require_postgres_command("psql"),
        "--dbname",
        _libpq_url(target_url),
        "--set",
        "ON_ERROR_STOP=1",
        "--single-transaction",
        "--file",
        str(dump_path),
    ]

    _run(dump_cmd)
    _run(restore_cmd)

    summary: dict[str, object] = {
        "source": _sanitized_url(source_url),
        "target": _sanitized_url(target_url),
        "dump_file": str(dump_path),
        "verified_counts": not args.skip_verify_counts,
    }

    if not args.skip_verify_counts:
        source_engine = create_engine(source_url, pool_pre_ping=True)
        target_engine = create_engine(target_url, pool_pre_ping=True)
        source_counts = _count_rows(source_engine)
        target_counts = _count_rows(target_engine)
        mismatches = _compare_counts(source_counts, target_counts)
        summary["source_counts"] = source_counts
        summary["target_counts"] = target_counts
        summary["mismatches"] = mismatches
        summary["row_count_match"] = not mismatches
        if mismatches:
            print(json.dumps(summary, indent=2))
            return 1

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
