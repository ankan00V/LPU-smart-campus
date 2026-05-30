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

urls = []
for name in ("CELERY_BROKER_URL", "WORKER_BROKER_URL", "REDIS_URL", "REDIS_URL_SECONDARY", "REDIS_URL_TERTIARY"):
    url = (os.getenv(name) or "").strip()
    if url and url not in urls:
        urls.append(url)

if not urls:
    sys.exit(0)

quota_errors = []
for url in urls:
    client = None
    try:
        client = redis.Redis.from_url(
            url,
            socket_timeout=1.5,
            socket_connect_timeout=1.5,
            health_check_interval=30,
            decode_responses=True,
        )
        client.ping()
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        message = str(exc or "")
        if "max requests limit exceeded" in message.lower():
            quota_errors.append(message)
            continue
        sys.exit(0)
    finally:
        try:
            if client is not None:
                client.close()
        except Exception:
            pass

if quota_errors:
    print("All configured Redis transports are quota exhausted; pausing Celery worker start.")
    sys.exit(42)

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
