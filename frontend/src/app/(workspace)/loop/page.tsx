"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Loader2,
  Play,
  Plus,
  RefreshCw,
  Repeat,
  Trash2,
  Radar,
  ShieldCheck,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";
import {
  PageMessageBanner,
  PageMessage,
  messageFromError,
} from "@/components/ui/PageMessageBanner";
import { LlmProviderSwitch } from "@/components/workflow/LlmProviderSwitch";

interface WatchCompany {
  id: string;
  name: string;
  careers_url?: string;
  ats_host?: string;
  priority?: string;
  notes?: string;
}

interface LoopSchedule {
  enabled: boolean;
  interval_hours: number;
  watchlist_only: boolean;
  last_run_at?: string | null;
  last_run_id?: string | null;
  last_run_jobs?: number;
  last_error?: string | null;
  preferences?: {
    targetRoles?: string;
    isRemote?: boolean;
    locationHubs?: string[];
    workAuthorization?: string;
  };
  philosophy?: string;
}

interface LoopStatus {
  watchlist: WatchCompany[];
  watchlist_count: number;
  schedule: LoopSchedule;
  due: boolean;
  digest: { text: string; href: string; run_id?: string }[];
  llm?: { provider?: string; model?: string };
  recommended_models?: Record<string, string[]>;
}

