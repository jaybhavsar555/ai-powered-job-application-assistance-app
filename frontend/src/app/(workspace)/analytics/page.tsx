"use client";

import { useCallback, useEffect, useState } from "react";
import { Activity, RefreshCw } from "lucide-react";
import api, { getApiErrorMessage } from "@/lib/api";
import {
  AnalyticsDashboard,
  AnalyticsSummary,
} from "@/components/analytics/AnalyticsDashboard";

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data: summary } = await api.get<AnalyticsSummary>("/analytics/summary");
      setData(summary);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Failed to load analytics"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  return (
    <div className="flex-1 p-8 space-y-6 overflow-y-auto">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Agent telemetry, estimated cost, and pipeline health
          </p>
        </div>
        <button
          onClick={fetchSummary}
          disabled={loading}
          className="flex items-center gap-2 border border-border bg-card px-3 py-2 rounded-md text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {loading && !data ? (
        <div className="flex justify-center p-12 text-muted-foreground">
          Loading telemetry…
        </div>
      ) : error && !data ? (
        <div className="rounded-xl border border-border bg-card p-12 flex flex-col items-center justify-center text-center space-y-4">
          <Activity className="w-12 h-12 text-red-400 opacity-50" />
          <div>
            <h3 className="font-semibold text-lg text-foreground">Couldn’t load analytics</h3>
            <p className="text-sm text-muted-foreground max-w-sm mt-1">{error}</p>
          </div>
          <button onClick={fetchSummary} className="text-sm text-primary hover:underline">
            Try again
          </button>
        </div>
      ) : data ? (
        <>
          {error && (
            <div className="text-sm text-amber-500 bg-amber-500/10 border border-amber-500/20 rounded-md px-3 py-2">
              {error}
            </div>
          )}
          <AnalyticsDashboard data={data} />
        </>
      ) : null}
    </div>
  );
}
