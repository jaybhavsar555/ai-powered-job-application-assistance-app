"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Briefcase, Loader2 } from "lucide-react";
import api, { getApiErrorMessage } from "@/lib/api";
import type { Application } from "@/components/tracker/ApplicationCard";

export const DEMO_JOB_ID = "00000000-0000-0000-0000-000000000000";
export const SELECTED_JOB_STORAGE_KEY = "career-os:selected-job-id";

export type JobOption = {
  jobId: string;
  applicationId: string;
  label: string;
  stage: string;
};

type Props = {
  selectedJobId: string;
  onSelect: (jobId: string) => void;
  disabled?: boolean;
};

export function jobLabel(app: Application): string {
  const company = app.job?.company_name || "Unknown company";
  const role = app.job?.role_title || "Untitled role";
  return `${company} · ${role}`;
}

export function CanvasJobPicker({ selectedJobId, onSelect, disabled }: Props) {
  const [options, setOptions] = useState<JobOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get<Application[]>("/applications/");
      setOptions(
        data.map((app) => ({
          jobId: app.job_id,
          applicationId: app.id,
          label: jobLabel(app),
          stage: String(app.stage),
        }))
      );
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Failed to load jobs"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const hasRealJobs = options.length > 0;

  return (
    <div className="flex flex-col gap-1 min-w-0 w-full sm:w-auto sm:min-w-[280px] max-w-md">
      <label className="text-[10px] uppercase tracking-wide text-muted-foreground">
        Job for Simulate
      </label>
      <div className="flex items-center gap-2">
        {loading ? (
          <div className="flex items-center gap-2 text-xs text-muted-foreground border border-border rounded-md px-3 py-2 flex-1">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Loading jobs…
          </div>
        ) : (
          <select
            value={selectedJobId}
            disabled={disabled}
            onChange={(e) => onSelect(e.target.value)}
            className="flex-1 min-w-0 rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
          >
            <option value="" disabled>
              {hasRealJobs ? "Select a Tracker job…" : "No Tracker jobs yet"}
            </option>
            {options.map((opt) => (
              <option key={opt.jobId} value={opt.jobId}>
                {opt.label} ({opt.stage})
              </option>
            ))}
            <option value={DEMO_JOB_ID}>Demo mock job (no Tracker row)</option>
          </select>
        )}
        <button
          type="button"
          title="Refresh job list"
          onClick={load}
          disabled={loading || disabled}
          className="shrink-0 border border-border rounded-md p-2 text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-50"
        >
          <Briefcase className="h-4 w-4" />
        </button>
      </div>
      {error && <p className="text-[10px] text-red-400">{error}</p>}
      {!loading && !hasRealJobs && (
        <p className="text-[10px] text-muted-foreground">
          Import a posting in{" "}
          <Link href="/tracker" className="text-primary hover:underline">
            Tracker
          </Link>{" "}
          first, or use Demo mock job.
        </p>
      )}
    </div>
  );
}
