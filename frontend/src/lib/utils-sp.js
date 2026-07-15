export function formatTime(ts, rangeKey) {
  const d = new Date(ts);
  if (rangeKey === "10d" || rangeKey === "360d") {
    return d.toLocaleDateString([], { month: "short", day: "numeric" });
  }
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function timeAgo(ts) {
  const diff = Math.floor((Date.now() - ts) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function fmtMs(v) {
  if (v == null) return "—";
  if (v < 1) return `${(v * 1000).toFixed(0)}µs`;
  if (v >= 1000) return `${(v / 1000).toFixed(2)}s`;
  return `${v.toFixed(1)}ms`;
}

export const statusMeta = {
  up: { label: "Up", color: "#22d3ee", dot: "bg-cyan-400" },
  warn: { label: "Degraded", color: "#facc15", dot: "bg-yellow-400" },
  down: { label: "Down", color: "#f87171", dot: "bg-red-400" },
};
