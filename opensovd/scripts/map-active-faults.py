"""
opensovd/scripts/map-active-faults.py

Fetches the current vehicle-001 twin from Ditto and prints each active
fault mapped into OpenSOVD's diagnostic resource shape (see
opensovd/fault_mapper.py). OpenSOVD's own gateway is read-only (confirmed:
docs/evidence/iteration-2/07-opensovd-confirmed-read-only.png), so this
prints the mapped output rather than pushing it anywhere.

Usage:
    python opensovd/scripts/map-active-faults.py
    python opensovd/scripts/map-active-faults.py --watch
"""
import argparse
import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from opensovd.fault_mapper import map_all_active_faults

DITTO_URL = "http://localhost:8080/api/2/things/sdv:vehicle-001"
AUTH = ("ditto", "ditto")


def fetch_and_map():
    response = requests.get(DITTO_URL, auth=AUTH, timeout=5)
    response.raise_for_status()
    thing = response.json()
    return map_all_active_faults(thing)


def print_result(faults):
    if not faults:
        print("[OpenSOVD] No active faults - vehicle-001 is HEALTHY.")
        return
    summary = ", ".join(f"{f['code']}({f['severity']})" for f in faults)
    print(f"[OpenSOVD] {len(faults)} active fault(s): {summary}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watch", action="store_true", help="Poll every 2 seconds instead of running once.")
    args = parser.parse_args()

    try:
        if not args.watch:
            faults = fetch_and_map()
            print_result(faults)
            if faults:
                print(json.dumps(faults, indent=2))
            return 0

        while True:
            faults = fetch_and_map()
            print_result(faults)
            time.sleep(2)

    except requests.RequestException as exc:
        print(f"Failed to query Ditto: {exc}")
        return 1
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())