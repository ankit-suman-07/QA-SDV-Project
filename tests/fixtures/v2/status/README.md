# C5 fingerprint vectors

`fingerprint-vectors.json` is UTF-8. Decode the outer JSON first.
Each entry's `inputJson` string then supplies the exact inner JSON,
including whitespace, number spelling and escapes. Do not parse it
with a decoder that discards duplicate names or token types.

- `observation` uses the vehicle-003 C5 health topic.
- `status` uses the vehicle-003 C5 status topic. Evaluate each entry
  independently with the authorized session and current accepted
  observation in `statusContext`, empty status history, revision
  watermark zero, and source silence initially false.
- `jcs` isolates JSON validation and canonicalization. Its input is
  already in canonicalization scope. Domain discriminator probes
  deliberately use the same empty payload to isolate domain identity.
  These cases are separate from application-schema acceptance.

Compare the canonical UTF-8 bytes and SHA-256 with `canonicalUtf8Hex`
and `sha256`. Rejected cases record a validation category and have
no digest. The two reference-rejection categories distinguish malformed
reference shape or types from a well-formed reference that differs from
the current accepted tuple.

Accepted outputs were compared byte-for-byte using Python rfc8785 0.1.4
and Java io.github.erdtman:java-json-canonicalization:1.1. Both runtimes
computed SHA-256 independently. The RFC example also checks the published
canonical output from sections 3.2.2–3.2.3. The negative cases were
checked by a temporary strict parser and scoped schema checks. These
vectors specify contract behavior and do not imply C5 production support.
