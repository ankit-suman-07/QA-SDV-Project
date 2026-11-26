# Run B verification

[Frozen task and plan](baseline.md) · [Paired comparison](../../../../../docs/findings/v2-frontend-skill-comparison.md)

## Initial implementation

Tested `798ed94723b74d00a020e383d1d86f91224f2e50` before review corrections.

- `cd frontend && npm test` exited 0 with 12 passing and 0 failing. [Log](initial-unit.txt)
- The frozen synthetic browser command first exited 1 during Chrome startup because the process sandbox denied Crashpad's socket operation. The same harness run outside that sandbox exited 1 at line 157. All V2 assertions ran and all four captures were written. The V1 fallback showed `20 m` while the assertion required `20 m (last known)`. The assertions after that line were unexecuted. [Launch log](initial-browser.txt) · [Assertion log](initial-browser-retry.txt)
- Initial captures at 1100 × 850 and 390 × 844. [Stale](initial/desktop-stale.png) · [Unavailable](initial/desktop-unavailable.png) · [Recovering](initial/desktop-recovering.png) · [Narrow](initial/narrow-stale.png)

## Review and final implementation

The correction adds last-known distance labelling to the V1 fallback, preserves case for roster vehicle IDs that inherited uppercase from the shared table rule, and gives selected health and availability the same status treatment as roster values. Source age is calculated against fleet `generatedAt`. The selected API response supplies its own source timestamp but no evaluation timestamp or explicit provenance field in the production DTO. The UI uses explicit provenance when supplied and the existing preview/mock marker when applicable.

- The corrected frontend in the checkpoint containing this file passed `cd frontend && npm test` (exit 0, 12/12) and the unchanged frozen Chrome harness (exit 0). [Unit log](final-unit.txt) · [Browser log](final-browser.txt)
- Common browser coverage includes roster identities, availability and critical totals, stale and unavailable details, returning to the recovering vehicle, a delayed state reply, selected-vehicle action transitions through acceptance/execution/timeout/success, independent recovery, restart payload/history, keyboard selection and visible focus at 390 px, and V1 default routing/rendering.
- Final captures. [Stale](final/desktop-stale.png) · [Unavailable](final/desktop-unavailable.png) · [Recovering](final/desktop-recovering.png) · [Narrow](final/narrow-stale.png)

Browser command from repository root, with Playwright Core 1.56.1 and Chrome 157.0.8103.50:

```bash
PLAYWRIGHT_MODULE=/tmp/sdv-run-b-tools/node_modules/playwright-core/index.mjs \
FLEET_SCREENSHOTS=evidence/v2/skill-evaluation/frontend-design/run-b-customized/final \
node frontend/tests/v2-fleet-browser.mjs
```

The browser harness simulates HTTP routes with shared fixtures. Live backend, fleet persistence, CARLA, native diagnostics and assistive technology testing were unexecuted. Browser routes and model tests together cover previous-vehicle responses. The browser harness specifically delays a state response, and the model tests cover stale history and action responses.

A supplemental synthetic run inserted the following before the frozen harness navigates to the V1 default. It exited 0. [Log](supplemental-browser.txt) · [768 px capture](supplemental/intermediate-stale.png)

```js
await page.setViewportSize({ width: 768, height: 900 });
assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
assert.equal(await roster.getByRole('rowheader').count(), 3);
assert.equal(await page.getByRole('link', { name: 'Open diagnostics' }).isVisible(), true);
await capture('intermediate-stale');
console.log('PASS: 768 px width, roster semantics and diagnostics link');
```
