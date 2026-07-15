import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "./ui/dialog";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Button } from "./ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { PROBES } from "../constants";
import { api } from "../api";
import { toast } from "sonner";
import { Activity, Loader2 } from "lucide-react";

export default function TargetFormModal({ open, onOpenChange, target, onSaved }) {
  const [groups, setGroups] = useState([]);
  const [form, setForm] = useState({
    name: "",
    host: "",
    probe: "ICMP",
    interval: 60,
    group_id: "",
  });
  const [saving, setSaving] = useState(false);
  const editing = !!target;

  useEffect(() => {
    if (open) {
      api.groups().then((g) => {
        setGroups(g);
        setForm((f) => ({ ...f, group_id: f.group_id || g[0]?.id || "" }));
      }).catch(() => {});
    }
  }, [open]);

  useEffect(() => {
    if (target) {
      setForm({
        name: target.name,
        host: target.host,
        probe: target.probe,
        interval: target.interval,
        group_id: target.group_id,
      });
    } else {
      setForm({ name: "", host: "", probe: "ICMP", interval: 60, group_id: "" });
    }
  }, [target, open]);

  const probe = PROBES.find((p) => p.key === form.probe) || PROBES[0];

  const save = async () => {
    if (!form.name.trim() || !form.host.trim()) {
      toast.error("Name and host are required");
      return;
    }
    setSaving(true);
    try {
      if (editing) {
        await api.updateTarget(target.id, form);
        toast.success(`Target "${form.name}" updated`);
      } else {
        await api.createTarget(form);
        toast.success(`Target "${form.name}" added`, {
          description: "Live probing has started for this target.",
        });
      }
      onOpenChange(false);
      onSaved?.();
    } catch (e) {
      toast.error("Could not save target", {
        description: e?.response?.data?.detail || "Please try again.",
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="glass max-w-lg border-border/60">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-cyan-400" />
            {editing ? "Edit Target" : "Add New Target"}
          </DialogTitle>
          <DialogDescription>
            Configure a host to monitor and the probe used to measure it.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label>Display name</Label>
            <Input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="e.g. Core Router"
              className="bg-background/50"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label>Probe type</Label>
              <Select
                value={form.probe}
                onValueChange={(v) => setForm({ ...form, probe: v })}
              >
                <SelectTrigger className="bg-background/50">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PROBES.map((p) => (
                    <SelectItem key={p.key} value={p.key}>
                      {p.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Group</Label>
              <Select
                value={form.group_id}
                onValueChange={(v) => setForm({ ...form, group_id: v })}
              >
                <SelectTrigger className="bg-background/50">
                  <SelectValue placeholder="Select group" />
                </SelectTrigger>
                <SelectContent>
                  {groups.map((g) => (
                    <SelectItem key={g.id} value={g.id}>
                      {g.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Host / target</Label>
            <Input
              value={form.host}
              onChange={(e) => setForm({ ...form, host: e.target.value })}
              placeholder={probe.hint}
              className="mono bg-background/50"
            />
            <p className="text-xs text-muted-foreground">{probe.desc}</p>
          </div>

          <div className="space-y-2">
            <Label>Poll interval (seconds)</Label>
            <Input
              type="number"
              min={10}
              value={form.interval}
              onChange={(e) =>
                setForm({ ...form, interval: Number(e.target.value) })
              }
              className="mono bg-background/50"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={save}
            disabled={saving}
            className="bg-gradient-to-r from-cyan-400 to-purple-500 font-semibold text-slate-950 hover:opacity-90"
          >
            {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {editing ? "Save changes" : "Add target"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
