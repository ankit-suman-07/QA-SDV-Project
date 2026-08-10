// Section 3 — Status mapping table, centralized so no page repeats raw
// strings or picks colors independently.
const STATUS_MAP = {
  HEALTHY: { tone: "green", label: "Healthy" },
  COMPLETED: { tone: "green", label: "Completed" },
  CONNECTED: { tone: "green", label: "Connected" },

  WARNING: { tone: "amber", label: "Warning" },
  STALE: { tone: "amber", label: "Stale" },

  ACCEPTED: { tone: "blue", label: "Accepted" },
  IN_PROGRESS: { tone: "blue", label: "In progress" },

  CRITICAL: { tone: "red", label: "Critical" },
  FAILED: { tone: "red", label: "Failed" },

  REJECTED: { tone: "gray", label: "Rejected" },
  DISCONNECTED: { tone: "gray", label: "Disconnected" },
};

/** Looks up tone/label for any domain value used across the app. Falls
 * back to neutral gray "Unknown" rather than throwing, so an unexpected
 * backend value never breaks the page. */
export function getStatusPresentation(value) {
  if (!value) return { tone: "gray", label: "Unknown" };
  return STATUS_MAP[value] ?? { tone: "gray", label: value };
}

const TONE_ICON = {
  green: "\u25CF",
  amber: "\u25B2",
  red: "\u25A0",
  blue: "\u25C6",
  gray: "\u25CB",
};

/** Renders a <span> status badge and returns it. Never encodes status
 * with color alone — icon + text are always present. */
export function renderStatusBadge(value, labelOverride) {
  const { tone, label } = getStatusPresentation(value);
  const span = document.createElement("span");
  span.className = `status-badge status-badge--${tone}`;
  span.setAttribute("role", "status");
  span.innerHTML = `<span aria-hidden="true" class="status-badge__icon">${TONE_ICON[tone]}</span>${labelOverride ?? label}`;
  return span;
}
