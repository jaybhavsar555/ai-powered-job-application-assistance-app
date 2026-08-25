"use client";

import { useCallback, useEffect, useMemo, useState, useRef } from "react";
import Link from "next/link";
import {
  FileText,
  Download,
  CheckCircle,
  FilePlus,
  UploadCloud,
  Eye,
  Sparkles,
  X,
  Wand2,
  Columns2,
  AlertCircle,
  Workflow,
  Search,
  ChevronDown,
  FileCode,
  Library,
  Package,
  MoreVertical,
  Trash,
} from "lucide-react";
import { StructuredResumeEditor, StructuredResumeData } from "@/components/ui/StructuredResumeEditor";
import { useAuthStore } from "@/store/auth";
import { apiFetch } from "@/lib/api";
import { usePanelStore } from "@/store/panelStore";
import { useWorkflowStore } from "@/hooks/useWorkflowStore";
import { useRouter } from "next/navigation";

interface BaseResume {
  name: string;
  path: string;
  role_hint: string | null;
}

interface PackageMeta {
  folder?: string | null;
  company?: string | null;
  role_family?: string | null;
  base_resume_name?: string | null;
  files?: Record<string, boolean>;
}

interface StudioItem {
  id: string;
  source: "resume_version" | "workflow_draft" | string;
  version_id?: string | null;
  application_id: string;
  job_id: string;
  company: string;
  role_title: string;
  stage: string;
  ats_score: number | null;
  missing_skills: string[];
  matching_skills: string[];
  recommendation?: string | null;
  created_at: string | null;
  approved: boolean;
  has_package: boolean;
  package: PackageMeta | null;
  tailored_preview?: string;
  added_keywords?: string[];
}

interface StudioDetail extends StudioItem {
  original: { label: string; text: string };
  tailored: { content: Record<string, unknown>; preview: string };
  ats: {
    score: number | null;
    missing_skills: string[];
    matching_skills: string[];
    recommendation?: string | null;
    added_keywords?: string[];
    parser_checks?: {
      overall_parser_score?: number;
      keyword_density?: number;
      warnings?: string[];
      suggestions?: string[];
      has_summary_section?: boolean;
      has_experience_section?: boolean;
      has_skills_section?: boolean;
    } | null;
    rationale?: string | null;
  };
  downloads: Record<string, string>;
}

const DOWNLOAD_LABELS: Record<string, string> = {
  resume_pdf: "Resume PDF",
  resume_docx: "Resume DOCX",
  resume_tex: "Resume LaTeX",
  cover_pdf: "Cover PDF",
  cover_docx: "Cover DOCX",
};

type StudioView = "tailored" | "library" | "compare";
type TailoredFilter = "all" | "approved" | "packaged";

function roleLabel(hint: string | null | undefined) {
  const h = (hint || "general").toLowerCase();
  if (h.includes("full")) return "fullstack";
  if (h.includes("flutter") || h.includes("mobile")) return "flutter";
  if (h.includes("ai") || h.includes("ml")) return "ai";
  if (h.includes("sde") || h.includes("software")) return "sde";
  return h || "general";
}

function shortName(name: string) {
  return name
    .replace(/\.pdf$/i, "")
    .replace(/\.docx$/i, "")
    .replace(/Jay[-_]?Padmakar[-_]?Bhavsar[-_]?/i, "")
    .replace(/Jay[-_]?Bhavsar[-_]?/i, "")
    .replace(/[_-]+/g, " ")
    .trim() || name;
}

