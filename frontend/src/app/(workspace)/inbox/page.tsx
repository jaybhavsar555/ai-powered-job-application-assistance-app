"use client";

import { useCallback, useEffect, useState } from "react";
import {
  LayoutDashboard,
  CheckCircle,
  Clock,
  Send,
  PlusCircle,
  Sparkles,
  Workflow,
  FileStack,
  Mail,
  Bell,
  HelpCircle,
} from "lucide-react";
import Link from "next/link";
import { useAuthStore } from "@/store/auth";
import { apiFetch, getApiErrorMessage } from "@/lib/api";
import {
  AgentTaskRow,
  stageToTaskStatus,
} from "@/components/ui/AgentTaskRow";
import {
  PageMessageBanner,
  messageFromError,
  type PageMessage,
} from "@/components/ui/PageMessageBanner";

interface NextAction {
  action: string;
  label: string;
  reason: string;
  href: string;
  job_id?: string;
  company?: string;
  role_title?: string;
  stage?: string;
  ats_score?: number | null;
  estimated_minutes?: number;
}

interface FollowUpItem {
  application_id: string;
  job_id: string;
  company: string;
  role_title?: string | null;
  follow_up_due_at?: string;
  href: string;
}

interface FreshJobItem {
  application_id: string;
  job_id: string;
  company: string;
  role_title?: string | null;
  stage?: string;
  age_hours?: number;
  label: string;
  href: string;
}

interface StartApplyItem {
  application_id: string;
  job_id: string;
  company: string;
  role_title?: string | null;
  stage?: string;
  href: string;
  url?: string | null;
}

interface DigestData {
  summary_lines?: string[];
  headline?: string;
}

interface ReadinessCheck {
  id: string;
  ok: boolean;
  label: string;
  fix?: string | null;
  href?: string;
}

interface DailyReadiness {
  ready_for_daily_apply?: boolean;
  checks?: ReadinessCheck[];
  playbook?: string[];
}

interface InboxSummary {
  total_applications: number;
  wishlist_count: number;
  ready_count: number;
  applied_count?: number;
  needs_input_count?: number;
  failed_count?: number;
  reapply_count?: number;
  pending_approvals: number;
  outreach_drafts?: number;
  follow_ups_due?: number;
  follow_ups?: FollowUpItem[];
  new_jobs_48h_count?: number;
  new_jobs_48h?: FreshJobItem[];
  start_applying_count?: number;
  start_applying?: StartApplyItem[];
  skip_queue?: { reason?: string; detail?: string; host?: string; at?: string }[];
  next_action?: NextAction | null;
  apply_mode?: string;
  apply_mode_note?: string;
  auto_consent?: boolean;
  work_authorization?: string;
  auto_usage?: { hour_count?: number; day_count?: number };
  pipeline_stages?: { id: string; title: string; desc: string; href?: string }[];
  positioning?: { headline?: string };
  readiness?: DailyReadiness;
  digest?: DigestData;
}

function heroHeadline(next: NextAction): string {
  const company = next.company || "this role";
  const ats = next.ats_score != null ? ` (${next.ats_score}%)` : "";
  if (next.action === "follow_up") return `Recommended: Follow up with ${company}`;
  if (next.action === "apply_now") return `New job < 48h — apply now · ${company}`;
  if (next.action === "apply") return `Recommended: Apply to ${company}${ats}`;
  if (next.action === "needs_input") return `Needs screening answers for ${company}`;
  if (next.action === "approve") return `Recommended: Approve docs for ${company}${ats}`;
  if (next.action === "outreach") return `Recommended: Send outreach to ${company}${ats}`;
  return `Recommended: Run pipeline for ${company}${ats}`;
}

function ctaLabel(action: string): string {
  if (action === "follow_up") return "Open follow-up draft";
  if (action === "apply_now" || action === "apply") return "Review & Apply";
  if (action === "needs_input") return "Open Screening Q&A";
  if (action === "approve") return "Review approvals";
  if (action === "outreach") return "Open outreach";
  return "Continue";
}

