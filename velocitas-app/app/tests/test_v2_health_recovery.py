import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest


def test_recovery_retains_fault_until_two_seconds_of_fresh_healthy_observations(monkeypatch):
    app_dir = Path(__file__).resolve().parents[1]
    fixture = app_dir.parents[1] / "tests/fixtures/v2/sequences/recovery.json"
    steps = json.loads(fixture.read_text(encoding="utf-8"))["steps"]
    monkeypatch.syspath_prepend(str(app_dir / "src"))
    try:
        from v2_health_recovery import V2HealthRecovery
    except ModuleNotFoundError as error:
        if error.name != "v2_health_recovery":
            raise
        pytest.fail("Production V2 health recovery interface is missing", pytrace=False)

    epoch = datetime.fromisoformat(steps[0]["now"].replace("Z", "+00:00"))
    utc_now = epoch
    receipt_seconds = 0.0
    vehicle_id = steps[0]["observation"]["vehicleId"]
    recovery = V2HealthRecovery(
        vehicle_id=vehicle_id,
        utc_now=lambda: utc_now,
        monotonic_now=lambda: receipt_seconds,
    )

    for step in steps:
        utc_now = datetime.fromisoformat(step["now"].replace("Z", "+00:00"))
        # This replay delivers each observation at the fixture's evaluation time.
        receipt_seconds = (utc_now - epoch).total_seconds()
        observation = step["observation"].copy()
        observation.pop("fixtureLabel")
        result = recovery.process(observation)

        expected_health, expected_state = step["expected"]
        assert result["health"] == expected_health, observation["eventId"]
        assert result["recoveryState"] == expected_state, observation["eventId"]
        expected_faults = [] if expected_health == "HEALTHY" else ["LIDAR_OBSTRUCTION"]
        assert result["faults"] == expected_faults, observation["eventId"]
        for field in ("vehicleId", "eventId", "sourceTimestamp"):
            assert result[field] == observation[field], (observation["eventId"], field)

    first_healthy = datetime.fromisoformat(
        steps[1]["observation"]["sourceTimestamp"].replace("Z", "+00:00")
    )
    last_source = datetime.fromisoformat(
        steps[-1]["observation"]["sourceTimestamp"].replace("Z", "+00:00")
    )
    assert last_source - first_healthy == timedelta(seconds=2)


@pytest.mark.parametrize(
    ("clock_samples", "restart_at_ms"),
    [
        pytest.param(
            [(1501, 1500), (2000, 1999), (2500, 2499), (3000, 2999), (3500, 3499), (3501, 3500)],
            1501,
            id="source-gap-501ms",
        ),
        pytest.param(
            [(1500, 1501), (2000, 2001), (2500, 2501), (3000, 3001), (3499, 3500), (3500, 3501)],
            1500,
            id="receipt-gap-501ms",
        ),
        pytest.param(
            [(1500, 1500), (2000, 2000), (2499, 2499), (2500, 2500)],
            None,
            id="both-gaps-exactly-500ms",
        ),
    ],
)
def test_recovery_gap_respects_both_clocks(monkeypatch, clock_samples, restart_at_ms):
    app_dir = Path(__file__).resolve().parents[1]
    fixture = app_dir.parents[1] / "tests/fixtures/v2/sequences/recovery.json"
    steps = json.loads(fixture.read_text(encoding="utf-8"))["steps"]
    fault, healthy = (step["observation"] for step in steps[:2])
    epoch = datetime.fromisoformat(fault["sourceTimestamp"].replace("Z", "+00:00"))
    vehicle_id = fault["vehicleId"]
    monotonic_origin = 40.0
    utc_now = epoch
    receipt_seconds = monotonic_origin

    monkeypatch.syspath_prepend(str(app_dir / "src"))
    from v2_health_recovery import V2HealthRecovery

    recovery = V2HealthRecovery(
        vehicle_id=vehicle_id,
        utc_now=lambda: utc_now,
        monotonic_now=lambda: receipt_seconds,
    )
    samples = [(0, 0), (500, 500), (1000, 1000), *clock_samples]
    completion_ms = (restart_at_ms if restart_at_ms is not None else 500) + 2000
    assert samples[-2][0] == completion_ms - 1
    assert samples[-1][0] == completion_ms
    if restart_at_ms is not None:
        assert any(source_ms == 2500 for source_ms, _ in samples)

    for index, (source_ms, receipt_ms) in enumerate(samples):
        source = epoch + timedelta(milliseconds=source_ms)
        utc_now = epoch + timedelta(milliseconds=receipt_ms)
        receipt_seconds = monotonic_origin + receipt_ms / 1000
        observation = (fault if index == 0 else healthy).copy()
        observation.pop("fixtureLabel")
        observation.update(
            eventId=f"{vehicle_id}-gap-test-{index}",
            sequence=index,
            frame=fault["frame"] + index,
            simulationSeconds=fault["simulationSeconds"] + source_ms / 1000,
            sourceTimestamp=source.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            processingTimestamp=utc_now.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        )
        result = recovery.process(observation)
        for field in ("vehicleId", "eventId", "sourceTimestamp"):
            assert result[field] == observation[field]

        if index == 0:
            assert (result["health"], result["recoveryState"]) == ("CRITICAL", "NONE")
            assert result["faults"] == ["LIDAR_OBSTRUCTION"]
            assert result["recoveryStartedAt"] is None
        elif index == len(samples) - 1:
            assert (result["health"], result["recoveryState"]) == ("HEALTHY", "NONE")
            assert result["faults"] == []
            assert result["recoveryStartedAt"] is None
        else:
            assert (result["health"], result["recoveryState"]) == ("CRITICAL", "IN_PROGRESS")
            assert result["faults"] == ["LIDAR_OBSTRUCTION"]
            started_ms = 500
            if restart_at_ms is not None and source_ms >= restart_at_ms:
                started_ms = restart_at_ms
            assert datetime.fromisoformat(
                result["recoveryStartedAt"].replace("Z", "+00:00")
            ) == epoch + timedelta(milliseconds=started_ms)


