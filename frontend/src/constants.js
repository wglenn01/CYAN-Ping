// Pure UI constants & helpers (no mock data)

export const LOSS_COLORS = [
  { max: 0, color: "#22d3ee", label: "0" },
  { max: 5, color: "#4ade80", label: "1/20" },
  { max: 15, color: "#a3e635", label: "2/20" },
  { max: 30, color: "#facc15", label: "3/20" },
  { max: 50, color: "#fb923c", label: "4/20" },
  { max: 80, color: "#f87171", label: "10/20" },
  { max: 100, color: "#a855f7", label: "19/20" },
];

export function lossColor(lossPct) {
  for (const band of LOSS_COLORS) {
    if (lossPct <= band.max) return band.color;
  }
  return "#a855f7";
}

export const TIME_RANGES = [
  { key: "3h", label: "Last 3 Hours", seconds: 3 * 3600 },
  { key: "30h", label: "Last 30 Hours", seconds: 30 * 3600 },
  { key: "10d", label: "Last 10 Days", seconds: 10 * 86400 },
  { key: "360d", label: "Last 360 Days", seconds: 360 * 86400 },
];

export const PROBES = [
  { key: "ICMP", label: "ICMP Ping", desc: "Classic fping latency & loss", hint: "IP or hostname (e.g. 8.8.8.8)" },
  { key: "HTTP", label: "HTTP(S)", desc: "Web endpoint response time", hint: "URL (e.g. https://site.com)" },
  { key: "DNS", label: "DNS", desc: "DNS query resolution time", hint: "Hostname to resolve" },
  { key: "TCP", label: "TCP Port", desc: "TCP connect time to a port", hint: "host:port (e.g. host:443)" },
];
