# V2 dashboard verification

Starting main `5ad8792af2b0d0f044c646ea15923ce984efe110` includes merged
backend and action PRs #57 and #58. The tested dashboard revision is
`bacaba1816b9bdb9f024f43859f11295709b2918`.
[State and fleet handoff](../backend-fleet/README.md) · [Action handoff](../diagnostic-action-tracking/README.md)

## Configuration and integration walkthrough

Set `globalThis.SDV_CONFIG.V2_API_BASE_URL` before the dashboard module loads.
Use an empty string for a same-origin gateway or an explicit API prefix for
a permitted local preview. Leaving the setting undefined retains the V1
dashboard. Set `FLEET_PREVIEW: true` for synthetic preview input.

The dashboard uses the prescribed three-vehicle roster while loading and
validates that the fleet snapshot contains all three in sorted order. Its
counts come from the fleet response and use that response's generatedAt.
Selected state is sampled independently and displays its own event and
source timestamp. Selection and request versions isolate delayed replies.
Aged or failed reads label retained health as last known. The backend
currently projects LiDAR and action history. Speed, battery, coolant, tire,
per-sample provenance and individual fault history are absent from the
merged V2 API projection. The UI shows unknown provenance when the
response and preview configuration supply none.

The backend requires a trusted bearer for actions and history. Serve the
dashboard and protected routes through the same authorized gateway. The
gateway must authenticate the operator, enforce target authorization and
cross-site request protection, and attach the backend credential server
side. The browser sends ordinary same-origin requests. It holds no
service bearer, Ditto, broker or executor credentials. Gateway deployment
and live executor/policy verification remain integration gates.

1. Open the V2 fleet view and verify exactly three registered entries.
   Select an unavailable vehicle. Verify missing health and distance are
   shown as unknown and compare the fleet generatedAt with the selected
   observation's source timestamp.
2. Select the assigned test vehicle. Inject an obstruction and observe
   ACCEPTED, then EXECUTING or a terminal result. Verify the other two
   vehicles stay isolated. Check health on subsequent observations.
3. Clear after executor completion. Confirm SUCCEEDED records clear
   execution and check separately for IN_PROGRESS and observed recovery.
4. Select the managed test app's vehicle and request restart. Check its
   correlated action and history. Verify restart success requires the
   executor's lifecycle and fresh observation evidence. If dispatch is
   uncertain, retain the displayed ID and check status rather than
   submitting a new action. Switch vehicles during polling and confirm
   the selected vehicle's state, history and current action stay separate.

## Checks and boundaries

Used Ankit verification-before-completion v1.0.0 to trace counts, loading,
unavailable/recovery rendering, selected-target races, dispatch uncertainty,
and protected request behavior to the checks below. No versioned Ankit TDD
derivative was available.

- `cd frontend && npm test` with Node 24.18.0 exited 0. Twelve tests passed,
  including existing V1 cases and five V2 API/model cases using shared
  synthetic fixtures. `node --check` passed for all frontend JS modules.
- `PLAYWRIGHT_MODULE=/tmp/sdv-v2-dashboard-tooling/node_modules/playwright-core/index.mjs node frontend/tests/v2-fleet-browser.mjs`
  exited 0 with headless Chrome and an isolated Playwright Core 1.56.1 from
  the npm cache. The actual dashboard rendered against intercepted
  synthetic V2 HTTP routes. Chrome checked three entries, missing telemetry,
  stale and recovering fields, timeout, clear versus recovery, restart and
  history. No Spring backend or joined/live integration is claimed for
  this browser component smoke. No screenshot artifact was produced.
- `python -m scripts.v2_dev.check` exited 0, eight prep tests and 23 synthetic
  fixture files and guide links checked.
- `git diff --check origin/main HEAD` passed. Evidence links resolve. No
  owned services are left running.

Joined verification still needs the real backend behind the authorized
gateway, Bayan's live twin and action results, and the selected scenario
and lifecycle executors. No backend schemas were changed.
