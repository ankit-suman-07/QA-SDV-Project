import asyncio
import json
import logging
import os
import signal

from health_logic import build_status_event
from kuksa_client.grpc import VSSClient
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

    def read_signals(self):
        values = self._kuksa_client.get_current_values(
            MONITORED_SIGNAL_PATHS
        )

        return {
            signal_path: values[signal_path].value
            for signal_path in MONITORED_SIGNAL_PATHS
        }

    async def monitor_signals(self):
        while True:
            try:
                signals = await asyncio.to_thread(
                    self.read_signals
                )

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