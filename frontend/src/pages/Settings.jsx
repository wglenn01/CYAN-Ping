import React, { useState } from "react";
import {
  Settings as SettingsIcon,
  User,
  Bell,
  Gauge,
  Server,
  Save,
  Mail,
  Webhook,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Switch } from "../components/ui/switch";
import { Separator } from "../components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { toast } from "sonner";

function Section({ icon: Icon, title, desc, children }) {
  return (
    <div className="glass rounded-2xl p-5">
      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-cyan-400/10">
          <Icon className="h-4.5 w-4.5 text-cyan-400" />
        </div>
        <div>
          <div className="font-semibold">{title}</div>
          <div className="text-xs text-muted-foreground">{desc}</div>
        </div>
      </div>
      <Separator className="mb-4 bg-border/60" />
      {children}
    </div>
  );
}

function Row({ label, hint, children }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2.5">
      <div>
        <div className="text-sm font-medium">{label}</div>
        {hint && <div className="text-xs text-muted-foreground">{hint}</div>}
      </div>
      {children}
    </div>
  );
}

export default function Settings() {
  const { user } = useAuth();
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [webhookAlerts, setWebhookAlerts] = useState(false);
  const [interval, setInterval] = useState("60");
  const [retention, setRetention] = useState("360");

  return (
    <div className="mx-auto max-w-[900px] p-4 lg:p-6">
      <div className="mb-6">
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
          <SettingsIcon className="h-6 w-6 text-purple-400" /> Settings
        </h1>
        <p className="text-sm text-muted-foreground">
          Configure monitoring behaviour, account and notifications
        </p>
      </div>

      <div className="space-y-5">
        <Section icon={User} title="Account" desc="Your login and profile">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Username</Label>
              <Input defaultValue={user?.username} className="bg-background/50" />
            </div>
            <div className="space-y-2">
              <Label>Role</Label>
              <Input
                defaultValue={user?.role}
                disabled
                className="bg-background/50"
              />
            </div>
            <div className="space-y-2">
              <Label>New password</Label>
              <Input
                type="password"
                placeholder="••••••••"
                className="bg-background/50"
              />
            </div>
            <div className="space-y-2">
              <Label>Confirm password</Label>
              <Input
                type="password"
                placeholder="••••••••"
                className="bg-background/50"
              />
            </div>
          </div>
        </Section>

        <Section
          icon={Gauge}
          title="Monitoring"
          desc="Default polling and data retention"
        >
          <Row label="Default poll interval" hint="How often targets are probed">
            <Select value={interval} onValueChange={setInterval}>
              <SelectTrigger className="w-40 bg-background/50">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="30">Every 30 seconds</SelectItem>
                <SelectItem value="60">Every 60 seconds</SelectItem>
                <SelectItem value="120">Every 2 minutes</SelectItem>
                <SelectItem value="300">Every 5 minutes</SelectItem>
              </SelectContent>
            </Select>
          </Row>
          <Row label="Data retention" hint="How long history is stored">
            <Select value={retention} onValueChange={setRetention}>
              <SelectTrigger className="w-40 bg-background/50">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="30">30 days</SelectItem>
                <SelectItem value="90">90 days</SelectItem>
                <SelectItem value="360">360 days</SelectItem>
                <SelectItem value="720">2 years</SelectItem>
              </SelectContent>
            </Select>
          </Row>
          <Row label="Pings per sample" hint="Packets sent per measurement (ICMP)">
            <Input
              type="number"
              defaultValue={20}
              className="mono w-40 bg-background/50"
            />
          </Row>
        </Section>

        <Section
          icon={Bell}
          title="Notifications"
          desc="Where alerts get delivered"
        >
          <Row label={
            <span className="flex items-center gap-2"><Mail className="h-4 w-4 text-cyan-400" /> Email alerts</span>
          } hint="Send email when a rule triggers">
            <Switch checked={emailAlerts} onCheckedChange={setEmailAlerts} />
          </Row>
          {emailAlerts && (
            <div className="ml-0 mt-1 space-y-2 sm:ml-7">
              <Input
                placeholder="alerts@cyanwireless.net"
                className="bg-background/50"
              />
            </div>
          )}
          <Separator className="my-3 bg-border/40" />
          <Row label={
            <span className="flex items-center gap-2"><Webhook className="h-4 w-4 text-purple-400" /> Webhook</span>
          } hint="POST alert payloads to a URL (Slack, Discord…)">
            <Switch checked={webhookAlerts} onCheckedChange={setWebhookAlerts} />
          </Row>
          {webhookAlerts && (
            <div className="ml-0 mt-1 space-y-2 sm:ml-7">
              <Input
                placeholder="https://hooks.slack.com/services/…"
                className="mono bg-background/50"
              />
            </div>
          )}
        </Section>

        <div className="flex justify-end">
          <Button
            onClick={() => toast.success("Settings saved (demo)")}
            className="bg-gradient-to-r from-cyan-400 to-purple-500 font-semibold text-slate-950 hover:opacity-90"
          >
            <Save className="mr-1.5 h-4 w-4" /> Save changes
          </Button>
        </div>
      </div>
    </div>
  );
}
