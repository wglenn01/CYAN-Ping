import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  BellRing,
  AlertTriangle,
  AlertOctagon,
  CheckCircle2,
  ChevronRight,
} from "lucide-react";
import { api } from "../api";
import { timeAgo } from "../lib/utils-sp";
import { Switch } from "../components/ui/switch";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";
import { toast } from "sonner";

const severityMeta = {
  critical: { color: "#f87171", icon: AlertOctagon, label: "Critical" },
  warning: { color: "#facc15", icon: AlertTriangle, label: "Warning" },
};

function AlertRow({ alert, onClick }) {
  const meta = severityMeta[alert.severity] || severityMeta.warning;
  const Icon = alert.status === "resolved" ? CheckCircle2 : meta.icon;
  const color = alert.status === "resolved" ? "#4ade80" : meta.color;
  return (
    <button
      onClick={onClick}
      className="glass group flex w-full items-center gap-4 rounded-xl p-4 text-left transition-all hover:border-cyan-400/30"
    >
      <div
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl"
        style={{ background: `${color}1a` }}
      >
        <Icon className="h-5 w-5" style={{ color }} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate font-semibold">{alert.target}</span>
          <span
            className="mono rounded-md px-1.5 py-0.5 text-[10px]"
            style={{ background: `${color}1a`, color }}
          >
            {alert.rule}
          </span>
        </div>
        <div className="truncate text-sm text-muted-foreground">
          {alert.message}
        </div>
      </div>
      <div className="hidden shrink-0 text-right sm:block">
        <div className="text-xs font-medium" style={{ color: alert.status === "resolved" ? "#4ade80" : color }}>
          {alert.status === "resolved" ? "Resolved" : "Active"}
        </div>
        <div className="text-xs text-muted-foreground">{alert.since ? timeAgo(alert.since) : ""}</div>
      </div>
      <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
    </button>
  );
}

export default function Alerts() {
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState([]);
  const [rules, setRules] = useState([]);

  const load = () => {
    api.alerts().then(setAlerts).catch(() => {});
    api.alertRules().then(setRules).catch(() => {});
  };

  useEffect(() => {
    load();
    const iv = setInterval(load, 30000);
    return () => clearInterval(iv);
  }, []);

  const active = alerts.filter((a) => a.status === "active");
  const resolved = alerts.filter((a) => a.status === "resolved");

  const toggleRule = async (r) => {
    try {
      await api.updateRule(r.id, !r.enabled);
      setRules((rs) => rs.map((x) => (x.id === r.id ? { ...x, enabled: !x.enabled } : x)));
      toast.success(`Rule "${r.name}" ${!r.enabled ? "enabled" : "disabled"}`);
    } catch (e) {
      toast.error("Could not update rule");
    }
  };

  return (
    <div className="mx-auto max-w-[1100px] p-4 lg:p-6">
      <div className="mb-6">
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
          <BellRing className="h-6 w-6 text-purple-400" /> Alerts
        </h1>
        <p className="text-sm text-muted-foreground">
          Notifications and threshold rules for your monitored targets
        </p>
      </div>

      <Tabs defaultValue="active">
        <TabsList className="bg-card/50">
          <TabsTrigger value="active">
            Active
            {active.length > 0 && (
              <span className="ml-2 rounded-full bg-red-500/20 px-1.5 text-[10px] font-bold text-red-300">
                {active.length}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="resolved">Resolved</TabsTrigger>
          <TabsTrigger value="rules">Rules</TabsTrigger>
        </TabsList>

        <TabsContent value="active" className="mt-4 space-y-3">
          {active.length ? (
            active.map((a) => (
              <AlertRow key={a.id} alert={a} onClick={() => navigate(`/target/${a.targetId}`)} />
            ))
          ) : (
            <EmptyState label="No active alerts — all systems healthy" />
          )}
        </TabsContent>

        <TabsContent value="resolved" className="mt-4 space-y-3">
          {resolved.length ? (
            resolved.map((a) => (
              <AlertRow key={a.id} alert={a} onClick={() => navigate(`/target/${a.targetId}`)} />
            ))
          ) : (
            <EmptyState label="No resolved alerts yet" />
          )}
        </TabsContent>

        <TabsContent value="rules" className="mt-4 space-y-3">
          {rules.map((r) => {
            const meta = severityMeta[r.severity] || severityMeta.warning;
            return (
              <div key={r.id} className="glass flex items-center gap-4 rounded-xl p-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl" style={{ background: `${meta.color}1a` }}>
                  <meta.icon className="h-5 w-5" style={{ color: meta.color }} />
                </div>
                <div className="flex-1">
                  <div className="font-semibold">{r.name}</div>
                  <div className="mono text-xs text-muted-foreground">
                    {r.condition} {r.operator} {r.value}
                    {r.condition === "latency" ? "ms" : "%"} · {meta.label}
                  </div>
                </div>
                <Switch checked={r.enabled} onCheckedChange={() => toggleRule(r)} />
              </div>
            );
          })}
          {rules.length === 0 && <EmptyState label="No rules configured" />}
        </TabsContent>
      </Tabs>
    </div>
  );
}

function EmptyState({ label }) {
  return (
    <div className="glass flex flex-col items-center justify-center rounded-2xl py-16 text-center">
      <CheckCircle2 className="mb-3 h-8 w-8 text-cyan-400" />
      <div className="text-sm text-muted-foreground">{label}</div>
    </div>
  );
}
