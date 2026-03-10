from __future__ import annotations

import base64
import hashlib
import json
import subprocess
from datetime import date, datetime, time, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import inspect, text

from .database import engine
from .postgres_tools import find_postgres_command, postgres_server_major_version


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc).isoformat()
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, (date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return {"encoding": "base64", "value": base64.b64encode(value).decode("ascii")}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(val) for key, val in value.items()}
    return str(value)


def _quote_ident(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def _qualified_table_name(schema: str | None, table_name: str) -> str:
    if schema:
        return f"{_quote_ident(schema)}.{_quote_ident(table_name)}"
    return _quote_ident(table_name)


def _portable_snapshot_artifact(destination: Path) -> dict[str, Any]:
    snapshot_path = destination / "postgres.portable.json"
    inspector = inspect(engine)
    schemas = [schema for schema in inspector.get_schema_names() if schema not in {"pg_catalog", "information_schema"}]
    tables: list[dict[str, Any]] = []
    total_rows = 0
    with engine.connect() as conn:
        for schema in schemas:
            for table_name in inspector.get_table_names(schema=schema):
                rows = [
                    {str(key): _jsonable(value) for key, value in row._mapping.items()}
                    for row in conn.execute(text(f"SELECT * FROM {_qualified_table_name(schema, table_name)}"))
                ]
                total_rows += len(rows)
                tables.append(
                    {
                        "schema": schema,
                        "name": table_name,
                        "columns": [
                            {
                                "name": str(column.get("name") or ""),
                                "type": str(column.get("type") or ""),
                                "nullable": bool(column.get("nullable", True)),
                                "default": _jsonable(column.get("default")),
                            }
                            for column in inspector.get_columns(table_name, schema=schema)
                        ],
                        "primary_key": list((inspector.get_pk_constraint(table_name, schema=schema) or {}).get("constrained_columns") or []),
                        "foreign_keys": _jsonable(inspector.get_foreign_keys(table_name, schema=schema) or []),
                        "indexes": _jsonable(inspector.get_indexes(table_name, schema=schema) or []),
                        "row_count": len(rows),
                        "rows": rows,
                    }
                )
    payload = {
        "format": "portable-postgresql-snapshot",
        "generated_at": _utc_now().isoformat(),
        "table_count": len(tables),
        "total_row_count": int(total_rows),
        "tables": tables,
    }
    snapshot_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {
        "backend": "postgresql",
        "format": "portable_snapshot",
        "path": str(snapshot_path),
        "size_bytes": snapshot_path.stat().st_size,
        "sha256": hashlib.sha256(snapshot_path.read_bytes()).hexdigest(),
        "table_count": len(tables),
        "total_row_count": int(total_rows),
    }


def create_postgresql_backup_artifact(destination: Path, dump_url: str) -> dict[str, Any]:
    preferred_major = postgres_server_major_version(dump_url)
    pg_dump = find_postgres_command("pg_dump", preferred_major=preferred_major, allow_version_fallback=False)
    if pg_dump:
        dump_path = destination / "postgres.sql"
        try:
            subprocess.run(
                [
                    pg_dump,
                    "--dbname",
                    dump_url,
                    "--file",
                    str(dump_path),
                    "--format=plain",
                    "--no-owner",
                    "--no-privileges",
                ],
                check=True,
            )
            return {
                "backend": "postgresql",
                "format": "plain_sql_dump",
                "path": str(dump_path),
                "size_bytes": dump_path.stat().st_size,
                "sha256": hashlib.sha256(dump_path.read_bytes()).hexdigest(),
            }
        except subprocess.CalledProcessError:
            pass
    return _portable_snapshot_artifact(destination)


def validate_postgresql_backup_artifact(backup_path: Path) -> dict[str, Any]:
    postgres_dumps = [p for p in backup_path.glob("*.sql")]
    if postgres_dumps:
        dump_path = postgres_dumps[0]
        content = dump_path.read_text(encoding="utf-8", errors="ignore")
        has_header = "PostgreSQL database dump" in content[:4096]
        has_schema = "CREATE TABLE" in content or "COPY " in content or "INSERT INTO" in content
        return {
            "backend": "postgresql",
            "format": "plain_sql_dump",
            "restored": False,
            "validated": bool(has_header and has_schema and dump_path.stat().st_size > 0),
            "size_bytes": dump_path.stat().st_size,
            "has_header": has_header,
            "has_schema_statements": has_schema,
        }

    portable_snapshots = [p for p in backup_path.glob("*.portable.json")]
    if portable_snapshots:
        snapshot_path = portable_snapshots[0]
        try:
            payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        tables = payload.get("tables")
        valid_tables = isinstance(tables, list) and any(
            isinstance(table, dict) and table.get("name") and isinstance(table.get("columns"), list)
            for table in tables
        )
        return {
            "backend": "postgresql",
            "format": "portable_snapshot",
            "restored": False,
            "validated": bool(
                payload.get("format") == "portable-postgresql-snapshot"
                and valid_tables
                and snapshot_path.stat().st_size > 0
            ),
            "size_bytes": snapshot_path.stat().st_size,
            "table_count": int(payload.get("table_count") or 0),
            "total_row_count": int(payload.get("total_row_count") or 0),
        }

    return {"backend": "unknown", "restored": False, "validated": False}
