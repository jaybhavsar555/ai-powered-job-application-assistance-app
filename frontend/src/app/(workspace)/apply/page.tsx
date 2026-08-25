"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Briefcase,
  Check,
  CheckCircle2,
  Download,
  ExternalLink,
  FileStack,
  FileText,
  Loader2,
  Lock,
  Mail,
  Play,
  Send,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";
import {
  PageMessage,
  PageMessageBanner,
  messageFromError,
} from "@/components/ui/PageMessageBanner";

interface FormField {
  key: string;
  label: string;
  value: string;
  status: string;
  locked?: boolean;
  group?: string;
  hint?: string;
  company?: string;
  title?: string;
  dates?: string;
}

interface ApplyStep {
  id: string;
  title: string;
  desc: string;
  status: string;
  showcase?: string;
  index: number;
}

interface DocsInfo {
  ats_score?: number | null;
  matching_skills?: string[];
  missing_skills?: string[];
  required_skills?: string[];
  present_skills?: string[];
  required_skill_count?: number;
  present_skill_count?: number;
  has_tailored_resume?: boolean;
  has_cover_letter?: boolean;
  cover_letter?: string | null;
  cover_letter_preview?: string | null;
  resume_preview?: string | null;
  job_description?: string | null;
  package_ready?: boolean;
  package?: { folder?: string; files?: string[] } | null;
  canvas_href?: string;
  approvals_href?: string;
  hint?: string;
}

interface ApplySession {
  session_id: string;
  application_id: string;
  job_id: string;
  mode: string;
  mode_note: string;
  status: string;
  current_step_index: number;
  company: string;
  role_title?: string | null;
  job_url?: string | null;
  steps: ApplyStep[];
  form_fields: FormField[];
  docs?: DocsInfo;
  browser?: {
    opened?: boolean;
    url?: string | null;
    fill_progress?: number;
    last_action?: string | null;
  };
  receipt?: {
    submitted_at?: string;
    company?: string;
    role_title?: string | null;
    job_url?: string | null;
    fields?: { label?: string; value?: string; status?: string }[];
    field_count?: number;
    filled_count?: number;
    resume?: string;
    ats_score?: number | null;
    cover_letter?: boolean;
    note?: string;
  };
  follow_up?: { scheduled?: boolean; note?: string } | null;
  stage?: string;
}

type StudioTab = "form" | "resume" | "cover" | "job";

function fieldByKey(fields: FormField[], key: string): FormField | undefined {
  return fields.find((f) => f.key === key);
}

function skillMatched(skill: string, present: string[]): boolean {
  const needle = skill.toLowerCase();
  return present.some(
    (p) => p.toLowerCase() === needle || p.toLowerCase().includes(needle)
  );
}

