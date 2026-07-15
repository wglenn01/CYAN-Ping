import React, { useState, useEffect, useCallback, useRef } from "react";
import { ResponsiveContainer, AreaChart, Area, YAxis } from "recharts";
import {
  Route,
  Play,
  Square,
  Loader2,
  ShieldAlert,
  Server,
  Radio,
} from "lucide-react";
import { api } from "../api";
import { lossColor } from "../constants";
import { fmtMs } from "../lib/utils-sp";
import { Button } from "./ui/button";
import { toast } from "sonner";

function HopGraph({ series, color }) {
  const gid = `hop-${color.replace("#", "")}`;
  return (
    <ResponsiveContainer width="100%" height={40}>
      <AreaChart data={series} margin={{ top: 3, right: 0, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.45} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <YAxis hide domain={["dataMin", "dataMax"]} />
        <Area
          type="monotone"
          dataKey="v"
          stroke={color}
          strokeWidth={1.5}
          fill={`url(#${gid})`}
          isAnimationActive={false}
          connectNulls
        />
      </AreaChart>
    </ResponsiveContainer>
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
            {isUnknown ? "* * *" : hop.host}
          </span>
        </div>
        <div className="mono shrink-0 text-right">
          <span className="text-base font-semibold text-cyan-300">
            {hop.avg != null ? fmtMs(hop.avg) : "—"}
          </span>
        </div>
        <div className="mono w-14 shrink-0 text-right text-xs" style={{ color }}>
          {(hop.loss ?? 0).toFixed(1)}%
        </div>
      </div>

      <div className="mt-2">
        <HopGraph series={hop.series || []} color={color} />
      </div>

      <div className="mono mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-[10px] text-muted-foreground">
        <span>Snt <span className="text-foreground/70">{hop.sent}</span></span>
        <span>Last <span className="text-foreground/70">{hop.last != null ? fmtMs(hop.last) : "—"}</span></span>
        <span>Best <span className="text-emerald-300/80">{hop.best != null ? fmtMs(hop.best) : "—"}</span></span>
        <span>Wrst <span className="text-orange-300/80">{hop.worst != null ? fmtMs(hop.worst) : "—"}</span></span>
        <span>StDev <span className="text-sky-300/80">{hop.stdev != null ? fmtMs(hop.stdev) : "—"}</span></span>
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
    pollRef.current = setInterval(poll, 1000);
  }, [poll]);

  // On mount: reconnect to a running session if one exists
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

  return (
    <div>
      <div className="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold uppercase tracking-wider">
            Route Analysis (MTR)
          </h2>
          {running && (
            <span className="flex items-center gap-1.5 rounded-full border border-cyan-400/20 bg-cyan-400/5 px-2.5 py-1 text-[11px] font-medium text-cyan-300">
              <span className="live-dot h-1.5 w-1.5 rounded-full bg-cyan-400" />
              Live · {cycles} cycles · {elapsed}s
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
          {hops.map((h, i) => (
            <LiveHopRow key={`${h.hop}-${i}`} hop={h} />
          ))}
        </div>
      ) : !notAvailable ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-border/50 py-12 text-center">
          <Route className="mb-3 h-8 w-8 text-muted-foreground" />
          <div className="text-sm text-muted-foreground">
            Click “Start Live MTR” to continuously trace the path (0.25s pings).
            Each hop gets a live latency graph — press Stop when done.
          </div>
        </div>
      ) : null}
    </div>
  );
}
