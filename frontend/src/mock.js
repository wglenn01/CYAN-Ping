// Mock data for SmokePing clone. This will be replaced by real backend API later.

// Loss color bands (classic SmokePing style, adapted to brand)
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

// Time range definitions
export const TIME_RANGES = [
  { key: "3h", label: "Last 3 Hours", seconds: 3 * 3600, points: 108 },
  { key: "30h", label: "Last 30 Hours", seconds: 30 * 3600, points: 180 },
  { key: "10d", label: "Last 10 Days", seconds: 10 * 86400, points: 240 },
  { key: "360d", label: "Last 360 Days", seconds: 360 * 86400, points: 360 },
];

// Deterministic pseudo-random for stable graphs
function seeded(seed) {
  let s = seed % 2147483647;
  if (s <= 0) s += 2147483646;
  return () => (s = (s * 16807) % 2147483647) / 2147483647;
}

// Generate a smoke time-series for a target
export function generateSeries(target, rangeKey) {
  const range = TIME_RANGES.find((r) => r.key === rangeKey) || TIME_RANGES[0];
  const rnd = seeded(
    target.baseLatency * 1000 + range.points + target.name.length * 37
  );
  const now = Date.now();
  const step = (range.seconds * 1000) / range.points;
  const data = [];
  let jitterBase = target.jitter;
  for (let i = 0; i < range.points; i++) {
    const t = now - (range.points - i) * step;
    // occasional spikes
    const spike = rnd() > 0.94 ? rnd() * target.baseLatency * 2.5 : 0;
    const wobble = Math.sin(i / 9) * target.jitter * 0.6;
    const median = Math.max(
      0.5,
      target.baseLatency + wobble + (rnd() - 0.5) * jitterBase + spike
    );
    const spread = jitterBase * (0.4 + rnd());
    const min = Math.max(0.2, median - spread * (0.5 + rnd()));
    const max = median + spread * (0.6 + rnd());
    // packet loss: mostly 0, occasional loss depending on target reliability
    let loss = 0;
    const lossRoll = rnd();
    if (lossRoll > target.reliability) {
      loss = Math.round((lossRoll - target.reliability) * 300);
      loss = Math.min(100, loss);
    }
    data.push({
      time: t,
      median: +median.toFixed(2),
      min: +min.toFixed(2),
      max: +max.toFixed(2),
      // area band offsets for stacked rendering
      band: +(max - min).toFixed(2),
      loss,
    });
  }
  return data;
}

export function computeStats(series) {
  const medians = series.map((d) => d.median);
  const losses = series.map((d) => d.loss);
  const avg = medians.reduce((a, b) => a + b, 0) / medians.length;
  const max = Math.max(...medians);
  const min = Math.min(...medians);
  const avgLoss = losses.reduce((a, b) => a + b, 0) / losses.length;
  const last = series[series.length - 1];
  return {
    avg: +avg.toFixed(2),
    max: +max.toFixed(2),
    min: +min.toFixed(2),
    avgLoss: +avgLoss.toFixed(1),
    current: last.median,
    currentLoss: last.loss,
  };
}

