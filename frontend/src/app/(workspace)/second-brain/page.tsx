"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  BookOpen,
  Brain,
  FolderOpen,
  RefreshCw,
  Sparkles,
  Copy,
  Check,
  ArrowRight,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";
import {
  PageMessageBanner,
  PageMessage,
  messageFromError,
} from "@/components/ui/PageMessageBanner";

interface LearningTrack {
  id: string;
  title: string;
  focus: string;
}

interface VaultStatus {
  configured?: boolean;
  vault_path?: string;
  career_os_folder?: string;
  exists?: boolean;
  writable?: boolean;
  application_notes?: number;
  daily_notes?: number;
  hint?: string;
  error?: string;
  learning_tracks?: LearningTrack[];
}

export default function SecondBrainPage() {
  const token = useAuthStore((s) => s.token);
  const [status, setStatus] = useState<VaultStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [banner, setBanner] = useState<PageMessage | null>(null);
  const [minutes, setMinutes] = useState(45);
  const [trackId, setTrackId] = useState("");
  const [copied, setCopied] = useState(false);
  const [showSetup, setShowSetup] = useState(false);

  const authHeaders = useCallback(
    () => ({ Authorization: `Bearer ${token}`, "Content-Type": "application/json" }),
    [token]
  );

  const loadStatus = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch("/api/v1/obsidian/status", { headers: authHeaders() });
      if (!res.ok) throw new Error("Could not load Obsidian status");
      const data = await res.json();
      setStatus(data);
      if (data.error && !data.writable) {
        setShowSetup(true);
      }
    } catch (err) {
      setBanner(messageFromError(err, "Could not reach Second Brain API"));
    } finally {
      setLoading(false);
    }
  }, [token, authHeaders]);

  useEffect(() => {
    void loadStatus();
  }, [loadStatus]);

  const run = async (path: string, body?: object) => {
    setBusy(true);
    setBanner(null);
    try {
      const res = await fetch(`/api/v1/obsidian/${path}`, {
        method: "POST",
        headers: authHeaders(),
        body: body ? JSON.stringify(body) : undefined,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail : "Request failed");
      }
      setStatus((prev) => ({ ...prev, ...data }));
      if (path === "sync") {
        setBanner({
          tone: "success",
          title: "Applications synced",
          detail: `${data.synced ?? 0} notes written under Career OS/Applications in your vault.`,
        });
      } else if (path === "daily-learning") {
        setBanner({
          tone: "success",
          title: "Daily session ready",
          detail: `Open ${data.file ? "today’s note in Obsidian" : "Career OS/Daily"} and spend your practice block.`,
        });
      } else if (path === "scaffold") {
        setBanner({
          tone: "success",
          title: "Vault folders ready",
          detail: "Career OS/Dashboard, Applications, Daily, and Interview Prep are set up.",
        });
      }
      await loadStatus();
    } catch (err) {
      setBanner(messageFromError(err, "Action failed"));
    } finally {
      setBusy(false);
    }
  };

  const copyPath = async () => {
    const path = status?.vault_path;
    if (!path) return;
    try {
      await navigator.clipboard.writeText(path);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      /* ignore */
    }
  };

  const vaultReady = Boolean(status?.configured && status?.writable);

  return (
    <div className="flex-1 p-4 md:p-8 space-y-6 overflow-y-auto os-scrollbar">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-1">
            Local second brain
          </p>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight flex items-center gap-2">
            <Brain className="h-7 w-7 text-muted-foreground shrink-0" aria-hidden />
            Second Brain
          </h1>
          <p className="text-sm text-muted-foreground mt-1 max-w-xl">
            Sync jobs, JDs, resumes, and status into Obsidian. Prep when shortlisted.
            Practice fundamentals every day. This is separate from{" "}
            <Link href="/vault" className="text-primary hover:underline">
              Knowledge Vault
            </Link>{" "}
            (in-app skills, portals, and semantic search).
          </p>
        </div>
        <button
          type="button"
          onClick={() => loadStatus()}
          disabled={loading || busy}
          aria-label="Refresh vault status"
          className="inline-flex items-center gap-2 text-sm border border-border rounded-md px-3 py-2 hover:bg-muted disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {banner && (
        <PageMessageBanner message={banner} onDismiss={() => setBanner(null)} />
      )}

      {/* Status */}
      <section className="rounded-xl border bg-card p-4 md:p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-semibold flex items-center gap-2 text-sm md:text-base">
            <FolderOpen className="h-4 w-4 text-muted-foreground" />
            Obsidian vault
          </h2>
          {!loading && (
            <span
              className={`text-[11px] font-medium px-2 py-0.5 rounded-md border ${
                vaultReady
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                  : "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400"
              }`}
            >
              {vaultReady ? "Connected" : "Needs setup"}
            </span>
          )}
        </div>

        {loading ? (
          <div className="space-y-2" aria-busy="true">
            <div className="h-12 rounded-lg bg-muted animate-pulse" />
            <div className="h-20 rounded-lg bg-muted animate-pulse" />
          </div>
        ) : !vaultReady ? (
          <div className="rounded-lg border border-dashed border-border p-6 text-center space-y-3">
            <p className="font-medium text-sm">Connect your Obsidian vault</p>
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
              Set <code className="text-xs bg-muted px-1 rounded">OBSIDIAN_VAULT_PATH</code> to
              your Jay OS folder, restart the API, then create folders here.
            </p>
            <div className="flex flex-wrap justify-center gap-2 pt-1">
              <button
                type="button"
                disabled={busy}
                onClick={() => run("scaffold")}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium disabled:opacity-50"
              >
                Create Career OS folders
              </button>
              <button
                type="button"
                onClick={() => setShowSetup((v) => !v)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-md border border-border text-sm hover:bg-muted"
              >
                {showSetup ? "Hide setup" : "Show setup steps"}
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <code className="text-xs bg-muted px-2 py-1.5 rounded-md truncate max-w-full flex-1 min-w-0">
                {status?.vault_path}
              </code>
              <button
                type="button"
                onClick={copyPath}
                className="inline-flex items-center gap-1.5 text-xs border border-border rounded-md px-2.5 py-1.5 hover:bg-muted shrink-0"
                aria-label="Copy vault path"
              >
                {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
                {copied ? "Copied" : "Copy"}
              </button>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              <div className="rounded-lg border bg-muted/30 px-3 py-2">
                <p className="text-[11px] text-muted-foreground uppercase tracking-wider">Applications</p>
                <p className="text-lg font-semibold tabular-nums">{status?.application_notes ?? 0}</p>
              </div>
              <div className="rounded-lg border bg-muted/30 px-3 py-2">
                <p className="text-[11px] text-muted-foreground uppercase tracking-wider">Daily notes</p>
                <p className="text-lg font-semibold tabular-nums">{status?.daily_notes ?? 0}</p>
              </div>
              <div className="rounded-lg border bg-muted/30 px-3 py-2 col-span-2 sm:col-span-1">
                <p className="text-[11px] text-muted-foreground uppercase tracking-wider">Folder</p>
                <p className="text-sm font-medium truncate">Career OS/</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2 pt-1">
              <button
                type="button"
                disabled={busy}
                aria-busy={busy}
                onClick={() => run("sync")}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium disabled:opacity-50"
              >
                <RefreshCw className={`h-4 w-4 ${busy ? "animate-spin" : ""}`} />
                Sync all applications
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => run("scaffold")}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-md border border-border text-sm hover:bg-muted disabled:opacity-50"
              >
                Refresh folders
              </button>
              <button
                type="button"
                onClick={() => setShowSetup((v) => !v)}
                className="text-sm text-muted-foreground hover:text-foreground px-2"
              >
                {showSetup ? "Hide setup" : "Setup help"}
              </button>
            </div>
          </div>
        )}

        {showSetup && (
          <div className="rounded-lg border bg-muted/20 p-4 text-sm space-y-2">
            <p className="font-medium">Setup (once)</p>
            <ol className="list-decimal pl-5 space-y-1.5 text-muted-foreground">
              <li>
                In <code className="text-xs bg-muted px-1 rounded">backend/.env</code> set{" "}
                <code className="text-xs bg-muted px-1 rounded">OBSIDIAN_VAULT_PATH</code> to your
                Obsidian vault root (e.g. your Jay OS folder).
              </li>
              <li>Restart the API (or Docker compose), then click Create / Sync above.</li>
              <li>
                Open that folder in Obsidian — notes land under <code className="text-xs">Career OS/</code>.
              </li>
            </ol>
            <p className="text-xs text-muted-foreground pt-1">
              Full guide: <code className="text-xs">docs/obsidian_second_brain.md</code> in the repo.
            </p>
          </div>
        )}
      </section>

      {/* Daily learning */}
      <section className="rounded-xl border bg-card p-4 md:p-5 space-y-4">
        <h2 className="font-semibold flex items-center gap-2 text-sm md:text-base">
          <BookOpen className="h-4 w-4 text-muted-foreground" />
          Daily learning
        </h2>
        <p className="text-sm text-muted-foreground">
          A focused block on core fundamentals and frameworks you already use — concepts,
          code practice, then a resume/interview glue step.
        </p>
        <div className="flex flex-col sm:flex-row flex-wrap gap-3 items-stretch sm:items-end">
          <label className="text-sm space-y-1.5">
            <span className="text-muted-foreground text-xs">Minutes</span>
            <input
              type="number"
              min={15}
              max={180}
              value={minutes}
              onChange={(e) => setMinutes(Number(e.target.value) || 45)}
              className="block w-full sm:w-24 rounded-md border border-border bg-background px-3 py-2 text-sm"
            />
          </label>
          <label className="text-sm space-y-1.5 flex-1 min-w-[180px]">
            <span className="text-muted-foreground text-xs">Track</span>
            <select
              value={trackId}
              onChange={(e) => setTrackId(e.target.value)}
              className="block w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            >
              <option value="">Auto-rotate for today</option>
              {(status?.learning_tracks || []).map((t) => (
                <option key={t.id} value={t.id}>
                  {t.title}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            disabled={busy || !vaultReady}
            onClick={() =>
              run("daily-learning", {
                minutes,
                track_id: trackId || null,
              })
            }
            className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-emerald-600 text-white text-sm font-medium hover:bg-emerald-700 disabled:opacity-50"
          >
            <Sparkles className="h-4 w-4" />
            Write today&apos;s session
          </button>
        </div>
        {!vaultReady && (
          <p className="text-xs text-muted-foreground">Connect the vault first to write daily notes.</p>
        )}
      </section>

      {/* How it fits the apply loop */}
      <section className="rounded-xl border bg-card p-4 md:p-5 space-y-3">
        <h2 className="font-semibold text-sm md:text-base">Your daily loop</h2>
        <ul className="space-y-3 text-sm text-muted-foreground">
          <li className="flex gap-3">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-muted text-xs font-semibold text-foreground">
              1
            </span>
            <span>
              Tailor &amp; apply in Career OS, then{" "}
              <strong className="text-foreground font-medium">Sync all applications</strong>.
            </span>
          </li>
          <li className="flex gap-3">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-muted text-xs font-semibold text-foreground">
              2
            </span>
            <span>
              On Tracker, move a card to{" "}
              <strong className="text-foreground font-medium">Shortlisted</strong> → open Prep Guide.
            </span>
          </li>
          <li className="flex gap-3">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-muted text-xs font-semibold text-foreground">
              3
            </span>
            <span>
              Write today&apos;s learning session and spend 30–45 minutes in Obsidian.
            </span>
          </li>
        </ul>
        <div className="flex flex-wrap gap-2 pt-2 border-t border-border">
          <Link
            href="/tailor"
            className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
          >
            Tailor <ArrowRight className="h-3.5 w-3.5" />
          </Link>
          <Link
            href="/tracker"
            className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
          >
            Tracker <ArrowRight className="h-3.5 w-3.5" />
          </Link>
          <Link
            href="/resumes"
            className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
          >
            Resume Studio <ArrowRight className="h-3.5 w-3.5" />
          </Link>
          <Link
            href="/vault"
            className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
          >
            Knowledge Vault <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </section>

      <section className="rounded-xl border border-dashed bg-muted/10 p-4 md:p-5 space-y-2">
        <h2 className="font-semibold text-sm">Second Brain vs Knowledge Vault</h2>
        <div className="grid sm:grid-cols-2 gap-3 text-sm text-muted-foreground">
          <div className="rounded-lg border bg-card p-3 space-y-1">
            <p className="font-medium text-foreground flex items-center gap-2">
              <Brain className="h-4 w-4" /> Obsidian Second Brain
            </p>
            <p>Markdown notes on your disk (Jay OS). Applications, prep, daily learning.</p>
          </div>
          <div className="rounded-lg border bg-card p-3 space-y-1">
            <p className="font-medium text-foreground flex items-center gap-2">
              <FolderOpen className="h-4 w-4" /> Knowledge Vault
            </p>
            <p>In-app graph: skills, job portals, semantic search for Discovery and agents.</p>
          </div>
        </div>
      </section>
    </div>
  );
}
