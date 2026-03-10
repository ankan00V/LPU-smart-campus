from __future__ import annotations

import os
import re
import shutil
import subprocess
from functools import lru_cache
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


def _major_from_version_output(raw: str) -> int | None:
    match = re.search(r"(\d+)(?:\.\d+)?", str(raw or ""))
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


@lru_cache(maxsize=64)
def _command_major_version(command: str) -> int | None:
    try:
        result = subprocess.run(
            [command, "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return None
    output = (result.stdout or result.stderr or "").strip()
    return _major_from_version_output(output)


def _candidate_commands(name: str) -> list[str]:
    commands: list[str] = []
    direct = shutil.which(name)
    if direct:
        commands.append(direct)
    for bin_dir in _candidate_bin_dirs():
        candidate = bin_dir / name
        if candidate.exists() and os.access(candidate, os.X_OK):
            commands.append(str(candidate))
    unique: list[str] = []
    seen: set[str] = set()
    for command in commands:
        resolved = str(Path(command).resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(resolved)
    return unique


def _preferred_command(
    commands: list[str],
    preferred_major: int | None,
    *,
    allow_version_fallback: bool,
) -> str | None:
    if not commands:
        return None
    if preferred_major is None:
        return commands[0]
    exact_matches = [command for command in commands if _command_major_version(command) == preferred_major]
    if exact_matches:
        return exact_matches[0]
    if not allow_version_fallback:
        return None
    return commands[0]


def _version_num_to_major(version_num: int) -> int | None:
    if version_num <= 0:
        return None
    if version_num >= 100000:
        return version_num // 10000
    return version_num // 10000


@lru_cache(maxsize=16)
def postgres_server_major_version(database_url: str | None) -> int | None:
    raw_url = str(database_url or "").strip()
    if not raw_url or not raw_url.startswith("postgresql"):
        return None
    try:
        from .database import postgres_libpq_url
        import psycopg
    except Exception:
        return None
    libpq_url = str(postgres_libpq_url(raw_url) or raw_url)
    try:
        with psycopg.connect(libpq_url, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SHOW server_version_num")
                row = cur.fetchone()
    except Exception:
        return None
    if not row:
        return None
    try:
        version_num = int(row[0])
    except Exception:
        return None
    return _version_num_to_major(version_num)


def find_postgres_command(
    name: str,
    *,
    preferred_major: int | None = None,
    allow_version_fallback: bool = True,
) -> str | None:
    return _preferred_command(
        _candidate_commands(name),
        preferred_major,
        allow_version_fallback=allow_version_fallback,
    )


def require_postgres_command(
    name: str,
    *,
    preferred_major: int | None = None,
    allow_version_fallback: bool = True,
) -> str:
    resolved = find_postgres_command(
        name,
        preferred_major=preferred_major,
        allow_version_fallback=allow_version_fallback,
    )
    if resolved:
        return resolved
    version_hint = f" for PostgreSQL {preferred_major}" if preferred_major is not None else ""
    raise RuntimeError(
        f"Unable to locate PostgreSQL tool '{name}'{version_hint}. "
        "Install PostgreSQL CLI tools or add them to PATH."
    )
