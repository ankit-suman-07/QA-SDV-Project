#!/usr/bin/env python3

import base64
import csv
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT_DIR = Path(__file__).resolve().parents[1]

BACKEND_ACTION_URL = (
    "http://localhost:8082/"
    "api/v1/diagnostics/actions"
)

DITTO_THING_URL = (
    "http://localhost:8080/api/2/things/"
    "sdv:vehicle-001"
)

RESULTS_FILE = (
    ROOT_DIR
    / "experiments"
    / "results"
    / "iteration3-full-pipeline-latency.csv"
)

VEHICLE_ID = "vehicle-001"
SCENARIO = "COOLING_SYSTEM_FAILURE"


def request_json(
        url,
        method="GET",
        payload=None,
        headers=None,
):
    request_headers = dict(headers or {})
    body = None

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = (
            "application/json"
        )

    request = Request(
        url=url,
        data=body,
        headers=request_headers,
        method=method,
    )

    try:
        with urlopen(
            request,
            timeout=10,
        ) as response:
            return json.load(response)

    except HTTPError as exception:
        response_body = exception.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            f"HTTP {exception.code} from {url}: "
            f"{response_body}"
        ) from exception

    except URLError as exception:
        raise RuntimeError(
            f"Could not reach {url}: "
            f"{exception.reason}"
        ) from exception


def ditto_headers():
    credentials = base64.b64encode(
        b"ditto:ditto"
    ).decode("ascii")

    return {
        "Authorization": f"Basic {credentials}",
    }


def get_ditto_thing():
    return request_json(
        DITTO_THING_URL,
        headers=ditto_headers(),
    )


def get_health_status(thing):
    return (
        thing["features"]["health"]
        ["properties"]["status"]
    )


def wait_for_health(
        expected_status,
        timeout_seconds=120,
):
    deadline = time.monotonic() + timeout_seconds
    last_status = None

    while time.monotonic() < deadline:
        thing = get_ditto_thing()
        last_status = get_health_status(thing)

        print(
            f"\rWaiting for {expected_status}: "
            f"current={last_status}",
            end="",
            flush=True,
        )

        if last_status == expected_status:
            print()
            return thing

        time.sleep(0.5)

    print()

    raise TimeoutError(
        f"Ditto did not reach {expected_status}; "
        f"last status was {last_status}"
    )

def wait_for_correlated_fault(
        expected_action_id,
        timeout_seconds=120,
):
    deadline = time.monotonic() + timeout_seconds
    last_status = None
    detail_count = 0

    while time.monotonic() < deadline:
        thing = get_ditto_thing()

        last_status = get_health_status(thing)

        fault_details = (
            thing["features"]["diagnostics"]
            ["properties"]
            ["activeFaultDetails"]
        )

        detail_count = len(fault_details)

        matching_detail = next(
            (
                detail
                for detail in fault_details
                if detail.get("actionId")
                == expected_action_id
            ),
            None,
        )

        print(
            "\rWaiting for correlated fault: "
            f"health={last_status}, "
            f"details={detail_count}",
            end="",
            flush=True,
        )

        if (
            last_status == "CRITICAL"
            and matching_detail is not None
        ):
            print()
            return thing

        time.sleep(0.5)

    print()

    raise TimeoutError(
        "Correlated fault was not fully stored; "
        f"last health={last_status}, "
        f"detail count={detail_count}"
    )

def submit_action(action):
    return request_json(
        BACKEND_ACTION_URL,
        method="POST",
        payload={
            "vehicleId": VEHICLE_ID,
            "action": action,
            "scenario": SCENARIO,
        },
    )


def append_result(
        started_at,
        inject_action_id,
        clear_action_id,
        detection_latency_ms,
        recovery_latency_ms,
):
    file_exists = RESULTS_FILE.exists()

    RESULTS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with RESULTS_FILE.open(
        "a",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "started_at",
                "inject_action_id",
                "clear_action_id",
                "detection_latency_ms",
                "recovery_latency_ms",
            ],
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow(
            {
                "started_at": started_at,
                "inject_action_id": (
                    inject_action_id
                ),
                "clear_action_id": (
                    clear_action_id
                ),
                "detection_latency_ms": (
                    f"{detection_latency_ms:.3f}"
                ),
                "recovery_latency_ms": (
                    f"{recovery_latency_ms:.3f}"
                ),
            }
        )


