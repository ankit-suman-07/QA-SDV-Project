#!/bin/sh
# Run three CARLA vehicles with front LiDAR and write V2 observations.
# Prerequisite: CARLA 0.9.15 running on CARLA_HOST:2000 with Town10HD_Opt loaded.
#
#   sh carla-bridge/run-fleet.sh [out-dir]
#
# Environment passed through: DURATION_SECONDS, SPAWN_POINTS, DRIVE, SEED,
# EXPECT_MAP, CARLA_HOST, CARLA_PORT.

set -eu

BRIDGE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
OUT=${1:-"${BRIDGE}/runs/$(date -u +%Y%m%dT%H%M%SZ)"}
IMAGE="qa-sdv-carla-client:0.9.15"

STATE="${BRIDGE}/state"   # persisted session generation; git-ignored
mkdir -p "${OUT}" "${STATE}"
OUT=$(CDPATH= cd -- "${OUT}" && pwd)
docker build --platform linux/amd64 -q -t "${IMAGE}" "${BRIDGE}" >/dev/null

docker run --rm --platform linux/amd64 \
    --add-host host.docker.internal:host-gateway \
    -v "${OUT}:/out" \
    -v "${STATE}:/state" \
    -e CARLA_HOST="${CARLA_HOST:-host.docker.internal}" \
    -e CARLA_PORT="${CARLA_PORT:-2000}" \
    -e DURATION_SECONDS="${DURATION_SECONDS:-30}" \
    -e SPAWN_POINTS="${SPAWN_POINTS:-1,2,3}" \
    -e DRIVE="${DRIVE:-0}" \
    -e SEED="${SEED:-7}" \
    -e EXPECT_MAP="${EXPECT_MAP:-Town10HD_Opt}" \
    "${IMAGE}"

echo "Run output: ${OUT}"
