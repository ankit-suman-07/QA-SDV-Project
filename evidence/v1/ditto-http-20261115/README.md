# V1-F04 — Ditto HTTP compatibility

Ankit; independent branch `ankit/fix/v1-ditto-http-compatibility` from main
`6a965bb`. No Part A or shutdown code imported. Phase V1 V1-04/08, supporting05.

## Root cause and smallest correction

Spring Web7.0.8 `JdkClientHttpRequest.buildRequest` adds SUPPORTED_ENCODINGS as two
header values (`gzip`, `deflate`) when automatic compression is enabled and no
Accept-Encoding field exists. JDK21 emits separate fields. Original nginx forwards
them; real Ditto3.8.4 rejects duplicate field names with HTTP400. Direct JDK clients
do not add these values, explaining the historical differing probes.

Both actual configured clients now default to one `Accept-Encoding: gzip, deflate`
field. Compression/decompression stays enabled; no unrelated headers are stripped.
Authentication, CA/default TLS, redirects policy, response bounds and timeouts are
unchanged. The acceptance launcher now uses original upstream nginx unchanged;
proxy normalization is no longer required. Initial-feature bootstrapping remains
the separate F03 boundary, not implicitly imported into this independent PR.

## Actual checks

- [Red](red.txt): actual configured reader over loopback HTTP sends two values,
  expected one-field assertion fails. The test server models Ditto's duplicate-field
  rejection. Tests use real Spring/JDK transport, not MockRestServiceServer.
- [Java21 clean verify](java-regression.txt): **209 tests, zero failures/errors/skips**.
  New regression verifies actual reader and fleet writer, plus gzip response decode.
- [Actual Java](actual-java.txt), [live record](live.json): separate fresh real Ditto
  project `qa-v1-release-engineering-ditto`, loopback18090, new network/database,
  pinned Ditto3.8.4 source revision, original nginx config without normalization.
  Baseline Spring transport reproduces HTTP400. Corrected production configuration
  reads both individual snapshots and materializes the fleet Thing successfully.
- Individual snapshots in this HTTP-only test are copied from actual existing real
  twins into create-only resources on the separate database; this is explicit
  existing-state preparation, not first-event initialization evidence or fabricated
  fresh data. Fleet projection may truthfully mark aged source unavailable.
- [Offline acceptance controls](acceptance-controls.txt) pass. These do not prove
  a complete fleet/fault workflow. That belongs to the combined candidate.

[Java probe](DittoHeaderLiveProbe.java) / [observer](live_http.py) reproduce the
actual boundary using runtime/ditto-engineering.json and official nginx. Credentials
are read in memory from documented official sample auth, never command arguments.
Java21 restored persistently from official Corretto download, version21.0.13+11,
archive SHA256 f3330bf440b8f4514b7b279b6145d4b4493dea9dda5f3a702b49c53c41bec1e4.

The new isolated stack remains available for follow-up, with its database preserved.
Original prerequisite stack, twins, policies, volumes and unused docker_default
network were not changed. No existing backend/fleet materializer was started.
Pinned dependency API/bytecode and actual transport outputs informed systematic
debugging; repository TDD and verification instructions applied. Supporting absent
skills are not claimed. Human approval, CI at exact head and combined candidate
remain separate. No merge/tag/release/full V1 acceptance.
