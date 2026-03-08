from __future__ import annotations

import os
import shutil
from pathlib import Path


def _candidate_bin_dirs() -> list[Path]:
    home = Path.home()
    return [
        Path("/opt/homebrew/opt/libpq/bin"),
        Path("/opt/homebrew/opt/postgresql@18/bin"),
        Path("/opt/homebrew/opt/postgresql@17/bin"),
        Path("/opt/homebrew/opt/postgresql@16/bin"),
        Path("/opt/homebrew/opt/postgresql@15/bin"),
        Path("/opt/homebrew/opt/postgresql@14/bin"),
        Path("/usr/local/opt/libpq/bin"),
        Path("/usr/local/opt/postgresql@18/bin"),
        Path("/usr/local/opt/postgresql@17/bin"),
        Path("/usr/local/opt/postgresql@16/bin"),
        Path("/usr/local/opt/postgresql@15/bin"),
        Path("/usr/local/opt/postgresql@14/bin"),
        Path("/Applications/Postgres.app/Contents/Versions/latest/bin"),
        home / "Applications/Postgres.app/Contents/Versions/latest/bin",
    ]


def find_postgres_command(name: str) -> str | None:
    direct = shutil.which(name)
    if direct:
        return direct
    for bin_dir in _candidate_bin_dirs():
        candidate = bin_dir / name
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def require_postgres_command(name: str) -> str:
    resolved = find_postgres_command(name)
    if resolved:
        return resolved
    raise RuntimeError(
        f"Unable to locate PostgreSQL tool '{name}'. Install PostgreSQL CLI tools or add them to PATH."
    )
