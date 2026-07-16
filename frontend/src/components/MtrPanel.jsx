import React, { useState, useEffect, useCallback, useRef } from "react";
import { ResponsiveContainer, AreaChart, Area, YAxis, Tooltip } from "recharts";
import {
  Route,
  Play,
  Square,
  Loader2,
  ShieldAlert,
  Server,
} from "lucide-react";
import { api } from "../api";
import { lossColor } from "../constants";
import { fmtMs } from "../lib/utils-sp";
import { Button } from "./ui/button";
import { toast } from "sonner";

const WINDOW_MS = 60000; // show last 60 seconds
const MAX_POINTS = 150;  // cap rendered points for smooth performance

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

function buildWindow(series) {
  return windowPoints(series).map((p, i) => ({ i, v: p.v, loss: p.loss }));
}

const LossDot = (props) => {
  const { cx, cy, payload } = props;
  if (cx == null || cy == null || !payload || !payload.loss) return null;
  return <circle cx={cx} cy={cy} r={2.5} fill="#f87171" stroke="#0a0a0f" strokeWidth={0.5} />;
};

function StripChart({ series, color }) {
  const data = buildWindow(series);
  const gid = `mtr-${color.replace("#", "")}`;
  return (
    <div className="relative h-16 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 6, right: 0, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.5} />
              <stop offset="100%" stopColor={color} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <YAxis hide domain={["dataMin", "dataMax"]} />
          <Tooltip
            cursor={false}
            contentStyle={{
              background: "rgba(20,20,31,0.9)", border: "1px solid #333",
              borderRadius: 8, fontSize: 11, padding: "4px 8px",
            }}
            labelFormatter={() => ""}
            formatter={(val, name, p) => [
              `${fmtMs(val)}${p.payload.loss ? ` · loss ${p.payload.loss}%` : ""}`,
              "rtt",
            ]}
          />
          <Area
            type="monotone" dataKey="v" stroke={color} strokeWidth={1.75}
            fill={`url(#${gid})`} isAnimationActive={false}
            connectNulls={false} dot={<LossDot />} activeDot={{ r: 3, fill: color }}
          />
        </AreaChart>
      </ResponsiveContainer>
      {/* fixed center pointer — waveform scrolls behind it */}
      <div className="pointer-events-none absolute inset-y-0 left-1/2 -translate-x-1/2">
        <div className="absolute left-1/2 top-0 -translate-x-1/2 border-x-[4px] border-t-[6px] border-x-transparent border-t-cyan-300" />
        <div className="h-full w-px bg-cyan-300/40" style={{ boxShadow: "0 0 6px rgba(34,211,238,0.5)" }} />
      </div>
    </div>
  );
}

function LossTimeline({ series }) {
  const win = windowPoints(series);
  const CELLS = 80;
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
        ? cells.map((c, i) => (
            <div key={i} className="flex-1" style={{ background: c }} />
          ))
        : <div className="w-full bg-white/5" />}
    </div>
  );
}

function Stat({ label, value, color }) {
  return (
    <div className="min-w-0">
      <div className="text-[9px] uppercase tracking-wider text-muted-foreground/70">{label}</div>
      <div className="mono truncate text-xs font-medium" style={{ color: color || undefined }}>{value}</div>
    </div>
  );
}

function LiveHopRow({ hop }) {
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
        <div
          className="mono w-16 shrink-0 rounded-md px-2 py-1 text-right text-xs font-semibold"
          style={{ background: `${color}1a`, color }}
        >
          {(hop.loss ?? 0).toFixed(1)}%
        </div>
      </div>

      <div className="mt-2">
        <StripChart series={hop.series || []} color={color} />
        <LossTimeline series={hop.series || []} />
      </div>

      <div className="mt-2 grid grid-cols-4 gap-x-3 gap-y-1.5 border-t border-border/40 pt-2 sm:grid-cols-7">
        <Stat label="Last" value={hop.last != null ? fmtMs(hop.last) : "—"} />
        <Stat label="Best" value={hop.best != null ? fmtMs(hop.best) : "—"} color="#4ade80" />
        <Stat label="Wrst" value={hop.worst != null ? fmtMs(hop.worst) : "—"} color="#fb923c" />
        <Stat label="Jitter" value={hop.stdev != null ? fmtMs(hop.stdev) : "—"} color="#38bdf8" />
        <Stat label="Sent" value={hop.sent ?? 0} />
        <Stat label="Recv" value={hop.recv ?? 0} color="#4ade80" />
        <Stat label="Drop" value={(hop.sent || 0) - (hop.recv || 0)} color="#f87171" />
      </div>
    </div>
  );
}

