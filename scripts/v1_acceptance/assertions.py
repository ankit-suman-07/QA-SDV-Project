"""Fail closed on identity, freshness counting and source/event corruption."""
IDS = ('vehicle-001', 'vehicle-002')


def fleet(summary):
    views = summary['vehicles']
    assert [v['vehicleId'] for v in views] == list(IDS), 'exactly two distinct sorted vehicles required'
    assert summary['totalVehicles'] == 2, 'registered denominator must remain two'
    for view in views:
        assert view['thingId'] == 'sdv:' + view['vehicleId'], 'Thing identity mismatch'
    for field, state in [('availableVehicles', 'AVAILABLE'), ('staleVehicles', 'STALE'),
                         ('unavailableVehicles', 'UNAVAILABLE')]:
        assert summary[field] == sum(v['availability'] == state for v in views), field
    assert sum(summary[f] for f in ('availableVehicles', 'staleVehicles', 'unavailableVehicles')) == 2
    for field, state in [('healthyVehicles', 'HEALTHY'), ('warningVehicles', 'WARNING'),
                         ('criticalVehicles', 'CRITICAL')]:
        assert summary[field] == sum(v['availability'] == 'AVAILABLE' and v['healthStatus'] == state for v in views), field
    assert sum(summary[f] for f in ('healthyVehicles', 'warningVehicles', 'criticalVehicles')) == summary['availableVehicles']


def preserved(event, thing, view):
    vehicle = event['vehicleId']
    assert vehicle in IDS
    assert thing['thingId'] == view['thingId'] == 'sdv:' + vehicle
    assert thing['attributes']['vehicleId'] == view['vehicleId'] == vehicle
    props = thing['features']['v1']['properties']
    assert props['vehicleId'] == vehicle
    for source, twin, api in [('eventId', 'lastEventId', 'lastEventId'),
                              ('sourceTimestamp', 'sourceTimestamp', 'sourceTimestamp'),
                              ('health', 'health', 'healthStatus'),
                              ('faults', 'faults', 'activeFaults'), ('lidar', 'lidar', 'lidar')]:
        assert event[source] == props[twin] == view[api], source
    for key in ('actionId', 'traceId'):
        assert props.get(key) == event.get(key), key
