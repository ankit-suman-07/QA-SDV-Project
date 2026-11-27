# Run A verification

Baseline and frozen task in [baseline.md](baseline.md). Run A applied the original frontend-design skill's two-pass design process and screenshot critique. The design follows the reference's top navigation, count strip, roster, selected vehicle and telemetry grouping, independent execution and recovery panels, and full-width observation strip. The page uses project-compatible local sans-serif fallbacks and CSS without visual dependencies. The repository verification skill governed the checklist and evidence.

| Checkpoint | Exact revision | Results |
|---|---|---|
| First completed implementation | `d3cb0699ad2136f67680c0a1e1d90e304574baf3` | 12 unit tests passed, exit 0. Chrome synthetic V2 check passed, exit 0. Diff and syntax checks passed, exit 0. [Initial desktop](initial/desktop-stale.png) and [initial narrow](initial/narrow-stale.png) show the first implementation. |
| Screenshot review corrections | `ca1cdb4ab6d6bd2f12144ba1d5b382b0a640bd2b` | 12 unit tests passed, exit 0. Chrome synthetic V2 and V1-default check passed, exit 0. Diff and browser script syntax checks passed, exit 0. CSS now stacks labeled roster fields on narrow screens. The shared renderer labels stale V1 LiDAR and faults consistently with V2. Column headings use sentence case. |

Chrome initially exited 1 on sandboxed launch because Crashpad's socket setup returned `Operation not permitted`. Running the same check with shell escalation resolved that launch blocker. The initial browser test run against archived baseline `700fc22a8f546b5159056242d95d85b6f0ba4388` then exited 1 at the new semantic roster assertion, which expected three row headers and received zero.

## Checklist results

1. Reviewed the 1100 px desktop and 390 px narrow captures. The first narrow capture exposed wrapped words in the six-column roster despite no page overflow. The review commit corrected the narrow arrangement while retaining row headers.
2. Chrome checked the ordered three V2 identities, total and status counts, selected identity, LiDAR and fault fields. The V1-default synthetic check returned two fixture vehicles, used the legacy endpoints and hid V2-only controls. Legacy vehicle and diagnostics links open the existing V1 pages with their existing vehicle target.
3. Captures cover [stale](screenshots/desktop-stale.png), [unavailable](screenshots/desktop-unavailable.png), and [available with recovery in progress](screenshots/desktop-recovering.png). Chrome checked visible synthetic labeling, retained health, unknown health and LiDAR, recovery and provenance. Successful clear execution was observed while recovery remained in progress. The available LiDAR sensor-failure fixture has no distance.
4. The browser withheld vehicle-002's response until vehicle-003 had rendered, then checked that vehicle-003's availability and empty observation persisted. Existing unit tests also cover delayed observation, history and action replies.
5. The [390 × 844 viewport capture](screenshots/narrow-stale.png) is full-page. Chrome checked that the document fits its viewport and that Tab reaches a visible focus outline and Home selects the first vehicle. The roster retains accessible row headers. No dedicated assistive-technology session was run.

Synthetic component checks intercepted HTTP in Chrome using the shared V2 twin, recovery and diagnostics fixtures with roster and action lifecycle responses assembled by the browser harness. Unit tests exercised the client and state model. No live backend, CARLA, persistence, authorization gateway or native diagnostic integration was exercised. Speed, battery, coolant temperature and tire pressure were omitted because the current state endpoints used by Fleet do not supply them. No comparison outcome was assessed.

## Rerun

Use Node 24.18.0, Chrome 157.0.8103.50, and Playwright Core 1.65.1. The browser driver was installed in a temporary directory after no usable local installation was found. Use an existing matching installation when available.

```sh
# Optional isolated setup when the test driver is absent
npm install --prefix /tmp/sdv-fleet-browser --no-save --no-package-lock playwright-core@1.65.1

# From the checkout root
git diff --check
node --check frontend/js/fleet-dashboard.js
node --check frontend/tests/v2-fleet-browser.mjs
npm --prefix frontend test
CHROME_PATH=/usr/bin/google-chrome \
PLAYWRIGHT_MODULE=/tmp/sdv-fleet-browser/node_modules/playwright-core/index.mjs \
FLEET_SCREENSHOTS=/tmp/sdv-fleet-final \
node frontend/tests/v2-fleet-browser.mjs
```

Use the final browser harness from `ca1cdb4` for the same comparison checks in Run B. For the first implementation's exact checks, run from `d3cb069` and set `FLEET_SCREENSHOTS=/tmp/sdv-fleet-initial`. To reproduce the baseline roster assertion failure, archive `frontend` and `tests/fixtures/v2` from the starting SHA, copy the browser harness from `d3cb069` into the archived frontend tests, and run that harness without `FLEET_SCREENSHOTS`. These checks make no requests to a running stack.
