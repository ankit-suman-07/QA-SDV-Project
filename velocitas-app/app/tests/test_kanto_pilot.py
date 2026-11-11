"""B5 static/mock preparation checks; no Kanto, Docker or broker execution."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock, patch

import pytest

KANTO = Path(__file__).resolve().parents[2] / 'kanto'


def module(name):
    path = KANTO / (name + '.py')
    assert path.exists(), 'B5 preparation module missing: ' + name
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    with patch.object(sys, 'path', [str(KANTO), *sys.path]):
        spec.loader.exec_module(result)
    return result


def example():
    return json.loads((KANTO / 'pilot-config.example.json').read_text(encoding='utf-8'))


def test_vehicle_002_descriptor_identity_endpoints_and_restart():
    renderer = module('render_pilot_config')
    config = example()
    descriptor = renderer.render_descriptor(config)
    assert descriptor['container_name'] == 'autonomoushealthapp-vehicle-002'
    assert descriptor['image']['name'] == config['image']
    env = dict(entry.split('=', 1) for entry in descriptor['config']['env'])
    assert len(env) == len(descriptor['config']['env'])
    assert env['SIMULATED_VEHICLE_ID'] == 'vehicle-002'
    assert env['SDV_VEHICLEDATABROKER_ADDRESS'] == 'grpc://192.0.2.10:55557'
    assert env['DATABROKER_HOST'] == '192.0.2.10'
    assert env['DATABROKER_PORT'] == '55557'
    assert env['SDV_MQTT_ADDRESS'] == 'mqtt://192.0.2.10:1883'
    assert env['AUTONOMOUS_HEALTH_POLL_INTERVAL_SECONDS'] == '2.0'
    assert descriptor['host_config']['restart_policy'] == config['restart_policy']
    assert descriptor['host_config']['network_mode'] == 'host'
    assert descriptor['host_config']['privileged'] is False
    assert descriptor['host_config']['devices'] == []
    assert config == example()  # rendering never changes its input


def test_dedicated_checked_in_descriptor_equals_renderer():
    renderer = module('render_pilot_config')
    assert json.loads((KANTO / 'autonomous-health-app-v1.json').read_text()) == renderer.render_descriptor(example())
    legacy = json.loads((KANTO / 'autonomous-health-app.json').read_text())
    assert legacy['container_name'] == 'autonomoushealthapp'
    assert 'SIMULATED_VEHICLE_ID=vehicle-001' in legacy['config']['env']


@pytest.mark.parametrize('key,value', [
    ('vehicle_id', 'vehicle-001'), ('vehicle_id', ' vehicle-002'),
    ('container_name', 'autonomoushealthapp'), ('container_name', 'pilot;command'),
    ('kuksa_port', 0), ('kuksa_port', 65536), ('mqtt_port', True), ('mqtt_port', '1883'),
    ('poll_interval_seconds', 0), ('poll_interval_seconds', float('nan')),
    ('poll_interval_seconds', float('inf')), ('poll_interval_seconds', True),
    pytest.param('poll_interval_seconds', 10 ** 400, id='poll-overflow'),
    ('image', ''), ('image', 'repo/app:latest'), ('image', 'repo/app'),
    ('image', 'https://user:password@registry/app:tag'), ('remote_lan', 'true'),
    ('kuksa_host', 'host:55557'), ('mqtt_host', 'mqtt://host'),
    ('mqtt_host', 'user:password@broker'), ('kuksa_host', '2001:db8::10%eth0'),
])
def test_invalid_pilot_settings_fail(key, value):
    renderer = module('render_pilot_config')
    config = example()
    config[key] = value
    with pytest.raises(ValueError):
        renderer.render_descriptor(config)


@pytest.mark.parametrize('host', ['localhost', 'LOCALHOST.', 'a.localhost', '127.0.0.1',
                                 '127.8.9.10', '::1', '::ffff:127.0.0.1', '0.0.0.0', '::',
                                 'localhost.localdomain', 'ip6-localhost', '127.1', '2130706433', '0x7f000001'])
def test_remote_lan_rejects_loopback_and_unspecified(host):
    renderer = module('render_pilot_config')
    for key in ['kuksa_host', 'mqtt_host']:
        config = example()
        config[key] = host
        with pytest.raises(ValueError):
            renderer.render_descriptor(config)


@pytest.mark.parametrize('host', ['0x7f.0.0.1', '0x7f.1', '0x0.0.0.0', '127.1',
                                 '2130706433', '0x7f000001', '0177.0x0.0.1',
                                 '127.0x0.0.1', '0X7F.0.0.1', '0x7f.1.'])
@pytest.mark.parametrize('key', ['kuksa_host', 'mqtt_host'])
@pytest.mark.parametrize('remote', [True, False])
def test_ambiguous_numeric_hosts_never_reach_descriptor(key, host, remote):
    renderer = module('render_pilot_config')
    config = example()
    config.update(remote_lan=remote)
    config[key] = host
    with pytest.raises(ValueError):
        renderer.render_descriptor(config)


@pytest.mark.parametrize('host,normalized', [
    ('192.168.1.20', '192.168.1.20'), ('10.0.0.8', '10.0.0.8'), ('172.16.1.9', '172.16.1.9'),
    ('kuksa.local', 'kuksa.local'), ('EDGE-002.EXAMPLE.ORG.', 'edge-002.example.org'),
    ('0x7f.example.org', '0x7f.example.org'), ('2001:db8::10', '2001:db8::10'),
    ('::ffff:192.168.1.20', '::ffff:c0a8:114')])
@pytest.mark.parametrize('key', ['kuksa_host', 'mqtt_host'])
def test_canonical_lan_and_legitimate_dns_hosts_are_preserved(key, host, normalized):
    renderer = module('render_pilot_config')
    config = example()
    config[key] = host
    descriptor = renderer.render_descriptor(config)
    env = dict(entry.split('=', 1) for entry in descriptor['config']['env'])
    authority = '[' + normalized + ']' if ':' in normalized else normalized
    if key == 'kuksa_host':
        assert env['DATABROKER_HOST'] == normalized
        assert env['SDV_VEHICLEDATABROKER_ADDRESS'] == f'grpc://{authority}:55557'
    else:
        assert env['SDV_MQTT_ADDRESS'] == f'mqtt://{authority}:1883'


@pytest.mark.parametrize('host', ['::ffff:127.0.0.1', '::ffff:7f00:1',
                                 '0:0:0:0:0:ffff:7f00:1', '::ffff:0.0.0.0',
                                 '::ffff:224.0.0.1', '::ffff:169.254.1.2'])
@pytest.mark.parametrize('key', ['kuksa_host', 'mqtt_host'])
def test_mapped_ipv6_uses_underlying_ipv4_restrictions(key, host):
    renderer = module('render_pilot_config')
    config = example()
    config[key] = host
    with pytest.raises(ValueError):
        renderer.render_descriptor(config)


@pytest.mark.parametrize('host', ['127.0.0.1', 'localhost', '::1', '::ffff:127.0.0.1'])
@pytest.mark.parametrize('key', ['kuksa_host', 'mqtt_host'])
def test_explicit_local_mode_allows_canonical_loopback(key, host):
    renderer = module('render_pilot_config')
    config = example()
    config['remote_lan'] = False
    config[key] = host
    renderer.render_descriptor(config)


def test_preparation_rejects_ambiguous_hosts_before_any_cli_check(capsys):
    prepare = module('prepare_v1_pilot')
    runner = Mock(side_effect=AssertionError('unexpected execution'))
    finder = Mock(side_effect=AssertionError('unexpected CLI discovery'))
    for key in ['kuksa_host', 'mqtt_host']:
        config = example()
        config[key] = '0x7f.1'
        with patch.object(prepare, 'load_config', return_value=config):
            assert prepare.main(['--check-cli'], runner=runner, finder=finder) == 1
        assert not capsys.readouterr().out
    runner.assert_not_called()
    finder.assert_not_called()


def test_local_mode_and_configurable_lan_ipv6_endpoints():
    renderer = module('render_pilot_config')
    config = example()
    config.update(remote_lan=False, kuksa_host='127.0.0.1', mqtt_host='localhost')
    renderer.render_descriptor(config)
    config.update(remote_lan=True, kuksa_host='2001:db8::10', kuksa_port=55558,
                  mqtt_host='broker.example.org', mqtt_port=18883)
    env = dict(entry.split('=', 1) for entry in renderer.render_descriptor(config)['config']['env'])
    assert env['SDV_VEHICLEDATABROKER_ADDRESS'] == 'grpc://[2001:db8::10]:55558'
    assert env['SDV_MQTT_ADDRESS'] == 'mqtt://broker.example.org:18883'


@pytest.mark.parametrize('restart', [None, {}, {'type': 'no'},
    {'type': 'unless-stopped', 'maximum_retry_count': -1, 'retry_timeout': 0},
    {'type': 'unless-stopped', 'maximum_retry_count': 0, 'retry_timeout': True}])
def test_invalid_restart_policy_is_rejected(restart):
    renderer = module('render_pilot_config')
    config = example()
    config['restart_policy'] = restart
    with pytest.raises(ValueError):
        renderer.render_descriptor(config)


def test_secret_and_arbitrary_environment_fields_are_not_supported():
    renderer = module('render_pilot_config')
    for field in ['password', 'token', 'env', 'mqtt_password']:
        config = example()
        config[field] = 'must-not-appear'
        with pytest.raises(ValueError) as caught:
            renderer.render_descriptor(config)
        assert 'must-not-appear' not in str(caught.value)


def test_default_preparation_has_no_subprocess_and_matches_descriptor(capsys):
    prepare = module('prepare_v1_pilot')
    with patch.object(prepare.subprocess, 'run', side_effect=AssertionError('unexpected execution')):
        assert prepare.main([]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan['mode'] == 'dry-run'
    assert plan['execution_permitted'] is False
    assert plan['descriptor'] == module('render_pilot_config').render_descriptor(example())
    assert all(step['container_name'] == plan['descriptor']['container_name'] for step in plan['lifecycle'])
    assert plan['cli_support'] == 'NOT_CHECKED'


def test_cli_capabilities_are_only_checked_with_help_and_never_deploy(capsys):
    prepare = module('prepare_v1_pilot')
    def run(args, **kwargs):
        assert args[-1] == '--help'
        return subprocess.CompletedProcess(args, 0, stdout='Eclipse Kanto create get start stop', stderr='')
    fake = Mock(side_effect=run)
    assert prepare.main(['--check-cli'], runner=fake, finder=lambda _: '/test/kanto-cm') == 0
    calls = [call.args[0] for call in fake.call_args_list]
    assert calls == [['/test/kanto-cm', '--help']] + [
        ['/test/kanto-cm', command, '--help'] for command in ['create', 'get', 'start', 'stop']]
    plan = json.loads(capsys.readouterr().out)
    assert plan['cli_support'] == 'HELP_CHECKS_PASSED'
    assert plan['execution_permitted'] is False


def test_missing_or_unsupported_cli_fails_without_mutation(capsys):
    prepare = module('prepare_v1_pilot')
    fake = Mock()
    assert prepare.main(['--check-cli'], runner=fake, finder=lambda _: None) == 1
    fake.assert_not_called()
    failed = Mock(return_value=subprocess.CompletedProcess([], 1, stdout='', stderr='private details'))
    assert prepare.main(['--check-cli'], runner=failed, finder=lambda _: '/test/kanto-cm') == 1
    assert 'private details' not in capsys.readouterr().err


def test_cli_timeout_is_bounded_and_redacted(capsys):
    prepare = module('prepare_v1_pilot')
    fake = Mock(side_effect=subprocess.TimeoutExpired('private details', 5))
    assert prepare.main(['--check-cli'], runner=fake, finder=lambda _: '/test/kanto-cm') == 1
    assert fake.call_args.kwargs['timeout'] == 5
    assert 'private details' not in capsys.readouterr().err


def test_deploy_option_is_not_available():
    prepare = module('prepare_v1_pilot')
    with pytest.raises(SystemExit) as caught:
        prepare.main(['--deploy'])
    assert caught.value.code == 2


def test_unsupported_secret_arguments_are_redacted(capsys):
    for name in ['prepare_v1_pilot', 'render_pilot_config']:
        tool = module(name)
        with pytest.raises(SystemExit) as caught:
            tool.main(['--password', 'must-not-appear'])
        assert caught.value.code == 2
        assert 'must-not-appear' not in capsys.readouterr().err


def test_cli_does_not_read_or_echo_environment_secrets(capsys):
    prepare = module('prepare_v1_pilot')
    with patch.dict('os.environ', {'SDV_MQTT_PASSWORD': 'must-not-appear', 'TOKEN': 'must-not-appear'}):
        assert prepare.main([]) == 0
    captured = capsys.readouterr()
    assert 'must-not-appear' not in captured.out + captured.err


def test_cli_check_stops_on_wrong_binary_and_subcommand_failure(capsys):
    prepare = module('prepare_v1_pilot')
    wrong = Mock(return_value=subprocess.CompletedProcess([], 0, stdout='not the expected program', stderr=''))
    assert prepare.main(['--check-cli'], runner=wrong, finder=lambda _: '/test/kanto-cm') == 1
    assert wrong.call_count == 1
    partial = Mock(side_effect=[
        subprocess.CompletedProcess([], 0, stdout='Kanto create get start stop', stderr=''),
        subprocess.CompletedProcess([], 1, stdout='', stderr='private details')])
    assert prepare.main(['--check-cli'], runner=partial, finder=lambda _: '/test/kanto-cm') == 1
    assert partial.call_count == 2
    assert 'private details' not in capsys.readouterr().err


def test_validate_and_render_modes_never_invoke_commands(capsys):
    prepare = module('prepare_v1_pilot')
    runner = Mock(side_effect=AssertionError('unexpected execution'))
    for mode in ['validate', 'render']:
        assert prepare.main(['--mode', mode], runner=runner) == 0
        output = json.loads(capsys.readouterr().out)
        if mode == 'validate':
            assert output == {'valid': True, 'execution_permitted': False}
        else:
            assert output == module('render_pilot_config').render_descriptor(example())
    runner.assert_not_called()


def test_configuration_load_failures_are_redacted_before_cli_checks(capsys):
    prepare = module('prepare_v1_pilot')
    runner = Mock(side_effect=AssertionError('unexpected execution'))
    with patch.object(prepare, 'load_config', side_effect=ValueError('must-not-appear')):
        assert prepare.main(['--check-cli'], runner=runner) == 1
    runner.assert_not_called()
    assert 'must-not-appear' not in capsys.readouterr().err


@pytest.mark.parametrize('raw', ['{"vehicle_id":"vehicle-002","vehicle_id":"vehicle-001"}',
                               '{"poll_interval_seconds":NaN}', '[]'])
def test_strict_config_json_rejects_duplicates_nonfinite_and_nonobjects(raw):
    renderer = module('render_pilot_config')
    with patch.object(renderer.Path, 'read_text', return_value=raw), pytest.raises(ValueError):
        renderer.render_descriptor(renderer.load_config('not-read.json'))


def test_explicit_always_policy_and_digest_image_are_preserved():
    renderer = module('render_pilot_config')
    config = example()
    config['restart_policy']['type'] = 'always'
    config['image'] = 'registry.example.org/sdv/app@sha256:' + 'a' * 64
    descriptor = renderer.render_descriptor(config)
    assert descriptor['host_config']['restart_policy']['type'] == 'always'
    assert descriptor['image']['name'] == config['image']
