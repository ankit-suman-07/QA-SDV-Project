/** Section 15 freshness utility. Uses sourceTimestamp, not request
 * completion time (section 5). Invalid dates degrade gracefully. */
export function getFreshness(sourceTimestamp, staleAfterMs, now = Date.now()) {
  if (!sourceTimestamp) return { state: "unknown", ageMs: null };

  const parsed = Date.parse(sourceTimestamp);
  if (Number.isNaN(parsed)) return { state: "unknown", ageMs: null };

  const ageMs = now - parsed;
  return { state: ageMs > staleAfterMs ? "stale" : "fresh", ageMs };
}

/** Human-friendly relative label; ISO value should be kept in a title
 * attribute wherever this is displayed. */
export function formatRelativeAge(ageMs) {
  if (ageMs === null || ageMs === undefined) return "Timestamp unavailable";
  if (ageMs < 1000) return "just now";
  const seconds = Math.round(ageMs / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  return `${minutes}m ago`;
}
