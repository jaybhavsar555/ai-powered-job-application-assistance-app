"use client";

import { useEffect, useState, FormEvent, useCallback } from "react";
import {
  Plus,
  Search,
  Briefcase,
  ExternalLink,
  RefreshCw,
  X,
  Import,
  Workflow,
  FileStack,
  Mail,
  Loader2,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { apiFetch } from "@/lib/api";
import Link from "next/link";
import { useRouter } from "next/navigation";

interface Job {
  id: string;
  url: string | null;
  role_title: string | null;
  description_normalized: {
    company_name?: string;
    location?: string;
  } | null;
  status?: string;
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importUrl, setImportUrl] = useState("");
  const [importRaw, setImportRaw] = useState("");
  const [packagingId, setPackagingId] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const token = useAuthStore((s) => s.token);
  const router = useRouter();

  const fetchJobs = useCallback(async () => {
    try {
      setLoading(true);
      setLoadError(null);
      const res = await apiFetch("/api/v1/jobs/");
      if (!res.ok) {
        throw new Error(
          res.status === 401
            ? "Not authenticated — sign in again"
            : `Failed to load jobs (${res.status})`
        );
      }
      const data = await res.json();
      setJobs(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Failed to fetch jobs", err);
      setJobs([]);
      setLoadError(
        err instanceof Error ? err.message : "Failed to load jobs"
      );
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (token) void fetchJobs();
  }, [token, fetchJobs]);

  // Vault "Import job URL" links here with ?import=1 (avoid useSearchParams Suspense issues)
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const shouldImport = params.get("import") === "1";
    const prefill = params.get("url");
    if (!shouldImport && !prefill) return;
    if (prefill) setImportUrl(prefill);
    setIsModalOpen(true);
    router.replace("/jobs", { scroll: false });
  }, [router]);

  const handleImport = async (e: FormEvent) => {
    e.preventDefault();
    if (!importUrl && !importRaw) return;
    setImporting(true);
    try {
      const res = await apiFetch("/api/v1/jobs/ingest", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url: importUrl || null,
          description_raw: importRaw || null,
        }),
      });
      if (res.ok) {
        setImportUrl("");
        setImportRaw("");
        setIsModalOpen(false);
        fetchJobs();
      } else {
        const body = await res.json().catch(() => ({}));
        setActionError(body.detail || "Failed to import job");
      }
    } catch (err) {
      console.error("Failed to import job", err);
      setActionError("Failed to import job");
    } finally {
      setImporting(false);
    }
  };

  const handlePackage = async (jobId: string) => {
    setPackagingId(jobId);
    setActionError(null);
    setActionMessage(null);
    try {
      const res = await apiFetch("/api/v1/documents/apply-package", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ job_id: jobId }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(
          typeof body.detail === "string"
            ? body.detail
            : "Failed to generate apply package"
        );
      }
      const data = await res.json();
      setActionMessage(
        `Package saved${data.company ? ` for ${data.company}` : ""}${
          data.folder ? ` → ${data.folder}` : ""
        }`
      );
    } catch (err) {
      setActionError(
        err instanceof Error ? err.message : "Failed to generate apply package"
      );
    } finally {
      setPackagingId(null);
    }
  };

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500 relative">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold tracking-tight mb-2">Jobs</h1>
          <p className="text-muted-foreground text-lg">
            Wishlist roles, then: Tailor resume → Resume Studio → Package → Apply.
          </p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors bg-primary text-primary-foreground shadow hover:bg-primary/90 h-10 px-6 py-2 gap-2"
        >
          <Plus className="h-4 w-4" /> Import New Job
        </button>
      </div>

      {jobs.length > 0 && (
        <div className="rounded-xl border bg-muted/20 px-4 py-3 text-sm flex flex-wrap items-center gap-x-4 gap-y-2">
          <span className="font-medium">Next steps</span>
          <Link href="/tailor" className="text-primary hover:underline">
            1. Tailor JD
          </Link>
          <Link href="/resumes" className="text-primary hover:underline">
            2. Resume Studio
          </Link>
          <span className="text-muted-foreground">3. Package / Apply</span>
          <Link href="/tracker" className="text-primary hover:underline ml-auto">
            Open Tracker →
          </Link>
        </div>
      )}

      {loadError && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive flex flex-wrap items-center justify-between gap-2">
          <span>{loadError}</span>
          <button
            type="button"
            onClick={() => fetchJobs()}
            className="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-muted text-foreground"
          >
            <RefreshCw className="h-3.5 w-3.5" /> Retry
          </button>
        </div>
      )}
      {actionMessage && (
        <div className="rounded-md border border-green-500/30 bg-green-500/10 px-4 py-3 text-sm">
          {actionMessage}
        </div>
      )}
      {actionError && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {actionError}
        </div>
      )}

      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="relative w-full max-w-sm">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              className="w-full rounded-md border border-input bg-transparent pl-9 pr-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              placeholder="Search by role or company..."
            />
          </div>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-44 rounded-xl bg-muted animate-pulse" />
            ))}
          </div>
        ) : jobs.length === 0 ? (
          <div className="text-center py-20 border rounded-xl border-dashed bg-card/50">
            <Briefcase className="mx-auto h-16 w-16 text-muted-foreground mb-4 opacity-50" />
            <h3 className="text-xl font-medium">No Jobs Tracked Yet</h3>
            <p className="text-muted-foreground mt-2 mb-6 max-w-md mx-auto">
              From Vault: open a portal, copy a job URL, then Import here. Or add
              matches from Discovery.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <button
                onClick={() => setIsModalOpen(true)}
                className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80 h-10 px-6 py-2 gap-2"
              >
                <Import className="h-4 w-4" /> Import Your First Job
              </button>
              <Link
                href="/vault"
                className="inline-flex items-center justify-center rounded-md text-sm font-medium border h-10 px-6 py-2 hover:bg-muted"
              >
                Open Vault portals
              </Link>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {jobs.map((job) => {
              const company =
                job.description_normalized?.company_name || "Unknown Company";
              const busy = packagingId === job.id;
              return (
                <div
                  key={job.id}
                  className="rounded-xl border bg-card p-5 shadow-sm hover:shadow-md transition-all flex flex-col justify-between h-full"
                >
                  <div>
                    <div className="flex justify-between items-start mb-3">
                      <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary font-bold text-lg">
                        {company[0].toUpperCase()}
                      </div>
                      {job.url && (
                        <a
                          href={job.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-muted-foreground hover:text-primary transition-colors"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </a>
                      )}
                    </div>
                    <h3 className="font-semibold text-lg line-clamp-2">
                      {job.role_title || "Untitled Role"}
                    </h3>
                    <p className="text-sm font-medium text-foreground mb-1">
                      {company}
                    </p>
                    <p className="text-xs text-muted-foreground line-clamp-1">
                      {job.description_normalized?.location ||
                        "Location not specified"}
                    </p>
                  </div>

                  <div className="mt-5 pt-4 border-t space-y-3">
                    <div className="text-xs font-semibold px-2.5 py-1 bg-secondary text-secondary-foreground rounded-md inline-block">
                      {job.status === "Imported"
                        ? "Wishlist"
                        : job.status || "Tracked"}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Link
                        href={`/apply?job_id=${encodeURIComponent(job.id)}`}
                        className="inline-flex items-center gap-1.5 rounded-md bg-primary text-primary-foreground px-2.5 py-1.5 text-xs font-medium"
                      >
                        Review &amp; Apply
                      </Link>
                      <Link
                        href="/tailor"
                        className="inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-medium hover:bg-muted"
                      >
                        Tailor
                      </Link>
                      <Link
                        href={`/canvas?job_id=${encodeURIComponent(job.id)}`}
                        className="inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-medium hover:bg-muted"
                      >
                        <Workflow className="h-3.5 w-3.5" />
                        Canvas
                      </Link>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => handlePackage(job.id)}
                        className="inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-medium hover:bg-muted disabled:opacity-50"
                      >
                        {busy ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <FileStack className="h-3.5 w-3.5" />
                        )}
                        Package
                      </button>
                      <Link
                        href="/outreach"
                        className="inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-medium hover:bg-muted"
                      >
                        <Mail className="h-3.5 w-3.5" />
                        Outreach
                      </Link>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-0">
          <div
            className="absolute inset-0 bg-background/80 backdrop-blur-sm"
            onClick={() => !importing && setIsModalOpen(false)}
          />

          <div className="relative bg-card border rounded-xl shadow-lg w-full max-w-lg p-6 animate-in zoom-in-95 duration-200">
            <button
              onClick={() => !importing && setIsModalOpen(false)}
              className="absolute top-4 right-4 text-muted-foreground hover:text-foreground transition-colors"
            >
              <X className="h-5 w-5" />
            </button>

            <h2 className="text-2xl font-bold mb-2">Import New Job</h2>
            <p className="text-muted-foreground text-sm mb-6">
              Paste a posting URL from a Vault portal (or LinkedIn/ATS). We scrape
              with Playwright when the page allows; otherwise paste the description.
            </p>

            <form onSubmit={handleImport} className="space-y-5">
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  Job URL (from portal / ATS)
                </label>
                <input
                  type="url"
                  className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  placeholder="https://..."
                  value={importUrl}
                  onChange={(e) => setImportUrl(e.target.value)}
                  disabled={importing}
                />
              </div>

              <div className="relative py-2">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t border-border" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-card px-3 text-muted-foreground font-medium">
                    Or
                  </span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1.5">
                  Paste Description
                </label>
                <textarea
                  className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring min-h-[140px] resize-y"
                  placeholder="Paste raw text here..."
                  value={importRaw}
                  onChange={(e) => setImportRaw(e.target.value)}
                  disabled={importing}
                />
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  disabled={importing}
                  className="px-4 py-2 rounded-md text-sm font-medium hover:bg-muted transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={importing || (!importUrl && !importRaw)}
                  className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors bg-primary text-primary-foreground shadow hover:bg-primary/90 h-9 px-6 py-2 disabled:opacity-50"
                >
                  {importing ? (
                    <>
                      <RefreshCw className="mr-2 h-4 w-4 animate-spin" />{" "}
                      Importing...
                    </>
                  ) : (
                    "Add to Wishlist"
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
