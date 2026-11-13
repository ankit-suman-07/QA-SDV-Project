import json
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from threading import Thread

from scenario_controller import WrongVehicleError


def create_request_handler(controller):

    class ControlRequestHandler(BaseHTTPRequestHandler):

        def do_GET(self):
            if self.path == "/health":
                self._write_json(
                    200,
                    {"status": "UP"},
                )
                return

            path_parts = self.path.strip("/").split("/")

            if (
                len(path_parts) == 6
                and path_parts[0] == "api"
                and path_parts[1] == "v1"
                and path_parts[2] == "vehicles"
                and path_parts[4] == "scenarios"
            ):
                vehicle_id = path_parts[3]
                scenario = path_parts[5]

                try:
                    state = controller.get_state(
                        vehicle_id=vehicle_id,
                        scenario=scenario,
                    )
                    self._write_json(200, state)
                except WrongVehicleError as exception:
                    self._reject_wrong_vehicle(
                        controller,
                        vehicle_id,
                        exception,
                    )
                except ValueError as exception:
                    self._write_json(
                        400,
                        {"error": str(exception)},
                    )

                return

            self._write_json(
                404,
                {"error": "Endpoint not found"},
            )

        def do_POST(self):
            if self.path != "/api/v1/scenarios/actions":
                self._write_json(
                    404,
                    {"error": "Endpoint not found"},
                )
                return

            try:
                request_body = self._read_request_body()

                payload = json.loads(
                    request_body.decode("utf-8")
                )

                result = controller.execute(
                    vehicle_id=payload["vehicleId"],
                    action=payload["action"],
                    scenario=payload["scenario"],
                    action_id=payload["actionId"],
                    trace_id=payload["traceId"],
                )

                self._write_json(200, result)

            except WrongVehicleError as exception:
                self._reject_wrong_vehicle(
                    controller,
                    payload.get("vehicleId"),
                    exception,
                )

            except (
                ValueError,
                TypeError,
                KeyError,
                json.JSONDecodeError,
            ) as exception:
                self._write_json(
                    400,
                    {"error": str(exception)},
                )

        def _read_request_body(self):
            transfer_encoding = self.headers.get(
                "Transfer-Encoding",
                "",
            ).lower()

            if "chunked" in transfer_encoding:
                request_body = bytearray()

                while True:
                    chunk_header = (
                        self.rfile.readline().strip()
                    )

                    if not chunk_header:
                        raise ValueError(
                            "Invalid chunked request body"
                        )

                    chunk_size = int(
                        chunk_header.split(b";", 1)[0],
                        16,
                    )

                    if chunk_size == 0:
                        while True:
                            trailer = self.rfile.readline()

                            if trailer in (
                                b"\r\n",
                                b"\n",
                                b"",
                            ):
                                break

                        break

                    request_body.extend(
                        self.rfile.read(chunk_size)
                    )

                    self.rfile.read(2)

                return bytes(request_body)

            content_length = int(
                self.headers.get("Content-Length", "0")
            )

            return self.rfile.read(content_length)

        def _reject_wrong_vehicle(
            self,
            controller,
            requested_vehicle_id,
            exception,
        ):
            print(
                "[Control] rejected "
                f"vehicle={requested_vehicle_id!r} "
                f"configured={controller.allowed_vehicle_id}",
                flush=True,
            )
            self._write_json(
                409,
                {"error": str(exception)},
            )

        def _write_json(self, status_code, payload):
            response_body = json.dumps(payload).encode(
                "utf-8"
            )

            self.send_response(status_code)
            self.send_header(
                "Content-Type",
                "application/json",
            )
            self.send_header(
                "Content-Length",
                str(len(response_body)),
            )
            self.end_headers()
            self.wfile.write(response_body)

        def log_message(self, format, *args):
            return

    return ControlRequestHandler


def start_control_server(
    controller,
    host="0.0.0.0",
    port=8090,
):
    server = ThreadingHTTPServer(
        (host, port),
        create_request_handler(controller),
    )

    server_thread = Thread(
        target=server.serve_forever,
        name="simulator-control-server",
        daemon=True,
    )
    server_thread.start()

    return server