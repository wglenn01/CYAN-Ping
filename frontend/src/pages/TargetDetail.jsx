import React, { useMemo, useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Pencil,
  Trash2,
  RefreshCw,
  Server,
  Timer,
  Radio,
  Activity,
} from "lucide-react";
import { api } from "../api";
import { lossColor, TIME_RANGES } from "../constants";
import { fmtMs, statusMeta, fmtInterval } from "../lib/utils-sp";
import SmokeGraph, { LossLegend } from "../components/SmokeGraph";
import TargetFormModal from "../components/TargetFormModal";
import { Button } from "../components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../components/ui/alert-dialog";
import { toast } from "sonner";

function StatPill({ label, value, color }) {
  return (
    <div className="glass rounded-xl px-4 py-3">
      <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="mono mt-1 text-lg font-bold" style={{ color: color || "#e5e7eb" }}>
        {value}
      </div>
    </div>
  );
}

export default function TargetDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [range, setRange] = useState("30h");
  const [editOpen, setEditOpen] = useState(false);
  const [delOpen, setDelOpen] = useState(false);
  const [target, setTarget] = useState(null);
  const [series, setSeries] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  const loadTarget = useCallback(() => {
    api.target(id).then(setTarget).catch(() => setNotFound(true));
  }, [id]);

  const loadSeries = useCallback(() => {
    api.series(id, range)
      .then((d) => {
        setSeries(d.points);
        setStats(d.stats);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [id, range]);

  useEffect(() => {
    setLoading(true);
    loadTarget();
    loadSeries();
  }, [loadTarget, loadSeries]);

  useEffect(() => {
    const iv = setInterval(() => {
      loadTarget();
      loadSeries();
    }, 10000);
    return () => clearInterval(iv);
  }, [loadTarget, loadSeries]);

  if (notFound) {
    return (
      <div className="flex h-full flex-col items-center justify-center text-center">
        <Activity className="mb-3 h-8 w-8 text-muted-foreground" />
        <div className="font-medium">Target not found</div>
        <Button variant="ghost" className="mt-3" onClick={() => navigate("/")}>
          Back to dashboard
        </Button>
      </div>
    );
  }

  const meta = statusMeta[target?.status] || statusMeta.up;
  const s = stats || { current: 0, currentLoss: 0, avg: 0, min: 0, max: 0, avgLoss: 0 };

  return (
    <div className="mx-auto max-w-[1400px] p-4 lg:p-6">
      <button
        onClick={() => navigate("/")}
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> Dashboard
      </button>

      <div className="mb-6 flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
        <div>
          <div className="flex items-center gap-3">
            <span
              className="h-3 w-3 rounded-full"
              style={{ background: meta.color, boxShadow: `0 0 12px ${meta.color}` }}
            />
            <h1 className="text-2xl font-bold tracking-tight">{target?.name || "…"}</h1>
            <span
              className="rounded-full px-2.5 py-0.5 text-xs font-semibold"
              style={{ background: `${meta.color}1a`, color: meta.color }}
            >
              {meta.label}
            </span>
          </div>
          {target && (
            <div className="mono mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <Server className="h-3.5 w-3.5" /> {target.host}
              </span>
              <span className="flex items-center gap-1.5">
                <Radio className="h-3.5 w-3.5 text-purple-400" /> {target.probe}
              </span>
              <span className="flex items-center gap-1.5">
                <Timer className="h-3.5 w-3.5" /> every {fmtInterval(target.interval)}
              </span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => { loadSeries(); loadTarget(); toast.success("Refreshed"); }} className="border-border/60 bg-card/50">
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" /> Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={() => setEditOpen(true)} className="border-border/60 bg-card/50">
            <Pencil className="mr-1.5 h-3.5 w-3.5" /> Edit
          </Button>
          <Button variant="outline" size="sm" onClick={() => setDelOpen(true)} className="border-red-500/30 bg-red-500/5 text-red-300 hover:bg-red-500/10 hover:text-red-200">
            <Trash2 className="mr-1.5 h-3.5 w-3.5" /> Delete
          </Button>
        </div>
      </div>

      <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
        <StatPill label="Current" value={fmtMs(s.current)} color="#22d3ee" />
        <StatPill label="Loss" value={`${s.currentLoss}%`} color={lossColor(s.currentLoss)} />
        <StatPill label="Avg" value={fmtMs(s.avg)} />
        <StatPill label="Min" value={fmtMs(s.min)} color="#4ade80" />
        <StatPill label="Max" value={fmtMs(s.max)} color="#fb923c" />
        <StatPill label="Jitter" value={fmtMs(s.jitter)} color="#38bdf8" />
        <StatPill label="Avg Loss" value={`${s.avgLoss}%`} color="#a855f7" />
      </div>

      <div className="glass rounded-2xl p-4 lg:p-5">
        <div className="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <h2 className="text-sm font-semibold uppercase tracking-wider">
            Latency &amp; Loss
          </h2>
          <div className="flex flex-wrap gap-1 rounded-lg border border-border/60 bg-background/40 p-1">
            {TIME_RANGES.map((r) => (
              <button
                key={r.key}
                onClick={() => setRange(r.key)}
                className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                  range === r.key
                    ? "bg-cyan-400/15 text-cyan-300"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {r.key}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="flex h-[340px] items-center justify-center text-sm text-muted-foreground">
            Loading measurements…
          </div>
        ) : series.length === 0 ? (
          <div className="flex h-[340px] flex-col items-center justify-center text-center text-sm text-muted-foreground">
            <Activity className="mb-2 h-6 w-6" />
            No data yet — measurements are being collected. Check back shortly.
          </div>
        ) : (
          <SmokeGraph data={series} rangeKey={range} height={340} />
        )}

        <div className="mt-4 border-t border-border/60 pt-3">
          <LossLegend />
        </div>
      </div>

      {target && (
        <TargetFormModal
          open={editOpen}
          onOpenChange={setEditOpen}
          target={target}
          onSaved={() => { loadTarget(); loadSeries(); }}
        />
      )}

      <AlertDialog open={delOpen} onOpenChange={setDelOpen}>
        <AlertDialogContent className="glass border-border/60">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete “{target?.name}”?</AlertDialogTitle>
            <AlertDialogDescription>
              This removes the target and all of its measurement history. This
              action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={async () => {
                try {
                  await api.deleteTarget(target.id);
                  toast.success(`Target "${target.name}" deleted`);
                  navigate("/");
                } catch (e) {
                  toast.error("Could not delete target");
                }
              }}
              className="bg-red-500 text-white hover:bg-red-600"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
