# Performance SLA And Capacity Runbook

## Default SLA Targets (p95)

- Auth: `<= 250ms`
- Attendance/Makeup: `<= 400ms`
- Food: `<= 600ms`
- Default: `<= 500ms`

Targets can be overridden with `APP_SLA_TARGETS_MS_JSON`.

## Live SLA Snapshot

Use:

```bash
GET /enterprise/performance/sla?window_minutes=15
```

Inspect:

- `bucket_metrics.*.p95_ms`
- `bucket_metrics.*.target_met`
- `bucket_metrics.*.error_rate_percent`

## Capacity Plan Snapshot

Use:

```bash
GET /enterprise/performance/capacity-plan?window_minutes=15&growth_percent=30&safety_factor=1.3
```

Inspect:

- `observed_rps`
- `projected_peak_rps`
- `recommended_nodes`
- `headroom_percent`
- `sla_target_violations`
- `autoscale_thresholds_percent`
- `autoscale_recommended_action`

## Load Test

```bash
PYTHONPATH=. .venv/bin/python scripts/sla_load_test.py \
  --base-url http://127.0.0.1:8000 \
  --paths /,/auth/me,/attendance/summary \
  --requests 500 \
  --concurrency 30 \
  --token "<bearer_token>"
```

## Capacity Planning Loop

1. Record weekly load-test p95/error-rate/throughput.
2. Compare against SLA budget and peak concurrency assumptions.
3. Increase capacity or optimize endpoints when:
   - p95 exceeds target for two consecutive runs.
   - error rate exceeds 0.5%.
4. Re-baseline after significant release changes.

## Automated Capacity Report

```bash
PYTHONPATH=. .venv/bin/python scripts/capacity_plan_report.py \
  --window-minutes 15 \
  --growth-percent 35 \
  --safety-factor 1.4
```

Tune thresholds with:

- `APP_AUTOSCALE_UP_THRESHOLD_PERCENT` (default `75`)
- `APP_AUTOSCALE_DOWN_THRESHOLD_PERCENT` (default `30`)
