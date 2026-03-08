#!/usr/bin/env python3
import argparse
import json
from typing import Any
import urllib.error
import urllib.request


def _request_json(url: str, *, method: str = "GET", token: str | None = None) -> tuple[int, Any]:
    req = urllib.request.Request(url=url, method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if method.upper() != "GET":
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            code = int(resp.getcode())
            payload = json.loads(resp.read().decode("utf-8"))
            return code, payload
    except urllib.error.HTTPError as exc:
        return int(exc.code), {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return 0, {"error": str(exc)}


def _bool(value: Any) -> bool:
    return bool(value)


def _controls_ok(code: int, body: Any) -> bool:
    if code != 200 or not isinstance(body, dict):
        return False
    provider = str(body.get("secrets_provider") or "").strip().lower()
    key_ids = [str(item) for item in (body.get("field_encryption_key_ids") or []) if str(item).strip()]
    return (
        _bool(body.get("mfa_enforced_for_admin_faculty"))
        and _bool(body.get("deletion_dual_control_required"))
        and _bool(body.get("scim_enabled"))
        and provider in {"file", "aws_secrets_manager"}
        and bool(key_ids)
        and all(not key_id.startswith("dev-") for key_id in key_ids)
    )


def _rotation_evidence_ok(code: int, body: Any) -> bool:
    if code != 200 or not isinstance(body, list) or not body:
        return False
    latest = body[0]
    if not isinstance(latest, dict):
        return False
    results = latest.get("results")
    if not isinstance(results, list) or not results:
        return False
    for item in results:
        if not isinstance(item, dict):
            return False
        if int(item.get("failed", 0)) > 0:
            return False
    return True


def _sla_ok(code: int, body: Any) -> bool:
    if code != 200 or not isinstance(body, dict):
        return False
    if int(body.get("sample_count", 0) or 0) <= 0:
        return False
    bucket_metrics = body.get("bucket_metrics")
    if not isinstance(bucket_metrics, dict) or not bucket_metrics:
        return False
    for metrics in bucket_metrics.values():
        if isinstance(metrics, dict) and not bool(metrics.get("target_met", False)):
            return False
    return True


def _capacity_ok(code: int, body: Any) -> bool:
    if code != 200 or not isinstance(body, dict):
        return False
    violations = body.get("sla_target_violations")
    return isinstance(violations, list) and len(violations) == 0


def _dr_backup_ok(code: int, body: Any) -> bool:
    return code == 200 and isinstance(body, list) and len(body) > 0


def _dr_drill_ok(code: int, body: Any) -> bool:
    if code != 200 or not isinstance(body, list) or not body:
        return False
    latest = body[0]
    if not isinstance(latest, dict):
        return False
    return bool(latest.get("target_met")) and bool(latest.get("manifest_integrity_ok"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run release gate checks for production promotion")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--admin-token", default="", help="Admin bearer token for protected checks")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    token = args.admin_token.strip() or None

    checks: list[dict] = []

    code, body = _request_json(f"{base}/")
    checks.append({"check": "health", "ok": code == 200, "code": code, "body": body})

    code, body = _request_json(f"{base}/enterprise/controls/status", token=token)
    controls_ok = _controls_ok(code, body)
    checks.append({"check": "enterprise_controls_status", "ok": controls_ok, "code": code, "body": body})

    code, body = _request_json(f"{base}/enterprise/security/encryption/rotation-runs?limit=1", token=token)
    has_rotation_evidence = _rotation_evidence_ok(code, body)
    checks.append(
        {
            "check": "encryption_rotation_evidence",
            "ok": has_rotation_evidence,
            "code": code,
            "body": body,
        }
    )

    code, body = _request_json(f"{base}/enterprise/performance/sla?window_minutes=15", token=token)
    checks.append({"check": "performance_sla", "ok": _sla_ok(code, body), "code": code, "body": body})

    code, body = _request_json(f"{base}/enterprise/performance/capacity-plan?window_minutes=15", token=token)
    checks.append({"check": "performance_capacity_plan", "ok": _capacity_ok(code, body), "code": code, "body": body})

    code, body = _request_json(f"{base}/enterprise/dr/backups?limit=1", token=token)
    checks.append({"check": "dr_latest_backup", "ok": _dr_backup_ok(code, body), "code": code, "body": body})

    code, body = _request_json(f"{base}/enterprise/dr/restore-drills?limit=1", token=token)
    checks.append({"check": "dr_latest_restore_drill", "ok": _dr_drill_ok(code, body), "code": code, "body": body})

    code, body = _request_json(f"{base}/enterprise/secrets/validate", method="POST", token=token)
    checks.append({"check": "secrets_validate", "ok": code == 200, "code": code, "body": body})

    summary = {
        "base_url": base,
        "checks": checks,
        "pass": all(item["ok"] for item in checks),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
