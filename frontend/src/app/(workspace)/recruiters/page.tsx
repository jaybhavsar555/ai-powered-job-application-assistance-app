"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Users, Search, Copy, Linkedin, Mail, Save, ExternalLink } from "lucide-react";
import { useAuthStore } from "@/store/auth";
import {
  PageMessageBanner,
  messageFromError,
  type PageMessage,
} from "@/components/ui/PageMessageBanner";

interface Recruiter {
  id: string;
  name: string;
  company_id: string;
  company_name?: string | null;
  linkedin_url: string | null;
  email: string | null;
}

export default function RecruitersPage() {
  const [recruiters, setRecruiters] = useState<Recruiter[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [edits, setEdits] = useState<
    Record<string, { email: string; linkedin_url: string; name: string }>
  >({});
  const [savingId, setSavingId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pageMessage, setPageMessage] = useState<PageMessage | null>(null);
  const token = useAuthStore((s) => s.token);

  useEffect(() => {
    const fetchRecruiters = async () => {
      try {
        setLoading(true);
        const res = await fetch("/api/v1/recruiters/", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setRecruiters(data);
          const next: Record<string, { email: string; linkedin_url: string; name: string }> =
            {};
          for (const r of data as Recruiter[]) {
            next[r.id] = {
              name: r.name || "",
              email: r.email || "",
              linkedin_url: r.linkedin_url || "",
            };
          }
          setEdits(next);
        }
      } catch (err) {
        console.error("Failed to fetch recruiters", err);
      } finally {
        setLoading(false);
      }
    };

    if (token) fetchRecruiters();
  }, [token]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const saveRecruiter = async (id: string) => {
    const e = edits[id];
    if (!e || !token) return;
    setSavingId(id);
    setNotice(null);
    try {
      const res = await fetch(`/api/v1/recruiters/${id}`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: e.name || undefined,
          email: e.email || null,
          linkedin_url: e.linkedin_url || null,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(
          typeof body.detail === "string" ? body.detail : "Save failed"
        );
      }
      const updated = await res.json();
      setRecruiters((prev) => prev.map((r) => (r.id === id ? { ...r, ...updated } : r)));
      setNotice("Contact saved — use Outreach to send (paste gate uses this email/LinkedIn).");
      setPageMessage({
        tone: "success",
        title: "Contact saved",
        detail: "Use Outreach to send — the paste gate uses this email/LinkedIn.",
      });
    } catch (err) {
      setPageMessage(
        messageFromError(
          err instanceof Error ? err.message : "Save failed",
          "Save failed"
        )
      );
    } finally {
      setSavingId(null);
    }
  };

  const filtered = recruiters.filter((r) => {
    const q = query.trim().toLowerCase();
    if (!q) return true;
    const blob = `${r.name} ${r.email || ""} ${r.linkedin_url || ""} ${r.company_name || ""}`.toLowerCase();
    return blob.includes(q);
  });

  return (
    <div className="p-4 md:p-8 max-w-6xl mx-auto space-y-8 animate-in fade-in duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold tracking-tight mb-2">Recruiters</h1>
          <p className="text-muted-foreground text-lg max-w-2xl">
            Paste email or LinkedIn when discovery is empty (Hunter optional via{" "}
            <code className="text-xs">HUNTER_API_KEY</code>). Saved contacts unlock Outreach send.
          </p>
        </div>
        <Link
          href="/outreach"
          className="inline-flex items-center gap-1.5 rounded-md border px-3 py-2 text-sm hover:bg-muted"
        >
          <ExternalLink className="h-4 w-4" /> Outreach
        </Link>
      </div>

      {pageMessage && (
        <PageMessageBanner
          message={pageMessage}
          onDismiss={() => setPageMessage(null)}
        />
      )}

      {notice && (
        <p className="text-sm rounded-md border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-emerald-800 dark:text-emerald-200">
          {notice}
        </p>
      )}

      <div className="flex items-center justify-between">
        <div className="relative w-full max-w-md">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={query}
            onChange={(ev) => setQuery(ev.target.value)}
            className="w-full rounded-md border border-input bg-transparent pl-9 pr-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            placeholder="Search recruiters..."
          />
        </div>
      </div>

      <div className="rounded-xl border bg-card overflow-hidden">
        <table className="w-full text-sm text-left">
          <thead className="bg-muted/50 border-b text-muted-foreground font-medium">
            <tr>
              <th className="px-6 py-4">Name</th>
              <th className="px-6 py-4">Contact (editable)</th>
              <th className="px-6 py-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={3} className="px-6 py-12 text-center text-muted-foreground">
                  <div className="animate-pulse flex space-x-4 justify-center">
                    <div className="h-4 bg-muted rounded w-3/4" />
                  </div>
                </td>
              </tr>
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={3} className="px-6 py-12 text-center">
                  <Users className="mx-auto h-12 w-12 text-muted-foreground mb-4 opacity-50" />
                  <h3 className="text-lg font-medium">No recruiters yet</h3>
                  <p className="text-muted-foreground mt-1 max-w-md mx-auto">
                    Run Canvas recruiter discovery (Hunter if keyed), use Quick Apply posts
                    with email, or paste contacts here after a pipeline creates a row.
                  </p>
                </td>
              </tr>
            ) : (
              filtered.map((r) => {
                const e = edits[r.id] || {
                  name: r.name,
                  email: r.email || "",
                  linkedin_url: r.linkedin_url || "",
                };
                return (
                  <tr
                    key={r.id}
                    className="border-b last:border-0 hover:bg-muted/30 transition-colors"
                  >
                    <td className="px-6 py-4 font-medium text-foreground align-top">
                      <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold shrink-0">
                          {(e.name || r.name || "?").charAt(0)}
                        </div>
                        <div className="space-y-1 min-w-0">
                          <input
                            value={e.name}
                            onChange={(ev) =>
                              setEdits((prev) => ({
                                ...prev,
                                [r.id]: { ...e, name: ev.target.value },
                              }))
                            }
                            className="w-full max-w-[200px] rounded border bg-background px-2 py-1 text-sm"
                          />
                          {r.company_name && (
                            <p className="text-xs text-muted-foreground truncate">
                              {r.company_name}
                            </p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 align-top">
                      <div className="flex flex-col gap-2 max-w-sm">
                        <label className="flex items-center gap-2 text-muted-foreground">
                          <Mail className="h-4 w-4 shrink-0" />
                          <input
                            type="email"
                            value={e.email}
                            onChange={(ev) =>
                              setEdits((prev) => ({
                                ...prev,
                                [r.id]: { ...e, email: ev.target.value },
                              }))
                            }
                            placeholder="paste email"
                            className="flex-1 rounded border bg-background px-2 py-1 text-sm text-foreground"
                          />
                        </label>
                        <label className="flex items-center gap-2 text-muted-foreground">
                          <Linkedin className="h-4 w-4 shrink-0" />
                          <input
                            value={e.linkedin_url}
                            onChange={(ev) =>
                              setEdits((prev) => ({
                                ...prev,
                                [r.id]: { ...e, linkedin_url: ev.target.value },
                              }))
                            }
                            placeholder="paste LinkedIn URL"
                            className="flex-1 rounded border bg-background px-2 py-1 text-sm text-foreground"
                          />
                        </label>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right align-top">
                      <div className="flex items-center justify-end gap-2 flex-wrap">
                        <button
                          type="button"
                          onClick={() => void saveRecruiter(r.id)}
                          disabled={savingId === r.id}
                          className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-md bg-primary text-primary-foreground disabled:opacity-50"
                        >
                          <Save className="h-3.5 w-3.5" />
                          {savingId === r.id ? "Saving…" : "Save"}
                        </button>
                        {e.email && (
                          <button
                            type="button"
                            onClick={() => copyToClipboard(e.email)}
                            className="px-3 py-1.5 text-xs font-medium border rounded-md hover:bg-muted"
                            title="Copy Email"
                          >
                            <Copy className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
