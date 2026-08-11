"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useWorkflowStore } from "@/hooks/useWorkflowStore";
import { ApprovalCard } from "@/components/ui/ApprovalCard";
import { AlertCircle, CheckCircle2, FileStack, Loader2, Download, Copy, Eye } from "lucide-react";
import api, { getApiErrorMessage, API_BASE_URL } from "@/lib/api";
import { DEMO_JOB_ID } from "@/components/workflow/CanvasJobPicker";

type CardKey = "cover_letter" | "resume";
type CardStatus = "pending" | "approved" | "rejected" | "saving" | "skipped";

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
  const router = useRouter();
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
  const resumeUpdates = useMemo(() => {
    const raw = finalState?.tailored_resume;
    if (!raw || typeof raw !== "object") {
      return {
        summary: undefined as string | undefined,
        tailored_bullets: undefined as string[] | undefined,
        added_keywords: undefined as string[] | undefined,
      };
    }
    const r = raw as {
      summary?: string;
      tailored_bullets?: string[];
      added_keywords?: string[];
      manual_override?: string;
    };
    return {
      summary: r.summary,
      tailored_bullets: r.tailored_bullets,
      added_keywords: r.added_keywords,
      manual_override: r.manual_override,
    };
  }, [finalState?.tailored_resume]);
  const jobId = String(finalState?.job_id || "");
  const [localAtsScore, setLocalAtsScore] = useState<number | undefined>(undefined);
  const [localEvidence, setLocalEvidence] = useState<string>("");

  useEffect(() => {
    setLocalAtsScore(typeof finalState?.ats_score === "number" ? finalState.ats_score : undefined);
    setLocalEvidence(
      `Boosted ATS Score to ${finalState?.ats_score ?? "?"}/100 based on job description keywords.`
    );
  }, [finalState?.ats_score]);

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

  const decide = async (artifact: CardKey, decision: "approve" | "reject", editedText?: string, editedData?: any) => {
    if (!jobId) {
      setError(
        "Missing job_id from workflow — re-run Simulate with a selected Tracker job."
      );
      return;
    }
    setError(null);
    setMessage(null);
    setStatuses((s) => ({ ...s, [artifact]: "saving" }));
    try {
      let finalResume = artifact === "resume" ? resumeUpdates : undefined;
      let finalCover = artifact === "cover_letter" ? coverLetter : undefined;

      if (editedData && artifact === "resume") {
        finalResume = { ...resumeUpdates, ...editedData, manual_override: true };
      } else if (editedText) {
        if (artifact === "cover_letter") {
          finalCover = editedText;
        } else if (artifact === "resume") {
          const summaryMatch = editedText.match(/Summary:\n([\s\S]*?)(?:\n\nAdded keywords:|$)/);
          const keywordsMatch = editedText.match(/Added keywords:\s*(.*?)(?:\n\nBullets:|$)/);
          const bulletsMatch = editedText.match(/Bullets:\n([\s\S]*)$/);

          finalResume = {
            summary: summaryMatch ? summaryMatch[1].trim() : editedText,
            added_keywords: keywordsMatch ? keywordsMatch[1].split(',').map(s => s.trim()) : resumeUpdates.added_keywords,
            tailored_bullets: bulletsMatch ? bulletsMatch[1].split('\n').filter(b => b.trim().startsWith('•')).map(b => b.replace(/^•\s*/, '').trim()) : resumeUpdates.tailored_bullets,
            manual_override: editedText
          };
        }
      }

      const { data } = await api.post("/approvals/decide", {
        artifact,
        decision,
        job_id: jobId,
        cover_letter: finalCover,
        tailored_resume: finalResume,
        ats_score: localAtsScore,
        evidence:
          artifact === "cover_letter"
            ? "Cover letter hooks mapped to company research and resume context."
            : localEvidence,
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

  const handleReevaluate = async (editedData: any) => {
    if (!jobId) return;
    try {
      const { data } = await api.post("/approvals/reevaluate", {
        job_id: jobId,
        tailored_resume: { ...resumeUpdates, ...editedData }
      });
      setLocalAtsScore(data.ats_score);
      setLocalEvidence(data.evidence);
    } catch (err) {
      setError(getApiErrorMessage(err, "Re-evaluation failed"));
    }
  };

  const skipCard = (artifact: CardKey) => {
    setStatuses((s) => ({ ...s, [artifact]: "skipped" }));
    setMessage(
      artifact === "cover_letter"
        ? "Cover letter skipped for now — resume can still be approved."
        : "Resume skipped for now — revisit from Canvas if needed."
    );
  };

  const reviseOnCanvas = () => {
    const href =
      jobId && !isDemoJob(jobId)
        ? `/canvas?job_id=${encodeURIComponent(jobId)}`
        : "/canvas";
    router.push(href);
  };

  if (workflowStatus !== "completed" || !finalState) {
    return (
      <div className="flex-1 p-4 md:p-8 space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold tracking-tight">
            Human-in-the-Loop Approvals
          </h1>
        </div>
        <div className="rounded-xl border border-border bg-card p-12 flex flex-col items-center justify-center text-center space-y-4">
          <AlertCircle className="w-12 h-12 text-muted-foreground" />
          <div>
            <h3 className="font-semibold text-lg text-foreground">
              No Pending Approvals
            </h3>
            <p className="text-sm text-muted-foreground max-w-sm mt-1">
              Select a Tracker job on Canvas, run Simulate, then approve the
              generated resume and cover letter here. Both approvals write a
              DOCX/PDF package to your resume folder.
            </p>
            <Link
              href="/canvas"
              className="inline-flex mt-4 text-sm font-medium text-primary hover:underline"
            >
              Open Canvas →
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 p-4 md:p-8 space-y-6 overflow-y-auto os-scrollbar os-scrollbar-auto">
      <div className="flex justify-between items-center gap-3 flex-wrap">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Pending Approvals</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Job{" "}
            <span className="font-mono text-xs">{jobId || "(missing)"}</span>
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
        <div className="flex flex-col gap-3 p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-md">
          <div className="flex items-start gap-2 text-sm text-emerald-400">
            <FileStack className="h-4 w-4 mt-0.5 shrink-0" />
            <span className="break-all font-medium">Package saved successfully!</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-2">
            {/* Resume Downloads */}
            <div className="space-y-2">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Tailored Resume</h4>
              <div className="flex items-center gap-2">
                <a href={`${API_BASE_URL}/documents/package-download-job?folder=${encodeURIComponent(packagePath)}&kind=resume_pdf`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 text-xs bg-primary/10 hover:bg-primary/20 text-primary px-3 py-1.5 rounded-md transition-colors">
                  <Download className="w-3.5 h-3.5" /> PDF
                </a>
                <a href={`${API_BASE_URL}/documents/package-download-job?folder=${encodeURIComponent(packagePath)}&kind=resume_docx`} className="inline-flex items-center gap-1.5 text-xs bg-secondary hover:bg-secondary/80 text-secondary-foreground px-3 py-1.5 rounded-md transition-colors">
                  <Download className="w-3.5 h-3.5" /> DOCX
                </a>
                <button onClick={() => window.open(`${API_BASE_URL}/documents/package-download-job?folder=${encodeURIComponent(packagePath)}&kind=resume_pdf`, '_blank')} className="inline-flex items-center gap-1.5 text-xs border border-border hover:bg-muted px-3 py-1.5 rounded-md transition-colors">
                  <Eye className="w-3.5 h-3.5" /> Preview
                </button>
              </div>
            </div>
            
            {/* Cover Letter Downloads */}
            {coverNeeded && (
              <div className="space-y-2">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Cover Letter</h4>
                <div className="flex items-center gap-2">
                  <a href={`${API_BASE_URL}/documents/package-download-job?folder=${encodeURIComponent(packagePath)}&kind=cover_pdf`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 text-xs bg-primary/10 hover:bg-primary/20 text-primary px-3 py-1.5 rounded-md transition-colors">
                    <Download className="w-3.5 h-3.5" /> PDF
                  </a>
                  <a href={`${API_BASE_URL}/documents/package-download-job?folder=${encodeURIComponent(packagePath)}&kind=cover_docx`} className="inline-flex items-center gap-1.5 text-xs bg-secondary hover:bg-secondary/80 text-secondary-foreground px-3 py-1.5 rounded-md transition-colors">
                    <Download className="w-3.5 h-3.5" /> DOCX
                  </a>
                  <button onClick={() => { navigator.clipboard.writeText(coverLetter); }} className="inline-flex items-center gap-1.5 text-xs border border-border hover:bg-muted px-3 py-1.5 rounded-md transition-colors" title="Copied to clipboard when clicked">
                    <Copy className="w-3.5 h-3.5" /> Copy
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Application Readiness Summary */}
          <div className="mt-4 pt-4 border-t border-emerald-500/20">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-emerald-500 mb-3">Application Readiness & Summary</h4>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="bg-background/40 p-3 rounded-md">
                <div className="text-xs text-muted-foreground mb-1">Final ATS Match</div>
                <div className="text-2xl font-bold text-emerald-400">{localAtsScore || finalState?.ats_score || "?"}/100</div>
              </div>
              <div className="bg-background/40 p-3 rounded-md">
                <div className="text-xs text-muted-foreground mb-1">Callback Chances</div>
                <div className="text-xl font-bold text-emerald-400">
                  {(localAtsScore || finalState?.ats_score || 0) >= 85 ? "Excellent 🚀" : (localAtsScore || finalState?.ats_score || 0) >= 70 ? "Strong Fit ✨" : "Competitive"}
                </div>
              </div>
              <div className="bg-background/40 p-3 rounded-md sm:col-span-3">
                <div className="text-xs text-muted-foreground mb-1">Fit Summary</div>
                <div className="text-sm text-foreground/90">{localEvidence || finalState?.ats_recommendation || "Resume successfully tailored with keywords from the Job Description."}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 max-w-3xl">
        {coverLetter && (
          <ApprovalCard
            title="Cover Letter Draft"
            originalText=""
            proposedText={coverLetter}
            evidence="Wove your past achievements into the company's current needs and values."
            status={statuses.cover_letter}
            disabled={statuses.resume === "saving" || statuses.cover_letter === "saving"}
            confidence={88}
            confidenceLabel="Engagement Score"
            onApprove={(editedText) => decide("cover_letter", "approve", editedText)}
            onReject={() => decide("cover_letter", "reject")}
            onSkip={() => skipCard("cover_letter")}
            onRevise={reviseOnCanvas}
            isNewDraft={true}
          />
        )}
        {hasResume && (
          <ApprovalCard
            title="Tailored Resume Updates"
            originalText=""
            proposedText={resumeProposed}
            proposedData={resumeUpdates}
            evidence={localEvidence}
            status={statuses.resume}
            disabled={statuses.resume === "saving" || statuses.cover_letter === "saving"}
            confidence={localAtsScore ?? (resumeUpdates.added_keywords?.length ? 92 : undefined)}
            confidenceLabel="Relevance Match"
            onApprove={(editedText, editedData) => decide("resume", "approve", editedText, editedData)}
            onReject={() => decide("resume", "reject")}
            onReevaluate={handleReevaluate}
            onSkip={() => skipCard("resume")}
            onRevise={reviseOnCanvas}
            isNewDraft={true}
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
