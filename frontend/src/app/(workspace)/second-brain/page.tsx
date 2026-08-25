"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  BookOpen,
  Brain,
  FolderOpen,
  RefreshCw,
  Sparkles,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";

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
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [minutes, setMinutes] = useState(45);
  const [trackId, setTrackId] = useState<string>("");

  const authHeaders = useCallback(
    () => ({ Authorization: `Bearer ${token}`, "Content-Type": "application/json" }),
    [token]
  );

  const loadStatus = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/v1/obsidian/status", { headers: authHeaders() });
      if (!res.ok) throw new Error("Could not load Obsidian status");
      setStatus(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load status");
    } finally {
      setLoading(false);
    }
  }, [token, authHeaders]);

  useEffect(() => {
    void loadStatus();
  }, [loadStatus]);

  const run = async (path: string, body?: object) => {
    setBusy(true);
    setError(null);
    setMessage(null);
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
        setMessage(`Synced ${data.synced ?? 0} application notes into your vault.`);
      } else if (path === "daily-learning") {
        setMessage(`Daily learning note ready: ${data.file || "Daily note written"}.`);
      } else if (path === "scaffold") {
        setMessage("Career OS folders + Dashboard created in your vault.");
      }
      await loadStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex-1 p-4 md:p-8 space-y-6 overflow-y-auto">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Brain className="h-8 w-8 text-primary" />
            Second Brain
          </h1>
          <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
            Sync jobs, JDs, resumes, and status into your Obsidian vault (Jay OS).
            Generate daily fundamentals practice and interview prep notes when you get shortlisted.
          </p>
        </div>
        <button
          type="button"
          onClick={() => loadStatus()}
          className="inline-flex items-center gap-2 text-sm border border-border rounded-md px-3 py-2 hover:bg-muted"
        >
          <RefreshCw className="h-4 w-4" /> Refresh
        </button>
      </div>

      {error && (
        <div className="flex items-start gap-2 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md p-3">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}
      {message && (
        <div className="flex items-start gap-2 text-sm text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-md p-3">
          <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />
          <span>{message}</span>
        </div>
      )}

      <section className="rounded-xl border bg-card p-5 space-y-3">
        <h2 className="font-semibold flex items-center gap-2">
          <FolderOpen className="h-4 w-4" /> Obsidian vault
        </h2>
        {loading ? (
          <p className="text-sm text-muted-foreground">Checking vault…</p>
        ) : (
          <div className="text-sm space-y-2">
            <p>
              <span className="text-muted-foreground">Path: </span>
              <code className="text-xs bg-muted px-1.5 py-0.5 rounded">
                {status?.vault_path || "(not set)"}
              </code>
            </p>
            <p className="text-muted-foreground">
              {status?.hint ||
                "Set OBSIDIAN_VAULT_PATH in backend/.env to your Jay OS folder."}
            </p>
            <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
              <span>App notes: {status?.application_notes ?? 0}</span>
              <span>Daily notes: {status?.daily_notes ?? 0}</span>
              <span>
                {status?.writable ? "Writable ✓" : "Not writable — check path / mount"}
              </span>
            </div>
            <pre className="text-xs bg-muted/40 rounded-md p-3 overflow-x-auto whitespace-pre-wrap">
{`# backend/.env (Windows host — Jay OS vault)
OBSIDIAN_VAULT_PATH=C:\\\\Users\\\\Asus\\\\OneDrive\\\\Desktop\\\\Jay OS

# Docker: mount the vault into the API container
# volumes:
#   - "C:/Users/Asus/OneDrive/Desktop/Jay OS:/data/obsidian"
# OBSIDIAN_VAULT_PATH=/data/obsidian`}
            </pre>
          </div>
        )}
        <div className="flex flex-wrap gap-2 pt-2">
          <button
            type="button"
            disabled={busy}
            onClick={() => run("scaffold")}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-border text-sm font-medium hover:bg-muted disabled:opacity-50"
          >
            Create Career OS folders
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => run("sync")}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${busy ? "animate-spin" : ""}`} />
            Sync all applications
          </button>
        </div>
      </section>

      <section className="rounded-xl border bg-card p-5 space-y-4">
        <h2 className="font-semibold flex items-center gap-2">
          <BookOpen className="h-4 w-4" /> Daily learning
        </h2>
        <p className="text-sm text-muted-foreground">
          Spend focused time on core fundamentals and frameworks you already use.
          Notes land under <code className="text-xs">Career OS/Daily/</code> in Obsidian.
        </p>
        <div className="flex flex-wrap gap-3 items-end">
          <label className="text-sm space-y-1">
            <span className="text-muted-foreground text-xs">Minutes</span>
            <input
              type="number"
              min={15}
              max={180}
              value={minutes}
              onChange={(e) => setMinutes(Number(e.target.value) || 45)}
              className="block w-24 rounded-md border border-border bg-background px-3 py-2 text-sm"
            />
          </label>
          <label className="text-sm space-y-1 flex-1 min-w-[200px]">
            <span className="text-muted-foreground text-xs">Track (optional)</span>
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
            disabled={busy}
            onClick={() =>
              run("daily-learning", {
                minutes,
                track_id: trackId || null,
              })
            }
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 text-white text-sm font-medium disabled:opacity-50"
          >
            <Sparkles className="h-4 w-4" />
            Write today’s session
          </button>
        </div>
      </section>

      <section className="rounded-xl border bg-card p-5 space-y-3 text-sm">
        <h2 className="font-semibold">How to use this with Jay OS</h2>
        <ol className="list-decimal pl-5 space-y-2 text-muted-foreground">
          <li>
            Point <code className="text-xs">OBSIDIAN_VAULT_PATH</code> at{" "}
            <code className="text-xs">C:\Users\Asus\OneDrive\Desktop\Jay OS</code>.
          </li>
          <li>
            Click <strong>Create Career OS folders</strong> once — creates{" "}
            <code className="text-xs">Career OS/</code> inside your vault.
          </li>
          <li>
            Apply / tailor jobs in Career OS, then <strong>Sync all applications</strong>.
            Each note stores JD, resume content, ATS, stage, and a <em>My notes</em> section you can edit in Obsidian.
          </li>
          <li>
            Drag a card to <strong>Shortlisted</strong> or <strong>Interview</strong> on Tracker →{" "}
            <Link href="/tracker" className="text-primary hover:underline">
              open Prep Guide
            </Link>{" "}
            and regenerate drills; re-sync to write Interview Prep notes.
          </li>
          <li>
            Every day: click <strong>Write today’s session</strong> and spend the block in Obsidian.
          </li>
        </ol>
      </section>
    </div>
  );
}
