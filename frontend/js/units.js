/** Section 5: temperature/pressure — one decimal max in cards. */
export function formatOneDecimal(value) {
  if (value === undefined || value === null || Number.isNaN(value))
    return "\u2014";
  return value.toFixed(1);
}

/** Section 9: latency — one decimal in cards, up to three in tables. */
export function formatLatencyCard(ms) {
  return `${ms.toFixed(1)} ms`;
}
export function formatLatencyTable(ms) {
  return `${ms.toFixed(3)} ms`;
}

/** Section 9: throughput — two decimals in cards, three in tables. */
export function formatThroughputCard(msgPerSec) {
  return `${msgPerSec.toFixed(2)} msg/s`;
}
export function formatThroughputTable(msgPerSec) {
  return `${msgPerSec.toFixed(3)} msg/s`;
}

/** Section 9: success rate — bare 100%; two decimals only when below. */
export function formatSuccessRate(percent) {
  if (percent >= 100) return "100%";
  return `${percent.toFixed(2)}%`;
}
