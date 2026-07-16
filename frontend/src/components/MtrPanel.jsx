import React, { useState, useEffect, useCallback, useRef } from "react";
import { Route, Play, Square, Loader2, ShieldAlert } from "lucide-react";
import { api } from "../api";
import { Button } from "./ui/button";
import { toast } from "sonner";
import MtrHops from "./MtrHops";

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
        <MtrHops hops={hops} />
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