export default function MtrPanel({ targetId }) {
  const [running, setRunning] = useState(false);
  const [hops, setHops] = useState([]);
  const [cycles, setCycles] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [starting, setStarting] = useState(false);
  const [notAvailable, setNotAvailable] = useState(false);
  const pollRef = useRef(null);

  const applyState = (s) => {
    setRunning(s.running);
    setHops(s.hops || []);
    setCycles(s.cycles || 0);
    setElapsed(s.elapsed || 0);
    if (s.available === false && !(s.hops && s.hops.length)) setNotAvailable(true);
  };

  const poll = useCallback(() => {
    api.liveMtr(targetId).then((s) => {
      applyState(s);
      if (!s.running && pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    }).catch(() => {});
  }, [targetId]);

  const startPolling = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    poll();
    pollRef.current = setInterval(poll, 350);
  }, [poll]);

  useEffect(() => {
    api.liveMtr(targetId).then((s) => {
      applyState(s);
      if (s.running) startPolling();
    }).catch(() => {});
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [targetId, startPolling]);

  const start = async () => {
    setStarting(true);
    try {
      const s = await api.startLiveMtr(targetId);
      setNotAvailable(false);
      applyState(s);
      startPolling();
      toast.success("Live MTR started", { description: "Pinging every 0.25s" });
    } catch (e) {
      if (e?.response?.status === 503) {
        setNotAvailable(true);
        toast.error("MTR unavailable here", {
          description: e.response.data?.detail || "Requires elevated privileges.",
        });
      } else {
        toast.error("Could not start MTR");
      }
    } finally {
      setStarting(false);
    }
  };

  const stop = async () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    setRunning(false);
    try {
      await api.stopLiveMtr(targetId);
    } catch (e) {}
    toast.info("Live MTR stopped");
  };

  const totalDrop = hops.reduce((a, h) => a + ((h.sent || 0) - (h.recv || 0)), 0);
  const worstLoss = hops.reduce((a, h) => Math.max(a, h.loss || 0), 0);

  return (
    <div>
      <div className="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-sm font-semibold uppercase tracking-wider">Route Analysis (MTR)</h2>
          {running && (
            <span className="flex items-center gap-1.5 rounded-full border border-cyan-400/20 bg-cyan-400/5 px-2.5 py-1 text-[11px] font-medium text-cyan-300">
              <span className="live-dot h-1.5 w-1.5 rounded-full bg-cyan-400" />
              Live · {cycles} cycles · {elapsed}s · {hops.length} hops
            </span>
          )}
          {running && worstLoss > 0 && (
            <span className="mono rounded-full bg-red-500/10 px-2 py-1 text-[11px] text-red-300">
              {totalDrop} dropped · worst {worstLoss}%
            </span>
          )}
        </div>
        {running ? (
          <Button onClick={stop} size="sm" variant="outline"
            className="border-red-500/40 bg-red-500/10 text-red-300 hover:bg-red-500/20 hover:text-red-200">
            <Square className="mr-1.5 h-3.5 w-3.5 fill-current" /> Stop
          </Button>
        ) : (
          <Button onClick={start} disabled={starting} size="sm"
            className="bg-gradient-to-r from-cyan-400 to-purple-500 font-semibold text-slate-950 hover:opacity-90">
            {starting ? (
              <><Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> Starting…</>
            ) : (
              <><Play className="mr-1.5 h-3.5 w-3.5 fill-current" /> Start Live MTR</>
            )}
          </Button>
        )}
      </div>

      {notAvailable && hops.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-amber-500/20 bg-amber-500/[0.06] py-10 text-center">
          <ShieldAlert className="mb-3 h-8 w-8 text-amber-400" />
          <div className="font-medium text-amber-200">MTR needs elevated privileges here</div>
          <p className="mt-1 max-w-md text-sm text-muted-foreground">
            Traceroute uses raw sockets, disabled in this cloud preview. It works
            fully on your self-hosted deployment (backend runs with
            <span className="mono"> NET_RAW</span> and the <span className="mono">mtr</span> binary).
          </p>
        </div>
      )}

      {hops.length > 0 ? (
        <div className="space-y-2">
          {hops.map((h, i) => <LiveHopRow key={`${h.hop}-${i}`} hop={h} />)}
        </div>
      ) : !notAvailable ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-border/50 py-12 text-center">
          <Route className="mb-3 h-8 w-8 text-muted-foreground" />
          <div className="max-w-md text-sm text-muted-foreground">
            Click “Start Live MTR” to continuously trace the path (0.25s pings).
            Each hop gets a live scrolling latency graph with a center pointer,
            a packet-loss timeline, and full stats — press Stop when done.
          </div>
        </div>
      ) : null}
    </div>
  );
}
