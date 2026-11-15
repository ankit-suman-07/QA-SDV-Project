"""Real persistence/ingress with a path-accurate substitute; live evidence separate."""
import copy
import json
import pytest
import requests
from ditto.v1_writer import DittoWriter, DittoConfig, DittoError
from ditto.mqtt_ingress import Ingress, EventError
from test_ditto_v1_writer import FakeDitto, response
from test_mqtt_ingress import fixture


def setup():
    http = FakeDitto()
    writer = DittoWriter(DittoConfig('http://ditto', 'test', 'test', attempts=1), request=http)
    writer.provision('nginx:test')
    http.things['sdv:vehicle-002']['features'] = {'legacy': {'properties': {'speed': 12}}}
    return http, writer


def send(writer, name='vehicle-002-fault'):
    event = fixture(name)
    event.update(actionId='actual-action', traceId='actual-trace')
    return Ingress(writer).process('sdv/vehicle-002/health', json.dumps(event))


def test_first_actual_fault_initializes_feature_preserves_legacy_and_restart_watermark():
    http, writer = setup()
    event = send(writer)
    thing = http.things['sdv:vehicle-002']
    assert thing['features']['legacy'] == {'properties': {'speed': 12}}
    properties = dict(event); properties['lastEventId'] = properties.pop('eventId')
    assert thing['features']['v1'] == {'properties': properties}
    before = copy.deepcopy(http.things)
    with pytest.raises(EventError): send(writer)
    assert before == http.things


@pytest.mark.parametrize('status', [401, 403, 404, 500, 503])
def test_read_failure_is_never_permission_to_initialize(status):
    http, writer = setup()
    original = writer._request
    def request(method, url, **kw):
        if method == 'GET': return response(status)
        return original(method, url, **kw)
    writer._request = request
    with pytest.raises(DittoError): send(writer)
    assert 'v1' not in http.things['sdv:vehicle-002']['features']


def test_competing_creator_cannot_be_overwritten_and_retry_loads_winner():
    http, writer = setup()
    original = writer._request
    winner = fixture('vehicle-002-recovered')
    props = dict(winner); props['lastEventId'] = props.pop('eventId')
    def request(method, url, **kw):
        if method == 'PUT' and '/features/v1' in url:
            http.things['sdv:vehicle-002']['features']['v1'] = {'properties': copy.deepcopy(props)}
        return original(method, url, **kw)
    writer._request = request
    with pytest.raises(DittoError): send(writer)
    assert http.things['sdv:vehicle-002']['features']['v1']['properties'] == props
    with pytest.raises(EventError): send(writer)


def test_conditional_update_preserves_feature_metadata_and_rejects_race():
    http, writer = setup()
    send(writer, 'vehicle-002-healthy')
    feature = http.things['sdv:vehicle-002']['features']['v1']
    feature['definition'] = ['example:definition:1']
    send(writer)
    assert http.things['sdv:vehicle-002']['features']['v1']['definition'] == ['example:definition:1']
    original = writer._request
    before = copy.deepcopy(http.things)
    def request(method, url, **kw):
        if method == 'PUT': return response(412)
        return original(method, url, **kw)
    writer._request = request
    with pytest.raises(DittoError): send(writer, 'vehicle-002-recovered')
    assert http.things == before


def test_uncertain_creation_response_does_not_advance_ingress_watermark():
    http, writer = setup()
    original = writer._request
    first = True
    def request(method, url, **kw):
        nonlocal first
        result = original(method, url, **kw)
        if method == 'PUT' and first:
            first = False
            raise requests.Timeout()
        return result
    writer._request = request
    ingress = Ingress(writer); event = fixture('vehicle-002-fault')
    with pytest.raises(DittoError): ingress.process('sdv/vehicle-002/health', json.dumps(event))
    assert 'vehicle-002' not in ingress._committed
    with pytest.raises(EventError): ingress.process('sdv/vehicle-002/health', json.dumps(event))

@pytest.mark.parametrize('status', [401, 403, 404, 412, 503])
def test_failed_creation_invalidates_cache_without_acknowledging_persistence(status):
    http, writer = setup()
    original = writer._request
    def request(method, url, **kw):
        return response(status) if method == 'PUT' else original(method, url, **kw)
    writer._request = request
    ingress = Ingress(writer)
    with pytest.raises(DittoError):
        ingress.process('sdv/vehicle-002/health', json.dumps(fixture('vehicle-002-fault')))
    assert 'vehicle-002' not in ingress._committed
    assert 'v1' not in http.things['sdv:vehicle-002']['features']


def test_missing_entity_tag_cannot_authorize_unconditional_update():
    http, writer = setup()
    send(writer, 'vehicle-002-healthy')
    before = copy.deepcopy(http.things)
    original = writer._request
    def request(method, url, **kw):
        result = original(method, url, **kw)
        if method == 'GET': result.headers = {}
        return result
    writer._request = request
    with pytest.raises(DittoError): send(writer)
    assert http.things == before


def test_existing_feature_updates_keep_properties_only_authorization_boundary():
    http, writer = setup()
    send(writer, 'vehicle-002-healthy')
    original = writer._request
    def request(method, url, **kw):
        if method == 'PUT' and url.endswith('/features/v1'):
            return response(403)  # existing principal may update properties, not definitions
        return original(method, url, **kw)
    writer._request = request
    send(writer)
    assert http.things['sdv:vehicle-002']['features']['v1']['properties']['health']=='CRITICAL'
