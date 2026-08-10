"use client";

import { useCallback, useEffect, useState } from "react";
import { Package, RefreshCw, Power } from "lucide-react";
import api, { getApiErrorMessage } from "@/lib/api";

type Plugin = {
  id: string;
  name: string;
  title: string;
  description: string;
  version: string;
  author: string;
  enabled: boolean;
  registered: boolean;
};

export default function MarketplacePage() {
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get<Plugin[]>("/marketplace/plugins");
      setPlugins(data);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Failed to load marketplace"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const toggle = async (plugin: Plugin) => {
    setBusyId(plugin.id);
    setError(null);
    try {
      const { data } = await api.post<Plugin>(`/marketplace/plugins/${plugin.id}/toggle`, {
        enabled: !plugin.enabled,
      });
      setPlugins((prev) => prev.map((p) => (p.id === plugin.id ? data : p)));
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Toggle failed"));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="flex-1 p-4 md:p-8 space-y-6 overflow-y-auto">
      <div className="flex justify-between items-center gap-3 flex-wrap">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Agent Marketplace</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Enable community / optional agents (YAML plugins under backend/app/marketplace/plugins)
          </p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-2 border border-border bg-card px-3 py-2 rounded-md text-sm text-muted-foreground hover:text-foreground"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-md px-3 py-2">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-muted-foreground text-sm">Loading plugins…</p>
      ) : plugins.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-12 text-center space-y-3">
          <Package className="w-10 h-10 mx-auto text-muted-foreground" />
          <p className="text-sm text-muted-foreground">No plugins found.</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {plugins.map((plugin) => (
            <div key={plugin.id} className="border border-border bg-card rounded-xl p-5 space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="font-semibold text-foreground">{plugin.title}</h2>
                  <p className="text-[11px] text-muted-foreground font-mono mt-0.5">
                    {plugin.name} · v{plugin.version} · {plugin.author}
                  </p>
                </div>
                <span
                  className={`text-[10px] uppercase tracking-wide px-2 py-0.5 rounded ${
                    plugin.registered
                      ? "bg-emerald-500/15 text-emerald-400"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {plugin.registered ? "Registered" : "Off"}
                </span>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">{plugin.description}</p>
              <button
                type="button"
                onClick={() => toggle(plugin)}
                disabled={busyId === plugin.id}
                className={`inline-flex items-center gap-2 text-sm px-3 py-2 rounded-md border transition-colors disabled:opacity-50 ${
                  plugin.enabled
                    ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                    : "border-border hover:bg-muted text-muted-foreground"
                }`}
              >
                <Power className="w-4 h-4" />
                {plugin.enabled ? "Disable" : "Enable"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
