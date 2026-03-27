import os
from typing import Any

from fastapi import HTTPException, Request

from .redis_client import RateLimitDecision, rate_limit_hit


def _client_ip(request: Request) -> str:
    forwarded = (request.headers.get("x-forwarded-for") or "").strip()
    if forwarded:
        first = forwarded.split(",", 1)[0].strip()
        if first:
            return first
    real_ip = (request.headers.get("x-real-ip") or "").strip()
    if real_ip:
        return real_ip
    if request.client and request.client.host:
        return str(request.client.host)
    return "unknown"


def _default_limit() -> int:
    raw = (os.getenv("API_RATE_LIMIT_DEFAULT", "120") or "").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 120
    return max(10, min(5000, value))


def _default_window_seconds() -> int:
    raw = (os.getenv("API_RATE_LIMIT_WINDOW_SECONDS", "60") or "").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 60
    return max(10, min(3600, value))


def enforce_rate_limit(
    request: Request,
    *,
    scope: str,
    principal: str | None = None,
    limit: int | None = None,
    window_seconds: int | None = None,
    include_ip: bool = True,
) -> RateLimitDecision:
    effective_limit = int(limit or _default_limit())
    effective_window = int(window_seconds or _default_window_seconds())

    actor = (principal or "").strip().lower() or "anon"
    scope_token = (scope or "").strip().lower() or "default"
    if include_ip:
        key = f"{scope_token}:{_client_ip(request)}:{actor}"
    else:
        key = f"{scope_token}:{actor}"
    try:
        decision = rate_limit_hit(key, limit=effective_limit, window_seconds=effective_window)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Rate limiter unavailable for {scope}: {exc}",
        ) from exc
    if decision.allowed:
        return decision

    headers = rate_limit_headers(decision)
    headers["Retry-After"] = str(decision.retry_after_seconds)
    raise HTTPException(
        status_code=429,
        detail={
            "error": "rate_limit_exceeded",
            "scope": scope_token,
            "message": "Too many requests for this endpoint window.",
            "limit": decision.limit,
            "remaining": decision.remaining,
            "retry_after_seconds": decision.retry_after_seconds,
        },
        headers=headers,
    )


def rate_limit_headers(decision: RateLimitDecision, *, prefix: str = "X-RateLimit") -> dict[str, Any]:
    root = (prefix or "X-RateLimit").strip()
    return {
        f"{root}-Limit": str(decision.limit),
        f"{root}-Remaining": str(decision.remaining),
        f"{root}-Reset": str(decision.retry_after_seconds),
    }
