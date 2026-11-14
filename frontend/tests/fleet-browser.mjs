// Opt-in browser integration: run after scripts.v1_dev.fleet_smoke --hold.
// PLAYWRIGHT_MODULE may point to an isolated playwright-core installation.
import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE ?? 'playwright-core');
const stackFile = process.argv[2] ?? '/tmp/a5-fleet-smoke/stack.json';
const stack = JSON.parse(await readFile(stackFile, 'utf8'));
const artifactDir = path.dirname(stackFile);
const controls = (id, state) => fetch(`${stack.mock}/_mock/states/${id}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ state }) });
const healthy = () => Promise.all(['vehicle-001', 'vehicle-002'].map(id => controls(id, 'healthy')));
const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH ?? '/usr/bin/google-chrome', headless: true, args: ['--no-sandbox'] });
const checks = []; const errors = [];
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(value => { globalThis.SDV_CONFIG = { API_BASE_URL: value }; }, stack.api);
  async function textIs(id, value) {
    await page.waitForFunction(({ id, value }) => document.getElementById(id)?.textContent === value, { id, value });
  }
  await healthy();
  await page.goto(stack.frontend);
  await textIs('healthyVehicles', '2');
  await textIs('vehicle-id', 'vehicle-001');
  await textIs('vehicle-availability', 'AVAILABLE');
  checks.push('fleet totals and selected vehicle from actual Java backend');
  await page.selectOption('#vehicle-select', 'vehicle-002');
  await textIs('thing-id', 'sdv:vehicle-002');
  await page.click('#inject');
  await page.waitForFunction(() => document.getElementById('action-status').textContent.includes('ACCEPTED / DISPATCHED'));
  await textIs('criticalVehicles', '1');
  await textIs('vehicle-health', 'CRITICAL');
  await textIs('vehicle-faults', 'LIDAR_OBSTRUCTION');
  await page.screenshot({ path: path.join(artifactDir, 'fleet-mock-fault.png'), fullPage: true });
  checks.push('inject acknowledgement and separately polled fault, vehicle-001 isolated');
  await controls('vehicle-001', 'healthy');
  await page.click('#clear');
  await textIs('healthyVehicles', '2');
  await textIs('vehicle-health', 'HEALTHY');
  checks.push('clear and observed mock recovery');
  await controls('vehicle-002', 'stale'); await page.click('#refresh');
  await textIs('staleVehicles', '1');
  await textIs('vehicle-health', 'HEALTHY (last known)');
  await textIs('vehicle-availability', 'STALE');
  checks.push('stale health visibly labelled and excluded from current counts');
  await controls('vehicle-002', 'missing'); await page.click('#refresh');
  await textIs('unavailableVehicles', '1'); await textIs('vehicle-health', 'Unknown');
  checks.push('missing twin shown unavailable with unknown health');
  await healthy();
  // Delay a genuine Java response, switch again, then release it.
  let releaseOld, enteredOld, finishOld;
  const gate = new Promise(resolve => { releaseOld = resolve; });
  const entered = new Promise(resolve => { enteredOld = resolve; });
  const finished = new Promise(resolve => { finishOld = resolve; });
  const oldRoute = async route => { const response = await route.fetch(); enteredOld(); await gate; await route.fulfill({ response }); finishOld(); };
  await page.route('**/api/v1/vehicles/vehicle-001/state', oldRoute);
  await page.selectOption('#vehicle-select', 'vehicle-001'); await entered;
  await page.selectOption('#vehicle-select', 'vehicle-002'); await textIs('thing-id', 'sdv:vehicle-002');
  releaseOld(); await finished;
  await page.unroute('**/api/v1/vehicles/vehicle-001/state', oldRoute);
  await page.waitForTimeout(100);
  assert.equal(await page.locator('#vehicle-id').textContent(), 'vehicle-002');
  assert.equal(await page.locator('#thing-id').textContent(), 'sdv:vehicle-002');
  checks.push('outdated vehicle response cannot overwrite newer selection');
  // Browser-only error simulation; successful integration requests above use Java.
  await page.route('**/api/v1/fleet', route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ message: 'Browser test outage' }) }));
  await page.route('**/api/v1/vehicles/vehicle-002/state', route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ message: 'Selected read unavailable' }) }));
  await page.click('#refresh');
  await page.waitForFunction(() => !document.getElementById('fleet-error').hidden && !document.getElementById('vehicle-error').hidden);
  assert.match(await page.locator('#fleet-status').textContent(), /last known/);
  assert.match(await page.locator('#vehicle-health').textContent(), /last known/);
  checks.push('request errors visibly label retained data as last known');
  await page.unroute('**/api/v1/fleet'); await page.unroute('**/api/v1/vehicles/vehicle-002/state');
  await healthy(); await page.click('#refresh'); await textIs('healthyVehicles', '2');
  await page.setViewportSize({ width: 375, height: 812 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  checks.push('375px layout has no horizontal overflow');
  await page.goto(stack.frontend + '/vehicle.html');
  await page.waitForSelector('#metric-temperature');
  assert.match(await page.title(), /Vehicle Dashboard/);
  checks.push('legacy vehicle page remains accessible');
  assert.deepEqual(errors, []);
  await writeFile(path.join(artifactDir, 'browser-result.json'), JSON.stringify({ status: 'PASS', checks, pageErrors: errors }, null, 2) + '\n');
  console.log(JSON.stringify({ status: 'PASS', checks: checks.length }));
} finally { await browser.close(); }
