#!/usr/bin/env python3
"""Explicit one-time fleet provisioning. Does not read or change individual twins."""
import base64
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen, build_opener, HTTPRedirectHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


# Never forward provisioning credentials to a redirect target.
urlopen = build_opener(NoRedirect()).open


def provision(base_url, username, password, owner_subject, service_subject):
    url = urlsplit(base_url)
    if (url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password
            or url.query or url.fragment or not username or not password
            or username.strip() != username or ':' in username
            or not owner_subject or not service_subject or owner_subject == service_subject):
        raise ValueError('Valid endpoint, provisioning credentials and distinct policy subjects required')
    policy = {'entries': {
        'owner': {'subjects': {owner_subject: {'type': 'provisioning administrator'}},
                  'resources': {'thing:/': {'grant': ['READ', 'WRITE'], 'revoke': []},
                                'policy:/': {'grant': ['READ', 'WRITE'], 'revoke': []}}},
        'fleet-writer': {'subjects': {service_subject: {'type': 'fleet backend service'}},
                         'resources': {'thing:/features/summary/properties':
                                       {'grant': ['READ', 'WRITE'], 'revoke': []}}}}}
    thing = {'policyId': 'sdv:fleet-v1-policy',
             'attributes': {'kind': 'fleet', 'vehicleIds': ['vehicle-001', 'vehicle-002']},
             'features': {'summary': {}}}
    auth = base64.b64encode(f'{username}:{password}'.encode()).decode()
    for resource, payload in [('policies/sdv:fleet-v1-policy', policy), ('things/sdv:fleet-v1', thing)]:
        request = Request(base_url.rstrip('/') + '/api/2/' + resource,
                          data=json.dumps(payload).encode(), method='PUT',
                          headers={'Content-Type': 'application/json', 'Authorization': 'Basic ' + auth,
                                   'If-None-Match': '*'})
        # Creation only: an existing policy/Thing fails rather than overwriting deployed state.
        with urlopen(request, timeout=5) as response:
            if response.status not in (200, 201, 204):
                raise ValueError('Unexpected provisioning response')


def main():
    try:
        provision(os.environ.get('SDV_V1_DITTO_BASE_URL', 'http://localhost:8080'),
                  os.environ.get('SDV_FLEET_PROVISION_USERNAME', ''),
                  os.environ.get('SDV_FLEET_PROVISION_PASSWORD', ''),
                  os.environ.get('SDV_FLEET_OWNER_SUBJECT', ''),
                  os.environ.get('SDV_FLEET_SERVICE_SUBJECT', ''))
    except HTTPError as error:
        print(f'Fleet provisioning failed: HTTP {error.code}. Existing resources (409/412) are preserved; inspect them before proceeding.', file=sys.stderr)
        return 1
    except (ValueError, URLError, OSError):
        print('Fleet provisioning failed: check endpoint, credentials, subjects and connectivity.', file=sys.stderr)
        return 1
    print('Created sdv:fleet-v1-policy and sdv:fleet-v1. Enable one backend fleet writer.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
