# SDV Frontend Dashboard

Plain HTML, CSS, and JavaScript (ES modules) — no build tool, no framework.
Implements the three pages from `SDV-Frontend-Dashboard-Handoff-Guide.pdf`:
Vehicle Dashboard, Diagnostics, Performance & Testing.

## Running it

Browsers block `fetch()` of local JSON files when a page is opened via
`file://`, so you need a static server (any will do):

```bash
cd frontend
python3 -m http.server 8080
# then open http://localhost:8080/index.html
```

Or with Node: `npx serve .`

## Switching between mock and real API

Edit `js/config.js`:

```js
export const CONFIG = {
  USE_MOCK_API: true,        // set false to call the real Spring Boot backend
  API_BASE_URL: "http://localhost:8080",
  POLL_INTERVAL_MS: 2000,
  STALE_AFTER_MS: 5000,
  ...
};
```

With `USE_MOCK_API: true`, all data comes from `mocks/*.json` and the
dev-only fixture switcher (visible at the top of Dashboard/Diagnostics)
lets you preview every required state without a backend.

**Before flipping to `false`:** confirm with the backend team that CORS
is enabled — browsers will silently block cross-origin requests
otherwise — and that `coolantPressureKpa` / `POST /api/v1/diagnostics/actions`
are actually deployed (see project notes; the handoff guide marks them
READY but this hadn't been independently confirmed as of this build).

## Structure

```
frontend/
  index.html            Vehicle Dashboard
  diagnostics.html      Diagnostics
  performance.html      Performance & Testing
  css/
    tokens.css           Design tokens (colors, spacing)
    layout.css            Sidebar, grid, page header
    components.css        Badges, cards, dialog, table, states
  js/
    config.js              Mock/real switch, timing constants
    api-client.js           fetch wrapper: timeout, retry, error normalization
    vehicle-api.js           GET state / GET health (mock + HTTP)
    diagnostic-api.js         POST action / GET action (mock + HTTP)
    performance-api.js         Loads mocks/performance.json (no live endpoint yet)
    status-mapping.js          Central status -> color/label/badge
    freshness.js                Staleness calculation
    units.js                     Formatting rules (decimals, %, msg/s)
    dashboard.js                  Page 1 logic
    diagnostics.js                  Page 2 logic
    performance.js                    Page 3 logic
  mocks/
    normal.json, warning.json, cooling-critical.json, recovered.json
    action-accepted.json (generated inline in diagnostic-api.js mock)
    validation-error.json
    performance.json        Built from real experiments/results/experiment-summary.csv
```

## What's real vs. mocked right now

| Data                                  | Status                                                                                            |
| ------------------------------------- | ------------------------------------------------------------------------------------------------- |
| Vehicle temperature, coolant pressure | Mocked by default; HTTP adapter ready, switch `USE_MOCK_API: false` once backend + CORS confirmed |
| Vehicle health                        | Same as above                                                                                     |
| Diagnostic action submit (POST)       | Same as above                                                                                     |
| Diagnostic action lookup (GET by id)  | Always mocked — guide marks the real endpoint IN PROGRESS                                         |
| Speed, battery, tire pressure         | Always mocked and labeled — not served by backend at all yet                                      |
| Active-fault detail                   | Always mocked — guide says do not infer from health status alone                                  |
| Performance page                      | Always fixture-based (real experiment numbers), per guide — no live metrics endpoint exists       |

## Manual test checklist

No test framework is wired up (plain JS, no bundler). Run through this
by hand and check off each item before calling a page done:

- [ ] Normal fixture: shows Healthy, correct temp/pressure, Connected, fresh timestamp
- [ ] Warning fixture: shows Warning badge
- [ ] Cooling-critical fixture: shows Critical + active fault banner
- [ ] Recovered fixture: shows Healthy again
- [ ] Simulate disconnected: shows Disconnected banner, Retry button works, last values stay visible
- [ ] Inject Scenario: confirm dialog appears, Accepted status + actionId shown, fault banner appears, then transitions to Completed after ~3s
- [ ] Clear Scenario: same flow, fault banner clears on completion
- [ ] Validation-error toggle + submit: inline error shown, not auto-retried
- [ ] Performance page: cards, both charts, table, and test summary all render with real experiment numbers
- [ ] Resize to ~375px width: sidebar collapses to a drawer, no horizontal scroll on any page
- [ ] Tab through every control: visible focus ring, nothing color-only (badges always have an icon + text)

## Known gaps / next steps

- No automated tests (would need a test runner, which conflicts with the "no framework" constraint — if that changes, Vitest + jsdom works with zero build config).
- Backend test count in `mocks/performance.json` (`backend.verified: false`) — 15 JUnit tests exist but couldn't be run in this environment (no Maven access); confirm pass count via `mvn test` before treating that number as final.
- `GET /api/v1/diagnostics/actions/{actionId}` stays mocked until the backend confirms it's live — swap the implementation in `diagnostic-api.js`'s `getAction` usage in `diagnostics.js` when ready.
