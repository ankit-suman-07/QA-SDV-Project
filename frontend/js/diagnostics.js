import { CONFIG } from "./config.js";
import {
  createMockDiagnosticApi,
  createHttpDiagnosticApi,
} from "./diagnostic-api.js";
import { renderStatusBadge } from "./status-mapping.js";

const SCENARIO = "COOLING_SYSTEM_FAILURE";
const TERMINAL = ["COMPLETED", "FAILED", "REJECTED"];

const CONFIRM_COPY = {
  INJECT_SCENARIO: {
    title: "Inject Cooling System Failure?",
    body: "This diagnostic action will request a simulated high-temperature and low-coolant-pressure condition for vehicle-001. Continue only in the development environment.",
    confirmLabel: "Inject scenario",
    tone: "destructive",
  },
  CLEAR_SCENARIO: {
    title: "Clear Cooling System Failure?",
    body: "This will request recovery of the simulated cooling signals. The dashboard may take several seconds to show HEALTHY.",
    confirmLabel: "Clear scenario",
    tone: "default",
  },
};

let history = [];
let isSubmitting = false;
let simulateValidationError = false;
let pollTimer = null;

const el = {
  injectBtn: document.getElementById("inject-btn"),
  clearBtn: document.getElementById("clear-btn"),
  validationToggle: document.getElementById("validation-error-toggle"),
  errorSlot: document.getElementById("error-slot"),
  currentActionSlot: document.getElementById("current-action-slot"),
  historyBody: document.getElementById("history-body"),
  historyEmpty: document.getElementById("history-empty"),
  overlay: document.getElementById("dialog-overlay"),
  dialogTitle: document.getElementById("dialog-title"),
  dialogBody: document.getElementById("dialog-body"),
  dialogConfirm: document.getElementById("dialog-confirm"),
  dialogCancel: document.getElementById("dialog-cancel"),
  liveRegion: document.getElementById("live-region"),
  faultSlot: document.getElementById("diagnostics-fault-slot"),
};

function getDiagnosticApi() {
  return CONFIG.USE_MOCK_API
    ? createMockDiagnosticApi({
        simulateValidationError,
        completeAfterMs: 3000,
      })
    : createHttpDiagnosticApi();
}

function renderCurrentAction(action) {
  el.currentActionSlot.innerHTML = "";
  if (!action) {
    el.currentActionSlot.innerHTML = `<p class="hint">No action submitted yet.</p>`;
    return;
  }
  const dl = document.createElement("dl");
  dl.className = "diagnostics-detail-list";
  dl.innerHTML = `
    <div><dt>Action ID</dt><dd>${action.actionId}</dd></div>
    <div><dt>Status</dt><dd id="current-status-badge"></dd></div>
    <div><dt>Trace ID</dt><dd>${action.traceId}</dd></div>
    <div><dt>Requested</dt><dd>${new Date(action.requestedAt).toLocaleTimeString()}</dd></div>
  `;
  el.currentActionSlot.appendChild(dl);
  dl.querySelector("#current-status-badge").appendChild(
    renderStatusBadge(action.status),
  );
}

