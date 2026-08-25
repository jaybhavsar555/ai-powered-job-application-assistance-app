"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Search,
  MapPin,
  Briefcase,
  DollarSign,
  Globe,
  CheckCircle,
  Bot,
  Sparkles,
  Wand2,
  Code2,
  ArrowRight,
  UploadCloud,
  AlertCircle,
  X,
  Info,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";

interface PreferenceState {
  targetRoles: string;
  minSalary: string;
  locationHubs: string[];
  isRemote: boolean;
  companyTypes: string[];
  experienceLevel: string;
  techStack: string;
  workAuthorization: string;
}

interface DiscoveredJob {
  id: string;
  company: string;
  title: string;
  location?: string;
  salary?: string;
  description?: string;
  full_jd?: string;
  company_info?: string;
  contact_info?: string;
  matchScore?: number;
  matchReason?: string;
  url?: string | null;
  source?: string | null;
  posted_at?: string | null;
  applyable?: boolean;
  wishlisted?: boolean;
  ingestedJobId?: string;
}

type PageMessage = {
  tone: "error" | "success" | "info";
  title: string;
  detail: string;
};

type MessageContext = "discover" | "autofill" | "upload" | "wishlist";

function explainIssue(raw: string, context: MessageContext): PageMessage {
  const msg = (raw || "").trim() || "Something went wrong";

  if (/abort|timeout|Failed to fetch|network/i.test(msg)) {
    return {
      tone: "error",
      title:
        context === "discover"
          ? "Discovery timed out"
          : "Request timed out",
      detail:
        "Boards + AI scoring can take 1–2 minutes. Wait a moment and retry. If it keeps failing, confirm the API is up on :8001 and check Canvas → LLM (Token Harbor may be busy).",
    };
  }

  if (/401|credentials|unauthorized|validate/i.test(msg)) {
    return {
      tone: "error",
      title: "Session expired",
      detail:
        "Your login token is no longer valid (common after API restart). Sign in again, then retry.",
    };
  }

  if (/502|503|Token Harbor|LLM unavailable|peak demand|upstream/i.test(msg)) {
    return {
      tone: "error",
      title: "AI provider unavailable",
      detail:
        msg.length <= 320
          ? msg
          : "Token Harbor / LLM returned an error. Retry in a minute, or switch model in Canvas / backend/.env (e.g. deepseek-v4-flash:free).",
    };
  }

  if (/no live jobs|returned no|no matching/i.test(msg)) {
    return {
      tone: "info",
      title: "No matching jobs found",
      detail:
        "Vault portals and remote boards returned nothing for these preferences. Broaden the role, keep Remote on, seed portals on Vault, then run Discovery again.",
    };
  }

  const titles: Record<MessageContext, string> = {
    discover: "Discovery failed",
    autofill: "Auto-Fill failed",
    upload: "Resume upload failed",
    wishlist: "Could not add to Wishlist",
  };

  return {
    tone: "error",
    title: titles[context],
    detail: msg,
  };
}

const LOCATION_HUBS = [
  { id: "india", label: "India Tech Hubs", desc: "BLR, BOM, PUN, HYD, DEL" },
  { id: "usa", label: "USA & Canada", desc: "SF, NY, Austin, Toronto" },
  { id: "europe", label: "Europe", desc: "Germany, UK, Denmark" },
];

const COMPANY_TYPES = ["Startups", "Mid-size", "MNCs / Enterprise"];

