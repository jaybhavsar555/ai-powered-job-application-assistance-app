"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  CheckCircle2,
  Circle,
  ExternalLink,
  Loader2,
  Play,
  ShieldCheck,
  Globe,
  FileStack,
  ArrowRight,
  RefreshCw,
  Workflow,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";

interface FormField {
  key: string;
  label: string;
  value: string;
  status: string;
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
  has_tailored_resume?: boolean;
  has_cover_letter?: boolean;
  cover_letter_preview?: string | null;
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
  follow_up?: { scheduled?: boolean; note?: string } | null;
  stage?: string;
}

export default function ApplyStudioPage() {
  const token = useAuthStore((s) => s.token);
  const router = useRouter();
  const [session, setSession] = useState<ApplySession | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [jobs, setJobs] = useState<
    { id: string; role_title: string | null; company: string }[]
  >([]);

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

  const startSession = useCallback(
    async (
      body: { job_id?: string; application_id?: string; reset?: boolean }
    ) => {
      setBusy(true);
      setError(null);
      setNotice(null);
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
        const data = await res.json();
        setSession(data);
        router.replace(
          `/apply?application_id=${encodeURIComponent(data.application_id)}`,
          { scroll: false }
        );
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to start");
      } finally {
        setBusy(false);
        setLoading(false);
      }
    },
    [authHeaders, router]
  );

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    (async () => {
      try {
        if (appIdParam || jobIdParam) {
          setBusy(true);
          setError(null);
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
          const data = await res.json();
          if (!cancelled) {
            setSession(data);
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
            setJobs(
              (Array.isArray(data) ? data : []).slice(0, 12).map((j: any) => ({
                id: j.id,
                role_title: j.role_title,
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
          setError(err instanceof Error ? err.message : "Failed to start");
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

  const current = useMemo(() => {
    if (!session) return null;
    return (
      session.steps.find((s) => s.status === "active") ||
      session.steps[session.current_step_index] ||
      null
    );
  }, [session]);

  const approve = async () => {
    if (!session || !current) return;
    setBusy(true);
    setError(null);
    try {
      if (current.id === "open_site" && session.job_url) {
        window.open(session.job_url, "_blank", "noopener,noreferrer");
      }
      if (current.id === "fill_form") {
        for (let i = 0; i < 4; i++) {
          const fillRes = await fetch(
            `/api/v1/apply-sessions/${session.application_id}/simulate-fill`,
            { method: "POST", headers: authHeaders() }
          );
          if (fillRes.ok) setSession(await fillRes.json());
          await new Promise((r) => setTimeout(r, 220));
        }
      }
      if (current.id === "submit_confirm") {
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
        const data = await res.json();
        setSession(data);
        setNotice(
          data.follow_up?.note ||
            "Marked Applied. Follow-up draft queued (~3 days)."
        );
        return;
      }

      // Approve current active step — omit step_id to avoid stale-client races
      const res = await fetch(
        `/api/v1/apply-sessions/${session.application_id}/approve`,
        {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({}),
        }
      );
      if (!res.ok) {
        const b = await res.json().catch(() => ({}));
        throw new Error(
          typeof b.detail === "string" ? b.detail : "Approve failed"
        );
      }
      setSession(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(false);
    }
  };

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
            Guided apply: open the employer site, map your data, approve each
            step — you click Submit.
          </p>
        </div>
        {error && (
          <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
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

  const progress =
    session.steps.filter((s) => s.status === "approved").length /
    Math.max(session.steps.length, 1);
  const docs = session.docs;
  const showDocsPanel =
    current?.id === "prepare_docs" ||
    current?.id === "attach_resume" ||
    current?.id === "review_match";

  return (
    <div className="p-4 md:p-8 max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-primary">
            Review &amp; Apply · human approval
          </p>
          <h1 className="text-3xl font-bold tracking-tight mt-1">
            {session.company}
            {session.role_title ? ` — ${session.role_title}` : ""}
          </h1>
          <p className="text-sm text-muted-foreground mt-2 max-w-2xl">
            {session.mode_note}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {session.job_url && (
            <a
              href={session.job_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 rounded-md border px-3 py-2 text-sm hover:bg-muted"
            >
              <ExternalLink className="h-4 w-4" /> Open job site
            </a>
          )}
          <Link
            href={`/canvas?job_id=${encodeURIComponent(session.job_id)}`}
            className="inline-flex items-center gap-1.5 rounded-md border px-3 py-2 text-sm hover:bg-muted"
          >
            <Workflow className="h-4 w-4" /> Canvas
          </Link>
          <button
            type="button"
            disabled={busy}
            onClick={() =>
              startSession({
                application_id: session.application_id,
                reset: true,
              })
            }
            className="inline-flex items-center gap-1.5 rounded-md border px-3 py-2 text-sm hover:bg-muted disabled:opacity-50"
            title="Restart Review & Apply from step 1"
          >
            <RefreshCw className="h-4 w-4" /> Restart
          </button>
        </div>
      </div>

      <div className="h-2 rounded-full bg-muted overflow-hidden">
        <div
          className="h-full bg-primary transition-all"
          style={{ width: `${Math.round(progress * 100)}%` }}
        />
      </div>

      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive flex items-center justify-between gap-3">
          <span>{error}</span>
          <button
            type="button"
            className="text-xs underline shrink-0"
            onClick={() => setError(null)}
          >
            Dismiss
          </button>
        </div>
      )}
      {notice && (
        <div className="rounded-md border border-green-500/30 bg-green-500/10 px-4 py-3 text-sm">
          {notice}{" "}
          <Link href="/outreach" className="underline font-medium">
            Outreach
          </Link>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="rounded-xl border bg-card p-5 space-y-3">
          <h2 className="font-semibold flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-primary" /> Steps (approve each)
          </h2>
          <ol className="space-y-2">
            {session.steps.map((step) => {
              const active = step.status === "active";
              const done = step.status === "approved";
              return (
                <li
                  key={step.id}
                  className={`rounded-lg border p-3 ${
                    active ? "border-primary bg-primary/5" : ""
                  }`}
                >
                  <div className="flex items-start gap-2">
                    {done ? (
                      <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
                    ) : (
                      <Circle
                        className={`h-4 w-4 mt-0.5 shrink-0 ${
                          active ? "text-primary" : "text-muted-foreground"
                        }`}
                      />
                    )}
                    <div className="min-w-0">
                      <p className="text-sm font-medium">{step.title}</p>
                      <p className="text-xs text-muted-foreground">{step.desc}</p>
                    </div>
                  </div>
                </li>
              );
            })}
          </ol>

          {session.status !== "completed" && current && (
            <>
              {current.id === "open_site" && !session.job_url && (
                <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-950 dark:text-amber-100 space-y-2 mb-3">
                  <p>
                    No apply URL on this job — can&apos;t open the ATS. Paste the
                    portal link on Jobs, then restart this session.
                  </p>
                  <Link
                    href="/jobs"
                    className="inline-flex text-xs font-medium underline"
                  >
                    Fix URL on Jobs
                  </Link>
                </div>
              )}
              <button
              type="button"
              disabled={busy || (current.id === "open_site" && !session.job_url)}
              onClick={approve}
              className="w-full inline-flex items-center justify-center gap-2 rounded-md bg-primary text-primary-foreground h-11 text-sm font-medium disabled:opacity-50"
            >
              {busy ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : current.id === "submit_confirm" ? (
                <>
                  I submitted on their site <ArrowRight className="h-4 w-4" />
                </>
              ) : current.id === "open_site" ? (
                <>
                  Open site &amp; approve <ExternalLink className="h-4 w-4" />
                </>
              ) : (
                <>
                  Approve: {current.title} <CheckCircle2 className="h-4 w-4" />
                </>
              )}
            </button>
            </>
          )}
          {session.status === "completed" && (
            <Link
              href="/tracker"
              className="w-full inline-flex items-center justify-center gap-2 rounded-md border h-11 text-sm font-medium hover:bg-muted"
            >
              View in Tracker
            </Link>
          )}
        </section>

        <section className="rounded-xl border bg-card overflow-hidden flex flex-col min-h-[28rem]">
          <div className="shrink-0 flex items-center gap-2 px-3 py-2 border-b bg-muted/40">
            <Globe className="h-4 w-4 text-muted-foreground" />
            <div className="flex-1 min-w-0 rounded-md bg-background border px-2 py-1 text-[11px] truncate font-mono">
              {session.browser?.url || session.job_url || "https://…"}
            </div>
            <span className="text-[10px] text-muted-foreground uppercase">
              {session.browser?.opened ? "Site open" : "Idle"}
            </span>
          </div>

          <div className="flex-1 p-4 space-y-4 bg-gradient-to-b from-muted/20 to-background">
            {showDocsPanel && docs && (
              <div className="rounded-lg border bg-background p-4 space-y-3">
                <p className="text-xs font-semibold uppercase text-muted-foreground">
                  Resume &amp; cover for this role
                </p>
                <p className="text-sm text-muted-foreground">{docs.hint}</p>
                <div className="flex flex-wrap gap-2 text-[11px]">
                  {docs.ats_score != null && (
                    <span className="rounded-full border px-2 py-0.5">
                      ATS {docs.ats_score}%
                    </span>
                  )}
                  <span className="rounded-full border px-2 py-0.5">
                    {docs.has_tailored_resume
                      ? "Tailored resume ready"
                      : "Master resume"}
                  </span>
                  <span className="rounded-full border px-2 py-0.5">
                    {docs.has_cover_letter ? "Cover letter ready" : "No cover yet"}
                  </span>
                  <span className="rounded-full border px-2 py-0.5">
                    {docs.package_ready ? "Package on disk" : "Not packaged"}
                  </span>
                </div>
                {!!docs.matching_skills?.length && (
                  <p className="text-xs text-muted-foreground">
                    JD match: {docs.matching_skills.join(", ")}
                  </p>
                )}
                {docs.cover_letter_preview && (
                  <pre className="text-xs whitespace-pre-wrap rounded-md bg-muted/50 border p-3 max-h-36 overflow-y-auto font-sans">
                    {docs.cover_letter_preview}
                  </pre>
                )}
                <div className="flex flex-wrap gap-2">
                  <Link
                    href={docs.canvas_href || `/canvas?job_id=${session.job_id}`}
                    className="inline-flex items-center gap-1 rounded-md border px-2.5 py-1.5 text-xs hover:bg-muted"
                  >
                    <Workflow className="h-3.5 w-3.5" /> Run Canvas
                  </Link>
                  <Link
                    href="/jobs"
                    className="inline-flex items-center gap-1 rounded-md border px-2.5 py-1.5 text-xs hover:bg-muted"
                  >
                    <FileStack className="h-3.5 w-3.5" /> Package on Jobs
                  </Link>
                  <Link
                    href="/approvals"
                    className="inline-flex items-center gap-1 rounded-md border px-2.5 py-1.5 text-xs hover:bg-muted"
                  >
                    Approvals
                  </Link>
                </div>
              </div>
            )}

            <div className="rounded-lg border bg-background p-4 space-y-2">
              <p className="text-xs font-semibold uppercase text-muted-foreground">
                Employer form showcase
              </p>
              <p className="text-sm text-muted-foreground">
                Most ATS pages block embedding. We open the real site in a new
                tab and mirror field mapping here.
              </p>
              <div className="h-2 rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full bg-emerald-500 transition-all duration-300"
                  style={{
                    width: `${session.browser?.fill_progress ?? 0}%`,
                  }}
                />
              </div>
              <p className="text-[11px] text-muted-foreground">
                Fill progress: {session.browser?.fill_progress ?? 0}%
                {session.browser?.last_action
                  ? ` · ${session.browser.last_action}`
                  : ""}
              </p>
            </div>

            <ul className="space-y-2">
              {session.form_fields.map((f) => (
                <li
                  key={f.key}
                  className="flex items-start justify-between gap-3 rounded-md border px-3 py-2 text-sm"
                >
                  <div className="min-w-0">
                    <p className="font-medium text-xs text-muted-foreground">
                      {f.label}
                    </p>
                    <p className="truncate">{f.value}</p>
                  </div>
                  <span
                    className={`text-[10px] uppercase font-semibold shrink-0 ${
                      f.status === "filled"
                        ? "text-green-500"
                        : f.status === "filling"
                          ? "text-amber-500 animate-pulse"
                          : f.status === "manual"
                            ? "text-orange-500"
                            : "text-muted-foreground"
                    }`}
                  >
                    {f.status}
                  </span>
                </li>
              ))}
            </ul>

            <div className="rounded-lg border border-dashed p-3 text-xs text-muted-foreground flex items-start gap-2">
              <FileStack className="h-4 w-4 shrink-0 mt-0.5" />
              <span>
                Attach your package PDF/DOCX on their form. Career OS never
                silently uploads to third-party boards — you click Submit.
              </span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
