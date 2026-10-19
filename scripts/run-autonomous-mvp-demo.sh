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

SCENARIO_ACTIVE=0


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


capture_status() {
    expected_status="$1"
    maximum_messages="$2"

    echo
    echo "Waiting for ${expected_status} MQTT event..."

    compose exec \
        -T \
        mqtt \
        sh -c \
        "mosquitto_sub \
        -h localhost \
        -t '${MQTT_TOPIC}' \
        -C ${maximum_messages} \
        -W 150 \
        | grep -m 1 \
        '\"healthStatus\": \"${expected_status}\"'"
}


send_scenario_action() {
    action="$1"
    action_id="$2"

    curl \
        -fsS \
        -X POST \
        http://localhost:8090/api/v1/scenarios/actions \
        -H "Content-Type: application/json" \
        -d "{
            \"vehicleId\": \"${VEHICLE_ID}\",
            \"action\": \"${action}\",
            \"scenario\": \"${SCENARIO}\",
            \"actionId\": \"${action_id}\",
            \"traceId\": \"${action_id}\"
        }" \
        | python -m json.tool
}


clear_active_scenario() {
    if [ "${SCENARIO_ACTIVE}" -eq 1 ]; then
        echo
        echo "Cleaning up the active scenario..."

        curl \
            -fsS \
            -X POST \
            http://localhost:8090/api/v1/scenarios/actions \
            -H "Content-Type: application/json" \
            -d "{
                \"vehicleId\": \"${VEHICLE_ID}\",
                \"action\": \"CLEAR_SCENARIO\",
                \"scenario\": \"${SCENARIO}\",
                \"actionId\": \"demo-cleanup\",
                \"traceId\": \"demo-cleanup\"
            }" \
            >/dev/null 2>&1 \
            || true
    fi
}


trap clear_active_scenario EXIT
trap 'exit 130' INT
trap 'exit 143' TERM


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

capture_status \
    "HEALTHY" \
    10

echo
echo "Injecting LiDAR obstruction..."

send_scenario_action \
    "INJECT_SCENARIO" \
    "demo-obstruction-001"

SCENARIO_ACTIVE=1

capture_status \
    "EMERGENCY_BRAKING" \
    60

echo
echo "Clearing LiDAR obstruction..."

send_scenario_action \
    "CLEAR_SCENARIO" \
    "demo-clear-001"

SCENARIO_ACTIVE=0

capture_status \
    "HEALTHY" \
    60

echo
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