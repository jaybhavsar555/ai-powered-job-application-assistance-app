"use client";

import { useEffect, useState } from "react";
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
import {
  AgentTaskRow,
  stageToTaskStatus,
} from "@/components/ui/AgentTaskRow";

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

interface PipelineStep {
  id: string;
  title: string;
  desc: string;
  href: string;
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
  blockers?: ReadinessCheck[];
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
  pipeline_steps?: PipelineStep[];
  pipeline_stages?: { id: string; title: string; desc: string; href?: string }[];
  active_pipeline_step?: string;
  positioning?: { headline?: string };
  readiness?: DailyReadiness;
}

function heroHeadline(next: NextAction): string {
  const company = next.company || "this role";
  const ats = next.ats_score != null ? ` (${next.ats_score}%)` : "";
  if (next.action === "follow_up") {
    return `Recommended: Follow up with ${company}`;
  }
  if (next.action === "apply_now") {
    return `New job < 48h — apply now · ${company}`;
  }
  if (next.action === "apply") {
    return `Recommended: Apply to ${company}${ats}`;
  }
  if (next.action === "needs_input") {
    return `Needs screening answers for ${company}`;
  }
  if (next.action === "approve") {
    return `Recommended: Approve docs for ${company}${ats}`;
  }
  if (next.action === "outreach") {
    return `Recommended: Send outreach to ${company}${ats}`;
  }
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
  const [digest, setDigest] = useState<DigestData | null>(null);
  const [loading, setLoading] = useState(true);
  const [modeBusy, setModeBusy] = useState(false);
  const [modeError, setModeError] = useState<string | null>(null);
  const [autoConfirmOpen, setAutoConfirmOpen] = useState(false);
  const token = useAuthStore((s) => s.token);

  const refresh = async () => {
    const res = await fetch("/api/v1/inbox/summary", {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) setSummary(await res.json());
    const d = await fetch("/api/v1/inbox/digest", {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (d.ok) setDigest(await d.json());
  };

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        await refresh();
      } catch (err) {
        console.error("Failed to fetch inbox summary", err);
      } finally {
        setLoading(false);
      }
    };

    if (token) fetchSummary();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const setApplyMode = async (mode: "review_and_apply" | "auto_apply") => {
    setModeBusy(true);
    setModeError(null);
    try {
      const res = await fetch("/api/v1/apply-prefs", {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          apply_mode: mode,
          auto_consent: mode === "auto_apply",
        }),
      });
      if (!res.ok) {
        const b = await res.json().catch(() => ({}));
        setModeError(
          typeof b.detail === "string" ? b.detail : "Failed to update apply mode"
        );
        return;
      }
      await refresh();
    } finally {
      setModeBusy(false);
    }
  };

  const setWorkAuth = async (value: string) => {
    setModeBusy(true);
    setModeError(null);
    try {
      const res = await fetch("/api/v1/apply-prefs", {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ work_authorization: value }),
      });
      if (!res.ok) {
        const b = await res.json().catch(() => ({}));
        setModeError(
          typeof b.detail === "string" ? b.detail : "Failed to save work authorization"
        );
        return;
      }
      await refresh();
    } finally {
      setModeBusy(false);
    }
  };

  const next = summary?.next_action;
  const jobId = next?.job_id;
  const steps = summary?.pipeline_steps || [];
  const active = summary?.active_pipeline_step;
  const isAuto =
    summary?.apply_mode === "auto_apply" && summary?.auto_consent;

  return (
    <div className="p-4 md:p-8 max-w-6xl mx-auto space-y-8 animate-in fade-in duration-500">
      <div>
        <h1 className="text-4xl font-bold tracking-tight mb-2">Career Inbox</h1>
        <p className="text-muted-foreground text-lg">
          {summary?.positioning?.headline ||
            "Tailored resume + cover + outreach — then autofill the form."}
        </p>
        {modeError && (
          <div className="mt-3 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {modeError}
          </div>
        )}
      </div>

      {/* Review vs Auto */}
      {!loading && (
        <div className="rounded-xl border bg-card p-4 md:p-5 space-y-3">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold">Apply mode</p>
              <p className="text-xs text-muted-foreground max-w-xl">
                {summary?.apply_mode_note}
              </p>
            </div>
            <div className="flex gap-2 shrink-0">
              <button
                type="button"
                disabled={modeBusy}
                onClick={() => setApplyMode("review_and_apply")}
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
                  isAuto
                    ? "bg-amber-600 text-white border-amber-600"
                    : "hover:bg-muted"
                }`}
              >
                Auto Apply (gated)
              </button>
            </div>
          </div>
          {autoConfirmOpen && (
            <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-3 text-sm space-y-2">
              <p>
                Enable gated Auto Apply? The extension may click Submit on
                Greenhouse / Lever / Workday when confidence is high. LinkedIn
                stays blocked. Captchas pause the queue. Career OS still does
                not silent mass-submit.
              </p>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={modeBusy}
                  onClick={() => {
                    setAutoConfirmOpen(false);
                    void setApplyMode("auto_apply");
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
          {isAuto && summary?.auto_usage && (
            <p className="text-[11px] text-muted-foreground">
              Usage today: {summary.auto_usage.day_count ?? 0} · this hour:{" "}
              {summary.auto_usage.hour_count ?? 0}
            </p>
          )}
          <label className="block space-y-1 pt-1">
            <span className="text-xs font-medium">Work authorization</span>
            <select
              disabled={modeBusy}
              value={summary?.work_authorization || ""}
              onChange={(e) => setWorkAuth(e.target.value)}
              className="w-full md:max-w-xs h-9 rounded-md border border-input bg-background px-2 text-sm"
            >
              <option value="">Not specified</option>
              <option value="citizen">Citizen / no sponsorship needed</option>
              <option value="opt">OPT / STEM-OPT</option>
              <option value="needs_sponsorship">Need visa sponsorship</option>
              <option value="other">Other</option>
            </select>
            <span className="text-[11px] text-muted-foreground">
              Used on ATS work-auth questions and Discovery (skip “no sponsor” roles).
            </span>
          </label>
        </div>
      )}

      {/* Daily digest */}
      {!loading && digest?.summary_lines && digest.summary_lines.length > 0 && (
        <div className="rounded-lg border border-sky-500/20 bg-sky-500/5 px-4 py-3 text-sm space-y-1">
          <p className="font-medium text-foreground flex items-center gap-2">
            <Bell className="h-4 w-4" /> {digest.headline || "Daily digest"}
          </p>
          <ul className="text-muted-foreground list-disc list-inside space-y-0.5">
            {digest.summary_lines.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Daily apply readiness */}
      {!loading && summary?.readiness && (
        <section
          className={`rounded-xl border px-4 py-4 space-y-3 ${
            summary.readiness.ready_for_daily_apply
              ? "border-emerald-500/25 bg-emerald-500/5"
              : "border-amber-500/30 bg-amber-500/5"
          }`}
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="font-medium text-foreground">
              {summary.readiness.ready_for_daily_apply
                ? "Daily apply ready"
                : "Fix these before today’s apply session"}
            </p>
            <Link
              href="/screening-qa"
              className="text-xs font-medium text-primary hover:underline"
            >
              Screening Q&A
            </Link>
          </div>
          <ul className="grid gap-2 sm:grid-cols-2 text-sm">
            {(summary.readiness.checks || []).map((c) => (
              <li key={c.id} className="flex items-start gap-2">
                <span
                  className={
                    c.ok ? "text-emerald-600 shrink-0" : "text-amber-700 shrink-0"
                  }
                >
                  {c.ok ? "✓" : "!"}
                </span>
                <span className="min-w-0">
                  {c.href ? (
                    <Link href={c.href} className="hover:underline">
                      {c.label}
                    </Link>
                  ) : (
                    c.label
                  )}
                  {!c.ok && c.fix ? (
                    <span className="block text-xs text-muted-foreground">
                      {c.fix}
                    </span>
                  ) : null}
                </span>
              </li>
            ))}
          </ul>
          {summary.readiness.playbook && summary.readiness.playbook.length > 0 && (
            <ol className="text-xs text-muted-foreground list-decimal list-inside space-y-0.5 pt-1 border-t border-border/60">
              {summary.readiness.playbook.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          )}
        </section>
      )}

      {/* Apply mode honesty banner removed — replaced by mode card above */}

      {loading ? (
        <div className="h-48 rounded-xl bg-muted animate-pulse" />
      ) : next ? (
        <section className="rounded-xl border border-primary/25 bg-gradient-to-br from-primary/10 via-card to-card p-6 md:p-8 space-y-5 shadow-sm">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-primary/15 text-primary shrink-0">
              <Sparkles className="h-6 w-6" />
            </div>
            <div className="min-w-0 space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-primary">
                Today&apos;s focus
              </p>
              <h2 className="text-2xl md:text-3xl font-bold tracking-tight leading-snug">
                {heroHeadline(next)}
              </h2>
              <p className="text-muted-foreground">{next.reason}</p>
              <p className="text-sm text-muted-foreground">
                {next.role_title ? `${next.role_title} · ` : ""}
                {next.stage || "Wishlist"}
                {next.estimated_minutes
                  ? ` · ~${next.estimated_minutes} min`
                  : ""}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <Link
              href={
                next.action === "apply" && next.job_id
                  ? `/apply?job_id=${encodeURIComponent(next.job_id)}`
                  : next.href
              }
              className="inline-flex items-center justify-center rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground hover:opacity-90"
            >
              {next.action === "apply"
                ? "Start Review & Apply"
                : ctaLabel(next.action)}
            </Link>
            {jobId ? (
              <>
                <Link
                  href={`/canvas?job_id=${encodeURIComponent(jobId)}`}
                  className="inline-flex items-center gap-2 rounded-md border bg-background px-4 py-2.5 text-sm font-medium hover:bg-muted"
                >
                  <Workflow className="h-4 w-4" />
                  Canvas
                </Link>
                <Link
                  href={`/approvals?job_id=${encodeURIComponent(jobId)}`}
                  className="inline-flex items-center gap-2 rounded-md border bg-background px-4 py-2.5 text-sm font-medium hover:bg-muted"
                >
                  <FileStack className="h-4 w-4" />
                  Package / approve
                </Link>
              </>
            ) : null}
            <Link
              href="/outreach"
              className="inline-flex items-center gap-2 rounded-md border bg-background px-4 py-2.5 text-sm font-medium hover:bg-muted"
            >
              <Mail className="h-4 w-4" />
              Outreach
            </Link>
          </div>
        </section>
      ) : (
        <section className="rounded-xl border border-dashed bg-card p-8 text-center space-y-4">
          <p className="text-lg font-medium">No recommended action yet</p>
          <p className="text-sm text-muted-foreground max-w-md mx-auto">
            Run Discovery (or Vault → copy job URL → Import) to build a list with
            JD + links, then work the pipeline below.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link
              href="/discovery"
              className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
            >
              <Sparkles className="h-4 w-4" />
              Discover jobs
            </Link>
            <Link
              href="/jobs?import=1"
              className="inline-flex items-center gap-2 rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted"
            >
              <PlusCircle className="h-4 w-4" />
              Import URL
            </Link>
          </div>
        </section>
      )}

      {/* Tsenta-style four stages (Career OS still Review & Apply) */}
      {(summary?.pipeline_stages || []).length > 0 && (
        <section className="rounded-xl border bg-card p-5 md:p-6 shadow-sm">
          <h2 className="text-lg font-semibold mb-1">Four stages. You stay in the loop.</h2>
          <p className="text-xs text-muted-foreground mb-4">
            Same Find → Prep → Apply → Track story as career-page appliers — we
            do not silent-submit. Diff + receipt before anything goes out in your name.
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {(summary?.pipeline_stages || []).map((st, i) => {
              const inner = (
                <>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    {String(i + 1).padStart(2, "0")} · {st.title}
                  </p>
                  <p className="text-sm text-muted-foreground leading-snug">
                    {st.desc}
                  </p>
                </>
              );
              const cls =
                "rounded-lg border bg-muted/20 p-3 space-y-1 block hover:border-primary/40 transition-colors";
              return st.href ? (
                <Link key={st.id} href={st.href} className={cls}>
                  {inner}
                </Link>
              ) : (
                <div key={st.id} className={cls}>
                  {inner}
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Optim Hire step rail */}
      {steps.length > 0 && (
        <section className="rounded-xl border bg-card p-5 md:p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <h2 className="text-lg font-semibold">Apply loop</h2>
            <span className="text-xs text-muted-foreground">
              Same idea as Optim Hire — Review &amp; Apply (you stay in control)
            </span>
          </div>
          <ol className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-3">
            {steps.map((step, i) => {
              const isActive = step.id === active;
              return (
                <li key={step.id}>
                  <Link
                    href={step.href}
                    className={`block h-full rounded-lg border p-3 transition-colors ${
                      isActive
                        ? "border-primary bg-primary/10"
                        : "hover:bg-muted/50"
                    }`}
                  >
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                      {i + 1}
                    </p>
                    <p className="text-sm font-medium leading-snug">{step.title}</p>
                    <p className="text-[11px] text-muted-foreground mt-1 line-clamp-3">
                      {step.desc}
                    </p>
                  </Link>
                </li>
              );
            })}
          </ol>
        </section>
      )}

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-28 rounded-xl bg-muted animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <MetricCard
            title="Total"
            value={summary?.total_applications.toString() || "0"}
            icon={<LayoutDashboard className="h-5 w-5 text-blue-500" />}
            href="/tracker"
          />
          <MetricCard
            title="New < 48h"
            value={(summary?.new_jobs_48h_count ?? 0).toString()}
            icon={<Sparkles className="h-5 w-5 text-emerald-500" />}
            href="/apply"
          />
          <MetricCard
            title="Wishlist"
            value={summary?.wishlist_count.toString() || "0"}
            icon={<Clock className="h-5 w-5 text-amber-500" />}
            href="/jobs"
          />
          <MetricCard
            title="Ready to apply"
            value={summary?.ready_count.toString() || "0"}
            icon={<Send className="h-5 w-5 text-green-500" />}
            href="/apply"
          />
          <MetricCard
            title="Follow-ups due"
            value={(summary?.follow_ups_due ?? 0).toString()}
            icon={<Bell className="h-5 w-5 text-rose-500" />}
            href="/outreach"
          />
        </div>
      )}

      {!loading && (summary?.new_jobs_48h?.length || 0) > 0 && (
        <section className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-5 space-y-3">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-emerald-600" />
            New job {"<"} 48h — apply now
          </h2>
          <p className="text-sm text-muted-foreground">
            Fresh roles convert better. Open Review & Apply, fill with the extension,
            you click Submit.
          </p>
          <ul className="space-y-2">
            {summary!.new_jobs_48h!.map((j) => (
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

      {!loading && (summary?.start_applying?.length || 0) > 0 && (
        <section className="rounded-xl border bg-card p-5 space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">Start Applying</h2>
            <Link
              href="/apply"
              className="text-xs font-medium text-primary hover:underline"
            >
              Open Apply studio
            </Link>
          </div>
          <p className="text-sm text-muted-foreground">
            Queue of Ready / Reapply / Wishlist roles — same Optim Hire “Start Applying” idea.
          </p>
          <ul className="space-y-2">
            {summary!.start_applying!.slice(0, 8).map((j) => (
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

      {!loading && (summary?.skip_queue?.length || 0) > 0 && (
        <section className="rounded-xl border border-orange-500/25 bg-orange-500/5 p-5 space-y-2">
          <h2 className="text-lg font-semibold">Paused (captcha / login / missing)</h2>
          <p className="text-sm text-muted-foreground">
            Fix Screening Q&A or log in on the employer site, move to Reapply on Tracker, resume.
          </p>
          <ul className="space-y-2">
            {summary!.skip_queue!.slice(0, 5).map((s, i) => (
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
          <div className="flex gap-3 pt-1">
            <Link href="/screening-qa" className="text-xs text-primary hover:underline">
              Screening Q&A
            </Link>
            <Link href="/tracker" className="text-xs text-primary hover:underline">
              Tracker → Reapply
            </Link>
          </div>
        </section>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="rounded-xl border bg-card p-6 shadow-sm space-y-4">
          <h2 className="text-xl font-semibold">Also useful</h2>
          {(summary?.follow_ups_due || 0) > 0 ? (
            <ActionItem
              title={`${summary?.follow_ups_due} follow-up(s) due`}
              desc="Human-tone drafts waiting — review and send from Outreach."
              href="/outreach"
              icon={<Bell className="h-5 w-5" />}
            />
          ) : null}
          {(summary?.needs_input_count || 0) > 0 ? (
            <ActionItem
              title={`${summary?.needs_input_count} need screening answers`}
              desc="Fill Q&A bank, then move to Reapply on Tracker."
              href="/screening-qa"
              icon={<HelpCircle className="h-5 w-5" />}
            />
          ) : null}
          {(summary?.failed_count || 0) + (summary?.reapply_count || 0) > 0 ? (
            <ActionItem
              title={`${(summary?.failed_count || 0) + (summary?.reapply_count || 0)} failed / reapply`}
              desc="Fix blockers on Tracker, then Review & Apply again."
              href="/tracker"
            />
          ) : null}
          {(summary?.outreach_drafts || 0) > 0 ? (
            <ActionItem
              title={`${summary?.outreach_drafts} outreach draft(s)`}
              desc="Recruiter / follow-up emails — copy or SMTP send."
              href="/outreach"
            />
          ) : null}
          {summary?.pending_approvals ? (
            <ActionItem
              title="Pending approvals"
              desc="Review tailored resume / cover before packaging."
              href="/approvals"
            />
          ) : null}
          <ActionItem
            title="Discover more roles"
            desc="AI matches with JD + link → Add to Wishlist."
            href="/discovery"
            icon={<Sparkles className="h-5 w-5" />}
          />
          <ActionItem
            title="Import from a portal"
            desc="Vault → open site → copy job URL → Import."
            href="/vault"
            icon={<PlusCircle className="h-5 w-5" />}
          />
        </div>

        <div className="rounded-xl border bg-card p-6 shadow-sm space-y-3">
          <h2 className="text-xl font-semibold">What we automate vs you</h2>
          <ul className="text-sm text-muted-foreground space-y-2 list-disc list-inside">
            <li>
              <span className="text-foreground font-medium">We:</span> score JD
              fit, tailor resume/cover, package files, draft recruiter + follow-up
              mail in your tone.
            </li>
            <li>
              <span className="text-foreground font-medium">You:</span> approve
              docs, submit on the job site, mark Applied, approve email sends.
            </li>
            <li>
              <span className="text-foreground font-medium">Not default:</span>{" "}
              silent mass Submit. Auto mode is gated (consent + allowlist + rate
              limits); LinkedIn stays blocked. Extension + you still own the click
              in Review mode.
            </li>
          </ul>
          <Link
            href="/canvas"
            className="inline-flex mt-4 text-sm text-primary hover:underline"
          >
            Open Advanced Canvas →
          </Link>
        </div>
      </div>
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
      <div className="rounded-xl border bg-card p-5 shadow-sm hover:shadow-md transition-shadow group cursor-pointer h-full">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-medium text-muted-foreground">{title}</h3>
          <div className="p-1.5 bg-primary/5 rounded-full group-hover:bg-primary/10 transition-colors">
            {icon}
          </div>
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
      <div className="flex items-start gap-4 p-4 rounded-lg border hover:bg-muted/50 transition-colors">
        <div className="mt-0.5 text-primary">
          {icon || <CheckCircle className="h-5 w-5" />}
        </div>
        <div>
          <div className="font-medium">{title}</div>
          <div className="text-sm text-muted-foreground">{desc}</div>
        </div>
      </div>
    </Link>
  );
}
