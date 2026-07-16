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

// Lightweight inline-SVG strip chart (no charting lib -> cheap, no hang).
function LightChart({ series, color }) {
  const pts = windowPoints(series);
  const W = 100, H = 40;
  const nums = pts.map((p) => p.v).filter((v) => v != null);
  const min = nums.length ? Math.min(...nums) : 0;
  const max = nums.length ? Math.max(...nums) : 1;
  const span = max - min || 1;
  const n = pts.length;
  const gid = `mtrfill-${color.replace("#", "")}`;

  // split into continuous segments (breaks where packets were lost)
  const segments = [];
  let cur = [];
  for (let i = 0; i < n; i++) {
    const p = pts[i];
    if (p.v == null) { if (cur.length) segments.push(cur); cur = []; continue; }
    const x = n > 1 ? (i / (n - 1)) * W : W / 2;
    const y = H - ((p.v - min) / span) * (H - 6) - 3;
    cur.push({ x, y });
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

  return (
    <div className="relative h-14 w-full">
      <svg width="100%" height="100%" viewBox={`0 0 ${W} ${H}`}
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
      <div className="pointer-events-none absolute inset-y-0 left-1/2 -translate-x-1/2">
        <div className="absolute left-1/2 top-0 -translate-x-1/2 border-x-[4px] border-t-[6px] border-x-transparent border-t-cyan-300" />
        <div className="h-full w-px bg-cyan-300/40" style={{ boxShadow: "0 0 6px rgba(34,211,238,0.5)" }} />
      </div>
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