export default function ResumesPage() {
  const [baseResumes, setBaseResumes] = useState<BaseResume[]>([]);
  const [items, setItems] = useState<StudioItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<StudioDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailSaving, setDetailSaving] = useState(false);
  const token = useAuthStore((s) => s.token);
  const router = useRouter();
  const setTailorState = useWorkflowStore((s) => s.setTailorState);

  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const setPreview = usePanelStore((s) => s.setPreview);
  const closePdf = usePanelStore((s) => s.closePdf);
  const pdfTitle = usePanelStore((s) => s.pdfTitle);

  const [view, setView] = useState<StudioView>("tailored");
  const [tailoredFilter, setTailoredFilter] = useState<TailoredFilter>("all");
  const [libQuery, setLibQuery] = useState("");
  const [libRole, setLibRole] = useState<string>("all");
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);

  // Close menu on outside click
  useEffect(() => {
    const handleClick = () => setMenuOpenId(null);
    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, []);

  const previewResume = async (name: string) => {
    if (!token) return;
    try {
      const res = await apiFetch(
        `/api/v1/documents/library-preview?name=${encodeURIComponent(name)}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) {
        throw new Error(`Preview failed (${res.status})`);
      }
      const data = await res.json();
      setPreview({
        title: data.name || name,
        kind: data.kind || "unsupported",
        fileUrl: data.file_url,
        text: data.text ?? null,
        note: data.note ?? null,
      });
    } catch {
      // Fallback: open authenticated download
      window.open(
        `/api/v1/documents/library-file?name=${encodeURIComponent(name)}`,
        "_blank"
      );
    }
  };

  const authHeaders = useCallback(
    () => ({ Authorization: `Bearer ${token}` }),
    [token]
  );

  const fetchData = useCallback(async () => {
    if (!token) return;
    try {
      setLoading(true);
      setError(null);

      const [libRes, studioRes] = await Promise.all([
        apiFetch("/api/v1/documents/resume-library", { headers: authHeaders() }),
        apiFetch("/api/v1/resumes/studio", { headers: authHeaders() }),
      ]);

      if (libRes.ok) {
        const data = await libRes.json();
        const files = data.files || [];
        setBaseResumes(files);
        if (files[0]) {
          // No longer track selectedBaseResume here since it moved to tailor page
        }
      } else {
        setBaseResumes([]);
      }

      if (studioRes.ok) {
        const data = await studioRes.json();
        setItems(data.items || []);
      } else {
        setItems([]);
        const body = await studioRes.json().catch(() => ({}));
        setError(
          typeof body.detail === "string"
            ? body.detail
            : "Could not load resume versions"
        );
      }
    } catch (err) {
      console.error(err);
      setError("Could not reach API for Resume Studio");
      setBaseResumes([]);
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [token, authHeaders]);

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const roleFilters = useMemo(() => {
    const set = new Set<string>();
    baseResumes.forEach((r) => set.add(roleLabel(r.role_hint)));
    return ["all", ...Array.from(set).sort()];
  }, [baseResumes]);

  const filteredLibrary = useMemo(() => {
    const q = libQuery.trim().toLowerCase();
    return baseResumes.filter((r) => {
      const role = roleLabel(r.role_hint);
      if (libRole !== "all" && role !== libRole) return false;
      if (!q) return true;
      return (
        r.name.toLowerCase().includes(q) ||
        role.includes(q) ||
        (r.role_hint || "").toLowerCase().includes(q)
      );
    });
  }, [baseResumes, libQuery, libRole]);

  const libraryByRole = useMemo(() => {
    const map = new Map<string, BaseResume[]>();
    for (const r of filteredLibrary) {
      const key = roleLabel(r.role_hint);
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(r);
    }
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [filteredLibrary]);

  const packagedCount = items.filter((i) => i.has_package).length;
  const approvedCount = items.filter((i) => i.approved).length;

  const filteredTailored = useMemo(() => {
    if (tailoredFilter === "approved") return items.filter((i) => i.approved);
    if (tailoredFilter === "packaged") return items.filter((i) => i.has_package);
    return items;
  }, [items, tailoredFilter]);

  const applyTailoredFilter = (next: TailoredFilter) => {
    setTailoredFilter((prev) => (prev === next ? "all" : next));
    setView("tailored");
  };

  const saveStudioContent = async (data: StructuredResumeData, rescore = true) => {
    if (!selectedId) return;
    setDetailSaving(true);
    setError(null);
    try {
      const res = await apiFetch(`/api/v1/resumes/studio/${encodeURIComponent(selectedId)}/content`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ tailored_resume: data, rescore }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(typeof body.detail === "string" ? body.detail : "Save failed");
      }
      const payload = await res.json();
      await openDetail(selectedId);
      if (payload.ats_score != null && detail) {
        setDetail({
          ...detail,
          ats: { ...detail.ats, score: payload.ats_score },
        });
      }
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setDetailSaving(false);
    }
  };

  const openDetail = async (id: string) => {
    setSelectedId(id);
    setView("compare");
    setDetailLoading(true);
    setDetail(null);
    try {
      const res = await apiFetch(`/api/v1/resumes/studio/${encodeURIComponent(id)}`, {
        headers: authHeaders(),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(
          typeof body.detail === "string" ? body.detail : "Failed to load compare view"
        );
      }
      setDetail(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load compare view");
      setView("tailored");
    } finally {
      setDetailLoading(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setIsUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await apiFetch("/api/v1/documents/upload", {
        method: "POST",
        headers: authHeaders(),
        body: formData,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(
          typeof body.detail === "string" ? body.detail : "Upload failed"
        );
      }
      await fetchData();
      setView("library");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };



  const downloadWithAuth = async (path: string, filename: string) => {
    try {
      const res = await apiFetch(path, { headers: authHeaders() });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(
          typeof body.detail === "string"
            ? body.detail
            : "Download only available after a successful package"
        );
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    }
  };

  const deleteStudioItem = async (id: string, isApproved: boolean) => {
    if (!confirm(`Are you sure you want to delete this ${isApproved ? "version" : "draft"}?`)) return;
    try {
      const res = await apiFetch(`/api/v1/resumes/studio/${encodeURIComponent(id)}`, {
        method: "DELETE",
        headers: authHeaders(),
      });
      if (!res.ok) {
        throw new Error("Failed to delete item");
      }
      setItems((prev) => prev.filter((i) => i.id !== id));
      if (selectedId === id) {
        setDetail(null);
        setSelectedId(null);
        setView("tailored");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  };

  const previewTailoredResume = (item: StudioItem) => {
    if (!item.has_package || !item.package?.files?.resume_pdf) {
      setError("No PDF package available to preview. Run Canvas/Approvals first.");
      return;
    }
    try {
      setPreview({
        title: `${item.company} Resume`,
        kind: "pdf",
        fileUrl: `/api/v1/documents/package-download?application_id=${item.application_id}&kind=resume_pdf`,
        text: null,
        note: "PDF opens in side panel.",
      });
    } catch {
      setError("Preview failed");
    }
  };

  return (
    <div className="min-h-full flex flex-col bg-background">
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileUpload}
        className="hidden"
        accept=".pdf,.docx"
      />

      {/* Compact header */}
      <header className="border-b bg-card/80 backdrop-blur sticky top-0 z-20">
        <div className="px-4 md:px-6 py-4 max-w-7xl mx-auto space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
            <div>
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight">
                Resume Studio
              </h1>
              <p className="text-sm text-muted-foreground mt-1">
                Upload templates, tailor to a JD, edit sections, compare, and download PDF/DOCX/LaTeX.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link
                href="/tailor"
                className="inline-flex items-center gap-2 rounded-md border bg-background h-9 px-3 text-sm font-medium hover:bg-muted"
              >
                <Wand2 className="h-4 w-4" />
                Tailor JD
              </Link>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                className="inline-flex items-center gap-2 rounded-md bg-primary text-primary-foreground h-9 px-3 text-sm font-medium disabled:opacity-50"
              >
                {isUploading ? (
                  <span className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <UploadCloud className="h-4 w-4" />
                )}
                Upload
              </button>
            </div>
          </div>

          {/* Stats — click to filter Tailored */}
          <div className="flex flex-wrap gap-2 text-xs">
            <StatChip
              icon={<Library className="h-3.5 w-3.5" />}
              label={`${baseResumes.length} templates`}
              active={view === "library"}
              onClick={() => {
                setTailoredFilter("all");
                setView("library");
              }}
            />
            <StatChip
              icon={<CheckCircle className="h-3.5 w-3.5" />}
              label={`${items.length} tailored`}
              active={view === "tailored" && tailoredFilter === "all"}
              onClick={() => {
                setTailoredFilter("all");
                setView("tailored");
              }}
            />
            <StatChip
              icon={<Sparkles className="h-3.5 w-3.5" />}
              label={`${approvedCount} approved`}
              active={view === "tailored" && tailoredFilter === "approved"}
              title="Show approved tailored resumes (toggle)"
              onClick={() => applyTailoredFilter("approved")}
            />
            <StatChip
              icon={<Package className="h-3.5 w-3.5" />}
              label={`${packagedCount} packaged`}
              active={view === "tailored" && tailoredFilter === "packaged"}
              title="Show apply packages ready to download (toggle)"
              onClick={() => applyTailoredFilter("packaged")}
            />
            {pdfTitle && (
              <StatChip
                icon={<Eye className="h-3.5 w-3.5" />}
                label={`Preview: ${shortName(pdfTitle)}`}
                title="Clear side-panel preview"
                onClick={() => closePdf()}
              />
            )}
          </div>

          {/* View switcher */}
          <div className="flex gap-1 p-1 rounded-lg bg-muted/60 w-full sm:w-fit">
            {(
              [
                { id: "tailored" as const, label: "Tailored", count: items.length },
                { id: "library" as const, label: "Library", count: baseResumes.length },
                {
                  id: "compare" as const,
                  label: "Compare",
                  count: detail || detailLoading ? 1 : 0,
                },
              ] as const
            ).map((tab) => (
              <button
                key={tab.id}
                type="button"
                disabled={tab.id === "compare" && !detail && !detailLoading}
                onClick={() => {
                  setView(tab.id);
                }}
                className={`flex-1 sm:flex-none px-4 py-2 rounded-md text-sm font-medium transition-colors disabled:opacity-40 ${
                  view === tab.id
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {tab.label}
                <span className="ml-1.5 text-xs opacity-70">{tab.count}</span>
              </button>
            ))}
          </div>
        </div>
      </header>

      <div className="flex-1 px-4 md:px-6 py-5 max-w-7xl mx-auto w-full space-y-4">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
          {[
            {
              href: "/tailor",
              icon: <Wand2 className="h-4 w-4" />,
              title: "Tailor to a JD",
              desc: "ATS score, skill gaps, then generate",
            },
            {
              href: "/tailor",
              icon: <FileText className="h-4 w-4" />,
              title: "Section editor",
              desc: "Edit summary, bullets, keywords",
            },
            {
              href: "/tailor",
              icon: <FileCode className="h-4 w-4" />,
              title: "LaTeX / PDF",
              desc: "Preview TeX and export ATS-friendly PDF",
            },
            {
              title: "Compare versions",
              icon: <Columns2 className="h-4 w-4" />,
              desc: "Original vs tailored + parser checks",
              onClick: () => setView(items.length ? "compare" : "tailored"),
            },
          ].map((card) => {
            const inner = (
              <>
                <p className="text-xs font-semibold flex items-center gap-1.5">
                  {card.icon}
                  {card.title}
                </p>
                <p className="text-[11px] text-muted-foreground mt-1 leading-snug">{card.desc}</p>
              </>
            );
            const cls =
              "rounded-lg border bg-card p-3 text-left hover:border-primary/40 transition-colors";
            if (card.href) {
              return (
                <Link key={card.title} href={card.href} className={cls}>
                  {inner}
                </Link>
              );
            }
            return (
              <button key={card.title} type="button" className={cls} onClick={card.onClick}>
                {inner}
              </button>
            );
          })}
        </div>
        {error && (
          <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm flex items-start gap-2">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            <span>{error}</span>
            <button type="button" className="ml-auto" onClick={() => setError(null)}>
              <X className="h-4 w-4" />
            </button>
          </div>
        )}
        {/* ===== TAILORED (primary) ===== */}
        {view === "tailored" && (
          <section className="space-y-3">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <h2 className="text-lg font-semibold">
                {tailoredFilter === "approved"
                  ? "Approved resumes"
                  : tailoredFilter === "packaged"
                    ? "Packaged for apply"
                    : "For your applications"}
              </h2>
              <div className="flex items-center gap-3">
                {tailoredFilter !== "all" && (
                  <button
                    type="button"
                    onClick={() => setTailoredFilter("all")}
                    className="text-xs text-muted-foreground hover:text-foreground underline-offset-2 hover:underline"
                  >
                    Clear filter
                  </button>
                )}
                <Link
                  href="/canvas"
                  className="text-xs text-primary hover:underline inline-flex items-center gap-1"
                >
                  <Workflow className="h-3.5 w-3.5" /> Run Canvas
                </Link>
              </div>
            </div>

            {loading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-16 rounded-lg bg-muted animate-pulse" />
                ))}
              </div>
            ) : items.length === 0 ? (
              <EmptyTailored onLibrary={() => setView("library")} />
            ) : filteredTailored.length === 0 ? (
              <div className="rounded-xl border border-dashed bg-card/50 px-6 py-10 text-center space-y-3">
                <p className="font-medium">
                  {tailoredFilter === "approved"
                    ? "No approved resumes yet"
                    : "No apply packages yet"}
                </p>
                <p className="text-sm text-muted-foreground max-w-md mx-auto">
                  {tailoredFilter === "approved"
                    ? "Approve resume/cover on Approvals after Canvas, then they show here."
                    : "On Jobs or Tracker, click Package for a role — downloads appear here."}
                </p>
                <div className="flex flex-wrap justify-center gap-2">
                  <button
                    type="button"
                    onClick={() => setTailoredFilter("all")}
                    className="rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-muted"
                  >
                    Show all tailored
                  </button>
                  <Link
                    href={tailoredFilter === "approved" ? "/approvals" : "/jobs"}
                    className="rounded-md bg-primary text-primary-foreground px-3 py-1.5 text-xs font-medium"
                  >
                    {tailoredFilter === "approved" ? "Open Approvals" : "Open Jobs"}
                  </Link>
                </div>
              </div>
            ) : (
              <ul className="divide-y divide-border rounded-xl border bg-card overflow-hidden">
                {filteredTailored.map((item) => (
                  <li
                    key={item.id}
                    className={`p-3 md:p-4 flex flex-col sm:flex-row sm:items-center gap-3 hover:bg-muted/30 ${
                      selectedId === item.id ? "bg-primary/5" : ""
                    }`}
                  >
                    <AtsBadge score={item.ats_score} compact />
                    <div className="min-w-0 flex-1">
                      <p className="font-medium truncate">
                        {item.company}
                        <span className="text-muted-foreground font-normal">
                          {" "}
                          · {item.role_title}
                        </span>
                      </p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {item.approved ? "Approved" : "Draft"} · {item.stage}
                        {item.has_package ? " · Package ready" : ""}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      <IconBtn
                        label="Compare"
                        onClick={() => openDetail(item.id)}
                        icon={<Columns2 className="h-3.5 w-3.5" />}
                      />
                      <Link
                        href={`/canvas?job_id=${encodeURIComponent(item.job_id)}`}
                        className="inline-flex items-center gap-1 rounded-md border px-2.5 py-1.5 text-xs hover:bg-muted"
                      >
                        <Workflow className="h-3.5 w-3.5" /> Canvas
                      </Link>
                      {item.has_package &&
                        Object.entries(item.package?.files || {})
                          .filter(([, ok]) => ok)
                          .map(([kind]) => (
                            <button
                              key={kind}
                              type="button"
                              onClick={() =>
                                downloadWithAuth(
                                  `/api/v1/documents/package-download?application_id=${item.application_id}&kind=${kind}`,
                                  `${item.company}_${kind}`
                                )
                              }
                              className="inline-flex items-center gap-1 rounded-md bg-primary text-primary-foreground px-2.5 py-1.5 text-xs"
                            >
                              <Download className="h-3.5 w-3.5" />
                              {DOWNLOAD_LABELS[kind] || kind}
                            </button>
                          ))}
                      {item.has_package && (
                        <button
                          type="button"
                          onClick={() => {
                            // Extension handles auto-fill; open Apply / install guide
                            window.location.href = "/apply";
                          }}
                          className="inline-flex items-center gap-1 rounded-md bg-emerald-600 text-white px-2.5 py-1.5 text-xs font-medium hover:bg-emerald-700 ml-2"
                        >
                          <Sparkles className="h-3.5 w-3.5" /> Apply Now
                        </button>
                      )}
                      <div className="relative">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setMenuOpenId(menuOpenId === item.id ? null : item.id);
                          }}
                          className="p-1.5 rounded-md hover:bg-muted"
                        >
                          <MoreVertical className="h-4 w-4" />
                        </button>
                        {menuOpenId === item.id && (
                          <div className="absolute right-0 top-full mt-1 w-32 rounded-md border bg-popover text-popover-foreground shadow-md z-50 overflow-hidden">
                            <button
                              type="button"
                              onClick={() => {
                                previewTailoredResume(item);
                                setMenuOpenId(null);
                              }}
                              className="w-full text-left px-3 py-2 text-sm hover:bg-muted flex items-center gap-2"
                            >
                              <Eye className="h-4 w-4" /> Preview
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                deleteStudioItem(item.id, item.approved);
                                setMenuOpenId(null);
                              }}
                              className="w-full text-left px-3 py-2 text-sm hover:bg-muted text-destructive flex items-center gap-2"
                            >
                              <Trash className="h-4 w-4" /> Delete
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}

            {/* Collapsed library peek */}
            <button
              type="button"
              onClick={() => setView("library")}
              className="w-full flex items-center justify-between rounded-xl border border-dashed px-4 py-3 text-sm text-muted-foreground hover:bg-muted/40 hover:text-foreground"
            >
              <span className="inline-flex items-center gap-2">
                <Library className="h-4 w-4" />
                Master library · {baseResumes.length} files
              </span>
              <ChevronDown className="h-4 w-4" />
            </button>
          </section>
        )}

        {/* ===== LIBRARY ===== */}
        {view === "library" && (
          <section className="space-y-4">
            <div className="flex flex-col md:flex-row gap-3 md:items-center">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  value={libQuery}
                  onChange={(e) => setLibQuery(e.target.value)}
                  placeholder="Search templates…"
                  className="w-full h-10 pl-9 pr-3 rounded-lg border bg-card text-sm"
                />
              </div>
              <div className="flex flex-wrap gap-1.5">
                {roleFilters.map((role) => (
                  <button
                    key={role}
                    type="button"
                    onClick={() => setLibRole(role)}
                    className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
                      libRole === role
                        ? "bg-primary text-primary-foreground border-primary"
                        : "bg-card text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {role === "all" ? "All roles" : role}
                  </button>
                ))}
              </div>
            </div>

            {loading ? (
              <div className="h-40 rounded-xl bg-muted animate-pulse" />
            ) : baseResumes.length === 0 ? (
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="w-full text-center py-12 border-2 border-dashed rounded-xl"
              >
                <FilePlus className="mx-auto h-8 w-8 text-muted-foreground mb-2" />
                <p className="font-medium">No templates yet</p>
                <p className="text-sm text-muted-foreground">Upload a PDF or DOCX</p>
              </button>
            ) : filteredLibrary.length === 0 ? (
              <p className="text-sm text-muted-foreground py-8 text-center">
                No templates match “{libQuery || libRole}”.
              </p>
            ) : (
              <div className="space-y-4">
                {libraryByRole.map(([role, files]) => (
                  <div key={role} className="rounded-xl border bg-card overflow-hidden">
                    <div className="px-4 py-2.5 border-b bg-muted/30 flex items-center justify-between">
                      <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        {role}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {files.length}
                      </span>
                    </div>
                    <ul className="divide-y divide-border">
                      {files.map((resume) => {
                        const active = pdfTitle === resume.name;
                        return (
                          <li
                            key={resume.name}
                            className={`flex items-center gap-3 px-3 py-2.5 hover:bg-muted/40 ${
                              active ? "bg-primary/5" : ""
                            }`}
                          >
                            <button
                              type="button"
                              onClick={() => {
                                previewResume(resume.name);
                              }}
                              className="flex items-center gap-3 min-w-0 flex-1 text-left"
                            >
                              <div className="h-9 w-9 rounded-md bg-muted flex items-center justify-center shrink-0">
                                <FileText className="h-4 w-4 text-muted-foreground" />
                              </div>
                              <div className="min-w-0">
                                <p className="text-sm font-medium truncate">
                                  {shortName(resume.name)}
                                </p>
                                <p
                                  className="text-[11px] text-muted-foreground truncate"
                                  title={resume.name}
                                >
                                  {resume.name}
                                </p>
                              </div>
                            </button>
                            <div className="flex items-center gap-1 shrink-0">
                              <button
                                type="button"
                                title="Preview in side panel"
                                onClick={() => previewResume(resume.name)}
                                className="p-2 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground"
                              >
                                <Eye className="h-4 w-4" />
                              </button>
                              <button
                                type="button"
                                title="Download"
                                onClick={async () => {
                                  if (!token) return;
                                  const res = await apiFetch(
                                    `/api/v1/documents/library-file?name=${encodeURIComponent(resume.name)}`,
                                    {
                                      headers: {
                                        Authorization: `Bearer ${token}`,
                                      },
                                    }
                                  );
                                  if (!res.ok) return;
                                  const blob = await res.blob();
                                  const url = URL.createObjectURL(blob);
                                  const a = document.createElement("a");
                                  a.href = url;
                                  a.download = resume.name;
                                  a.click();
                                  URL.revokeObjectURL(url);
                                }}
                                className="p-2 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground"
                              >
                                <Download className="h-4 w-4" />
                              </button>
                              <button
                                type="button"
                                title="Use for Tailor JD"
                                aria-label="Use for Tailor JD"
                                onClick={() => {
                                  setTailorState({ selectedBaseResume: resume.name, step: 1 });
                                  router.push("/tailor");
                                }}
                                className="p-2 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground"
                              >
                                <Wand2 className="h-4 w-4" />
                              </button>
                            </div>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* ===== COMPARE ===== */}
        {view === "compare" && (
          <section className="rounded-xl border bg-card overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b">
              <h2 className="font-semibold flex items-center gap-2 text-sm md:text-base">
                <Columns2 className="h-4 w-4" />
                Original vs tailored
              </h2>
              <button
                type="button"
                onClick={() => {
                  setDetail(null);
                  setSelectedId(null);
                  setView("tailored");
                }}
                className="p-2 rounded-md hover:bg-muted"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {detailLoading || !detail ? (
              <div className="h-56 flex items-center justify-center text-sm text-muted-foreground">
                Loading compare…
              </div>
            ) : (
              <div className="p-4 md:p-5 space-y-5">
                <div className="flex flex-wrap items-center gap-3">
                  <p className="font-medium">
                    {detail.company} — {detail.role_title}
                  </p>
                  <AtsBadge score={detail.ats.score} compact />
                </div>

                {(detail.ats.missing_skills?.length > 0 ||
                  detail.ats.matching_skills?.length > 0 ||
                  detail.ats.added_keywords?.length ||
                  detail.ats.recommendation) && (
                  <div className="rounded-lg border bg-muted/30 p-4 space-y-3 text-sm">
                    <p className="font-medium">ATS evidence</p>
                    {detail.ats.recommendation && (
                      <p className="text-muted-foreground">
                        {detail.ats.recommendation}
                      </p>
                    )}
                    {detail.ats.matching_skills?.length > 0 && (
                      <SkillRow
                        label="Matching"
                        skills={detail.ats.matching_skills}
                        tone="good"
                      />
                    )}
                    {detail.ats.missing_skills?.length > 0 && (
                      <SkillRow
                        label="Missing"
                        skills={detail.ats.missing_skills}
                        tone="warn"
                      />
                    )}
                    {(detail.ats.added_keywords?.length || 0) > 0 && (
                      <SkillRow
                        label="Added keywords"
                        skills={detail.ats.added_keywords || []}
                        tone="neutral"
                      />
                    )}
                    {detail.ats.parser_checks && (
                      <div className="rounded-md border bg-background/50 p-3 space-y-2 text-xs">
                        <p className="font-medium">Parser checks</p>
                        <p className="text-muted-foreground">
                          Parser score {detail.ats.parser_checks.overall_parser_score ?? "?"}/100 ·
                          keyword density {Math.round((detail.ats.parser_checks.keyword_density || 0) * 100)}%
                        </p>
                        {(detail.ats.parser_checks.warnings || []).slice(0, 3).map((w, i) => (
                          <p key={i} className="text-amber-600 dark:text-amber-400">{w}</p>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                <div className="rounded-lg border p-4 space-y-3">
                  <h3 className="text-sm font-semibold">Structured editor</h3>
                  <StructuredResumeEditor
                    value={(detail.tailored.content || {}) as StructuredResumeData}
                    onChange={() => {}}
                    onSave={(data) => saveStudioContent(data, true)}
                    onRescore={(data) => saveStudioContent(data, true)}
                    saving={detailSaving}
                    rescoreLabel="Save & re-score ATS"
                  />
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                  <div className="rounded-lg border p-3 space-y-2 min-h-0">
                    <h3 className="text-sm font-semibold">Original</h3>
                    <p className="text-xs text-muted-foreground">
                      {detail.original.label}
                    </p>
                    <div className="text-sm leading-relaxed whitespace-pre-wrap max-h-72 overflow-y-auto os-scrollbar text-muted-foreground">
                      {detail.original.text}
                    </div>
                  </div>
                  <div className="rounded-lg border p-3 space-y-2">
                    <h3 className="text-sm font-semibold">Tailored</h3>
                    <p className="text-xs text-muted-foreground">
                      {detail.approved ? "Saved version" : "Workflow draft"}
                    </p>
                    <div className="text-sm leading-relaxed whitespace-pre-wrap max-h-72 overflow-y-auto os-scrollbar">
                      {detail.tailored.preview || "No tailored content yet."}
                    </div>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2">
                  {Object.keys(detail.downloads).length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      Downloads appear after a successful apply package.
                    </p>
                  ) : (
                    Object.entries(detail.downloads).map(([kind, path]) => (
                      <button
                        key={kind}
                        type="button"
                        onClick={() =>
                          downloadWithAuth(path, `${detail.company}_${kind}`)
                        }
                        className="inline-flex items-center gap-2 rounded-md bg-primary text-primary-foreground px-3 py-2 text-sm font-medium"
                      >
                        <Download className="h-4 w-4" />
                        {DOWNLOAD_LABELS[kind] || kind}
                      </button>
                    ))
                  )}
                </div>
              </div>
            )}
          </section>
        )}
      </div>

    </div>
  );
}

function StatChip({
  icon,
  label,
  onClick,
  active,
  title,
}: {
  icon: React.ReactNode;
  label: string;
  onClick?: () => void;
  active?: boolean;
  title?: string;
}) {
  const Tag = onClick ? "button" : "div";
  return (
    <Tag
      type={onClick ? "button" : undefined}
      title={title || (onClick ? label : undefined)}
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 transition-colors ${
        active
          ? "border-primary/50 bg-primary/10 text-foreground"
          : "bg-card text-muted-foreground"
      } ${
        onClick
          ? "hover:text-foreground hover:bg-muted cursor-pointer"
          : ""
      }`}
    >
      {icon}
      {label}
    </Tag>
  );
}

function IconBtn({
  label,
  onClick,
  icon,
}: {
  label: string;
  onClick: () => void;
  icon: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-1 rounded-md border px-2.5 py-1.5 text-xs hover:bg-muted"
    >
      {icon}
      {label}
    </button>
  );
}

function EmptyTailored({ onLibrary }: { onLibrary: () => void }) {
  return (
    <div className="rounded-xl border border-dashed p-8 text-center space-y-3">
      <Wand2 className="mx-auto h-8 w-8 text-primary opacity-80" />
      <p className="font-medium">Start with Tailor — then versions land here</p>
      <p className="text-sm text-muted-foreground max-w-md mx-auto">
        Pick a library template, paste a JD, review skill gaps, edit sections, save to
        Studio, and download PDF/DOCX/LaTeX. Canvas is optional for the full agent loop.
      </p>
      <div className="flex flex-wrap justify-center gap-2 pt-2">
        <Link
          href="/tailor"
          className="inline-flex items-center gap-2 rounded-md bg-primary text-primary-foreground px-3 py-2 text-sm"
        >
          <Wand2 className="h-4 w-4" /> Tailor a JD
        </Link>
        <button
          type="button"
          onClick={onLibrary}
          className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-muted"
        >
          <Library className="h-4 w-4" /> Browse library
        </button>
        <Link
          href="/canvas"
          className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-muted"
        >
          <Workflow className="h-4 w-4" /> Canvas
        </Link>
      </div>
    </div>
  );
}

function AtsBadge({
  score,
  compact,
}: {
  score: number | null;
  compact?: boolean;
}) {
  const size = compact ? "w-10 h-10" : "w-14 h-14";
  const svg = compact ? "w-10 h-10" : "w-14 h-14";
  const r = compact ? 16 : 24;
  const c = compact ? 20 : 28;
  const circ = 2 * Math.PI * r;

  if (score == null) {
    return (
      <div
        className={`${size} rounded-lg border border-dashed flex items-center justify-center shrink-0 text-[9px] text-muted-foreground font-medium text-center leading-tight`}
      >
        No
        <br />
        ATS
      </div>
    );
  }
  return (
    <div className={`relative ${size} flex items-center justify-center shrink-0`}>
      <svg className={`${svg} -rotate-90`}>
        <circle
          cx={c}
          cy={c}
          r={r}
          stroke="currentColor"
          strokeWidth="3"
          fill="transparent"
          className="text-muted"
        />
        <circle
          cx={c}
          cy={c}
          r={r}
          stroke="currentColor"
          strokeWidth="3"
          fill="transparent"
          strokeDasharray={circ}
          strokeDashoffset={
            circ - (circ * Math.min(100, Math.max(0, score))) / 100
          }
          className="text-primary"
        />
      </svg>
      <span className={`absolute font-bold ${compact ? "text-xs" : "text-sm"}`}>
        {score}
      </span>
    </div>
  );
}

function SkillRow({
  label,
  skills,
  tone,
}: {
  label: string;
  skills: string[];
  tone: "good" | "warn" | "neutral";
}) {
  const toneClass =
    tone === "good"
      ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
      : tone === "warn"
        ? "bg-amber-500/10 text-amber-800 dark:text-amber-300"
        : "bg-muted text-muted-foreground";
  return (
    <div>
      <p className="text-xs font-medium mb-1.5">{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {skills.map((s) => (
          <span key={s} className={`px-2 py-0.5 rounded text-xs ${toneClass}`}>
            {s}
          </span>
        ))}
      </div>
    </div>
  );
}
