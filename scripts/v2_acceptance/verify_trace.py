"""Verify saved V2 boundary captures. This command makes no network calls."""

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

from scripts.v1_dev.contract import decode_event, parse_timestamp
from scripts.v2_dev.contract import VEHICLES
from scripts.v2_dev.observation_mapping import prepare_observation

BOUNDARIES = ("source", "kuksa", "companion", "health", "twin", "api", "browser")


class MissingCapture(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ValueError(message)


def observation_key(payload, boundary):
    vehicle = payload.get("vehicleId")
    event = payload.get("lastEventId" if boundary in {"twin", "api", "browser"} else "eventId")
    require(vehicle in VEHICLES and isinstance(event, str) and event.strip(), "invalid vehicle/event identity")
    return vehicle, event


def matches_context(source, actual, boundary):
    fields = ("sourceTimestamp", "sessionId", "sessionGeneration", "sequence", "frame")
    if boundary in {"browser", "kuksa"}:
        fields = ("sourceTimestamp",)
    return all(actual.get(key) == source[key] for key in fields)


def check_join(bucket, manifest, synthetic):
    source = bucket["source"]
    expected_origin = "SYNTHETIC" if synthetic else "CARLA"
    prepared = prepare_observation(json.dumps(source), vehicle_id=source["vehicleId"], manifest=manifest,
                                   now=parse_timestamp(source["sourceTimestamp"]))
    require(source.get("provenance") == expected_origin, "source has incorrect provenance for this run")
    require(bucket["companion"] == source, "companion changed the source envelope")
    for boundary in BOUNDARIES[1:]:
        require(matches_context(source, bucket[boundary], boundary), f"{boundary} changed observation context")

    _, expected_signals = prepared
    kuksa = bucket["kuksa"]
    values = kuksa.get("signals")
    require(kuksa.get("allWritesConfirmed") is True and isinstance(values, dict)
            and set(values) == set(expected_signals), "incomplete KUKSA confirmation")
    for path, expected in expected_signals.items():
        actual = values[path]
        matches = actual is expected if isinstance(expected, bool) else (
            type(actual) in (float, int) and math.isclose(actual, expected, rel_tol=1e-6, abs_tol=1e-7))
        require(matches, f"KUKSA value mismatch at {path}")

    for boundary in ("twin", "api", "browser"):
        require(bucket[boundary].get("thingId") == f"sdv:{source['vehicleId']}",
                f"{boundary} used the wrong Thing")
    health = bucket["health"]
    for boundary in ("health", "twin", "api"):
        sample = bucket[boundary]
        require(sample.get("lidar") == source["lidar"], f"{boundary} LiDAR mismatch")
        state = sample.get("healthStatus" if boundary == "api" else "health")
        faults = sample.get("activeFaults" if boundary == "api" else "faults")
        require(state in {"HEALTHY", "WARNING", "CRITICAL"} and state == health["health"]
                and isinstance(faults, list) and faults == health["faults"], f"{boundary} health mismatch")
        require(sample.get("recoveryState") in {"NONE", "IN_PROGRESS"}
                and sample["recoveryState"] == health["recoveryState"]
                and "recoveryStartedAt" in sample and sample["recoveryStartedAt"] == health["recoveryStartedAt"]
                and type(sample.get("sourceSilent")) is bool
                and sample["sourceSilent"] is health["sourceSilent"], f"{boundary} recovery/silence mismatch")
    api, browser = bucket["api"], bucket["browser"]
    require(api.get("availability") in {"AVAILABLE", "STALE", "UNAVAILABLE"}
            and browser.get("availability") == api["availability"]
            and browser.get("healthStatus") == api["healthStatus"]
            and browser.get("recoveryState") == api["recoveryState"], "browser does not match individual API render")


def verify(manifest, captures, vehicles, *, synthetic=False):
    require(isinstance(manifest, dict) and isinstance(manifest.get("vehicles"), list), "invalid run manifest")
    if not synthetic:
        require("fixtureLabel" not in manifest, "fixture manifest cannot be used for live evidence")
    rows = manifest["vehicles"]
    require(len(rows) == 3 and {row["vehicleId"] for row in rows} == set(VEHICLES), "manifest requires all three mappings")
    require(len({(row["broker"], row["brokerPort"]) for row in rows}) == 3, "broker endpoints must be distinct")
    require(len({row["actorId"] for row in rows}) == 3 and len({row["sensorId"] for row in rows}) == 3,
            "actor and sensor mappings must be distinct")
    for row in rows:
        require(row["twinId"] == f"sdv:{row['vehicleId']}", "incorrect twin mapping")

    records = defaultdict(dict)
    for capture in captures:
        boundary = capture["boundary"]
        payload = capture["payload"]
        require(boundary in BOUNDARIES and isinstance(payload, dict), "invalid capture record")
        if not synthetic:
            require(not (payload.get("mock") or "fixtureLabel" in payload or payload.get("provenance") == "SYNTHETIC"),
                    "mock or fixture capture in live input")
        identity = observation_key(payload, boundary)
        if boundary in {"companion", "health"}:
            suffix = "observations" if boundary == "companion" else "health"
            require(capture.get("topic") == f"sdv/{identity[0]}/v2/{suffix}", f"{boundary} topic mismatch")
        bucket = records[identity]
        require(boundary not in bucket or bucket[boundary] == payload, f"conflicting {boundary} capture")
        bucket[boundary] = payload

    matched = defaultdict(list)
    for (vehicle, event), bucket in records.items():
        if vehicle in vehicles and all(boundary in bucket for boundary in BOUNDARIES):
            check_join(bucket, manifest, synthetic)
            matched[vehicle].append(event)
    missing = [vehicle for vehicle in vehicles if not matched[vehicle]]
    if missing:
        raise MissingCapture("no complete identity join for " + ", ".join(missing))
    return dict(matched)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--vehicle", choices=VEHICLES)
    target.add_argument("--all-vehicles", action="store_true")
    parser.add_argument("--synthetic", action="store_true", help="label captured fixture data as offline")
    args = parser.parse_args(argv)
    try:
        with args.trace.open("rb") as trace:
            matched = verify(decode_event(args.manifest.read_bytes()),
                             (decode_event(line) for line in trace if line.strip()),
                             VEHICLES if args.all_vehicles else [args.vehicle], synthetic=args.synthetic)
    except (MissingCapture, FileNotFoundError) as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        return 2
    except (ValueError, KeyError, TypeError, OSError, OverflowError) as error:
        print(f"FAILED: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"status": "PASS", "scope": "synthetic join" if args.synthetic else "supplied capture join only",
                      "matchedEvents": matched}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
