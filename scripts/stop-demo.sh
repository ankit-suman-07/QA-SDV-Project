#!/usr/bin/env bash

set -u

ROOT_DIR="$(
  cd "$(dirname "${BASH_SOURCE[0]}")/.."
  pwd
)"

RUNTIME_DIR="${ROOT_DIR}/.demo-runtime"

stop_process() {
  local name="$1"
  local pid_file="$2"

  if [[ ! -f "${pid_file}" ]]; then
    echo "[not managed] ${name}"
    return
  fi

  local process_pid
  process_pid="$(cat "${pid_file}")"

  if kill -0 "${process_pid}" >/dev/null 2>&1; then
    kill "${process_pid}"

    for _ in {1..10}; do
      if ! kill -0 "${process_pid}" >/dev/null 2>&1; then
        break
      fi

      sleep 1
    done

    if kill -0 "${process_pid}" >/dev/null 2>&1; then
      kill -9 "${process_pid}" >/dev/null 2>&1
    fi

    echo "[stopped] ${name}"
  else
    echo "[already stopped] ${name}"
  fi

  rm -f "${pid_file}"
}

stop_process \
  "Frontend" \
  "${RUNTIME_DIR}/frontend.pid"

stop_process \
  "Spring Boot backend" \
  "${RUNTIME_DIR}/backend.pid"

stop_process \
  "Kuksa-to-Ditto bridge" \
  "${RUNTIME_DIR}/bridge.pid"

echo "Stopping Kuksa and vehicle simulator..."

docker compose \
  -f "${ROOT_DIR}/vehicle-simulator/docker-compose.yml" \
  down

echo
echo "Repository demo services stopped."
echo "External Eclipse Ditto was left running."