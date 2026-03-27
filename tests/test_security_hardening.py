import os
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.rate_limit import enforce_rate_limit
from app.redis_client import RateLimitDecision, rate_limit_hit
from app.validation import validate_request_security_constraints


def _request(*, path: str = "/", method: str = "GET", query: bytes = b"", headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": headers or [],
        "client": ("127.0.0.1", 9000),
        "query_string": query,
    }
    return Request(scope)


def test_enforce_rate_limit_uses_user_scope_without_ip_when_requested():
    captured: dict[str, str] = {}

    def _fake_rate_limit_hit(key: str, *, limit: int, window_seconds: int) -> RateLimitDecision:
        captured["key"] = key
        return RateLimitDecision(allowed=True, limit=limit, used=1, remaining=max(0, limit - 1), retry_after_seconds=window_seconds)

    with patch("app.rate_limit.rate_limit_hit", side_effect=_fake_rate_limit_hit):
        decision = enforce_rate_limit(
            _request(path="/any"),
            scope="public-user",
            principal="user:42",
            limit=10,
            window_seconds=60,
            include_ip=False,
        )

    assert decision.allowed is True
    assert captured["key"] == "public-user:user:42"


def test_enforce_rate_limit_returns_graceful_429_payload():
    with patch(
        "app.rate_limit.rate_limit_hit",
        return_value=RateLimitDecision(
            allowed=False,
            limit=3,
            used=4,
            remaining=0,
            retry_after_seconds=12,
        ),
    ):
        with pytest.raises(HTTPException) as ctx:
            enforce_rate_limit(
                _request(path="/limited"),
                scope="public-ip",
                principal="ip",
                limit=3,
                window_seconds=60,
            )
    exc = ctx.value
    assert exc.status_code == 429
    assert isinstance(exc.detail, dict)
    assert exc.detail.get("error") == "rate_limit_exceeded"
    assert exc.headers is not None
    assert exc.headers.get("Retry-After") == "12"
    assert exc.headers.get("X-RateLimit-Limit") == "3"


def test_request_validation_rejects_query_control_characters():
    request = _request(path="/resources/overview", query=b"section=%00bad")
    with pytest.raises(HTTPException) as ctx:
        validate_request_security_constraints(request)
    assert ctx.value.status_code == 422


def test_request_validation_rejects_body_overflow_limit():
    os.environ["API_MAX_BODY_BYTES"] = "32768"
    request = _request(
        path="/auth/register",
        method="POST",
        headers=[(b"content-length", b"65536")],
    )
    try:
        with pytest.raises(HTTPException) as ctx:
            validate_request_security_constraints(request)
        assert ctx.value.status_code == 413
    finally:
        os.environ.pop("API_MAX_BODY_BYTES", None)


def test_rate_limit_hit_uses_local_fallback_without_redis():
    os.environ["API_RATE_LIMIT_ALLOW_LOCAL_FALLBACK"] = "true"
    try:
        with patch("app.redis_client._redis_required", return_value=False), patch("app.redis_client.get_redis", return_value=None):
            first = rate_limit_hit("local-fallback-key", limit=2, window_seconds=60)
            second = rate_limit_hit("local-fallback-key", limit=2, window_seconds=60)
            third = rate_limit_hit("local-fallback-key", limit=2, window_seconds=60)
    finally:
        os.environ.pop("API_RATE_LIMIT_ALLOW_LOCAL_FALLBACK", None)

    assert first.allowed is True
    assert second.allowed is True
    assert third.allowed is False
