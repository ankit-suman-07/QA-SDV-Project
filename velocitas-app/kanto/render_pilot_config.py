"""Pure, secret-free V1 Kanto pilot configuration rendering; no deployment."""
import argparse
import copy
import ipaddress
import json
import math
from pathlib import Path
import re
import sys

DEFAULT_CONFIG = Path(__file__).with_name('pilot-config.example.json')
FIELDS = {'vehicle_id', 'container_name', 'image', 'remote_lan', 'kuksa_host',
          'kuksa_port', 'mqtt_host', 'mqtt_port', 'poll_interval_seconds', 'restart_policy'}


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(2, 'Invalid preparation arguments; use --help.\n')


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def load_config(path):
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, 'Duplicate configuration field')
            result[key] = value
        return result
    def nonfinite(_value):
        raise ValueError('Non-finite configuration number')
    return json.loads(Path(path).read_text(encoding='utf-8'),
                      object_pairs_hook=pairs, parse_constant=nonfinite)


def _host(value, remote):
    _require(isinstance(value, str) and value == value.strip() and bool(value) and '%' not in value,
             'Invalid endpoint host')
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        host = value.lower().rstrip('.')
        # Legacy IPv4 parsers accept short, octal and mixed hexadecimal forms.
        # Never let an all-numeric component sequence fall through as DNS after
        # strict ipaddress parsing failed; reject it in both remote/local modes.
        numeric_component = r'(?:[0-9]+|0x[0-9a-f]+)'
        _require(not re.fullmatch(numeric_component + r'(?:\.' + numeric_component + r')*', host),
                 'Invalid numeric endpoint address')
        _require(len(host) <= 253 and all(re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', part)
                                        for part in host.split('.')), 'Invalid endpoint host')
        _require(not remote or (host not in ('localhost', 'localhost.localdomain', 'localhost6',
                                            'ip6-localhost', 'ip6-loopback') and not host.endswith('.localhost')),
                 'Loopback endpoints are not allowed in remote-LAN mode')
        return host
    mapped = getattr(address, 'ipv4_mapped', None) or address
    _require(not mapped.is_unspecified and not mapped.is_multicast, 'Invalid endpoint address')
    _require(not remote or (not mapped.is_loopback and not mapped.is_link_local),
             'Loopback/link-local endpoints are not allowed in remote-LAN mode')
    return address.compressed


def _port(value):
    _require(type(value) is int and 1 <= value <= 65535, 'Port must be an integer from 1 through 65535')
    return value


def _image(value):
    _require(isinstance(value, str) and re.fullmatch(
        r'(?:[a-z0-9.-]+(?::[0-9]{1,5})?/)?'
        r'[a-z0-9]+(?:[._-][a-z0-9]+)*(?:/[a-z0-9]+(?:[._-][a-z0-9]+)*)*'
        r'(?::[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}|@sha256:[0-9a-f]{64})', value),
        'Image must be an explicit tagged or sha256 OCI reference')
    _require(not value.rsplit(':', 1)[-1].lower() == 'latest', 'Mutable latest image tag is not allowed')
    registry = value.split('/')[0]
    if '/' in value and ':' in registry:
        _port(int(registry.rsplit(':', 1)[1]))
    return value


def render_descriptor(config):
    """Return a validated descriptor. Unknown/secret/env fields are never accepted."""
    _require(isinstance(config, dict) and set(config) == FIELDS, 'Missing or unsupported configuration fields')
    _require(config['vehicle_id'] == 'vehicle-002', 'V1 pilot must identify vehicle-002')
    name = config['container_name']
    _require(isinstance(name, str) and len(name) <= 100 and re.fullmatch(
        r'autonomoushealthapp-vehicle-002(?:-[a-z0-9]+(?:-[a-z0-9]+)*)?', name), 'Invalid pilot container name')
    image = _image(config['image'])
    remote = config['remote_lan']
    _require(type(remote) is bool, 'remote_lan must be boolean')
    kuksa_host = _host(config['kuksa_host'], remote)
    mqtt_host = _host(config['mqtt_host'], remote)
    kuksa_port, mqtt_port = _port(config['kuksa_port']), _port(config['mqtt_port'])
    interval = config['poll_interval_seconds']
    _require(type(interval) in (int, float), 'Polling interval must be finite and positive')
    try:
        interval = float(interval)
    except OverflowError as error:
        raise ValueError('Polling interval must be finite and positive') from error
    _require(math.isfinite(interval) and interval > 0, 'Polling interval must be finite and positive')
    restart = config['restart_policy']
    _require(isinstance(restart, dict) and set(restart) == {'type', 'maximum_retry_count', 'retry_timeout'},
             'Invalid restart configuration')
    _require(restart['type'] in ('unless-stopped', 'always'), 'Unsupported V1 restart policy')
    for key in ('maximum_retry_count', 'retry_timeout'):
        _require(type(restart[key]) is int and restart[key] == 0,
                 'V1 restart retry settings must be zero for the selected policy')
    def authority(host, port):
        return f'[{host}]:{port}' if ':' in host else f'{host}:{port}'
    return {
        'container_name': name,
        'image': {'name': image},
        'host_config': {'devices': [], 'network_mode': 'host', 'privileged': False,
                        'restart_policy': copy.deepcopy(restart)},
        'config': {'env': [
            'SDV_MIDDLEWARE_TYPE=native',
            'SDV_VEHICLEDATABROKER_ADDRESS=grpc://' + authority(kuksa_host, kuksa_port),
            'SDV_MQTT_ADDRESS=mqtt://' + authority(mqtt_host, mqtt_port),
            'DATABROKER_HOST=' + kuksa_host, 'DATABROKER_PORT=' + str(kuksa_port),
            'SIMULATED_VEHICLE_ID=vehicle-002',
            'AUTONOMOUS_HEALTH_POLL_INTERVAL_SECONDS=' + str(float(interval))]}}


def main(argv=None):
    parser = SafeParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args(argv)
    try:
        descriptor = render_descriptor(load_config(args.config))
    except (ValueError, TypeError, OSError, OverflowError):
        print('Invalid or unreadable pilot configuration; no output generated.', file=sys.stderr)
        return 1
    print(json.dumps(descriptor, ensure_ascii=False, allow_nan=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
