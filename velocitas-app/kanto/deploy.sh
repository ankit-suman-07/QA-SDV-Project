#!/bin/sh

set -eu

APP_NAME="autonomoushealthapp"
LOCAL_IMAGE="qa-sdv-autonomous-health-app:local"
KANTO_IMAGE="localhost:12345/${APP_NAME}:local"
REGISTRY_CONTAINER="qa-sdv-kanto-registry"

SCRIPT_DIRECTORY=$(
    CDPATH= cd -- "$(dirname -- "$0")"
    pwd
)

REPOSITORY_ROOT=$(
    CDPATH= cd -- "${SCRIPT_DIRECTORY}/../.."
    pwd
)

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is required."
    exit 1
fi

if ! command -v kanto-cm >/dev/null 2>&1; then
    echo "kanto-cm is required."
    echo "Run this script on a Linux Kanto target."
    exit 1
fi

echo "Building Velocitas vehicle application..."

docker build \
    -t "${LOCAL_IMAGE}" \
    -f "${REPOSITORY_ROOT}/velocitas-app/app/Dockerfile" \
    "${REPOSITORY_ROOT}/velocitas-app"

if docker container inspect \
    "${REGISTRY_CONTAINER}" \
    >/dev/null 2>&1
then
    if [ "$(
        docker container inspect \
            -f '{{.State.Running}}' \
            "${REGISTRY_CONTAINER}"
    )" != "true" ]
    then
        docker start "${REGISTRY_CONTAINER}"
    fi
else
    docker run \
        -d \
        -p 12345:5000 \
        --restart unless-stopped \
        --name "${REGISTRY_CONTAINER}" \
        registry:2
fi

docker tag \
    "${LOCAL_IMAGE}" \
    "${KANTO_IMAGE}"

docker push "${KANTO_IMAGE}"

if kanto-cm get \
    -n "${APP_NAME}" \
    >/dev/null 2>&1
then
    kanto-cm remove \
        -f \
        -n "${APP_NAME}"
fi

kanto-cm create \
    --i \
    --t \
    --network host \
    --e "SDV_MIDDLEWARE_TYPE=native" \
    --e \
    "SDV_VEHICLEDATABROKER_ADDRESS=grpc://127.0.0.1:55555" \
    --e \
    "SDV_MQTT_ADDRESS=mqtt://127.0.0.1:1883" \
    --e "DATABROKER_HOST=127.0.0.1" \
    --e "DATABROKER_PORT=55555" \
    --e "SIMULATED_VEHICLE_ID=vehicle-001" \
    --e \
    "AUTONOMOUS_HEALTH_POLL_INTERVAL_SECONDS=2.0" \
    -n "${APP_NAME}" \
    "${KANTO_IMAGE}"

kanto-cm start \
    -n "${APP_NAME}"

echo "Kanto deployment completed."

kanto-cm get \
    -n "${APP_NAME}"