@pytest.mark.parametrize(
    "replay_kind",
    [
        "latest-event-retry",
        "latest-event-id-with-new-metadata",
        "earlier-event-id-with-new-metadata",
        "repeated-source-timestamp",
        "cached-frame-with-new-metadata",
    ],
)
def test_recovery_ignores_replayed_observations(monkeypatch, replay_kind):
    app_dir = Path(__file__).resolve().parents[1]
    fixture = app_dir.parents[1] / "tests/fixtures/v2/sequences/recovery.json"
    steps = json.loads(fixture.read_text(encoding="utf-8"))["steps"]
    fault, healthy = (step["observation"] for step in steps[:2])
    epoch = datetime.fromisoformat(fault["sourceTimestamp"].replace("Z", "+00:00"))
    utc_now = epoch
    receipt_seconds = 40.0
    vehicle_id = fault["vehicleId"]

    monkeypatch.syspath_prepend(str(app_dir / "src"))
    from v2_health_recovery import V2HealthRecovery

    recovery = V2HealthRecovery(
        vehicle_id=vehicle_id,
        utc_now=lambda: utc_now,
        monotonic_now=lambda: receipt_seconds,
    )

    def observe(index, source_ms, receipt_ms):
        source = epoch + timedelta(milliseconds=source_ms)
        receipt_utc = epoch + timedelta(milliseconds=receipt_ms)
        observation = (fault if index == 0 else healthy).copy()
        observation.pop("fixtureLabel")
        observation.update(
            eventId=f"{vehicle_id}-replay-test-{index}",
            sequence=index,
            frame=fault["frame"] + index,
            simulationSeconds=fault["simulationSeconds"] + source_ms / 1000,
            sourceTimestamp=source.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            processingTimestamp=receipt_utc.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        )
        return observation

    def deliver(observation, receipt_ms):
        nonlocal utc_now, receipt_seconds
        utc_now = epoch + timedelta(milliseconds=receipt_ms)
        receipt_seconds = 40.0 + receipt_ms / 1000
        result = recovery.process(observation)
        for field in ("vehicleId", "eventId", "sourceTimestamp"):
            assert result[field] == observation[field]
        return result

    def assert_recovering(result):
        assert (result["health"], result["recoveryState"]) == ("CRITICAL", "IN_PROGRESS")
        assert result["faults"] == ["LIDAR_OBSTRUCTION"]
        assert datetime.fromisoformat(
            result["recoveryStartedAt"].replace("Z", "+00:00")
        ) == epoch + timedelta(milliseconds=500)

    initial = deliver(observe(0, 0, 0), 0)
    assert (initial["health"], initial["recoveryState"]) == ("CRITICAL", "NONE")
    assert initial["faults"] == ["LIDAR_OBSTRUCTION"]
    first_healthy = observe(1, 500, 500)
    latest_healthy = observe(2, 1000, 1000)
    assert_recovering(deliver(first_healthy, 500))
    assert_recovering(deliver(latest_healthy, 1000))

    # Start from otherwise fresh metadata so each conflict is isolated.
    replay = observe(3, 1250, 1250)
    if replay_kind == "latest-event-retry":
        replay = latest_healthy.copy()
    elif replay_kind == "latest-event-id-with-new-metadata":
        replay["eventId"] = latest_healthy["eventId"]
    elif replay_kind == "earlier-event-id-with-new-metadata":
        replay["eventId"] = first_healthy["eventId"]
    elif replay_kind == "repeated-source-timestamp":
        replay["sourceTimestamp"] = latest_healthy["sourceTimestamp"]
        replay["simulationSeconds"] = latest_healthy["simulationSeconds"]
    else:
        replay["frame"] = first_healthy["frame"]

    with pytest.raises(ValueError):
        deliver(replay, 1250)

    # A rejected replay is not evidence of a gap when fresh data still arrives
    # within 500 ms of the last accepted observation on both clocks.
    for index, ms in enumerate((1500, 2000, 2499), start=3):
        assert_recovering(deliver(observe(index, ms, ms), ms))

    complete = deliver(observe(6, 2500, 2500), 2500)
    assert (complete["health"], complete["recoveryState"]) == ("HEALTHY", "NONE")
    assert complete["faults"] == []
    assert complete["recoveryStartedAt"] is None