function renderHistory() {
  el.historyBody.innerHTML = "";
  el.historyEmpty.hidden = history.length !== 0;
  history.forEach((entry) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${entry.actionId}</td>
      <td>${entry.action}</td>
      <td>${entry.scenario}</td>
      <td></td>
      <td>${new Date(entry.requestedAt).toLocaleTimeString()}</td>
    `;
    tr.children[3].appendChild(renderStatusBadge(entry.status));
    el.historyBody.appendChild(tr);
  });
}

function renderFaultBanner(show) {
  el.faultSlot.innerHTML = "";
  if (!show) return;
  const div = document.createElement("div");
  div.className = "fault-banner fault-banner--red";
  div.setAttribute("role", "alert");
  div.innerHTML = `<span aria-hidden="true">\u26A0</span><div><div class="fault-banner__title">Active Fault: COOLING_SYSTEM_FAILURE</div><div class="fault-banner__subtitle">Severity: CRITICAL</div></div>`;
  el.faultSlot.appendChild(div);
}

function setSubmitting(value) {
  isSubmitting = value;
  el.injectBtn.disabled = value;
  el.clearBtn.disabled = value;
}

function showError(err) {
  el.errorSlot.innerHTML = "";
  if (!err) return;
  const div = document.createElement("div");
  div.className = "inline-error";
  div.setAttribute("role", "alert");
  div.innerHTML = `<strong>${err.code}</strong>: ${err.message}${err.path ? `<div>${err.path}</div>` : ""}`;
  el.errorSlot.appendChild(div);
}

function announce(text) {
  el.liveRegion.textContent = text;
}

async function pollUntilTerminal(actionId) {
  const api = getDiagnosticApi();
  const startedAt = Date.now();
  if (pollTimer) clearTimeout(pollTimer);

  async function tick() {
   if (Date.now() - startedAt > CONFIG.ACTION_TIMEOUT_MS) {
  el.currentActionSlot.querySelector("#current-status-badge")?.replaceChildren(
    renderStatusBadge("ACCEPTED", "Accepted (completion pending)")
  );
  announce("Action accepted. The backend hasn't reported completion yet.");
  return;
}
    }
    try {
      const result = await api.getAction(actionId);
      renderCurrentAction(result);
      history = [
        result,
        ...history.filter((e) => e.actionId !== result.actionId),
      ];
      renderHistory();
      announce(`Action ${result.actionId} is ${result.status}`);
      renderFaultBanner(
        result.action === "INJECT_SCENARIO" &&
          result.status !== "FAILED" &&
          result.status !== "REJECTED",
      );
      if (TERMINAL.includes(result.status)) return;
    } catch {
      // A single failed lookup doesn't end polling; try again next tick.
    }
    pollTimer = setTimeout(tick, CONFIG.ACTION_POLL_MS);
  }
  pollTimer = setTimeout(tick, CONFIG.ACTION_POLL_MS);
}

async function submitAction(action) {
  setSubmitting(true);
  showError(null);
  try {
    const api = getDiagnosticApi();
    const response = await api.submitAction({
      vehicleId: CONFIG.VEHICLE_ID,
      action,
      scenario: SCENARIO,
    });
    renderCurrentAction(response);
    history = [response, ...history];
    renderHistory();
    announce(`Action ${response.actionId} accepted`);
    if (action === "INJECT_SCENARIO") renderFaultBanner(true);
    if (action === "CLEAR_SCENARIO") renderFaultBanner(false);
    pollUntilTerminal(response.actionId);
  } catch (err) {
    const apiErr = err.apiError ?? {
      code: "UNKNOWN_ERROR",
      message: err.message,
    };
    showError(apiErr);
    announce(`Error: ${apiErr.message}`);
  } finally {
    setSubmitting(false);
  }
}

function openDialog(action) {
  const copy = CONFIRM_COPY[action];
  el.dialogTitle.textContent = copy.title;
  el.dialogBody.textContent = copy.body;
  el.dialogConfirm.textContent = copy.confirmLabel;
  el.dialogConfirm.className = `btn btn--${copy.tone === "destructive" ? "destructive" : "primary"}`;
  el.dialogConfirm.onclick = () => {
    closeDialog();
    submitAction(action);
  };
  el.overlay.hidden = false;
  el.dialogConfirm.focus();
}

function closeDialog() {
  el.overlay.hidden = true;
}

el.injectBtn.addEventListener(
  "click",
  () => !isSubmitting && openDialog("INJECT_SCENARIO"),
);
el.clearBtn.addEventListener(
  "click",
  () => !isSubmitting && openDialog("CLEAR_SCENARIO"),
);
el.dialogCancel.addEventListener("click", closeDialog);
el.overlay.addEventListener("click", (e) => {
  if (e.target === el.overlay) closeDialog();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !el.overlay.hidden) closeDialog();
});

if (!CONFIG.USE_MOCK_API) {
  document.getElementById("dev-switcher-panel").hidden = true;
} else {
  el.validationToggle.addEventListener("change", (e) => {
    simulateValidationError = e.target.checked;
  });
}

renderCurrentAction(null);
renderHistory();
