#!/usr/bin/env python3
import argparse
import json
import time
import urllib.error
import urllib.request


def _fetch_json(url: str, timeout: float = 3.0) -> tuple[int, dict]:
    req = urllib.request.Request(url=url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            body = json.loads(raw) if raw else {}
            if not isinstance(body, dict):
                body = {"raw": body}
            return int(resp.getcode()), body
    except urllib.error.HTTPError as exc:
        return int(exc.code), {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return 0, {"error": str(exc)}


def _fetch_status(url: str, timeout: float = 3.0) -> int:
    req = urllib.request.Request(url=url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(resp.getcode())
    except urllib.error.HTTPError as exc:
        return int(exc.code)
    except Exception:
        return 0


def _evaluate_root_payload(payload: dict) -> list[str]:
    failures: list[str] = []
    if payload.get("runtime_strict") is not True:
        failures.append("runtime_strict is not true")
    managed_services_required = payload.get("managed_services_required") is True
    database = payload.get("database", {})
    if database.get("connected") is not True:
        failures.append("database.connected is not true")
    if database.get("backend") != "postgresql":
        failures.append(f"database.backend is not postgresql (got {database.get('backend')!r})")
    if managed_services_required:
        if database.get("remote_host") is not True:
            failures.append("database.remote_host is not true")
        if database.get("tls_enabled") is not True:
            failures.append("database.tls_enabled is not true")
    if payload.get("mongo", {}).get("enabled") is not True:
        failures.append("mongo.enabled is not true")
    if managed_services_required:
        mongo = payload.get("mongo", {})
        if mongo.get("remote_host") is not True:
            failures.append("mongo.remote_host is not true")
        if mongo.get("tls_enabled") is not True:
            failures.append("mongo.tls_enabled is not true")
    if payload.get("redis", {}).get("enabled") is not True:
        failures.append("redis.enabled is not true")
    if managed_services_required:
        redis = payload.get("redis", {})
        if redis.get("remote_host") is not True:
            failures.append("redis.remote_host is not true")
        if redis.get("tls_enabled") is not True:
            failures.append("redis.tls_enabled is not true")

    worker = payload.get("worker", {})
    if worker.get("required") is not True:
        failures.append("worker.required is not true")
    if worker.get("ready") is not True:
        failures.append("worker.ready is not true")
    if worker.get("live") is not True:
        failures.append("worker.live is not true")
    if worker.get("inline_fallback_enabled") is not False:
        failures.append("worker.inline_fallback_enabled is not false")
    if managed_services_required:
        transport = worker.get("transport", {})
        for target_name in ("broker", "backend"):
            target = transport.get(target_name, {})
            if target.get("configured") is not True:
                failures.append(f"worker.transport.{target_name}.configured is not true")
            if target.get("remote_host") is not True:
                failures.append(f"worker.transport.{target_name}.remote_host is not true")
            if target.get("tls_enabled") is not True:
                failures.append(f"worker.transport.{target_name}.tls_enabled is not true")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate strict-runtime deployment health.")
    parser.add_argument("--base-url", default="http://127.0.0.1:18000")
    parser.add_argument("--timeout-seconds", type=int, default=240)
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    timeout_seconds = max(10, int(args.timeout_seconds))
    poll_seconds = max(0.5, float(args.poll_seconds))
    deadline = time.time() + timeout_seconds

    last_report: dict = {}
    while time.time() <= deadline:
        code, body = _fetch_json(f"{base_url}/")
        report = {
            "check": "strict_runtime_root",
            "url": f"{base_url}/",
            "code": code,
            "body": body,
            "failures": [],
        }
        if code != 200:
            report["failures"] = [f"root endpoint returned status {code}"]
            last_report = report
            time.sleep(poll_seconds)
            continue

        failures = _evaluate_root_payload(body)
        report["failures"] = failures
        if failures:
            last_report = report
            time.sleep(poll_seconds)
            continue

        docs_code = _fetch_status(f"{base_url}/docs")
        metrics_code = _fetch_status(f"{base_url}/metrics")
        report["docs_code"] = docs_code
        report["metrics_code"] = metrics_code
        if docs_code != 200:
            report["failures"].append(f"/docs returned status {docs_code}")
        if metrics_code != 200:
            report["failures"].append(f"/metrics returned status {metrics_code}")

        if report["failures"]:
            last_report = report
            time.sleep(poll_seconds)
            continue

        print(
            json.dumps(
                {
                    "pass": True,
                    "base_url": base_url,
                    "checks": [
                        report,
                    ],
                },
                indent=2,
            )
        )
        return 0

    print(
        json.dumps(
            {
                "pass": False,
                "base_url": base_url,
                "timeout_seconds": timeout_seconds,
                "last_report": last_report
                or {"error": "No response before timeout"},
            },
            indent=2,
        )
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
