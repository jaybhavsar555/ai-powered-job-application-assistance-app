"use client";

import { useState } from "react";
import { Link2, Loader2, Plus } from "lucide-react";
import api, { getApiErrorMessage } from "@/lib/api";

type IngestedJob = {
  id: string;
  role_title: string;
  url?: string | null;
};

type Props = {
  onIngested: () => void;
};

export function JobIngestForm({ onIngested }: Props) {
  const [url, setUrl] = useState("");
  const [description, setDescription] = useState("");
  const [roleTitle, setRoleTitle] = useState("");
  const [company, setCompany] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);

    const trimmedUrl = url.trim();
    const trimmedDesc = description.trim();
    if (!trimmedUrl && !trimmedDesc) {
      setError("Paste a job URL or raw description.");
      return;
    }

    setBusy(true);
    try {
      const payload: Record<string, string> = {};
      if (trimmedUrl) payload.url = trimmedUrl;
      if (trimmedDesc) payload.description_raw = trimmedDesc;
      if (roleTitle.trim()) payload.role_title = roleTitle.trim();
      if (company.trim()) payload.company_name = company.trim();

      const { data } = await api.post<IngestedJob>("/jobs/ingest", payload);
      setMessage(`Added “${data.role_title}” to Wishlist`);
      setUrl("");
      setDescription("");
      setRoleTitle("");
      setCompany("");
      onIngested();
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Ingest failed"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form
      onSubmit={submit}
      className="rounded-xl border border-border bg-card/60 p-4 space-y-3 shrink-0"
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <Link2 className="w-4 h-4 text-primary shrink-0" />
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-foreground">Import job</h2>
            <p className="text-xs text-muted-foreground truncate">
              Playwright scrapes the URL when description is empty
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setShowAdvanced((v) => !v)}
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          {showAdvanced ? "Hide details" : "More options"}
        </button>
      </div>

      <div className="flex flex-col sm:flex-row gap-2">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://boards.greenhouse.io/…/jobs/…"
          className="flex-1 min-w-0 rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-primary"
        />
        <button
          type="submit"
          disabled={busy}
          className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50 shrink-0"
        >
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
          Ingest
        </button>
      </div>

      {showAdvanced && (
        <div className="grid gap-2 sm:grid-cols-2">
          <input
            value={roleTitle}
            onChange={(e) => setRoleTitle(e.target.value)}
            placeholder="Role title (optional)"
            className="rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-primary"
          />
          <input
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="Company (optional)"
            className="rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-primary"
          />
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Or paste the job description text…"
            rows={4}
            className="sm:col-span-2 rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-primary resize-y"
          />
        </div>
      )}

      {error && (
        <p className="text-xs text-red-400">{error}</p>
      )}
      {message && (
        <p className="text-xs text-emerald-400">{message}</p>
      )}
    </form>
  );
}
