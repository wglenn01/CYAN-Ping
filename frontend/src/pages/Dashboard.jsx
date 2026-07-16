import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { ResponsiveContainer, AreaChart, Area } from "recharts";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Gauge,
  Plus,
  Search,
  TrendingUp,
  Zap,
} from "lucide-react";
import { api } from "../api";
import { lossColor } from "../constants";
import { fmtMs, statusMeta } from "../lib/utils-sp";
import { Input } from "../components/ui/input";
import { Button } from "../components/ui/button";
import TargetFormModal from "../components/TargetFormModal";

function StatCard({ icon: Icon, label, value, sub, accent }) {
  return (
    <div className="glass fade-up rounded-2xl p-5">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            {label}
          </div>
          <div className="mono mt-2 text-3xl font-bold" style={{ color: accent }}>
            {value}
          </div>
          <div className="mt-1 text-xs text-muted-foreground">{sub}</div>
        </div>
        <div
          className="flex h-10 w-10 items-center justify-center rounded-xl"
          style={{ background: `${accent}1a` }}
        >
          <Icon className="h-5 w-5" style={{ color: accent }} />
        </div>
      </div>
    </div>
  );
}

function Sparkline({ data, color }) {
  const gid = `spark-${color.replace("#", "")}`;
  return (
    <ResponsiveContainer width="100%" height={44}>
      <AreaChart data={data} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.5} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey="median"
          stroke={color}
          strokeWidth={1.5}
          fill={`url(#${gid})`}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function TargetCard({ target, onClick }) {
  const [spark, setSpark] = useState([]);
  const [avg, setAvg] = useState(null);
  const meta = statusMeta[target.status] || statusMeta.up;

  useEffect(() => {
    let alive = true;
    const fetchSeries = () => {
      api.series(target.id, "3h").then((d) => {
        if (!alive) return;
        setSpark(d.points.slice(-40));
        setAvg(d.stats.avg);
      }).catch(() => {});
    };
    fetchSeries();
    const iv = setInterval(fetchSeries, 30000);
    return () => {
      alive = false;
      clearInterval(iv);
    };
  }, [target.id]);

  return (
    <button
      onClick={onClick}
      className="glass group fade-up relative overflow-hidden rounded-2xl p-4 text-left transition-all hover:-translate-y-0.5 hover:border-cyan-400/30"
    >
      <div
        className="absolute inset-x-0 top-0 h-0.5"
        style={{ background: meta.color }}
      />
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span
              className="h-2 w-2 shrink-0 rounded-full"
              style={{ background: meta.color }}
            />
            <span className="truncate text-sm font-semibold">{target.name}</span>
          </div>
          <div className="mono mt-0.5 truncate text-xs text-muted-foreground">
            {target.host}
          </div>
        </div>
        <span className="mono shrink-0 rounded-md bg-white/5 px-1.5 py-0.5 text-[10px] text-purple-300">
          {target.probe}
        </span>
      </div>

      <div className="my-2">
        <Sparkline data={spark} color={meta.color} />
      </div>

      <div className="flex items-end justify-between">
        <div>
          <div className="mono text-xl font-bold text-foreground">
            {fmtMs(target.current)}
          </div>
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
            current
          </div>
        </div>
        <div className="text-right">
          <div
            className="mono text-sm font-semibold"
            style={{ color: lossColor(target.currentLoss || 0) }}
          >
            {target.currentLoss || 0}%
          </div>
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
            loss
          </div>
        </div>
        <div className="text-right">
          <div className="mono text-sm font-semibold text-muted-foreground">
            {avg != null ? fmtMs(avg) : "—"}
          </div>
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
            avg 3h
          </div>
        </div>
      </div>
    </button>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [tree, setTree] = useState([]);
  const [overview, setOverview] = useState({ up: 0, warn: 0, down: 0, total: 0, avg_latency: 0 });

  const load = useCallback(() => {
    api.tree().then(setTree).catch(() => {});
    api.overview().then(setOverview).catch(() => {});
  }, []);

  useEffect(() => {
    load();
    const iv = setInterval(load, 30000);
    return () => clearInterval(iv);
  }, [load]);

  const grouped = tree
    .map((g) => ({
      ...g,
      items: g.children.filter(
        (t) =>
          t.name.toLowerCase().includes(query.toLowerCase()) ||
          t.host.toLowerCase().includes(query.toLowerCase())
      ),
    }))
    .filter((g) => g.items.length > 0);

  return (
    <div className="mx-auto max-w-[1400px] p-4 lg:p-6">
      <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Real-time latency and packet-loss overview across all targets
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search targets…"
              className="w-full bg-card/50 pl-9 sm:w-56"
            />
          </div>
          <Button
            onClick={() => setModalOpen(true)}
            className="bg-gradient-to-r from-cyan-400 to-purple-500 font-semibold text-slate-950 hover:opacity-90"
          >
            <Plus className="mr-1.5 h-4 w-4" /> Add Target
          </Button>
        </div>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard icon={CheckCircle2} label="Up" value={overview.up} sub={`of ${overview.total} targets`} accent="#22d3ee" />
        <StatCard icon={AlertTriangle} label="Degraded" value={overview.warn} sub="elevated latency / loss" accent="#facc15" />
        <StatCard icon={Zap} label="Down" value={overview.down} sub="unreachable" accent="#f87171" />
        <StatCard icon={Gauge} label="Avg Latency" value={fmtMs(overview.avg_latency)} sub="across all targets" accent="#a855f7" />
      </div>

      {grouped.map((group) => (
        <div key={group.id} className="mb-7">
          <div className="mb-3 flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-purple-400" />
            <h2 className="text-sm font-semibold uppercase tracking-wider text-foreground/90">
              {group.name}
            </h2>
            <span className="text-xs text-muted-foreground">
              {group.items.length} targets
            </span>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {group.items.map((t) => (
              <TargetCard key={t.id} target={t} onClick={() => navigate(`/target/${t.id}`)} />
            ))}
          </div>
        </div>
      ))}

      {grouped.length === 0 && (
        <div className="glass flex flex-col items-center justify-center rounded-2xl py-16 text-center">
          <Activity className="mb-3 h-8 w-8 text-muted-foreground" />
          <div className="font-medium">No targets found</div>
          <div className="text-sm text-muted-foreground">
            {query ? "Try a different search term" : "Add a target to start monitoring"}
          </div>
        </div>
      )}

      <TargetFormModal open={modalOpen} onOpenChange={setModalOpen} onSaved={load} />
    </div>
  );
}
