"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  Info,
  GitCommit,
  FileCode2,
  Clock,
  DollarSign,
  Zap,
  Save,
  Bot,
  Loader2,
  FileText,
  FileSearch,
  X,
  ExternalLink,
  PanelRight,
  Download,
} from "lucide-react";
import { usePanelStore } from "@/store/panelStore";
import { useAuthStore } from "@/store/auth";
import { useWorkflowStore } from "@/hooks/useWorkflowStore";
import api, { getApiErrorMessage } from "@/lib/api";
import { DocxFormattedPreview } from "@/components/preview/DocxFormattedPreview";

type AgentInfo = {
  name: string;
  label: string;
  description: string;
  capabilities: string[];
  system_prompt: string | null;
  configurable: boolean;
  role: string;
};

function findTelemetry(
  nodeTelemetry: Record<
    string,
    {
      latency_ms?: number;
      tokens?: number;
      cost?: number;
      evidence?: unknown;
      status: string;
    }
  >,
  agentName: string | null
) {
  if (!agentName) return null;
  const norm = (s: string) => s.toLowerCase().replace(/[\s_]+/g, "");
  const target = norm(agentName);
  const direct = nodeTelemetry[agentName];
  if (direct) return direct;
  const hit = Object.entries(nodeTelemetry).find(([k]) => {
    const n = norm(k);
    return n === target || n.includes(target) || target.includes(n);
  });
  return hit?.[1] ?? null;
}

