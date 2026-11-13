# B5 V1 Kanto pilot preparation: vehicle-002

Baseline: `8b3143aaa1631ee81b18042e6fb1aa34d50484dc` on
`bayan/config/v1-kanto-pilot`. This work follows
[contract v1.0.0 C2-C5/C9-C10](../../docs/v1-interface-contracts.md),
[B5 task distribution](../../docs/10-detailed-task-distribution.md) and the
[independent guide](../../docs/v1-independent-development.md).

**Preparation only. No deployment capability is implemented by these new tools.**
The example image and addresses are documentation placeholders, not working
endpoints or evidence that a compatible image exists. B5 remains Phase V1/V1-09;
B7 repeats the validation with CARLA in V2. Blocked Linux evidence stays pending.
Ankit owns A5 fleet aggregation. No fleet, publisher, simulator or V2 code changes
are included, and there are no imports from unmerged PR #30 or #31.

## Files and legacy compatibility

- `pilot-config.example.json`: nonsecret example configuration for vehicle-002.
- `autonomous-health-app-v1.json`: dedicated example descriptor, exactly matching
  the renderer's output. Its unique name is `autonomoushealthapp-vehicle-002`.
- `render_pilot_config.py`: pure configuration validation/descriptor rendering.
- `prepare_v1_pilot.py`: validation, rendering and dry-run lifecycle preparation;
  optional local CLI help checks only. It has no deploy/build/push/remove mode.
- `../app/tests/test_kanto_pilot.py`: static and mock tests.

The legacy vehicle-001 descriptor, `deploy.sh`, app manifest, publisher and
Dockerfile are unchanged. **Do not use legacy `deploy.sh` as the V1 preparation
command:** it builds/pushes an image and removes/recreates its named container;
it also duplicates CLI settings instead of consuming the descriptor.

## Safe Windows preparation commands

From the repository root, using the existing Python 3.12 environment:

```powershell
.\.venv-b1\Scripts\python.exe -X utf8 -B velocitas-app/kanto/prepare_v1_pilot.py
.\.venv-b1\Scripts\python.exe -X utf8 -B velocitas-app/kanto/prepare_v1_pilot.py --mode validate
.\.venv-b1\Scripts\python.exe -X utf8 -B velocitas-app/kanto/prepare_v1_pilot.py --mode render
.\.venv-b1\Scripts\python.exe -X utf8 -B velocitas-app/kanto/render_pilot_config.py
```

These commands only read local config and print JSON. The default is dry-run:
`execution_permitted=false`, a resolved descriptor and non-executable lifecycle
intentions for the same container name. No subprocess runs unless `--check-cli`
is explicitly supplied. Config validation occurs before any help invocation.
Output goes to stdout, not automatically to a Kanto deployment directory.

For your own configuration, use `--config <path>`. A filename such as
`pilot-config.local.json` matches the repository's existing local-config ignore
rule. Do not put secrets in that file or a generated descriptor. Unknown fields,
including arbitrary `env`, passwords and tokens, are rejected. Tools do not read
environment credentials, and diagnostics never echo config values or raw CLI
errors. Argument parse errors are also redacted.

The example uses reserved `192.0.2.10` and `registry.example.invalid`; replace them
in your local configuration before a future real run. No DNS lookup, network
probe, registry access or container inspection is performed by validation.

## Validated configuration

| Input | Policy |
|---|---|
| vehicle_id | Exactly `vehicle-002` |
| container_name | `autonomoushealthapp-vehicle-002`, optionally with a lowercase suffix |
| image | Explicit OCI tag or sha256 digest; no URL credentials or `latest` |
| remote_lan | Boolean; true for the cross-device V1 pilot |
| kuksa_host / mqtt_host | Separate configurable IP/DNS hosts; no URI, userinfo, port or path |
| kuksa_port / mqtt_port | Integers 1-65535; booleans and strings rejected |
| poll_interval_seconds | Finite positive numeric value |
| restart_policy.type | `unless-stopped` (default example) or `always` |
| retry settings | Explicit integer zero for both counters, matching these policies |

The renderer sets matching SDK and direct-client KUKSA endpoints, a configured
SDK MQTT address, host networking, no device mappings and `privileged=false`.
IPv6 address authorities are bracketed. There are no duplicate environment keys.
Remote-LAN mode rejects literal/mapped loopback, common localhost aliases,
ambiguous numeric address forms and link-local addresses. Unspecified/multicast
IP endpoints and IPv6 zone IDs are rejected. Explicit `remote_lan=false` permits
a deliberate same-device localhost smoke-test profile, not proof of remote V1-09.
After strict IP parsing fails, an all-numeric dotted component sequence (decimal,
octal-looking or hexadecimal, including mixed forms) is rejected instead of
being treated as DNS. Examples include `0x7f.0.0.1`, `0x7f.1`, `0x0.0.0.0`,
`127.1` and `2130706433`. This ambiguity rejection applies in both modes and to
both KUKSA/MQTT hosts. Canonical LAN addresses and legitimate names such as
`0x7f.example.org` remain supported. IPv4-mapped IPv6 is checked against its
underlying IPv4 address: remote loopback/link-local and all unspecified/multicast
addresses are rejected; canonical local-mode loopback remains allowed. Invalid
hosts fail before descriptor output or any optional CLI help discovery.

