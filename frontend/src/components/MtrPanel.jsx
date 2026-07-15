import React, { useState, useEffect, useCallback } from "react";
import {
  Route,
  Play,
  Loader2,
  ShieldAlert,
  RefreshCw,
  Server,
} from "lucide-react";
import { api } from "../api";
import { lossColor } from "../constants";
import { fmtMs, timeAgo } from "../lib/utils-sp";
import { Button } from "./ui/button";
import { toast } from "sonner";

function HopRow({ hop, maxAvg }) {
  const isUnknown = !hop.host || hop.host === "???";
  const barW = maxAvg > 0 && hop.avg ? Math.max(4, (hop.avg / maxAvg) * 100) : 0;
  return (
    <tr className="border-b border-border/40 transition-colors hover:bg-white/[0.03]">
      <td className="py-2 pl-3 pr-2 text-right text-muted-foreground">{hop.hop}</td>
      <td className="max-w-[220px] py-2 pr-2">
        <div className="flex items-center gap-1.5">
          <Server className="h-3 w-3 shrink-0 text-muted-foreground/60" />
          <span className={`truncate ${isUnknown ? "text-muted-foreground/50" : "text-foreground"}`}>
            {isUnknown ? "* * *" : hop.host}
          </span>
        </div>
      </td>
      <td className="py-2 pr-2 text-right">
        <span style={{ color: lossColor(hop.loss || 0) }}>{(hop.loss ?? 0).toFixed(1)}%</span>
      </td>
      <td className="hidden py-2 pr-2 text-right text-muted-foreground sm:table-cell">{hop.sent ?? "—"}</td>
      <td className="hidden py-2 pr-2 text-right text-foreground/80 md:table-cell">{hop.last != null ? fmtMs(hop.last) : "—"}</td>
      <td className="py-2 pr-2 text-right">
        <div className="flex items-center justify-end gap-2">
          <div className="hidden h-1.5 w-16 overflow-hidden rounded-full bg-white/5 lg:block">
            <div className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-purple-500" style={{ width: `${barW}%` }} />
          </div>
          <span className="text-cyan-300">{hop.avg != null ? fmtMs(hop.avg) : "—"}</span>
        </div>
      </td>
      <td className="hidden py-2 pr-2 text-right text-emerald-300/80 md:table-cell">{hop.best != null ? fmtMs(hop.best) : "—"}</td>
      <td className="hidden py-2 pr-2 text-right text-orange-300/80 md:table-cell">{hop.worst != null ? fmtMs(hop.worst) : "—"}</td>
      <td className="py-2 pl-2 pr-3 text-right text-sky-300/80">{hop.stdev != null ? fmtMs(hop.stdev) : "—"}</td>
    </tr>
  );
}

export default function MtrPanel({ targetId }) {
  const [available, setAvailable] = useState(true);
  const [latest, setLatest] = useState(null);
  const [running, setRunning] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    api.getMtr(targetId)
      .then((d) => {
        setAvailable(d.available);
        setLatest(d.latest);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [targetId]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  const run = async () => {
    setRunning(true);
    try {
      const res = await api.runMtr(targetId);
      setLatest(res);
      setAvailable(true);
      toast.success("MTR complete", { description: `${res.hops.length} hops traced` });
    } catch (e) {
      if (e?.response?.status === 503) {
        setAvailable(false);
        toast.error("MTR unavailable here", {
          description: e.response.data?.detail || "Requires elevated privileges.",
        });
      } else {
        toast.error("MTR failed", { description: "Please try again." });
      }
    } finally {
      setRunning(false);
    }
  };

  const hops = latest?.hops || [];
  const maxAvg = hops.reduce((m, h) => Math.max(m, h.avg || 0), 0);

  return (
    <div>
      <div className="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold uppercase tracking-wider">
            Route Analysis (MTR)
          </h2>
          {latest && (
            <span className="text-xs text-muted-foreground">
              · {latest.source === "scheduled" ? "auto" : "manual"} · {timeAgo(latest.timestamp)}
            </span>
          )}
        </div>
        <Button
          onClick={run}
          disabled={running}
          size="sm"
          className="bg-gradient-to-r from-cyan-400 to-purple-500 font-semibold text-slate-950 hover:opacity-90"
        >
          {running ? (
            <><Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> Tracing…</>
          ) : latest ? (
            <><RefreshCw className="mr-1.5 h-3.5 w-3.5" /> Run MTR</>
          ) : (
            <><Play className="mr-1.5 h-3.5 w-3.5" /> Run MTR</>
          )}
        </Button>
      </div>

      {!available && !latest && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-amber-500/20 bg-amber-500/[0.06] py-10 text-center">
          <ShieldAlert className="mb-3 h-8 w-8 text-amber-400" />
          <div className="font-medium text-amber-200">MTR needs elevated privileges here</div>
          <p className="mt-1 max-w-md text-sm text-muted-foreground">
            Traceroute uses raw sockets, which are disabled in this cloud preview.
            It works fully on your self-hosted deployment (the backend runs with
            <span className="mono"> NET_RAW</span> and the <span className="mono">mtr</span> binary).
          </p>
        </div>
      )}

      {loading ? (
        <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">
          Loading route…
        </div>
      ) : hops.length > 0 ? (
        <div className="overflow-x-auto rounded-xl border border-border/50">
          <table className="mono w-full text-xs">
            <thead>
              <tr className="border-b border-border/60 bg-white/[0.03] text-[10px] uppercase tracking-wider text-muted-foreground">
                <th className="py-2 pl-3 pr-2 text-right font-medium">#</th>
                <th className="py-2 pr-2 text-left font-medium">Host</th>
                <th className="py-2 pr-2 text-right font-medium">Loss</th>
                <th className="hidden py-2 pr-2 text-right font-medium sm:table-cell">Snt</th>
                <th className="hidden py-2 pr-2 text-right font-medium md:table-cell">Last</th>
                <th className="py-2 pr-2 text-right font-medium">Avg</th>
                <th className="hidden py-2 pr-2 text-right font-medium md:table-cell">Best</th>
                <th className="hidden py-2 pr-2 text-right font-medium md:table-cell">Wrst</th>
                <th className="py-2 pl-2 pr-3 text-right font-medium">StDev</th>
              </tr>
            </thead>
            <tbody>
              {hops.map((h, i) => (
                <HopRow key={`${h.hop}-${i}`} hop={h} maxAvg={maxAvg} />
              ))}
            </tbody>
          </table>
        </div>
      ) : available ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-border/50 py-10 text-center">
          <Route className="mb-3 h-8 w-8 text-muted-foreground" />
          <div className="text-sm text-muted-foreground">
            No trace yet — click “Run MTR” to analyze the network path.
          </div>
        </div>
      ) : null}
    </div>
  );
}
