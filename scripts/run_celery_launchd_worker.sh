#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
CELERY_BIN="${ROOT_DIR}/.venv/bin/celery"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"

load_env_from_dotenv() {
  eval "$("${PYTHON_BIN}" - "${ROOT_DIR}" <<'PY'
import os
import shlex
import sys
from pathlib import Path

from dotenv import dotenv_values

root = Path(sys.argv[1]).resolve()
base_values = {
    str(key): value
    for key, value in dotenv_values(root / ".env").items()
    if key is not None
}
env_name = str(os.getenv("APP_ENV") or base_values.get("APP_ENV") or "development").strip().lower() or "development"
merged = dict(base_values)
overlay_path = root / (".env.production" if env_name in {"prod", "production"} else ".env.local")
should_overlay = env_name in {"prod", "production"}
if overlay_path.exists() and not should_overlay:
    overlay_preview = {
        str(key): value
        for key, value in dotenv_values(overlay_path).items()
        if key is not None
    }
    strict_value = str(overlay_preview.get("APP_RUNTIME_STRICT") or "").strip().lower()
    should_overlay = strict_value in {"1", "true", "yes", "on"}
if overlay_path.exists() and should_overlay:
    merged.update(
        {
            str(key): value
            for key, value in dotenv_values(overlay_path).items()
            if key is not None
        }
    )

for key, value in merged.items():
    if value is None:
        continue
    print(f"export {key}={shlex.quote(value)}")
PY
)"
}

require_value() {
  local name="$1"
  local expected="$2"
  local raw="${!name:-}"
  local got
  got="$(printf '%s' "${raw}" | tr '[:upper:]' '[:lower:]')"
  if [[ "${got}" != "${expected}" ]]; then
    echo "FATAL: ${name} must be '${expected}' for strict runtime (found '${raw:-<unset>}')." >&2
    exit 1
  fi
}

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "FATAL: missing env file at ${ENV_FILE}" >&2
  exit 1
fi

if [[ ! -x "${CELERY_BIN}" ]]; then
  echo "FATAL: celery executable not found at ${CELERY_BIN}" >&2
  exit 1
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "FATAL: python executable not found at ${PYTHON_BIN}" >&2
  exit 1
fi

mkdir -p "${ROOT_DIR}/logs"

load_env_from_dotenv

require_value "APP_RUNTIME_STRICT" "true"
require_value "REDIS_REQUIRED" "true"
require_value "WORKER_REQUIRED" "true"
require_value "WORKER_ENABLE_OTP" "true"
require_value "WORKER_ENABLE_NOTIFICATIONS" "true"
require_value "WORKER_ENABLE_FACE_REVERIFY" "true"
require_value "WORKER_ENABLE_RECOMPUTE" "true"
require_value "WORKER_WAIT_FOR_OTP_RESULT" "true"
require_value "WORKER_INLINE_FALLBACK_ENABLED" "false"

if [[ -z "${REDIS_URL:-}" ]]; then
  echo "FATAL: REDIS_URL must be set." >&2
  exit 1
fi

case "$(printf '%s' "${OTP_DELIVERY_MODE:-smtp}" | tr '[:upper:]' '[:lower:]')" in
  smtp|graph)
    ;;
  *)
    echo "FATAL: OTP_DELIVERY_MODE must be 'smtp' or 'graph'." >&2
    exit 1
    ;;
esac

if [[ -z "${CELERY_BROKER_URL:-}" ]]; then
  export CELERY_BROKER_URL="${REDIS_URL}"
fi

if [[ -z "${CELERY_RESULT_BACKEND:-}" ]]; then
  export CELERY_RESULT_BACKEND="${REDIS_URL}"
fi

cd "${ROOT_DIR}"
exec "${CELERY_BIN}" -A app.workers:celery_app worker \
  --loglevel="${CELERY_LOG_LEVEL:-INFO}" \
  --concurrency="${CELERY_WORKER_CONCURRENCY:-2}" \
  --hostname="${CELERY_WORKER_HOSTNAME:-worker-launchd@%h}"
