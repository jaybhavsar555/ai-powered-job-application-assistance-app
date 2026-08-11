"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Send,
  Loader2,
  Download,
  Mail,
  ExternalLink,
  FileText,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";
import {
  PageMessageBanner,
  type PageMessage,
} from "@/components/ui/PageMessageBanner";

type QuickApplyResult = {
  parsed: {
    role_title: string;
    company_name: string;
    contact_email: string | null;
    contact_name: string | null;
    linkedin_post_url?: string | null;
    linkedin_profile_url?: string | null;
    required_skills?: string[];
    location?: string | null;
  };
  job_id: string;
  application_id?: string | null;
  message_id?: string | null;
  email_draft: { to: string | null; subject: string; body: string };
  mailto?: string | null;
  gmail_url?: string | null;
  resume_download_url?: string | null;
  warnings?: string[];
  next_steps?: string[];
  note?: string;
};

const EXAMPLE_HINT =
  "Paste a LinkedIn hiring post (or JD). We’ll extract the email, tailor your resume, and draft the reply.";

export default function QuickApplyPage() {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const [postText, setPostText] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactName, setContactName] = useState("");
  const [candidateName, setCandidateName] = useState(
    () => user?.email?.split("@")[0]?.replace(/\./g, " ") || ""
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pageMessage, setPageMessage] = useState<PageMessage | null>(null);
  const [result, setResult] = useState<QuickApplyResult | null>(null);
  const [draftSubject, setDraftSubject] = useState("");
  const [draftBody, setDraftBody] = useState("");

  const run = async () => {
    setError(null);
    setResult(null);
    if (postText.trim().length < 40) {
      setError("Paste the full hiring post (or JD text).");
      return;
    }
    try {
      setBusy(true);
      const res = await fetch("/api/v1/jobs/quick-apply-from-post", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          post_text: postText,
          source_url: sourceUrl || null,
          contact_email: contactEmail || null,
          contact_name: contactName || null,
          candidate_name: candidateName || null,
          run_package: true,
        }),
        // Long LLM tailor — do not abort early
        signal: AbortSignal.timeout(300_000),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail =
          typeof data.detail === "string"
            ? data.detail
            : Array.isArray(data.detail)
              ? data.detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join("; ")
              : null;
        setError(
          detail ||
            `Quick apply failed (HTTP ${res.status}). Is Docker API up on :8001?`
        );
        return;
      }
      setResult(data as QuickApplyResult);
      setDraftSubject(data.email_draft?.subject || "");
      setDraftBody(data.email_draft?.body || "");
      if (data.parsed?.contact_email && !contactEmail) {
        setContactEmail(data.parsed.contact_email);
      }
      if (data.parsed?.contact_name && !contactName) {
        setContactName(data.parsed.contact_name);
      }
    } catch (err) {
      console.error(err);
      const msg = err instanceof Error ? err.message : String(err);
      if (/abort|timeout|ECONNRESET|Failed to fetch|network/i.test(msg)) {
        setError(
          "Connection dropped while tailoring (often slow Ollama or empty data/resumes). " +
            "Confirm Docker API is up, put a PDF in data/resumes/, then retry."
        );
      } else {
        setError("Network error running quick apply");
      }
    } finally {
      setBusy(false);
    }
  };

  const downloadResume = async (): Promise<boolean> => {
    if (!result?.resume_download_url || !token) return false;
    const res = await fetch(result.resume_download_url, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      setPageMessage({
        tone: "error",
        title: "Download failed",
        detail:
          "Package may be missing. Add a resume under data/resumes, run Quick Apply again, then download.",
      });
      return false;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `tailored_resume_${result.parsed.role_title.replace(/\s+/g, "_")}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
    return true;
  };

  const openGmail = () => {
    const to = contactEmail || result?.email_draft?.to || "";
    if (!to) {
      setPageMessage({
        tone: "info",
        title: "Recipient email needed",
        detail: "Add a contact email above, then open Gmail.",
      });
      return;
    }
    const url =
      "https://mail.google.com/mail/?view=cm&fs=1" +
      `&to=${encodeURIComponent(to)}` +
      `&su=${encodeURIComponent(draftSubject)}` +
      `&body=${encodeURIComponent(draftBody)}`;
    window.open(url, "_blank");
  };

  /** Browsers cannot auto-attach PDFs to Gmail/mailto — download then open compose. */
  const downloadPdfAndOpenGmail = async () => {
    const ok = await downloadResume();
    if (!ok) return;
    openGmail();
  };

  return (
    <div className="p-4 md:p-8 max-w-4xl mx-auto space-y-8 animate-in fade-in duration-500">
      <div>
        <h1 className="text-4xl font-bold tracking-tight mb-2">Quick Apply</h1>
        <p className="text-muted-foreground text-lg max-w-2xl">{EXAMPLE_HINT}</p>
      </div>

      {pageMessage && (
        <PageMessageBanner
          message={pageMessage}
          onDismiss={() => setPageMessage(null)}
        />
      )}

      <div className="rounded-xl border bg-card p-6 space-y-4">
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">LinkedIn post URL (optional)</span>
          <input
            value={sourceUrl}
            onChange={(e) => setSourceUrl(e.target.value)}
            placeholder="https://www.linkedin.com/posts/…"
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
          />
        </label>

        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Paste hiring post / JD</span>
          <textarea
            value={postText}
            onChange={(e) => setPostText(e.target.value)}
            rows={14}
            placeholder="Immediate Hiring | Mobile App Developer…&#10;…&#10;📧 someone@email.com"
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm font-mono leading-relaxed"
          />
        </label>

        <div className="grid md:grid-cols-3 gap-3">
          <label className="block space-y-1">
            <span className="text-xs text-muted-foreground">Your name (sign-off)</span>
            <input
              value={candidateName}
              onChange={(e) => setCandidateName(e.target.value)}
              className="w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-sm"
            />
          </label>
          <label className="block space-y-1">
            <span className="text-xs text-muted-foreground">Contact email override</span>
            <input
              type="email"
              value={contactEmail}
              onChange={(e) => setContactEmail(e.target.value)}
              placeholder="auto from paste"
              className="w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-sm"
            />
          </label>
          <label className="block space-y-1">
            <span className="text-xs text-muted-foreground">Contact name override</span>
            <input
              value={contactName}
              onChange={(e) => setContactName(e.target.value)}
              placeholder="auto from paste"
              className="w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-sm"
            />
          </label>
        </div>

        {error && (
          <p className="text-sm text-red-500 flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
            {error}
          </p>
        )}

        <button
          type="button"
          onClick={run}
          disabled={busy || !token}
          className="inline-flex items-center gap-2 rounded-md bg-primary text-primary-foreground px-4 py-2.5 text-sm font-medium disabled:opacity-50"
        >
          {busy ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <FileText className="h-4 w-4" />
          )}
          {busy ? "Tailoring resume + drafting email…" : "Tailor resume & draft email"}
        </button>
      </div>

      {result && (
        <div className="rounded-xl border bg-card p-6 space-y-5">
          <div className="flex items-start gap-2">
            <CheckCircle2 className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
            <div>
              <h2 className="font-semibold text-lg">
                {result.parsed.role_title}
                {result.parsed.location ? ` · ${result.parsed.location}` : ""}
              </h2>
              <p className="text-sm text-muted-foreground">
                To: {result.parsed.contact_email || "—"} ·{" "}
                {result.parsed.contact_name || "Hiring contact"}
              </p>
            </div>
          </div>

          {result.warnings && result.warnings.length > 0 && (
            <ul className="text-sm text-amber-700 dark:text-amber-400 space-y-1 list-disc pl-5">
              {result.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          )}

          <p className="text-xs text-muted-foreground">{result.note}</p>
          <p className="text-xs rounded-md border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-amber-900 dark:text-amber-200">
            Gmail cannot auto-attach PDFs from the browser. Use{" "}
            <strong className="font-medium">Download PDF &amp; open Gmail</strong>, then
            attach the downloaded file in compose (paperclip).
          </p>

          <div className="space-y-2">
            <label className="block space-y-1">
              <span className="text-xs font-medium text-muted-foreground">Subject</span>
              <input
                value={draftSubject}
                onChange={(e) => setDraftSubject(e.target.value)}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm font-medium"
              />
            </label>
            <label className="block space-y-1">
              <span className="text-xs font-medium text-muted-foreground">Body</span>
              <textarea
                value={draftBody}
                onChange={(e) => setDraftBody(e.target.value)}
                rows={10}
                className="w-full rounded-md border border-border bg-muted/30 px-3 py-2 text-sm leading-relaxed"
              />
            </label>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={downloadPdfAndOpenGmail}
              disabled={!result.resume_download_url}
              className="inline-flex items-center gap-1.5 rounded-md bg-primary text-primary-foreground px-3 py-2 text-sm disabled:opacity-40"
            >
              <Mail className="h-4 w-4" /> Download PDF &amp; open Gmail
            </button>
            <button
              type="button"
              onClick={() => void downloadResume()}
              disabled={!result.resume_download_url}
              className="inline-flex items-center gap-1.5 rounded-md border px-3 py-2 text-sm hover:bg-muted disabled:opacity-40"
            >
              <Download className="h-4 w-4" /> Download only
            </button>
            <button
              type="button"
              onClick={openGmail}
              className="inline-flex items-center gap-1.5 rounded-md border px-3 py-2 text-sm hover:bg-muted"
            >
              <Mail className="h-4 w-4" /> Open Gmail only
            </button>
            {result.parsed.linkedin_post_url && (
              <a
                href={result.parsed.linkedin_post_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 rounded-md border px-3 py-2 text-sm hover:bg-muted"
              >
                <ExternalLink className="h-4 w-4" /> LinkedIn post
              </a>
            )}
            {result.message_id && (
              <Link
                href="/outreach"
                className="inline-flex items-center gap-1.5 rounded-md border px-3 py-2 text-sm hover:bg-muted"
              >
                <Send className="h-4 w-4" /> Open in Outreach
              </Link>
            )}
            {result.job_id && (
              <Link
                href={`/canvas?job_id=${encodeURIComponent(result.job_id)}`}
                className="inline-flex items-center gap-1.5 rounded-md border px-3 py-2 text-sm hover:bg-muted"
              >
                Canvas
              </Link>
            )}
          </div>

          {result.next_steps && (
            <ol className="text-sm text-muted-foreground list-decimal pl-5 space-y-1">
              {result.next_steps.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  );
}
