"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { useWorkflowStream } from "@/hooks/useWorkflowStream";
import { useWorkflowStore } from "@/hooks/useWorkflowStore";
import { Timeline } from "@/components/workflow/Timeline";
import { WorkflowCanvas } from "@/components/workflow/WorkflowCanvas";
import { LlmProviderSwitch } from "@/components/workflow/LlmProviderSwitch";
import {
  CanvasJobPicker,
  DEMO_JOB_ID,
  SELECTED_JOB_STORAGE_KEY,
} from "@/components/workflow/CanvasJobPicker";
import api from "@/lib/api";

type CheckpointerInfo = {
  backend: string;
  durable: boolean;
  message: string;
  graph_backend?: string;
};

function CanvasPageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const [selectedJobId, setSelectedJobId] = useState<string>("");
  const [streamJobId, setStreamJobId] = useState<string>("");
  const [resume, setResume] = useState(false);
  const [nonce, setNonce] = useState(0);
  const [pickerError, setPickerError] = useState<string | null>(null);
  const [checkpointer, setCheckpointer] = useState<CheckpointerInfo | null>(null);

  useWorkflowStream(streamJobId, resume, nonce);
  const { workflowStatus } = useWorkflowStore();

  useEffect(() => {
    api
      .get<CheckpointerInfo>("/workflows/checkpointer")
      .then(({ data }) => setCheckpointer(data))
      .catch(() => setCheckpointer(null));
  }, []);

  useEffect(() => {
    const fromQuery = searchParams.get("job_id")?.trim() || "";
    if (fromQuery) {
      setSelectedJobId(fromQuery);
      try {
        sessionStorage.setItem(SELECTED_JOB_STORAGE_KEY, fromQuery);
      } catch {
        /* ignore */
      }
      return;
    }
    try {
      const stored = sessionStorage.getItem(SELECTED_JOB_STORAGE_KEY) || "";
      if (stored) setSelectedJobId(stored);
    } catch {
      /* ignore */
    }
  }, [searchParams]);

  const onSelectJob = useCallback(
    (jobId: string) => {
      setSelectedJobId(jobId);
      setPickerError(null);
      try {
        if (jobId) sessionStorage.setItem(SELECTED_JOB_STORAGE_KEY, jobId);
        else sessionStorage.removeItem(SELECTED_JOB_STORAGE_KEY);
      } catch {
        /* ignore */
      }
      const params = new URLSearchParams(searchParams.toString());
      if (jobId && jobId !== DEMO_JOB_ID) params.set("job_id", jobId);
      else params.delete("job_id");
      const q = params.toString();
      router.replace(q ? `${pathname}?${q}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams]
  );

  const startWorkflow = (asResume = false) => {
    if (!selectedJobId) {
      setPickerError("Select a Tracker job (or Demo mock) before Simulate.");
      return;
    }
    setPickerError(null);
    setResume(asResume);
    setStreamJobId(selectedJobId);
    setNonce((n) => n + 1);
  };

  const canRun = Boolean(selectedJobId) && workflowStatus !== "running";

  return (
    <div className="h-full min-h-0 flex flex-col os-scrollbar os-scrollbar-auto overflow-y-auto">
      <div className="flex-1 min-h-0 flex flex-col p-6 lg:p-8 gap-6">
        <div className="flex justify-between items-start gap-4 shrink-0 flex-wrap">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">AI Operating System</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Pick a Tracker job · Switch LLM · Simulate runs against that JD
            </p>
            {checkpointer && (
              <p
                className={`text-[11px] mt-1 ${
                  checkpointer.durable ? "text-emerald-400" : "text-amber-500"
                }`}
                title={checkpointer.message}
              >
                Checkpoints: {checkpointer.backend}
                {checkpointer.durable ? " (durable)" : " (lost on API restart)"}
              </p>
            )}
          </div>
          <div className="flex items-center gap-3 flex-wrap justify-end">
            <LlmProviderSwitch />
          </div>
        </div>

        <div className="flex flex-col sm:flex-row sm:items-end gap-3 shrink-0 flex-wrap">
          <CanvasJobPicker
            selectedJobId={selectedJobId}
            onSelect={onSelectJob}
            disabled={workflowStatus === "running"}
          />
          <div className="flex items-center gap-2">
            <button
              onClick={() => startWorkflow(true)}
              disabled={!canRun}
              title={
                checkpointer?.durable
                  ? "Continue from last Postgres checkpoint for this job"
                  : "Continue from in-memory checkpoint (cleared if API restarts)"
              }
              className="border border-border bg-card hover:bg-muted text-foreground px-4 py-2 rounded-md font-medium transition-colors disabled:opacity-50 shrink-0 text-sm"
            >
              Resume checkpoint
            </button>
            <button
              onClick={() => startWorkflow(false)}
              disabled={!canRun}
              className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-md font-medium transition-colors disabled:opacity-50 shrink-0"
            >
              {workflowStatus === "running"
                ? "Agents Working..."
                : "Simulate Application Flow"}
            </button>
          </div>
        </div>

        {pickerError && (
          <div className="text-sm text-amber-500 bg-amber-500/10 border border-amber-500/20 rounded-md px-3 py-2 shrink-0">
            {pickerError}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-[520px] lg:min-h-0">
          <div className="lg:col-span-2 min-h-[420px] lg:min-h-0 h-full">
            <WorkflowCanvas />
          </div>
          <div className="min-h-[320px] lg:min-h-0 h-full">
            <Timeline />
          </div>
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense
      fallback={
        <div className="flex-1 p-4 md:p-8 text-sm text-muted-foreground">Loading canvas…</div>
      }
    >
      <CanvasPageInner />
    </Suspense>
  );
}
