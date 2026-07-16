import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  Radar,
  Play,
  Square,
  Loader2,
  ShieldAlert,
  Radio,
} from "lucide-react";
import { api } from "../api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { toast } from "sonner";
import MtrHops from "../components/MtrHops";

export default function MtrTool() {
  const [host, setHost] = useState("");
  const [activeHost, setActiveHost] = useState("");
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

  const poll = useCallback((h) => {
    const target = h || activeHost;
    if (!target) return;
    api.liveMtrTool(target).then((s) => {
      applyState(s);
      if (!s.running && pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    }).catch(() => {});
  }, [activeHost]);

  const startPolling = useCallback((h) => {
    if (pollRef.current) clearInterval(pollRef.current);
    poll(h);
    pollRef.current = setInterval(() => poll(h), 500);
  }, [poll]);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const start = async () => {
    const h = host.trim();
    if (!h) {
      toast.error("Enter a host or IP");
      return;
    }
    // stop any previous session on a different host
    if (activeHost && activeHost !== h) {
      try { await api.stopMtrTool(activeHost); } catch (e) {}
    }
    setStarting(true);
    setHops([]);
    setNotAvailable(false);
    try {
      const s = await api.startMtrTool(h);
      setActiveHost(h);
      applyState(s);
      startPolling(h);
      toast.success(`Tracing ${h}`, { description: "Pinging every 0.25s" });
    } catch (e) {
      if (e?.response?.status === 503) {
        setNotAvailable(true);
        setActiveHost(h);
        toast.error("MTR unavailable here", {
          description: e.response.data?.detail || "Requires elevated privileges.",
        });
      } else if (e?.response?.status === 400) {
        toast.error("Host is required");
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
      if (activeHost) await api.stopMtrTool(activeHost);
    } catch (e) {}
    toast.info("MTR stopped");
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !running) start();
  };

  const totalDrop = hops.reduce((a, h) => a + ((h.sent || 0) - (h.recv || 0)), 0);
  const worstLoss = hops.reduce((a, h) => Math.max(a, h.loss || 0), 0);

  return (
    <div className="mx-auto max-w-[1100px] p-4 lg:p-6">
      <div className="mb-6">
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
          <Radar className="h-6 w-6 text-purple-400" /> MTR Tool
        </h1>
        <p className="text-sm text-muted-foreground">
          Run a live, continuous traceroute to any host or IP — no need to add it
          as a monitored target.
        </p>
      </div>

      <div className="glass mb-5 rounded-2xl p-4">
        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <Radio className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={host}
              onChange={(e) => setHost(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="e.g. 8.8.8.8, 1.1.1.1, or example.com"
              disabled={running}
              className="mono bg-background/50 pl-9"
            />
          </div>
          {running ? (
            <Button onClick={stop} variant="outline"
              className="border-red-500/40 bg-red-500/10 text-red-300 hover:bg-red-500/20 hover:text-red-200">
              <Square className="mr-1.5 h-4 w-4 fill-current" /> Stop
            </Button>
          ) : (
            <Button onClick={start} disabled={starting}
              className="bg-gradient-to-r from-cyan-400 to-purple-500 font-semibold text-slate-950 hover:opacity-90">
              {starting ? (
                <><Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> Starting…</>
              ) : (
                <><Play className="mr-1.5 h-4 w-4 fill-current" /> Run MTR</>
              )}
            </Button>
          )}
        </div>

        {running && (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="flex items-center gap-1.5 rounded-full border border-cyan-400/20 bg-cyan-400/5 px-2.5 py-1 text-[11px] font-medium text-cyan-300">
              <span className="live-dot h-1.5 w-1.5 rounded-full bg-cyan-400" />
              Live · {activeHost} · {cycles} cycles · {elapsed}s · {hops.length} hops
            </span>
            {worstLoss > 0 && (
              <span className="mono rounded-full bg-red-500/10 px-2 py-1 text-[11px] text-red-300">
                {totalDrop} dropped · worst {worstLoss}%
              </span>
            )}
          </div>
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
        <div className="glass flex flex-col items-center justify-center rounded-2xl py-16 text-center">
          <Radar className="mb-3 h-8 w-8 text-muted-foreground" />
          <div className="max-w-md text-sm text-muted-foreground">
            Type a host or IP above and hit <span className="text-foreground">Run MTR</span>.
            Each hop streams a live latency graph (0.25s pings) with a packet-loss
            timeline and full stats. Press Stop when done.
          </div>
        </div>
      ) : null}
    </div>
  );
}
