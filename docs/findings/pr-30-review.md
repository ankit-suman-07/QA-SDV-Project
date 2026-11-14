# PR #30 — V1 MQTT ingress and individual Ditto twins

## Review metadata

| Field | Reviewed value |
| --- | --- |
| PR | [#30 — feat: implement V1 MQTT ingress and isolated Ditto twins](https://github.com/ankit-suman-07/QA-SDV-Project/pull/30) |
| Author | Bayan Sayyadifar (`sayadifarbayan-lgtm`) |
| Head branch | `bayan/feature/v1-mqtt-twins` |
| Base branch | `main` |
| Head SHA | `8b359e27ff707218d0130d7e8a6f12f957bb1125` |
| Base SHA and merge base | `8b3143aaa1631ee81b18042e6fb1aa34d50484dc` |
| Review date | November 11, 2026 |
| Tasks | B1 MQTT ingress; B2 individual twin routing/provisioning |
| Acceptance | V1-02; supports V1-03, V1-04, V1-05 and V1-08 |
| Recommendation | **REQUEST CHANGES** |

Freshly fetched head has one commit, whose sole parent is the base SHA. It contains neither #31 nor #32. All line numbers refer to this head, not local `main`. The primary worktree remained on `main`; inspection/testing used detached worktrees in a temporary repository.

## Executive summary

The PR provides a focused production boundary: strict event decoding, exact topic/identity routing, serialized per-vehicle writes, restart watermark loading, authenticated atomic V1 property replacement, create-only provisioning and explicit MQTT acknowledgments. It preserves legacy features and leaves fleet aggregation to Ankit.

The focused and full non-integration suites pass, including the real Paho construction test and mock HTTP transport. Two deterministic input failures nevertheless remain: deep extensions fail copying, and lone Unicode surrogates fail serialization. Both are treated as retryable persistence failures. Later valid events for the affected vehicle cannot progress; a full queue then stops both workers. These are missing negative tests, not evidence that ordinary compliant traffic always fails.

Historical issues 30-A and 30-B were rechecked at the current fetched head and remain confirmed. Earlier conversation reports are not assumed to exist on disk: no earlier PR review files were present at the start of this task. Current reproduction results below supersede reliance on historical test counts or dependency blockers.

## Authoritative context

Read [docs/SOURCE-OF-TRUTH.md](../SOURCE-OF-TRUTH.md), [V1 contracts](../v1-interface-contracts.md), [task allocation](../10-detailed-task-distribution.md), [scope](../08-project-scope-and-acceptance.md), [architecture](../09-architecture-diagrams.md) and [independent development](../v1-independent-development.md). There is no root `SOURCE-OF-TRUTH.md`; its actual location is `docs/`.

Contract v1.0.0 is **proposed for affected-owner review**, not established as fully approved. The latest task allocation and C1 supersede older scope/diagram wording assigning fleet aggregation to Bayan: Ankit owns the sole Spring Boot aggregate and fleet materialization. V1 targets two synthetic vehicles by November 16, 2026. V2 work is outside this review.

## Findings summary

| ID | Severity | Status | Issue | File and lines at reviewed head |
| --- | --- | --- | --- | --- |
| PR30-F01 | P2 — Medium | Confirmed | Accepted deep extension is retried forever after copying fails | `ditto/mqtt_ingress.py:196`; `ditto/mqtt_subscriber.py:168–174` |
| PR30-F02 | P2 — Medium | Confirmed | Lone surrogate is accepted, then permanently fails UTF-8 persistence | `ditto/mqtt_ingress.py:83–90`; `ditto/v1_writer.py:119–122`; `ditto/mqtt_subscriber.py:168–174` |

Counts: P0 0, P1 0, P2 2, P3 0. These findings are introduced by new PR code, which is absent from the base. Queue overflow is a documented mechanism; it is the consequence of these input failures, not an additional duplicate finding.

## PR30-F01 — Deep extension blocks subsequent delivery

- **Severity/status:** P2 — Medium; Confirmed. Historical issue 30-A remains open.
- **Location:** [`ditto/mqtt_ingress.py:196`](https://github.com/ankit-suman-07/QA-SDV-Project/blob/8b359e27ff707218d0130d7e8a6f12f957bb1125/ditto/mqtt_ingress.py#L196); retry loop at [`ditto/mqtt_subscriber.py:168`](https://github.com/ankit-suman-07/QA-SDV-Project/blob/8b359e27ff707218d0130d7e8a6f12f957bb1125/ditto/mqtt_subscriber.py#L168).
- **Affected behavior:** C3 extension acceptance, rejection/continuation, and per-vehicle delivery progress.
- **Root cause:** JSON decoding and recursive finite-number validation can accept nesting that Python's `copy.deepcopy` cannot process. The copy sits outside the persistence `try` block. Its `RecursionError` escapes as a general exception; the subscriber catches all such exceptions as `persistence_pending` and retries the same payload before later messages.
- **Reproduction:** Load `tests/fixtures/v1/vehicle-002-healthy.json`; set `extension = json.loads('[' * 600 + '0' + ']' * 600)`; serialize with default `json.dumps(...).encode()`. The 1,444-byte payload passes `decode_event('sdv/vehicle-002/health', payload)` and fails `Ingress.process` with `RecursionError`. A mock-backed subscriber with `queue_size=2` and `retry_seconds=0.01` retries it at least three times. Enqueue a later vehicle-002 fault and a vehicle-001 healthy event. Only the vehicle-001 message is acknowledged; vehicle-002 has no V1 write. Two more vehicle-002 deliveries fill the pending queue and trigger `QUEUE_FULL`.
- **Expected:** Either safely persist the compatible extension, or reject unsupported structure through a controlled input error before enqueueing. A deterministic input problem must not become an unrecoverable persistence retry. Invalid input must leave twin state/watermarks intact and allow later valid events to progress.
- **Actual:** Repeated `RecursionError`; no ACK for the poison or following vehicle-002 event. Vehicle-001 initially progresses, then queue overflow stops the subscriber globally.
- **Impact:** A small extension can block one vehicle indefinitely and eventually interrupt both. No twin corruption was observed; failure is delivery availability.
- **Minimum required correction:** Ensure validation guarantees that accepted data survives copying/persistence, or use safe copying and a controlled depth rejection. Classify deterministic input-processing failures separately from transient downstream outages. If adding an explicit nesting limit, agree and test that shared boundary rather than silently changing extension semantics. Catching every exception and acknowledging it would lose real persistence failures and is not an acceptable fix.
- **Regression tests:** Nested arrays and dictionaries around the supported boundary; invalid event followed by valid events for both vehicles; rejected event causes no PUT/watermark advancement; transient Ditto errors still withhold ACK; no queue overflow caused by deterministic rejection; repeat the restart/readback path with allowed nested extensions.
- **Contract/acceptance:** C3 validation and continuation, C6 persistence semantics; B1/B2; V1-02 and support for V1-03/V1-05.
- **Definition of done:** The reproduction no longer enters a permanent retry; both vehicles can subsequently persist/ACK valid events, without swallowing genuine downstream failure.

## PR30-F02 — Lone surrogate cannot be serialized to Ditto

- **Severity/status:** P2 — Medium; Confirmed. Historical issue 30-B remains open.
- **Location:** [`ditto/mqtt_ingress.py:83`](https://github.com/ankit-suman-07/QA-SDV-Project/blob/8b359e27ff707218d0130d7e8a6f12f957bb1125/ditto/mqtt_ingress.py#L83); [`ditto/v1_writer.py:119`](https://github.com/ankit-suman-07/QA-SDV-Project/blob/8b359e27ff707218d0130d7e8a6f12f957bb1125/ditto/v1_writer.py#L119); subscriber lines 168–174.
- **Affected behavior:** Validation-to-persistence compatibility and subscriber progress.
- **Root cause:** UTF-8 wire decoding does not ensure that JSON escape sequences decode to Unicode scalar values. Python's JSON decoder accepts a lone surrogate. Validation checks number finiteness but not string/key encodability. The writer uses `ensure_ascii=False` followed by UTF-8 encoding, which fails before any HTTP request. The resulting `DittoError('INVALID_DITTO_JSON')` is retried as a downstream outage.
- **Reproduction:** Add `extension = '\ud800'` to the healthy fixture, and use default `json.dumps` so the surrogate is escaped on the wire. The 251-byte payload passes validation but `Ingress.process` with a real `DittoWriter` and fake HTTP transport raises `INVALID_DITTO_JSON`. A surrogate dictionary key, `extension = {'\ud800': 'text'}`, produces the same failure in a 261-byte payload. The same subscriber experiment as F01 confirms repeated retries, blocked later vehicle-002 delivery, successful initial vehicle-001 ACK, and eventual `QUEUE_FULL`.
- **Expected:** Reject malformed/unusable text as a controlled input rejection before enqueueing, or adopt an explicitly agreed persistence representation that works end to end. Preserve valid Unicode and valid surrogate pairs decoded into non-BMP characters.
- **Actual:** The encoder raises `UnicodeEncodeError`, wrapped as `INVALID_DITTO_JSON`; retrying cannot repair the input. No HTTP PUT is dispatched for the malformed value.
- **Impact:** Same delivery blockage as F01. Valid UTF-8 wire bytes alone are not sufficient validation of decoded escaped text.
- **Minimum required correction:** Validate string values and object keys recursively for lone surrogates, including event/context IDs and extensions, and report a controlled code such as `MALFORMED_JSON`. Do so without introducing another recursion failure. Retain persistence-gated ACKs for actual downstream errors. Coordinate the decoded-snapshot policy with #31.
- **Regression tests:** Lone high/low surrogates in IDs, values and keys; valid non-ASCII text and non-BMP characters; valid surrogate-pair escapes; no PUT/watermark change on rejection; following valid events progress; near-64-KiB Unicode payloads continue to work.
- **Contract/acceptance:** C3 strict UTF-8 JSON/validation and continuation; C6 serializable atomic property updates; B1/B2; V1-02/V1-05.
- **Definition of done:** Both value/key reproductions produce safe rejection or agreed successful persistence, never a permanent retry, with valid Unicode coverage retained.

## Reproduction instructions

Run against the exact PR revision in an isolated checkout; dependencies and fixtures are needed. This minimal snippet reproduces the synchronous failures without contacting a service:

```python
import json
from unittest.mock import Mock
from ditto.mqtt_ingress import Ingress, decode_event
from ditto.v1_writer import DittoWriter, DittoConfig

for extension in [json.loads('[' * 600 + '0' + ']' * 600),
                  '\ud800', {'\ud800': 'text'}]:
    event = json.load(open('tests/fixtures/v1/vehicle-002-healthy.json'))
    event['extension'] = extension
    payload = json.dumps(event).encode()
    decode_event('sdv/vehicle-002/health', payload)  # accepts
    writer = DittoWriter(DittoConfig('http://mock', 'u', 'p'), request=Mock())
    writer.load_watermark = lambda _: None
    try:
        Ingress(writer).process('sdv/vehicle-002/health', payload)
    except Exception as error:
        print(type(error).__name__, str(error))
```

The review also ran a subscriber-level experiment using the existing test `FakeDitto`, real `Ingress`/`DittoWriter`, a fake MQTT client, a counted `process` wrapper and finite waits. Its output for each payload was `attempts>=3 True`, `ACKs [call(3, 1)]`, `vehicle002_written False`, `overflow QUEUE_FULL`. The temporary script is `/tmp/bayan-review-ndC62A/reproduce30.py`; its exit code 0 means the asserted bug behavior was reproduced, not that the implementation passed a regression test.

## Verification

Environment: Linux x86_64, CPython **3.12.16**, pytest **9.1.1**, Paho **2.1.0**, requests **2.32.5**, grpcio **1.82.1**, grpcio-tools **1.68.0**, protobuf **5.29.6**, kuksa_client **0.5.1**. Installed pinned requirements under `/tmp/bayan-review-ndC62A/venv`; no primary-worktree environment changes. `PYTHONDONTWRITEBYTECODE=1` was set. Use `PY=/tmp/bayan-review-ndC62A/venv/bin/python` below, with cwd `/tmp/bayan-review-ndC62A/pr30`.

```bash
mkdir -p uprotocol/generated
$PY -m grpc_tools.protoc -I uprotocol/proto --python_out=uprotocol/generated \
  uprotocol/proto/common.proto uprotocol/proto/health_status.proto \
  uprotocol/proto/vehicle_status.proto uprotocol/proto/vehicle_fault.proto \
  uprotocol/proto/vehicle_diagnostic.proto
$PY -B -m pytest -q -ra -p no:cacheprovider tests/test_mqtt_ingress.py tests/test_mqtt_subscriber.py tests/test_ditto_v1_writer.py tests/test_ditto_v1_cli.py
$PY -B -m pytest -q -ra -p no:cacheprovider
$PY -B -m unittest discover -s tests -p 'test_v1_*.py' -q
PYTHONPATH=. $PY /tmp/bayan-review-ndC62A/reproduce30.py
git diff --check 8b3143a...HEAD
```

| Check | Exit | Passed | Failed | Skipped / deselected | Notes |
| --- | --- | --- | --- | --- | --- |
| Protobuf generation | 0 | N/A | 0 | N/A | Temporary generated files only |
| Focused PR tests | 0 | 54 + 40 subtests | 0 | 0 / 0 | Paho construction and mock loopback HTTP included |
| Full non-integration pytest | 0 | 212 + 258 subtests | 0 | 0 / 9 | Integration excluded by repository pytest configuration |
| Documented V1 unittest suite | 0 | 31 | 0 | 0 / 0 | Included in full pytest as well |
| Bug reproductions | 0 | N/A | N/A | N/A | Three payload cases assert the failures described above |
| Changed Python AST / tracked JSON parsing | 0 | 8 / 28 files | 0 | N/A | Read-only static validation |
| Diff whitespace | 0 | N/A | 0 | N/A | No whitespace errors |

Unchanged base passed 158 tests and 218 subtests, with 9 integration tests deselected. Historical missing-Protobuf/KUKSA collection blockers were overcome locally by installing the pinned dependencies and generating modules; they are not current collection blockers in this review. Supported-version tests do not imply live service acceptance.

GitHub at metadata refresh reported all six checks successful, including Python unit tests and synthetic baseline integration: [CI run](https://github.com/ankit-suman-07/QA-SDV-Project/actions/runs/43067219743), [pipeline run](https://github.com/ankit-suman-07/QA-SDV-Project/actions/runs/43067219753). The existing pipeline workflow targets the single-vehicle baseline, not these PRs' complete two-vehicle V1 path.

No live Mosquitto/Eclipse Ditto session, policy/provisioning, reconnect, KUKSA or two-edge fault/recovery run was executed locally. No shared services were started or altered. Loopback HTTP used a mock; fake MQTT ACKs do not prove broker session replay.

## Contract compliance and review coverage

| Boundary | Assessment |
| --- | --- |
| C2/C3 two identities and exact topics | Implemented; positive/negative tests pass. Unknown/padded IDs and topic mismatch reject before writes. |
| C3 schema, fields, duplicate keys, non-finite values, 64-KiB budget | Broad implementation/test coverage; F01/F02 leave validation-to-processing gaps. |
| C3/C6 IDs, timestamps, optional context and ordering | Preserved; per-vehicle locks, equal/older rejection, submicrosecond comparison, restart watermark and uncertain-write reload tested. |
| C4 health/fault boundaries and recovery | C4 classifications checked; 5 m/10 m, sensor failure and fixture recovery tested. No cooling faults silently mixed into V1. |
| C5 freshness | Original timestamps preserved; source-age/future availability intentionally belongs to backend evaluation, not ingress relabeling. Live clock behavior remains unverified. |
| C6 writes and provisioning | Atomic feature PUT, status checks, authentication, bounded HTTP retries and create-only policies/Things tested with mocks. Real policy enforcement and provisioning remain pending. |
| Isolation and outage handling | Separate workers and persistence-gated ACKs tested. F01/F02 undermine progress under deterministic bad input. Global stop on bounded-queue overflow is explicitly documented. |
| Security | New credentials come from configuration; password repr redacted, redirects disabled, TLS verification retained, no new committed real secret found. New logs avoid response bodies/raw dependency exception text. No live authorization test performed. |
| Ownership/scope | No second fleet aggregator, backend/dashboard changes or V2 implementation. Existing legacy unit/context issues are not attributed to this PR. |

Additional deterministic-input review covered malformed JSON/UTF-8, duplicate keys, non-finite numbers, missing fields, wrong types/identities, timestamp format, health/fault mismatches and extension keys. No separate confirmed defect beyond F01/F02 was established. Do not interpret this as proof against all malformed-input or concurrency failures.

## Compatibility and final recommendation

#31 accepts ordinary #30 output; a temporary shared contract matrix passed 20 tests, including both identities, fault/recovery, missing fields, timestamps, thresholds and old-event rejection. #31 has its own deep-copy defect and accepts lone surrogates into decoded snapshots; see [its report](pr-31-review.md). These are separate implementations, so fixing one PR does not fix the other. #32 needs this ingress/twin capability for live Kanto-to-twin evidence but not for static preparation.

`git merge-tree --write-tree` in the temporary repository confirmed a `ditto/README.md` conflict between #30 and #31 (exit 1); no production source conflict. No resolution was applied. Preserve both sets of documentation links when the owner updates the later PR.

**REQUEST CHANGES:** correct F01/F02, add the specified progress/negative tests, rerun focused and full supported-version CI, and obtain affected-owner interface review. Merge readiness must be distinguished from later live V1-02/V1-03 acceptance. Suggested practical order is corrected #31, corrected #30, then #32; #32 preparation can merge independently after its own CI fix. No obsolete PR is part of this sequence.

Review used [systematic debugging](../../skills/systematic-debugging.md) and [verification before completion](../../skills/verification-before-completion.md) at base SHA `8b3143a`. No fixes or existing test edits were made.
