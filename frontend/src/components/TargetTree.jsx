import React, { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ChevronRight, Folder, FolderOpen, Circle } from "lucide-react";
import { api } from "../api";
import { statusMeta } from "../lib/utils-sp";

export default function TargetTree({ onNavigate, refreshKey }) {
  const [tree, setTree] = useState([]);
  const [open, setOpen] = useState({});
  const navigate = useNavigate();
  const { id } = useParams();

  useEffect(() => {
    let alive = true;
    const load = () =>
      api.tree().then((data) => {
        if (!alive) return;
        setTree(data);
        setOpen((prev) =>
          Object.keys(prev).length
            ? prev
            : Object.fromEntries(data.map((g) => [g.id, true]))
        );
      }).catch(() => {});
    load();
    const iv = setInterval(load, 30000);
    return () => {
      alive = false;
      clearInterval(iv);
    };
  }, [refreshKey]);

  const toggle = (gid) => setOpen((o) => ({ ...o, [gid]: !o[gid] }));

  return (
    <div className="space-y-1">
      {tree.map((group) => {
        const isOpen = open[group.id];
        return (
          <div key={group.id}>
            <button
              onClick={() => toggle(group.id)}
              className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-sm font-medium text-foreground/90 transition-colors hover:bg-white/5"
            >
              <ChevronRight
                className={`h-3.5 w-3.5 text-muted-foreground transition-transform ${
                  isOpen ? "rotate-90" : ""
                }`}
              />
              {isOpen ? (
                <FolderOpen className="h-4 w-4 text-purple-400" />
              ) : (
                <Folder className="h-4 w-4 text-purple-400" />
              )}
              <span className="truncate">{group.name}</span>
              <span className="ml-auto text-[10px] text-muted-foreground">
                {group.children.length}
              </span>
            </button>

            {isOpen && (
              <div className="ml-3 border-l border-border/60 pl-2">
                {group.children.map((t) => {
                  const meta = statusMeta[t.status] || statusMeta.up;
                  const active = id === t.id;
                  return (
                    <button
                      key={t.id}
                      onClick={() => {
                        navigate(`/target/${t.id}`);
                        onNavigate?.();
                      }}
                      className={`group flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors ${
                        active
                          ? "bg-cyan-400/10 text-cyan-200"
                          : "text-muted-foreground hover:bg-white/5 hover:text-foreground"
                      }`}
                    >
                      <Circle
                        className="h-2 w-2 shrink-0"
                        fill={meta.color}
                        color={meta.color}
                      />
                      <span className="truncate">{t.name}</span>
                      <span className="mono ml-auto text-[10px] text-muted-foreground/70">
                        {t.probe}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
      {tree.length === 0 && (
        <div className="px-3 py-6 text-center text-xs text-muted-foreground">
          Loading targets…
        </div>
      )}
    </div>
  );
}
