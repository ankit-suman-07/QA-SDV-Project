import { CONFIG } from "./config.js";
import {
  createMockVehicleApi,
  createHttpVehicleApi,
  loadFixture,
} from "./vehicle-api.js";
import { renderStatusBadge } from "./status-mapping.js";
import { getFreshness, formatRelativeAge } from "./freshness.js";
import { formatOneDecimal } from "./units.js";

const FIXTURE_NAMES = ["normal", "warning", "cooling-critical", "recovered"];
let currentFixtureName = "normal";
let currentFixture = null;
let simulateDisconnected = false;
let pollTimer = null;
let samples = []; // { t: secondsAgo, value }

const el = {
  connectionBadge: document.getElementById("connection-badge"),
  lastUpdated: document.getElementById("last-updated"),
  healthBadge: document.getElementById("health-badge-slot"),
  speed: document.getElementById("metric-speed"),
  battery: document.getElementById("metric-battery"),
  temperature: document.getElementById("metric-temperature"),
  coolant: document.getElementById("metric-coolant"),
  faultSlot: document.getElementById("fault-slot"),
  disconnectedBanner: document.getElementById("disconnected-banner"),
  retryBtn: document.getElementById("retry-btn"),
  fixtureSwitcher: document.getElementById("fixture-switcher"),
  disconnectToggle: document.getElementById("disconnect-toggle"),
  chartSvg: document.getElementById("telemetry-chart"),
  metricGrid: document.getElementById("metric-grid"),
};

function getVehicleApi() {
  if (!CONFIG.USE_MOCK_API) return createHttpVehicleApi();
  return createMockVehicleApi({
    fixture: currentFixture,
    simulateDisconnected,
  });
}

function setMetric(node, value, unit) {
  if (value === null || value === undefined) {
    node.innerHTML = `<span aria-hidden="true">\u2014</span><span class="sr-only">Value unavailable</span> <span class="metric-card__badge">Mock</span>`;
    node.classList.add("metric-card__value--muted");
  } else {
    node.classList.remove("metric-card__value--muted");
    node.innerHTML = `${value}<span class="metric-card__unit">${unit}</span>`;
  }
}

function renderFaultBanner(activeFaults, severity) {
  el.faultSlot.innerHTML = "";
  const div = document.createElement("div");
  if (activeFaults === null || activeFaults === undefined) {
    div.className = "fault-banner fault-banner--gray";
    div.setAttribute("role", "status");
    div.innerHTML = `<span aria-hidden="true">\u25CB</span><div><div class="fault-banner__title">Fault detail unavailable</div><div class="fault-banner__subtitle">The active-fault contract is not yet supplied by the backend.</div></div>`;
  } else if (activeFaults.length === 0) {
    div.className = "fault-banner fault-banner--green";
    div.setAttribute("role", "status");
    div.innerHTML = `<span aria-hidden="true">\u2713</span><div class="fault-banner__title">No active faults</div>`;
  } else {
    div.className = "fault-banner fault-banner--red";
    div.setAttribute("role", "alert");
    div.innerHTML = `<span aria-hidden="true">\u26A0</span><div><div class="fault-banner__title">Active Fault: ${activeFaults[0]}</div>${severity ? `<div class="fault-banner__subtitle">Severity: ${severity}</div>` : ""}</div>`;
  }
  el.faultSlot.appendChild(div);
}

