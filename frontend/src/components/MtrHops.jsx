import React from "react";
import { Server } from "lucide-react";
import { lossColor } from "../constants";
import { fmtMs } from "../lib/utils-sp";

const WINDOW_MS = 30000; // show last 30 seconds
const MAX_POINTS = 120;

function windowPoints(series) {
  const pts = series || [];
  if (!pts.length) return [];
  const now = pts[pts.length - 1].t;
  const cutoff = now - WINDOW_MS;
  let win = pts.filter((p) => p.t >= cutoff);
  if (win.length > MAX_POINTS) {
    const stride = Math.ceil(win.length / MAX_POINTS);
    win = win.filter((_, i) => i % stride === 0);
  }
  return win;
}

const GRID_LINES = 4;   // horizontal reference lines
const PAD_PCT = 7.5;    // top/bottom padding inside the plot (matches SVG)

// Lightweight inline-SVG strip chart (no charting lib -> cheap, no hang).
// X axis is TIME-based over a fixed 30s window: newest sample sits at the right
// edge and older data scrolls off (and disappears at) the left edge.
function LightChart({ series, color }) {
  const pts = windowPoints(series);
  const W = 100, H = 40;
  const nums = pts.map((p) => p.v).filter((v) => v != null);
  const hasData = nums.length > 0;
  let min = hasData ? Math.min(...nums) : 0;
  let max = hasData ? Math.max(...nums) : 1;
  if (min === max) { min = Math.max(0, min - 1); max = max + 1; }
  const span = max - min || 1;
  const gid = `mtrfill-${color.replace("#", "")}`;

  // fixed 30s window anchored on the latest sample -> real scrolling
  const now = pts.length ? pts[pts.length - 1].t : 0;
  const t0 = now - WINDOW_MS;
  const xOf = (t) => Math.max(0, Math.min(W, ((t - t0) / WINDOW_MS) * W));
  const yOf = (v) => H - ((v - min) / span) * (H - 6) - 3;

  // split into continuous segments (breaks where packets were lost)
  const segments = [];
  let cur = [];
  for (const p of pts) {
    if (p.v == null) { if (cur.length) segments.push(cur); cur = []; continue; }
    cur.push({ x: xOf(p.t), y: yOf(p.v) });
  }
  if (cur.length) segments.push(cur);

  const lineD = segments
    .map((seg) => seg.map((pt, k) => `${k ? "L" : "M"}${pt.x.toFixed(2)} ${pt.y.toFixed(2)}`).join(" "))
    .join(" ");
  const areaD = segments
    .map((seg) => {
      const pts2 = seg.map((pt) => `${pt.x.toFixed(2)} ${pt.y.toFixed(2)}`).join(" L");
      return `M${seg[0].x.toFixed(2)} ${H} L${pts2} L${seg[seg.length - 1].x.toFixed(2)} ${H} Z`;
    })
    .join(" ");

  // evenly spaced background gridlines labelled with the latency at that height
  const grid = [];
  for (let k = 0; k < GRID_LINES; k++) {
    const frac = k / (GRID_LINES - 1);
    grid.push({
      top: PAD_PCT + frac * (100 - 2 * PAD_PCT),
      value: max - frac * (max - min),
    });
  }

  const leadX = segments.length ? segments[segments.length - 1].slice(-1)[0].x : W;

  return (
    <div className="relative h-16 w-full overflow-hidden rounded-md bg-black/20">
      {/* background gridlines + ms labels */}
      {hasData && grid.map((g, i) => (
        <div key={i} className="pointer-events-none absolute left-0 right-0 flex items-center"
          style={{ top: `${g.top}%` }}>
          <div className="h-px w-full bg-white/[0.06]" />
          <span className="mono absolute right-1 -translate-y-1/2 text-[8px] leading-none text-muted-foreground/60">
            {fmtMs(g.value)}
          </span>
        </div>
      ))}
      <svg width="100%" height="100%" viewBox={`0 0 ${W} ${H}`} className="absolute inset-0"
        preserveAspectRatio="none" style={{ display: "block" }}>
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.35" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        {areaD && <path d={areaD} fill={`url(#${gid})`} stroke="none" />}
        {lineD && (
          <path d={lineD} fill="none" stroke={color} strokeWidth="1.5"
            vectorEffect="non-scaling-stroke" strokeLinejoin="round"
            strokeLinecap="round" />
        )}
      </svg>
      {/* leading-edge "now" marker that rides the newest sample */}
      {hasData && (
        <div className="pointer-events-none absolute inset-y-0" style={{ left: `${leadX}%` }}>
          <div className="h-full w-px bg-cyan-300/50" style={{ boxShadow: "0 0 6px rgba(34,211,238,0.5)" }} />
          <div className="absolute left-1/2 top-0 -translate-x-1/2 border-x-[4px] border-t-[6px] border-x-transparent border-t-cyan-300" />
        </div>
      )}
    </div>
  );
}

