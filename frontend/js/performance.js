import { createPerformanceApi } from "./performance-api.js";
import {
  formatLatencyCard,
  formatLatencyTable,
  formatThroughputCard,
  formatThroughputTable,
  formatSuccessRate,
} from "./units.js";

const el = {
  source: document.getElementById("perf-source"),
  avgLatency: document.getElementById("summary-avg-latency"),
  p95Latency: document.getElementById("summary-p95-latency"),
  throughput: document.getElementById("summary-throughput"),
  successRate: document.getElementById("summary-success-rate"),
  latencyChart: document.getElementById("latency-chart"),
  throughputChart: document.getElementById("throughput-chart"),
  tableBody: document.getElementById("experiment-table-body"),
  backendCount: document.getElementById("backend-test-count"),
  backendNote: document.getElementById("backend-test-note"),
  pythonCount: document.getElementById("python-test-count"),
  pythonNote: document.getElementById("python-test-note"),
  emptyState: document.getElementById("perf-empty-state"),
  content: document.getElementById("perf-content"),
};

function renderBarChart(svg, entries, key, color, unitLabel) {
  const width = 460,
    height = 200,
    padding = { top: 10, right: 10, bottom: 28, left: 40 };
  const innerW = width - padding.left - padding.right;
  const innerH = height - padding.top - padding.bottom;
  const maxVal = Math.max(...entries.map((e) => e[key])) * 1.15;
  const barWidth = innerW / entries.length - 16;

  let bars = "";
  let labels = "";
  entries.forEach((e, i) => {
    const barHeight = (e[key] / maxVal) * innerH;
    const x = padding.left + i * (innerW / entries.length) + 8;
    const y = padding.top + innerH - barHeight;
    bars += `<rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" fill="${color}" rx="3">
      <title>${e.intervalSeconds}s: ${e[key].toFixed(2)} ${unitLabel}</title>
    </rect>`;
    labels += `<text x="${x + barWidth / 2}" y="${height - 8}" text-anchor="middle" font-size="11" fill="var(--color-text-muted)">${e.intervalSeconds}s</text>`;
  });

  const axis = `<line x1="${padding.left}" y1="${padding.top + innerH}" x2="${width - padding.right}" y2="${padding.top + innerH}" stroke="var(--color-border)" />`;

  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.innerHTML = axis + bars + labels;
}

(async function init() {
  const api = createPerformanceApi();
  const data = await api.getResults();

  if (!data || !data.experiments || data.experiments.length === 0) {
    el.emptyState.hidden = false;
    el.content.hidden = true;
    return;
  }

  el.source.textContent = `Source: ${data.source}`;

  const sorted = data.experiments
    .slice()
    .sort((a, b) => b.intervalSeconds - a.intervalSeconds);
  const latest = sorted[sorted.length - 1];

  el.avgLatency.textContent = formatLatencyCard(latest.averageLatencyMs);
  el.p95Latency.textContent = formatLatencyCard(latest.p95LatencyMs);
  el.throughput.textContent = formatThroughputCard(
    latest.throughputMessagesPerSecond,
  );
  el.successRate.textContent = formatSuccessRate(latest.successRatePercent);

  renderBarChart(
    el.latencyChart,
    sorted,
    "averageLatencyMs",
    "var(--color-blue)",
    "ms",
  );
  renderBarChart(
    el.throughputChart,
    sorted,
    "throughputMessagesPerSecond",
    "var(--color-teal)",
    "msg/s",
  );

  el.tableBody.innerHTML = "";
  sorted.forEach((e) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${e.intervalSeconds}s</td>
      <td>${e.messageCount}</td>
      <td>${formatLatencyTable(e.averageLatencyMs)}</td>
      <td>${formatLatencyTable(e.p95LatencyMs)}</td>
      <td>${formatThroughputTable(e.throughputMessagesPerSecond)}</td>
      <td>${formatSuccessRate(e.successRatePercent)}</td>
    `;
    el.tableBody.appendChild(tr);
  });

  const { backend, python } = data.testSummary;
  el.backendCount.textContent = `${backend.passed}/${backend.total}`;
  el.pythonCount.textContent = `${python.passed}/${python.total}`;
  if (!backend.verified) {
    el.backendNote.textContent =
      "Not run in this environment \u2014 confirm via mvn test";
  }
  if (python.verified) {
    el.pythonNote.textContent = "Verified this run";
    el.pythonNote.classList.add("test-summary__note--green");
  }
})();