function renderTelemetryChart() {
  const width = 560,
    height = 160,
    padding = 24;
  if (samples.length === 0) {
    el.chartSvg.innerHTML = `<text x="${width / 2}" y="${height / 2}" text-anchor="middle" fill="var(--color-text-muted)" font-size="13">Collecting samples\u2026</text>`;
    return;
  }
  const values = samples.map((s) => s.value);
  const min = 0,
    max = 150;
  const maxT = Math.max(...samples.map((s) => s.t), 30);

  const points = samples
    .slice()
    .reverse()
    .map((s) => {
      const x = padding + ((maxT - s.t) / maxT) * (width - padding * 2);
      const y =
        height -
        padding -
        ((s.value - min) / (max - min)) * (height - padding * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  el.chartSvg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  el.chartSvg.innerHTML = `
    <polyline points="${points}" fill="none" stroke="var(--color-blue)" stroke-width="2" />
    <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" stroke="var(--color-border)" />
  `;
}

async function fetchOnce() {
  const api = getVehicleApi();
  let state, health;
  try {
    [state, health] = await Promise.all([
      api.getState(CONFIG.VEHICLE_ID),
      api.getHealth(CONFIG.VEHICLE_ID),
    ]);
  } catch {
    // Section 15: preserve last-known data; only flip the connection badge.
    el.connectionBadge.replaceChildren(renderStatusBadge("DISCONNECTED"));
    el.disconnectedBanner.hidden = false;
    return;
  }

  // Network succeeded — connection status is settled regardless of what
  // happens in rendering below, so a display bug can never masquerade as
  // a disconnect.
  el.disconnectedBanner.hidden = true;
  const freshness = getFreshness(state.sourceTimestamp, CONFIG.STALE_AFTER_MS);
  el.connectionBadge.replaceChildren(
    renderStatusBadge(freshness.state === "stale" ? "STALE" : "CONNECTED"),
  );
  el.lastUpdated.textContent = `Last updated: ${formatRelativeAge(freshness.ageMs)}`;
  el.lastUpdated.title = state.sourceTimestamp;

  el.healthBadge.replaceChildren(renderStatusBadge(health.healthStatus));
  setMetric(
    el.temperature,
    formatOneDecimal(state.temperatureCelsius),
    "\u00b0C",
  );
  setMetric(el.coolant, formatOneDecimal(state.coolantPressureKpa), "kPa");

  const mockOnly = CONFIG.USE_MOCK_API ? currentFixture.mockOnly : null;
  setMetric(
    el.speed,
    mockOnly ? formatOneDecimal(mockOnly.speedKph) : null,
    "km/h",
  );
  setMetric(
    el.battery,
    mockOnly ? formatOneDecimal(mockOnly.batteryPercent) : null,
    "%",
  );

  const activeFaults = CONFIG.USE_MOCK_API
    ? currentFixture.activeFaults
    : undefined;
  renderFaultBanner(
    activeFaults,
    health.healthStatus === "CRITICAL"
      ? "CRITICAL"
      : health.healthStatus === "WARNING"
        ? "WARNING"
        : undefined,
  );

  // Section 5: keep last 30-60 local samples, no persistence.
  samples = [
    { t: 0, value: state.temperatureCelsius },
    ...samples.map((s) => ({ ...s, t: s.t + CONFIG.POLL_INTERVAL_MS / 1000 })),
  ].slice(0, 30);
  renderTelemetryChart();
}

function startPolling() {
  if (pollTimer) clearInterval(pollTimer);
  fetchOnce();
  pollTimer = setInterval(fetchOnce, CONFIG.POLL_INTERVAL_MS);
}

async function setFixture(name) {
  currentFixtureName = name;
  currentFixture = await loadFixture(name);
  [...el.fixtureSwitcher.children].forEach((btn) => {
    btn.setAttribute("aria-pressed", String(btn.dataset.fixture === name));
  });
  samples = [];
  startPolling();
}

function initFixtureSwitcher() {
  if (!CONFIG.USE_MOCK_API) {
    document.getElementById("dev-switcher-panel").hidden = true;
    return;
  }
  FIXTURE_NAMES.forEach((name) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "dev-switcher__btn";
    btn.textContent = name;
    btn.dataset.fixture = name;
    btn.setAttribute("aria-pressed", String(name === currentFixtureName));
    btn.addEventListener("click", () => setFixture(name));
    el.fixtureSwitcher.appendChild(btn);
  });

  el.disconnectToggle.addEventListener("change", (e) => {
    simulateDisconnected = e.target.checked;
    startPolling();
  });
}

el.retryBtn.addEventListener("click", fetchOnce);

// Stop polling when the tab is hidden/unloaded so requests never pile up.
document.addEventListener("visibilitychange", () => {
  if (document.hidden && pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  } else if (!document.hidden && !pollTimer) {
    startPolling();
  }
});
window.addEventListener(
  "beforeunload",
  () => pollTimer && clearInterval(pollTimer),
);

(async function init() {
  initFixtureSwitcher();
  if (CONFIG.USE_MOCK_API) {
    currentFixture = await loadFixture(currentFixtureName);
  }
  startPolling();
})();
