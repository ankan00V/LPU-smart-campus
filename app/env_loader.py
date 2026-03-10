from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values


PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_LOADED = False


def _resolve_env_name(base_values: dict[str, str | None]) -> str:
    raw = os.getenv("APP_ENV") or base_values.get("APP_ENV") or "development"
    return str(raw).strip().lower() or "development"


def _overlay_paths(project_root: Path, env_name: str) -> list[Path]:
    if env_name in {"prod", "production"}:
        return [project_root / ".env.production"]
    return [project_root / ".env.local"]


def _dotenv_should_override_process_env(env_name: str) -> bool:
    raw = os.getenv("APP_DOTENV_OVERRIDE")
    if raw is not None:
        return str(raw).strip().lower() in {"1", "true", "yes", "on"}
    return env_name not in {"prod", "production"}


def load_app_env(*, force: bool = False, project_root: Path | None = None) -> None:
    global _ENV_LOADED
    if _ENV_LOADED and not force:
        return

    root = Path(project_root or PROJECT_ROOT).resolve()
    base_values = {
        str(key): value
        for key, value in dotenv_values(root / ".env").items()
        if key is not None
    }
    merged_values = dict(base_values)
    for overlay_path in _overlay_paths(root, _resolve_env_name(base_values)):
        if not overlay_path.exists():
            continue
        merged_values.update(
            {
                str(key): value
                for key, value in dotenv_values(overlay_path).items()
                if key is not None
            }
        )

    env_name = _resolve_env_name(base_values)
    explicit_env_keys = set(os.environ)
    override_process_env = _dotenv_should_override_process_env(env_name)
    for key, value in merged_values.items():
        if value is None:
            continue
        if key in explicit_env_keys and not override_process_env:
            continue
        os.environ[key] = value

    _ENV_LOADED = True
