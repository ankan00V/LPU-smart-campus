from __future__ import annotations

import ipaddress
import os
from urllib.parse import SplitResult, urlsplit


_LOCAL_HOST_ALIASES = {
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "host.docker.internal",
}


def bool_env(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name, "true" if default else "false") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def app_env() -> str:
    return (os.getenv("APP_ENV") or "development").strip().lower() or "development"


def managed_services_required() -> bool:
    raw = (os.getenv("APP_MANAGED_SERVICES_REQUIRED") or "").strip()
    if raw:
        return raw.lower() in {"1", "true", "yes", "on"}
    return app_env() in {"prod", "production"}


def normalize_host(host: str | None) -> str | None:
    raw = str(host or "").strip().strip("[]").rstrip(".").lower()
    return raw or None


def is_loopback_host(host: str | None) -> bool:
    normalized = normalize_host(host)
    if not normalized:
        return False
    if normalized in _LOCAL_HOST_ALIASES:
        return True
    try:
        ip = ipaddress.ip_address(normalized)
    except ValueError:
        return False
    return ip.is_loopback or ip.is_unspecified


def is_remote_service_host(host: str | None) -> bool:
    normalized = normalize_host(host)
    return bool(normalized) and not is_loopback_host(normalized)


def split_url(value: str) -> SplitResult:
    return urlsplit((value or "").strip())
