#!/bin/sh

set -eu

SCRIPT_DIRECTORY=$(
    CDPATH= cd -- "$(dirname -- "$0")"
    pwd
)

REPOSITORY_ROOT=$(
    CDPATH= cd -- "${SCRIPT_DIRECTORY}/.."
    pwd
)

COMPOSE_FILE="${REPOSITORY_ROOT}/vehicle-simulator/docker-compose.yml"

VEHICLE_ID="${SIMULATED_VEHICLE_ID:-vehicle-001}"
SCENARIO="LIDAR_OBSTRUCTION"
MQTT_TOPIC="sdv/autonomy/status"

compose() {
    docker compose \
        -f "${COMPOSE_FILE}" \
        "$@"
}


require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Required command not found: $1"
        exit 1
    fi
}


wait_for_simulator() {
    echo "Waiting for the simulator control API..."

    attempts=0

    while [ "${attempts}" -lt 60 ]; do
        if curl \
            -fsS \
            http://localhost:8090/health \
            >/dev/null 2>&1
        then
            echo "Simulator control API is ready."
            return
        fi

        attempts=$((attempts + 1))
        sleep 2
    done

    echo "Simulator control API did not become ready."
    exit 1
}


wait_for_velocitas_app() {
    echo "Waiting for the Velocitas application..."

    attempts=0

    while [ "${attempts}" -lt 60 ]; do
        container_id=$(
            compose ps \
                --status running \
                -q autonomous-health-app
        )

        if [ -n "${container_id}" ]; then
            echo "Velocitas application is running."
            return
        fi

        attempts=$((attempts + 1))
        sleep 2
    done

    echo "Velocitas application did not start."
    compose logs \
        --tail=80 \
        autonomous-health-app
    exit 1
}


require_command docker
require_command curl
require_command python

if ! docker info >/dev/null 2>&1; then
    echo "Docker Desktop is not running."
    exit 1
fi

echo "========================================"
echo "Autonomous SDV MVP Demonstration"
echo "========================================"
echo "Vehicle: ${VEHICLE_ID}"
echo "Scenario: ${SCENARIO}"
echo

echo "Starting the demonstration stack..."

compose up \
    -d \
    --build \
    --force-recreate

wait_for_simulator
wait_for_velocitas_app

echo
compose ps

python - "${COMPOSE_FILE}" "${VEHICLE_ID}" "${SCENARIO}" "${MQTT_TOPIC}" "${REPOSITORY_ROOT}" <<'PYTHON'
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from queue import Empty, Queue
import signal
import subprocess
import sys
from threading import Thread
from time import monotonic_ns
from urllib.request import Request, urlopen
from uuid import uuid4

compose_file, vehicle, scenario, topic, root = sys.argv[1:]
trials = int(os.getenv("MVP_TRIALS", "5"))
if trials < 1:
    raise SystemExit("MVP_TRIALS must be at least 1")

run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
output = Path(os.getenv(
    "MVP_TIMINGS_CSV", str(Path(root) / "evidence" / "v1" / f"mvp-timings-{run_id}.csv")
))
output.parent.mkdir(parents=True, exist_ok=True)
events = Queue()
active = False


def read_events(stream):
    for line in stream:
        received = monotonic_ns()
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("vehicleId") == vehicle:
            events.put((received, event))
    events.put(None)


def wait_for_status(status, started):
    deadline = started + 150_000_000_000
    print(f"Waiting for {status} MQTT event...", flush=True)
    while True:
        try:
            item = events.get(timeout=max(0, (deadline - monotonic_ns()) / 1e9))
        except Empty:
            raise TimeoutError(f"No {status} event for {vehicle} within 150 seconds") from None
        if item is None:
            raise RuntimeError("MQTT subscriber exited")
        received, event = item
        if received > deadline:
            raise TimeoutError(f"No {status} event for {vehicle} within 150 seconds")
        if received >= started and event.get("healthStatus") == status:
            print(json.dumps(event), flush=True)
            return (received - started) / 1e6


def send_action(action):
    action_id = f"demo-{uuid4().hex}"
    request = Request(
        "http://localhost:8090/api/v1/scenarios/actions",
        data=json.dumps({
            "vehicleId": vehicle, "action": action, "scenario": scenario,
            "actionId": action_id, "traceId": action_id,
        }).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = monotonic_ns()
    with urlopen(request, timeout=15) as response:
        body = json.load(response)
    print(json.dumps(body, indent=2), flush=True)
    expected_active = action == "INJECT_SCENARIO"
    if (body.get("vehicleId") != vehicle or body.get("scenario") != scenario
            or body.get("actionId") != action_id or body.get("active") is not expected_active):
        raise RuntimeError(f"Unexpected simulator response for {action}")
    return started


def stop(signum, _frame):
    raise SystemExit(128 + signum)


signal.signal(signal.SIGTERM, stop)
with output.open("x", newline="", encoding="utf-8") as csv_file:
    writer = csv.writer(csv_file)
    writer.writerow(["trial", "vehicle_id", "fault_ms", "recovery_ms", "result", "error"])
    csv_file.flush()
    print(f"Timing CSV: {output}", flush=True)
    with subprocess.Popen(
        ["docker", "compose", "-f", compose_file, "exec", "-T", "mqtt",
         "mosquitto_sub", "-h", "localhost", "-t", topic, "-R"],
        stdout=subprocess.PIPE, text=True,
    ) as subscriber:
        Thread(target=read_events, args=(subscriber.stdout,), daemon=True).start()
        try:
            for trial in range(1, trials + 1):
                fault_ms = recovery_ms = ""
                print(f"Trial {trial}/{trials}", flush=True)
                try:
                    wait_for_status("HEALTHY", monotonic_ns())
                    active = True
                    fault_ms = round(wait_for_status(
                        "EMERGENCY_BRAKING", send_action("INJECT_SCENARIO")
                    ), 3)
                    cleared_at = send_action("CLEAR_SCENARIO")
                    active = False
                    recovery_ms = round(wait_for_status("HEALTHY", cleared_at), 3)
                    writer.writerow([trial, vehicle, fault_ms, recovery_ms, "pass", ""])
                    print(f"Fault: {fault_ms} ms | Recovery: {recovery_ms} ms", flush=True)
                except (Exception, KeyboardInterrupt, SystemExit) as error:
                    writer.writerow([trial, vehicle, fault_ms, recovery_ms, "fail", str(error)])
                    raise
                finally:
                    csv_file.flush()
        finally:
            try:
                if active:
                    try:
                        send_action("CLEAR_SCENARIO")
                    except Exception as error:
                        print(f"Scenario cleanup failed: {error}", file=sys.stderr)
            finally:
                subscriber.terminate()
                try:
                    subscriber.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    subscriber.kill()
                    subscriber.wait()
PYTHON

echo "========================================"
echo "MVP demonstration completed successfully"
echo "========================================"
echo
echo "Validated pipeline:"
echo "Simulator -> KUKSA -> Velocitas -> MQTT"
echo
echo "The Docker services remain running."
echo "Stop them with:"
echo "docker compose -f vehicle-simulator/docker-compose.yml down"
