from __future__ import annotations

import ipaddress
import json
import os
import re
import socket
import subprocess
import threading
from pathlib import Path
from urllib.parse import SplitResult, urlsplit

try:
    import dns.resolver as dns_resolver
except Exception:  # noqa: BLE001
    dns_resolver = None


_LOCAL_HOST_ALIASES = {
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "host.docker.internal",
}
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ORIGINAL_SOCKET_GETADDRINFO = socket.getaddrinfo
_SOCKET_DNS_FALLBACK_LOCK = threading.Lock()
_SOCKET_DNS_FALLBACK_INSTALLED = False
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


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


def _service_dns_fallback_enabled() -> bool:
    raw = (os.getenv("SERVICE_DNS_FALLBACK_ENABLED") or "").strip().lower()
    if raw:
        return raw in {"1", "true", "yes", "on"}
    return managed_services_required()


def _service_dns_nameservers() -> list[str]:
    raw = (os.getenv("SERVICE_DNS_NAMESERVERS") or os.getenv("MONGO_DNS_NAMESERVERS") or "1.1.1.1,8.8.8.8").strip()
    return [token.strip() for token in raw.split(",") if token.strip()]


def _service_dns_timeout_seconds() -> float:
    raw = (os.getenv("SERVICE_DNS_TIMEOUT_SECONDS") or "5").strip()
    try:
        value = float(raw)
    except ValueError:
        value = 5.0
    return max(1.0, min(15.0, value))


def _service_dns_static_map_path() -> Path:
    raw = (os.getenv("SERVICE_DNS_STATIC_MAP_FILE") or ".runtime/service_dns_static_map.json").strip()
    path = Path(raw)
    if not path.is_absolute():
        path = (_PROJECT_ROOT / path).resolve()
    return path


def _service_dns_static_map() -> dict[str, list[str]]:
    path = _service_dns_static_map_path()
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text())
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    parsed: dict[str, list[str]] = {}
    for raw_host, raw_values in payload.items():
        host = normalize_host(str(raw_host or ""))
        if not host:
            continue
        values = raw_values if isinstance(raw_values, list) else [raw_values]
        addresses: list[str] = []
        for candidate in values:
            _append_unique_ip(addresses, str(candidate or ""))
        if addresses:
            parsed[host] = addresses
    return parsed


def _service_dns_resolver():
    if dns_resolver is None:
        return None
    resolver = dns_resolver.Resolver(configure=False)
    nameservers = _service_dns_nameservers()
    if nameservers:
        resolver.nameservers = nameservers
    timeout = _service_dns_timeout_seconds()
    resolver.timeout = timeout
    resolver.lifetime = timeout
    return resolver


def _append_unique_ip(target: list[str], candidate: str) -> None:
    value = str(candidate or "").strip()
    if not value:
        return
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return
    if ip.version != 4:
        return
    if value not in target:
        target.append(value)


def resolve_service_hostaddrs(host: str | None) -> list[str]:
    normalized = normalize_host(host)
    if not is_remote_service_host(normalized):
        return []
    static_map = _service_dns_static_map()
    if normalized in static_map:
        return list(static_map[normalized])
    if not _service_dns_fallback_enabled():
        return []

    addresses: list[str] = []
    resolver = _service_dns_resolver()
    if resolver is not None:
        try:
            records = resolver.resolve(normalized, "A")
            for record in records:
                _append_unique_ip(addresses, str(record).strip())
        except Exception:
            pass
    if addresses:
        return addresses

    timeout = _service_dns_timeout_seconds()
    for nameserver in _service_dns_nameservers():
        try:
            completed = subprocess.run(
                ["nslookup", normalized, nameserver],
                capture_output=True,
                check=False,
                text=True,
                timeout=timeout,
            )
        except Exception:
            continue
        if completed.returncode != 0:
            continue
        seen_answer_block = False
        for line in (completed.stdout or "").splitlines():
            stripped = line.strip()
            lower = stripped.lower()
            if lower.startswith("name:") or "non-authoritative answer" in lower:
                seen_answer_block = True
            if not seen_answer_block:
                continue
            for match in _IPV4_RE.findall(stripped):
                _append_unique_ip(addresses, match)
        if addresses:
            return addresses
    return addresses


def resolve_service_hostaddr(host: str | None) -> str | None:
    addresses = resolve_service_hostaddrs(host)
    return addresses[0] if addresses else None


def _fallback_getaddrinfo(
    original_getaddrinfo,
    host,
    port,
    family=0,
    type=0,
    proto=0,
    flags=0,
):
    try:
        return original_getaddrinfo(host, port, family, type, proto, flags)
    except socket.gaierror:
        if family == socket.AF_INET6:
            raise
        fallback_addrs = resolve_service_hostaddrs(str(host or ""))
        if not fallback_addrs:
            raise
        resolved: list[tuple] = []
        target_family = socket.AF_INET if family in {0, socket.AF_UNSPEC, socket.AF_INET} else family
        for address in fallback_addrs:
            try:
                resolved.extend(
                    original_getaddrinfo(address, port, target_family, type, proto, flags)
                )
            except socket.gaierror:
                continue
        if resolved:
            return resolved
        raise


def install_socket_dns_fallback() -> None:
    global _SOCKET_DNS_FALLBACK_INSTALLED

    if not _service_dns_fallback_enabled():
        return
    with _SOCKET_DNS_FALLBACK_LOCK:
        if _SOCKET_DNS_FALLBACK_INSTALLED:
            return
        socket.getaddrinfo = lambda host, port, family=0, type=0, proto=0, flags=0: _fallback_getaddrinfo(  # type: ignore[assignment]
            _ORIGINAL_SOCKET_GETADDRINFO,
            host,
            port,
            family,
            type,
            proto,
            flags,
        )
        _SOCKET_DNS_FALLBACK_INSTALLED = True
