import asyncio
import json
import logging
import os
import signal

from health_logic import build_status_event
from kuksa_client.grpc import VSSClient
from kuksa_reconnect import reconnect
from v1_event import (
    ObservationGate,
    observation_from_datapoints,
    topic,
)
from v1_publisher import deliver, pub_client_of
from vehicle import Vehicle, vehicle  # type: ignore
from velocitas_sdk.util.log import (  # type: ignore
    get_opentelemetry_log_factory,
    get_opentelemetry_log_format,
)
from velocitas_sdk.vehicle_app import VehicleApp


logging.setLogRecordFactory(
    get_opentelemetry_log_factory()
)
logging.basicConfig(
    format=get_opentelemetry_log_format()
)
logging.getLogger().setLevel("INFO")
logger = logging.getLogger(__name__)

STATUS_TOPIC = "sdv/autonomy/status"

VEHICLE_ID = os.getenv(
    "SIMULATED_VEHICLE_ID",
    "vehicle-001",
).strip()

DATABROKER_HOST = os.getenv(
    "DATABROKER_HOST",
    "databroker",
).strip()

DATABROKER_PORT = int(
    os.getenv(
        "DATABROKER_PORT",
        "55555",
    )
)

POLL_INTERVAL_SECONDS = float(
    os.getenv(
        "AUTONOMOUS_HEALTH_POLL_INTERVAL_SECONDS",
        "2.0",
    )
)

SPEED_PATH = "Vehicle.Speed"

LIDAR_DISTANCE_PATH = (
    "Vehicle.Automation.Lidar.Front."
    "NearestObstacleDistance"
)

LIDAR_HEALTH_PATH = (
    "Vehicle.Automation.Lidar.Front.IsHealthy"
)

OBSTACLE_WARNING_PATH = (
    "Vehicle.Automation.ObstacleWarning.IsActive"
)

AUTONOMOUS_BRAKING_PATH = (
    "Vehicle.Automation.AutonomousBraking.IsActive"
)

V1_SKIP_MESSAGES = {
    "incomplete": "LiDAR value or timestamp missing in KUKSA",
    "invalid": "LiDAR reading is invalid (bad distance or naive timestamp)",
    "older": "observation time went backwards; check the broker clock",
}

MONITORED_SIGNAL_PATHS = [
    SPEED_PATH,
    LIDAR_DISTANCE_PATH,
    LIDAR_HEALTH_PATH,
    OBSTACLE_WARNING_PATH,
    AUTONOMOUS_BRAKING_PATH,
]


class AutonomousHealthApp(VehicleApp):

    def __init__(self, vehicle_client: Vehicle):
        super().__init__()
        self.Vehicle = vehicle_client
        self._kuksa_client = VSSClient(
            DATABROKER_HOST,
            DATABROKER_PORT,
        )
        self._monitor_task = None
        self._kuksa_reconnect_needed = False
        self._v1_gate = ObservationGate(VEHICLE_ID)
        self._v1_topic = topic(VEHICLE_ID)
        self._v1_last_skip_logged = None
        # QoS 1 publisher for v1 events (the SDK's publish_event sends QoS 0).
        self._v1_mqtt = pub_client_of(self.pubsub_client)

    async def on_start(self):
        logger.info(
            "Starting autonomous health monitoring "
            "for vehicle=%s",
            VEHICLE_ID,
        )

        await asyncio.to_thread(
            self._kuksa_client.connect
        )

        self._monitor_task = asyncio.create_task(
            self.monitor_signals()
        )

    def read_datapoints(self):
        """Current KUKSA datapoints (value + broker timestamp) by path."""
        return self._kuksa_client.get_current_values(
            MONITORED_SIGNAL_PATHS
        )

    async def reconnect_kuksa_if_needed(self):
        if not self._kuksa_reconnect_needed:
            return
        try:
            await asyncio.to_thread(
                reconnect,
                self._kuksa_client,
            )
            self._kuksa_reconnect_needed = False
            logger.info("Reconnected to KUKSA databroker")
        except Exception:
            logger.exception(
                "KUKSA reconnect failed; retrying next poll"
            )

    async def publish_v1(self, datapoints):
        """Publish a contract v1 health event when there is a new reading.

        sourceTimestamp is the broker timestamp of the LiDAR reading, never
        the poll or publish time. Events go out at QoS 1, retain=false; one
        that is not acknowledged stays pending and is retried unchanged
        (same eventId and sourceTimestamp) on the next poll.
        """
        observation = observation_from_datapoints(
            datapoints.get(LIDAR_DISTANCE_PATH),
            datapoints.get(LIDAR_HEALTH_PATH),
        )
        event = self._v1_gate.next_event(observation)

        skip = self._v1_gate.last_skip
        if skip != self._v1_last_skip_logged:
            if skip is not None:
                logger.warning(
                    "v1: not publishing (%s): %s",
                    skip,
                    V1_SKIP_MESSAGES[skip],
                )
            self._v1_last_skip_logged = skip

        if event is None:
            return

        if not await deliver(
            self._v1_gate,
            event,
            self._v1_mqtt,
            self._v1_topic,
        ):
            logger.warning(
                "v1: publish not acknowledged; will retry eventId=%s",
                event["eventId"],
            )
            return

        logger.info(
            "v1: published topic=%s eventId=%s health=%s "
            "sourceTimestamp=%s",
            self._v1_topic,
            event["eventId"],
            event["health"],
            event["sourceTimestamp"],
        )

    async def monitor_signals(self):
        while True:
            await self.reconnect_kuksa_if_needed()

            try:
                datapoints = await asyncio.to_thread(
                    self.read_datapoints
                )
            except Exception:
                logger.exception(
                    "Failed to read KUKSA signals"
                )
                self._kuksa_reconnect_needed = True
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                continue

            try:
                signals = {
                    signal_path: datapoints[signal_path].value
                    for signal_path in MONITORED_SIGNAL_PATHS
                }

                event = build_status_event(
                    vehicle_id=VEHICLE_ID,
                    speed=signals[SPEED_PATH],
                    lidar_distance_m=signals[
                        LIDAR_DISTANCE_PATH
                    ],
                    lidar_sensor_healthy=signals[
                        LIDAR_HEALTH_PATH
                    ],
                    obstacle_warning=signals[
                        OBSTACLE_WARNING_PATH
                    ],
                    autonomous_braking=signals[
                        AUTONOMOUS_BRAKING_PATH
                    ],
                )

                event_json = json.dumps(event)

                await self.publish_event(
                    STATUS_TOPIC,
                    event_json,
                )

                logger.info(
                    "Published autonomous status: %s",
                    event_json,
                )

            except Exception:
                logger.exception(
                    "Failed to evaluate autonomous signals"
                )

            try:
                await self.publish_v1(datapoints)
            except Exception:
                logger.exception(
                    "v1: failed to publish health event"
                )

            await asyncio.sleep(
                POLL_INTERVAL_SECONDS
            )


async def main():
    logger.info(
        "Launching Velocitas AutonomousHealthApp"
    )

    app = AutonomousHealthApp(vehicle)
    await app.run()


LOOP = asyncio.get_event_loop()
LOOP.add_signal_handler(
    signal.SIGTERM,
    LOOP.stop,
)
LOOP.run_until_complete(main())
LOOP.close()