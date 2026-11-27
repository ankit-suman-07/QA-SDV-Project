# C5 strict envelope vectors

[envelope-vectors.json](envelope-vectors.json) supplements the existing
[fingerprint vectors](fingerprint-vectors.json). The outer
`fixtureLabel` marks synthetic test data. Each `inputJson` string is the
complete wire body for its accompanying `topic`. Pass only the wire body
to JSON decoding and fingerprinting. The outer fixture fields never enter
that process.

Each case is independent. For status cases, use `statusContext` as the
authorized session and accepted observation, with empty status history,
revision watermark zero, and source silence initially false.
`expected.validation` marks acceptance or rejection. Accepted cases
include exact canonical UTF-8 bytes in hexadecimal and SHA-256. Rejected
cases provide a fixture-level rejection category and no digest.

The `relations` entries express cross-case expectations. The overlay
relation is an integration expectation for later testing. After applying
the status reset to the original health observation, reconcile an exact
retry against the retained original health digest and preserve the status
projection. The two message types have separate fingerprint domains, as
also isolated by the same-payload domain probes in the existing vectors.

Python rfc8785 0.1.4 and Java java-json-canonicalization 1.1 independently
verified the accepted canonical bytes and SHA-256.
