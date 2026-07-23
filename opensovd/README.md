# Eclipse OpenSOVD - Diagnostic Interface (Atharva)

## Status
Standalone feasibility only - not yet wired to the Ditto/Kuksa pipeline.

## Run (mock mode)
```bash
docker run -p 7690:7690 ghcr.io/eclipse-opensovd/opensovd-gateway --mock
curl -s http://localhost:7690/sovd/v1
```
API is discoverable: root → `components` → `{component}/data` → `{signal}`.
See `docs/evidence/component-tests/opensovd-mock/` for the full API
traversal with real mock sensor values (voltage, temperature).

## Open question (pending Day 2)
Whether mock mode accepts pushed fault data, or only serves its own canned
values - unresolved, blocks building the real fault-mapping adapter
(`config/fault-mappings.json`, per the finalized folder structure).