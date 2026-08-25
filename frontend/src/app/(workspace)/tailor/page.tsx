"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuthStore } from "@/store/auth";
import { usePanelStore } from "@/store/panelStore";
import { useWorkflowStore, SkillImpact } from "@/hooks/useWorkflowStore";
import {
  CheckCircle, Wand2, X, AlertCircle, ArrowLeft, Download,
  Eye, RefreshCw, TrendingUp, Zap, Minus, ArrowUp, FileCode, FileText, Save
} from "lucide-react";
import Link from "next/link";
import { ResumeComparison } from "@/components/ui/ResumeComparison";
import { StructuredResumeEditor, StructuredResumeData } from "@/components/ui/StructuredResumeEditor";
import type { ParserChecks, UnifiedAtsPayload, TailorResumeRequestBody } from "@/types/resume";
import { LatexEditor } from "@/components/ui/LatexEditor";

interface BaseResume {
  name: string;
  path: string;
  role_hint: string | null;
}

function roleLabel(hint: string | null) {
  if (!hint) return "general";
  const map: Record<string, string> = {
    se: "software_engineer", fe: "frontend", be: "backend",
    fs: "fullstack", pm: "product_manager", ds: "data_science",
    mle: "ml_engineer", ui: "ui_ux", devops: "devops",
  };
  return map[hint] || hint;
}

function shortName(name: string) {
  return name
    .replace(/\.[^/.]+$/, "")
    .replace(/Jay[-_]?Bhavsar[-_]?/i, "")
    .replace(/[_-]+/g, " ")
    .trim() || name;
}

/** Circular ATS score ring */
function AtsRing({ score, label, size = 80 }: { score: number; label?: string; size?: number }) {
  const r = (size / 2) - 8;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;
  const color = score >= 80 ? "#10b981" : score >= 60 ? "#f59e0b" : "#ef4444";
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="currentColor" strokeWidth={6} className="text-muted/30" />
          <circle
            cx={size/2} cy={size/2} r={r} fill="none" stroke={color}
            strokeWidth={6} strokeLinecap="round"
            strokeDasharray={circ} strokeDashoffset={offset}
            style={{ transition: "stroke-dashoffset 0.8s ease" }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span style={{ color, fontSize: size * 0.22, fontWeight: 700, lineHeight: 1 }}>{score}</span>
        </div>
      </div>
      {label && <span className="text-xs text-muted-foreground font-medium">{label}</span>}
    </div>
  );
}


