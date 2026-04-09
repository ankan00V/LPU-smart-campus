import json
import socket
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from app import runtime_infra


class RuntimeDnsFallbackTests(unittest.TestCase):
    def setUp(self):
        self._env_backup = dict(runtime_infra.os.environ)

    def tearDown(self):
        runtime_infra.os.environ.clear()
        runtime_infra.os.environ.update(self._env_backup)

    def test_resolve_service_hostaddr_uses_public_nameserver_fallback(self):
        runtime_infra.os.environ["APP_MANAGED_SERVICES_REQUIRED"] = "true"
        runtime_infra.os.environ["SERVICE_DNS_NAMESERVERS"] = "1.1.1.1"
        runtime_infra.os.environ["SERVICE_DNS_TIMEOUT_SECONDS"] = "1"
        nslookup_output = """
Server:         1.1.1.1
Address:        1.1.1.1#53

Non-authoritative answer:
db.example.com  canonical name = db.public.example.com.
Name:   db.public.example.com
Address: 34.120.55.1
"""
        with patch.object(runtime_infra, "dns_resolver", None):
            with patch.object(
                runtime_infra.subprocess,
                "run",
                return_value=subprocess.CompletedProcess(
                    args=["nslookup", "db.example.com", "1.1.1.1"],
                    returncode=0,
                    stdout=nslookup_output,
                    stderr="",
                ),
            ):
                self.assertEqual(runtime_infra.resolve_service_hostaddr("db.example.com"), "34.120.55.1")

    def test_fallback_getaddrinfo_returns_ipv4_records_after_system_dns_failure(self):
        runtime_infra.os.environ["APP_MANAGED_SERVICES_REQUIRED"] = "true"

        def _original_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
            if host == "db.example.com":
                raise socket.gaierror(8, "nodename nor servname provided, or not known")
            return [
                (
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                    6,
                    "",
                    (host, port),
                )
            ]

        with patch.object(runtime_infra, "resolve_service_hostaddrs", return_value=["34.120.55.1"]):
            result = runtime_infra._fallback_getaddrinfo(
                _original_getaddrinfo,
                "db.example.com",
                5432,
                socket.AF_UNSPEC,
                socket.SOCK_STREAM,
                0,
                0,
            )

        self.assertEqual(result[0][4][0], "34.120.55.1")

    def test_fallback_getaddrinfo_prefers_ipv4_results_when_available(self):
        runtime_infra.os.environ["APP_MANAGED_SERVICES_REQUIRED"] = "true"
        runtime_infra.os.environ["SERVICE_PREFER_IPV4"] = "true"

        def _original_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
            return [
                (
                    socket.AF_INET6,
                    socket.SOCK_STREAM,
                    6,
                    "",
                    (host, port, 0, 0),
                ),
                (
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                    6,
                    "",
                    ("34.120.55.1", port),
                ),
            ]

        result = runtime_infra._fallback_getaddrinfo(
            _original_getaddrinfo,
            "smtp.gmail.com",
            587,
            socket.AF_UNSPEC,
            socket.SOCK_STREAM,
            0,
            0,
        )

        self.assertEqual(result[0][0], socket.AF_INET)

    def test_fallback_getaddrinfo_uses_dns_ipv4_fallback_when_only_ipv6_results_exist(self):
        runtime_infra.os.environ["APP_MANAGED_SERVICES_REQUIRED"] = "true"
        runtime_infra.os.environ["SERVICE_PREFER_IPV4"] = "true"

        def _original_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
            if host == "smtp.gmail.com":
                return [
                    (
                        socket.AF_INET6,
                        socket.SOCK_STREAM,
                        6,
                        "",
                        (host, port, 0, 0),
                    )
                ]
            if host == "74.125.200.109":
                return [
                    (
                        socket.AF_INET,
                        socket.SOCK_STREAM,
                        6,
                        "",
                        ("74.125.200.109", port),
                    )
                ]
            raise socket.gaierror(8, "nodename nor servname provided, or not known")

        with patch.object(runtime_infra, "resolve_service_hostaddrs", return_value=["74.125.200.109"]):
            result = runtime_infra._fallback_getaddrinfo(
                _original_getaddrinfo,
                "smtp.gmail.com",
                587,
                socket.AF_UNSPEC,
                socket.SOCK_STREAM,
                0,
                0,
            )

        self.assertEqual(result[0][0], socket.AF_INET)
        self.assertEqual(result[0][4][0], "74.125.200.109")

    def test_resolve_service_hostaddr_uses_static_map_file(self):
        runtime_infra.os.environ["APP_MANAGED_SERVICES_REQUIRED"] = "true"
        with tempfile.NamedTemporaryFile("w+", suffix=".json") as handle:
            json.dump({"db.example.com": ["34.120.55.1"]}, handle)
            handle.flush()
            runtime_infra.os.environ["SERVICE_DNS_STATIC_MAP_FILE"] = handle.name
            self.assertEqual(runtime_infra.resolve_service_hostaddr("db.example.com"), "34.120.55.1")