function LossTimeline({ series }) {
  const win = windowPoints(series);
  const CELLS = 60;
  const cells = [];
  if (win.length) {
    const per = win.length / CELLS;
    for (let c = 0; c < CELLS; c++) {
      const start = Math.floor(c * per);
      const end = Math.max(start + 1, Math.floor((c + 1) * per));
      const slice = win.slice(start, end);
      const anyFull = slice.some((p) => p.loss >= 100 || p.v == null);
      const anyPart = slice.some((p) => p.loss > 0 && p.loss < 100);
      cells.push(anyFull ? "#ef4444" : anyPart ? "#fb923c" : "#22d3ee55");
    }
  }
  return (
    <div className="mt-1.5 flex h-1.5 w-full overflow-hidden rounded-sm">
      {cells.length
        ? cells.map((c, i) => <div key={i} className="flex-1" style={{ background: c }} />)
        : <div className="w-full bg-white/5" />}
    </div>
  );
}

function Stat({ label, value, color }) {
  return (
    <div className="min-w-0 rounded-lg bg-white/[0.03] px-2 py-1.5 text-center" data-testid={`mtr-stat-${label.toLowerCase().replace(/[^a-z]/g, "")}`}>
      <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">{label}</div>
      <div className="mono truncate text-sm font-semibold" style={{ color: color || undefined }}>{value}</div>
    </div>
  );
}

const LiveHopRow = React.memo(function LiveHopRow({ hop }) {
  const isUnknown = !hop.host || hop.host === "???";
  const color = lossColor(hop.loss || 0);
  return (
    <div className="rounded-xl border border-border/50 bg-white/[0.02] p-3">
      <div className="flex items-center gap-3">
        <div className="mono flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-white/5 text-[11px] text-muted-foreground">
          {hop.hop}
        </div>
        <div className="flex min-w-0 flex-1 items-center gap-1.5">
          <Server className="h-3 w-3 shrink-0 text-muted-foreground/50" />
          <span className={`mono truncate text-sm ${isUnknown ? "text-muted-foreground/50" : "text-foreground"}`}>
            {isUnknown ? "* * * (no reply)" : hop.host}
          </span>
        </div>
        <div className="mono shrink-0 text-right leading-tight">
          <div className="text-base font-semibold text-cyan-300">{hop.avg != null ? fmtMs(hop.avg) : "—"}</div>
          <div className="text-[9px] uppercase tracking-wider text-muted-foreground/70">avg</div>
        </div>
        <div className="mono w-16 shrink-0 rounded-md px-2 py-1 text-right text-xs font-semibold"
          style={{ background: `${color}1a`, color }}>
          {(hop.loss ?? 0).toFixed(1)}%
        </div>
      </div>

      <div className="mt-2">
        <LightChart series={hop.series || []} color={color} />
        <LossTimeline series={hop.series || []} />
      </div>

      <div className="mt-2 grid grid-cols-3 gap-1.5 border-t border-border/40 pt-2 sm:grid-cols-6">
        <Stat label="Loss%" value={`${(hop.loss ?? 0).toFixed(1)}%`} color={color} />
        <Stat label="Snt" value={hop.sent ?? 0} />
        <Stat label="Avg" value={hop.avg != null ? fmtMs(hop.avg) : "—"} color="#22d3ee" />
        <Stat label="Best" value={hop.best != null ? fmtMs(hop.best) : "—"} color="#4ade80" />
        <Stat label="Wrst" value={hop.worst != null ? fmtMs(hop.worst) : "—"} color="#fb923c" />
        <Stat label="StDev" value={hop.stdev != null ? fmtMs(hop.stdev) : "—"} color="#a78bfa" />
      </div>
    </div>
  );
});

export default function MtrHops({ hops }) {
  return (
    <div className="space-y-2">
      {hops.map((h, i) => <LiveHopRow key={`${h.hop}-${i}`} hop={h} />)}
    </div>
  );
}
