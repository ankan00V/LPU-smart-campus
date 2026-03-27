#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="com.smartcampus.celery.worker"
TEMPLATE_PATH="${ROOT_DIR}/deploy/launchd/${LABEL}.plist.template"
TARGET_DIR="${HOME}/Library/LaunchAgents"
TARGET_PATH="${TARGET_DIR}/${LABEL}.plist"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
ENV_FILES=()
if [[ -f "${ROOT_DIR}/.env" ]]; then
  ENV_FILES+=("${ROOT_DIR}/.env")
fi
if [[ -f "${ROOT_DIR}/.env.local" ]]; then
  ENV_FILES+=("${ROOT_DIR}/.env.local")
fi
STDOUT_LOG="${HOME}/Library/Logs/smartcampus-celery-launchd.out.log"
STDERR_LOG="${HOME}/Library/Logs/smartcampus-celery-launchd.err.log"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/install_celery_launchd_agent.sh [install|remove|status]

Commands:
  install   Render plist, install LaunchAgent, and start worker (default)
  remove    Unload and remove LaunchAgent
  status    Show launchd + worker status
EOF
}

ensure_requirements() {
  if [[ ! -f "${TEMPLATE_PATH}" ]]; then
    echo "Missing template: ${TEMPLATE_PATH}" >&2
    exit 1
  fi
  if [[ "${#ENV_FILES[@]}" -eq 0 ]]; then
    echo "Missing env file: ${ROOT_DIR}/.env (or .env.local)" >&2
    exit 1
  fi
  if [[ ! -x "${PYTHON_BIN}" ]]; then
    echo "Missing python executable: ${PYTHON_BIN}" >&2
    exit 1
  fi
}

load_env_from_dotenv() {
  eval "$("${PYTHON_BIN}" - "${ENV_FILES[@]}" <<'PY'
import shlex
import sys

from dotenv import dotenv_values

data = {}
for path in sys.argv[1:]:
    for key, value in dotenv_values(path).items():
        if value is None:
            continue
        data[key] = value

for key, value in data.items():
    print(f"export {key}={shlex.quote(value)}")
PY
)"
}

render_env_xml() {
  "${PYTHON_BIN}" - "${ENV_FILES[@]}" <<'PY'
import sys
from xml.sax.saxutils import escape

from dotenv import dotenv_values

data = {}
for path in sys.argv[1:]:
    for key, value in dotenv_values(path).items():
        if value is None:
            continue
        data[key] = value

for key, value in data.items():
    print(f"    <key>{escape(key)}</key>")
    print(f"    <string>{escape(value)}</string>")
PY
}

validate_strict_env() {
  "${PYTHON_BIN}" - "${ENV_FILES[@]}" <<'PY'
import sys

from dotenv import dotenv_values

data = {}
for path in sys.argv[1:]:
    for key, value in dotenv_values(path).items():
        if value is None:
            continue
        data[key] = value

required = {
    "APP_RUNTIME_STRICT": "true",
    "REDIS_REQUIRED": "true",
    "WORKER_REQUIRED": "true",
    "WORKER_ENABLE_OTP": "true",
    "WORKER_ENABLE_NOTIFICATIONS": "true",
    "WORKER_ENABLE_FACE_REVERIFY": "true",
    "WORKER_ENABLE_RECOMPUTE": "true",
    "WORKER_WAIT_FOR_OTP_RESULT": "true",
    "WORKER_INLINE_FALLBACK_ENABLED": "false",
}
errors = []
for key, expected in required.items():
    got = (data.get(key) or "").strip().lower()
    if got != expected:
        errors.append(f"{key} must be '{expected}' (found '{data.get(key)}')")

if not (data.get("REDIS_URL") or "").strip():
    errors.append("REDIS_URL must be set")
if not (data.get("CELERY_BROKER_URL") or "").strip():
    errors.append("CELERY_BROKER_URL must be set")
if not (data.get("CELERY_RESULT_BACKEND") or "").strip():
    errors.append("CELERY_RESULT_BACKEND must be set")

otp_mode = (data.get("OTP_DELIVERY_MODE") or "smtp").strip().lower()
if otp_mode not in {"smtp", "graph"}:
    errors.append("OTP_DELIVERY_MODE must be 'smtp' or 'graph'")

if errors:
    print("Strict env validation failed:", file=sys.stderr)
    for err in errors:
        print(f" - {err}", file=sys.stderr)
    raise SystemExit(1)
PY
}