DNS names can still resolve differently on the target: verify their actual LAN
resolution there. No claim of reachability is made by static rendering. Prefer a
verified image digest for live evidence; a non-latest tag alone is not immutable.

## Linux/Kanto preflight: still pending

On the intended Linux device, with Python 3.12 and the genuine Kanto CLI installed,
the optional preparation-only check is:

```sh
python3 -B velocitas-app/kanto/prepare_v1_pilot.py --config /path/to/pilot-config.local.json --check-cli
```

It invokes only `kanto-cm --help` and the `create/get/start/stop --help` queries,
with a five-second timeout each, and suppresses raw output/errors. Missing CLI,
unexpected root help or nonzero help exits fail closed. HELP_CHECKS_PASSED means
those help queries succeeded, **not** that create flags, descriptor import,
effective restart policy, daemon access or the image have been validated.

No mutating command is constructed or dispatched by this tool, even after help
checks succeed. Review the installed CLI version and its descriptor/argument
support before preparing an actual deployment procedure. That future procedure
must apply all resolved descriptor settings, inspect existing names first and
refuse unexpected collisions. Do not remove an existing container, restart the
whole manager or execute build/push steps as an implicit preparation action.

Record Linux architecture, Kanto/container-runtime versions and actual image
digest. Confirm the image supports that architecture: current repository image
publication targets linux/amd64, so ARM support must not be assumed. A Docker
build/cache is not proof that Kanto's runtime can resolve the image; verify registry
access from the Kanto runtime separately.

## Main-host LAN and publisher dependencies

The remote Linux device must reach the main host's **vehicle-002 KUKSA instance**
and the configured shared Mosquitto broker. Use the main host's LAN address,
not Linux-device loopback or Docker-only service names. The contract's proposed
host ports are 55556/55557 for the two KUKSA brokers; current baseline Compose only
provides one broker at host 55556. A renderer accepting 55557 does not create it.
Verify the actual mapping and firewall/listener reachability on your own setup.

Emmanuel must supply/confirm a compatible V1 app image and deployment inputs:

- Topic `sdv/vehicle-002/health`, schema 1.0.0 and matching vehicle identity.
- Unique new observation IDs, original observation source timestamps, and optional
  command context; publishing time must not substitute for source time.
- C4 LiDAR/health/fault classification, QoS 1, retain=false and reconnect behavior.
- Updated publication permissions/manifest and noncolliding MQTT client identity.
- Image architecture, exact revision/digest and required signal paths.

The existing app publishes `sdv/autonomy/status` with legacy `healthStatus` and
publication-time `timestamp`, so changing environment variables alone cannot
make it V1 compliant. B5 does not translate or duplicate Emmanuel's publisher.
Authenticated/TLS service or registry credentials require a separately reviewed,
image-supported secret-injection procedure; no plaintext secret fields are added
to this descriptor. This renderer currently expresses `grpc://` and `mqtt://`
endpoints; secure transport support must not be inferred.

Independent static work and observer rehearsal need no teammate branch. An own
isolated KUKSA/Mosquitto and deterministic signal feeder can support later Linux
component testing, but fixtures alone are not Kanto evidence.

## Restart -> MQTT -> Ditto evidence procedure (not executed)

1. Select an agreed isolated pilot environment. Record exact configuration,
   source/image revisions, versions, architecture and UTC clock synchronization.
   Confirm no other publisher is emitting vehicle-002 observations on that broker.
2. Under a reviewed version-specific deployment procedure, inspect/create only
   the unique pilot container and confirm its effective environment/restart policy
   matches the rendered descriptor. Keep vehicle-001 untouched.
3. Start MQTT observation **before** lifecycle changes. Save a pre-restart event:
   topic, eventId, sourceTimestamp, receipt UTC, schema, vehicle, health/faults and
   available QoS/retain metadata. Save the corresponding individual twin snapshot.
4. Capture Kanto stop/start (or verified managed restart) commands, exit status,
   status/logs and UTC boundaries. After stopping the old process, record a UTC
   boundary immediately before starting the replacement process. A stop/start
   test proves an explicit lifecycle restart; it does not prove crash auto-restart.
5. Require an app-generated post-start event with the correct topic/vehicle/schema,
   a different eventId and strictly newer sourceTimestamp than the pre-restart
   observation. Source time must be after the recorded start-request boundary,
   receipt must follow start, and source age must satisfy the agreed freshness
   window (C5 default <=5 seconds, future tolerance <=1 second). Report clock skew
   or stale observations as failures, not successful recovery.
6. Read `GET {dittoBaseUrl}/api/2/things/sdv:vehicle-002` and match
   `attributes.vehicleId`, `features.v1.properties.vehicleId`, `lastEventId`,
   `sourceTimestamp`, health, faults, LiDAR and known command context to that event.
   Poll within an explicit recorded timeout; a Kanto RUNNING status or a publisher
   QoS acknowledgment alone does not prove twin persistence.