@pytest.fixture
def replay_session(monkeypatch):
    app_dir = Path(__file__).resolve().parents[1]
    fixture = app_dir.parents[1] / "tests/fixtures/v2/sequences/recovery.json"
    template = json.loads(fixture.read_text(encoding="utf-8"))["steps"][0]["observation"]
    template.pop("fixtureLabel")
    epoch = datetime.fromisoformat(template["sourceTimestamp"].replace("Z", "+00:00"))
    utc_now = epoch
    receipt_seconds = 40.0

    monkeypatch.syspath_prepend(str(app_dir / "src"))
    import v2_health_recovery

    def make_engine(vehicle_id=template["vehicleId"]):
        return v2_health_recovery.V2HealthRecovery(
            vehicle_id=vehicle_id,
            utc_now=lambda: utc_now,
            monotonic_now=lambda: receipt_seconds,
        )

    def observation(index, *, distance=3, source_ms=None, receipt_ms=None, age_ms=0, **overrides):
        nonlocal utc_now, receipt_seconds
        source_ms = index * 125 if source_ms is None else source_ms
        receipt_ms = source_ms if receipt_ms is None else receipt_ms
        source = epoch + timedelta(milliseconds=source_ms)
        utc_now = source + timedelta(milliseconds=age_ms)
        receipt_seconds = 40.0 + receipt_ms / 1000
        timestamp = source.isoformat(timespec="milliseconds").replace("+00:00", "Z")
        return {
            **template,
            "eventId": f"ledger-event-{index}",
            "sequence": index,
            "frame": template["frame"] + index,
            "simulationSeconds": template["simulationSeconds"] + source_ms / 1000,
            "sourceTimestamp": timestamp,
            "processingTimestamp": timestamp,
            "lidar": {"distanceMeters": distance, "sensorAvailable": True},
            **overrides,
        }

    return v2_health_recovery.MAX_SESSION_EVENT_IDS, make_engine, observation


def accepted_recovery_state(engine):
    # Capture both accepted clocks, recovery state, and the ledger because a
    # saturated session cannot emit another event to expose a state change.
    return (
        engine._latest,
        engine._started_at,
        engine._health,
        tuple(engine._faults),
        frozenset(engine._accepted_event_ids),
    )


