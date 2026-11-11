"""Development-only MQTT fixture replay/capture via Mosquitto CLI clients.

No Ditto, backend, SDK or Python MQTT package is required. Run --help.
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import contract as c

FIXTURES = Path(__file__).resolve().parents[2] / 'tests/fixtures/v1'
SCENARIOS = {
    'cycle': ['vehicle-001-healthy', 'vehicle-002-healthy', 'vehicle-002-fault', 'vehicle-002-recovered'],
    'healthy': ['vehicle-001-healthy', 'vehicle-002-healthy'],
    'fault': ['vehicle-002-fault'], 'recovery': ['vehicle-002-recovered'],
    'stale': ['vehicle-002-stale'], 'malformed': ['event-malformed'],
    'unknown': ['vehicle-unknown'], 'out-of-order': ['vehicle-002-fault', 'event-out-of-order'],
}


def replay_packets(scenario, anchor, run_id='replay-1'):
    packets = []
    for name in SCENARIOS[scenario]:
        event = json.loads((FIXTURES / (name + '.json')).read_text())
        event = c.rebase_event(event, anchor)
        event['eventId'] += '-' + run_id
        packets.append((c.topic(event['vehicleId']), event))
    return packets


def publish_packets(packets, host, port, interval=1.):
    for index, (mqtt_topic, event) in enumerate(packets):
        if index:
            time.sleep(interval)
        subprocess.run(['mosquitto_pub', '-h', host, '-p', str(port), '-q', '1',
                        '-t', mqtt_topic, '-m', json.dumps(event, allow_nan=False)], check=True, timeout=10)
        print(json.dumps({'mock': True, 'topic': mqtt_topic, 'event': event}), flush=True)


def check_lines(lines, expect_cycle=False, emit=False):
    capture = c.Capture() if expect_cycle else c.EventStream()
    count = 0
    for line in lines:
        mqtt_topic, separator, payload = line.rstrip('\n').partition(' ')
        c.require(bool(separator), 'MALFORMED_JSON', 'expected topic then JSON')
        try:
            event = c.decode_event(payload)
        except ValueError as error:
            raise c.ContractError('MALFORMED_JSON', str(error)) from error
        capture.accept(mqtt_topic, event)
        count += 1
        if emit:
            print(json.dumps({'topic': mqtt_topic, 'event': event}), flush=True)
    complete = isinstance(capture, c.Capture) and capture.cycle_complete()
    if expect_cycle:
        c.require(complete, 'INCOMPLETE_CYCLE', 'need vehicle-001 healthy and vehicle-002 healthy/fault/recovery')
    c.require(count > 0, 'NO_EVENTS', 'no events received')
    return dict(mockTool=True, accepted=count, cycleComplete=complete)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['publish', 'capture', 'check', 'render'])
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=18883)
    parser.add_argument('--scenario', choices=SCENARIOS, default='cycle')
    parser.add_argument('--anchor', help='fixture epoch as UTC time; default current time minus four seconds')
    parser.add_argument('--run-id', default='replay-1')
    parser.add_argument('--interval', type=float, default=1.)
    parser.add_argument('--timeout', type=int, default=120)
    parser.add_argument('--expect-cycle', action='store_true')
    args = parser.parse_args()
    if args.interval < 0 or args.timeout <= 0:
        parser.error('interval must be nonnegative and timeout positive')
    try:
        anchor = c.parse_timestamp(args.anchor) if args.anchor else datetime.now(timezone.utc) - c.timedelta(seconds=4)
        packets = replay_packets(args.scenario, anchor, args.run_id)
        if args.command == 'render':
            for mqtt_topic, event in packets:
                print(mqtt_topic + ' ' + json.dumps(event))
        elif args.command == 'publish':
            publish_packets(packets, args.host, args.port, args.interval)
        elif args.command == 'check':
            print(json.dumps(check_lines(sys.stdin, args.expect_cycle)))
        else:
            # -F emits one topic + compact JSON payload per line; V1 events are single-line JSON.
            cmd = ['mosquitto_sub', '-h', args.host, '-p', str(args.port), '-q', '1',
                   '-t', c.topic('vehicle-001'), '-t', c.topic('vehicle-002'),
                   '-F', '%t %p', '-W', str(args.timeout)]
            with subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True) as process:
                try:
                    result = check_lines(process.stdout, args.expect_cycle, emit=True)
                    code = process.wait(timeout=2)
                    c.require(code in (0, 27), 'MQTT_CONNECTION', f'mosquitto_sub exit {code}')
                    print(json.dumps(result))
                finally:
                    if process.poll() is None:
                        process.terminate(); process.wait(timeout=5)
    except (c.ContractError, OSError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
