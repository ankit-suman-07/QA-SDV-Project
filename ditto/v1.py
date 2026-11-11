"""Run B1+B2 or provision/read the two individual twins: python -m ditto.v1."""
import argparse
import json
import logging

from ditto.mqtt_ingress import Ingress, VEHICLES
from ditto.mqtt_subscriber import MqttConfig, Subscriber
from ditto.v1_writer import DittoConfig, DittoError, DittoWriter

LOG = logging.getLogger(__name__)


def main(argv=None, *, writer_factory=DittoWriter, subscriber_factory=Subscriber):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    provision = commands.add_parser('provision', help='Create absent policies/Things; never replace existing ones')
    provision.add_argument('--subject', required=True, help='Authenticated Ditto subject, e.g. nginx:<username>')
    read = commands.add_parser('read', help='Validate/read whole individual Things')
    read.add_argument('vehicle_id', choices=VEHICLES + ('all',), default='all', nargs='?')
    commands.add_parser('run', help='Run the MQTT subscriber with the authenticated Ditto writer')
    args = parser.parse_args(argv)
    try:
        writer = writer_factory(DittoConfig.from_env())
        if args.command == 'provision':
            writer.provision(args.subject)
            LOG.info('individual_twin_provisioning_verified')
        elif args.command == 'read':
            vehicles = VEHICLES if args.vehicle_id == 'all' else (args.vehicle_id,)
            print(json.dumps([writer.read_thing(vehicle) for vehicle in vehicles], indent=2))
        else:
            subscriber = subscriber_factory(Ingress(writer), MqttConfig.from_env())
            try:
                subscriber.run()
            except KeyboardInterrupt:
                pass
            finally:
                subscriber.stop()
    except DittoError as error:
        LOG.error('ditto_failure code=%s status=%s', error.code, error.status)
        return 1
    except (ValueError, OSError, RuntimeError, ImportError) as error:
        # No dependency exception text/tracebacks: requests may include credentials.
        LOG.error('startup_or_runtime_failure type=%s', type(error).__name__)
        return 1
    return 0


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    raise SystemExit(main())
