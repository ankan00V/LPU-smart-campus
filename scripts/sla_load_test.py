#!/usr/bin/env python3
import argparse
import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import median
from typing import Any


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, int(round(q * (len(ordered) - 1)))))
    return float(ordered[idx])


def _request_once(url: str, token: str | None) -> dict[str, Any]:
    started = time.perf_counter()
    req = urllib.request.Request(url=url, method="GET")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            code = int(resp.getcode())
            _ = resp.read(256)
    except urllib.error.HTTPError as exc:
        code = int(exc.code)
    except Exception:
        code = 0
    latency_ms = (time.perf_counter() - started) * 1000.0
    return {"status_code": code, "latency_ms": latency_ms}


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple HTTP load test with p95/error-rate output")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base API URL")
    parser.add_argument(
        "--paths",
        default="/,/auth/me,/resources/overview",
        help="Comma-separated path list to cycle across requests",
    )
    parser.add_argument("--requests", type=int, default=300, help="Total requests to execute")
    parser.add_argument("--concurrency", type=int, default=20, help="Worker concurrency")
    parser.add_argument("--token", default="", help="Optional bearer token")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    paths = [p.strip() for p in args.paths.split(",") if p.strip()]
    total = max(1, int(args.requests))
    workers = max(1, int(args.concurrency))
    token = args.token.strip() or None

    jobs = [f"{base}{paths[idx % len(paths)]}" for idx in range(total)]
    latencies: list[float] = []
    status_codes: list[int] = []

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_request_once, url, token) for url in jobs]
        for future in as_completed(futures):
            result = future.result()
            latencies.append(float(result["latency_ms"]))
            status_codes.append(int(result["status_code"]))
    elapsed = time.perf_counter() - started

    errors = sum(1 for code in status_codes if code == 0 or code >= 500)
    out = {
        "total_requests": total,
        "concurrency": workers,
        "elapsed_seconds": round(elapsed, 3),
        "throughput_rps": round(total / elapsed, 2) if elapsed > 0 else 0.0,
        "latency_ms": {
            "p50": round(float(median(latencies)) if latencies else 0.0, 2),
            "p95": round(_percentile(latencies, 0.95), 2),
            "max": round(max(latencies) if latencies else 0.0, 2),
        },
        "error_rate_percent": round((errors / total * 100.0) if total else 0.0, 3),
        "status_counts": {
            str(code): status_codes.count(code) for code in sorted(set(status_codes))
        },
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
