#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/deploy/docker-compose.strict.yml"
PROJECT_NAME="${PROJECT_NAME:-attendance-strict}"
BASE_URL="${BASE_URL:-http://127.0.0.1:18000}"
HEALTH_TIMEOUT_SECONDS="${HEALTH_TIMEOUT_SECONDS:-300}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

compose() {
  docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" "$@"
}

usage() {
  cat <<'EOF'
Usage:
  ./scripts/deploy_strict_stack.sh [up|down|status|logs|gate|restart]

Commands:
  up       Build + start strict stack and run health gate (default)
  down     Stop stack and remove volumes
  status   Show stack status
  logs     Stream stack logs (use SERVICE=<name> to narrow)
  gate     Run strict runtime health gate against running stack
  restart  Restart stack and run health gate

Environment overrides:
  PROJECT_NAME            Compose project name (default: attendance-strict)
  BASE_URL                Health gate base URL (default: http://127.0.0.1:18000)
  HEALTH_TIMEOUT_SECONDS  Health gate timeout in seconds (default: 300)
  PYTHON_BIN              Python executable for gate script (default: python3)
EOF
}

run_gate() {
  "${PYTHON_BIN}" "${ROOT_DIR}/scripts/strict_runtime_health_gate.py" \
    --base-url "${BASE_URL}" \
    --timeout-seconds "${HEALTH_TIMEOUT_SECONDS}"
}

ensure_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is required but not found in PATH." >&2
    exit 1
  fi
}

cmd="${1:-up}"
ensure_docker

case "${cmd}" in
  up)
    compose up -d --build
    if ! run_gate; then
      echo "Health gate failed. Current service state:" >&2
      compose ps >&2 || true
      echo "Recent logs:" >&2
      compose logs --tail=200 app worker redis mongo postgres >&2 || true
      exit 1
    fi
    compose ps
    ;;
  down)
    compose down -v --remove-orphans
    ;;
  status)
    compose ps
    ;;
  logs)
    if [[ -n "${SERVICE:-}" ]]; then
      compose logs -f "${SERVICE}"
    else
      compose logs -f
    fi
    ;;
  gate)
    run_gate
    ;;
  restart)
    compose down --remove-orphans
    compose up -d --build
    run_gate
    compose ps
    ;;
  *)
    usage
    exit 1
    ;;
esac