export default function InboxPage() {
  const [summary, setSummary] = useState<InboxSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [modeBusy, setModeBusy] = useState(false);
  const [pageMessage, setPageMessage] = useState<PageMessage | null>(null);
  const [autoConfirmOpen, setAutoConfirmOpen] = useState(false);
  const [readinessOpen, setReadinessOpen] = useState(false);
  const token = useAuthStore((s) => s.token);

  const refresh = useCallback(async () => {
    const res = await apiFetch("/api/v1/inbox/summary");
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(
        typeof body.detail === "string"
          ? body.detail
          : `Failed to load inbox (${res.status})`
      );
    }
    setSummary(await res.json());
  }, []);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      setPageMessage({
        tone: "error",
        title: "Not signed in",
        detail: "Sign in at /login, then return to Inbox.",
      });
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        await refresh();
        if (!cancelled) setPageMessage(null);
      } catch (err) {
        console.error("Failed to fetch inbox summary", err);
        if (!cancelled) {
          setPageMessage(
            messageFromError(getApiErrorMessage(err, "Failed to load inbox"))
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token, refresh]);

  const patchPrefs = async (body: Record<string, unknown>) => {
    setModeBusy(true);
    try {
      const res = await apiFetch("/api/v1/apply-prefs", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const b = await res.json().catch(() => ({}));
        setPageMessage({
          tone: "error",
          title: "Could not update apply prefs",
          detail: typeof b.detail === "string" ? b.detail : "Request failed",
        });
        return;
      }
      await refresh();
    } finally {
      setModeBusy(false);
    }
  };

  const next = summary?.next_action;
  const jobId = next?.job_id;
  const isAuto = summary?.apply_mode === "auto_apply" && summary?.auto_consent;
  const digest = summary?.digest;
  const blockers = (summary?.readiness?.checks || []).filter((c) => !c.ok);

  return (
    <div className="p-4 md:p-8 max-w-5xl mx-auto space-y-6 animate-in fade-in duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight mb-1">Career Inbox</h1>
        <p className="text-muted-foreground">
          {summary?.positioning?.headline ||
            "Tailored resume + cover + outreach — then autofill the form."}
        </p>
      </div>

      {pageMessage && (
        <PageMessageBanner
          message={pageMessage}
          onDismiss={() => setPageMessage(null)}
        />
      )}

      {!loading && summary && (
        <div className="rounded-xl border bg-card px-4 py-3 flex flex-col md:flex-row md:items-center gap-3">
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold">Apply mode</p>
            <p className="text-xs text-muted-foreground line-clamp-2">
              {summary.apply_mode_note}
            </p>
          </div>
          <div className="flex gap-2 shrink-0">
            <button
              type="button"
              disabled={modeBusy}
              onClick={() => void patchPrefs({ apply_mode: "review_and_apply", auto_consent: false })}
              className={`rounded-md px-3 py-2 text-xs font-medium border ${
                !isAuto
                  ? "bg-primary text-primary-foreground border-primary"
                  : "hover:bg-muted"
              }`}
            >
              Review &amp; Apply
            </button>
            <button
              type="button"
              disabled={modeBusy}
              onClick={() => setAutoConfirmOpen(true)}
              className={`rounded-md px-3 py-2 text-xs font-medium border ${
                isAuto ? "bg-amber-600 text-white border-amber-600" : "hover:bg-muted"
              }`}
            >
              Auto (gated)
            </button>
          </div>
          <select
            disabled={modeBusy}
            value={summary.work_authorization || ""}
            onChange={(e) => void patchPrefs({ work_authorization: e.target.value })}
            className="h-9 rounded-md border border-input bg-background px-2 text-xs md:max-w-[220px]"
            aria-label="Work authorization"
          >
            <option value="">Work auth: not specified</option>
            <option value="citizen">Citizen / no sponsorship</option>
            <option value="opt">OPT / STEM-OPT</option>
            <option value="needs_sponsorship">Need visa sponsorship</option>
            <option value="other">Other</option>
          </select>
        </div>
      )}

      {autoConfirmOpen && (
        <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-3 text-sm space-y-2">
          <p>
            Enable gated Auto Apply? The extension may click Submit on Greenhouse /
            Lever / Workday when confidence is high. LinkedIn stays blocked.
          </p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={modeBusy}
              onClick={() => {
                setAutoConfirmOpen(false);
                void patchPrefs({ apply_mode: "auto_apply", auto_consent: true });
              }}
              className="rounded-md bg-amber-600 text-white px-3 py-1.5 text-xs font-medium disabled:opacity-50"
            >
              Enable Auto Apply
            </button>
            <button
              type="button"
              onClick={() => setAutoConfirmOpen(false)}
              className="rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-muted"
            >
              Keep Review &amp; Apply
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="space-y-4">
          <div className="h-40 rounded-xl bg-muted animate-pulse" />
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-24 rounded-xl bg-muted animate-pulse" />
            ))}
          </div>
        </div>
      ) : (
        <>
          {digest?.summary_lines && digest.summary_lines.length > 0 && (
            <div className="rounded-lg border border-sky-500/20 bg-sky-500/5 px-4 py-3 text-sm space-y-1">
              <p className="font-medium flex items-center gap-2">
                <Bell className="h-4 w-4" /> {digest.headline || "Today"}
              </p>
              <ul className="text-muted-foreground list-disc list-inside space-y-0.5">
                {digest.summary_lines.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </div>
          )}

          {summary?.readiness && (
            <button
              type="button"
              onClick={() => setReadinessOpen((v) => !v)}
              className={`w-full text-left rounded-xl border px-4 py-3 ${
                summary.readiness.ready_for_daily_apply
                  ? "border-emerald-500/25 bg-emerald-500/5"
                  : "border-amber-500/30 bg-amber-500/5"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <p className="font-medium text-sm">
                  {summary.readiness.ready_for_daily_apply
                    ? "Daily apply ready"
                    : `Fix ${blockers.length} item(s) before applying`}
                </p>
                <span className="text-xs text-muted-foreground">
                  {readinessOpen ? "Hide" : "Details"}
                </span>
              </div>
              {readinessOpen && (
                <ul className="grid gap-2 sm:grid-cols-2 text-sm mt-3">
                  {(summary.readiness.checks || []).map((c) => (
                    <li key={c.id} className="flex items-start gap-2">
                      <span className={c.ok ? "text-emerald-600" : "text-amber-700"}>
                        {c.ok ? "✓" : "!"}
                      </span>
                      <span>
                        {c.href ? (
                          <Link href={c.href} className="hover:underline" onClick={(e) => e.stopPropagation()}>
                            {c.label}
                          </Link>
                        ) : (
                          c.label
                        )}
                        {!c.ok && c.fix ? (
                          <span className="block text-xs text-muted-foreground">{c.fix}</span>
                        ) : null}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </button>
          )}

          {next ? (
            <section className="rounded-xl border border-primary/25 bg-gradient-to-br from-primary/10 via-card to-card p-5 md:p-6 space-y-4">
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-primary/15 text-primary shrink-0">
                  <Sparkles className="h-5 w-5" />
                </div>
                <div className="min-w-0 space-y-1">
                  <p className="text-xs font-semibold uppercase tracking-wide text-primary">
                    Today&apos;s focus
                  </p>
                  <h2 className="text-xl md:text-2xl font-bold tracking-tight leading-snug">
                    {heroHeadline(next)}
                  </h2>
                  <p className="text-sm text-muted-foreground">{next.reason}</p>
                  <p className="text-xs text-muted-foreground">
                    {next.role_title ? `${next.role_title} · ` : ""}
                    {next.stage || "Wishlist"}
                    {next.estimated_minutes ? ` · ~${next.estimated_minutes} min` : ""}
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Link
                  href={
                    next.action === "apply" && next.job_id
                      ? `/apply?job_id=${encodeURIComponent(next.job_id)}`
                      : next.href
                  }
                  className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
                >
                  {next.action === "apply" ? "Start Review & Apply" : ctaLabel(next.action)}
                </Link>
                {jobId ? (
                  <>
                    <Link
                      href={`/canvas?job_id=${encodeURIComponent(jobId)}`}
                      className="inline-flex items-center gap-2 rounded-md border bg-background px-3 py-2 text-sm hover:bg-muted"
                    >
                      <Workflow className="h-4 w-4" />
                      Canvas
                    </Link>
                    <Link
                      href={`/approvals?job_id=${encodeURIComponent(jobId)}`}
                      className="inline-flex items-center gap-2 rounded-md border bg-background px-3 py-2 text-sm hover:bg-muted"
                    >
                      <FileStack className="h-4 w-4" />
                      Package
                    </Link>
                  </>
                ) : null}
                <Link
                  href="/outreach"
                  className="inline-flex items-center gap-2 rounded-md border bg-background px-3 py-2 text-sm hover:bg-muted"
                >
                  <Mail className="h-4 w-4" />
                  Outreach
                </Link>
              </div>
            </section>
          ) : (
            <section className="rounded-xl border border-dashed bg-card p-6 text-center space-y-3">
              <p className="font-medium">No recommended action yet</p>
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                Discover roles or import a job URL, then work Tailor → Approvals → Apply.
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                <Link
                  href="/discovery"
                  className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
                >
                  <Sparkles className="h-4 w-4" />
                  Discover jobs
                </Link>
                <Link
                  href="/jobs?import=1"
                  className="inline-flex items-center gap-2 rounded-md border px-4 py-2 text-sm hover:bg-muted"
                >
                  <PlusCircle className="h-4 w-4" />
                  Import URL
                </Link>
              </div>
            </section>
          )}

          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <MetricCard title="Total" value={String(summary?.total_applications ?? 0)} icon={<LayoutDashboard className="h-4 w-4 text-blue-500" />} href="/tracker" />
            <MetricCard title="New < 48h" value={String(summary?.new_jobs_48h_count ?? 0)} icon={<Sparkles className="h-4 w-4 text-emerald-500" />} href="/apply" />
            <MetricCard title="Wishlist" value={String(summary?.wishlist_count ?? 0)} icon={<Clock className="h-4 w-4 text-amber-500" />} href="/jobs" />
            <MetricCard title="Ready" value={String(summary?.ready_count ?? 0)} icon={<Send className="h-4 w-4 text-green-500" />} href="/apply" />
            <MetricCard title="Follow-ups" value={String(summary?.follow_ups_due ?? 0)} icon={<Bell className="h-4 w-4 text-rose-500" />} href="/outreach" />
          </div>

          {(summary?.pipeline_stages || []).length > 0 && (
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              {(summary?.pipeline_stages || []).map((st, i) => (
                <Link
                  key={st.id}
                  href={st.href || "/inbox"}
                  className="rounded-lg border bg-card p-3 hover:border-primary/40 transition-colors"
                >
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    {String(i + 1).padStart(2, "0")} · {st.title}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{st.desc}</p>
                </Link>
              ))}
            </div>
          )}

          {(summary?.new_jobs_48h?.length || 0) > 0 && (
            <section className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-4 space-y-2">
              <h2 className="font-semibold flex items-center gap-2 text-sm">
                <Sparkles className="h-4 w-4 text-emerald-600" />
                New job {"<"} 48h
              </h2>
              <ul className="space-y-2">
                {summary!.new_jobs_48h!.slice(0, 5).map((j) => (
                  <li key={j.application_id}>
                    <AgentTaskRow
                      title={`${j.company} — ${j.role_title || "Role"}`}
                      subtitle={`~${j.age_hours ?? 0}h old`}
                      meta={j.stage || "Wishlist"}
                      status="pending"
                      badge="Fresh"
                      href={j.href}
                      actionLabel="Apply now →"
                    />
                  </li>
                ))}
              </ul>
            </section>
          )}

          {(summary?.start_applying?.length || 0) > 0 && (
            <section className="rounded-xl border bg-card p-4 space-y-2">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-sm">Start applying</h2>
                <Link href="/apply" className="text-xs text-primary hover:underline">
                  Apply studio
                </Link>
              </div>
              <ul className="space-y-2">
                {summary!.start_applying!.slice(0, 6).map((j) => (
                  <li key={j.application_id}>
                    <AgentTaskRow
                      title={`${j.company} — ${j.role_title || "Role"}`}
                      subtitle={j.stage}
                      meta={j.url ? "Has apply URL" : "No URL — fix on Jobs"}
                      status={stageToTaskStatus(j.stage)}
                      badge={j.stage}
                      href={j.href}
                      actionLabel="Start →"
                    />
                  </li>
                ))}
              </ul>
            </section>
          )}

          {(summary?.skip_queue?.length || 0) > 0 && (
            <section className="rounded-xl border border-orange-500/25 bg-orange-500/5 p-4 space-y-2">
              <h2 className="font-semibold text-sm">Paused (captcha / login / missing)</h2>
              <ul className="space-y-2">
                {summary!.skip_queue!.slice(0, 4).map((s, i) => (
                  <li key={`${s.at}-${i}`}>
                    <AgentTaskRow
                      title={s.reason || "Paused apply"}
                      subtitle={s.host || undefined}
                      meta={s.detail || undefined}
                      status="needs_input"
                      href="/screening-qa"
                      actionLabel="Fix →"
                    />
                  </li>
                ))}
              </ul>
            </section>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {(summary?.follow_ups_due || 0) > 0 && (
              <ActionItem
                title={`${summary?.follow_ups_due} follow-up(s) due`}
                desc="Review drafts on Outreach."
                href="/outreach"
                icon={<Bell className="h-5 w-5" />}
              />
            )}
            {(summary?.needs_input_count || 0) > 0 && (
              <ActionItem
                title={`${summary?.needs_input_count} need screening answers`}
                desc="Fill Q&A, then Reapply on Tracker."
                href="/screening-qa"
                icon={<HelpCircle className="h-5 w-5" />}
              />
            )}
            {(summary?.failed_count || 0) + (summary?.reapply_count || 0) > 0 && (
              <ActionItem
                title={`${(summary?.failed_count || 0) + (summary?.reapply_count || 0)} failed / reapply`}
                desc="Fix blockers, then Review & Apply again."
                href="/tracker"
              />
            )}
            {(summary?.outreach_drafts || 0) > 0 && (
              <ActionItem
                title={`${summary?.outreach_drafts} outreach draft(s)`}
                desc="Copy or SMTP send after review."
                href="/outreach"
              />
            )}
            {!!summary?.pending_approvals && (
              <ActionItem
                title="Pending approvals"
                desc="Review tailored resume / cover."
                href="/approvals"
              />
            )}
            <ActionItem
              title="Discover more roles"
              desc="Match JD + link → Wishlist."
              href="/discovery"
              icon={<Sparkles className="h-5 w-5" />}
            />
          </div>
        </>
      )}
    </div>
  );
}

function MetricCard({
  title,
  value,
  icon,
  href,
}: {
  title: string;
  value: string;
  icon: React.ReactNode;
  href: string;
}) {
  return (
    <Link href={href}>
      <div className="rounded-xl border bg-card p-4 hover:shadow-md transition-shadow h-full">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-xs font-medium text-muted-foreground">{title}</h3>
          {icon}
        </div>
        <div className="text-2xl font-bold">{value}</div>
      </div>
    </Link>
  );
}

function ActionItem({
  title,
  desc,
  href,
  icon,
}: {
  title: string;
  desc: string;
  href: string;
  icon?: React.ReactNode;
}) {
  return (
    <Link href={href} className="block">
      <div className="flex items-start gap-3 p-3 rounded-lg border hover:bg-muted/50 h-full">
        <div className="mt-0.5 text-primary">{icon || <CheckCircle className="h-5 w-5" />}</div>
        <div>
          <div className="font-medium text-sm">{title}</div>
          <div className="text-xs text-muted-foreground">{desc}</div>
        </div>
      </div>
    </Link>
  );
}
