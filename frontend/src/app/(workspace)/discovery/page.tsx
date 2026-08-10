"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { 
  Search, MapPin, Briefcase, DollarSign, Globe, Play, 
  CheckCircle, Bot, Sparkles, Wand2, Building, Code2, ArrowRight,
  UploadCloud
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
}

const LOCATION_HUBS = [
  { id: "india", label: "India Tech Hubs", desc: "BLR, BOM, PUN, HYD, DEL" },
  { id: "usa", label: "USA & Canada", desc: "SF, NY, Austin, Toronto" },
  { id: "europe", label: "Europe", desc: "Germany, UK, Denmark" },
];

const COMPANY_TYPES = ["Startups", "Mid-size", "MNCs / Enterprise"];
const EXP_LEVELS = ["Junior (0-2y)", "Mid-Level (3-5y)", "Senior (5-8y)", "Staff / Principal (8y+)"];

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
  });

  const [dynamicSalary, setDynamicSalary] = useState(true);

  const [loading, setLoading] = useState(false);
  const [autoFilling, setAutoFilling] = useState(false);
  const [recommendedJobs, setRecommendedJobs] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<'setup' | 'results'>('setup');
  const [ingestingId, setIngestingId] = useState<string | null>(null);
  const [wishlistNotice, setWishlistNotice] = useState<string | null>(null);
  const [libraryResumes, setLibraryResumes] = useState<string[]>([]);
  const [selectedResume, setSelectedResume] = useState<string>("");
  const [autofillNote, setAutofillNote] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const handleUploadResume = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !token) return;
    setUploading(true);
    setAutofillNote(null);
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
    } catch (err) {
      alert(err instanceof Error ? err.message : "Upload failed");
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
      setAutofillNote(
        note ||
          (used_resumes?.length
            ? `Filled from: ${used_resumes.join(", ")}`
            : source === "fallback_no_library"
              ? "No library resume found — defaults applied. Upload one first."
              : "Preferences updated")
      );
    } catch (err) {
      console.error(err);
      alert(
        err instanceof Error
          ? err.message
          : "Failed to analyze resumes. Please ensure backend is running."
      );
    } finally {
      setAutoFilling(false);
    }
  };

  const handleRunDiscovery = async () => {
    setLoading(true);
    setWishlistNotice(null);
    try {
      const res = await fetch("/api/v1/workflows/discover", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(preferences)
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        const detail =
          typeof body.detail === "string"
            ? body.detail
            : `Discovery failed (${res.status})`;
        throw new Error(detail);
      }
      const data = await res.json();
      const jobs = data.jobs || [];
      if (jobs.length === 0) {
        throw new Error("Discovery returned no jobs");
      }
      setRecommendedJobs(jobs);
      setActiveTab("results");
    } catch (err) {
      console.error(err);
      alert(
        err instanceof Error
          ? err.message
          : "Discovery failed — is the API running on :8001?"
      );
    } finally {
      setLoading(false);
    }
  };

  const handleAddToWishlist = async (jobId: string) => {
    const job = recommendedJobs.find((j) => j.id === jobId);
    if (!job) return;

    setIngestingId(jobId);
    setWishlistNotice(null);
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
      setRecommendedJobs((prev) =>
        prev.map((j) =>
          j.id === jobId ? { ...j, wishlisted: true, ingestedJobId: data.id } : j
        )
      );
    } catch (err) {
      console.error(err);
      alert(err instanceof Error ? err.message : "Error adding to Wishlist.");
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
              Set preferences, review AI matches, then one-click add roles to your Wishlist — tailor and apply with human approval.
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
              <div className="space-y-6">
                {wishlistNotice && (
                  <div className="rounded-xl border border-green-500/30 bg-green-500/10 px-4 py-3 text-sm flex flex-wrap items-center justify-between gap-3">
                    <span>{wishlistNotice}</span>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => router.push("/jobs")}
                        className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground"
                      >
                        Open Jobs
                      </button>
                      <button
                        type="button"
                        onClick={() => router.push("/tracker")}
                        className="rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-muted"
                      >
                        Tracker
                      </button>
                    </div>
                  </div>
                )}
                {recommendedJobs.map((job) => (
                  <div key={job.id} className="group rounded-2xl border bg-card p-1 shadow-sm hover:shadow-xl transition-all duration-300">
                    <div className="bg-card rounded-xl p-6 md:p-8 flex flex-col lg:flex-row gap-8 relative overflow-hidden">
                      <div className="absolute -right-12 -top-12 w-48 h-48 bg-green-500/5 rounded-full blur-2xl"></div>
                      
                      <div className="flex-1 space-y-6">
                        <div className="flex justify-between items-start">
                          <div>
                            <div className="flex items-center gap-3 mb-2 flex-wrap">
                              <h3 className="text-2xl font-black">{job.title}</h3>
                              <span className="px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-bold uppercase tracking-wider">
                                {job.wishlisted ? "On Wishlist" : "New Match"}
                              </span>
                              {job.source && (
                                <span className="px-2 py-1 rounded-full border text-[10px] font-semibold uppercase text-muted-foreground">
                                  {job.source}
                                </span>
                              )}
                            </div>
                            <p className="text-lg text-muted-foreground font-medium">{job.company}</p>
                          </div>
                          
                          <div className="flex flex-col items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-green-500/20 to-green-500/5 border border-green-500/20">
                            <span className="text-3xl font-black text-green-600">{job.matchScore}</span>
                            <span className="text-[10px] font-bold uppercase text-green-700/70">Score</span>
                          </div>
                        </div>
                        
                        <div className="flex flex-wrap gap-4 text-sm font-medium">
                          <span className="flex items-center gap-2 bg-muted px-4 py-2 rounded-lg">
                            <MapPin className="h-4 w-4 text-primary" /> {job.location}
                          </span>
                          <span className="flex items-center gap-2 bg-muted px-4 py-2 rounded-lg">
                            <DollarSign className="h-4 w-4 text-green-600" /> {job.salary}
                          </span>
                        </div>
                        
                        <div className="bg-gradient-to-r from-blue-500/10 to-transparent p-5 rounded-xl border-l-4 border-blue-500">
                          <div className="flex items-start gap-3">
                            <Bot className="h-6 w-6 text-blue-600 shrink-0 mt-0.5" />
                            <div>
                              <h4 className="text-sm font-bold text-blue-900 dark:text-blue-400 mb-1">AI Analysis</h4>
                              <p className="text-blue-800/80 dark:text-blue-300/80 leading-relaxed">{job.matchReason}</p>
                            </div>
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex lg:flex-col justify-end gap-3 lg:w-56 lg:border-l lg:pl-8">
                        {job.wishlisted && job.ingestedJobId ? (
                          <div className="flex flex-col gap-2 w-full">
                            <Link
                              href={`/apply?job_id=${encodeURIComponent(job.ingestedJobId)}`}
                              className="flex-1 w-full inline-flex items-center justify-center rounded-xl text-sm font-bold bg-primary text-primary-foreground h-12 px-6 gap-2"
                            >
                              Review &amp; Apply
                            </Link>
                            <Link
                              href={`/canvas?job_id=${encodeURIComponent(job.ingestedJobId)}`}
                              className="flex-1 w-full inline-flex items-center justify-center rounded-xl text-sm font-bold border h-12 px-6 gap-2 hover:bg-muted"
                            >
                              Open Canvas
                            </Link>
                            <Link
                              href="/jobs"
                              className="flex-1 w-full inline-flex items-center justify-center rounded-xl text-sm font-medium border h-10 px-6 gap-2 hover:bg-muted"
                            >
                              View on Jobs
                            </Link>
                          </div>
                        ) : (
                          <button
                            type="button"
                            disabled={ingestingId === job.id}
                            onClick={() => handleAddToWishlist(job.id)}
                            className="flex-1 w-full inline-flex items-center justify-center rounded-xl text-sm font-bold transition-all bg-primary text-primary-foreground hover:opacity-90 h-14 px-6 gap-2 shadow-lg disabled:opacity-60"
                          >
                            <CheckCircle className="h-5 w-5" />
                            {ingestingId === job.id ? "Adding…" : "Add to Wishlist"}
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() =>
                            setRecommendedJobs((prev) => prev.filter((j) => j.id !== job.id))
                          }
                          className="flex-1 w-full inline-flex items-center justify-center rounded-xl text-sm font-medium transition-colors border-2 hover:bg-muted text-muted-foreground hover:text-foreground h-14 px-6"
                        >
                          Dismiss
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
        
      </div>
    </div>
  );
}
