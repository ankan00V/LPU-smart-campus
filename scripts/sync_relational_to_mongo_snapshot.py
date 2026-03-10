#!/usr/bin/env python3
"""Backfill the Mongo read model from the active relational database."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from app.database import SessionLocal, database_status  # noqa: E402
from app.main import sync_sql_snapshot_to_mongo  # noqa: E402
from app.mongo import mongo_status  # noqa: E402


def main() -> int:
    db_state = database_status()
    if str(db_state.get("backend") or "").strip().lower() != "postgresql" or not bool(db_state.get("connected")):
        raise SystemExit("Active relational backend must be a live PostgreSQL connection before Mongo snapshot sync.")

    session = SessionLocal()
    try:
        sync_sql_snapshot_to_mongo(session)
        result = {
            "database": db_state,
            "mongo": mongo_status(),
            "status": "ok",
        }
        print(json.dumps(result, indent=2, default=str))
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