def test_replay_ledger_fails_closed_at_production_capacity(replay_session):
    capacity, make_engine, observation = replay_session
    assert capacity == 65_536
    recovery = make_engine()
    accepted_ids = set()
    for index in range(capacity):
        event = observation(index, distance=20 if index == capacity - 1 else 3)
        result = recovery.process(event)
        accepted_ids.add(event["eventId"])

    for field in ("vehicleId", "eventId", "sourceTimestamp"):
        assert result[field] == event[field]
    assert (result["health"], result["recoveryState"]) == ("CRITICAL", "IN_PROGRESS")
    assert result["faults"] == ["LIDAR_OBSTRUCTION"]

    from hashlib import sha256

    before = accepted_recovery_state(recovery)
    assert before[-1] == {sha256(event_id.encode("utf-8")).digest() for event_id in accepted_ids}

    for accepted_index in (0, capacity // 2, capacity - 1):
        replay = observation(capacity, distance=20, eventId=f"ledger-event-{accepted_index}")
        with pytest.raises(ValueError, match="duplicate event ID"):
            recovery.process(replay)
        assert accepted_recovery_state(recovery) == before

    # The first new ID beyond capacity and later attempts all fail, including
    # one whose source time would otherwise be past the recovery deadline.
    for index in (capacity, capacity + 1, capacity + 16):
        with pytest.raises(ValueError, match="source session event-ID capacity reached"):
            recovery.process(observation(index, distance=20))
        assert accepted_recovery_state(recovery) == before


def test_replay_ledger_keeps_vehicle_and_current_session_isolated(replay_session):
    _, make_engine, observation = replay_session
    recovery = make_engine()
    other = make_engine("vehicle-003")
    initial = observation(0, sessionGeneration=2, sessionId="current-session")
    result = recovery.process(initial)
    assert (result["health"], result["faults"]) == ("CRITICAL", ["LIDAR_OBSTRUCTION"])
    assert result["vehicleId"] == initial["vehicleId"]
    assert result["eventId"] == initial["eventId"]
    assert result["sourceTimestamp"] == initial["sourceTimestamp"]

    healthy = observation(1, distance=20, sessionGeneration=2, sessionId="current-session")
    assert recovery.process(healthy)["recoveryState"] == "IN_PROGRESS"
    before = accepted_recovery_state(recovery)

    foreign = {**healthy, "vehicleId": "vehicle-003"}
    foreign_result = other.process(foreign)
    assert (foreign_result["vehicleId"], foreign_result["eventId"], foreign_result["sourceTimestamp"]) == (
        foreign["vehicleId"], foreign["eventId"], foreign["sourceTimestamp"],
    )
    assert foreign_result["health"] == "HEALTHY"
    with pytest.raises(ValueError, match="observation vehicle does not match"):
        recovery.process(foreign)
    assert accepted_recovery_state(recovery) == before

    for generation, session_id in ((1, "retired-session"), (2, "conflicting-session")):
        wrong_session = observation(2, distance=20, sessionGeneration=generation, sessionId=session_id)
        with pytest.raises(ValueError, match="out-of-order source session"):
            recovery.process(wrong_session)
        assert accepted_recovery_state(recovery) == before

    fresh = observation(3, distance=20, sessionGeneration=2, sessionId="current-session")
    result = recovery.process(fresh)
    assert (result["health"], result["recoveryState"]) == ("CRITICAL", "IN_PROGRESS")
    assert datetime.fromisoformat(result["recoveryStartedAt"].replace("Z", "+00:00")) == (
        datetime.fromisoformat(healthy["sourceTimestamp"].replace("Z", "+00:00"))
    )
    assert result["faults"] == ["LIDAR_OBSTRUCTION"]
    for field in ("vehicleId", "eventId", "sourceTimestamp"):
        assert result[field] == fresh[field]


@pytest.fixture
def recovery_near_completion(replay_session):
    _, make_engine, observation = replay_session
    engine = make_engine()

    def deliver(index, source_ms, receipt_ms, *, age_ms=0, distance=20, **overrides):
        event = observation(
            index, distance=distance, source_ms=source_ms,
            receipt_ms=receipt_ms, age_ms=age_ms, **overrides,
        )
        result = engine.process(event)
        for field in ("vehicleId", "eventId", "sourceTimestamp"):
            assert result[field] == event[field]
        return result

    assert deliver(0, 0, 0, distance=3)["faults"] == ["LIDAR_OBSTRUCTION"]
    first = deliver(1, 500, 480)
    started_at = first["recoveryStartedAt"]
    assert datetime.fromisoformat(started_at) == datetime.fromisoformat(first["sourceTimestamp"])
    for index, source_ms in enumerate((1000, 1500, 2000), start=2):
        result = deliver(index, source_ms, source_ms - 20)
        assert result["recoveryStartedAt"] == started_at
        assert result["faults"] == ["LIDAR_OBSTRUCTION"]
    return engine, deliver, started_at


@pytest.mark.parametrize(
    ("source_ms", "sequence"),
    [
        pytest.param(1750, 5, id="older-source-time"),
        pytest.param(2500, 3, id="lower-sequence"),
        pytest.param(2500, 4, id="repeated-sequence"),
    ],
)
def test_ordering_rejection_preserves_recovery(recovery_near_completion, source_ms, sequence):
    engine, deliver, started_at = recovery_near_completion
    before = accepted_recovery_state(engine)
    with pytest.raises(ValueError, match="out-of-order observation"):
        deliver(5, source_ms, 2230, sequence=sequence)
    assert accepted_recovery_state(engine) == before

    before_deadline = deliver(6, 2499, 2479)
    assert (before_deadline["health"], before_deadline["recoveryState"]) == ("CRITICAL", "IN_PROGRESS")
    assert before_deadline["faults"] == ["LIDAR_OBSTRUCTION"]
    assert before_deadline["recoveryStartedAt"] == started_at
    at_deadline = deliver(7, 2500, 2480)
    assert (at_deadline["health"], at_deadline["recoveryState"]) == ("HEALTHY", "NONE")
    assert at_deadline["faults"] == []
    assert at_deadline["recoveryStartedAt"] is None


@pytest.mark.parametrize("age_ms", [5000, -1000])
def test_recovery_completion_accepts_fresh_utc_boundaries(recovery_near_completion, age_ms):
    _, deliver, _ = recovery_near_completion
    result = deliver(5, 2500, 2480, age_ms=age_ms)
    assert (result["health"], result["recoveryState"]) == ("HEALTHY", "NONE")
    assert result["faults"] == []
    assert result["recoveryStartedAt"] is None


@pytest.mark.parametrize("age_ms", [5001, 30000, 30001, -1001])
def test_clock_rejection_preserves_accepted_observation_and_restarts_recovery(replay_session, age_ms):
    _, make_engine, observation = replay_session
    engine = make_engine()
    initial = engine.process(observation(0, source_ms=0))
    assert initial["health"] == "CRITICAL" and initial["faults"] == ["LIDAR_OBSTRUCTION"]
    accepted = observation(1, distance=20, source_ms=500)
    assert engine.process(accepted)["recoveryState"] == "IN_PROGRESS"
    before = accepted_recovery_state(engine)
    rejected = observation(2, distance=31, source_ms=1000, age_ms=age_ms, provenance="CARLA")
    reset = engine.process(rejected)

    assert {field: reset[field] for field in accepted} == accepted
    assert (reset["health"], reset["recoveryState"]) == ("CRITICAL", "NONE")
    assert reset["faults"] == ["LIDAR_OBSTRUCTION"]
    assert reset["recoveryStartedAt"] is None
    assert accepted_recovery_state(engine) == (before[0], None, *before[2:])

    # The first fresh sample can reuse the rejected sample's identity and time.
    for index, ms in enumerate((1000, 1500, 2000, 2500, 2999), start=2):
        fresh = engine.process(observation(index, distance=20, source_ms=ms))
        assert (fresh["health"], fresh["recoveryState"]) == ("CRITICAL", "IN_PROGRESS")
        assert fresh["faults"] == ["LIDAR_OBSTRUCTION"]
        assert datetime.fromisoformat(fresh["recoveryStartedAt"]) == (
            datetime.fromisoformat(accepted["sourceTimestamp"]) + timedelta(milliseconds=500)
        )

    cleared = engine.process(observation(7, distance=20, source_ms=3000))
    assert (cleared["health"], cleared["recoveryState"]) == ("HEALTHY", "NONE")
    assert cleared["faults"] == []
    assert cleared["recoveryStartedAt"] is None


def test_clock_rejection_before_first_accepted_observation(replay_session):
    _, make_engine, observation = replay_session
    engine = make_engine()
    with pytest.raises(ValueError, match="without an accepted sample"):
        engine.process(observation(0, age_ms=-1001))
    assert engine.evaluate_silence()["health"] is None
    assert engine.process(observation(0, distance=20))["health"] == "HEALTHY"


def test_clock_only_silence_interrupts_recovery_without_changing_observation(monkeypatch):
    app_dir = Path(__file__).resolve().parents[1]
    fixture = app_dir.parents[1] / "tests/fixtures/v2/sequences/source-silence.json"
    steps = json.loads(fixture.read_text(encoding="utf-8"))["steps"]
    fault_step, recovery_step, at_boundary, beyond_boundary = steps[:4]
    epoch = datetime.fromisoformat(fault_step["now"])
    utc_now = epoch
    receipt_seconds = 0.0
    vehicle_id = fault_step["observation"]["vehicleId"]

    monkeypatch.syspath_prepend(str(app_dir / "src"))
    from v2_health_recovery import V2HealthRecovery

    recovery = V2HealthRecovery(
        vehicle_id=vehicle_id,
        utc_now=lambda: utc_now,
        monotonic_now=lambda: receipt_seconds,
    )
    for step in (fault_step, recovery_step):
        utc_now = datetime.fromisoformat(step["now"])
        receipt_seconds = (utc_now - epoch).total_seconds()
        observation = step["observation"].copy()
        observation.pop("fixtureLabel")
        result = recovery.process(observation)
        assert [result["health"], result["recoveryState"]] == step["expected"]
        assert result["faults"] == ["LIDAR_OBSTRUCTION"]

    started_at = result["recoveryStartedAt"]
    assert datetime.fromisoformat(started_at) == datetime.fromisoformat(
        recovery_step["observation"]["sourceTimestamp"]
    )
    accepted = recovery._latest
    accepted_ids = frozenset(recovery._accepted_event_ids)

    for step in (at_boundary, beyond_boundary):
        assert "observation" not in step
        # Leave UTC frozen at the last observation. Only receipt-clock time advances.
        receipt_seconds = (datetime.fromisoformat(step["now"]) - epoch).total_seconds()
        snapshot = recovery.evaluate_silence()

        assert [snapshot["health"], snapshot["recoveryState"], snapshot["sourceSilent"]] == step[
            "expected"
        ]
        assert snapshot["vehicleId"] == vehicle_id
        assert snapshot["faults"] == ["LIDAR_OBSTRUCTION"]
        expected_start = None if step["expected"][2] else started_at
        assert snapshot["recoveryStartedAt"] == expected_start
        assert "eventId" not in snapshot
        assert "sourceTimestamp" not in snapshot
        assert recovery._latest == accepted
        assert recovery._accepted_event_ids == accepted_ids


def test_recovery_requires_new_full_interval_after_clock_only_silence(monkeypatch):
    app_dir = Path(__file__).resolve().parents[1]
    fixture = app_dir.parents[1] / "tests/fixtures/v2/sequences/source-silence.json"
    fault_step, recovering_step, _, silent_step, _ = json.loads(
        fixture.read_text(encoding="utf-8")
    )["steps"]
    epoch = datetime.fromisoformat(fault_step["now"])
    utc_now = epoch
    receipt_seconds = 0.0

    monkeypatch.syspath_prepend(str(app_dir / "src"))
    from v2_health_recovery import V2HealthRecovery

    vehicle_id = fault_step["observation"]["vehicleId"]
    recovery = V2HealthRecovery(vehicle_id, lambda: utc_now, lambda: receipt_seconds)
    active_faults = ["LIDAR_OBSTRUCTION"]

    def deliver(observation, now):
        nonlocal utc_now, receipt_seconds
        utc_now = now
        receipt_seconds = (now - epoch).total_seconds()
        payload = observation.copy()
        payload.pop("fixtureLabel")
        result = recovery.process(payload)
        for field in ("vehicleId", "eventId", "sourceTimestamp", "sessionId", "sessionGeneration"):
            assert result[field] == payload[field]
        return result

    for step in (fault_step, recovering_step):
        result = deliver(step["observation"], datetime.fromisoformat(step["now"]))
        assert [result["health"], result["recoveryState"]] == step["expected"]
        assert result["faults"] == active_faults

    original_start = datetime.fromisoformat(result["recoveryStartedAt"])
    assert original_start == datetime.fromisoformat(recovering_step["observation"]["sourceTimestamp"])
    original_deadline = original_start + timedelta(seconds=2)
    accepted, _, health, faults, ledger = accepted_recovery_state(recovery)

    receipt_seconds = (datetime.fromisoformat(silent_step["now"]) - epoch).total_seconds()
    first_silence = recovery.evaluate_silence()
    assert [first_silence[key] for key in ("health", "recoveryState", "sourceSilent")] == silent_step[
        "expected"
    ]
    assert first_silence["vehicleId"] == vehicle_id
    assert first_silence["faults"] == active_faults
    assert first_silence["recoveryStartedAt"] is None
    assert "eventId" not in first_silence
    assert "sourceTimestamp" not in first_silence
    assert accepted_recovery_state(recovery) == (accepted, None, health, faults, ledger)

    receipt_seconds += 0.050
    assert recovery.evaluate_silence() == first_silence
    assert accepted_recovery_state(recovery) == (accepted, None, health, faults, ledger)

    template = recovering_step["observation"]
    new_start = epoch + timedelta(milliseconds=700)
    new_deadline = new_start + timedelta(seconds=2)
    samples = (
        new_start,
        epoch + timedelta(milliseconds=1100),
        epoch + timedelta(milliseconds=1600),
        original_deadline,
        epoch + timedelta(milliseconds=2600),
        new_deadline - timedelta(milliseconds=1),
        new_deadline,
    )
    assert original_start < new_start < original_deadline < new_deadline
    for index, source in enumerate(samples, start=1):
        timestamp = source.isoformat(timespec="milliseconds").replace("+00:00", "Z")
        observation = {
            **template,
            "eventId": f"{vehicle_id}-post-silence-{index}",
            "sequence": template["sequence"] + index,
            "frame": template["frame"] + index,
            "simulationSeconds": template["simulationSeconds"] + (source - original_start).total_seconds(),
            "sourceTimestamp": timestamp,
            "processingTimestamp": timestamp,
        }
        result = deliver(observation, source)
        assert result["sourceSilent"] is False
        if source < new_deadline:
            assert (result["health"], result["recoveryState"]) == ("CRITICAL", "IN_PROGRESS")
            assert result["faults"] == active_faults
            assert datetime.fromisoformat(result["recoveryStartedAt"]) == new_start
        else:
            assert (result["health"], result["recoveryState"]) == ("HEALTHY", "NONE")
            assert result["faults"] == []
            assert result["recoveryStartedAt"] is None


def test_clock_only_silence_is_isolated_per_vehicle(monkeypatch):
    app_dir = Path(__file__).resolve().parents[1]
    fixture = app_dir.parents[1] / "tests/fixtures/v2/sequences/source-silence.json"
    steps = json.loads(fixture.read_text(encoding="utf-8"))["steps"]
    epoch = datetime.fromisoformat(steps[0]["now"])
    first_id, second_id = "vehicle-001", steps[0]["observation"]["vehicleId"]
    utc = {first_id: epoch, second_id: epoch}
    receipt = {first_id: 0.0, second_id: 0.0}

    monkeypatch.syspath_prepend(str(app_dir / "src"))
    from v2_health_recovery import V2HealthRecovery

    def make_engine(vehicle_id):
        return V2HealthRecovery(
            vehicle_id, lambda: utc[vehicle_id], lambda: receipt[vehicle_id]
        )

    first = make_engine(first_id)
    second = make_engine(second_id)
    fault = ["LIDAR_OBSTRUCTION"]

    def deliver(engine, vehicle_id, sequence, elapsed, template):
        utc[vehicle_id] = epoch + elapsed
        receipt[vehicle_id] = elapsed.total_seconds()
        timestamp = utc[vehicle_id].isoformat(timespec="milliseconds").replace("+00:00", "Z")
        observation = {
            **template,
            "vehicleId": vehicle_id,
            "eventId": f"{vehicle_id}-silence-isolation-{sequence}",
            "sessionId": f"{vehicle_id}-session",
            "sequence": sequence,
            "frame": steps[0]["observation"]["frame"] + sequence,
            "simulationSeconds": steps[0]["observation"]["simulationSeconds"] + elapsed.total_seconds(),
            "sourceTimestamp": timestamp,
            "processingTimestamp": timestamp,
        }
        observation.pop("fixtureLabel")
        result = engine.process(observation)
        for field in ("vehicleId", "eventId", "sourceTimestamp", "sessionId", "sessionGeneration"):
            assert result[field] == observation[field]
        return result

    for engine, vehicle_id in ((first, first_id), (second, second_id)):
        for sequence, step in enumerate(steps[:2]):
            elapsed = datetime.fromisoformat(step["now"]) - epoch
            result = deliver(engine, vehicle_id, sequence, elapsed, step["observation"])
            assert [result["health"], result["recoveryState"]] == step["expected"]
            assert result["faults"] == fault
            assert result["sourceSilent"] is False

    first_before = accepted_recovery_state(first)
    first_clocks = utc[first_id], receipt[first_id]
    second_latest, _, second_health, second_faults, second_ledger = accepted_recovery_state(second)

    silent_step = steps[3]
    receipt[second_id] = (datetime.fromisoformat(silent_step["now"]) - epoch).total_seconds()
    assert second.evaluate_silence() == {
        "vehicleId": second_id,
        "sourceSilent": True,
        "health": "CRITICAL",
        "faults": fault,
        "recoveryState": "NONE",
        "recoveryStartedAt": None,
    }
    second_after = (second_latest, None, second_health, second_faults, second_ledger)
    assert accepted_recovery_state(second) == second_after
    assert accepted_recovery_state(first) == first_before
    assert (utc[first_id], receipt[first_id]) == first_clocks

    original_start = first_before[1]
    for sequence, offset_ms in enumerate((500, 1000, 1500, 1999, 2000), start=2):
        elapsed = original_start - epoch + timedelta(milliseconds=offset_ms)
        result = deliver(first, first_id, sequence, elapsed, steps[1]["observation"])
        if offset_ms < 2000:
            assert (result["health"], result["recoveryState"], result["faults"]) == (
                "CRITICAL", "IN_PROGRESS", fault,
            )
            assert datetime.fromisoformat(result["recoveryStartedAt"]) == original_start
        else:
            assert (result["health"], result["recoveryState"], result["faults"]) == (
                "HEALTHY", "NONE", [],
            )
            assert result["recoveryStartedAt"] is None
        assert accepted_recovery_state(second) == second_after


@pytest.mark.parametrize(
    ("bad_source_ms", "bad_receipt_ms", "age_ms", "restart_ms"),
    [(375, 5376, 5001, 5500), (1501, 500, -1001, 875)],
    ids=["stale", "future"],
)
def test_freshness_rejection_resets_recovery_without_replacing_accepted_observation(
    replay_session, bad_source_ms, bad_receipt_ms, age_ms, restart_ms,
):
    _, make_engine, observation = replay_session
    fault = ["LIDAR_OBSTRUCTION"]
    obstruction = observation(0)
    engine = make_engine()
    other_id = "vehicle-002" if obstruction["vehicleId"] != "vehicle-002" else "vehicle-001"
    other = make_engine(other_id)
    other.process(dict(obstruction, vehicleId=other_id, sessionId="unaffected-session"))
    other_before = accepted_recovery_state(other)

    initial = engine.process(obstruction)
    assert (initial["health"], initial["faults"], initial["recoveryState"]) == (
        "CRITICAL", fault, "NONE",
    )
    healthy = observation(2, distance=20)
    partial = engine.process(healthy)
    assert (partial["health"], partial["faults"], partial["recoveryState"]) == (
        "CRITICAL", fault, "IN_PROGRESS",
    )
    identity_fields = ("lidar", "eventId", "sourceTimestamp", "sequence", "frame",
                       "vehicleId", "sessionId", "sessionGeneration")
    assert {key: partial[key] for key in identity_fields} == {
        key: healthy[key] for key in identity_fields
    }
    latest, original_start, health, faults, ledger = accepted_recovery_state(engine)

    rejected = observation(
        9, distance=31, source_ms=bad_source_ms, receipt_ms=bad_receipt_ms, age_ms=age_ms,
    )
    response = engine.process(rejected)

    assert engine._started_at is None
    assert (engine._health, engine._faults) == ("CRITICAL", fault)
    assert engine._latest == latest, "Freshness rejection replaced the last accepted observation"
    assert accepted_recovery_state(engine) == (latest, None, health, faults, ledger)
    assert response["recoveryState"] == "NONE"
    assert response["recoveryStartedAt"] is None
    assert (response["health"], response["faults"]) == ("CRITICAL", fault)
    assert {key: response[key] for key in identity_fields} == {
        key: healthy[key] for key in identity_fields
    }

    # No delivery at this tick. The rejected receipt cannot postpone silence.
    observation(10, source_ms=restart_ms - 1, receipt_ms=restart_ms - 1)
    status = engine.evaluate_silence()
    assert status["sourceSilent"] is True
    assert status["recoveryState"] == "NONE"
    assert status["recoveryStartedAt"] is None
    assert (status["health"], status["faults"]) == ("CRITICAL", fault)
    assert accepted_recovery_state(other) == other_before

    for index, offset in enumerate((0, 500, 1000, 1500, 1999, 2000), start=3):
        sample = observation(index, distance=20, source_ms=restart_ms + offset)
        result = engine.process(sample)
        if offset == 0:
            new_start = datetime.fromisoformat(sample["sourceTimestamp"])
            assert new_start > original_start
        if offset < 2000:
            assert (result["health"], result["faults"], result["recoveryState"]) == (
                "CRITICAL", fault, "IN_PROGRESS",
            )
            assert datetime.fromisoformat(result["recoveryStartedAt"]) == new_start
        else:
            assert (result["health"], result["faults"], result["recoveryState"]) == (
                "HEALTHY", [], "NONE",
            )
            assert result["recoveryStartedAt"] is None
        assert accepted_recovery_state(other) == other_before

    completed = accepted_recovery_state(engine)
    with pytest.raises(ValueError, match="duplicate event ID"):
        engine.process(healthy)
    with pytest.raises(ValueError, match="out-of-order observation"):
        engine.process(dict(healthy, eventId="distinct-but-out-of-order"))
    assert accepted_recovery_state(engine) == completed
