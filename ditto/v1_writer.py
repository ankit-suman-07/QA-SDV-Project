"""B2 authenticated HTTP adapter and create-only individual-twin provisioning."""
from dataclasses import dataclass, field
import math
import os
import time
from urllib.parse import quote, urlsplit

import requests

from ditto.mqtt_ingress import (VEHICLES, EventError, WatermarkError, validate_event,
                                decode_json, encode_json, timestamp_key,
                                V2_VEHICLES, validate_v2_health, v2_write_needed)

THINGS = {vehicle: f'sdv:{vehicle}' for vehicle in VEHICLES}
POLICIES = {vehicle: f'sdv:{vehicle}-policy' for vehicle in VEHICLES}


class DittoError(WatermarkError):
    """Safe operational failure; never contains URL, credentials or response body."""
    def __init__(self, code, status=None):
        self.code = code
        self.status = status
        super().__init__(code if status is None else f'{code} status={status}')


@dataclass(frozen=True)
class DittoConfig:
    base_url: str
    username: str
    password: str = field(repr=False)
    timeout_seconds: float = 2.0
    attempts: int = 3
    retry_delay_seconds: float = 0.2
    tls_ca: str | None = None

    def __post_init__(self):
        parsed = urlsplit(self.base_url)
        if (parsed.scheme not in ('http', 'https') or not parsed.hostname or
                parsed.username is not None or parsed.password is not None or
                parsed.query or parsed.fragment or any(c.isspace() for c in self.base_url)):
            raise ValueError('Ditto base URL must be HTTP(S), without credentials/query/fragment')
        try:
            parsed.port
        except ValueError as error:
            raise ValueError('invalid Ditto port') from error
        if not self.username.strip() or not self.password:
            raise ValueError('Ditto username and password are required')
        if type(self.attempts) is not int or not 1 <= self.attempts <= 10:
            raise ValueError('Ditto attempts must be between 1 and 10')
        if (not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0 or
                not math.isfinite(self.retry_delay_seconds) or not 0 <= self.retry_delay_seconds <= 30):
            raise ValueError('invalid Ditto timeout or retry delay')

    @classmethod
    def from_env(cls, environ=None):
        env = os.environ if environ is None else environ
        return cls(base_url=env.get('SDV_DITTO_BASE_URL', 'http://localhost:8080'),
                   username=env.get('SDV_DITTO_USERNAME', ''),
                   password=env.get('SDV_DITTO_PASSWORD', ''),
                   timeout_seconds=float(env.get('SDV_DITTO_TIMEOUT_SECONDS', '2')),
                   attempts=int(env.get('SDV_DITTO_ATTEMPTS', '3')),
                   retry_delay_seconds=float(env.get('SDV_DITTO_RETRY_DELAY_SECONDS', '0.2')),
                   tls_ca=env.get('SDV_DITTO_TLS_CA'))


def _vehicle(vehicle_id):
    if not isinstance(vehicle_id, str) or vehicle_id not in THINGS:
        raise DittoError('UNKNOWN_VEHICLE')


def validate_properties(vehicle_id, properties):
    _vehicle(vehicle_id)
    if not isinstance(properties, dict) or 'lastEventId' not in properties:
        raise DittoError('INVALID_PERSISTED_STATE')
    # Rename only the envelope key; validation never mutates nested values.
    event = dict(properties)
    event['eventId'] = event.pop('lastEventId')
    try:
        validate_event(f'sdv/{vehicle_id}/health', event)
    except (EventError, ValueError, TypeError, RecursionError) as error:
        raise DittoError('INVALID_PERSISTED_STATE') from error
    return properties['lastEventId'], properties['sourceTimestamp']


def validate_thing(vehicle_id, thing):
    _vehicle(vehicle_id)
    if (not isinstance(thing, dict) or thing.get('thingId') != THINGS[vehicle_id] or
            not isinstance(thing.get('attributes'), dict) or
            thing['attributes'].get('vehicleId') != vehicle_id):
        raise DittoError('TWIN_IDENTITY')
    features = thing.get('features', {})
    if not isinstance(features, dict):
        raise DittoError('INVALID_PERSISTED_STATE')
    if 'v1' not in features:
        return None
    feature = features['v1']
    if not isinstance(feature, dict):
        raise DittoError('INVALID_PERSISTED_STATE')
    return validate_properties(vehicle_id, feature.get('properties'))