export default function ApplyStudioPage() {
  const token = useAuthStore((s) => s.token);
  const router = useRouter();
  const [session, setSession] = useState<ApplySession | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<PageMessage | null>(null);
  const [jobs, setJobs] = useState<
    { id: string; role_title: string | null; company: string }[]
  >([]);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [studioTab, setStudioTab] = useState<StudioTab>("form");
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const params =
    typeof window !== "undefined"
      ? new URLSearchParams(window.location.search)
      : null;
  const jobIdParam = params?.get("job_id") || null;
  const appIdParam = params?.get("application_id") || null;

  const authHeaders = useCallback(
    () => ({
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    }),
    [token]
  );

  const syncDrafts = useCallback((data: ApplySession) => {
    const next: Record<string, string> = {};
    for (const f of data.form_fields || []) {
      next[f.key] = f.value ?? "";
    }
    setDrafts(next);
  }, []);

  const startSession = useCallback(
    async (body: {
      job_id?: string;
      application_id?: string;
      reset?: boolean;
    }) => {
      setBusy(true);
      setMessage(null);
      try {
        const res = await fetch("/api/v1/apply-sessions/start", {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify(body),
        });
        if (!res.ok) {
          const b = await res.json().catch(() => ({}));
          throw new Error(
            typeof b.detail === "string" ? b.detail : "Failed to start session"
          );
        }
        const data = (await res.json()) as ApplySession;
        setSession(data);
        syncDrafts(data);
        if (data.status === "completed") setStudioTab("form");
        router.replace(
          `/apply?application_id=${encodeURIComponent(data.application_id)}`,
          { scroll: false }
        );
      } catch (err) {
        setMessage(messageFromError(err, "Could not start Review & Apply"));
      } finally {
        setBusy(false);
        setLoading(false);
      }
    },
    [authHeaders, router, syncDrafts]
  );

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    (async () => {
      try {
        if (appIdParam || jobIdParam) {
          setBusy(true);
          setMessage(null);
          const res = await fetch("/api/v1/apply-sessions/start", {
            method: "POST",
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify(
              appIdParam
                ? { application_id: appIdParam }
                : { job_id: jobIdParam }
            ),
          });
          if (!res.ok) {
            const b = await res.json().catch(() => ({}));
            throw new Error(
              typeof b.detail === "string" ? b.detail : "Failed to start session"
            );
          }
          const data = (await res.json()) as ApplySession;
          if (!cancelled) {
            setSession(data);
            syncDrafts(data);
            if (data.status === "completed") setStudioTab("form");
            router.replace(
              `/apply?application_id=${encodeURIComponent(data.application_id)}`,
              { scroll: false }
            );
          }
          return;
        }
        const res = await fetch("/api/v1/jobs/", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          if (!cancelled) {
            type JobListItem = {
              id: string;
              role_title?: string | null;
              company_name?: string | null;
              description_normalized?: { company_name?: string } | null;
            };
            setJobs(
              (Array.isArray(data) ? (data as JobListItem[]) : [])
                .slice(0, 12)
                .map((j) => ({
                  id: j.id,
                  role_title: j.role_title ?? null,
                  company:
                    j.description_normalized?.company_name ||
                    j.company_name ||
                    "Unknown company",
                }))
            );
          }
        }
      } catch (err) {
        if (!cancelled) {
          setMessage(messageFromError(err, "Could not start Review & Apply"));
        }
      } finally {
        if (!cancelled) {
          setBusy(false);
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- boot once from URL
  }, [token]);

  const patchFields = useCallback(
    async (fields: Record<string, string>) => {
      if (!session) return;
      try {
        const res = await fetch(
          `/api/v1/apply-sessions/${session.application_id}/fields`,
          {
            method: "PATCH",
            headers: authHeaders(),
            body: JSON.stringify({ fields }),
          }
        );
        if (!res.ok) {
          const b = await res.json().catch(() => ({}));
          throw new Error(
            typeof b.detail === "string" ? b.detail : "Could not save field"
          );
        }
        const data = (await res.json()) as ApplySession;
        setSession(data);
      } catch (err) {
        setMessage(messageFromError(err, "Could not save edits"));
      }
    },
    [authHeaders, session]
  );

  const onFieldChange = (key: string, value: string) => {
    setDrafts((d) => ({ ...d, [key]: value }));
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      void patchFields({ [key]: value });
    }, 450);
  };

  const downloadWithAuth = async (path: string, filename: string) => {
    try {
      const res = await fetch(path, { headers: authHeaders() });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(
          typeof body.detail === "string"
            ? body.detail
            : "Download is available after you package resume/cover on Jobs or Canvas."
        );
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setMessage(messageFromError(err, "Download failed"));
    }
  };

  const submitApplication = async () => {
    if (!session) return;
    if (!session.job_url) {
      setMessage({
        tone: "error",
        title: "No employer URL",
        detail:
          "This job has no apply link. Paste the portal URL on Jobs, then restart Review & Apply.",
      });
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      window.open(session.job_url, "_blank", "noopener,noreferrer");
      const res = await fetch(
        `/api/v1/apply-sessions/${session.application_id}/confirm-submitted`,
        { method: "POST", headers: authHeaders() }
      );
      if (!res.ok) {
        const b = await res.json().catch(() => ({}));
        throw new Error(
          typeof b.detail === "string" ? b.detail : "Confirm failed"
        );
      }
      const data = (await res.json()) as ApplySession;
      setSession(data);
      setStudioTab("form");
      setMessage({
        tone: "success",
        title: "Marked submitted",
        detail:
          data.follow_up?.note ||
          "We opened the employer form. Click Submit there — Career OS does not silent-submit. Follow-up draft queued (~3 days).",
      });
    } catch (err) {
      setMessage(messageFromError(err, "Submit failed"));
    } finally {
      setBusy(false);
    }
  };

  const personal = useMemo(
    () => (session?.form_fields || []).filter((f) => f.group !== "experience"),
    [session]
  );
  const experience = useMemo(
    () => (session?.form_fields || []).filter((f) => f.group === "experience"),
    [session]
  );

  if (loading) {
    return (
      <div className="p-8 flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading Review &amp; Apply…
      </div>
    );
  }

  if (!session) {
    return (
      <div className="p-4 md:p-8 max-w-3xl mx-auto space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Review &amp; Apply</h1>
          <p className="text-muted-foreground mt-1">
            Check the mapped form, edit anything unlocked, then submit on the
            employer site. Career OS never silent-submits to an ATS.
          </p>
        </div>
        {message && (
          <PageMessageBanner
            message={message}
            onDismiss={() => setMessage(null)}
          />
        )}
        {jobs.length === 0 ? (
          <div className="rounded-xl border border-dashed p-8 text-center space-y-3">
            <p className="font-medium">No wishlisted jobs yet</p>
            <p className="text-sm text-muted-foreground">
              Discover roles first, then start Review &amp; Apply.
            </p>
            <Link
              href="/discovery"
              className="inline-flex rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium"
            >
              Open Discovery
            </Link>
          </div>
        ) : (
          <ul className="divide-y rounded-xl border bg-card overflow-hidden">
            {jobs.map((j) => (
              <li
                key={j.id}
                className="flex items-center justify-between gap-3 p-4"
              >
                <div className="min-w-0">
                  <p className="font-medium truncate">
                    {j.company} · {j.role_title || "Role"}
                  </p>
                </div>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => startSession({ job_id: j.id })}
                  className="inline-flex items-center gap-1.5 rounded-md bg-primary text-primary-foreground px-3 py-1.5 text-xs font-medium disabled:opacity-50"
                >
                  <Play className="h-3.5 w-3.5" /> Start
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  const completed = session.status === "completed";
  const first = fieldByKey(personal, "first_name");
  const last = fieldByKey(personal, "last_name");
  const otherPersonal = personal.filter(
    (f) => f.key !== "first_name" && f.key !== "last_name"
  );

  if (completed) {
    return (
      <StudioView
        session={session}
        tab={studioTab}
        onTab={setStudioTab}
        message={message}
        onDismissMessage={() => setMessage(null)}
        onDownload={downloadWithAuth}
        onRestart={() =>
          startSession({
            application_id: session.application_id,
            reset: true,
          })
        }
        busy={busy}
      />
    );
  }

  return (
    <div className="flex flex-col h-full min-h-0 bg-background">
      <div className="flex flex-1 min-h-0">
        <aside className="hidden md:flex w-72 shrink-0 flex-col border-r border-border p-6 gap-5 bg-muted/20">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">
              Review before submit
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Waiting for your approval.
            </p>
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Check what we filled in for{" "}
            <span className="text-foreground font-medium">{session.company}</span>
            , and edit anything before we submit.
          </p>
          <div className="rounded-lg border border-border bg-muted/40 px-3 py-3 text-sm text-muted-foreground flex gap-2">
            <Lock className="h-4 w-4 shrink-0 mt-0.5" />
            <span>
              Locked fields come straight from your saved profile. Edit those in{" "}
              <Link href="/resumes" className="underline text-foreground">
                Resumes
              </Link>{" "}
              or Inbox. Everything else is editable here.
            </span>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Submit opens the employer form in a new tab and saves a receipt.
            You still click Submit on their site — we do not silent-ATS-submit.
            The Chrome extension can autofill Greenhouse / Lever / Workday.
          </p>
        </aside>

        <div className="flex-1 overflow-y-auto p-4 md:p-8 pb-28">
          <div className="md:hidden mb-6 space-y-2">
            <h1 className="text-xl font-semibold">Review before submit</h1>
            <p className="text-sm text-muted-foreground">
              Waiting for your approval. Check what we filled in for{" "}
              {session.company}.
            </p>
          </div>

          {message && (
            <div className="mb-6">
              <PageMessageBanner
                message={message}
                onDismiss={() => setMessage(null)}
              />
            </div>
          )}

          <div className="max-w-2xl space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {first && (
                <FieldInput
                  field={first}
                  value={drafts[first.key] ?? first.value}
                  onChange={onFieldChange}
                />
              )}
              {last && (
                <FieldInput
                  field={last}
                  value={drafts[last.key] ?? last.value}
                  onChange={onFieldChange}
                />
              )}
            </div>

            {otherPersonal.map((f) => (
              <FieldInput
                key={f.key}
                field={f}
                value={drafts[f.key] ?? f.value}
                onChange={onFieldChange}
              />
            ))}

            <section className="pt-2">
              <div className="flex items-baseline justify-between mb-3">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                  Work Experience
                </h2>
                <span className="text-xs text-muted-foreground">
                  {experience.length}{" "}
                  {experience.length === 1 ? "field" : "fields"}
                </span>
              </div>
              {experience.length === 0 ? (
                <p className="text-sm text-muted-foreground rounded-lg border border-dashed p-4">
                  No work-history blocks parsed from your resume. Add roles in
                  Resume Studio, or type them on the employer form.
                </p>
              ) : (
                <div className="space-y-5">
                  {experience.map((f, i) => (
                    <div key={f.key} className="space-y-2">
                      <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                        Work Experience {i + 1}
                      </p>
                      <FieldInput
                        field={f}
                        value={drafts[f.key] ?? f.value}
                        onChange={onFieldChange}
                        hideLabel
                      />
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>
        </div>
      </div>

      <footer className="shrink-0 border-t border-border bg-background px-4 md:px-8 py-3 flex items-center justify-end gap-4">
        <button
          type="button"
          onClick={() => router.push("/inbox")}
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          Cancel application
        </button>
        <button
          type="button"
          disabled={busy || !session.job_url}
          onClick={() => void submitApplication()}
          className="inline-flex items-center gap-2 rounded-md bg-emerald-800 hover:bg-emerald-900 text-white h-10 px-4 text-sm font-medium disabled:opacity-50"
        >
          {busy ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
          Submit application
        </button>
      </footer>
    </div>
  );
}

function FieldInput({
  field,
  value,
  onChange,
  hideLabel,
}: {
  field: FormField;
  value: string;
  onChange: (key: string, value: string) => void;
  hideLabel?: boolean;
}) {
  const locked = Boolean(field.locked);
  const isResume = field.key === "resume";
  const attached = isResume && /attached/i.test(field.value || value);

  return (
    <label className="block space-y-1.5">
      {!hideLabel && (
        <span className="text-sm font-medium">{field.label}</span>
      )}
      {isResume ? (
        <div
          className={`flex items-center gap-2 rounded-md border px-3 py-2.5 text-sm ${
            attached
              ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-800 dark:text-emerald-300"
              : "border-border bg-muted/40 text-muted-foreground"
          }`}
        >
          {attached ? (
            <CheckCircle2 className="h-4 w-4 shrink-0" />
          ) : (
            <Lock className="h-4 w-4 shrink-0" />
          )}
          <span>{value || field.value}</span>
        </div>
      ) : (
        <input
          type="text"
          disabled={locked}
          value={value}
          onChange={(e) => onChange(field.key, e.target.value)}
          className={`w-full rounded-md border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/30 ${
            locked
              ? "bg-muted/50 text-muted-foreground cursor-not-allowed"
              : "bg-background"
          }`}
        />
      )}
      {locked && field.key === "email" && (
        <span className="text-xs text-muted-foreground">
          Locked from your account.{" "}
          <Link href="/resumes" className="underline">
            Manage resume contact
          </Link>
        </span>
      )}
      {locked && field.key === "phone" && (
        <span className="text-xs text-muted-foreground">
          Locked from your resume. Edit the file in{" "}
          <Link href="/resumes" className="underline">
            Resumes
          </Link>
          .
        </span>
      )}
      {isResume && (
        <span className="text-xs text-muted-foreground">
          File uploads are managed in{" "}
          <Link href="/resumes" className="underline">
            Resume Studio
          </Link>
          .
        </span>
      )}
      {locked && field.key === "work_auth" && (
        <span className="text-xs text-muted-foreground">
          Set on{" "}
          <Link href="/inbox" className="underline">
            Inbox → Work authorization
          </Link>
          .
        </span>
      )}
    </label>
  );
}

function StudioView({
  session,
  tab,
  onTab,
  message,
  onDismissMessage,
  onDownload,
  onRestart,
  busy,
}: {
  session: ApplySession;
  tab: StudioTab;
  onTab: (t: StudioTab) => void;
  message: PageMessage | null;
  onDismissMessage: () => void;
  onDownload: (path: string, filename: string) => Promise<void>;
  onRestart: () => void;
  busy: boolean;
}) {
  const docs = session.docs;
  const required = docs?.required_skills?.length
    ? docs.required_skills
    : [
        ...(docs?.matching_skills || []),
        ...(docs?.missing_skills || []),
      ].slice(0, 12);
  const present = docs?.present_skills?.length
    ? docs.present_skills
    : docs?.matching_skills || [];
  const presentCount =
    docs?.present_skill_count ??
    required.filter((s) => skillMatched(s, present)).length;
  const requiredCount = docs?.required_skill_count || required.length;
  const resumeText = docs?.resume_preview || "";
  const coverText = docs?.cover_letter || docs?.cover_letter_preview || "";
  const jdText = docs?.job_description || "";

  const tabs: { id: StudioTab; label: string; icon: typeof FileText }[] = [
    { id: "form", label: "Form", icon: FileText },
    { id: "resume", label: "Resume", icon: FileStack },
    { id: "cover", label: "Cover", icon: Mail },
    { id: "job", label: "Job", icon: Briefcase },
  ];

  return (
    <div className="flex flex-col h-full min-h-0 bg-background">
      <header className="shrink-0 border-b border-border px-4 md:px-6 py-4 flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-lg md:text-xl font-semibold tracking-tight truncate">
            {session.role_title || "Role"}
          </h1>
          <p className="text-sm text-muted-foreground truncate">
            {session.company}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 shrink-0">
          {session.job_url && (
            <a
              href={session.job_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm hover:bg-muted"
            >
              <ExternalLink className="h-4 w-4" /> View job posting
            </a>
          )}
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-600 text-white px-3 py-1.5 text-sm font-medium">
            <Check className="h-4 w-4" /> Submitted
          </span>
        </div>
      </header>

      {session.receipt && (
        <div className="shrink-0 border-b border-emerald-500/30 bg-emerald-500/10 px-4 md:px-6 py-3 text-sm">
          <p className="font-medium text-emerald-800 dark:text-emerald-300">
            Application receipt
          </p>
          <p className="text-muted-foreground mt-0.5">
            {session.receipt.role_title || session.role_title} ·{" "}
            {session.receipt.company || session.company}
            {" · "}
            {session.receipt.submitted_at
              ? new Date(session.receipt.submitted_at).toLocaleString()
              : "just now"}
            {" · "}
            {session.receipt.filled_count ?? 0}/
            {session.receipt.field_count ?? 0} fields mapped
            {session.receipt.ats_score != null
              ? ` · ATS ${session.receipt.ats_score}`
              : ""}
            {session.receipt.cover_letter ? " · cover letter in package" : ""}
          </p>
          {session.receipt.note && (
            <p className="text-xs text-muted-foreground mt-1">
              {session.receipt.note}
            </p>
          )}
        </div>
      )}

      {message && (
        <div className="px-4 md:px-6 pt-4">
          <PageMessageBanner message={message} onDismiss={onDismissMessage} />
        </div>
      )}

      <div className="flex flex-1 min-h-0">
        <nav className="w-[11.5rem] md:w-56 shrink-0 border-r border-border p-3 md:p-4 overflow-y-auto space-y-6">
          <ul className="space-y-1">
            {tabs.map((t) => {
              const active = tab === t.id;
              return (
                <li key={t.id}>
                  <button
                    type="button"
                    onClick={() => onTab(t.id)}
                    className={`w-full flex items-center gap-2 rounded-md px-3 py-2 text-sm ${
                      active
                        ? "bg-primary/10 text-primary font-medium"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground"
                    }`}
                  >
                    <t.icon className="h-4 w-4 shrink-0" />
                    {t.label}
                  </button>
                </li>
              );
            })}
          </ul>

          {tab === "resume" && required.length > 0 && (
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                Required skills{" "}
                <span className="normal-case tracking-normal">
                  {presentCount}/{requiredCount || required.length}
                </span>
              </p>
              <div className="flex flex-wrap gap-1.5">
                {required.map((s) => {
                  const ok = skillMatched(s, present);
                  return (
                    <span
                      key={s}
                      className={`text-[11px] rounded-full px-2 py-0.5 border ${
                        ok
                          ? "bg-emerald-500/15 text-emerald-800 dark:text-emerald-300 border-emerald-500/30"
                          : "bg-muted text-muted-foreground border-border"
                      }`}
                    >
                      {s}
                    </span>
                  );
                })}
              </div>
            </div>
          )}

          <button
            type="button"
            disabled={busy}
            onClick={onRestart}
            className="text-xs text-muted-foreground hover:text-foreground underline"
          >
            Review again
          </button>
        </nav>

        <div className="flex-1 overflow-y-auto p-4 md:p-6">
          {tab === "form" && (
            <div className="max-w-2xl space-y-3">
              <h2 className="font-semibold">Submitted form</h2>
              <p className="text-sm text-muted-foreground">
                {session.receipt?.note ||
                  "Receipt of fields mapped before you confirmed Submit on the employer site."}
              </p>
              {session.receipt && (
                <p className="text-xs text-muted-foreground">
                  Confirmed{" "}
                  {session.receipt.submitted_at
                    ? new Date(session.receipt.submitted_at).toLocaleString()
                    : "just now"}
                  {" · "}
                  {session.receipt.filled_count ?? 0}/
                  {session.receipt.field_count ?? 0} fields mapped
                  {session.receipt.ats_score != null
                    ? ` · ATS ${session.receipt.ats_score}`
                    : ""}
                </p>
              )}
              <ul className="divide-y rounded-xl border bg-card overflow-hidden">
                {(session.receipt?.fields || session.form_fields).map(
                  (f, i) => (
                    <li
                      key={("key" in f && f.key) || i}
                      className="flex justify-between gap-3 px-4 py-2.5 text-sm"
                    >
                      <span className="text-muted-foreground shrink-0">
                        {f.label}
                      </span>
                      <span className="truncate text-right">
                        {f.value || "—"}
                      </span>
                    </li>
                  )
                )}
              </ul>
              <Link
                href="/tracker"
                className="inline-flex text-sm underline text-muted-foreground hover:text-foreground"
              >
                View in Tracker
              </Link>
            </div>
          )}

          {tab === "resume" && (
            <div className="max-w-3xl space-y-4">
              <div className="flex items-center justify-between gap-3">
                <h2 className="font-semibold">Optimized resume</h2>
                <button
                  type="button"
                  onClick={() =>
                    void onDownload(
                      `/api/v1/documents/package-download?application_id=${session.application_id}&kind=resume_pdf`,
                      `${session.company}_resume.pdf`
                    )
                  }
                  className="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm hover:bg-muted"
                >
                  <Download className="h-4 w-4" /> Download
                </button>
              </div>
              {resumeText ? (
                <div className="rounded-lg border bg-white text-zinc-900 shadow-sm p-8 min-h-[28rem] whitespace-pre-wrap text-sm leading-relaxed font-serif">
                  {resumeText}
                </div>
              ) : (
                <div className="rounded-lg border border-dashed p-8 text-sm text-muted-foreground space-y-3">
                  <p>
                    No tailored preview yet. Run Canvas for this role, or
                    package on Jobs, then return here.
                  </p>
                  <Link
                    href={docs?.canvas_href || `/canvas?job_id=${session.job_id}`}
                    className="inline-flex rounded-md border px-3 py-1.5 text-xs hover:bg-muted"
                  >
                    Open Canvas
                  </Link>
                </div>
              )}
            </div>
          )}

          {tab === "cover" && (
            <div className="max-w-3xl space-y-4">
              <div className="flex items-center justify-between gap-3">
                <h2 className="font-semibold">Cover letter</h2>
                {docs?.has_cover_letter && (
                  <button
                    type="button"
                    onClick={() =>
                      void onDownload(
                        `/api/v1/documents/package-download?application_id=${session.application_id}&kind=cover_pdf`,
                        `${session.company}_cover.pdf`
                      )
                    }
                    className="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm hover:bg-muted"
                  >
                    <Download className="h-4 w-4" /> Download
                  </button>
                )}
              </div>
              {coverText ? (
                <div className="rounded-lg border bg-white text-zinc-900 shadow-sm p-8 min-h-[20rem] whitespace-pre-wrap text-sm leading-relaxed">
                  {coverText}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground rounded-lg border border-dashed p-8">
                  No cover letter for this role yet. Generate one in Canvas,
                  then confirm submit again if you want it on the receipt.
                </p>
              )}
            </div>
          )}

          {tab === "job" && (
            <div className="max-w-3xl space-y-4">
              <h2 className="font-semibold">Job posting</h2>
              {session.job_url && (
                <a
                  href={session.job_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 text-sm underline"
                >
                  <ExternalLink className="h-4 w-4" /> Open original posting
                </a>
              )}
              {jdText ? (
                <pre className="rounded-lg border bg-card p-6 text-sm whitespace-pre-wrap font-sans leading-relaxed">
                  {jdText}
                </pre>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No stored job description. Use View job posting for the live
                  listing.
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
