# PR #32 — V1 Kanto vehicle-002 pilot

## Review metadata

| Field | Reviewed value |
| --- | --- |
| PR | [#32 — config: prepare V1 Kanto pilot for vehicle-002](https://github.com/ankit-suman-07/QA-SDV-Project/pull/32) |
| Author | Bayan Sayyadifar (`sayadifarbayan-lgtm`) |
| Head branch | `bayan/config/v1-kanto-pilot` |
| Base branch | `main` |
| Head SHA | `255a6507817db08d1212dd290c09f7cafd6907c1` |
| Base SHA and merge base | `8b3143aaa1631ee81b18042e6fb1aa34d50484dc` |
| Review date | November 11, 2026 |
| Task | B5 Kanto vehicle-002 Linux pilot preparation |
| Acceptance | V1-09; supports V1-01/V1-02/V1-07 |
| Recommendation | **REQUEST CHANGES** for CI portability; live pilot still NEEDS VERIFICATION |

Fresh fetch confirms one commit directly parented by `main` at the base SHA. There are no #30/#31 commits or implementation imports. Line numbers below refer to this head.

## Executive summary

The PR adds a dedicated vehicle-002 descriptor, strict nonsecret configuration renderer, non-deploying preparation modes, optional bounded CLI-help checks and detailed live-evidence instructions. It preserves the legacy vehicle-001 descriptor, deployment script and app. Preparation is explicitly separated from real Kanto deployment and V1-09 completion.

One confirmed P2 test portability defect keeps current Python CI red. The new tests hard-code an IPv4-mapped IPv6 spelling that changed between Python 3.12.10 and 3.12.16. Both spellings represent the same packed address. This review found no evidence that this difference itself routes traffic incorrectly; assertions must check endpoint semantics or the project must deliberately define stable textual normalization. Downgrading Python solely to make the assertions pass is not the recommended correction.

## Source-of-truth and scope

Reviewed [SOURCE-OF-TRUTH.md](../SOURCE-OF-TRUTH.md) in `docs/`, [V1 interface contract](../v1-interface-contracts.md), [task allocation](../10-detailed-task-distribution.md), [scope](../08-project-scope-and-acceptance.md), [architecture](../09-architecture-diagrams.md) and [independent development](../v1-independent-development.md). Contract 1.0.0 remains **proposed for affected-owner review**. Ankit owns all fleet aggregation; B5 is Bayan's responsibility. Two synthetic vehicles and a separate one-device Kanto pilot are V1 targets for November 16, 2026. CARLA and V2 runtime work are excluded.

## Findings summary

| ID | Severity | Status | Issue | File and lines at reviewed head |
| --- | --- | --- | --- | --- |
| PR32-F01 | P2 — Medium | Confirmed | Hard-coded IPv4-mapped IPv6 formatting fails supported Python 3.12 CI | `velocitas-app/app/tests/test_kanto_pilot.py:107`, `117–120`; renderer `velocitas-app/kanto/render_pilot_config.py:63` |

Counts: P0 0, P1 0, P2 1, P3 0. Missing live pilot evidence is tracked below as incomplete acceptance, not inflated into an additional code defect.

## PR32-F01 — IPv6 spelling assumption breaks CI

- **Severity/status:** P2 — Medium; Confirmed. Historical CI failure remains present at the latest fetched head.
- **Location:** [`test_kanto_pilot.py:107`](https://github.com/ankit-suman-07/QA-SDV-Project/blob/255a6507817db08d1212dd290c09f7cafd6907c1/velocitas-app/app/tests/test_kanto_pilot.py#L107), assertions at lines 117–120. `_host` returns `address.compressed` at [`render_pilot_config.py:63`](https://github.com/ankit-suman-07/QA-SDV-Project/blob/255a6507817db08d1212dd290c09f7cafd6907c1/velocitas-app/kanto/render_pilot_config.py#L63).
- **Affected behavior:** Supported-version test reproducibility and CI merge readiness; textual descriptor output varies with the Python standard library.
- **Root cause:** The test assumes `ipaddress.ip_address('::ffff:192.168.1.20').compressed` is always `::ffff:c0a8:114`. On the author's Python 3.12.10 it is; on Python 3.12.16 it is `::ffff:192.168.1.20`. Inspecting the installed 3.12.16 `IPv6Address.__str__` shows its explicit IPv4-mapped formatting branch. CI uses `python-version: "3.12"`, so a patch-specific spelling assumption is incompatible with the configured version range.
- **Reproduction:** Run the unchanged app suite under both versions with pinned dependencies. Python 3.12.10: 144 passed. Python 3.12.16: 142 passed, 2 failed, at the KUKSA and MQTT mapped-address cases. Direct `_host(..., True)` calls return the two spellings. `socket.inet_pton(AF_INET6, old_text) == socket.inet_pton(AF_INET6, new_text)` returns `True`.
- **Expected:** Tests pass across supported Python 3.12 patches for semantically equivalent valid endpoints, while still checking IPv6 brackets, ports, identity, and rejection of mapped loopback/unspecified/multicast/link-local addresses.
- **Actual:** The KUKSA string assertion and MQTT URI assertion fail on 3.12.16 and in current GitHub Python CI. Full non-integration pytest reports 2 failed, 292 passed, 9 deselected and 218 passing subtests.
- **Impact:** Required Python CI is red; otherwise valid configuration is treated as a test failure. No endpoint reachability or networking failure was demonstrated by this formatting mismatch.
- **Minimum required correction:** Since the current contract does not mandate one textual IPv6 spelling, compare parsed address equivalence while asserting URI brackets/ports and security properties separately. Alternatively, if stable descriptor text is genuinely required, specify and implement an explicit version-independent formatter and test it. Do not weaken mapped-address restrictions or use a Python downgrade as the sole fix.
- **Regression tests:** Run relevant cases on 3.12.10 and current 3.12; both equivalent input spellings; KUKSA and MQTT address/port correspondence; correct brackets; forbidden mapped addresses still rejected before descriptor output or CLI invocation; checked-in descriptor remains equivalent to rendering its example.
- **Contract/acceptance:** C2 configurable correct endpoints, C9/C10 reproducibility; B5; V1-05 and support for V1-07/V1-09.
- **Definition of done:** Focused and full supported-version suites pass, GitHub Python CI is green, and endpoint/security assertions remain meaningful.

Minimal standard-library reproduction from this PR's root, run with each interpreter:

```python
import ipaddress, socket, sys
sys.path.insert(0, 'velocitas-app/kanto')
from render_pilot_config import _host
print(sys.version.split()[0], _host('::ffff:192.168.1.20', True))
assert socket.inet_pton(socket.AF_INET6, '::ffff:c0a8:114') == \
       socket.inet_pton(socket.AF_INET6, '::ffff:192.168.1.20')
```

This establishes a Python patch-version formatting change, not an OS-only hypothesis or evidence of incorrect numeric normalization. The author's historical 3.12.10 pass is consistent with the reproduced result; it must not be substituted for current CI evidence.

## Verification

Primary environment: Linux x86_64, CPython **3.12.16**, pytest **9.1.1**, requests **2.32.5**, grpcio **1.82.1**, grpcio-tools **1.68.0**, protobuf **5.29.6**, kuksa_client **0.5.1**. The shared primary temporary environment additionally contained Paho **2.1.0**, which this PR does not require. Secondary environment: CPython **3.12.10** with this PR's pinned requirements. Both environments and all output files were under `/tmp/bayan-review-ndC62A`. `PYTHONDONTWRITEBYTECODE=1` was set.

With cwd `/tmp/bayan-review-ndC62A/pr32`, define `PY=/tmp/bayan-review-ndC62A/venv/bin/python` and `PY_OLD=/tmp/bayan-review-ndC62A/venv31210/bin/python`:

```bash
mkdir -p uprotocol/generated
$PY -m grpc_tools.protoc -I uprotocol/proto --python_out=uprotocol/generated \
  uprotocol/proto/common.proto uprotocol/proto/health_status.proto \
  uprotocol/proto/vehicle_status.proto uprotocol/proto/vehicle_fault.proto \
  uprotocol/proto/vehicle_diagnostic.proto
$PY -B -m pytest -q -ra -p no:cacheprovider velocitas-app/app/tests
$PY -B -m pytest -q -ra -p no:cacheprovider
$PY_OLD -B -m pytest -q -ra -p no:cacheprovider velocitas-app/app/tests
$PY -B velocitas-app/kanto/prepare_v1_pilot.py --mode validate
$PY -B velocitas-app/kanto/prepare_v1_pilot.py --mode render
docker compose -f vehicle-simulator/docker-compose.yml config --quiet
docker compose -f scripts/v1_dev/compose.yaml config --quiet
sh -n velocitas-app/kanto/deploy.sh
git diff --check 8b3143a...HEAD
```

| Check | Exit | Passed | Failed | Skipped / deselected | Notes |
| --- | --- | --- | --- | --- | --- |
| Protobuf generation | 0 | N/A | 0 | N/A | Temporary files only |
| App focused tests, 3.12.16 | 1 | 142 | 2 | 0 / 0 | Both mapped-address assertions |
| Full non-integration pytest, 3.12.16 | 1 | 292 + 218 subtests | 2 | 0 / 9 | Same two failures; all modules collect |
| App focused tests, 3.12.10 | 0 | 144 | 0 | 0 / 0 | Reproduces author's historical result |
| Preparation validate/render | 0 each | N/A | 0 | N/A | Reports validation and renders example; never deploys |
| Compose configuration checks | 0 each | N/A | 0 | N/A | Parsing only; neither starts a service |
| Legacy deployment shell syntax | 0 | N/A | 0 | N/A | Syntax only; script not executed |
| Changed Python AST / tracked JSON parsing | 0 | 3 / 30 files | 0 | N/A | Static validation |
| Diff whitespace | 0 | N/A | 0 | N/A | Passed |

The unchanged base passes 158 tests and 218 subtests, with 9 integration tests deselected, on 3.12.16. This distinguishes the new portability failures from baseline defects. Fresh GitHub metadata reports five checks successful and Python unit tests failed: [CI](https://github.com/ankit-suman-07/QA-SDV-Project/actions/runs/43082941968), [synthetic baseline integration](https://github.com/ankit-suman-07/QA-SDV-Project/actions/runs/43082941897).

No `kanto-cm` or Mosquitto executable was available on the review host. No genuine Kanto daemon, compatible V1 image, real endpoints or deployment was exercised. Docker configuration parsing is not image-build or runtime evidence. No build/push/container lifecycle command was run; real integration is unverified rather than reported as passed.

## Contract compliance and configuration review

| Requirement | Static/component result | Remaining live requirement |
| --- | --- | --- |
| Vehicle identity/isolation | Exactly vehicle-002; unique constrained container name; legacy vehicle-001 descriptor unchanged | Verify effective running image/env and vehicle-001 health during restart |
| KUKSA and MQTT endpoints | Independently configurable hosts/ports; SDK/direct KUKSA endpoints agree; IPv6 authorities bracketed | Resolve LAN DNS/IP and verify actual listeners, firewall and vehicle-002 broker mapping |
| Host/container network distinction | Descriptor uses host networking; docs explain remote LAN versus local loopback | Confirm intended Linux host namespace and installed runtime behavior |
| LAN input validation | Tests reject ambiguous numeric IPv4, literal/mapped loopback and other forbidden endpoints; no arbitrary env/secret fields | DNS can still resolve differently on target; static validation does not prove reachability |
| App image | Explicit tag/digest required; `latest` rejected; example clearly uses placeholders | Obtain Emmanuel's V1-compatible image, architecture, registry access and exact digest |
| Restart configuration | Constrained `always`/`unless-stopped` policy; descriptor and generated example agree | Confirm manager honors settings; stop/start evidence is separate from crash auto-restart |
| Safe preparation | validate/render/dry-run do not deploy; optional subprocess calls are argument lists and bounded help queries | Review version-specific actual deployment/import options; successful help alone is insufficient |
| Security | No new hard-coded real credentials; secret fields rejected; errors redacted; no shell interpolation in new tools | Auth/TLS/registry secret injection needs separate supported configuration; plain URI rendering does not prove secure transport |
| Source/event preservation | Documentation requires app-generated new event ID and source time after restart | Capture actual publication and correlate to live twin; renderer cannot create this behavior |
| Ownership | No publisher rewrite, fleet aggregate, simulator or V2 changes | Coordinate image/config boundary with Emmanuel and live twin evidence with #30 |

The repository's unchanged app still publishes `sdv/autonomy/status` and its manifest grants that legacy topic. That is an inherited E1 dependency, not a new #32 bug: this PR explicitly says it does not make the old publisher V1 compliant through environment changes. The unchanged legacy `deploy.sh` builds/pushes and replaces vehicle-001; the new documentation explicitly says not to use it for V1 preparation. No recommendation is made to run it unchanged.

## Live V1-09 acceptance still pending

- [ ] Review/approve the affected C2–C5 interface and actual deployment inputs.
- [ ] Supply the compatible V1 publisher image and verify target architecture/digest/registry access.
- [ ] Verify real vehicle-002 KUKSA signals and shared Mosquitto connectivity from Bayan's Linux device.
- [ ] Confirm genuine Kanto version, descriptor/create options, effective environment and restart policy.
- [ ] Capture pre-restart MQTT event/twin snapshot and exact UTC lifecycle boundaries.
- [ ] Capture an app-generated post-start event with matching identity/topic/schema, new event ID and strictly newer original source time after the start boundary, within the agreed freshness window.
- [ ] Match that event to `sdv:vehicle-002` V1 properties, preserving IDs/time/context.
- [ ] Verify vehicle-001 remains unaffected; allow legitimate independent telemetry updates when evaluating isolation.
- [ ] Record logs, versions, exact revisions, failure cases and explicit timeouts separately from mock/static evidence.

## Recommendation and dependencies

**REQUEST CHANGES** for F01. Correct the supported-version assertion/normalization policy, retain mapped-address rejection coverage and rerun CI. Static preparation may be merge-ready before live B5 completion, provided the outstanding acceptance evidence remains explicit and affected-owner configuration review is complete.

#32 is technically independent of #30/#31 and shares no changed files with them. Merge-tree checks against each returned exit 0. Its live MQTT-to-twin evidence depends on the ingress/twin capability supplied by corrected #30 (or an equivalent approved implementation), plus Emmanuel's publisher/edge setup. #31 is useful optional verification. Neither of #30's poison-input bugs is implemented by these preparation tools, but a blocked ingress would prevent the required post-restart twin correlation.

Review used [systematic debugging](../../skills/systematic-debugging.md) and [verification before completion](../../skills/verification-before-completion.md) at `8b3143a`. No production or existing test changes were made.