// Target tree — groups and targets
export const mockTree = [
  {
    id: "grp-core",
    type: "group",
    name: "Core Network",
    children: [
      {
        id: "tgt-gw",
        type: "target",
        name: "Edge Gateway",
        host: "10.0.0.1",
        probe: "ICMP",
        interval: 60,
        baseLatency: 1.8,
        jitter: 0.6,
        reliability: 0.995,
        status: "up",
      },
      {
        id: "tgt-core-sw",
        type: "target",
        name: "Core Switch",
        host: "10.0.0.2",
        probe: "ICMP",
        interval: 60,
        baseLatency: 0.9,
        jitter: 0.3,
        reliability: 0.999,
        status: "up",
      },
    ],
  },
  {
    id: "grp-internet",
    type: "group",
    name: "Internet Uplinks",
    children: [
      {
        id: "tgt-google",
        type: "target",
        name: "Google DNS",
        host: "8.8.8.8",
        probe: "ICMP",
        interval: 60,
        baseLatency: 12.4,
        jitter: 3.2,
        reliability: 0.99,
        status: "up",
      },
      {
        id: "tgt-cf",
        type: "target",
        name: "Cloudflare DNS",
        host: "1.1.1.1",
        probe: "ICMP",
        interval: 60,
        baseLatency: 9.7,
        jitter: 2.1,
        reliability: 0.995,
        status: "up",
      },
      {
        id: "tgt-uplink",
        type: "target",
        name: "ISP Uplink",
        host: "203.0.113.1",
        probe: "ICMP",
        interval: 120,
        baseLatency: 24.6,
        jitter: 8.5,
        reliability: 0.94,
        status: "warn",
      },
    ],
  },
  {
    id: "grp-services",
    type: "group",
    name: "Web Services",
    children: [
      {
        id: "tgt-api",
        type: "target",
        name: "Public API",
        host: "https://api.cyanwireless.net/health",
        probe: "HTTP",
        interval: 120,
        baseLatency: 84.0,
        jitter: 22.0,
        reliability: 0.97,
        status: "up",
      },
      {
        id: "tgt-portal",
        type: "target",
        name: "Customer Portal",
        host: "https://portal.cyanwireless.net",
        probe: "HTTP",
        interval: 120,
        baseLatency: 142.0,
        jitter: 38.0,
        reliability: 0.9,
        status: "down",
      },
      {
        id: "tgt-dns",
        type: "target",
        name: "Authoritative DNS",
        host: "ns1.cyanwireless.net",
        probe: "DNS",
        interval: 300,
        baseLatency: 18.2,
        jitter: 5.0,
        reliability: 0.98,
        status: "up",
      },
    ],
  },
  {
    id: "grp-remote",
    type: "group",
    name: "Remote Sites",
    children: [
      {
        id: "tgt-site-a",
        type: "target",
        name: "Site A - Datacenter",
        host: "172.16.10.1",
        probe: "ICMP",
        interval: 60,
        baseLatency: 34.5,
        jitter: 6.0,
        reliability: 0.97,
        status: "up",
      },
      {
        id: "tgt-site-b",
        type: "target",
        name: "Site B - Warehouse",
        host: "172.16.20.1",
        probe: "TCP",
        interval: 60,
        baseLatency: 58.0,
        jitter: 14.0,
        reliability: 0.92,
        status: "warn",
      },
    ],
  },
];

export function flattenTargets(tree) {
  const out = [];
  tree.forEach((grp) => {
    (grp.children || []).forEach((t) =>
      out.push({ ...t, groupName: grp.name, groupId: grp.id })
    );
  });
  return out;
}

export const mockAlerts = [
  {
    id: "al-1",
    target: "Customer Portal",
    targetId: "tgt-portal",
    rule: "loss > 50%",
    severity: "critical",
    status: "active",
    message: "Host unreachable — 100% packet loss for 6 minutes",
    since: Date.now() - 6 * 60 * 1000,
  },
  {
    id: "al-2",
    target: "ISP Uplink",
    targetId: "tgt-uplink",
    rule: "latency > 40ms",
    severity: "warning",
    status: "active",
    message: "Median latency 46.2ms exceeds threshold (40ms)",
    since: Date.now() - 22 * 60 * 1000,
  },
  {
    id: "al-3",
    target: "Site B - Warehouse",
    targetId: "tgt-site-b",
    rule: "loss > 15%",
    severity: "warning",
    status: "active",
    message: "Intermittent loss detected (18%)",
    since: Date.now() - 48 * 60 * 1000,
  },
  {
    id: "al-4",
    target: "Public API",
    targetId: "tgt-api",
    rule: "latency > 200ms",
    severity: "warning",
    status: "resolved",
    message: "Latency recovered to 84ms",
    since: Date.now() - 3 * 3600 * 1000,
  },
];

export const mockAlertRules = [
  { id: "r1", name: "Host Down", condition: "loss", operator: ">", value: 50, severity: "critical", enabled: true },
  { id: "r2", name: "High Latency", condition: "latency", operator: ">", value: 40, severity: "warning", enabled: true },
  { id: "r3", name: "Packet Loss", condition: "loss", operator: ">", value: 15, severity: "warning", enabled: true },
  { id: "r4", name: "Slow API", condition: "latency", operator: ">", value: 200, severity: "warning", enabled: false },
];

export const PROBES = [
  { key: "ICMP", label: "ICMP Ping", desc: "Classic fping latency & loss", hint: "IP or hostname (e.g. 8.8.8.8)" },
  { key: "HTTP", label: "HTTP(S)", desc: "Web endpoint response time", hint: "URL (e.g. https://site.com)" },
  { key: "DNS", label: "DNS", desc: "DNS query resolution time", hint: "Hostname to resolve" },
  { key: "TCP", label: "TCP Port", desc: "TCP connect time to a port", hint: "host:port (e.g. host:443)" },
];

export const mockUser = { username: "admin", role: "Administrator" };