export default function LoopEngineerPage() {
  const token = useAuthStore((s) => s.token);
  const [status, setStatus] = useState<LoopStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [banner, setBanner] = useState<PageMessage | null>(null);
  const [newName, setNewName] = useState("");
  const [newUrl, setNewUrl] = useState("");
  const [targetRoles, setTargetRoles] = useState("software engineer");
  const [isRemote, setIsRemote] = useState(true);
  const [watchlistOnly, setWatchlistOnly] = useState(false);
  const [intervalHours, setIntervalHours] = useState(24);
  const [scheduleEnabled, setScheduleEnabled] = useState(false);

  const authHeaders = useCallback(
    () => ({
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    }),
    [token]
  );

  const loadStatus = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch("/api/v1/loop-engineer/status", {
        headers: authHeaders(),
      });
      if (!res.ok) return;
      const data: LoopStatus = await res.json();
      setStatus(data);
      const sched = data.schedule || {};
      setTargetRoles(sched.preferences?.targetRoles || "software engineer");
      setIsRemote(sched.preferences?.isRemote ?? true);
      setWatchlistOnly(sched.watchlist_only ?? false);
      setIntervalHours(sched.interval_hours ?? 24);
      setScheduleEnabled(sched.enabled ?? false);
    } catch {
      /* ignore */
    }
  }, [token, authHeaders]);

  useEffect(() => {
    void loadStatus();
  }, [loadStatus]);

  const saveSchedule = async (patch: Partial<LoopSchedule>) => {
    setBusy(true);
    setBanner(null);
    try {
      const res = await fetch("/api/v1/loop-engineer/schedule", {
        method: "PUT",
        headers: authHeaders(),
        body: JSON.stringify({
          ...patch,
          preferences: {
            targetRoles,
            isRemote,
            locationHubs: isRemote ? ["Remote"] : [],
            minSalary: "0",
            companyTypes: [],
            techStack: "",
            experienceLevel: "",
            workAuthorization: "",
          },
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(
          typeof data.detail === "string" ? data.detail : "Could not save schedule"
        );
      }
      await loadStatus();
      setBanner({
        tone: "success",
        title: "Schedule saved",
        detail: patch.enabled
          ? `Loop Engineer will scan every ${intervalHours}h (Ollama/Kimi/DeepSeek).`
          : "Schedule updated.",
      });
    } catch (err) {
      setBanner(messageFromError(err, "Schedule save failed"));
    } finally {
      setBusy(false);
    }
  };

  const addCompany = async () => {
    if (!newName.trim()) return;
    setBusy(true);
    setBanner(null);
    try {
      const res = await fetch("/api/v1/loop-engineer/watchlist", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          name: newName.trim(),
          careers_url: newUrl.trim(),
          priority: "normal",
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(
          typeof data.detail === "string" ? data.detail : "Could not add company"
        );
      }
      setNewName("");
      setNewUrl("");
      await loadStatus();
      setBanner({
        tone: "success",
        title: "Company added",
        detail: `${data.company?.name || newName} is on your watchlist.`,
      });
    } catch (err) {
      setBanner(messageFromError(err, "Add company failed"));
    } finally {
      setBusy(false);
    }
  };

  const removeCompany = async (id: string) => {
    setBusy(true);
    try {
      await fetch(`/api/v1/loop-engineer/watchlist/${id}`, {
        method: "DELETE",
        headers: authHeaders(),
      });
      await loadStatus();
    } finally {
      setBusy(false);
    }
  };

  const seedExamples = async () => {
    setBusy(true);
    try {
      const res = await fetch("/api/v1/loop-engineer/watchlist/seed-examples", {
        method: "POST",
        headers: authHeaders(),
      });
      const data = await res.json();
      await loadStatus();
      setBanner({
        tone: "success",
        title: "Examples seeded",
        detail: `Added ${data.seeded || 0} ATS-friendly companies (Stripe, Figma, Notion).`,
      });
    } catch (err) {
      setBanner(messageFromError(err, "Seed failed"));
    } finally {
      setBusy(false);
    }
  };

  const runNow = async () => {
    setBusy(true);
    setBanner(null);
    try {
      await saveSchedule({
        enabled: scheduleEnabled,
        interval_hours: intervalHours,
        watchlist_only: watchlistOnly,
      });
      const res = await fetch("/api/v1/loop-engineer/run-now", {
        method: "POST",
        headers: authHeaders(),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(
          typeof data.detail === "string" ? data.detail : "Scan failed"
        );
      }
      await loadStatus();
      setBanner({
        tone: "success",
        title: "Loop scan complete",
        detail: (
          data.message as string
        ) || `Found ${data.job_count ?? 0} jobs — approve shortlist in Pipeline.`,
      });
    } catch (err) {
      setBanner(messageFromError(err, "Run now failed"));
    } finally {
      setBusy(false);
    }
  };

  const watchlist = status?.watchlist || [];

  return (
    <div className="max-w-5xl mx-auto p-4 md:p-8 space-y-8">
      <header className="space-y-2">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10 text-primary">
            <Repeat className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Loop Engineer</h1>
            <p className="text-sm text-muted-foreground max-w-2xl">
              Watch companies, deep-search openings on a schedule with Ollama / Kimi /
              DeepSeek, then approve every step in Pipeline — no silent apply.
            </p>
          </div>
        </div>
      </header>

      <PageMessageBanner message={banner} onDismiss={() => setBanner(null)} />

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border bg-card p-5 space-y-4">
          <h2 className="font-medium flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-primary" />
            Company watchlist
          </h2>
          <p className="text-sm text-muted-foreground">
            Add employers you care about. Loop Engineer runs DuckDuckGo site searches on
            their careers pages before broader boards.
          </p>

          <div className="flex flex-col sm:flex-row gap-2">
            <input
              className="flex-1 rounded-md border bg-background px-3 py-2 text-sm"
              placeholder="Company name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
            <input
              className="flex-1 rounded-md border bg-background px-3 py-2 text-sm"
              placeholder="Careers URL (Greenhouse, Lever, Ashby…)"
              value={newUrl}
              onChange={(e) => setNewUrl(e.target.value)}
            />
            <button
              type="button"
              disabled={busy || !newName.trim()}
              onClick={() => void addCompany()}
              className="inline-flex items-center justify-center gap-1 rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground disabled:opacity-50"
            >
              <Plus className="h-4 w-4" />
              Add
            </button>
          </div>

          {watchlist.length === 0 ? (
            <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground space-y-2">
              <p>No companies yet.</p>
              <button
                type="button"
                disabled={busy}
                onClick={() => void seedExamples()}
                className="text-primary hover:underline"
              >
                Seed Stripe, Figma, Notion examples
              </button>
            </div>
          ) : (
            <ul className="divide-y rounded-lg border">
              {watchlist.map((co) => (
                <li
                  key={co.id}
                  className="flex items-start justify-between gap-2 p-3 text-sm"
                >
                  <div className="min-w-0">
                    <div className="font-medium">{co.name}</div>
                    {co.careers_url ? (
                      <a
                        href={co.careers_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-primary truncate block"
                      >
                        {co.careers_url}
                      </a>
                    ) : null}
                  </div>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void removeCompany(co.id)}
                    className="text-muted-foreground hover:text-destructive p-1"
                    aria-label={`Remove ${co.name}`}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="rounded-xl border bg-card p-5 space-y-4">
          <h2 className="font-medium flex items-center gap-2">
            <RefreshCw className="h-4 w-4 text-primary" />
            Schedule & scan prefs
          </h2>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={scheduleEnabled}
              onChange={(e) => setScheduleEnabled(e.target.checked)}
            />
            Enable scheduled scans
          </label>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={watchlistOnly}
              onChange={(e) => setWatchlistOnly(e.target.checked)}
            />
            Watchlist companies only (skip general boards)
          </label>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-sm space-y-1">
              <span className="text-muted-foreground">Target roles</span>
              <input
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={targetRoles}
                onChange={(e) => setTargetRoles(e.target.value)}
              />
            </label>
            <label className="text-sm space-y-1">
              <span className="text-muted-foreground">Interval (hours)</span>
              <input
                type="number"
                min={1}
                max={168}
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={intervalHours}
                onChange={(e) => setIntervalHours(Number(e.target.value) || 24)}
              />
            </label>
          </div>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={isRemote}
              onChange={(e) => setIsRemote(e.target.checked)}
            />
            Prefer remote roles
          </label>

          <div className="flex flex-wrap gap-2 pt-2">
            <button
              type="button"
              disabled={busy}
              onClick={() =>
                void saveSchedule({
                  enabled: scheduleEnabled,
                  interval_hours: intervalHours,
                  watchlist_only: watchlistOnly,
                })
              }
              className="rounded-md border px-3 py-2 text-sm hover:bg-muted disabled:opacity-50"
            >
              Save schedule
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => void runNow()}
              className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
            >
              {busy ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              Run scan now
            </button>
          </div>

          {status?.schedule?.last_run_at ? (
            <p className="text-xs text-muted-foreground">
              Last run: {status.schedule.last_run_jobs ?? 0} job(s) at{" "}
              {String(status.schedule.last_run_at).slice(0, 16).replace("T", " ")} UTC
              {status.due ? " · next scan due" : ""}
            </p>
          ) : null}
          {status?.schedule?.last_error ? (
            <p className="text-xs text-destructive">{status.schedule.last_error}</p>
          ) : null}
        </section>
      </div>

      <section className="rounded-xl border bg-card p-5 space-y-3">
        <h2 className="font-medium">LLM for scoring (Ollama / Kimi / DeepSeek)</h2>
        <p className="text-sm text-muted-foreground">
          Discovery and Pipeline use this provider to score watchlist matches. Local
          Ollama: <code className="text-xs">qwen2.5:3b</code> or{" "}
          <code className="text-xs">deepseek-r1:1.5b</code>. Free cloud: Kimi K3 or
          DeepSeek via Token Harbor.
        </p>
        <LlmProviderSwitch />
        {status?.llm?.provider ? (
          <p className="text-xs text-muted-foreground">
            Active: {status.llm.provider} / {status.llm.model}
          </p>
        ) : null}
      </section>

      <section className="rounded-xl border bg-card p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="font-medium flex items-center gap-2">
            <Radar className="h-4 w-4 text-primary" />
            After scan — approve in Pipeline
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Shortlist → evaluate → prepare → apply/email gates. Resume tailoring stays in
            Tailor / Studio (not auto-rewritten without you).
          </p>
        </div>
        <Link
          href={
            status?.schedule?.last_run_id
              ? `/pipeline?run_id=${status.schedule.last_run_id}`
              : "/pipeline"
          }
          className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground shrink-0"
        >
          Open Pipeline
        </Link>
      </section>

      {(status?.digest || []).length > 0 ? (
        <section className="rounded-xl border bg-muted/30 p-4 text-sm space-y-2">
          <h3 className="font-medium">Inbox digest preview</h3>
          <ul className="list-disc pl-5 text-muted-foreground space-y-1">
            {status!.digest.map((d, i) => (
              <li key={i}>
                <Link href={d.href} className="text-primary hover:underline">
                  {d.text}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
