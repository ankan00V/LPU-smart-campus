#!/usr/bin/env python3
import argparse
import json
import urllib.error
import urllib.request


def _post_json(url: str, *, token: str, payload: dict) -> tuple[int, dict]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url=url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return int(resp.getcode()), json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8"))
        except Exception:  # noqa: BLE001
            detail = {"detail": str(exc)}
        return int(exc.code), detail
    except Exception as exc:  # noqa: BLE001
        return 0, {"detail": str(exc)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Trigger recovery retro notification dispatch")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--admin-token", default="", help="Admin bearer token")
    parser.add_argument("--limit", type=int, default=400)
    parser.add_argument("--student-id", type=int, default=0)
    parser.add_argument("--course-id", type=int, default=0)
    parser.add_argument("--force-resend", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-refresh", action="store_true")
    args = parser.parse_args()

    payload = {
        "limit": max(1, int(args.limit)),
        "force_resend": bool(args.force_resend),
        "dry_run": bool(args.dry_run),
        "refresh_scope": not bool(args.no_refresh),
    }
    if int(args.student_id) > 0:
        payload["student_id"] = int(args.student_id)
    if int(args.course_id) > 0:
        payload["course_id"] = int(args.course_id)

    code, body = _post_json(
        f"{args.base_url.rstrip('/')}/attendance/recovery/retro-notify",
        token=str(args.admin_token or "").strip(),
        payload=payload,
    )
    print(json.dumps({"status_code": code, "payload": body}, indent=2))
    if code != 200:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
