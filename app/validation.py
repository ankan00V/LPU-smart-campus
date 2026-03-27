from __future__ import annotations

import os
import re
from enum import Enum as PyEnum
from typing import Any

from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict, field_validator

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
_BODY_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _int_env(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = (os.getenv(name, str(default)) or "").strip()
    try:
        value = int(raw)
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def sanitize_text(value: str) -> str:
    cleaned = value.strip()
    if _CONTROL_CHAR_RE.search(cleaned):
        raise ValueError("Control characters are not allowed.")
    return cleaned


def sanitize_nested(value: Any) -> Any:
    # Preserve enum instances so model validators still receive canonical enum values.
    if isinstance(value, PyEnum):
        return value
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [sanitize_nested(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize_nested(item) for item in value)
    if isinstance(value, dict):
        sanitized: dict[Any, Any] = {}
        for key, item in value.items():
            next_key = sanitize_text(key) if isinstance(key, str) else key
            sanitized[next_key] = sanitize_nested(item)
        return sanitized
    return value


class StrictSchemaModel(BaseModel):
    # Reject unknown fields and normalize string whitespace for request hardening.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("*", mode="before")
    @classmethod
    def _sanitize_fields(cls, value: Any) -> Any:
        return sanitize_nested(value)


def validate_request_security_constraints(request: Request) -> None:
    max_path_length = _int_env("API_MAX_PATH_LENGTH", 1024, minimum=64, maximum=4096)
    max_query_key_length = _int_env("API_MAX_QUERY_KEY_LENGTH", 80, minimum=10, maximum=300)
    max_query_value_length = _int_env("API_MAX_QUERY_VALUE_LENGTH", 400, minimum=20, maximum=4000)
    max_body_bytes = _int_env("API_MAX_BODY_BYTES", 8 * 1024 * 1024, minimum=32_768, maximum=50 * 1024 * 1024)

    try:
        path = sanitize_text(request.url.path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Request path contains invalid control characters.") from exc
    if len(path) > max_path_length:
        raise HTTPException(status_code=414, detail="Request path is too long.")

    for key, value in request.query_params.multi_items():
        try:
            clean_key = sanitize_text(key)
            clean_value = sanitize_text(value)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"Query parameter '{str(key)[:40]}' contains invalid control characters.") from exc
        if len(clean_key) > max_query_key_length:
            raise HTTPException(status_code=422, detail=f"Query parameter name '{clean_key[:40]}' is too long.")
        if len(clean_value) > max_query_value_length:
            raise HTTPException(status_code=422, detail=f"Query parameter '{clean_key}' is too long.")

    if request.method.upper() not in _BODY_METHODS:
        return
    content_length_raw = (request.headers.get("content-length") or "").strip()
    if not content_length_raw:
        return
    try:
        content_length = int(content_length_raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid Content-Length header.") from exc
    if content_length < 0:
        raise HTTPException(status_code=400, detail="Invalid Content-Length header.")
    if content_length > max_body_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Request body too large. Maximum allowed is {max_body_bytes} bytes.",
        )
