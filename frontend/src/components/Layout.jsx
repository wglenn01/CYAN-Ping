import React, { useState, useEffect } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  Activity,
  LayoutDashboard,
  BellRing,
  Settings as SettingsIcon,
  LogOut,
  Menu,
  X,
  Radio,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import TargetTree from "./TargetTree";
import { api } from "../api";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import { Avatar, AvatarFallback } from "./ui/avatar";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/alerts", label: "Alerts", icon: BellRing },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [activeAlerts, setActiveAlerts] = useState(0);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    let alive = true;
    const load = () => {
      api.alerts().then((a) => {
        if (alive) setActiveAlerts(a.filter((x) => x.status === "active").length);
      }).catch(() => {});
      api.overview().then((o) => {
        if (alive) setTotal(o.total);
      }).catch(() => {});
    };
    load();
    const iv = setInterval(load, 30000);
    return () => {
      alive = false;
      clearInterval(iv);
    };
  }, [location.pathname]);

  const SidebarContent = () => (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2.5 px-5 py-5">
        <div className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400 to-purple-500 glow-cyan">
          <Activity className="h-5 w-5 text-slate-950" strokeWidth={2.5} />
        </div>
        <div>
          <div className="text-[15px] font-bold leading-tight tracking-tight">
            Cyan<span className="text-gradient">Ping</span>
          </div>
          <div className="text-[10px] uppercase tracking-widest text-muted-foreground">
            Latency Monitor
          </div>
        </div>
      </div>

      <nav className="px-3 pb-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active =
            item.to === "/"
              ? location.pathname === "/"
              : location.pathname.startsWith(item.to);
          return (
            <button
              key={item.to}
              onClick={() => {
                navigate(item.to);
                setMobileOpen(false);
              }}
              className={`group mb-1 flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                active
                  ? "bg-cyan-400/10 text-cyan-300"
                  : "text-muted-foreground hover:bg-white/5 hover:text-foreground"
              }`}
            >
              <Icon className="h-4 w-4" />
              {item.label}
              {item.label === "Alerts" && activeAlerts > 0 && (
                <span className="ml-auto rounded-full bg-red-500/20 px-1.5 py-0.5 text-[10px] font-bold text-red-300">
                  {activeAlerts}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="mx-3 mb-2 mt-1 border-t border-border/60 pt-3">
        <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
          Targets
        </div>
      </div>
      <div className="flex-1 overflow-y-auto px-2 pb-4">
        <TargetTree onNavigate={() => setMobileOpen(false)} />
      </div>
    </div>
  );

  return (
    <div className="flex h-screen w-full overflow-hidden">
      <aside className="hidden w-72 shrink-0 border-r border-border/60 bg-card/40 backdrop-blur-xl lg:block">
        <SidebarContent />
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="absolute left-0 top-0 h-full w-72 border-r border-border/60 bg-card">
            <button
              className="absolute right-3 top-4 text-muted-foreground"
              onClick={() => setMobileOpen(false)}
            >
              <X className="h-5 w-5" />
            </button>
            <SidebarContent />
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 shrink-0 items-center gap-3 border-b border-border/60 bg-card/30 px-4 backdrop-blur-xl lg:px-6">
          <button
            className="text-muted-foreground lg:hidden"
            onClick={() => setMobileOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </button>

          <div className="flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/5 px-3 py-1.5">
            <span className="live-dot h-2 w-2 rounded-full bg-cyan-400" />
            <span className="text-xs font-medium text-cyan-300">Live</span>
            <span className="hidden text-xs text-muted-foreground sm:inline">
              probing continuously
            </span>
          </div>

          <div className="ml-auto flex items-center gap-3">
            <div className="hidden items-center gap-1.5 text-xs text-muted-foreground sm:flex">
              <Radio className="h-3.5 w-3.5 text-purple-400" />
              {total} targets
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="flex items-center gap-2 rounded-full border border-border/60 bg-white/5 py-1 pl-1 pr-3 transition-colors hover:bg-white/10">
                  <Avatar className="h-7 w-7">
                    <AvatarFallback className="bg-gradient-to-br from-cyan-400 to-purple-500 text-xs font-bold text-slate-950">
                      {user?.username?.slice(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <span className="text-sm font-medium">{user?.username}</span>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuLabel>
                  <div className="font-medium">{user?.username}</div>
                  <div className="text-xs font-normal text-muted-foreground">
                    {user?.role}
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => navigate("/settings")}>
                  <SettingsIcon className="mr-2 h-4 w-4" /> Settings
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => {
                    logout();
                    navigate("/login");
                  }}
                  className="text-red-400 focus:text-red-400"
                >
                  <LogOut className="mr-2 h-4 w-4" /> Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
