#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
CELERY_BIN="${ROOT_DIR}/.venv/bin/celery"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"

load_env_from_dotenv() {
  eval "$("${PYTHON_BIN}" - "${ENV_FILE}" <<'PY'
import shlex
import sys

from dotenv import dotenv_values

for key, value in dotenv_values(sys.argv[1]).items():
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
