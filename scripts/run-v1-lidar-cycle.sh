#!/bin/sh
# Run one V1 LiDAR fault and recovery cycle on the two-vehicle edge stack
# (vehicle-simulator/docker-compose.v1.yml) and check it with the team's
# capture oracle (scripts/v1_dev, a development tool).
#
# Pass: vehicle-002 goes HEALTHY -> CRITICAL LIDAR_OBSTRUCTION -> HEALTHY,
# vehicle-001 stays HEALTHY, and provider-002 rejects vehicle-001 with 409.
#
# Environment:
#   PUBLISH_INTERVAL_SECONDS  provider tick (default 5, as in the stack)
#   PROVIDER_002_URL          provider-002 control URL (default http://localhost:8092)
#   E2_CAPTURE_OUT            optional path to keep the raw capture output

set -eu

SCRIPT_DIRECTORY=$(
    CDPATH= cd -- "$(dirname -- "$0")"
    pwd
)

REPOSITORY_ROOT=$(
    CDPATH= cd -- "${SCRIPT_DIRECTORY}/.."
    pwd
)

COMPOSE_FILE="${REPOSITORY_ROOT}/vehicle-simulator/docker-compose.v1.yml"
COMPOSE_NETWORK="qa-sdv-v1_default"
TICK="${PUBLISH_INTERVAL_SECONDS:-5}"
PROVIDER="${PROVIDER_002_URL:-http://localhost:8092}"
ACTIONS_URL="${PROVIDER}/api/v1/scenarios/actions"
CONTEXT_URL="${PROVIDER}/api/v1/vehicles/vehicle-002/scenarios/LIDAR_OBSTRUCTION"
CAPTURE_NAME="v1-lidar-cycle-capture-$$"

WORK_DIRECTORY=$(mktemp -d)
CAPTURE_LOG="${WORK_DIRECTORY}/capture.log"
RESPONSE_FILE="${WORK_DIRECTORY}/response.json"
SCENARIO_ACTIVE=0
CAPTURE_PID=""


seconds() {
    awk "BEGIN { print $1 * ${TICK} }"
}

post_action() {
    # $1 vehicleId, $2 action, $3 actionId; prints the HTTP status code.
    curl -sS -o "${RESPONSE_FILE}" -w '%{http_code}' \
        -X POST \
        -H "Content-Type: application/json" \
        -d "{\"vehicleId\":\"$1\",\"action\":\"$2\",\"scenario\":\"LIDAR_OBSTRUCTION\",\"actionId\":\"$3\",\"traceId\":\"$3\"}" \
        "${ACTIONS_URL}"
}

cleanup() {
    if [ "${SCENARIO_ACTIVE}" = "1" ]; then
        echo "Clearing the injected scenario before exit"
        post_action vehicle-002 CLEAR_SCENARIO e2-cycle-clear-trap \
            >/dev/null 2>&1 || true
    fi

    docker rm -f "${CAPTURE_NAME}" >/dev/null 2>&1 || true
    rm -rf "${WORK_DIRECTORY}"
}

trap cleanup EXIT
trap 'exit 130' INT TERM

fail() {
    echo "FAIL: $*" >&2
    exit 1
}


# 1. Preflight: the stack must be up before anything is injected.
RUNNING=$(docker compose -f "${COMPOSE_FILE}" ps --status running --services 2>/dev/null || true)

for service in mqtt provider-001 provider-002 app-001 app-002; do
    if ! printf '%s\n' "${RUNNING}" | grep -qx "${service}"; then
        echo "Service ${service} is not running." >&2
        echo "Start the stack first: docker compose -f vehicle-simulator/docker-compose.v1.yml up -d --build" >&2
        exit 1
    fi
done

curl -fsS "${PROVIDER}/health" >/dev/null || fail "provider-002 is not answering at ${PROVIDER}"