7. Verify vehicle-001 stays HEALTHY without injected faults. For controlled
   target-only writes compare its complete before/after snapshot; with a real
   independently updating publisher, allow its own telemetry to advance and check
   its identity/source ordering and unaffected health instead.
8. Preserve the correlated timeline and raw event/twin snapshots, with secrets
   redacted. Label failed/missing stages pending. A retained/replayed event, a new
   event ID over old source data or an unrelated Ditto update is insufficient.

The fixture capture/check tools in `scripts/v1_dev/mqtt.py` can rehearse event
validation using deterministic source offsets. Label such rehearsal as mock input;
remove replay publishers before real Kanto evidence. Production B5 code imports
neither those tools nor PR #30/#31. Their separately approved/merged ingress/twin
components are needed later for end-to-end evidence; they are not copied here.

## Verification levels and Draft PR scope

| Windows/static/mock | Linux/live, pending |
|---|---|
| Config validation and descriptor equivalence | Genuine Kanto daemon/version/descriptor behavior |
| Wrong identity/ports/image/interval/restart rejection | Image pull and target-architecture compatibility |
| Safe modes, redacted failures and mocked help checks | Effective environment/restart policy and LAN access |
| Legacy descriptor/health tests | Fresh app-generated post-restart MQTT event |
| Fixture/capture-oracle rehearsal | Matching live Ditto write and vehicle-001 isolation |

Run local tests without deployment:

```powershell
.\.venv-b1\Scripts\python.exe -X utf8 -B -m pytest -q -p no:cacheprovider velocitas-app/app/tests
```

Before Draft PR review, rerun Python 3.12 static/mock tests and available baseline
regressions, syntax/JSON checks and `git diff --check`. Keep `.venv-b1/` untracked
and unstaged. No dependencies are installed by these tools. Existing generated
Protobuf/KUKSA dependency blockers must be reported separately from passing tests.

Verified locally on Python 3.12.10: 144 app tests passed (136 new pilot tests,
three legacy Kanto descriptor tests and five existing health tests). The available
regression run passed 284 tests and 218 subtests. Existing temporary-file tests
required execution outside the filesystem sandbox. Full collection was attempted
but blocked by `common_pb2` imports in `tests/test_uprotocol_transport.py`,
`uprotocol/tests/test_extended_transport.py` and `uprotocol/tests/test_transport.py`,
and by `kuksa_client` in `vehicle-simulator/tests/test_kuksa_publication.py`.
Those four modules were explicitly excluded from the available run; the KUKSA
publication module also requires live KUKSA to execute. No new dependencies,
Docker/Kanto operations or shared-service access were used for this verification.

Preparation can be Draft-PR-ready while V1-09 remains pending. Static tests, an
example descriptor or successful CLI help must never be presented as completed
Kanto deployment or live V1 acceptance.


## PR32-F01 portability correction (November 12, 2026)

Reviewed the correction against authoritative `origin/main`
`8e9566ed3fe24f75889325aa867e4395019f350b`, contract 1.0.0 (still proposed for
affected-owner review), B5 allocation and the PR #32 review findings. C2 requires
correct endpoints, not a fixed IPv4-mapped IPv6 spelling. Production rendering,
configuration validation, descriptors, deployment preparation and CI are unchanged.

Tests now compare parsed numeric IPv6 addresses and independently require the
correct URI scheme, brackets and ports, including direct-client/SDK KUKSA agreement.
Both `::ffff:c0a8:114` and `::ffff:192.168.1.20` are exercised as inputs and simulated
renderer outputs. Hexadecimal mapped unspecified/multicast/link-local cases were
added alongside their dotted equivalents; mapped loopback rejection remains.
DNS/LAN, identity, image/restart, nonsecret configuration, descriptor consistency,
legacy compatibility and safe dry-run checks remain intact.

A controlled dotted-output probe reproduced both old assertion failures before
correction and passed afterward. Fresh local verification on Python **3.12.10**:
**156 app tests passed**; **296 available regression tests and 218 subtests passed**.
Full pytest collection was attempted and stopped at the same four dependency-blocked
modules listed above; they were explicitly ignored for the available run. No new
interpreter or dependencies were installed. Both string renderings are simulated
in focused tests; this is not an executed Python 3.12.16 run. Current supported-patch
GitHub Actions must be rerun after the reviewed changes are pushed.

Python AST syntax, tracked JSON parsing, targeted secret and `git diff --check`
checks passed. Applied the existing repository systematic-debugging,
test-driven-development and verification-before-completion instructions; missing
supporting skills are not claimed. Changes remain unstaged/uncommitted for review.

All evidence here is static/mock only. A compatible Emmanuel V1 image, genuine
Linux/Kanto runtime, real KUKSA/MQTT connectivity, launch/restart, a fresh post-start
event, matching `sdv:vehicle-002` twin state and vehicle-001 isolation evidence
remain **pending live V1-09 acceptance**. No deployment, image publication, CLI help
execution, live service access, merge or PR update was performed by this correction.
