#!/usr/bin/env sh
set -eu

pause_seconds="${WORKER_REDIS_QUOTA_RETRY_SECONDS:-180}"
restart_delay_seconds="${WORKER_RESTART_DELAY_SECONDS:-3}"

while true; do
  if [ "${WORKER_AUTO_DEGRADE_ON_REDIS_QUOTA_EXCEEDED:-true}" = "true" ]; then
    if python3 - <<'PY'
import os
import sys

try:
    import redis
except Exception:
    sys.exit(0)

url = (os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL") or "").strip()
if not url:
    sys.exit(0)

try:
    client = redis.Redis.from_url(
        url,
        socket_timeout=1.5,
        socket_connect_timeout=1.5,
        health_check_interval=30,
        decode_responses=True,
    )
    client.ping()
except Exception as exc:  # noqa: BLE001
    if "max requests limit exceeded" in str(exc or "").lower():
        print("Redis quota exhausted; pausing Celery worker start.")
        sys.exit(42)
    sys.exit(0)

sys.exit(0)
PY
    then
      :
    else
      preflight_code="$?"
      if [ "$preflight_code" = "42" ]; then
        echo "Worker paused for ${pause_seconds}s due to Redis monthly request limit."
        sleep "$pause_seconds"
        continue
      fi
    fi
  fi

  celery -A app.workers:celery_app worker --loglevel=INFO --concurrency="${CELERY_CONCURRENCY:-2}" --hostname=worker@%h
  exit_code="$?"
  if [ "$exit_code" = "0" ]; then
    exit 0
  fi
  echo "Celery exited with status ${exit_code}; retrying in ${restart_delay_seconds}s."
  sleep "$restart_delay_seconds"
done
