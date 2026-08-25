"use client";

import { useCallback, useState } from "react";
import { FileCode, Download, RefreshCw, AlertCircle } from "lucide-react";

interface LatexEditorProps {
  initialTex: string;
  authHeaders: () => Record<string, string>;
  filename?: string;
  onClose?: () => void;
}

export function LatexEditor({
  initialTex,
  authHeaders,
  filename = "Tailored_Resume",
  onClose,
}: LatexEditorProps) {
  const [tex, setTex] = useState(initialTex);
  const [compiling, setCompiling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);

  const compilePdf = useCallback(async () => {
    setCompiling(true);
    setError(null);
    if (pdfUrl) {
      URL.revokeObjectURL(pdfUrl);
      setPdfUrl(null);
    }
    try {
      const res = await fetch("/api/v1/documents/compile/tex", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ tex_content: tex, filename }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(typeof body.detail === "string" ? body.detail : "Compile failed");
      }
      const blob = await res.blob();
      setPdfUrl(URL.createObjectURL(blob));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Compile failed");
    } finally {
      setCompiling(false);
    }
  }, [authHeaders, filename, pdfUrl, tex]);

  const downloadTex = () => {
    const blob = new Blob([tex], { type: "application/x-tex" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${filename}.tex`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadPdf = () => {
    if (!pdfUrl) return;
    const a = document.createElement("a");
    a.href = pdfUrl;
    a.download = `${filename}.pdf`;
    a.click();
  };

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2 p-4 border-b border-border bg-muted/40">
        <span className="font-semibold text-sm flex items-center gap-2">
          <FileCode className="h-4 w-4" />
          LaTeX editor
        </span>
        <div className="flex flex-wrap items-center gap-2">
          {onClose && (
            <button type="button" onClick={onClose} className="text-xs text-muted-foreground hover:text-foreground">
              Close
            </button>
          )}
          <button
            type="button"
            onClick={downloadTex}
            className="inline-flex items-center gap-1 text-xs font-medium border border-border px-2.5 py-1.5 rounded-md hover:bg-muted"
          >
            <Download className="h-3.5 w-3.5" /> .tex
          </button>
          <button
            type="button"
            onClick={compilePdf}
            disabled={compiling || !tex.trim()}
            className="inline-flex items-center gap-1 text-xs font-medium bg-primary text-primary-foreground px-3 py-1.5 rounded-md disabled:opacity-50"
          >
            {compiling ? (
              <span className="h-3.5 w-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <RefreshCw className="h-3.5 w-3.5" />
            )}
            Recompile PDF
          </button>
          {pdfUrl && (
            <button
              type="button"
              onClick={downloadPdf}
              className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 dark:text-emerald-400 hover:underline"
            >
              Download PDF
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="mx-4 mt-4 flex items-start gap-2 text-xs text-destructive bg-destructive/10 border border-destructive/20 rounded-md p-3">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-0 lg:divide-x divide-border">
        <textarea
          value={tex}
          onChange={(e) => setTex(e.target.value)}
          spellCheck={false}
          className="w-full min-h-[320px] max-h-[480px] p-4 text-xs font-mono bg-background border-0 resize-y focus:outline-none focus:ring-0"
          placeholder="\\documentclass..."
        />
        <div className="min-h-[320px] bg-muted/20 flex flex-col">
          <p className="text-[11px] uppercase tracking-wider text-muted-foreground px-4 py-2 border-b border-border">
            PDF preview
          </p>
          {pdfUrl ? (
            <iframe title="LaTeX PDF preview" src={pdfUrl} className="flex-1 w-full min-h-[280px] bg-white" />
          ) : (
            <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground p-6 text-center">
              Edit LaTeX, then click Recompile PDF to preview.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