def show_opensovd_mapping():
    print()
    print("OpenSOVD-compatible mapped fault:")

    subprocess.run(
        [
            sys.executable,
            str(
                ROOT_DIR
                / "opensovd"
                / "scripts"
                / "map-active-faults.py"
            ),
        ],
        cwd=ROOT_DIR,
        check=False,
    )


def main():
    print("Checking initial Ditto state...")

    initial_thing = get_ditto_thing()
    initial_status = get_health_status(
        initial_thing
    )

    if initial_status != "HEALTHY":
        raise RuntimeError(
            "Demo must begin in HEALTHY state; "
            f"current state is {initial_status}"
        )

    print("Initial state: HEALTHY")
    print()
    print("Submitting INJECT_SCENARIO...")

    started_at = datetime.now(
        timezone.utc
    ).isoformat()

    detection_start = time.monotonic()
    inject_response = submit_action(
        "INJECT_SCENARIO"
    )

    print(
        json.dumps(
            inject_response,
            indent=2,
        )
    )

    critical_thing = wait_for_correlated_fault(
        inject_response["actionId"]
    )

    detection_latency_ms = (
        time.monotonic() - detection_start
    ) * 1000

    fault_details = (
        critical_thing["features"]
        ["diagnostics"]["properties"]
        ["activeFaultDetails"]
    )

    if not fault_details:
        raise RuntimeError(
            "CRITICAL state has no "
            "activeFaultDetails"
        )

    fault_detail = fault_details[0]

    action_id_matches = (
        fault_detail.get("actionId")
        == inject_response.get("actionId")
    )

    trace_id_matches = (
        fault_detail.get("traceId")
        == inject_response.get("traceId")
    )

    print()
    print(
        "Correlated fault detected in "
        f"{detection_latency_ms:.3f} ms"
    )
    print(
        f"actionId matches: {action_id_matches}"
    )
    print(
        f"traceId matches: {trace_id_matches}"
    )

    if not (
        action_id_matches
        and trace_id_matches
    ):
        raise RuntimeError(
            "Fault trace identifiers do not "
            "match the submitted action"
        )

    show_opensovd_mapping()

    print()
    print(
        "Holding CRITICAL state for "
        "three seconds..."
    )
    time.sleep(3)

    print("Submitting CLEAR_SCENARIO...")

    recovery_start = time.monotonic()
    clear_response = submit_action(
        "CLEAR_SCENARIO"
    )

    print(
        json.dumps(
            clear_response,
            indent=2,
        )
    )

    healthy_thing = wait_for_health(
        "HEALTHY"
    )

    recovery_latency_ms = (
        time.monotonic() - recovery_start
    ) * 1000

    active_faults = (
        healthy_thing["features"]["health"]
        ["properties"]["activeFaults"]
    )

    active_fault_details = (
        healthy_thing["features"]
        ["diagnostics"]["properties"]
        ["activeFaultDetails"]
    )

    if active_faults or active_fault_details:
        raise RuntimeError(
            "Fault records were not cleared "
            "after recovery"
        )

    append_result(
        started_at=started_at,
        inject_action_id=(
            inject_response["actionId"]
        ),
        clear_action_id=(
            clear_response["actionId"]
        ),
        detection_latency_ms=(
            detection_latency_ms
        ),
        recovery_latency_ms=(
            recovery_latency_ms
        ),
    )

    print()
    print(
        "Recovery completed in "
        f"{recovery_latency_ms:.3f} ms"
    )
    print("Final state: HEALTHY")
    print(
        f"Result saved to: {RESULTS_FILE}"
    )
    print()
    print("DEMO SCENARIO PASSED")


if __name__ == "__main__":
    main()