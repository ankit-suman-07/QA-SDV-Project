import json
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from threading import Thread


def create_request_handler(controller):

    class ControlRequestHandler(BaseHTTPRequestHandler):

        def do_GET(self):
            if self.path != "/health":
                self._write_json(
                    404,
                    {"error": "Endpoint not found"},
                )
                return

            self._write_json(
                200,
                {"status": "UP"},
            )

        def do_POST(self):
            if self.path != "/api/v1/scenarios/actions":
                self._write_json(
                    404,
                    {"error": "Endpoint not found"},
                )
                return

            try:
                content_length = int(
                    self.headers.get("Content-Length", "0")
                )
                request_body = self.rfile.read(
                    content_length
                )
                payload = json.loads(
                    request_body.decode("utf-8")
                )

                result = controller.execute(
                    action=payload["action"],
                    scenario=payload["scenario"],
                    action_id=payload["actionId"],
                    trace_id=payload["traceId"],
                )

                self._write_json(200, result)

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