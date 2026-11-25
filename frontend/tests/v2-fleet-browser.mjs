// Opt-in browser component smoke. Routes are simulated from shared V2 fixtures.
import assert from 'node:assert/strict';
import { readFile, mkdir } from 'node:fs/promises';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE ?? 'playwright-core');

const root = new URL('../', import.meta.url);
const fixture = async name => JSON.parse(await readFile(new URL(`../tests/fixtures/v2/${name}.json`, root)));
const recovery = await fixture('health-events/recovery-sensor-failure');
const actionFixture = (await fixture('diagnostics/cases')).request;
const origin = 'http://localhost:19085';
const ids = ['vehicle-001', 'vehicle-002', 'vehicle-003'];
const views = new Map();
views.set('vehicle-002', {
  ...recovery, thingId: 'sdv:vehicle-002', healthStatus: recovery.health, availability: 'AVAILABLE',
  activeFaults: recovery.faults, lastEventId: recovery.eventId,
});
views.set('vehicle-001', {
  ...(await fixture('twins/vehicle-001')).features.v2.properties,
  thingId: 'sdv:vehicle-001', healthStatus: 'HEALTHY', availability: 'STALE', activeFaults: [],
});
views.set('vehicle-003', {
  vehicleId: 'vehicle-003', thingId: 'sdv:vehicle-003', availability: 'UNAVAILABLE', healthStatus: null, lidar: null,
});
const browser = await chromium.launch({
  executablePath: process.env.CHROME_PATH ?? '/usr/bin/google-chrome', headless: true, args: ['--no-sandbox'],
});
try {
  const page = await browser.newPage({ viewport: { width: 1100, height: 850 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => { globalThis.SDV_CONFIG = { V2_API_BASE_URL: '', FLEET_PREVIEW: true }; });
  let releaseDelayedReply;
  let delayedReplyFinished;
  let lastAction, actionStatus = 'ACCEPTED';
  const submitted = [];
  await page.route(`${origin}/**`, async route => {
    const path = new URL(route.request().url()).pathname;
    const respond = (json, status = 200) => route.fulfill({ json, status });
    if (path === '/api/v2/fleet') {
      return respond({
        generatedAt: '2026-01-01T00:00:04Z', vehicles: ids.map(id => views.get(id)),
        totalVehicles: 3, availableVehicles: 1, staleVehicles: 1, unavailableVehicles: 1,
        healthyVehicles: 0, warningVehicles: 0, criticalVehicles: 1,
      });
    }
    const state = path.match(/^\/api\/v2\/vehicles\/(vehicle-00[123])\/state$/);
    if (state) {
      if (state[1] === 'vehicle-002' && releaseDelayedReply === undefined && delayedReplyFinished) {
        await new Promise(resolve => { releaseDelayedReply = resolve; });
        await respond(views.get(state[1]));
        delayedReplyFinished();
        return;
      }
      return respond(views.get(state[1]));
    }
    const history = path.match(/^\/api\/v2\/diagnostics\/vehicles\/(vehicle-00[123])\/actions$/);
    if (history) return respond(lastAction?.vehicleId === history[1] ? [{ ...lastAction, status: actionStatus }] : []);
    if (path === '/api/v2/diagnostics/actions' && route.request().method() === 'POST') {
      assert.equal(route.request().headers().authorization, undefined);
      submitted.push(route.request().postDataJSON());
      lastAction = submitted.at(-1);
      actionStatus = 'ACCEPTED';
      return respond({ ...lastAction, status: actionStatus }, 202);
    }
    if (lastAction && path === `/api/v2/diagnostics/actions/${lastAction.actionId}`) {
      return respond({ ...lastAction, status: actionStatus });
    }
    if (path.startsWith('/api/')) return respond({ message: 'Unexpected component request' }, 404);
    const file = path === '/' ? 'index.html' : path.slice(1);
    const type = { html: 'text/html', css: 'text/css', js: 'text/javascript' }[file.split('.').at(-1)];
    if (!type) return route.fulfill({ status: 404 });
    return route.fulfill({ body: await readFile(new URL(file, root)), contentType: type });
  });

  const see = (id, value) => page.waitForFunction(({ id, value }) =>
    document.getElementById(id)?.textContent.includes(value), { id, value });
  const screenshotDir = process.env.FLEET_SCREENSHOTS;
  if (screenshotDir) await mkdir(screenshotDir, { recursive: true });
  const capture = name => screenshotDir && page.screenshot({ path: `${screenshotDir}/${name}.png`, fullPage: true });
  await page.goto(origin);
  await see('totalVehicles', '3');
  assert.deepEqual(await page.locator('#fleet-vehicles th[scope=row]').allTextContents(), ids);
  for (const key of ['availableVehicles', 'staleVehicles', 'unavailableVehicles', 'criticalVehicles']) {
    assert.equal(await page.locator(`#${key}`).textContent(), '1');
  }
  assert.equal(await page.locator('#preview-label').isVisible(), true);
  await see('vehicle-health', 'HEALTHY (last known)');
  await capture('desktop-stale');
  const delayed = new Promise(resolve => { delayedReplyFinished = resolve; });
  await page.selectOption('#vehicle-select', 'vehicle-002');
  await page.selectOption('#vehicle-select', 'vehicle-003');
  await see('vehicle-availability', 'UNAVAILABLE');
  const deadline = Date.now() + 5000;
  while (!releaseDelayedReply && Date.now() < deadline) await new Promise(resolve => setTimeout(resolve, 10));
  assert.ok(releaseDelayedReply, 'Delayed request reached the synthetic route');
  releaseDelayedReply();
  await delayed;
  await page.waitForLoadState('networkidle');
  await see('vehicle-id', 'vehicle-003');
  await see('vehicle-availability', 'UNAVAILABLE');
  await see('vehicle-health', 'Unknown');
  await see('lidar-distance', 'Unknown');
  await capture('desktop-unavailable');
  await page.selectOption('#vehicle-select', 'vehicle-002');
  await see('vehicle-recovery', 'IN_PROGRESS');
  await see('vehicle-faults', 'LIDAR_SENSOR_FAILURE');
  await see('source-provenance', 'SYNTHETIC');
  await page.click('#inject');
  await see('action-status', 'ACCEPTED');
  assert.equal(submitted[0].action, actionFixture.action);
  assert.equal(submitted[0].vehicleId, 'vehicle-002');
  actionStatus = 'EXECUTING';
  await page.click('#refresh');
  await see('action-status', 'EXECUTING');
  actionStatus = 'TIMED_OUT';
  await page.click('#refresh');
  await see('action-status', 'TIMED_OUT');
  await page.click('#clear');
  await see('action-status', 'ACCEPTED');
  actionStatus = 'SUCCEEDED';
  await page.click('#refresh');
  await see('action-status', 'Check observed recovery separately');
  await see('vehicle-recovery', 'IN_PROGRESS');
  await page.click('#restart');
  await see('action-status', 'ACCEPTED');
  assert.equal(submitted.at(-1).action, 'RESTART_APP');
  assert.equal('scenario' in submitted.at(-1), false);
  await see('action-history', 'RESTART_APP');
  await capture('desktop-recovering');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator('#refresh').focus();
  await page.keyboard.press('Tab');
  assert.equal(await page.locator('#vehicle-select').evaluate(select => select.matches(':focus-visible')), true);
  assert.equal(await page.locator('#vehicle-select').evaluate(select => getComputedStyle(select).outlineStyle), 'solid');
  await page.keyboard.press('Home');
  await see('vehicle-health', 'HEALTHY (last known)');
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await capture('narrow-stale');
  assert.deepEqual(errors, []);
  console.log('PASS: Chrome V2 dashboard component smoke with synthetic HTTP routes');
} finally {
  await browser.close();
}
