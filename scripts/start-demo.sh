#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(
  cd "$(dirname "${BASH_SOURCE[0]}")/.."
  pwd
)"

RUNTIME_DIR="${ROOT_DIR}/.demo-runtime"
LOG_DIR="${RUNTIME_DIR}/logs"
PYTHON="${ROOT_DIR}/.venv/bin/python"

mkdir -p "${LOG_DIR}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: Required command not found: $1"
    exit 1
  fi
}

wait_for_url() {
  local name="$1"
  local url="$2"
  local attempts="${3:-30}"

  for ((attempt = 1; attempt <= attempts; attempt++)); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "[ready] ${name}"
      return 0
    fi

    sleep 1
  done

  echo "ERROR: ${name} did not become ready: ${url}"
  return 1
}

start_background_process() {
  local name="$1"
  local pid_file="$2"
  local log_file="$3"
  shift 3

  if [[ -f "${pid_file}" ]]; then
    local existing_pid
    existing_pid="$(cat "${pid_file}")"

    if kill -0 "${existing_pid}" >/dev/null 2>&1; then
      echo "[running] ${name} (PID ${existing_pid})"
      return 0
    fi
  fi

  nohup "$@" >"${log_file}" 2>&1 &
  local process_pid=$!
  echo "${process_pid}" >"${pid_file}"

  echo "[started] ${name} (PID ${process_pid})"
}

require_command curl
require_command docker

if [[ ! -x "${PYTHON}" ]]; then
  echo "ERROR: Python virtual environment not found."
  echo "Create it at ${ROOT_DIR}/.venv and install dependencies."
  exit 1
fi

echo "Checking external Eclipse Ditto..."

if ! curl -fsS \
  -u ditto:ditto \
  "http://localhost:8080/api/2/things" \
  >/dev/null 2>&1; then
  echo "ERROR: Eclipse Ditto is not available on port 8080."
  echo "Start the external Ditto Docker deployment first."
  exit 1
fi

echo "[ready] Eclipse Ditto"

echo "Starting Kuksa and vehicle simulator..."

docker compose \
  -f "${ROOT_DIR}/vehicle-simulator/docker-compose.yml" \
  up -d --build

wait_for_url \
  "Vehicle simulator" \
  "http://localhost:8090/health" \
  45

echo "Starting Kuksa-to-Ditto bridge..."

start_background_process \
  "Kuksa-to-Ditto bridge" \
  "${RUNTIME_DIR}/bridge.pid" \
  "${LOG_DIR}/bridge.log" \
  env \
  PYTHONUNBUFFERED=1 \
  EXPERIMENT_ID=demo-runtime \
  EXPERIMENT_EVENT_LIMIT=100000 \
  PUBLISH_INTERVAL_SECONDS=1 \
  SIMULATOR_CONTROL_URL=http://localhost:8090 \
  "${PYTHON}" \
  "${ROOT_DIR}/ditto/scripts/interim-kuksa-to-ditto-bridge.py"

echo "Starting Spring Boot backend..."

if curl -fsS \
  "http://localhost:8082/actuator/health" \
  >/dev/null 2>&1; then
  echo "[running] Spring Boot backend"
else
  (
    cd "${ROOT_DIR}/backend"

    nohup env \
      SERVER_PORT=8082 \
      SDV_SIMULATOR_MODE=http \
      SIMULATOR_BASE_URL=http://localhost:8090 \
      ./mvnw spring-boot:run \
      >"${LOG_DIR}/backend.log" 2>&1 &

    echo $! >"${RUNTIME_DIR}/backend.pid"
  )

  wait_for_url \
    "Spring Boot backend" \
    "http://localhost:8082/actuator/health" \
    60
fi

echo "Starting frontend..."

if curl -fsS \
  "http://localhost:3000/index.html" \
  >/dev/null 2>&1; then
  echo "[running] Frontend"
else
  start_background_process \
    "Frontend" \
    "${RUNTIME_DIR}/frontend.pid" \
    "${LOG_DIR}/frontend.log" \
    "${PYTHON}" \
    -m http.server \
    3000 \
    --directory "${ROOT_DIR}/frontend"

  wait_for_url \
    "Frontend" \
    "http://localhost:3000/index.html" \
    15
fi

echo
echo "SDV demo services are ready:"
echo "  Frontend:  http://localhost:3000/index.html"
echo "  Backend:   http://localhost:8082/actuator/health"
echo "  Simulator: http://localhost:8090/health"
echo "  Ditto:     http://localhost:8080/api/2/things/sdv:vehicle-001"
echo
echo "Logs:"
echo "  ${LOG_DIR}/bridge.log"
echo "  ${LOG_DIR}/backend.log"
echo "  ${LOG_DIR}/frontend.log"