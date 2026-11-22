"""Summarize bounded V2 trials from captured identities and UTC timestamps."""

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

from scripts.v1_dev.contract import parse_timestamp
from scripts.v2_acceptance.verify_trace import require
from scripts.v2_dev.contract import VEHICLES

STAGES = ("companion", "health", "twin", "api", "browser")
OUTCOMES = {"PASS", "FAILED", "TIMED_OUT"}


def distribution(values):
    if not values:
        return {"n": 0}
    return {
        "n": len(values),
        "min": min(values),
        "median": statistics.median(values),
        "max": max(values),
        "sampleStdDev": statistics.stdev(values) if len(values) > 1 else None,
    }


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def first_seen(rows, *, source=False):
    result = {}
    for row in rows:
        vehicle, event = row["vehicleId"], row["eventId"]
        require(vehicle in VEHICLES and isinstance(event, str) and event.strip(), "invalid observation identity")
        key = (vehicle, event)
        timestamp = parse_timestamp(row["sourceTimestamp" if source else "observedAt"])
        if key in result:
            require(not source or timestamp == result[key], "source retry changed source timestamp")
            result[key] = min(result[key], timestamp)
        else:
            result[key] = timestamp
    return result


def summarize_trial(trial, uncertainty):
    require(trial["status"] in OUTCOMES and trial["target"] in VEHICLES, "invalid trial status or target")
    require(bool(trial.get("reason")) or trial["status"] == "PASS", "record the trial failure or timeout reason")
    opened = parse_timestamp(trial["windowStart"])
    closed = parse_timestamp(trial["windowEnd"])
    require(closed > opened, "trial window is empty or reversed")
    source = first_seen(trial["source"], source=True)
    require(all(opened <= at <= closed for at in source.values()), "source outside the trial window")
    stages = trial["stages"]
    require(stages.keys() <= set(STAGES), "unknown measurement stage")
    timings = {}
    excluded = []

    def interval_samples(metric, pairs):
        values = []
        for key, start, end in pairs:
            delta = (end - start).total_seconds() * 1000
            if delta < -uncertainty:
                excluded.append({"metric": metric, "identity": list(key), "milliseconds": delta})
            else:
                # Keep small signed values rather than masking clock uncertainty.
                values.append(delta)
        timings[metric] = distribution(values)

    counts = {}
    for stage in STAGES:
        if stage not in stages:
            counts[stage] = {"status": "NOT_CAPTURED"}
            continue
        rows = stages[stage]
        seen = first_seen(rows)
        require(all(opened <= at <= closed for at in seen.values()), "observation outside the trial window")
        matched = seen.keys() & source.keys()
        counts[stage] = {
            "matchingUnique": len(matched),
            "eligibleSourceUnique": len(source),
            "duplicateDeliveries": len(rows) - len(seen),
            "unmatchedUnique": len(seen.keys() - source.keys()),
            "byVehicle": {
                vehicle: {
                    "matchingUnique": sum(key[0] == vehicle for key in matched),
                    "eligibleSourceUnique": sum(key[0] == vehicle for key in source),
                }
                for vehicle in VEHICLES
            },
        }
        interval_samples(f"sourceTo{stage.title()}Ms", ((key, source[key], seen[key]) for key in sorted(matched)))

    target = trial["target"]

    def event_time(field):
        if field not in trial:
            return None
        key = (target, trial[field])
        require(key in source, f"{field} is not a captured target source event")
        return source[key]

    fault = event_time("faultEventId")
    healthy = event_time("firstHealthyEventId")
    recovered = event_time("recoveredEventId")
    for name, start, end in [
        ("groundTruthToFaultSourceMs", parse_timestamp(trial["obstructionAt"]) if "obstructionAt" in trial else None, fault),
        ("groundTruthClearToRecoveredSourceMs", parse_timestamp(trial["clearAt"]) if "clearAt" in trial else None, recovered),
        ("healthyWindowToRecoveredSourceMs", healthy, recovered),
    ]:
        if start is not None:
            require(opened <= start <= closed, "ground truth outside the trial window")
        interval_samples(name, [((target,), start, end)] if start is not None and end is not None else [])

    resources = {}
    for row in trial.get("resources", []):
        require(opened <= parse_timestamp(row["sampledAt"]) <= closed, "resource sample outside trial window")
        require(number(row["cpuPercent"]) and type(row["memoryBytes"]) is int and row["memoryBytes"] >= 0,
                "invalid normalized resource values")
        cpu, memory = resources.setdefault(row["target"], ([], []))
        cpu.append(row["cpuPercent"])
        memory.append(row["memoryBytes"])
    return {
        "id": trial["id"], "status": trial["status"], "reason": trial.get("reason"),
        "sourceUnique": len(source), "stages": counts, "timingsMilliseconds": timings,
        "clockConflicts": excluded,
        "resources": {target: {"cpuPercent": distribution(cpu), "memoryBytes": distribution(memory)}
                      for target, (cpu, memory) in resources.items()},
    }


def summarize(run):
    scope = run["scope"]
    require(scope in {"JOINED_CARLA", "SYNTHETIC_CHECK"}, "unknown measurement scope")
    require(isinstance(run["implementationSha"], str) and len(run["implementationSha"]) == 40
            and all(char in "0123456789abcdef" for char in run["implementationSha"]), "record an exact implementation SHA")
    uncertainty = run["clockUncertaintyMs"]
    require(number(uncertainty), "record the maximum pairwise UTC uncertainty in milliseconds")
    trials = run["trials"]
    require(1 <= len(trials) <= 20 and len({trial["id"] for trial in trials}) == len(trials), "expected 1 to 20 unique trials")
    summaries = [summarize_trial(trial, uncertainty) for trial in trials]
    metrics = sorted({name for trial in summaries for name in trial["timingsMilliseconds"]})
    across_trials = {}
    for metric in metrics:
        samples = [trial["timingsMilliseconds"].get(metric, {}) for trial in summaries]
        across_trials[metric] = distribution([sample["median"] for sample in samples if sample.get("n", 0) > 0])
    return {
        "scope": scope, "implementationSha": run["implementationSha"], "clockUncertaintyMs": uncertainty,
        "trialOutcomes": {status: sum(trial["status"] == status for trial in summaries) for status in sorted(OUTCOMES)},
        "trialMedianDistributionsMilliseconds": across_trials,
        "trials": summaries,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    args = parser.parse_args(argv)
    try:
        result = summarize(json.loads(args.input.read_bytes()))
    except FileNotFoundError as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        return 2
    except (ValueError, TypeError, KeyError, OSError, OverflowError) as error:
        print(f"FAILED: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
