"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useWorkflowStore } from "@/hooks/useWorkflowStore";
import { ApprovalCard } from "@/components/ui/ApprovalCard";
import { AlertCircle, CheckCircle2, FileStack, Loader2 } from "lucide-react";
import api, { getApiErrorMessage } from "@/lib/api";
import { DEMO_JOB_ID } from "@/components/workflow/CanvasJobPicker";

type CardKey = "cover_letter" | "resume";
type CardStatus = "pending" | "approved" | "rejected" | "saving";

function asCoverLetterText(value: unknown): string {
  if (!value) return "";
  if (typeof value === "string") return value;
  if (typeof value === "object" && value !== null && "content" in value) {
    return String((value as { content: string }).content || "");
  }
  return JSON.stringify(value, null, 2);
}

function isDemoJob(jobId: string): boolean {
  return !jobId || jobId === DEMO_JOB_ID;
}

export default function ApprovalsPage() {
  const { finalState, workflowStatus, setFinalState } = useWorkflowStore();
  const [statuses, setStatuses] = useState<Record<CardKey, CardStatus>>({
    cover_letter: "pending",
    resume: "pending",
  });
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [packaging, setPackaging] = useState(false);
  const [packagePath, setPackagePath] = useState<string | null>(null);
  const packageAttempted = useRef(false);

  const coverLetter = asCoverLetterText(finalState?.cover_letter);
  const resumeUpdates = (finalState?.tailored_resume || {}) as {
    summary?: string;
    tailored_bullets?: string[];
    added_keywords?: string[];
  };
  const jobId = String(finalState?.job_id || "");
  const atsScore =
    typeof finalState?.ats_score === "number" ? finalState.ats_score : undefined;

  const resumeProposed = useMemo(() => {
    const parts: string[] = [];
    if (resumeUpdates.summary) parts.push(`Summary:\n${resumeUpdates.summary}`);
    if (resumeUpdates.added_keywords?.length) {
      parts.push(`Added keywords: ${resumeUpdates.added_keywords.join(", ")}`);
    }
    if (resumeUpdates.tailored_bullets?.length) {
      parts.push(
        `Bullets:\n${resumeUpdates.tailored_bullets.map((b) => `• ${b}`).join("\n")}`
      );
    }
    return parts.join("\n\n") || JSON.stringify(resumeUpdates, null, 2);
  }, [resumeUpdates]);

  const hasResume =
    Boolean(resumeUpdates.added_keywords?.length) ||
    Boolean(resumeUpdates.summary) ||
    Boolean(resumeUpdates.tailored_bullets?.length);

  const coverNeeded = Boolean(coverLetter);
  const resumeNeeded = hasResume;

  const bothApproved =
    (!coverNeeded || statuses.cover_letter === "approved") &&
    (!resumeNeeded || statuses.resume === "approved") &&
    (coverNeeded || resumeNeeded);

  const allDecided =
    (!coverNeeded || statuses.cover_letter !== "pending") &&
    (!resumeNeeded || statuses.resume !== "pending");

  // Reset approval UI when a new workflow completion arrives for a job
  const runKey =
    workflowStatus === "completed" && finalState
      ? `${String(finalState.job_id || "")}:${coverLetter.slice(0, 40)}:${resumeUpdates.summary || ""}`
      : "";

  useEffect(() => {
    if (!runKey) return;
    packageAttempted.current = false;
    setPackagePath(null);
    setStatuses({ cover_letter: "pending", resume: "pending" });
    setMessage(null);
    setError(null);
  }, [runKey]);

  const runApplyPackage = async () => {
    if (!jobId || isDemoJob(jobId) || packaging) return;
    setPackaging(true);
    setError(null);
    try {
      const { data } = await api.post<{
        folder: string;
        company: string;
        role_family: string;
      }>("/documents/apply-package", { job_id: jobId });
      setPackagePath(data.folder);
      setMessage(
        `Package saved for ${data.company} (${data.role_family}) → ${data.folder}`
      );
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to write apply package"));
    } finally {
      setPackaging(false);
    }
  };

  useEffect(() => {
    if (!bothApproved || isDemoJob(jobId) || packageAttempted.current) return;
    packageAttempted.current = true;
    void runApplyPackage();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- trigger once when both approved
  }, [bothApproved, jobId]);

  const decide = async (artifact: CardKey, decision: "approve" | "reject") => {
    if (!jobId) {
      setError("Missing job_id from workflow — re-run Simulate with a selected Tracker job.");
      return;
    }
    setError(null);
    setMessage(null);
    setStatuses((s) => ({ ...s, [artifact]: "saving" }));
    try {
      const { data } = await api.post("/approvals/decide", {
        artifact,
        decision,
        job_id: jobId,
        cover_letter: artifact === "cover_letter" ? coverLetter : undefined,
        tailored_resume: artifact === "resume" ? resumeUpdates : undefined,
        ats_score: atsScore,
        evidence:
          artifact === "cover_letter"
            ? "Cover letter hooks mapped to company research and resume context."
            : "ATS gaps woven into resume bullets while preserving factual claims.",
      });
      setStatuses((s) => ({
        ...s,
        [artifact]: decision === "approve" ? "approved" : "rejected",
      }));
      setMessage(`${data.message} · Tracker stage: ${data.stage}`);
    } catch (err) {
      setStatuses((s) => ({ ...s, [artifact]: "pending" }));
      setError(getApiErrorMessage(err, "Approval decision failed"));
    }
  };

  if (workflowStatus !== "completed" || !finalState) {
    return (
      <div className="flex-1 p-8 space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold tracking-tight">Human-in-the-Loop Approvals</h1>
        </div>
        <div className="rounded-xl border border-border bg-card p-12 flex flex-col items-center justify-center text-center space-y-4">
          <AlertCircle className="w-12 h-12 text-muted-foreground" />
          <div>
            <h3 className="font-semibold text-lg text-foreground">No Pending Approvals</h3>
            <p className="text-sm text-muted-foreground max-w-sm mt-1">
              Select a Tracker job on Canvas, run Simulate, then approve the generated resume and
              cover letter here. Both approvals write a DOCX/PDF package to your resume folder.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 p-8 space-y-6 overflow-y-auto os-scrollbar os-scrollbar-auto">
      <div className="flex justify-between items-center gap-3 flex-wrap">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Pending Approvals</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Job{" "}
            <span className="font-mono text-xs">
              {jobId || "(missing)"}
            </span>
            {isDemoJob(jobId) && (
              <span className="ml-2 text-amber-500">
                · demo mock — package export skipped
              </span>
            )}
          </p>
        </div>
        {allDecided ? (
          <div className="flex items-center gap-2 text-sm text-emerald-400 bg-emerald-500/10 px-3 py-1.5 rounded-full border border-emerald-500/20 font-medium">
            <CheckCircle2 className="w-4 h-4" />
            Review complete
          </div>
        ) : (
          <div className="flex items-center gap-2 text-sm text-amber-500 bg-amber-500/10 px-3 py-1.5 rounded-full border border-amber-500/20 font-medium">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500" />
            </span>
            Requires Human Review
          </div>
        )}
      </div>

      {message && (
        <div className="text-sm text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-md px-3 py-2">
          {message}
        </div>
      )}
      {error && (
        <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-md px-3 py-2">
          {error}
        </div>
      )}

      {packaging && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Writing resume + cover letter package…
        </div>
      )}

      {packagePath && (
        <div className="flex items-start gap-2 text-sm text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-md px-3 py-2">
          <FileStack className="h-4 w-4 mt-0.5 shrink-0" />
          <span className="break-all">Package folder: {packagePath}</span>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 max-w-4xl">
        {coverLetter && (
          <ApprovalCard
            title="Generated Cover Letter"
            originalText="[No existing cover letter — showing newly generated draft.]"
            proposedText={coverLetter}
            evidence="Hooks from company research (funding, stack) woven into an opening that maps to the JD."
            status={statuses.cover_letter}
            onApprove={() => decide("cover_letter", "approve")}
            onReject={() => decide("cover_letter", "reject")}
          />
        )}

        {hasResume && (
          <ApprovalCard
            title="Resume Optimization"
            originalText="[Base resume before ATS keyword weave]"
            proposedText={resumeProposed}
            evidence="ATS Analyzer missing skills injected into summary/bullets without fabricating experience."
            status={statuses.resume}
            onApprove={() => decide("resume", "approve")}
            onReject={() => decide("resume", "reject")}
          />
        )}
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        {bothApproved && !isDemoJob(jobId) && !packaging && (
          <button
            type="button"
            onClick={() => {
              packageAttempted.current = false;
              void runApplyPackage();
            }}
            className="inline-flex items-center gap-2 text-sm border border-border rounded-md px-3 py-1.5 hover:bg-muted"
          >
            <FileStack className="h-4 w-4" />
            {packagePath ? "Re-write package" : "Write package now"}
          </button>
        )}
        {allDecided && (
          <button
            type="button"
            onClick={() => setFinalState(null)}
            className="text-sm text-muted-foreground hover:text-foreground underline"
          >
            Clear from inbox
          </button>
        )}
      </div>
    </div>
  );
}