class DittoWriter:
    """Single writer for two v1 features, safe for independent vehicle threads.

    Uses independent requests rather than sharing a mutable requests.Session.
    Legacy HTTP helpers intentionally remain unchanged: they lack authenticated
    GETs, strict snapshot validation and HTTP-status retry semantics needed here.
    """
    def __init__(self, config, *, request=None, sleeper=None):
        self.config = config
        self._request = request or requests.request
        self._sleep = sleeper or time.sleep

    def _http(self, method, path, *, value=None, create_only=False, missing_ok=False, match_etag=None):
        headers = {'Accept': 'application/json'}
        body = None
        if value is not None:
            headers['Content-Type'] = 'application/json'
            body = encode_json(value)
        if create_only:
            headers['If-None-Match'] = '*'
        if match_etag is not None:
            headers['If-Match'] = match_etag
        failure = DittoError('DITTO_UNAVAILABLE')
        for attempt in range(self.config.attempts):
            try:
                result = self._request(method, self.config.base_url.rstrip('/') + '/api/2/' + path,
                    auth=(self.config.username, self.config.password), headers=headers,
                    timeout=self.config.timeout_seconds, verify=self.config.tls_ca or True,
                    allow_redirects=False, **({'data': body} if body is not None else {}))
            except requests.exceptions.SSLError as error:
                raise DittoError('DITTO_TLS_FAILURE') from error
            except (requests.Timeout, requests.ConnectionError) as error:
                failure = DittoError('DITTO_TIMEOUT' if isinstance(error, requests.Timeout)
                                     else 'DITTO_UNAVAILABLE')
            except requests.RequestException as error:
                raise DittoError('DITTO_REQUEST_FAILURE') from error
            else:
                status = result.status_code
                if (method == 'GET' and status == 200) or (method == 'PUT' and status in (200, 201, 204)):
                    return result
                if status == 404 and missing_ok:
                    return None
                if status == 412 and create_only:
                    return None  # raced with another creator; caller must reread/validate
                if status in (401, 403):
                    raise DittoError('DITTO_AUTH_FAILURE', status)
                if status not in (408, 429, 500, 502, 503, 504):
                    raise DittoError('DITTO_HTTP_FAILURE', status)
                failure = DittoError('DITTO_UNAVAILABLE', status)
            if attempt + 1 < self.config.attempts:
                self._sleep(min(self.config.retry_delay_seconds * 2 ** attempt, 30))
        raise failure

    def _read(self, kind, identity, *, missing_ok=False):
        result = self._http('GET', kind + '/' + quote(identity, safe=':'), missing_ok=missing_ok)
        if result is None:
            return None
        try:
            value = decode_json(result.content, max_bytes=1024 * 1024)
        except EventError as error:
            raise DittoError('INVALID_DITTO_JSON') from error
        if not isinstance(value, dict):
            raise DittoError('INVALID_DITTO_JSON')
        return value

    def read_thing(self, vehicle_id):
        _vehicle(vehicle_id)
        thing = self._read('things', THINGS[vehicle_id])
        validate_thing(vehicle_id, thing)
        return thing

    def load_watermark(self, vehicle_id):
        return validate_thing(vehicle_id, self.read_thing(vehicle_id))

    def persist(self, vehicle_id, properties):
        validate_properties(vehicle_id, properties)
        # A failed/unauthorized whole-Thing read never authorizes creation.
        thing = self.read_thing(vehicle_id)
        path = f'things/{THINGS[vehicle_id]}/features/v1'
        if 'v1' not in thing.get('features', {}):
            # This subresource PUT cannot create a missing Thing. A concurrent
            # creator wins: never overwrite its feature or trust a failed reply.
            if self._http('PUT', path, value={'properties': properties}, create_only=True) is None:
                raise DittoError('DITTO_CONCURRENT_UPDATE', 412)
            return
        path += '/properties'
        result = self._http('GET', path)
        try:
            stored = decode_json(result.content, max_bytes=1024 * 1024)
        except EventError as error:
            raise DittoError('INVALID_PERSISTED_STATE') from error
        previous = validate_properties(vehicle_id, stored)
        if (previous[0] == properties['lastEventId'] or
                timestamp_key(properties['sourceTimestamp']) <= timestamp_key(previous[1])):
            # Ingress invalidates its cache on failure; next attempt reloads and
            # classifies duplicate/old input without acknowledging a lost write.
            raise DittoError('DITTO_WATERMARK_CHANGED')
        etag = result.headers.get('ETag')
        if not isinstance(etag, str) or not etag.strip():
            raise DittoError('DITTO_ETAG_MISSING')
        # Keep the existing properties-only authorization boundary. Definitions,
        # desiredProperties and legacy features are outside this conditional write.
        self._http('PUT', path, value=properties, match_etag=etag)

    @staticmethod
    def _v2_thing_id(vehicle_id):
        if vehicle_id not in V2_VEHICLES:
            raise DittoError('UNKNOWN_VEHICLE')
        return f'sdv:{vehicle_id}'

    @staticmethod
    def _validate_v2_properties(vehicle_id, properties):
        if not isinstance(properties, dict) or 'lastEventId' not in properties or 'eventId' in properties:
            raise DittoError('INVALID_PERSISTED_STATE')
        event = dict(properties)
        event['eventId'] = event.pop('lastEventId')
        try:
            validate_v2_health(f'sdv/{vehicle_id}/v2/health', event)
        except EventError as error:
            raise DittoError('INVALID_PERSISTED_STATE') from error
        return properties

    def load_v2_watermark(self, vehicle_id):
        thing = self._read('things', self._v2_thing_id(vehicle_id))
        attributes, features = thing.get('attributes'), thing.get('features', {})
        if (thing.get('thingId') != f'sdv:{vehicle_id}' or not isinstance(attributes, dict)
                or attributes.get('vehicleId') != vehicle_id):
            raise DittoError('TWIN_IDENTITY')
        if not isinstance(features, dict):
            raise DittoError('INVALID_PERSISTED_STATE')
        if 'v2' not in features:
            return None
        feature = features['v2']
        if not isinstance(feature, dict):
            raise DittoError('INVALID_PERSISTED_STATE')
        return self._validate_v2_properties(vehicle_id, feature.get('properties'))

    def persist_v2(self, vehicle_id, properties):
        feature_path = f'things/{self._v2_thing_id(vehicle_id)}/features/v2'
        properties_path = feature_path + '/properties'
        self._validate_v2_properties(vehicle_id, properties)
        for _ in range(2):
            previous = self.load_v2_watermark(vehicle_id)
            etag = None
            if previous is not None:
                result = self._http('GET', properties_path)
                try:
                    previous = self._validate_v2_properties(
                        vehicle_id, decode_json(result.content, max_bytes=1024 * 1024)
                    )
                except EventError as error:
                    raise DittoError('INVALID_DITTO_JSON') from error
                etag = result.headers.get('ETag')
                if not isinstance(etag, str) or not etag.strip():
                    raise DittoError('DITTO_ETAG_MISSING')
            if not v2_write_needed(properties, previous):
                return
            try:
                if previous is None:
                    result = self._http('PUT', feature_path,
                                        value={'properties': properties}, create_only=True)
                else:
                    result = self._http('PUT', properties_path, value=properties, match_etag=etag)
            except DittoError as error:
                if error.status != 412:
                    raise
                continue
            if result is not None:
                if result.status_code not in (201, 204):
                    raise DittoError('DITTO_HTTP_FAILURE', result.status_code)
                return
        raise DittoError('DITTO_CONCURRENT_UPDATE', 412)

    @staticmethod
    def _validate_policy(policy, policy_id, subject):
        if not isinstance(policy, dict) or policy.get('policyId') != policy_id:
            raise DittoError('POLICY_IDENTITY')
        entries = policy.get('entries')
        if not isinstance(entries, dict):
            raise DittoError('POLICY_CONFIGURATION')
        granted = False
        for entry in entries.values():
            if not isinstance(entry, dict) or not isinstance(entry.get('subjects'), dict):
                raise DittoError('POLICY_CONFIGURATION')
            if subject not in entry['subjects']:
                continue
            resources = entry.get('resources', {})
            if not isinstance(resources, dict):
                raise DittoError('POLICY_CONFIGURATION')
            for resource in resources.values():
                if (not isinstance(resource, dict) or
                        not isinstance(resource.get('grant', []), list) or
                        not all(isinstance(item, str) for item in resource.get('grant', [])) or
                        not isinstance(resource.get('revoke', []), list) or resource.get('revoke')):
                    # Conservative: do not silently accept a matching principal
                    # with subresource revocations or malformed permissions.
                    raise DittoError('POLICY_CONFIGURATION')
            if all(isinstance(resources.get(path), dict) and
                   {'READ', 'WRITE'} <= set(resources[path].get('grant', [])) and
                   not resources[path].get('revoke')
                   for path in ('thing:/', 'policy:/')):
                granted = True
        if not granted:
            raise DittoError('POLICY_CONFIGURATION')

    def provision(self, subject):
        """Create absent policies/Things only; validate existing resources unchanged.

        Run while ingress/other provisioning is stopped. No whole-Thing overwrite,
        property resets, fabricated observation or fleet resource creation occurs.
        """
        if not isinstance(subject, str) or not subject.strip() or subject != subject.strip():
            raise ValueError('explicit Ditto policy subject required')
        for vehicle in VEHICLES:
            policy_id = POLICIES[vehicle]
            policy = self._read('policies', policy_id, missing_ok=True)
            if policy is None:
                value = {'entries': {'owner': {
                    'subjects': {subject: {'type': 'configured ingress principal'}},
                    'resources': {path: {'grant': ['READ', 'WRITE'], 'revoke': []}
                                  for path in ('thing:/', 'policy:/')}}}}
                self._http('PUT', 'policies/' + policy_id, value=value, create_only=True)
                policy = self._read('policies', policy_id)
            self._validate_policy(policy, policy_id, subject)
        for vehicle in VEHICLES:
            thing = self._read('things', THINGS[vehicle], missing_ok=True)
            if thing is None:
                self._http('PUT', 'things/' + THINGS[vehicle], create_only=True,
                           value={'policyId': POLICIES[vehicle], 'attributes': {'vehicleId': vehicle}})
                thing = self._read('things', THINGS[vehicle])
            validate_thing(vehicle, thing)
            if thing.get('policyId') != POLICIES[vehicle]:
                raise DittoError('POLICY_BINDING_MISMATCH')
