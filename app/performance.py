import json
import math
import os
import threading
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Any

_LOCK = threading.Lock()
_MAX_SAMPLES = max(1000, min(200_000, int((os.getenv("APP_PERFORMANCE_HISTORY_SIZE", "50000") or "50000"))))
_SAMPLES: deque[dict[str, Any]] = deque(maxlen=_MAX_SAMPLES)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _bucket_for_path(path: str) -> str:
    if path.startswith("/auth"):
        return "auth"
    if path.startswith("/attendance") or path.startswith("/makeup"):
        return "attendance"
    if path.startswith("/food"):
        return "food"
    if path.startswith("/enterprise") or path.startswith("/admin"):
        return "ops"
    return "default"


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, int(round((0.95 * (len(ordered) - 1))))))
    return float(ordered[idx])


def _p50(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = len(ordered) // 2
    if len(ordered) % 2 == 0 and idx > 0:
        return float((ordered[idx - 1] + ordered[idx]) / 2.0)
    return float(ordered[idx])


def get_sla_targets_ms() -> dict[str, float]:
    defaults = {
        "auth": 250.0,
        "attendance": 400.0,
        "food": 600.0,
        "ops": 5000.0,
        "default": 500.0,
    }
    raw = (os.getenv("APP_SLA_TARGETS_MS_JSON") or "").strip()
    if not raw:
        return defaults
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return defaults
    if not isinstance(parsed, dict):
        return defaults
    result = dict(defaults)
    for key, value in parsed.items():
        try:
            result[str(key)] = max(50.0, float(value))
        except (TypeError, ValueError):
            continue
    return result


def _float_env(name: str, default: float, *, minimum: float = 0.0) -> float:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return max(minimum, float(default))
    try:
        value = float(raw)
    except ValueError:
        value = float(default)
    return max(minimum, value)


def record_request_metric(path: str, method: str, status_code: int, duration_ms: float) -> None:
    entry = {
        "ts": _utc_now(),
        "path": str(path or "/"),
        "method": str(method or "GET"),
        "status_code": int(status_code),
        "duration_ms": float(max(0.0, duration_ms)),
        "bucket": _bucket_for_path(str(path or "/")),
    }
    with _LOCK:
        _SAMPLES.append(entry)


def snapshot_sla(window_minutes: int = 15) -> dict[str, Any]:
    cutoff = _utc_now() - timedelta(minutes=max(1, int(window_minutes)))
    with _LOCK:
        samples = [dict(item) for item in _SAMPLES if item.get("ts") and item["ts"] >= cutoff]

    by_bucket: dict[str, dict[str, Any]] = {}
    by_route: dict[str, dict[str, Any]] = {}
    targets = get_sla_targets_ms()

    grouped_bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    grouped_route: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in samples:
        bucket = str(item.get("bucket") or "default")
        grouped_bucket[bucket].append(item)
        route_key = f"{item.get('method', 'GET')} {item.get('path', '/')}"
        grouped_route[route_key].append(item)

    for bucket, rows in grouped_bucket.items():
        durations = [float(row.get("duration_ms", 0.0) or 0.0) for row in rows]
        error_count = sum(1 for row in rows if int(row.get("status_code", 200)) >= 500)
        total = len(rows)
        p95 = _p95(durations)
        by_bucket[bucket] = {
            "requests": total,
            "p50_ms": round(_p50(durations), 2),
            "p95_ms": round(p95, 2),
            "error_rate_percent": round((error_count / total * 100.0) if total else 0.0, 3),
            "target_p95_ms": float(targets.get(bucket, targets["default"])),
            "target_met": bool(p95 <= float(targets.get(bucket, targets["default"]))),
        }

    for route_key, rows in grouped_route.items():
        durations = [float(row.get("duration_ms", 0.0) or 0.0) for row in rows]
        error_count = sum(1 for row in rows if int(row.get("status_code", 200)) >= 500)
        total = len(rows)
        by_route[route_key] = {
            "requests": total,
            "p50_ms": round(_p50(durations), 2),
            "p95_ms": round(_p95(durations), 2),
            "error_rate_percent": round((error_count / total * 100.0) if total else 0.0, 3),
        }

    return {
        "window_minutes": max(1, int(window_minutes)),
        "sample_count": len(samples),
        "targets_ms": targets,
        "bucket_metrics": by_bucket,
        "route_metrics": by_route,
        "captured_at": _utc_now().isoformat(),
    }


def build_capacity_plan(
    *,
    window_minutes: int = 15,
    expected_peak_rps: float | None = None,
    growth_percent: float = 30.0,
    safety_factor: float = 1.3,
) -> dict[str, Any]:
    snapshot = snapshot_sla(window_minutes=max(1, int(window_minutes)))
    observed_rps = float(snapshot.get("sample_count", 0)) / float(max(60, int(window_minutes) * 60))
    baseline_rps = max(observed_rps, _float_env("APP_CAPACITY_BASELINE_RPS", 0.0))

    projected_rps = float(expected_peak_rps) if expected_peak_rps and expected_peak_rps > 0 else baseline_rps
    projected_rps *= 1.0 + max(0.0, float(growth_percent)) / 100.0
    protected_rps = projected_rps * max(1.0, float(safety_factor))

    per_node_rps = _float_env("APP_CAPACITY_PER_NODE_RPS", 25.0, minimum=1.0)
    current_nodes = int(_float_env("APP_CAPACITY_CURRENT_NODES", 1.0, minimum=1.0))
    recommended_nodes = max(1, int(math.ceil(protected_rps / per_node_rps)))
    headroom_percent = 0.0
    current_load_percent = 0.0
    if current_nodes > 0 and per_node_rps > 0:
        current_capacity = current_nodes * per_node_rps
        current_load_percent = (protected_rps / current_capacity) * 100.0 if current_capacity else 0.0
        headroom_percent = ((current_capacity - protected_rps) / current_capacity) * 100.0

    scale_up_threshold = _float_env("APP_AUTOSCALE_UP_THRESHOLD_PERCENT", 75.0, minimum=30.0)
    scale_down_threshold = _float_env("APP_AUTOSCALE_DOWN_THRESHOLD_PERCENT", 30.0, minimum=5.0)
    if scale_down_threshold >= scale_up_threshold:
        scale_down_threshold = max(5.0, scale_up_threshold - 10.0)
    if current_load_percent >= scale_up_threshold:
        autoscale_action = "scale_up"
    elif current_load_percent <= scale_down_threshold:
        autoscale_action = "scale_down"
    else:
        autoscale_action = "stable"

    target_violations = [
        bucket
        for bucket, metrics in (snapshot.get("bucket_metrics") or {}).items()
        if not bool((metrics or {}).get("target_met", True))
    ]
    return {
        "window_minutes": max(1, int(window_minutes)),
        "observed_rps": round(observed_rps, 3),
        "baseline_rps": round(baseline_rps, 3),
        "projected_peak_rps": round(projected_rps, 3),
        "protected_peak_rps": round(protected_rps, 3),
        "per_node_rps_assumption": round(per_node_rps, 3),
        "current_nodes": current_nodes,
        "recommended_nodes": recommended_nodes,
        "additional_nodes_required": max(0, recommended_nodes - current_nodes),
        "current_load_percent": round(current_load_percent, 2),
        "headroom_percent": round(headroom_percent, 2),
        "autoscale_thresholds_percent": {
            "scale_up": round(scale_up_threshold, 2),
            "scale_down": round(scale_down_threshold, 2),
        },
        "autoscale_recommended_action": autoscale_action,
        "sla_target_violations": target_violations,
        "snapshot": snapshot,
        "generated_at": _utc_now().isoformat(),
    }
