#!/usr/bin/env python3
"""Copy relational app data from SQLite into PostgreSQL."""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy import MetaData, Table, create_engine, inspect, select, text
from sqlalchemy.engine import make_url

from app import models  # noqa: F401
from app.database import Base

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _normalized_sqlite_url(raw: str) -> str:
    value = str(raw or "").strip() or "sqlite:///./campus.db"
    if value.startswith("sqlite:///./"):
        suffix = value[len("sqlite:///./") :]
        return f"sqlite:///{(PROJECT_ROOT / suffix).resolve()}"
    if value.startswith("sqlite:///") and not value.startswith("sqlite:////"):
        suffix = value[len("sqlite:///") :]
        if suffix and not suffix.startswith("/"):
            return f"sqlite:///{(PROJECT_ROOT / suffix).resolve()}"
    return value


def _sqlite_file_from_url(url: str) -> Path | None:
    if not url.startswith("sqlite:///") or url.startswith("sqlite:///:memory:"):
        return None
    raw = url[len("sqlite:///") :]
    path = Path(raw)
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    return path


def _normalized_postgres_url(raw: str) -> str:
    value = str(raw or "").strip()
    if value.startswith("postgres://"):
        return f"postgresql+psycopg://{value[len('postgres://'):]}"
    if value.startswith("postgresql://") and not value.startswith("postgresql+"):
        return f"postgresql+psycopg://{value[len('postgresql://'):]}"
    return value


def _table_names_in_source(engine) -> set[str]:
    inspector = inspect(engine)
    return set(inspector.get_table_names())


def _truncate_target_tables(connection) -> None:
    for table in reversed(Base.metadata.sorted_tables):
        connection.execute(text(f'TRUNCATE TABLE "{table.name}" RESTART IDENTITY CASCADE'))


def _nullable_foreign_key_sets(source_engine, source_tables: set[str], table) -> dict[str, set[Any]]:
    reference_sets: dict[str, set[Any]] = {}
    source_metadata = MetaData()
    for column in table.columns:
        if not column.nullable or len(column.foreign_keys) != 1:
            continue
        foreign_key = next(iter(column.foreign_keys))
        referred_column = foreign_key.column
        referred_table = referred_column.table.name
        if referred_table not in source_tables:
            continue
        source_reference_table = Table(referred_table, source_metadata, autoload_with=source_engine)
        with source_engine.connect() as source_connection:
            values = source_connection.execute(select(source_reference_table.c[referred_column.name])).scalars().all()
        reference_sets[column.name] = set(values)
    return reference_sets


def _copy_table_rows(source_engine, target_connection, table, batch_size: int, source_tables: set[str]) -> tuple[int, dict[str, int]]:
    copied = 0
    repaired_columns: dict[str, int] = defaultdict(int)
    source_table = Table(table.name, MetaData(), autoload_with=source_engine)
    target_columns = {column.name for column in table.columns}
    nullable_fk_sets = _nullable_foreign_key_sets(source_engine, source_tables, table)
    with source_engine.connect() as source_connection:
        result = source_connection.execution_options(stream_results=True).execute(select(source_table))
        while True:
            batch = result.mappings().fetchmany(batch_size)
            if not batch:
                break
            rows = []
            for row in batch:
                normalized = {key: value for key, value in dict(row).items() if key in target_columns}
                for column_name, valid_values in nullable_fk_sets.items():
                    value = normalized.get(column_name)
                    if value is not None and value not in valid_values:
                        normalized[column_name] = None
                        repaired_columns[column_name] += 1
                rows.append(normalized)
            if rows:
                target_connection.execute(table.insert(), rows)
                copied += len(rows)
    return copied, dict(repaired_columns)


def _reset_postgres_sequences(connection) -> None:
    for table in Base.metadata.sorted_tables:
        primary_keys = list(table.primary_key.columns)
        if len(primary_keys) != 1:
            continue
        column = primary_keys[0]
        try:
            python_type = column.type.python_type
        except Exception:  # noqa: BLE001
            python_type = None
        if python_type not in {int}:
            continue
        connection.execute(
            text(
                f"""
                SELECT setval(
                    pg_get_serial_sequence('"{table.name}"', '{column.name}'),
                    COALESCE((SELECT MAX("{column.name}") FROM "{table.name}"), 1),
                    EXISTS (SELECT 1 FROM "{table.name}")
                )
                """
            )
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate app data from SQLite to PostgreSQL.")
    parser.add_argument(
        "--sqlite-url",
        default=os.getenv("SQLITE_SOURCE_DATABASE_URL", "sqlite:///./campus.db"),
        help="Source SQLite URL (default: sqlite:///./campus.db)",
    )
    parser.add_argument(
        "--postgres-url",
        default=(
            os.getenv("POSTGRES_ADMIN_DATABASE_URL")
            or os.getenv("POSTGRES_TARGET_DATABASE_URL")
            or os.getenv("SQLALCHEMY_DATABASE_URL", "")
        ),
        help="Target PostgreSQL URL (default: SQLALCHEMY_DATABASE_URL)",
    )
    parser.add_argument("--batch-size", type=int, default=500, help="Rows per insert batch")
    parser.add_argument(
        "--truncate-first",
        action="store_true",
        help="Truncate target tables before copy",
    )
    args = parser.parse_args()

    sqlite_url = _normalized_sqlite_url(args.sqlite_url)
    postgres_url = _normalized_postgres_url(args.postgres_url)
    if not sqlite_url.startswith("sqlite"):
        raise SystemExit("--sqlite-url must be a SQLite SQLAlchemy URL")
    if not postgres_url.startswith("postgresql"):
        raise SystemExit("--postgres-url must be a PostgreSQL SQLAlchemy URL")
    sqlite_file = _sqlite_file_from_url(sqlite_url)
    if sqlite_file is not None and not sqlite_file.exists():
        raise SystemExit(f"SQLite source file not found: {sqlite_file}")

    source_engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    target_engine = create_engine(postgres_url, pool_pre_ping=True)

    Base.metadata.create_all(bind=target_engine)
    source_tables = _table_names_in_source(source_engine)

    copied_summary: dict[str, int] = {}
    repaired_summary: dict[str, dict[str, int]] = {}
    with target_engine.begin() as target_connection:
        if args.truncate_first:
            _truncate_target_tables(target_connection)

        for table in Base.metadata.sorted_tables:
            if table.name not in source_tables:
                copied_summary[table.name] = 0
                continue
            copied_rows, repaired_columns = _copy_table_rows(
                source_engine,
                target_connection,
                table,
                max(1, int(args.batch_size)),
                source_tables,
            )
            copied_summary[table.name] = copied_rows
            if repaired_columns:
                repaired_summary[table.name] = repaired_columns

        _reset_postgres_sequences(target_connection)

    print(
        json.dumps(
            {
                "source": sqlite_url,
                "target": make_url(postgres_url).render_as_string(hide_password=True),
                "tables_copied": copied_summary,
                "repaired_nullable_foreign_keys": repaired_summary,
                "total_rows": int(sum(copied_summary.values())),
                "truncated_first": bool(args.truncate_first),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