export function InspectorPanel() {
  const { activeNode, selectedNode, nodeTelemetry, setSelectedNode } =
    useWorkflowStore();
  const {
    activeTab,
    pdfUrl,
    pdfTitle,
    preview,
    mobileOpen,
    setActiveTab,
    closePdf,
    openMobilePanel,
    closeMobilePanel,
  } = usePanelStore();
  const focusNode = selectedNode || activeNode;

  const [agent, setAgent] = useState<AgentInfo | null>(null);
  const [promptDraft, setPromptDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const telemetry = findTelemetry(nodeTelemetry, focusNode);
  const hasPdf = !!(preview || pdfUrl);
  const isPdfTab = activeTab === "pdf";

  useEffect(() => {
    if (!focusNode) {
      setAgent(null);
      setPromptDraft("");
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      setMessage(null);
      try {
        const { data } = await api.get<AgentInfo>(`/agents/${focusNode}`);
        if (cancelled) return;
        setAgent(data);
        setPromptDraft(data.system_prompt || "");
      } catch (err: unknown) {
        if (!cancelled) {
          setAgent(null);
          setError(getApiErrorMessage(err, "Could not load agent"));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [focusNode]);

  // When a canvas node is selected, surface the inspector tab (keep PDF loaded).
  useEffect(() => {
    if (focusNode && !isPdfTab) {
      openMobilePanel("inspector");
    }
  }, [focusNode]); // eslint-disable-line react-hooks/exhaustive-deps

  const evidencePretty = useMemo(() => {
    if (!telemetry?.evidence) return null;
    try {
      return JSON.stringify(telemetry.evidence, null, 2);
    } catch {
      return String(telemetry.evidence);
    }
  }, [telemetry?.evidence]);

  const savePrompt = async () => {
    if (!agent?.configurable || !focusNode) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const { data } = await api.put<{
        system_prompt: string;
        persisted: boolean;
      }>(`/agents/${focusNode}/prompt`, {
        system_prompt: promptDraft,
        persist: true,
      });
      setPromptDraft(data.system_prompt);
      setMessage(
        data.persisted
          ? "Prompt saved to YAML (next runs use it)."
          : "Prompt updated in memory."
      );
      setAgent((a) =>
        a ? { ...a, system_prompt: data.system_prompt } : a
      );
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Failed to save prompt"));
    } finally {
      setSaving(false);
    }
  };

  const closeAll = () => {
    closePdf();
    setSelectedNode(null);
    closeMobilePanel();
  };

  // Desktop: always visible. Mobile: overlay when opened / has content.
  const showAsOverlay = mobileOpen || hasPdf || !!focusNode;
  const wideForPdf = isPdfTab && hasPdf;

  const asideWidth = wideForPdf
    ? "lg:w-[min(52vw,40rem)] xl:w-[min(48vw,44rem)]"
    : "lg:w-80 xl:w-96";

  return (
    <>
      {/* Mobile: reopen side panel */}
      {!showAsOverlay && (
        <button
          type="button"
          onClick={() => openMobilePanel(hasPdf ? "pdf" : "inspector")}
          className="lg:hidden fixed bottom-20 right-4 z-40 inline-flex items-center gap-2 rounded-full border bg-card px-3 py-2.5 text-xs font-medium shadow-lg"
          title="Open side panel"
        >
          <PanelRight className="h-4 w-4" />
          Panel
        </button>
      )}

      {showAsOverlay && (
        <button
          type="button"
          aria-label="Close panel backdrop"
          className="lg:hidden fixed inset-0 z-40 bg-background/60 backdrop-blur-[2px]"
          onClick={closeAll}
        />
      )}

      <aside
        className={[
          "bg-card border-l border-border flex flex-col min-h-0 shrink-0 transition-all duration-300 ease-in-out overflow-hidden",
          asideWidth,
          showAsOverlay
            ? wideForPdf
              ? "fixed inset-y-0 right-0 z-50 w-[min(100vw,100%)] sm:w-[min(100vw,28rem)] md:w-[min(100vw,36rem)] shadow-2xl lg:static lg:z-auto lg:w-auto lg:shadow-none"
              : "fixed inset-y-0 right-0 z-50 w-[min(100vw,28rem)] sm:w-[min(100vw,32rem)] shadow-2xl lg:static lg:z-auto lg:w-auto lg:shadow-none"
            : "hidden lg:flex",
        ].join(" ")}
      >
        {/* Tabs */}
        <div className="h-12 sm:h-14 border-b border-border flex items-stretch px-1 sm:px-2 bg-muted/20 shrink-0 gap-0.5">
          <button
            type="button"
            onClick={() => setActiveTab("inspector")}
            className={`flex-1 min-w-0 text-xs sm:text-sm font-semibold flex items-center justify-center gap-1.5 px-2 border-b-2 transition-colors ${
              activeTab === "inspector"
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <FileSearch className="w-4 h-4 shrink-0" />
            <span className="truncate">Inspector</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("pdf")}
            className={`flex-1 min-w-0 text-xs sm:text-sm font-semibold flex items-center justify-center gap-1.5 px-2 border-b-2 transition-colors ${
              activeTab === "pdf"
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <FileText className="w-4 h-4 shrink-0" />
            <span className="truncate">Preview</span>
            {hasPdf && (
              <span className="hidden sm:inline h-1.5 w-1.5 rounded-full bg-primary shrink-0" />
            )}
          </button>
          <button
            type="button"
            onClick={closeAll}
            className="px-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-md my-1.5 lg:hidden"
            title="Close panel"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-hidden flex flex-col min-h-0">
          {isPdfTab ? (
            <PreviewPane
              preview={preview}
              fallbackUrl={pdfUrl}
              fallbackTitle={pdfTitle}
              onClear={closePdf}
              onSwitchInspector={() => setActiveTab("inspector")}
            />
          ) : (
            <InspectorPane
              focusNode={focusNode}
              activeNode={activeNode}
              agent={agent}
              loading={loading}
              telemetry={telemetry}
              evidencePretty={evidencePretty}
              promptDraft={promptDraft}
              setPromptDraft={setPromptDraft}
              saving={saving}
              savePrompt={savePrompt}
              message={message}
              error={error}
              hasPdf={hasPdf}
              onOpenPdf={() => setActiveTab("pdf")}
            />
          )}
        </div>
      </aside>
    </>
  );
}

function PreviewPane({
  preview,
  fallbackUrl,
  fallbackTitle,
  onClear,
  onSwitchInspector,
}: {
  preview: import("@/store/panelStore").DocumentPreview | null;
  fallbackUrl: string | null;
  fallbackTitle: string | null;
  onClear: () => void;
  onSwitchInspector: () => void;
}) {
  const title = preview?.title || fallbackTitle;
  const fileUrl = preview?.fileUrl || fallbackUrl;
  const kind =
    preview?.kind ||
    (fileUrl?.toLowerCase().endsWith(".pdf")
      ? "pdf"
      : fileUrl?.toLowerCase().endsWith(".docx")
        ? "docx"
        : "unsupported");
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loadingPdf, setLoadingPdf] = useState(false);
  const [docxMode, setDocxMode] = useState<"formatted" | "text">("formatted");
  const token = useAuthStore((s) => s.token);

  const isModernDocx =
    kind === "docx" &&
    (/\.docx($|\?)/i.test(fileUrl || "") || /\.docx($|\?)/i.test(title || ""));

  useEffect(() => {
    setDocxMode(isModernDocx ? "formatted" : "text");
  }, [fileUrl, kind, isModernDocx]);

  useEffect(() => {
    let revoked: string | null = null;
    let cancelled = false;

    async function loadPdfBlob() {
      if (kind !== "pdf" || !fileUrl) {
        setBlobUrl(null);
        setLoadError(null);
        return;
      }
      setLoadingPdf(true);
      setLoadError(null);
      try {
        const headers: HeadersInit = {};
        if (fileUrl.startsWith("/api/") && token) {
          headers.Authorization = `Bearer ${token}`;
        }
        const res = await fetch(fileUrl, { headers });
        if (!res.ok) {
          throw new Error(`Failed to load file (${res.status})`);
        }
        const blob = await res.blob();
        const typed =
          blob.type === "application/pdf"
            ? blob
            : new Blob([blob], { type: "application/pdf" });
        const url = URL.createObjectURL(typed);
        if (cancelled) {
          URL.revokeObjectURL(url);
          return;
        }
        revoked = url;
        setBlobUrl(url);
      } catch (err) {
        if (!cancelled) {
          setBlobUrl(null);
          setLoadError(
            err instanceof Error ? err.message : "Failed to load PDF document."
          );
        }
      } finally {
        if (!cancelled) setLoadingPdf(false);
      }
    }

    loadPdfBlob();
    return () => {
      cancelled = true;
      if (revoked) URL.revokeObjectURL(revoked);
    };
  }, [kind, fileUrl, token]);

  if (!fileUrl && !preview) {
    return (
      <div className="flex-1 p-6 flex flex-col items-center justify-center text-center text-muted-foreground text-sm gap-3">
        <FileText className="w-10 h-10 opacity-40" />
        <p className="font-medium text-foreground">No document open</p>
        <p className="max-w-xs leading-relaxed">
          In Resume Studio Library, click the eye on a PDF or DOCX — PDFs and
          DOCX render with layout here (DOCX ≈ Word formatting).
        </p>
        <button
          type="button"
          onClick={onSwitchInspector}
          className="mt-2 text-xs text-primary hover:underline"
        >
          Go to Node Inspector
        </button>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="shrink-0 flex flex-wrap items-center gap-1.5 sm:gap-2 px-2 sm:px-3 py-2 border-b border-border bg-muted/10">
        <div className="min-w-0 flex-1 basis-[40%]">
          <p className="text-xs font-medium truncate" title={title || fileUrl || ""}>
            {title || "Document"}
          </p>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wide">
            {kind === "pdf"
              ? "PDF preview"
              : kind === "docx"
                ? docxMode === "formatted"
                  ? "DOCX · Word layout"
                  : "DOCX · plain text"
                : kind === "text"
                  ? "Text preview"
                  : "Download only"}
          </p>
        </div>
        {kind === "docx" && isModernDocx && (
          <div className="flex rounded-md border border-border overflow-hidden text-[11px] shrink-0">
            <button
              type="button"
              onClick={() => setDocxMode("formatted")}
              className={`px-2 py-1 ${
                docxMode === "formatted"
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-muted text-muted-foreground"
              }`}
            >
              Formatted
            </button>
            <button
              type="button"
              onClick={() => setDocxMode("text")}
              className={`px-2 py-1 ${
                docxMode === "text"
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-muted text-muted-foreground"
              }`}
            >
              Text
            </button>
          </div>
        )}
        {fileUrl && (
          <a
            href={fileUrl}
            download={title || undefined}
            className="inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground px-2 py-1 rounded-md hover:bg-muted"
            onClick={async (e) => {
              if (!fileUrl.startsWith("/api/") || !token) return;
              e.preventDefault();
              const res = await fetch(fileUrl, {
                headers: { Authorization: `Bearer ${token}` },
              });
              if (!res.ok) return;
              const blob = await res.blob();
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = title || "resume";
              a.click();
              URL.revokeObjectURL(url);
            }}
          >
            <Download className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Download</span>
          </a>
        )}
        {fileUrl && (
          <a
            href={blobUrl || fileUrl}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground px-2 py-1 rounded-md hover:bg-muted"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Open</span>
          </a>
        )}
        <button
          type="button"
          onClick={onClear}
          className="inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground px-2 py-1 rounded-md hover:bg-muted"
          title="Clear preview"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {preview?.note && (
        <p className="shrink-0 px-3 py-1.5 text-[10px] sm:text-[11px] text-muted-foreground border-b border-border bg-muted/5 line-clamp-2">
          {preview.note}
        </p>
      )}

      {kind === "pdf" ? (
        loadingPdf ? (
          <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground gap-2">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading PDF…
          </div>
        ) : loadError || !blobUrl ? (
          <div className="flex-1 p-6 flex flex-col items-center justify-center text-center gap-3 text-sm">
            <p className="font-medium text-foreground">
              {loadError || "Failed to load PDF document."}
            </p>
            <p className="text-muted-foreground max-w-xs">
              Some PDFs fail in the embedded viewer. Download or open in a new tab
              instead.
            </p>
            <div className="flex flex-wrap gap-2 justify-center">
              {fileUrl && (
                <a
                  href={fileUrl}
                  className="inline-flex items-center gap-2 rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium"
                  onClick={async (e) => {
                    if (!token) return;
                    e.preventDefault();
                    const res = await fetch(fileUrl, {
                      headers: { Authorization: `Bearer ${token}` },
                    });
                    const blob = await res.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = title || "resume.pdf";
                    a.click();
                    URL.revokeObjectURL(url);
                  }}
                >
                  <Download className="w-4 h-4" /> Download PDF
                </a>
              )}
            </div>
          </div>
        ) : (
          <iframe
            src={`${blobUrl}#view=FitH`}
            className="flex-1 w-full min-h-[50vh] lg:min-h-0 bg-muted/30"
            title={title || "PDF Preview"}
          />
        )
      ) : kind === "docx" ? (
        docxMode === "formatted" && fileUrl && isModernDocx ? (
          <DocxFormattedPreview fileUrl={fileUrl} token={token} />
        ) : (
          <div className="flex-1 overflow-auto os-scrollbar p-4">
            <pre className="text-xs leading-relaxed whitespace-pre-wrap font-mono text-foreground/90">
              {preview?.text ||
                "No text extracted. Switch to Formatted or Download the original."}
            </pre>
          </div>
        )
      ) : kind === "text" ? (
        <div className="flex-1 overflow-auto os-scrollbar p-4">
          <pre className="text-xs leading-relaxed whitespace-pre-wrap font-mono text-foreground/90">
            {preview?.text || "No text extracted. Use Download for the original file."}
          </pre>
        </div>
      ) : (
        <div className="flex-1 p-6 flex flex-col items-center justify-center text-center gap-3 text-sm text-muted-foreground">
          <p>This file type cannot be previewed inline.</p>
          {fileUrl && (
            <a
              href={fileUrl}
              className="inline-flex items-center gap-2 rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium"
              onClick={async (e) => {
                if (!token) return;
                e.preventDefault();
                const res = await fetch(fileUrl, {
                  headers: { Authorization: `Bearer ${token}` },
                });
                const blob = await res.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = title || "file";
                a.click();
                URL.revokeObjectURL(url);
              }}
            >
              <Download className="w-4 h-4" /> Download file
            </a>
          )}
        </div>
      )}
    </div>
  );
}

function InspectorPane({
  focusNode,
  activeNode,
  agent,
  loading,
  telemetry,
  evidencePretty,
  promptDraft,
  setPromptDraft,
  saving,
  savePrompt,
  message,
  error,
  hasPdf,
  onOpenPdf,
}: {
  focusNode: string | null;
  activeNode: string | null;
  agent: AgentInfo | null;
  loading: boolean;
  telemetry: {
    latency_ms?: number;
    tokens?: number;
    cost?: number;
    status: string;
  } | null;
  evidencePretty: string | null;
  promptDraft: string;
  setPromptDraft: (v: string) => void;
  saving: boolean;
  savePrompt: () => void;
  message: string | null;
  error: string | null;
  hasPdf: boolean;
  onOpenPdf: () => void;
}) {
  if (!focusNode) {
    return (
      <div className="flex-1 p-4 flex flex-col items-center justify-center text-center text-muted-foreground text-sm gap-3">
        <Bot className="w-8 h-8 opacity-40" />
        <p>
          Click a canvas agent to inspect what it does and edit its system
          prompt.
        </p>
        {hasPdf && (
          <button
            type="button"
            onClick={onOpenPdf}
            className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-xs font-medium hover:bg-muted text-foreground"
          >
            <FileText className="w-4 h-4" />
            Switch to document preview
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-auto os-scrollbar p-4 space-y-5">
      {activeNode === focusNode && (
        <p className="text-[10px] uppercase tracking-wide text-primary font-medium">
          Running
        </p>
      )}
      {loading ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="w-4 h-4 animate-spin" /> Loading agent…
        </div>
      ) : (
        <>
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-primary font-medium text-sm">
              <Info className="h-4 w-4 shrink-0" />
              <span>{agent?.label || focusNode}</span>
            </div>
            <p className="text-[11px] text-muted-foreground font-mono">
              {focusNode}
            </p>
            {agent?.description && (
              <p className="text-xs text-muted-foreground leading-relaxed">
                {agent.description}
              </p>
            )}
            {agent?.capabilities?.length ? (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {agent.capabilities.map((c) => (
                  <span
                    key={c}
                    className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground border border-border"
                  >
                    {c}
                  </span>
                ))}
              </div>
            ) : null}
          </div>

          <div className="space-y-3 pt-4 border-t border-border">
            <h4 className="text-xs font-semibold uppercase text-muted-foreground tracking-wider flex items-center gap-1.5">
              <Zap className="w-3 h-3" /> Last run telemetry
            </h4>
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-muted/50 p-2.5 rounded-lg border border-border/50">
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
                  <Clock className="h-3 w-3" /> Latency
                </div>
                <span className="text-sm font-medium">
                  {telemetry?.latency_ms != null
                    ? `${(telemetry.latency_ms / 1000).toFixed(2)}s`
                    : "—"}
                </span>
              </div>
              <div className="bg-muted/50 p-2.5 rounded-lg border border-border/50">
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
                  <DollarSign className="h-3 w-3" /> Cost
                </div>
                <span className="text-sm font-medium">
                  {telemetry?.cost != null
                    ? `$${telemetry.cost.toFixed(4)}`
                    : "—"}
                </span>
              </div>
              <div className="bg-muted/50 p-2.5 rounded-lg border border-border/50 col-span-2">
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
                  <FileCode2 className="h-3 w-3" /> Tokens / status
                </div>
                <span className="text-sm font-medium">
                  {telemetry?.tokens != null
                    ? `${telemetry.tokens} tkns`
                    : "—"}
                  {telemetry?.status ? ` · ${telemetry.status}` : ""}
                </span>
              </div>
            </div>
          </div>

          {evidencePretty && (
            <div className="space-y-2 pt-4 border-t border-border">
              <h4 className="text-xs font-semibold uppercase text-muted-foreground tracking-wider flex items-center gap-1.5">
                <GitCommit className="w-3 h-3" /> Evidence (last output)
              </h4>
              <pre className="text-[10px] leading-relaxed bg-muted/40 border border-border rounded-lg p-2.5 overflow-auto max-h-40 whitespace-pre-wrap break-words font-mono text-muted-foreground">
                {evidencePretty}
              </pre>
            </div>
          )}

          {agent?.configurable && (
            <div className="space-y-2 pt-4 border-t border-border">
              <div className="flex items-center justify-between gap-2">
                <h4 className="text-xs font-semibold uppercase text-muted-foreground tracking-wider">
                  System prompt
                </h4>
                <button
                  type="button"
                  onClick={savePrompt}
                  disabled={
                    saving || promptDraft === (agent.system_prompt || "")
                  }
                  className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-md bg-primary text-primary-foreground disabled:opacity-40"
                >
                  {saving ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <Save className="w-3 h-3" />
                  )}
                  Save
                </button>
              </div>
              <textarea
                value={promptDraft}
                onChange={(e) => setPromptDraft(e.target.value)}
                rows={10}
                className="w-full text-[11px] leading-relaxed font-mono rounded-lg border border-border bg-background px-2.5 py-2 outline-none focus:ring-1 focus:ring-primary resize-y min-h-[140px]"
                spellCheck={false}
              />
              <p className="text-[10px] text-muted-foreground">
                Edits persist to{" "}
                <code className="text-[10px]">
                  backend/app/core/prompts/{focusNode}.yaml
                </code>
              </p>
            </div>
          )}

          {agent && !agent.configurable && (
            <div className="pt-4 border-t border-border text-xs text-muted-foreground leading-relaxed">
              This step is UI/DB only — review drafts on{" "}
              <span className="text-foreground">/approvals</span>.
            </div>
          )}

          {message && <p className="text-[11px] text-emerald-400">{message}</p>}
          {error && <p className="text-[11px] text-red-400">{error}</p>}

          {hasPdf && (
            <button
              type="button"
              onClick={onOpenPdf}
              className="w-full mt-2 inline-flex items-center justify-center gap-2 rounded-md border px-3 py-2 text-xs font-medium hover:bg-muted"
            >
              <FileText className="w-4 h-4" />
              Switch to document preview
            </button>
          )}
        </>
      )}
    </div>
  );
}