/** Impact badge for a skill */
function ImpactBadge({ level }: { level: "high" | "medium" | "low" }) {
  const cfg = {
    high: { label: "High Impact", bg: "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/30", icon: <Zap className="h-3 w-3" /> },
    medium: { label: "Medium", bg: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30", icon: <TrendingUp className="h-3 w-3" /> },
    low: { label: "Low", bg: "bg-muted text-muted-foreground border-border", icon: <Minus className="h-3 w-3" /> },
  };
  const { label, bg, icon } = cfg[level];
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full border ${bg}`}>
      {icon}{label}
    </span>
  );
}

export default function TailorPage() {
  const token = useAuthStore((s) => s.token);
  const { setPreview, closePdf } = usePanelStore();
  const {
    tailorState, setTailorState, finalState, setFinalState,
    originalResumeData, setOriginalResumeData,
  } = useWorkflowStore();
  const {
    step, jdText, jobUrl, selectedBaseResume,
    proposedSkills, approvedSkills,
    beforeAtsScore, afterAtsScore, rationale, skillImpacts,
    presentSkills, niceToHaveMissing, qualificationsMatch,
    previouslyAddedSkills, iterativeMode, iterativeTailoredText,
  } = tailorState;

  const setStep = (s: 1 | 2 | 3) => setTailorState({ step: s });
  const setJdText = (jdText: string) => setTailorState({ jdText });
  const setJobUrl = (jobUrl: string) => setTailorState({ jobUrl });
  const setSelectedBaseResume = (selectedBaseResume: string) => setTailorState({ selectedBaseResume });
  const setProposedSkills = (proposedSkills: string[]) => setTailorState({ proposedSkills });
  const setApprovedSkills = (approvedSkills: string[]) => setTailorState({ approvedSkills });

  const [baseResumes, setBaseResumes] = useState<BaseResume[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scrapeWarning, setScrapeWarning] = useState<string | null>(null);
  const [isTailoring, setIsTailoring] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [showComparison, setShowComparison] = useState(false);
  const [downloadData, setDownloadData] = useState<StructuredResumeData | null>(null);
  const [latexPreview, setLatexPreview] = useState<string | null>(null);
  const [showLatex, setShowLatex] = useState(false);
  const [loadingLatex, setLoadingLatex] = useState(false);
  const [parserChecks, setParserChecks] = useState<ParserChecks | null>(null);
  const [unifiedAts, setUnifiedAts] = useState<UnifiedAtsPayload | null>(null);
  const [structuredDraft, setStructuredDraft] = useState<StructuredResumeData>({});
  const [savingStudio, setSavingStudio] = useState(false);
  const [studioSavedId, setStudioSavedId] = useState<string | null>(null);

  const authHeaders = useCallback(
    () => ({ Authorization: `Bearer ${token}` }),
    [token]
  );

  const previewResume = useCallback(async (name: string) => {
    if (!token) return;
    try {
      const res = await fetch(
        `/api/v1/documents/library-preview?name=${encodeURIComponent(name)}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.ok) {
        const data = await res.json();
        setPreview({
          title: data.name || name,
          kind: data.kind || "unsupported",
          fileUrl: data.file_url,
          text: data.text ?? null,
          note: data.note ?? null,
        });
        setOriginalResumeData({ text: data.text ?? "", fileUrl: data.file_url ?? undefined });
      }
    } catch { /* ignore */ }
  }, [token, setPreview, setOriginalResumeData]);

  useEffect(() => {
    if (selectedBaseResume && token) previewResume(selectedBaseResume);
  }, [selectedBaseResume, token, previewResume]);

  useEffect(() => {
    if (!token) return;
    const fetchLibrary = async () => {
      try {
        const res = await fetch("/api/v1/documents/resume-library", { headers: authHeaders() });
        if (res.ok) {
          const data = await res.json();
          const files = data.files || [];
          setBaseResumes(files);
          if (files[0] && !selectedBaseResume) setSelectedBaseResume(files[0].name);
        }
      } catch { setError("Failed to load templates."); }
      finally { setLoading(false); }
    };
    fetchLibrary();
    return () => { closePdf(); };
  }, [token, authHeaders]);

  const handleAnalyzeJd = async () => {
    if (!jdText.trim() && !jobUrl.trim()) {
      setError("Paste a job description or URL first.");
      return;
    }
    setIsTailoring(true);
    setError(null);
    setScrapeWarning(null);
    try {
      const res = await fetch("/api/v1/workflows/analyze-jd-skills", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({
          job_description: jdText,
          job_url: jobUrl,
          base_resume: selectedBaseResume || baseResumes[0]?.name,
        }),
        signal: AbortSignal.timeout(300_000),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        const detail =
          typeof body.detail === "string"
            ? body.detail
            : Array.isArray(body.detail)
              ? body.detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join("; ")
              : null;
        throw new Error(detail || `Analysis failed (HTTP ${res.status})`);
      }
      const data = await res.json();
      const gap = data.skill_gap || {};
      const missing = gap.missing_skills || [];
      setProposedSkills(missing);
      setApprovedSkills([...missing]);
      setTailorState({
        beforeAtsScore: data.match_score ?? gap.match_score ?? null,
        rationale: data.rationale ?? gap.rationale ?? "",
        skillImpacts: data.skill_impacts ?? gap.skill_impacts ?? [],
        presentSkills: data.present_skills ?? gap.present_skills ?? [],
        niceToHaveMissing: data.nice_to_have_missing ?? gap.nice_to_have_missing ?? [],
        qualificationsMatch: data.qualifications_match ?? gap.qualifications_match ?? "",
      });
      if (data.unified_ats) {
        setUnifiedAts(data.unified_ats);
        setParserChecks(data.unified_ats.parser_checks || null);
      } else if (gap.parser_checks) {
        setParserChecks(gap.parser_checks);
      }
      if (data.scrape_warning) setScrapeWarning(data.scrape_warning);
      else if (data.analysis_mode === "heuristic") {
        setScrapeWarning(
          "AI was busy — used fast keyword matching. You can still tailor; re-run Analyze later for a full LLM score."
        );
      }
      setStep(2);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Analysis failed";
      if (/abort|timeout|Failed to fetch|network/i.test(msg)) {
        setError(
          "Analysis did not finish in time. Paste the full JD text (not only a URL) and retry — the app will use a fast keyword match if Token Harbor is still busy."
        );
      } else {
        setError(msg);
      }
    } finally {
      setIsTailoring(false);
    }
  };

  const handleGenerateTailored = async () => {
    setIsTailoring(true);
    setError(null);
    try {
      const body: TailorResumeRequestBody = {
        job_description: jdText,
        job_url: jobUrl,
        base_resume: selectedBaseResume || baseResumes[0]?.name,
        approved_skills: approvedSkills,
        before_ats_score: beforeAtsScore,
      };
      // Iterative mode: use the previous tailored text as the new base
      if (iterativeMode && iterativeTailoredText) {
        body.current_tailored_text = iterativeTailoredText;
      }
      const res = await fetch("/api/v1/workflows/tailor-resume", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(300_000),
      });
      if (!res.ok) {
        const b = await res.json().catch(() => ({}));
        throw new Error(typeof b.detail === "string" ? b.detail : "Tailor failed");
      }
      const data = await res.json();
      setFinalState({ tailored_resume: data.optimized_resume });
      setStructuredDraft(data.optimized_resume || {});
      setTailorState({ afterAtsScore: data.after_ats_score ?? null });
      if (data.unified_ats) {
        setUnifiedAts(data.unified_ats);
        setParserChecks(data.unified_ats.parser_checks || null);
      }
      setStep(3);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Tailor failed";
      if (/abort|timeout|Failed to fetch|network/i.test(msg)) {
        setError("Tailor timed out — retry in a moment (Token Harbor may be busy).");
      } else {
        setError(msg);
      }
    } finally {
      setIsTailoring(false);
    }
  };

  const handleSaveToStudio = async (approve = false) => {
    const payload = structuredDraft.summary ? structuredDraft : finalState?.tailored_resume;
    if (!payload || !jdText.trim()) {
      setError("Generate a tailored resume before saving to Studio.");
      return;
    }
    setSavingStudio(true);
    setError(null);
    try {
      const res = await fetch("/api/v1/resumes/studio/save-tailor", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({
          job_description: jdText,
          job_url: jobUrl || null,
          base_resume: selectedBaseResume || baseResumes[0]?.name,
          tailored_resume: payload,
          before_ats_score: beforeAtsScore,
          after_ats_score: afterAtsScore,
          unified_ats: unifiedAts,
          approve_version: approve,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(typeof body.detail === "string" ? body.detail : "Save failed");
      }
      const data = await res.json();
      setStudioSavedId(data.item_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save to Studio failed");
    } finally {
      setSavingStudio(false);
    }
  };

  const handleStructuredChange = (next: StructuredResumeData) => {
    setStructuredDraft(next);
    setFinalState({ tailored_resume: next });
  };

  const handleDownloadDocx = async (editedData?: StructuredResumeData) => {
    await downloadExport("/api/v1/documents/export/docx", editedData, "Tailored_Resume.docx");
  };

  const handleDownloadPdf = async (editedData?: StructuredResumeData) => {
    await downloadExport("/api/v1/documents/export/pdf", editedData, "Tailored_Resume.pdf");
  };

  const handleDownloadTex = async (editedData?: StructuredResumeData) => {
    await downloadExport("/api/v1/documents/export/tex", editedData, "Tailored_Resume.tex");
  };

  const downloadExport = async (
    url: string,
    editedData: StructuredResumeData | undefined,
    filename: string
  ) => {
    setIsDownloading(true);
    try {
      const payload = editedData || finalState?.tailored_resume || {};
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`Failed to export ${filename.split(".").pop()}`);
      const blob = await res.blob();
      const objectUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = objectUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      URL.revokeObjectURL(objectUrl);
      document.body.removeChild(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setIsDownloading(false);
    }
  };

  const loadLatexPreview = async () => {
    const payload = finalState?.tailored_resume;
    if (!payload) return;
    setLoadingLatex(true);
    try {
      const res = await fetch("/api/v1/documents/export/tex", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Could not generate LaTeX preview");
      setLatexPreview(await res.text());
      setShowLatex(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "LaTeX preview failed");
    } finally {
      setLoadingLatex(false);
    }
  };

  /** Enter iterative mode — go back to step 2 but use current tailored as base */
  const handleImproveFurther = () => {
    const opt = finalState?.tailored_resume;
    if (!opt) return;
    const tailoredText = [
      opt.summary ?? "",
      ...(opt.tailored_bullets ?? []),
      ...(opt.added_keywords ?? []),
    ].filter(Boolean).join("\n");

    // Mark all approved skills from this round as "previously added"
    const newPrev = Array.from(new Set([...previouslyAddedSkills, ...approvedSkills]));

    setTailorState({
      iterativeMode: true,
      iterativeTailoredText: tailoredText,
      previouslyAddedSkills: newPrev,
      afterAtsScore: null,
      approvedSkills: [],
    });
    // Re-analyze with the tailored text as base to find remaining gaps
    handleAnalyzeJdWithText(tailoredText);
  };

  const handleAnalyzeJdWithText = async (resumeText: string) => {
    setIsTailoring(true);
    setError(null);
    try {
      const res = await fetch("/api/v1/workflows/analyze-jd-skills", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({
          job_description: jdText,
          job_url: jobUrl,
          base_resume: selectedBaseResume || baseResumes[0]?.name,
          resume_text: resumeText,
        }),
        signal: AbortSignal.timeout(300_000),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(
          typeof body.detail === "string" ? body.detail : "Re-analysis failed"
        );
      }
      const data = await res.json();
      const gap = data.skill_gap || {};
      const missing = (gap.missing_skills || []).filter(
        (s: string) => !previouslyAddedSkills.includes(s)
      );
      setProposedSkills(missing);
      setApprovedSkills([...missing]);
      setTailorState({
        beforeAtsScore: afterAtsScore, // carry forward last round's after as new before
        rationale: data.rationale ?? gap.rationale ?? "",
        skillImpacts: (data.skill_impacts ?? gap.skill_impacts ?? []).filter(
          (si: SkillImpact) => !previouslyAddedSkills.includes(si.skill)
        ),
      });
      setStep(2);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Re-analysis failed");
    } finally {
      setIsTailoring(false);
    }
  };

  const handleApproveAndPreview = () => {
    const data = finalState?.tailored_resume;
    if (!data) return;
    setDownloadData(data);
    setShowComparison(true);
  };

  const handleDownloadNow = async () => {
    if (downloadData) {
      await handleDownloadDocx(downloadData);
      setShowComparison(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <span className="h-8 w-8 border-4 border-primary/30 border-t-primary rounded-full animate-spin" />
      </div>
    );
  }

  const atsDelta = (beforeAtsScore !== null && afterAtsScore !== null)
    ? afterAtsScore - beforeAtsScore : null;

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden relative">
      <header className="border-b bg-card/80 backdrop-blur sticky top-0 z-20 px-4 md:px-6 py-3 md:py-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 md:gap-4 min-w-0">
          <Link
            href="/resumes"
            aria-label="Back to Resume Studio"
            className="p-2 rounded-md hover:bg-muted text-muted-foreground transition-colors shrink-0"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div className="min-w-0">
            <h1 className="text-xl md:text-2xl font-bold tracking-tight truncate">Tailor Resume</h1>
            <p className="text-xs md:text-sm text-muted-foreground" aria-current="step">
              {step === 1 && "Step 1 of 3 — Template & job description"}
              {step === 2 && `Step 2 of 3 — ${iterativeMode ? "Improve further" : "Review missing skills"}`}
              {step === 3 && "Step 3 of 3 — Edit, save & download"}
            </p>
          </div>
        </div>
        {step >= 2 && beforeAtsScore !== null && (
          <div className="flex items-center gap-2 text-sm shrink-0">
            <span className="text-muted-foreground">ATS before</span>
            <span className={`font-bold tabular-nums ${beforeAtsScore >= 80 ? "text-emerald-500" : beforeAtsScore >= 60 ? "text-amber-500" : "text-red-500"}`}>
              {beforeAtsScore}
            </span>
          </div>
        )}
      </header>

      <main className="flex-1 overflow-y-auto p-6 md:p-10 flex justify-center">
        <div className="w-full max-w-2xl space-y-8">
          {error && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm flex items-start gap-2">
              <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
              <span>{error}</span>
              <button type="button" className="ml-auto" onClick={() => setError(null)}>
                <X className="h-4 w-4" />
              </button>
            </div>
          )}

          {/* ── STEP 1 ── */}
          {step === 1 && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="space-y-2">
                <label className="text-sm font-semibold">Master template</label>
                <p className="text-xs text-muted-foreground mb-2">
                  Select a base resume. Preview appears in the side panel when available.
                </p>
                {baseResumes.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-border p-6 text-center space-y-3">
                    <p className="text-sm font-medium">No templates in your library</p>
                    <p className="text-xs text-muted-foreground">
                      Upload a PDF or DOCX in Resume Studio, then come back to tailor.
                    </p>
                    <Link
                      href="/resumes"
                      className="inline-flex items-center justify-center px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium"
                    >
                      Open Resume Studio
                    </Link>
                  </div>
                ) : (
                  <select
                    value={selectedBaseResume}
                    onChange={(e) => setSelectedBaseResume(e.target.value)}
                    className="w-full p-3.5 rounded-lg border bg-card text-sm shadow-sm transition-all focus:ring-2 focus:ring-primary/20"
                  >
                    {baseResumes.map((r) => (
                      <option key={r.name} value={r.name}>
                        [{roleLabel(r.role_hint)}] {shortName(r.name)}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div className="space-y-2">
                <label className="text-sm font-semibold">Job URL (Optional)</label>
                <input
                  type="url" value={jobUrl} onChange={(e) => setJobUrl(e.target.value)}
                  className="w-full p-3.5 rounded-lg border bg-card text-sm shadow-sm transition-all focus:ring-2 focus:ring-primary/20"
                  placeholder="https://..."
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-semibold flex items-center justify-between">
                  <span>Job description</span>
                  <span className="text-xs font-normal text-muted-foreground">Optional if URL provided</span>
                </label>
                <textarea
                  value={jdText} onChange={(e) => setJdText(e.target.value)}
                  className="w-full h-48 p-3.5 rounded-lg border bg-card text-sm font-mono shadow-sm resize-y transition-all focus:ring-2 focus:ring-primary/20"
                  placeholder="Paste the Job Description here..."
                />
              </div>

              <div className="pt-4 flex justify-end">
                <button
                  type="button" onClick={handleAnalyzeJd}
                  disabled={isTailoring || (!jdText.trim() && !jobUrl.trim())}
                  className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-lg bg-primary text-primary-foreground font-semibold shadow-md hover:bg-primary/90 disabled:opacity-50 transition-all hover:-translate-y-0.5 active:translate-y-0"
                >
                  {isTailoring ? (
                    <span className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : <Wand2 className="h-5 w-5" />}
                  {isTailoring ? "Analyzing (may take 1–2 min)…" : "Analyze JD & Score Resume"}
                </button>
              </div>
            </div>
          )}

          {/* ── STEP 2 ── */}
          {step === 2 && (
            <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-500">
              {/* Scrape degradation warning */}
              {scrapeWarning && (
                <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 mt-0.5 shrink-0 text-amber-500" />
                  <div className="flex-1">
                    <p className="font-semibold text-amber-600 dark:text-amber-400">URL could not be scraped</p>
                    <p className="text-muted-foreground mt-0.5">{scrapeWarning}</p>
                  </div>
                  <button type="button" onClick={() => setScrapeWarning(null)} className="text-muted-foreground hover:text-foreground shrink-0">
                    <X className="h-4 w-4" />
                  </button>
                </div>
              )}
              {/* ATS Before Score */}
              {beforeAtsScore !== null && (
                <div className="rounded-xl border border-border bg-card p-5 flex items-center gap-6">
                  <AtsRing score={beforeAtsScore} label={iterativeMode ? "Current ATS" : "ATS Score"} size={88} />
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-base">
                      {iterativeMode ? "Iterating on tailored resume" : "Resume Match Analysis"}
                    </p>
                    <p className="text-sm text-muted-foreground mt-1 leading-relaxed">{rationale}</p>
                    {iterativeMode && previouslyAddedSkills.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {previouslyAddedSkills.map((s) => (
                          <span key={s} className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
                            ✓ {s}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              <div className="space-y-2">
                <h3 className="font-semibold text-lg">
                  {proposedSkills.length > 0
                    ? `${proposedSkills.length} Missing Skill${proposedSkills.length > 1 ? "s" : ""} Found`
                    : "Perfect Match!"}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {proposedSkills.length > 0
                    ? "Select the skills you have experience with — we'll weave them naturally into your resume bullets."
                    : "Your resume already covers all key skills in the JD."}
                </p>
              </div>

              {proposedSkills.length === 0 ? (
                <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-8 text-center flex flex-col items-center gap-3">
                  <CheckCircle className="h-12 w-12 text-emerald-500" />
                  <div>
                    <p className="font-semibold text-emerald-600 dark:text-emerald-400">Great Match!</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      Click Generate to create the tailored version.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="grid gap-3 p-1">
                  {proposedSkills.map((skill) => {
                    const impact = skillImpacts.find((si) => si.skill === skill);
                    const checked = approvedSkills.includes(skill);
                    return (
                      <label
                        key={skill}
                        className={`flex items-start gap-4 p-4 rounded-xl border cursor-pointer transition-all ${
                          checked ? "bg-primary/5 border-primary shadow-sm" : "bg-card hover:bg-muted/50 border-border"
                        }`}
                      >
                        <input
                          type="checkbox" checked={checked}
                          onChange={(e) => {
                            if (e.target.checked) setApprovedSkills([...approvedSkills, skill]);
                            else setApprovedSkills(approvedSkills.filter((s) => s !== skill));
                          }}
                          className="h-5 w-5 mt-0.5 rounded-md border-muted-foreground/30 text-primary focus:ring-primary/20"
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-sm font-medium">{skill}</span>
                            {impact && <ImpactBadge level={impact.level} />}
                          </div>
                          {impact?.reason && (
                            <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{impact.reason}</p>
                          )}
                        </div>
                      </label>
                    );
                  })}
                </div>
              )}

              {/* Select all / none shortcuts */}
              {proposedSkills.length > 1 && (
                <div className="flex gap-3 text-xs text-muted-foreground">
                  <button type="button" onClick={() => setApprovedSkills([...proposedSkills])}
                    className="hover:text-foreground underline-offset-2 hover:underline">
                    Select all
                  </button>
                  <button type="button" onClick={() => setApprovedSkills([])}
                    className="hover:text-foreground underline-offset-2 hover:underline">
                    Clear all
                  </button>
                </div>
              )}

              {/* ✅ Skills already present in the resume */}
              {presentSkills.length > 0 && (
                <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 mb-3 flex items-center gap-1.5">
                    <CheckCircle className="h-3.5 w-3.5" /> Already in your resume ({presentSkills.length})
                  </p>
                  <div className="space-y-2">
                    {presentSkills.map((ps) => (
                      <div key={ps.skill} className="flex items-start gap-2">
                        <span className={`shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded border mt-0.5 ${
                          ps.confidence === "strong"
                            ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30"
                            : "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30"
                        }`}>
                          {ps.confidence === "strong" ? "✓ STRONG" : "~ PARTIAL"}
                        </span>
                        <div>
                          <span className="text-sm font-medium">{ps.skill}</span>
                          {ps.note && <p className="text-xs text-muted-foreground mt-0.5">{ps.note}</p>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 💡 Nice-to-have missing */}
              {niceToHaveMissing.length > 0 && (
                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400 mb-3 flex items-center gap-1.5">
                    <TrendingUp className="h-3.5 w-3.5" /> Nice-to-have gaps ({niceToHaveMissing.length})
                  </p>
                  <div className="space-y-2">
                    {niceToHaveMissing.map((nth) => (
                      <div key={nth.skill} className="flex items-start gap-2">
                        <span className="shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded border bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30 mt-0.5">
                          BONUS
                        </span>
                        <div>
                          <span className="text-sm font-medium">{nth.skill}</span>
                          <p className="text-xs text-muted-foreground mt-0.5">{nth.reason}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 🎓 Qualifications */}
              {qualificationsMatch && (
                <div className="rounded-lg border border-border bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
                  <span className="font-semibold text-foreground">Qualifications: </span>{qualificationsMatch}
                </div>
              )}


              <div className="pt-6 flex items-center justify-between border-t border-border mt-4">
                <button
                  type="button"
                  onClick={() => {
                    setTailorState({ iterativeMode: false, iterativeTailoredText: "", previouslyAddedSkills: [] });
                    setStep(1);
                  }}
                  className="px-5 py-2.5 rounded-lg border bg-background hover:bg-muted font-medium transition-colors"
                >
                  Back
                </button>
                <button
                  type="button" onClick={handleGenerateTailored} disabled={isTailoring}
                  className="inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-lg bg-emerald-600 text-white font-semibold shadow-md hover:bg-emerald-500 disabled:opacity-50 transition-all hover:-translate-y-0.5 active:translate-y-0"
                >
                  {isTailoring ? (
                    <span className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : <Wand2 className="h-5 w-5" />}
                  {isTailoring ? "Generating & Scoring…" : "Generate Tailored Resume"}
                </button>
              </div>
            </div>
          )}

          {/* ── STEP 3 ── */}
          {step === 3 && (
            <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-500">
              {/* ATS Before → After delta card */}
              {beforeAtsScore !== null && afterAtsScore !== null && (
                <div className="rounded-xl border border-border bg-card p-5">
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-4">ATS Score Impact</p>
                  <div className="flex items-center justify-center gap-6 md:gap-10">
                    <div className="flex flex-col items-center gap-1">
                      <AtsRing score={beforeAtsScore} size={80} />
                      <span className="text-xs text-muted-foreground">Before</span>
                    </div>
                    <div className="flex flex-col items-center gap-1">
                      <ArrowUp className="h-6 w-6 text-emerald-500" />
                      {atsDelta !== null && (
                        <span className={`text-sm font-bold ${atsDelta > 0 ? "text-emerald-500" : "text-muted-foreground"}`}>
                          {atsDelta > 0 ? `+${atsDelta}` : atsDelta}
                        </span>
                      )}
                    </div>
                    <div className="flex flex-col items-center gap-1">
                      <AtsRing score={afterAtsScore} size={80} />
                      <span className="text-xs text-muted-foreground">After</span>
                    </div>
                  </div>
                  {atsDelta !== null && atsDelta > 0 && (
                    <p className="text-center text-sm text-muted-foreground mt-3">
                      Your resume match score improved by <strong className="text-emerald-500">{atsDelta} points</strong>.
                    </p>
                  )}
                  {afterAtsScore < 75 && (
                    <p className="text-center text-xs text-amber-600 dark:text-amber-400 mt-2">
                      Score is below 75 — consider clicking <strong>Improve Further</strong> to add more skills.
                    </p>
                  )}
                </div>
              )}

              {/* Parser / ATS checks */}
              {parserChecks && (
                <div className="rounded-xl border border-border bg-card p-4 space-y-2 text-sm">
                  <p className="font-semibold text-sm">ATS parser checks</p>
                  <div className="flex flex-wrap gap-2 text-xs">
                    {parserChecks.has_summary_section && <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600">Summary ✓</span>}
                    {parserChecks.has_experience_section && <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600">Experience ✓</span>}
                    {parserChecks.has_skills_section && <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600">Skills ✓</span>}
                    <span className="px-2 py-0.5 rounded-full bg-muted text-muted-foreground">
                      Keyword match {Math.round((parserChecks.keyword_density || 0) * 100)}%
                    </span>
                    <span className="px-2 py-0.5 rounded-full bg-muted text-muted-foreground">
                      Parser score {parserChecks.overall_parser_score}/100
                    </span>
                  </div>
                  {((parserChecks.warnings?.length ?? 0) > 0) && (
                    <ul className="text-xs text-amber-600 dark:text-amber-400 list-disc pl-4 space-y-1">
                      {(parserChecks.warnings ?? []).map((w: string, i: number) => <li key={i}>{w}</li>)}
                    </ul>
                  )}
                  {((parserChecks.suggestions?.length ?? 0) > 0) && (
                    <ul className="text-xs text-muted-foreground list-disc pl-4 space-y-1">
                      {(parserChecks.suggestions ?? []).slice(0, 3).map((s: string, i: number) => <li key={i}>{s}</li>)}
                    </ul>
                  )}
                </div>
              )}

              {/* Structured editor */}
              {finalState?.tailored_resume && (
                <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm p-4">
                  <p className="font-semibold text-sm mb-3">Edit sections before download</p>
                  <StructuredResumeEditor
                    value={structuredDraft.summary ? structuredDraft : finalState.tailored_resume}
                    onChange={handleStructuredChange}
                  />
                </div>
              )}

              {/* Tailored content preview (read-only summary) */}
              {finalState?.tailored_resume && (
                <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
                  <div className="flex items-center gap-2 p-4 border-b border-border bg-muted/40">
                    <CheckCircle className="h-4 w-4 text-emerald-500" />
                    <span className="font-semibold text-sm">Tailored Content</span>
                    {(finalState.tailored_resume.added_keywords?.length ?? 0) > 0 && (
                      <span className="ml-auto text-xs text-muted-foreground">
                        {(finalState.tailored_resume.added_keywords ?? []).length} keywords added
                      </span>
                    )}
                  </div>
                  <div className="p-5 space-y-4 max-h-48 overflow-y-auto">
                    {finalState.tailored_resume.summary && (
                      <div>
                        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">Summary</p>
                        <p className="text-sm leading-relaxed whitespace-pre-wrap">{finalState.tailored_resume.summary}</p>
                      </div>
                    )}
                    {(finalState.tailored_resume.tailored_bullets?.length ?? 0) > 0 && (
                      <div>
                        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">Tailored Bullets</p>
                        <ul className="text-sm space-y-1.5 list-disc pl-4">
                          {(finalState.tailored_resume.tailored_bullets ?? []).map((b: string, i: number) => (
                            <li key={i} className="leading-relaxed">{b}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {(finalState.tailored_resume.added_keywords?.length ?? 0) > 0 && (
                      <div>
                        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">Added Keywords</p>
                        <div className="flex flex-wrap gap-1.5">
                          {(finalState.tailored_resume.added_keywords ?? []).map((k: string, i: number) => (
                            <span key={i} className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">{k}</span>
                          ))}
                        </div>
                      </div>
                    )}
                    {previouslyAddedSkills.length > 0 && (
                      <div>
                        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">Previously Added (Round 1+)</p>
                        <div className="flex flex-wrap gap-1.5">
                          {previouslyAddedSkills.map((k, i) => (
                            <span key={i} className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">✓ {k}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Action buttons */}
              <div className="flex flex-col gap-3 pt-4 border-t border-border mt-2">
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setTailorState({ iterativeMode: false, iterativeTailoredText: "", previouslyAddedSkills: [] });
                      setStep(1);
                    }}
                    className="px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground"
                  >
                    Start over
                  </button>
                  <div className="flex-1" />
                  <button
                    type="button"
                    onClick={() => handleSaveToStudio(false)}
                    disabled={savingStudio}
                    className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md border border-border text-sm font-medium hover:bg-muted disabled:opacity-50"
                  >
                    {savingStudio ? (
                      <span className="h-4 w-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                    ) : (
                      <Save className="h-4 w-4" />
                    )}
                    Save to Studio
                  </button>
                  {studioSavedId && (
                    <Link href="/resumes" className="text-xs text-emerald-600 dark:text-emerald-400 hover:underline">
                      Open Studio
                    </Link>
                  )}
                  <button
                    type="button"
                    onClick={handleImproveFurther}
                    disabled={isTailoring}
                    className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md border border-border text-sm font-medium hover:bg-muted disabled:opacity-50"
                  >
                    <RefreshCw className="h-4 w-4" />
                    Improve
                  </button>
                  <button
                    type="button"
                    onClick={handleApproveAndPreview}
                    className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md border border-border text-sm font-medium hover:bg-muted"
                  >
                    <Eye className="h-4 w-4" />
                    Compare
                  </button>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => (showLatex ? setShowLatex(false) : loadLatexPreview())}
                    disabled={loadingLatex}
                    className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md border border-border text-sm font-medium hover:bg-muted"
                  >
                    {loadingLatex ? (
                      <span className="h-4 w-4 border-2 border-muted-foreground/30 border-t-foreground rounded-full animate-spin" />
                    ) : (
                      <FileCode className="h-4 w-4" />
                    )}
                    {showLatex ? "Hide LaTeX" : "Edit LaTeX"}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDownloadTex()}
                    disabled={isDownloading}
                    className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md border border-border text-sm font-medium hover:bg-muted disabled:opacity-50"
                  >
                    .tex
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDownloadPdf()}
                    disabled={isDownloading}
                    className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md border border-emerald-600/40 text-emerald-600 dark:text-emerald-400 text-sm font-medium hover:bg-emerald-500/10 disabled:opacity-50"
                  >
                    <FileText className="h-4 w-4" />
                    PDF
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDownloadDocx()}
                    disabled={isDownloading}
                    className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700 disabled:opacity-50"
                  >
                    {isDownloading ? (
                      <span className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                      <Download className="h-4 w-4" />
                    )}
                    DOCX
                  </button>
                </div>
              </div>

              {showLatex && latexPreview && (
                <LatexEditor
                  initialTex={latexPreview}
                  authHeaders={authHeaders}
                  onClose={() => setShowLatex(false)}
                />
              )}
            </div>
          )}
        </div>
      </main>

      {/* Resume Comparison Modal — rendered at root level */}
      {showComparison && originalResumeData && downloadData && (
        <ResumeComparison
          original={originalResumeData}
          updated={{
            text: [
              downloadData.summary,
              ...(downloadData.tailored_bullets || []),
              ...(downloadData.added_keywords || []),
            ].filter(Boolean).join("\n\n"),
          }}
          onClose={() => setShowComparison(false)}
          onDownload={handleDownloadNow}
        />
      )}
    </div>
  );
}