render_template() {
  mkdir -p "${TARGET_DIR}"
  mkdir -p "${HOME}/Library/Logs"
  local escaped_root
  local escaped_home
  local escaped_python
  local env_xml_file
  local tmp_rendered
  escaped_root="$(printf '%s' "${ROOT_DIR}" | sed 's/[\\/&]/\\&/g')"
  escaped_home="$(printf '%s' "${HOME}" | sed 's/[\\/&]/\\&/g')"
  escaped_python="$(printf '%s' "${PYTHON_BIN}" | sed 's/[\\/&]/\\&/g')"
  env_xml_file="$(mktemp)"
  tmp_rendered="$(mktemp)"
  render_env_xml > "${env_xml_file}"
  sed -e "s#__PROJECT_ROOT__#${escaped_root}#g" \
      -e "s#__HOME_DIR__#${escaped_home}#g" \
      -e "s#__PYTHON_BIN__#${escaped_python}#g" \
      "${TEMPLATE_PATH}" | awk -v repl_file="${env_xml_file}" '
        /__DOTENV_ENV_XML__/ {
          while ((getline line < repl_file) > 0) {
            print line
          }
          close(repl_file)
          next
        }
        { print }
      ' > "${tmp_rendered}"
  mv "${tmp_rendered}" "${TARGET_PATH}"
  rm -f "${env_xml_file}"
  chmod 0600 "${TARGET_PATH}"
}

stop_agent() {
  launchctl bootout "gui/${UID}" "${TARGET_PATH}" >/dev/null 2>&1 || true
  launchctl bootout "gui/${UID}/${LABEL}" >/dev/null 2>&1 || true
}

start_agent() {
  launchctl bootstrap "gui/${UID}" "${TARGET_PATH}"
  launchctl enable "gui/${UID}/${LABEL}" >/dev/null 2>&1 || true
  launchctl kickstart -k "gui/${UID}/${LABEL}"
}

status_agent() {
  if [[ -f "${TARGET_PATH}" ]]; then
    echo "LaunchAgent plist: ${TARGET_PATH}"
  else
    echo "LaunchAgent plist missing: ${TARGET_PATH}"
  fi
  launchctl print "gui/${UID}/${LABEL}" | awk '
    /^gui\// { print; next }
    /^\t(state|path|program|working directory|stdout path|stderr path|runs|pid|immediate reason|last exit code|last terminating signal)[[:space:]]*=/ { print }
  '
  (
    load_env_from_dotenv
    "${PYTHON_BIN}" -m celery -A app.workers:celery_app inspect ping --timeout=2
  ) || true
  echo "stdout: ${STDOUT_LOG}"
  echo "stderr: ${STDERR_LOG}"
}

wait_for_worker() {
  local attempts="${1:-20}"
  local i=0
  while [[ "${i}" -lt "${attempts}" ]]; do
    if (
      load_env_from_dotenv
      "${PYTHON_BIN}" -m celery -A app.workers:celery_app inspect ping --timeout=2 >/dev/null 2>&1
    ); then
      return 0
    fi
    i=$((i + 1))
    sleep 1
  done
  return 1
}

cmd="${1:-install}"

case "${cmd}" in
  install)
    ensure_requirements
    validate_strict_env
    render_template
    stop_agent
    start_agent
    if ! wait_for_worker 30; then
      echo "LaunchAgent started but worker ping did not succeed within timeout." >&2
      status_agent
      exit 1
    fi
    status_agent
    ;;
  remove)
    stop_agent
    rm -f "${TARGET_PATH}"
    echo "Removed ${TARGET_PATH}"
    ;;
  status)
    status_agent
    ;;
  *)
    usage
    exit 1
    ;;
esac
