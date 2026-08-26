"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Check,
  Loader2,
  Radar,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";
import {
  PageMessageBanner,
  PageMessage,
  messageFromError,
} from "@/components/ui/PageMessageBanner";

type StageId =
  | "scan"
  | "awaiting_shortlist"
  | "evaluate"
  | "awaiting_evaluate"
  | "prepare"
  | "awaiting_execute"
  | "execute"
  | "done";

interface PipelineJob {
  id: string;
  company?: string;
  title?: string;
  location?: string;
  salary?: string;
  description?: string;
  matchScore?: number;
  matchReason?: string;
  url?: string | null;
  source?: string | null;
  shortlisted?: boolean;
  evaluate_approved?: boolean;
  evaluation?: {
    global_score?: number;
    recommendation?: string;
    notes?: string;
    dimensions?: Record<string, number>;
  } | null;
  prepared?: boolean;
  ingested_job_id?: string | null;
  email_draft?: {
    subject?: string;
    body?: string;
    to?: string | null;
    status?: string;
    mailto?: string;
  } | null;
  approve_apply?: boolean;
  approve_email?: boolean;
  apply_session_id?: string | null;
  execute_notes?: string[];
}

interface PipelineRun {
  id: string;
  stage: StageId;
  preferences?: Record<string, unknown>;
  sources_used?: string[];
  jobs: PipelineJob[];
  history?: { at: string; stage: string; detail: string }[];
  philosophy?: string;
}

const STAGE_ORDER: StageId[] = [
  "scan",
  "awaiting_shortlist",
  "evaluate",
  "awaiting_evaluate",
  "prepare",
  "awaiting_execute",
  "execute",
  "done",
];

const STAGE_LABEL: Record<StageId, string> = {
  scan: "Scan",
  awaiting_shortlist: "Shortlist",
  evaluate: "Evaluate",
  awaiting_evaluate: "Approve prep",
  prepare: "Prepare",
  awaiting_execute: "Approve actions",
  execute: "Execute",
  done: "Done",
};

