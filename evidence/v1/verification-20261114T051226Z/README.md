# Fresh Phase V1 verification — 2026-11-14 UTC

Assessed `main` / `origin/main`: `ac701cd9a56ffd1031d6cd8744e413075ab4b955`; initial working tree clean.

**Verdict: DEFECTS FOUND.** Real two-vehicle edge routing passed, but provider recovery failed; the existing pressure-unit boundary is inconsistent. Real Ditto acceptance and required Linux/Kanto verification are blocked.

- [Findings and acceptance matrix](../../../docs/findings/v1-implementation-verification.md)
- [Manifest and exact commands](manifest.json), [machine-readable results](result-summary.json), [artifact SHA256 index](artifact-sha256.json)
- [Final Python](python-unit-final.log), [Java21](backend.log), [frontend](frontend-unit.log), [actual KUKSA](kuksa-live-signals.log), [actual MQTT transport](mqtt-live-transport.log)
- [Actual Java + mock HTTP + actual Chrome](mock-smoke-port3000/result.json), [browser result](mock-smoke-port3000/browser-result.json), [screenshot of mock-data dashboard](mock-smoke-port3000/fleet-mock-fault.png)
- [Real routing checks](live-edge/checks.json), [MQTT capture](live-edge/mqtt.jsonl), [API responses](live-edge/api-responses.json), [monotonic measurements](live-edge/measurements.json). Individual states/writes in that directory use a **mock in-memory writer**, not real Ditto.
- [Recovery failure](edge-recovery/results.json), [qualification excluding weak original app-restart timing](edge-recovery/qualification.json), [corrected fresh-source app restart](app-restart/result.json), [unit-boundary probe](tire-unit-boundary.log)
- [Unavailable live prerequisites](blocked-live-checks.json), [exact-head CI](ci-exact-sha.json), [source hashes](source-hashes.json), [implementation hashes](implementation-hashes.json)
- [Owned scenario cleared](final-owned-context.log), [Compose cleanup](edge-cleanup.json), [final Docker inventory](final-docker-inventory.log), [final listeners](final-ports.log)

Each root command JSON records command/cwd/environment overrides, timestamps, exit code and paired output path. Initial collection/import/browser setup failures are retained; final results are explicitly named. `mock-smoke/ATTEMPT-NOTES.json` qualifies superseded mixed scratch artifacts. Recovery result JSON's original app-restart PASS/timing is superseded by the qualification and corrected `app-restart/` check.

`harnesses/` preserves temporary verification helpers, not product implementation. The helpers record this workstation's temporary tooling paths and must be configured for another host. No real Ditto credentials were available or recorded. Test HTTP authentication uses synthetic fixture credentials only. Raw `.log` files are intentionally saved locally despite the repository's existing ignore rule; no ignore-policy edits or staging were performed.

No test-owned services remain running. Only test-owned resources were stopped; no volumes were deleted. Image/build caches and the stopped standalone transport broker may remain.
