"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Database,
  Search,
  Plus,
  Sparkles,
  RefreshCw,
  Globe,
  ExternalLink,
  Loader2,
  Import,
} from "lucide-react";
import api, { getApiErrorMessage } from "@/lib/api";

interface WikiEntity {
  id: string;
  entity_type: string;
  title: string;
  content: Record<string, unknown>;
  vector_id?: string | null;
  created_at: string;
  score?: number;
}

function portalUrl(content: Record<string, unknown>): string | null {
  const url = content?.url;
  return typeof url === "string" && url.startsWith("http") ? url : null;
}

export default function VaultPage() {
  const [entities, setEntities] = useState<WikiEntity[]>([]);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [semanticMode, setSemanticMode] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newType, setNewType] = useState("skill");
  const [newContent, setNewContent] = useState("");
  const [saving, setSaving] = useState(false);

  const fetchEntities = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSemanticMode(false);
    try {
      const { data } = await api.get<WikiEntity[]>("/knowledge/me");
      setEntities(data);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Failed to fetch knowledge graph"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEntities();
  }, [fetchEntities]);

  const seedJobPortals = async () => {
    setSeeding(true);
    setError(null);
    setNotice(null);
    try {
      const { data } = await api.post<{
        created: number;
        skipped: number;
        total: number;
        ats_created?: number;
      }>("/knowledge/me/seed-job-portals");
      const ats = data.ats_created ?? 0;
      setNotice(
        data.created > 0
          ? `Added ${data.created} job portals${
              ats ? ` (including ${ats} ATS career pages)` : ""
            } — ${data.skipped} already present.`
          : `All ${data.total} job portals already in your vault, including Greenhouse / Lever / Ashby / Workday.`
      );
      await fetchEntities();
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Failed to seed job portals"));
    } finally {
      setSeeding(false);
    }
  };

  const runSemanticSearch = async (e?: React.FormEvent) => {
    e?.preventDefault();
    const q = query.trim();
    if (!q) {
      fetchEntities();
      return;
    }
    setSearching(true);
    setError(null);
    try {
      const { data } = await api.post<WikiEntity[]>("/knowledge/me/search", {
        query: q,
        limit: 12,
      });
      setEntities(data);
      setSemanticMode(true);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Semantic search failed"));
    } finally {
      setSearching(false);
    }
  };

  const createEntity = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const content: Record<string, string> =
        newType === "job_portal"
          ? {
              url: newContent.trim() || newTitle.trim(),
              note: "Custom job portal",
              category: "job_board",
            }
          : { note: newContent.trim() || newTitle.trim() };
      await api.post("/knowledge/me", {
        entity_type: newType,
        title: newTitle.trim(),
        content,
      });
      setNewTitle("");
      setNewContent("");
      setShowAdd(false);
      await fetchEntities();
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Failed to create entity"));
    } finally {
      setSaving(false);
    }
  };

  const filteredLocal =
    !semanticMode && query.trim()
      ? entities.filter(
          (e) =>
            e.title.toLowerCase().includes(query.toLowerCase()) ||
            e.entity_type.toLowerCase().includes(query.toLowerCase()) ||
            String(e.content?.url || "")
              .toLowerCase()
              .includes(query.toLowerCase())
        )
      : entities;

  const portals = filteredLocal.filter((e) => e.entity_type === "job_portal");
  const others = filteredLocal.filter((e) => e.entity_type !== "job_portal");

  return (
    <div className="flex-1 p-4 md:p-8 space-y-6 overflow-y-auto">
      <div className="flex justify-between items-center gap-3 flex-wrap">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Knowledge Graph Vault</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Long-term memory and job-portal bookmarks — not auto-scrapers
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={seedJobPortals}
            disabled={seeding}
            className="flex items-center gap-2 border border-border bg-card px-3 py-2 rounded-md text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors disabled:opacity-50"
          >
            {seeding ? <Loader2 className="w-4 h-4 animate-spin" /> : <Globe className="w-4 h-4" />}
            Seed job portals
          </button>
          <button
            onClick={fetchEntities}
            className="flex items-center gap-2 border border-border bg-card px-3 py-2 rounded-md text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button
            onClick={() => setShowAdd((v) => !v)}
            className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-md font-medium text-sm hover:bg-primary/90 transition-colors"
          >
            <Plus className="w-4 h-4" /> Add Entity
          </button>
        </div>
      </div>

      {notice && (
        <div className="text-sm text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-md px-3 py-2">
          {notice}
        </div>
      )}

      <div className="rounded-xl border bg-muted/20 px-4 py-3 text-sm space-y-1">
        <p className="font-medium">How to use portals</p>
        <p className="text-muted-foreground">
          Open a portal → search → copy the job posting URL → Import on Jobs.
          Discovery searches ATS career pages first (Greenhouse, Lever, Ashby,
          Workday), then other Vault portals, then Remotive / RemoteOK /
          Arbeitnow. Seed portals here so Find stays aligned. We do not crawl
          50k company sites or silent-submit.
        </p>
        <div className="flex flex-wrap gap-2 pt-1">
          <Link
            href="/jobs?import=1"
            className="inline-flex items-center gap-1.5 rounded-md bg-primary text-primary-foreground px-3 py-1.5 text-xs font-medium"
          >
            <Import className="w-3.5 h-3.5" />
            Import job URL
          </Link>
          <Link
            href="/discovery"
            className="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-muted"
          >
            Or use Discovery
          </Link>
        </div>
      </div>

      {showAdd && (
        <form
          onSubmit={createEntity}
          className="border border-border bg-card rounded-xl p-4 space-y-3 max-w-xl"
        >
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <select
              value={newType}
              onChange={(e) => setNewType(e.target.value)}
              className="rounded-md border border-border bg-background px-3 py-2 text-sm"
            >
              <option value="skill">Skill</option>
              <option value="company">Company</option>
              <option value="project">Project</option>
              <option value="story">Story</option>
              <option value="experience">Experience</option>
              <option value="job_portal">Job portal</option>
            </select>
            <input
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="Title"
              className="sm:col-span-2 rounded-md border border-border bg-background px-3 py-2 text-sm"
              required
            />
          </div>
          <textarea
            value={newContent}
            onChange={(e) => setNewContent(e.target.value)}
            placeholder={
              newType === "job_portal"
                ? "Portal URL (https://…)"
                : "Details / anecdote (embedded into vector memory)"
            }
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm min-h-[80px]"
          />
          <button
            type="submit"
            disabled={saving}
            className="text-sm font-medium px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {saving ? "Saving & indexing…" : "Save to Vault"}
          </button>
        </form>
      )}

      <form onSubmit={runSemanticSearch} className="flex flex-col sm:flex-row gap-2 max-w-2xl">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Semantic search: e.g. remote job boards, Kubernetes…"
            className="w-full pl-9 pr-4 py-2 rounded-md border border-border bg-card focus:outline-none focus:ring-1 focus:ring-primary text-sm"
          />
        </div>
        <button
          type="submit"
          disabled={searching}
          className="flex items-center justify-center gap-2 px-4 py-2 rounded-md border border-border bg-card text-sm font-medium hover:bg-muted transition-colors disabled:opacity-50"
        >
          <Sparkles className={`w-4 h-4 ${searching ? "animate-pulse text-amber-400" : "text-primary"}`} />
          {searching ? "Searching…" : "Semantic Search"}
        </button>
      </form>

      {semanticMode && (
        <div className="text-xs text-muted-foreground flex items-center gap-2">
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          Showing vector similarity results
          <button onClick={fetchEntities} className="underline hover:text-foreground">
            Clear
          </button>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center p-12 text-muted-foreground">Loading Knowledge Graph...</div>
      ) : error ? (
        <div className="rounded-xl border border-border bg-card p-12 flex flex-col items-center justify-center text-center space-y-4 text-red-400">
          <Database className="w-12 h-12 opacity-50" />
          <div>
            <h3 className="font-semibold text-lg text-foreground">API Error</h3>
            <p className="text-sm mt-1">{error}</p>
          </div>
        </div>
      ) : filteredLocal.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-12 flex flex-col items-center justify-center text-center space-y-4">
          <Database className="w-12 h-12 text-muted-foreground" />
          <div>
            <h3 className="font-semibold text-lg text-foreground">
              {semanticMode ? "No similar memories" : "Vault is Empty"}
            </h3>
            <p className="text-sm text-muted-foreground max-w-sm mt-1">
              {semanticMode
                ? "Try a different query, or add entities that match this topic."
                : "Seed job portals or add an entity to populate your Knowledge Graph."}
            </p>
          </div>
          {!semanticMode && (
            <button
              onClick={seedJobPortals}
              disabled={seeding}
              className="text-sm text-primary hover:underline disabled:opacity-50"
            >
              Seed Instahyre, Wellfound, YC Jobs…
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-8">
          {portals.length > 0 && (
            <section className="space-y-3">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                <Globe className="w-4 h-4" /> Job portals ({portals.length})
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {portals.map((entity) => {
                  const url = portalUrl(entity.content);
                  return (
                    <div
                      key={entity.id}
                      className="border border-border bg-card rounded-lg p-4 space-y-3 hover:border-primary/50 transition-colors"
                    >
                      <div className="flex justify-between items-start gap-2">
                        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-sky-500/10 text-sky-400 capitalize">
                          {entity.entity_type.replace("_", " ")}
                        </span>
                        <span className="text-[10px] text-muted-foreground">
                          {String(entity.content?.region || "")}
                        </span>
                      </div>
                      <h4 className="font-medium text-foreground">{entity.title}</h4>
                      {url ? (
                        <p className="text-xs text-muted-foreground truncate" title={url}>
                          {url.replace(/^https?:\/\//, "")}
                        </p>
                      ) : (
                        <p className="text-sm text-muted-foreground line-clamp-2">
                          {JSON.stringify(entity.content).replace(/["{}]/g, " ")}
                        </p>
                      )}
                      <div className="flex flex-wrap gap-2 pt-1">
                        {url && (
                          <a
                            href={url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-medium hover:bg-muted"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                            Open portal
                          </a>
                        )}
                        <Link
                          href="/jobs?import=1"
                          className="inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-medium hover:bg-muted"
                        >
                          <Import className="w-3.5 h-3.5" />
                          Import job URL
                        </Link>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          {others.length > 0 && (
            <section className="space-y-3">
              {portals.length > 0 && (
                <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                  Other memories ({others.length})
                </h2>
              )}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {others.map((entity) => (
                  <div
                    key={entity.id}
                    className="border border-border bg-card rounded-lg p-4 space-y-2 hover:border-primary/50 transition-colors"
                  >
                    <div className="flex justify-between items-start gap-2">
                      <span className="text-xs font-semibold px-2 py-0.5 rounded bg-primary/10 text-primary capitalize">
                        {entity.entity_type}
                      </span>
                      <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                        {typeof entity.score === "number" && (
                          <span className="text-amber-400/90 tabular-nums">
                            {(entity.score * 100).toFixed(0)}% match
                          </span>
                        )}
                        {entity.vector_id && (
                          <span className="text-emerald-500/80" title="Indexed in Qdrant">
                            ● vec
                          </span>
                        )}
                        <span>{new Date(entity.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <h4 className="font-medium text-foreground">{entity.title}</h4>
                    <p className="text-sm text-muted-foreground line-clamp-3">
                      {JSON.stringify(entity.content).replace(/["{}]/g, " ")}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
