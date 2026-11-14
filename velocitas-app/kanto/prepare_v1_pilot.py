"""Non-deploying B5 preparation. Default dry-run never invokes external commands."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

from render_pilot_config import DEFAULT_CONFIG, SafeParser, load_config, render_descriptor


def check_cli_support(*, runner=None, finder=None):
    """Read local CLI help only. This is not permission or proof of deployability."""
    runner = runner or subprocess.run
    executable = (finder or shutil.which)('kanto-cm')
    if not executable:
        raise ValueError('Kanto CLI is unavailable')
    for command in ([], ['create'], ['get'], ['start'], ['stop']):
        result = runner([executable, *command, '--help'], capture_output=True, text=True,
                        timeout=5, check=False)
        if result.returncode != 0:
            raise ValueError('Required Kanto CLI help is unsupported')
        if not command and not all(word in result.stdout.lower() for word in ('kanto', 'create', 'get', 'start', 'stop')):
            raise ValueError('Unexpected CLI capabilities')
    return 'HELP_CHECKS_PASSED'


def preparation_plan(descriptor, cli_support='NOT_CHECKED'):
    name = descriptor['container_name']
    return {
        'mode': 'dry-run', 'execution_permitted': False, 'cli_support': cli_support,
        'descriptor': descriptor,
        'lifecycle': [{'operation': operation, 'container_name': name, 'execute': False}
                      for operation in ('inspect', 'create-if-absent', 'start', 'stop', 'start', 'inspect')],
        'blockers': [
            'Actual Linux Kanto version, create options and effective descriptor settings need review.',
            'Existing container names must be inspected; replacement is not permitted by this tool.',
            'Emmanuel V1 image, target architecture, registry access and LAN endpoints need verification.',
            'Real post-restart MQTT and matching Ditto evidence are pending.']}


def main(argv=None, *, runner=None, finder=None):
    parser = SafeParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    parser.add_argument('--mode', choices=('validate', 'render', 'dry-run'), default='dry-run')
    parser.add_argument('--check-cli', action='store_true', help='Read local Kanto help only; never deploy')
    args = parser.parse_args(argv)
    try:
        descriptor = render_descriptor(load_config(args.config))
        if args.check_cli and args.mode != 'dry-run':
            raise ValueError('CLI checks require dry-run mode')
        cli_support = check_cli_support(runner=runner, finder=finder) if args.check_cli else 'NOT_CHECKED'
    except (ValueError, TypeError, OSError, OverflowError, subprocess.SubprocessError):
        print('Pilot preparation failed; configuration or local CLI help is unavailable/unsupported.', file=sys.stderr)
        return 1
    output = ({'valid': True, 'execution_permitted': False} if args.mode == 'validate' else
              descriptor if args.mode == 'render' else preparation_plan(descriptor, cli_support))
    print(json.dumps(output, ensure_ascii=False, allow_nan=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