# 2. Capture both vehicles' events with the cycle oracle.
CAPTURE_TIMEOUT=$(awk "BEGIN { print int(12 * ${TICK} + 30) }")
echo "Starting capture (timeout ${CAPTURE_TIMEOUT}s, tick ${TICK}s)"

docker run --rm --name "${CAPTURE_NAME}" \
    --network "${COMPOSE_NETWORK}" \
    -v "${REPOSITORY_ROOT}:/repo:ro" \
    -w /repo \
    python:3.12-slim \
    sh -c "apt-get update -qq >/dev/null && apt-get install -y -qq mosquitto-clients >/dev/null 2>&1 && python -B -m scripts.v1_dev.mqtt capture --host mqtt --port 1883 --expect-cycle --timeout ${CAPTURE_TIMEOUT}" \
    >"${CAPTURE_LOG}" 2>&1 &
CAPTURE_PID=$!


# 3. Wait until the capture has seen vehicle-002 healthy (the oracle needs
#    a healthy event before the fault).
waited=0
until grep -q '"vehicleId": "vehicle-002".*"health": "HEALTHY"' "${CAPTURE_LOG}" 2>/dev/null; do
    if ! kill -0 "${CAPTURE_PID}" 2>/dev/null; then
        cat "${CAPTURE_LOG}" >&2
        fail "capture stopped before vehicle-002 was seen healthy"
    fi
    if [ "${waited}" -ge 120 ]; then
        fail "no healthy vehicle-002 event within 120 s"
    fi
    sleep 1
    waited=$((waited + 1))
done
echo "Capture ready: vehicle-002 seen HEALTHY"


# 4. Inject, hold for four ticks, read the context, clear, wait four ticks.
#    Mark the scenario active before sending: the provider may apply the
#    inject even if this script then fails, and CLEAR is idempotent.
SCENARIO_ACTIVE=1
status=$(post_action vehicle-002 INJECT_SCENARIO e2-cycle-inject)
[ "${status}" = "200" ] && grep -q '"active": true' "${RESPONSE_FILE}" \
    || fail "inject returned ${status}: $(cat "${RESPONSE_FILE}")"
echo "Injected: $(cat "${RESPONSE_FILE}")"

sleep "$(seconds 4)"
echo "Context: $(curl -sS "${CONTEXT_URL}")"

status=$(post_action vehicle-002 CLEAR_SCENARIO e2-cycle-clear)
[ "${status}" = "200" ] && grep -q '"active": false' "${RESPONSE_FILE}" \
    || fail "clear returned ${status}: $(cat "${RESPONSE_FILE}")"
SCENARIO_ACTIVE=0
echo "Cleared: $(cat "${RESPONSE_FILE}")"

sleep "$(seconds 4)"


# 5. provider-002 must refuse a command for vehicle-001.
status=$(post_action vehicle-001 INJECT_SCENARIO e2-cycle-wrong-vehicle)
[ "${status}" = "409" ] || fail "wrong-vehicle request returned ${status}, expected 409"
echo "Wrong vehicle rejected (409): $(cat "${RESPONSE_FILE}")"


# 6. Let the capture finish and judge the result.
echo "Waiting for the capture to finish"
capture_status=0
wait "${CAPTURE_PID}" || capture_status=$?

if [ -n "${E2_CAPTURE_OUT:-}" ]; then
    cp "${CAPTURE_LOG}" "${E2_CAPTURE_OUT}"
    echo "Capture saved to ${E2_CAPTURE_OUT}"
fi

result=$(tail -n 1 "${CAPTURE_LOG}")
echo "Capture result: ${result}"

if [ "${capture_status}" -ne 0 ]; then
    fail "capture exited ${capture_status}"
fi

printf '%s\n' "${result}" | grep -q '"cycleComplete": true' \
    || fail "cycle incomplete"

echo "PASS: vehicle-002 fault and recovery observed; vehicle-001 stayed HEALTHY"
