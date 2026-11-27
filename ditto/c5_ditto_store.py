"""Opt-in standalone C5 health persistence, verified with offline HTTP fakes.

Capacity checks cover replay metadata only. Optional byte budgets are
caller-supplied and provisional. The properties ETag does not guard other
Thing fields, so this adapter provides no hard whole-Thing byte limit.

Root PATCH with a Thing revision ETag is a future design candidate.
Required-null preservation, permissions and real Ditto behavior still need
validation. Backend authorization and rollover handoff remain pending.
Production throughput and 30-minute endurance remain unverified.
"""

from dataclasses import replace

from .c5_fingerprint import fingerprint_decoded_envelope, fingerprint_envelope
from .c5_replay_ledger import load_ledger, new_ledger, record_observation
from .mqtt_ingress import EventError, WatermarkError, decode_json, encode_json
from .v1_writer import DittoError, DittoWriter

_UNCERTAIN = {"DITTO_TIMEOUT", "DITTO_UNAVAILABLE", "DITTO_REQUEST_FAILURE"}


class C5HealthStore:
    """Conditionally commit one health projection and its replay state.

    Initial sessions come from trusted provisioning, independently of the
    message. Successor authorization and metadata migration are out of scope.
    The conditional write protects v2 properties, not the rest of the Thing.
    """

    def __init__(
        self, config, *, initial_sessions, max_observations,
        max_membership_bytes=None, max_metadata_bytes=None, attempts=2, request=None,
    ):
        if type(attempts) is not int or not 1 <= attempts <= 10:
            raise ValueError("C5 conditional attempts must be between 1 and 10")
        if max_metadata_bytes is not None and (
            type(max_metadata_bytes) is not int or max_metadata_bytes < 1
        ):
            raise ValueError("C5 metadata byte budget must be a positive integer")
        self._max_metadata_bytes = max_metadata_bytes
        self._initial = {
            vehicle: new_ledger(vehicle, session, 1)
            for vehicle, session in initial_sessions.items()
        }
        self._limits = {
            "max_observations": max_observations,
            "max_membership_bytes": max_membership_bytes,
        }
        self._attempts = attempts
        # Never resend a PUT beneath the reconciliation loop.
        self._http = DittoWriter(replace(config, attempts=1), request=request)

    def _load(self, vehicle, feature_path):
        thing = self._http._read("things", f"sdv:{vehicle}")
        attributes = thing.get("attributes")
        if (thing.get("thingId") != f"sdv:{vehicle}" or not isinstance(attributes, dict)
                or attributes.get("vehicleId") != vehicle):
            raise DittoError("TWIN_IDENTITY")
        features = thing.get("features", {})
        if not isinstance(features, dict):
            raise DittoError("INVALID_PERSISTED_STATE")
        if "v2" not in features:
            return self._initial[vehicle], None

        result = self._http._http("GET", feature_path + "/properties")
        etag = result.headers.get("ETag")
        if not isinstance(etag, str) or not etag.strip():
            raise DittoError("DITTO_ETAG_MISSING")
        try:
            properties = decode_json(result.content, max_bytes=1024 * 1024)
            if not isinstance(properties, dict):
                raise DittoError("INVALID_PERSISTED_STATE")
            if "_ingress" not in properties:
                raise DittoError("C5_LEGACY_STATE")
            ledger = load_ledger(properties.pop("_ingress"))
            if ledger["vehicleId"] != vehicle:
                raise DittoError("TWIN_IDENTITY")
            if ledger["sessionGeneration"] != 1 or ledger["sessionId"] != self._initial[vehicle]["sessionId"]:
                raise DittoError("C5_SESSION_UNVERIFIED")
            if "eventId" in properties or "lastEventId" not in properties:
                raise DittoError("INVALID_PERSISTED_STATE")
            properties["eventId"] = properties.pop("lastEventId")
            projection = fingerprint_decoded_envelope(f"sdv/{vehicle}/v2/health", properties).envelope
            latest = ledger["latest"]
            if latest is None or any(projection[key] != value for key, value in latest.items()
                                     if key != "fingerprint"):
                raise DittoError("INVALID_PERSISTED_STATE")
        except EventError as error:
            raise DittoError("INVALID_PERSISTED_STATE") from error
        return ledger, etag

    def persist_health(self, topic, raw):
        """Return the original fingerprint after confirmed commit or exact retry."""
        if not isinstance(topic, str) or not topic.endswith("/v2/health"):
            raise EventError("TOPIC_MISMATCH")
        candidate = fingerprint_envelope(topic, raw)
        vehicle = candidate.envelope["vehicleId"]
        if vehicle not in self._initial:
            raise EventError("UNREGISTERED_SESSION")
        feature_path = f"things/sdv:{vehicle}/features/v2"
        for attempt in range(self._attempts + 1):
            ledger, etag = self._load(vehicle, feature_path)
            updated = record_observation(ledger, candidate, **self._limits)
            if updated is None:
                return candidate
            if attempt == self._attempts:
                break
            if (self._max_metadata_bytes is not None
                    and len(encode_json(updated)) > self._max_metadata_bytes):
                raise WatermarkError("C5_REPLAY_CAPACITY")
            projection = dict(candidate.envelope, _ingress=updated)
            projection["lastEventId"] = projection.pop("eventId")
            try:
                if etag is None:
                    result = self._http._http("PUT", feature_path, create_only=True,
                                              value={"properties": projection})
                else:
                    result = self._http._http("PUT", feature_path + "/properties",
                                              match_etag=etag, value=projection)
            except DittoError as error:
                if error.status == 412:
                    continue
                if error.code not in _UNCERTAIN:
                    raise
                return self._reconcile_uncertain(vehicle, feature_path, candidate)
            if result is None:
                continue  # Conditional creation received HTTP 412.
            if result.status_code in (201, 204):
                return candidate
            return self._reconcile_uncertain(vehicle, feature_path, candidate)
        raise DittoError("DITTO_CONCURRENT_UPDATE", 412)

    def _reconcile_uncertain(self, vehicle, path, candidate):
        try:
            ledger, _ = self._load(vehicle, path)
            if record_observation(ledger, candidate, **self._limits) is None:
                return candidate
        except (WatermarkError, EventError) as error:
            raise DittoError("C5_WRITE_UNRESOLVED") from error
        raise DittoError("C5_WRITE_UNRESOLVED")