export default function DiscoveryPage() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const [preferences, setPreferences] = useState<PreferenceState>({
    targetRoles: "",
    minSalary: "900000",
    locationHubs: ["india", "remote"],
    isRemote: true,
    companyTypes: ["Startups", "Mid-size"],
    experienceLevel: "Mid-Level (2-4y)",
    techStack: "",
    workAuthorization: "",
  });

  const [dynamicSalary, setDynamicSalary] = useState(true);

  const [loading, setLoading] = useState(false);
  const [autoFilling, setAutoFilling] = useState(false);
  const [recommendedJobs, setRecommendedJobs] = useState<DiscoveredJob[]>([]);
  const [activeTab, setActiveTab] = useState<"setup" | "results">("setup");
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [expandedJDs, setExpandedJDs] = useState<Record<string, boolean>>({});
  const [ingestingId, setIngestingId] = useState<string | null>(null);
  const [wishlistNotice, setWishlistNotice] = useState<string | null>(null);
  const [libraryResumes, setLibraryResumes] = useState<string[]>([]);
  const [selectedResume, setSelectedResume] = useState<string>("");
  const [autofillNote, setAutofillNote] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [pageMessage, setPageMessage] = useState<PageMessage | null>(null);
  const resumeInputRef = useRef<HTMLInputElement>(null);

  const loadLibrary = async () => {
    if (!token) return;
    try {
      const res = await fetch("/api/v1/documents/resume-library", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;
      const data = await res.json();
      const names = (Array.isArray(data) ? data : data.files || [])
        .map((f: { name?: string }) => f.name)
        .filter(Boolean) as string[];
      setLibraryResumes(names);
      setSelectedResume((prev) => prev || names[0] || "");
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    loadLibrary();
    if (!token) return;
    (async () => {
      try {
        const res = await fetch("/api/v1/apply-prefs", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) return;
        const data = await res.json();
        const auth = String(data.work_authorization || "").trim();
        if (auth) {
          setPreferences((p) =>
            p.workAuthorization ? p : { ...p, workAuthorization: auth }
          );
        }
      } catch {
        /* ignore */
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const handleUploadResume = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !token) return;
    setUploading(true);
    setAutofillNote(null);
    setPageMessage(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch("/api/v1/documents/upload", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(
          typeof body.detail === "string" ? body.detail : "Upload failed"
        );
      }
      const data = await res.json();
      const name = data.filename || file.name;
      await loadLibrary();
      setSelectedResume(name);
      setAutofillNote(`Uploaded ${name} — ready for Auto-Fill.`);
      setPageMessage({
        tone: "success",
        title: "Resume uploaded",
        detail: `${name} is in your library and selected for Auto-Fill.`,
      });
    } catch (err) {
      setPageMessage(
        explainIssue(
          err instanceof Error ? err.message : "Upload failed",
          "upload"
        )
      );
    } finally {
      setUploading(false);
      if (resumeInputRef.current) resumeInputRef.current.value = "";
    }
  };

  const toggleLocationHub = (id: string) => {
    setPreferences(prev => ({
      ...prev,
      locationHubs: prev.locationHubs.includes(id) 
        ? prev.locationHubs.filter(h => h !== id)
        : [...prev.locationHubs, id]
    }));
  };

  const toggleCompanyType = (type: string) => {
    setPreferences(prev => ({
      ...prev,
      companyTypes: prev.companyTypes.includes(type)
        ? prev.companyTypes.filter(t => t !== type)
        : [...prev.companyTypes, type]
    }));
  };

  const handleAutoFill = async () => {
    setAutoFilling(true);
    setAutofillNote(null);
    setPageMessage(null);
    try {
      const res = await fetch("/api/v1/workflows/analyze-resumes", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          resume_name: selectedResume || null,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(
          typeof body.detail === "string"
            ? body.detail
            : "Failed to analyze resumes"
        );
      }
      const data = await res.json();
      const {
        used_resumes,
        available_resumes,
        note,
        source,
        ...prefs
      } = data;
      setPreferences((prev) => ({
        ...prev,
        ...prefs,
      }));
      if (Array.isArray(available_resumes) && available_resumes.length) {
        setLibraryResumes(available_resumes);
      }
      const filledNote =
        note ||
        (used_resumes?.length
          ? `Filled from: ${used_resumes.join(", ")}`
          : source === "fallback_no_library"
            ? "No library resume found — defaults applied. Upload one first."
            : "Preferences updated");
      setAutofillNote(filledNote);
      setPageMessage({
        tone: source === "fallback_no_library" ? "info" : "success",
        title:
          source === "fallback_no_library"
            ? "Using defaults"
            : "Preferences filled from resume",
        detail: filledNote,
      });
    } catch (err) {
      console.error(err);
      setPageMessage(
        explainIssue(
          err instanceof Error
            ? err.message
            : "Failed to analyze resumes. Ensure the backend is running on :8001.",
          "autofill"
        )
      );
    } finally {
      setAutoFilling(false);
    }
  };

  const handleRunDiscovery = async () => {
    setLoading(true);
    setWishlistNotice(null);
    setPageMessage(null);
    try {
      const res = await fetch("/api/v1/workflows/discover", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(preferences),
        signal: AbortSignal.timeout(300_000),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        const detail =
          typeof body.detail === "string"
            ? body.detail
            : Array.isArray(body.detail)
              ? body.detail
                  .map((d: { msg?: string }) => d.msg)
                  .filter(Boolean)
                  .join("; ")
              : `Discovery failed (HTTP ${res.status})`;
        throw new Error(detail);
      }
      const data = await res.json();
      const jobs = (data.jobs || []) as DiscoveredJob[];
      if (jobs.length === 0) {
        throw new Error(
          "Discovery returned no live jobs — try broader roles or check Remotive/RemoteOK."
        );
      }
      setRecommendedJobs(jobs);
      if (jobs.length > 0) setSelectedJobId(jobs[0].id);
      setActiveTab("results");
      setPageMessage({
        tone: "success",
        title: `Found ${jobs.length} matches`,
        detail:
          "Review scores below. Add strong fits to Wishlist, then open Jobs → Canvas / Review & Apply.",
      });
    } catch (err) {
      console.error(err);
      const msg = err instanceof Error ? err.message : String(err);
      setPageMessage(explainIssue(msg, "discover"));
    } finally {
      setLoading(false);
    }
  };

  const handleAddToWishlist = async (jobId: string) => {
    const job = recommendedJobs.find((j) => j.id === jobId);
    if (!job) return;

    setIngestingId(jobId);
    setWishlistNotice(null);
    setPageMessage(null);
    try {
      const description = [
        job.description || job.matchReason || "",
        job.location ? `Location: ${job.location}` : "",
        job.salary ? `Salary: ${job.salary}` : "",
        job.url ? `Source: ${job.url}` : "",
      ]
        .filter(Boolean)
        .join("\n");

      const res = await fetch("/api/v1/jobs/ingest", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          url:
            job.url && /^https?:\/\//i.test(job.url.trim())
              ? job.url.trim()
              : null,
          role_title: job.title,
          company_name: job.company,
          description_raw: description || `${job.title} at ${job.company}`,
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(
          typeof body.detail === "string"
            ? body.detail
            : "Failed to add job to Wishlist"
        );
      }

      const data = await res.json();
      setWishlistNotice(
        `Added ${job.company} — ${job.title}. Next: open Jobs → Canvas → Package → Outreach.`
      );
      setPageMessage({
        tone: "success",
        title: "Added to Wishlist",
        detail: `${job.company} — ${job.title}. Next: Jobs → Canvas → Package → Outreach.`,
      });
      setRecommendedJobs((prev) =>
        prev.map((j) =>
          j.id === jobId ? { ...j, wishlisted: true, ingestedJobId: data.id } : j
        )
      );
    } catch (err) {
      console.error(err);
      setPageMessage(
        explainIssue(
          err instanceof Error ? err.message : "Error adding to Wishlist.",
          "wishlist"
        )
      );
    } finally {
      setIngestingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-background/50 pb-20">
      {/* Premium Header */}
      <div className="relative overflow-hidden bg-card border-b">
        <div className="absolute inset-0 bg-gradient-to-r from-primary/10 via-background to-primary/5 opacity-50"></div>
        <div className="absolute -top-24 -right-24 w-96 h-96 bg-primary/20 rounded-full blur-3xl opacity-30"></div>
        
        <div className="relative p-4 md:p-8 max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="space-y-2 text-center md:text-left">
            <h1 className="text-4xl font-extrabold tracking-tight flex items-center justify-center md:justify-start gap-3">
              <Sparkles className="h-8 w-8 text-primary" />
              Proactive Job Discovery
            </h1>
            <p className="text-muted-foreground text-lg max-w-xl">
              Searches Vault ATS career pages first (Greenhouse, Lever, Ashby,
              Workday), then other portal KBs — then fills with Remotive /
              RemoteOK / Arbeitnow. Score, Wishlist, then Canvas / Review &amp; Apply.
            </p>
          </div>
          
          <div className="flex bg-muted/50 p-1.5 rounded-lg border">
            <button 
              onClick={() => setActiveTab('setup')}
              className={`px-6 py-2.5 rounded-md text-sm font-medium transition-all ${
                activeTab === 'setup' 
                  ? 'bg-background shadow-sm text-foreground' 
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              1. Setup Preferences
            </button>
            <button 
              onClick={() => setActiveTab('results')}
              className={`px-6 py-2.5 rounded-md text-sm font-medium transition-all ${
                activeTab === 'results' 
                  ? 'bg-background shadow-sm text-foreground' 
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              2. Review Matches
              {recommendedJobs.length > 0 && (
                <span className="ml-2 px-2 py-0.5 rounded-full bg-primary/20 text-primary text-xs">
                  {recommendedJobs.length}
                </span>
              )}
            </button>
          </div>
        </div>
      </div>

      <div className="p-4 md:p-8 max-w-7xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-700">
        {pageMessage && (
          <div
            role="status"
            className={`mb-6 rounded-xl border px-4 py-3 text-sm flex items-start gap-3 ${
              pageMessage.tone === "error"
                ? "border-destructive/30 bg-destructive/10"
                : pageMessage.tone === "success"
                  ? "border-emerald-500/30 bg-emerald-500/10"
                  : "border-amber-500/30 bg-amber-500/10"
            }`}
          >
            {pageMessage.tone === "error" ? (
              <AlertCircle className="h-5 w-5 mt-0.5 shrink-0 text-destructive" />
            ) : pageMessage.tone === "success" ? (
              <CheckCircle className="h-5 w-5 mt-0.5 shrink-0 text-emerald-500" />
            ) : (
              <Info className="h-5 w-5 mt-0.5 shrink-0 text-amber-500" />
            )}
            <div className="min-w-0 flex-1 space-y-1">
              <p
                className={`font-semibold ${
                  pageMessage.tone === "error"
                    ? "text-destructive"
                    : pageMessage.tone === "success"
                      ? "text-emerald-700 dark:text-emerald-400"
                      : "text-amber-700 dark:text-amber-400"
                }`}
              >
                {pageMessage.title}
              </p>
              <p className="text-muted-foreground leading-relaxed">
                {pageMessage.detail}
              </p>
            </div>
            <button
              type="button"
              aria-label="Dismiss message"
              onClick={() => setPageMessage(null)}
              className="text-muted-foreground hover:text-foreground shrink-0 p-1"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* SETUP TAB */}
        {activeTab === 'setup' && (
          <div className="space-y-8">
            <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 rounded-2xl border bg-card p-4 md:p-5">
              <div className="space-y-2 min-w-0 flex-1">
                <label className="text-sm font-medium">Resume for Auto-Fill</label>
                <p className="text-xs text-muted-foreground">
                  Uses your resume library folder (same as Resume Studio). Pick one
                  file, or upload a PDF/DOCX here.
                </p>
                <div className="flex flex-col sm:flex-row gap-2">
                  <select
                    value={selectedResume}
                    onChange={(e) => setSelectedResume(e.target.value)}
                    className="w-full sm:max-w-md h-11 px-3 rounded-xl border border-input bg-background text-sm"
                  >
                    {libraryResumes.length === 0 ? (
                      <option value="">No resumes in library — upload below</option>
                    ) : (
                      libraryResumes.map((name) => (
                        <option key={name} value={name}>
                          {name}
                        </option>
                      ))
                    )}
                  </select>
                  <input
                    ref={resumeInputRef}
                    type="file"
                    accept=".pdf,.docx,.doc,.txt,.md"
                    className="hidden"
                    onChange={handleUploadResume}
                  />
                  <button
                    type="button"
                    disabled={uploading}
                    onClick={() => resumeInputRef.current?.click()}
                    className="inline-flex items-center justify-center gap-2 h-11 px-4 rounded-xl border text-sm font-medium hover:bg-muted disabled:opacity-50"
                  >
                    {uploading ? (
                      <div className="h-4 w-4 border-2 border-muted-foreground/30 border-t-muted-foreground rounded-full animate-spin" />
                    ) : (
                      <UploadCloud className="h-4 w-4" />
                    )}
                    Upload
                  </button>
                </div>
                {autofillNote && (
                  <p className="text-xs text-primary">{autofillNote}</p>
                )}
              </div>
              <button
                onClick={handleAutoFill}
                disabled={autoFilling}
                className="inline-flex items-center justify-center rounded-full text-sm font-bold transition-all bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg hover:shadow-xl hover:scale-[1.02] h-12 px-6 gap-2 shrink-0"
              >
                {autoFilling ? (
                  <div className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <Wand2 className="h-4 w-4" />
                )}
                {autoFilling
                  ? "Analyzing resume…"
                  : selectedResume
                    ? "Auto-Fill from Resume"
                    : "Auto-Fill (defaults)"}
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-stretch">
              
              {/* Column 1: Role & Experience */}
              <div className="bg-card border rounded-2xl p-6 md:p-8 shadow-sm relative overflow-hidden group hover:shadow-md transition-shadow">
                <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-bl-full -z-10 transition-transform group-hover:scale-110 duration-500"></div>
                
                <div className="flex items-center gap-3 mb-6">
                  <div className="p-3 rounded-xl bg-blue-500/10 text-blue-500">
                    <Briefcase className="h-6 w-6" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold">Target Role</h3>
                    <p className="text-sm text-muted-foreground">Your target position</p>
                  </div>
                </div>
                
                <div className="space-y-5">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Target Roles (Comma separated)</label>
                    <input
                      type="text"
                      value={preferences.targetRoles}
                      onChange={(e) => setPreferences({ ...preferences, targetRoles: e.target.value })}
                      className="w-full h-12 px-4 rounded-xl border border-input bg-background/50 focus:bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                      placeholder="e.g. Software Engineer, Tech Lead"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Experience Level</label>
                    <select
                      value={preferences.experienceLevel}
                      onChange={(e) => setPreferences({ ...preferences, experienceLevel: e.target.value })}
                      className="w-full h-12 px-4 rounded-xl border border-input bg-background/50 focus:bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all appearance-none"
                    >
                      <option value="Entry-Level (0-2y)">Entry-Level (0-2y)</option>
                      <option value="Mid-Level (2-4y)">Mid-Level (2-4y)</option>
                      <option value="Senior (5-8y)">Senior (5-8y)</option>
                      <option value="Lead/Staff (8y+)">Lead/Staff (8y+)</option>
                    </select>
                  </div>
                  
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Minimum Base Salary (INR)</label>
                    <div className="relative">
                      <span className="absolute left-4 top-1/2 -translate-y-1/2 font-medium text-muted-foreground">₹</span>
                      <input
                        type="number"
                        value={preferences.minSalary}
                        onChange={(e) => setPreferences({ ...preferences, minSalary: e.target.value })}
                        className="w-full h-12 pl-10 pr-4 rounded-xl border border-input bg-background/50 focus:bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                      />
                    </div>
                  </div>
                  
                  <div className="flex items-start gap-4 p-4 rounded-xl bg-blue-500/5 border border-blue-500/20 hover:bg-blue-500/10 transition-colors">
                    <label className="relative inline-flex items-center cursor-pointer mt-0.5">
                      <input 
                        type="checkbox" 
                        className="sr-only"
                        checked={dynamicSalary}
                        onChange={(e) => setDynamicSalary(e.target.checked)}
                      />
                      <div className={`w-11 h-6 rounded-full transition-colors flex items-center px-0.5 ${dynamicSalary ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-700'}`}>
                        <div className={`w-5 h-5 rounded-full bg-white shadow-sm transform transition-transform duration-300 ${dynamicSalary ? 'translate-x-5' : 'translate-x-0'}`} />
                      </div>
                    </label>
                    <div>
                      <p className="text-sm font-bold text-blue-900 dark:text-blue-400">Dynamic AI Negotiation</p>
                      <p className="text-xs text-blue-800/70 dark:text-blue-300/70 mt-1 leading-relaxed">
                        AI will automatically convert and adjust your 9-12 LPA baseline to local market rates (e.g., USD for US, EUR for Europe, AUD for Australia) based on the target country and company budget.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Column 2: Tech & Company */}
              <div className="bg-card border rounded-2xl p-6 md:p-8 shadow-sm relative overflow-hidden group hover:shadow-md transition-shadow">
                <div className="absolute top-0 right-0 w-32 h-32 bg-orange-500/10 rounded-bl-full -z-10 transition-transform group-hover:scale-110 duration-500"></div>
                
                <div className="flex items-center gap-3 mb-6">
                  <div className="p-3 rounded-xl bg-orange-500/10 text-orange-500">
                    <Code2 className="h-6 w-6" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold">Tech & Company</h3>
                    <p className="text-sm text-muted-foreground">Match your tech stack</p>
                  </div>
                </div>
                
                <div className="space-y-5">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Core Tech Stack (Keywords)</label>
                    <textarea
                      value={preferences.techStack}
                      onChange={(e) => setPreferences({ ...preferences, techStack: e.target.value })}
                      className="w-full h-24 p-4 rounded-xl border border-input bg-background/50 focus:bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all resize-none"
                      placeholder="e.g. Python, React, Next.js, AWS"
                    />
                  </div>
                  
                  <div className="space-y-3">
                    <label className="text-sm font-medium">Target Company Types</label>
                    <div className="flex flex-wrap gap-2">
                      {COMPANY_TYPES.map(type => (
                        <button
                          key={type}
                          onClick={() => toggleCompanyType(type)}
                          className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
                            preferences.companyTypes.includes(type)
                              ? 'bg-orange-500/10 border-orange-500 text-orange-600 dark:text-orange-400'
                              : 'bg-transparent text-muted-foreground hover:bg-muted'
                          }`}
                        >
                          {type}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Column 3: Location Hubs */}
              <div className="bg-card border rounded-2xl p-6 md:p-8 shadow-sm relative overflow-hidden group hover:shadow-md transition-shadow">
                <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/10 rounded-bl-full -z-10 transition-transform group-hover:scale-110 duration-500"></div>
                
                <div className="flex items-center gap-3 mb-6">
                  <div className="p-3 rounded-xl bg-purple-500/10 text-purple-500">
                    <Globe className="h-6 w-6" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold">Location & Hubs</h3>
                    <p className="text-sm text-muted-foreground">Where do you want to work?</p>
                  </div>
                </div>
                
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 rounded-xl border bg-background/50 hover:bg-muted/30 transition-colors">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-primary/10 rounded-md"><MapPin className="h-4 w-4 text-primary" /></div>
                      <div>
                        <p className="font-medium text-sm">Remote Only</p>
                        <p className="text-xs text-muted-foreground">Only show 100% remote roles</p>
                      </div>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input 
                        type="checkbox" 
                        className="sr-only"
                        checked={preferences.isRemote}
                        onChange={(e) => setPreferences({ ...preferences, isRemote: e.target.checked })}
                      />
                      <div className={`w-11 h-6 rounded-full transition-colors flex items-center px-0.5 ${preferences.isRemote ? 'bg-primary' : 'bg-gray-300 dark:bg-gray-700'}`}>
                        <div className={`w-5 h-5 rounded-full bg-white shadow-sm transform transition-transform duration-300 ${preferences.isRemote ? 'translate-x-5' : 'translate-x-0'}`} />
                      </div>
                    </label>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium">Work authorization</label>
                    <p className="text-xs text-muted-foreground">
                      Same pref as Inbox. Skips roles that say they do not sponsor
                      (OPT / visa). Saved to apply prefs.
                    </p>
                    <select
                      value={preferences.workAuthorization}
                      onChange={(e) => {
                        const value = e.target.value;
                        setPreferences({
                          ...preferences,
                          workAuthorization: value,
                        });
                        if (!token) return;
                        void fetch("/api/v1/apply-prefs", {
                          method: "PUT",
                          headers: {
                            Authorization: `Bearer ${token}`,
                            "Content-Type": "application/json",
                          },
                          body: JSON.stringify({ work_authorization: value }),
                        });
                      }}
                      className="w-full h-11 px-3 rounded-xl border border-input bg-background text-sm"
                    >
                      <option value="">Not specified</option>
                      <option value="citizen">Citizen / no sponsorship needed</option>
                      <option value="opt">OPT / STEM-OPT</option>
                      <option value="needs_sponsorship">Need visa sponsorship</option>
                      <option value="other">Other / prefer not to say</option>
                    </select>
                  </div>
                  
                  <div className="pt-2 space-y-3">
                    <label className="text-sm font-medium">Preferred Regions / Tech Hubs</label>
                    <div className="grid gap-3">
                      {LOCATION_HUBS.map(hub => (
                        <div 
                          key={hub.id}
                          onClick={() => toggleLocationHub(hub.id)}
                          className={`cursor-pointer p-3 rounded-xl border flex items-center justify-between transition-all ${
                            preferences.locationHubs.includes(hub.id)
                              ? 'bg-purple-500/10 border-purple-500/50'
                              : 'bg-background/50 hover:bg-muted'
                          }`}
                        >
                          <div>
                            <p className={`text-sm font-bold ${preferences.locationHubs.includes(hub.id) ? 'text-purple-700 dark:text-purple-300' : 'text-foreground'}`}>
                              {hub.label}
                            </p>
                            <p className="text-xs text-muted-foreground">{hub.desc}</p>
                          </div>
                          <div className={`w-5 h-5 rounded-full border flex items-center justify-center ${
                            preferences.locationHubs.includes(hub.id) ? 'bg-purple-500 border-purple-500' : 'border-input'
                          }`}>
                            {preferences.locationHubs.includes(hub.id) && <CheckCircle className="h-3 w-3 text-white" />}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

            </div>

            <div className="pt-4">
              <button
                onClick={handleRunDiscovery}
                disabled={loading}
                className="w-full h-16 relative overflow-hidden group rounded-2xl text-lg font-bold transition-all bg-primary text-primary-foreground shadow-xl hover:shadow-primary/25 hover:-translate-y-1 disabled:opacity-50 disabled:hover:translate-y-0"
              >
                <div className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:animate-[shimmer_1.5s_infinite]"></div>
                <div className="flex items-center justify-center gap-3 relative z-10">
                  {loading ? (
                    <div className="h-6 w-6 border-4 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <Bot className="h-6 w-6" />
                  )}
                  {loading ? "AI is discovering jobs..." : "Start Auto-Discovery Engine"}
                  {!loading && <ArrowRight className="h-5 w-5 ml-2 transition-transform group-hover:translate-x-1" />}
                </div>
              </button>
            </div>
            
          </div>
        )}

        {/* RESULTS TAB */}
        {activeTab === 'results' && (
          <div>
            {recommendedJobs.length === 0 ? (
              <div className="rounded-2xl border border-dashed bg-card/30 p-16 text-center max-w-2xl mx-auto flex flex-col items-center justify-center">
                <div className="w-24 h-24 rounded-full bg-muted/50 flex items-center justify-center mb-6">
                  <Search className="h-10 w-10 text-muted-foreground opacity-50" />
                </div>
                <h3 className="text-2xl font-bold mb-3">No Discoveries Yet</h3>
                <p className="text-muted-foreground text-lg">
                  Go back to the Setup tab and run the discovery engine to find personalized job matches.
                </p>
                <button 
                  onClick={() => setActiveTab('setup')}
                  className="mt-8 px-6 py-3 rounded-full bg-primary/10 text-primary font-medium hover:bg-primary/20 transition-colors"
                >
                  Configure Preferences
                </button>
              </div>
            ) : (
              <div className="flex flex-col lg:flex-row gap-6 h-[calc(100vh-250px)]">
                {/* Master List */}
                <div className="w-full lg:w-1/3 flex flex-col gap-4 overflow-y-auto pr-2 pb-20">
                  {wishlistNotice && (
                    <div className="rounded-xl border border-green-500/30 bg-green-500/10 px-4 py-3 text-sm flex flex-col gap-3">
                      <span>{wishlistNotice}</span>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => router.push("/jobs")}
                          className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground text-center flex-1"
                        >
                          Open Jobs
                        </button>
                        <button
                          type="button"
                          onClick={() => router.push("/tracker")}
                          className="rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-muted text-center flex-1"
                        >
                          Tracker
                        </button>
                      </div>
                    </div>
                  )}

                  {recommendedJobs.map(job => (
                    <div 
                      key={job.id} 
                      onClick={() => setSelectedJobId(job.id)}
                      className={`p-4 rounded-xl border cursor-pointer transition-all ${
                        selectedJobId === job.id 
                          ? 'border-primary bg-primary/5 shadow-md scale-[1.02]' 
                          : 'hover:border-primary/50 bg-card hover:bg-muted/50'
                      }`}
                    >
                      <div className="flex justify-between items-start mb-2 gap-2">
                        <h4 className="font-bold text-base leading-tight">{job.title}</h4>
                        <span className="text-xs font-bold text-green-600 bg-green-500/10 px-2 py-1 rounded-md shrink-0">
                          {job.matchScore}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground">{job.company}</p>
                      <div className="flex gap-2 mt-3 flex-wrap">
                        <span className="text-[11px] bg-muted px-2 py-1 rounded-md font-medium text-muted-foreground">
                          {job.location}
                        </span>
                        {job.wishlisted && (
                          <span className="text-[11px] bg-primary/10 text-primary px-2 py-1 rounded-md font-bold uppercase tracking-wider">
                            Wishlisted
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Detail Pane */}
                <div className="w-full lg:w-2/3 bg-card border rounded-2xl p-6 lg:p-8 overflow-y-auto pb-20 relative shadow-sm">
                  {(() => {
                    const job = recommendedJobs.find(j => j.id === selectedJobId) || recommendedJobs[0];
                    if (!job) return null;
                    return (
                      <div className="space-y-6">
                        <div className="flex justify-between items-start flex-wrap gap-4">
                          <div>
                            <div className="flex items-center gap-3 mb-2 flex-wrap">
                              <h3 className="text-3xl font-black">{job.title}</h3>
                              {job.wishlisted && (
                                <span className="px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-bold uppercase tracking-wider">
                                  On Wishlist
                                </span>
                              )}
                              {job.source && (
                                <span className="px-2 py-1 rounded-full border text-[10px] font-semibold uppercase text-muted-foreground">
                                  {job.source}
                                </span>
                              )}
                            </div>
                            <p className="text-xl text-muted-foreground font-medium">{job.company}</p>
                          </div>
                          
                          <div className="flex flex-col items-center justify-center w-24 h-24 rounded-3xl bg-gradient-to-br from-green-500/20 to-green-500/5 border border-green-500/20 shadow-inner">
                            <span className="text-4xl font-black text-green-600">{job.matchScore}</span>
                            <span className="text-[11px] font-bold uppercase text-green-700/70 tracking-widest mt-1">Match</span>
                          </div>
                        </div>
                        
                        <div className="flex flex-wrap gap-4 text-sm font-medium">
                          <span className="flex items-center gap-2 bg-muted px-4 py-2.5 rounded-xl border border-border/50 shadow-sm">
                            <MapPin className="h-4 w-4 text-primary" /> {job.location}
                          </span>
                          <span className="flex items-center gap-2 bg-muted px-4 py-2.5 rounded-xl border border-border/50 shadow-sm">
                            <DollarSign className="h-4 w-4 text-green-600" /> {job.salary}
                          </span>
                        </div>

                        <div className="flex flex-wrap gap-3 mt-2">
                          {job.wishlisted && job.ingestedJobId ? (
                            <>
                              <Link
                                href={`/apply?job_id=${encodeURIComponent(job.ingestedJobId)}`}
                                className="inline-flex items-center justify-center rounded-xl text-sm font-bold bg-primary text-primary-foreground h-12 px-6 shadow-md hover:shadow-lg transition-all"
                              >
                                Review &amp; Apply
                              </Link>
                              <Link
                                href={`/canvas?job_id=${encodeURIComponent(job.ingestedJobId)}`}
                                className="inline-flex items-center justify-center rounded-xl text-sm font-bold border h-12 px-6 hover:bg-muted transition-colors"
                              >
                                Open Canvas
                              </Link>
                            </>
                          ) : (
                            <button
                              type="button"
                              disabled={ingestingId === job.id}
                              onClick={() => handleAddToWishlist(job.id)}
                              className="inline-flex items-center justify-center rounded-xl text-sm font-bold transition-all bg-primary text-primary-foreground hover:opacity-90 h-12 px-8 gap-2 shadow-lg disabled:opacity-60"
                            >
                              <CheckCircle className="h-4 w-4" />
                              {ingestingId === job.id ? "Adding…" : "Add to Wishlist"}
                            </button>
                          )}
                          {job.url && (
                            <a
                              href={job.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center justify-center rounded-xl text-sm font-medium transition-colors text-blue-600 hover:text-blue-700 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-950/30 h-12 px-6 gap-2 border border-blue-200 dark:border-blue-900"
                            >
                              <Globe className="h-4 w-4" />
                              View Original
                            </a>
                          )}
                        </div>
                        
                        <div className="bg-gradient-to-r from-blue-500/10 to-transparent p-6 rounded-2xl border-l-4 border-blue-500 mt-6">
                          <div className="flex items-start gap-4">
                            <Bot className="h-8 w-8 text-blue-600 shrink-0 mt-1" />
                            <div>
                              <h4 className="text-base font-bold text-blue-900 dark:text-blue-400 mb-2">AI Match Analysis</h4>
                              <p className="text-blue-900/80 dark:text-blue-300/80 leading-relaxed text-[15px]">{job.matchReason}</p>
                            </div>
                          </div>
                        </div>

                        {job.company_info && (
                          <div className="p-6 rounded-2xl border bg-muted/30 mt-6">
                            <h4 className="text-base font-bold mb-3 flex items-center gap-2">
                              <Briefcase className="h-5 w-5 text-muted-foreground" /> Firm Overview
                            </h4>
                            <p className="text-[15px] leading-relaxed text-muted-foreground">{job.company_info}</p>
                          </div>
                        )}
                        
                        {job.contact_info && (
                          <div className="p-6 rounded-2xl border bg-orange-500/5 border-orange-500/20 mt-6">
                            <h4 className="text-base font-bold text-orange-700 dark:text-orange-400 mb-3 flex items-center gap-2">
                              Contact Info Found
                            </h4>
                            <p className="text-[15px] leading-relaxed text-orange-800/80 dark:text-orange-300/80">{job.contact_info}</p>
                          </div>
                        )}
                        
                        {job.full_jd && (
                          <div className="mt-8 border-t pt-8">
                            <h4 className="text-lg font-bold mb-4 flex items-center gap-2">
                              Full Job Description
                            </h4>
                            <div className="text-[15px] leading-relaxed text-muted-foreground whitespace-pre-wrap font-serif">
                              {job.full_jd}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })()}
                </div>
              </div>
            )}
          </div>
        )}
        
      </div>
    </div>
  );
}
