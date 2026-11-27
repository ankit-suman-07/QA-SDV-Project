"""Persisted CARLA session generation.

V2-C2: a restart creates a new session with an increasing, persisted
generation, and UTC must not roll backwards across sessions. The claim is
written (atomically) before the run publishes anything, so a crashed run still
uses up its generation and the next run cannot reuse it. A missing file means
no earlier session; an unreadable file is an error, never a reset to 1.
"""

import json
import os
from datetime import datetime, timezone


def _iso(moment):
    return moment.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def claim_session(path, *, session_id, utc_origin):
    path = os.fspath(path)
    previous = None
    if os.path.exists(path):
        try:
            with open(path) as handle:
                previous = json.load(handle)
            generation = previous["sessionGeneration"]
            last_origin = datetime.fromisoformat(previous["utcOrigin"].replace("Z", "+00:00"))
        except (ValueError, KeyError, TypeError) as error:
            raise ValueError(f"unreadable session state {path}; fix it, do not delete it") from error
        if type(generation) is not int or generation < 1:
            raise ValueError(f"invalid session generation in {path}")
        if utc_origin <= last_origin:
            raise ValueError("UTC origin must be later than the previous session's")
        if session_id == previous.get("sessionId"):
            raise ValueError("session ID was already used by the previous session")
    generation = previous["sessionGeneration"] + 1 if previous else 1

    state = {"sessionGeneration": generation, "sessionId": session_id,
             "utcOrigin": _iso(utc_origin)}
    temporary = f"{path}.tmp"
    with open(temporary, "w") as handle:
        json.dump(state, handle)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    return generation