export default function SearchPipelinePage() {
  const token = useAuthStore((s) => s.token);
  const [run, setRun] = useState<PipelineRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [banner, setBanner] = useState<PageMessage | null>(null);
  const [targetRoles, setTargetRoles] = useState("software engineer");
  const [isRemote, setIsRemote] = useState(true);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [execFlags, setExecFlags] = useState<
    Record<string, { apply: boolean; email: boolean; to: string }>
  >({});

  const authHeaders = useCallback(
    () => ({
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    }),
    [token]
  );

  const syncFromRun = useCallback((data: PipelineRun) => {
    setRun(data);
    if (data.stage === "awaiting_shortlist") {
      setSelected(
        new Set(
          (data.jobs || [])
            .filter((j) => (j.matchScore || 0) >= 75)
            .map((j) => j.id)
        )
      );
    } else if (data.stage === "awaiting_evaluate") {
      setSelected(
        new Set(
          (data.jobs || []).filter((j) => j.shortlisted).map((j) => j.id)
        )
      );
    } else if (data.stage === "awaiting_execute") {
      const flags: Record<string, { apply: boolean; email: boolean; to: string }> =
        {};
      for (const j of data.jobs || []) {
        if (!j.prepared) continue;
        flags[j.id] = {
          apply: true,
          email: false,
          to: j.email_draft?.to || "",
        };
      }
      setExecFlags(flags);
    }
  }, []);

  const loadLatest = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch("/api/v1/search-pipeline/runs", {
        headers: authHeaders(),
      });
      if (!res.ok) return;
      const data = await res.json();
      const first = (data.runs || [])[0];
      if (!first?.id) return;
      const detail = await fetch(`/api/v1/search-pipeline/runs/${first.id}`, {
        headers: authHeaders(),
      });
      if (detail.ok) syncFromRun(await detail.json());
    } catch {
      /* ignore */
    }
  }, [token, authHeaders, syncFromRun]);

  useEffect(() => {
    void loadLatest();
  }, [loadLatest]);

  const stageIndex = useMemo(() => {
    if (!run) return -1;
    return STAGE_ORDER.indexOf(run.stage);
  }, [run]);

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const startScan = async () => {
    setBusy(true);
    setBanner(null);
    try {
      const res = await fetch("/api/v1/search-pipeline/scan", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          targetRoles,
          isRemote,
          locationHubs: isRemote ? ["Remote"] : [],
          minSalary: "0",
          companyTypes: [],
          techStack: "",
          experienceLevel: "",
          workAuthorization: "",
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(
          typeof data.detail === "string" ? data.detail : "Scan failed"
        );
      }
      syncFromRun(data);
      setBanner({
        tone: "success",
        title: "Scan complete",
        detail: `Found ${data.jobs?.length ?? 0} jobs. Approve a shortlist to continue.`,
      });
    } catch (err) {
      setBanner(messageFromError(err, "Pipeline scan failed"));
    } finally {
      setBusy(false);
    }
  };

  const approveShortlist = async () => {
    if (!run) return;
    setBusy(true);
    setBanner(null);
    try {
      const res = await fetch(
        `/api/v1/search-pipeline/runs/${run.id}/approve-shortlist`,
        {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({ job_ids: Array.from(selected) }),
        }
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(
          typeof data.detail === "string" ? data.detail : "Shortlist failed"
        );
      }
      syncFromRun(data);
      setBanner({
        tone: "success",
        title: "Shortlist approved",
        detail: "Review fit scores, then approve which roles to prepare.",
      });
    } catch (err) {
      setBanner(messageFromError(err, "Could not approve shortlist"));
    } finally {
      setBusy(false);
    }
  };

  const approveEvaluate = async () => {
    if (!run) return;
    setBusy(true);
    setBanner(null);
    try {
      const res = await fetch(
        `/api/v1/search-pipeline/runs/${run.id}/approve-evaluate`,
        {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({ job_ids: Array.from(selected) }),
        }
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(
          typeof data.detail === "string" ? data.detail : "Prepare failed"
        );
      }
      syncFromRun(data);
      setBanner({
        tone: "success",
        title: "Docs prepared",
        detail:
          "Jobs wishlisted with email drafts. Approve apply and/or email per role.",
      });
    } catch (err) {
      setBanner(messageFromError(err, "Could not prepare jobs"));
    } finally {
      setBusy(false);
    }
  };

  const approveExecute = async () => {
    if (!run) return;
    setBusy(true);
    setBanner(null);
    try {
      const actions = Object.entries(execFlags).map(([job_id, f]) => ({
        job_id,
        approve_apply: f.apply,
        approve_email: f.email,
        email_to: f.to || null,
      }));
      const res = await fetch(
        `/api/v1/search-pipeline/runs/${run.id}/approve-execute`,
        {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({ actions }),
        }
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(
          typeof data.detail === "string" ? data.detail : "Execute failed"
        );
      }
      syncFromRun(data);
      setBanner({
        tone: "success",
        title: "Actions executed",
        detail:
          "Continue in Review & Apply and Outreach — nothing was silent-submitted.",
      });
    } catch (err) {
      setBanner(messageFromError(err, "Could not execute approvals"));
    } finally {
      setBusy(false);
    }
  };

  const visibleJobs = useMemo(() => {
    if (!run) return [];
    if (run.stage === "awaiting_shortlist") return run.jobs;
    if (run.stage === "awaiting_evaluate")
      return run.jobs.filter((j) => j.shortlisted);
    if (run.stage === "awaiting_execute" || run.stage === "done")
      return run.jobs.filter((j) => j.prepared);
    return run.jobs;
  }, [run]);

  return (
    <div className="flex-1 p-4 md:p-8 space-y-6 overflow-y-auto os-scrollbar">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-1">
            Approval-gated workflow
          </p>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight flex items-center gap-2">
            <Radar className="h-7 w-7 text-muted-foreground shrink-0" aria-hidden />
            Search Pipeline
          </h1>
          <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
            Scan Knowledge Vault portals, common boards, and the open web — then
            shortlist, evaluate, prepare, and apply/email with{" "}
            <strong className="text-foreground font-medium">your approval at every gate</strong>
            . Inspired by career-ops and ai-job-search; runs on Ollama / Kimi.
          </p>
        </div>
        <button
          type="button"
          onClick={() => loadLatest()}
          className="inline-flex items-center gap-2 text-sm border border-border rounded-md px-3 py-2 hover:bg-muted"
          aria-label="Refresh pipeline"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {banner && (
        <PageMessageBanner message={banner} onDismiss={() => setBanner(null)} />
      )}

      {/* Stage rail */}
      <section className="rounded-xl border bg-card p-4 md:p-5">
        <div className="flex flex-wrap gap-2">
          {(
            [
              "scan",
              "awaiting_shortlist",
              "evaluate",
              "awaiting_evaluate",
              "prepare",
              "awaiting_execute",
              "done",
            ] as StageId[]
          ).map((s) => {
            const idx = STAGE_ORDER.indexOf(s);
            const active = stageIndex === idx;
            const done = stageIndex > idx;
            return (
              <div
                key={s}
                className={`text-xs px-2.5 py-1.5 rounded-md border ${
                  active
                    ? "border-primary bg-primary/10 text-primary font-medium"
                    : done
                      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                      : "border-border text-muted-foreground"
                }`}
              >
                {STAGE_LABEL[s]}
              </div>
            );
          })}
        </div>
        <p className="text-xs text-muted-foreground mt-3 flex items-start gap-2">
          <ShieldCheck className="h-3.5 w-3.5 mt-0.5 shrink-0" />
          No board submit or email send happens until you approve that step.
        </p>
      </section>

      {/* Start scan */}
      <section className="rounded-xl border bg-card p-4 md:p-5 space-y-4">
        <h2 className="font-semibold text-sm md:text-base">1. Scan</h2>
        <div className="flex flex-col sm:flex-row flex-wrap gap-3 items-stretch sm:items-end">
          <label className="text-sm space-y-1.5 flex-1 min-w-[200px]">
            <span className="text-muted-foreground text-xs">Target roles</span>
            <input
              value={targetRoles}
              onChange={(e) => setTargetRoles(e.target.value)}
              className="block w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
              placeholder="e.g. backend engineer, ML engineer"
            />
          </label>
          <label className="inline-flex items-center gap-2 text-sm px-1 py-2">
            <input
              type="checkbox"
              checked={isRemote}
              onChange={(e) => setIsRemote(e.target.checked)}
              className="rounded border-border"
            />
            Remote-friendly
          </label>
          <button
            type="button"
            disabled={busy || !token}
            onClick={startScan}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium disabled:opacity-50"
          >
            {busy ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Radar className="h-4 w-4" />
            )}
            Scan Vault + boards + web
          </button>
        </div>
        <p className="text-xs text-muted-foreground">
          Vault includes LinkedIn, Indeed, Unstop, Instahyre, Wellfound, Naukri,
          and ATS hosts. Prefer pasting a posting URL via{" "}
          <Link href="/jobs?import=1" className="text-primary hover:underline">
            Jobs → Import
          </Link>{" "}
          when you already have a link from those sites.
        </p>
        {run?.sources_used && run.sources_used.length > 0 && (
          <p className="text-xs text-muted-foreground">
            Sources this run: {run.sources_used.join(", ")}
          </p>
        )}
      </section>

      {/* Jobs + approvals */}
      {run && (
        <section className="rounded-xl border bg-card p-4 md:p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-semibold text-sm md:text-base">
              {run.stage === "awaiting_shortlist" && "2. Approve shortlist"}
              {run.stage === "awaiting_evaluate" && "3. Approve roles to prepare"}
              {run.stage === "awaiting_execute" && "4. Approve apply / email"}
              {run.stage === "done" && "Pipeline complete"}
              {!["awaiting_shortlist", "awaiting_evaluate", "awaiting_execute", "done"].includes(
                run.stage
              ) && `Stage: ${STAGE_LABEL[run.stage]}`}
            </h2>
            {run.stage === "awaiting_shortlist" && (
              <button
                type="button"
                disabled={busy || selected.size === 0}
                onClick={approveShortlist}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium disabled:opacity-50"
              >
                <Check className="h-4 w-4" />
                Approve {selected.size} shortlist
              </button>
            )}
            {run.stage === "awaiting_evaluate" && (
              <button
                type="button"
                disabled={busy || selected.size === 0}
                onClick={approveEvaluate}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium disabled:opacity-50"
              >
                <Check className="h-4 w-4" />
                Prepare {selected.size} roles
              </button>
            )}
            {run.stage === "awaiting_execute" && (
              <button
                type="button"
                disabled={busy}
                onClick={approveExecute}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-emerald-600 text-white text-sm font-medium disabled:opacity-50"
              >
                <Check className="h-4 w-4" />
                Execute approved actions
              </button>
            )}
          </div>

          {visibleJobs.length === 0 ? (
            <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
              No jobs at this gate yet. Run a scan above.
            </div>
          ) : (
            <ul className="space-y-3">
              {visibleJobs.map((job) => (
                <li
                  key={job.id}
                  className="rounded-lg border border-border p-3 md:p-4 space-y-2"
                >
                  <div className="flex flex-wrap items-start gap-3">
                    {(run.stage === "awaiting_shortlist" ||
                      run.stage === "awaiting_evaluate") && (
                      <input
                        type="checkbox"
                        checked={selected.has(job.id)}
                        onChange={() => toggle(job.id)}
                        className="mt-1 rounded border-border"
                        aria-label={`Select ${job.title}`}
                      />
                    )}
                    <div className="min-w-0 flex-1 space-y-1">
                      <div className="flex flex-wrap items-baseline gap-2">
                        <p className="font-medium text-sm md:text-base">
                          {job.title || "Role"}
                        </p>
                        <span className="text-sm text-muted-foreground">
                          {job.company}
                        </span>
                        {typeof job.matchScore === "number" && (
                          <span className="text-xs tabular-nums font-medium text-emerald-600 dark:text-emerald-400">
                            {job.matchScore}/100
                          </span>
                        )}
                        {job.source && (
                          <span className="text-[10px] uppercase tracking-wider text-muted-foreground border rounded px-1.5 py-0.5">
                            {job.source}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {job.matchReason || job.description}
                      </p>
                      {job.evaluation && (
                        <p className="text-xs">
                          Fit {job.evaluation.global_score}/5 —{" "}
                          {job.evaluation.recommendation}
                        </p>
                      )}
                      {job.url && (
                        <a
                          href={job.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-xs text-primary hover:underline inline-flex items-center gap-1"
                        >
                          Open posting <ArrowRight className="h-3 w-3" />
                        </a>
                      )}
                    </div>
                  </div>

                  {run.stage === "awaiting_execute" && job.prepared && (
                    <div className="pl-0 sm:pl-7 flex flex-col sm:flex-row flex-wrap gap-3 pt-2 border-t border-border/60">
                      <label className="inline-flex items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          checked={!!execFlags[job.id]?.apply}
                          onChange={(e) =>
                            setExecFlags((prev) => ({
                              ...prev,
                              [job.id]: {
                                ...(prev[job.id] || { apply: false, email: false, to: "" }),
                                apply: e.target.checked,
                              },
                            }))
                          }
                        />
                        Start Review &amp; Apply
                      </label>
                      <label className="inline-flex items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          checked={!!execFlags[job.id]?.email}
                          onChange={(e) =>
                            setExecFlags((prev) => ({
                              ...prev,
                              [job.id]: {
                                ...(prev[job.id] || { apply: false, email: false, to: "" }),
                                email: e.target.checked,
                              },
                            }))
                          }
                        />
                        Save / send email draft
                      </label>
                      <input
                        type="email"
                        placeholder="Recruiter email (optional)"
                        value={execFlags[job.id]?.to || ""}
                        onChange={(e) =>
                          setExecFlags((prev) => ({
                            ...prev,
                            [job.id]: {
                              ...(prev[job.id] || { apply: false, email: false, to: "" }),
                              to: e.target.value,
                            },
                          }))
                        }
                        className="rounded-md border border-border bg-background px-2 py-1.5 text-sm min-w-[200px]"
                      />
                    </div>
                  )}

                  {run.stage === "done" && (
                    <div className="text-xs text-muted-foreground space-y-1 pt-2 border-t border-border/60">
                      {(job.execute_notes || []).map((n, i) => (
                        <p key={i}>{n}</p>
                      ))}
                      <div className="flex flex-wrap gap-2 pt-1">
                        {job.ingested_job_id && (
                          <Link
                            href={`/apply?job_id=${encodeURIComponent(job.ingested_job_id)}`}
                            className="text-primary hover:underline inline-flex items-center gap-1"
                          >
                            Open Apply <ArrowRight className="h-3 w-3" />
                          </Link>
                        )}
                        <Link
                          href="/outreach"
                          className="text-primary hover:underline inline-flex items-center gap-1"
                        >
                          Outreach <ArrowRight className="h-3 w-3" />
                        </Link>
                      </div>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <section className="rounded-xl border border-dashed bg-muted/10 p-4 text-sm text-muted-foreground space-y-2">
        <p className="font-medium text-foreground">Local models</p>
        <p>
          Use Ollama (<code className="text-xs bg-muted px-1 rounded">qwen2.5:7b</code>) or
          Token Harbor Kimi (<code className="text-xs bg-muted px-1 rounded">kimi-k3:free</code>).
          See <code className="text-xs">docs/local_llm_models.md</code> and switch in Canvas → LLM.
        </p>
        <div className="flex flex-wrap gap-3 pt-1">
          <Link href="/vault" className="text-primary hover:underline text-sm">
            Knowledge Vault
          </Link>
          <Link href="/discovery" className="text-primary hover:underline text-sm">
            Classic Discovery
          </Link>
          <Link href="/apply" className="text-primary hover:underline text-sm">
            Review &amp; Apply
          </Link>
        </div>
      </section>
    </div>
  );
}
