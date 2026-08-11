import React, { useState } from "react";
import { X } from "lucide-react";

interface ResumeData {
  title?: string;
  text: string;
}

export interface ResumeComparisonProps {
  original: ResumeData;
  updated: ResumeData;
  onDownload: () => void;
  onClose: () => void;
}

export const ResumeComparison: React.FC<ResumeComparisonProps> = ({ original, updated, onDownload, onClose }) => {
  const [viewMode, setViewMode] = useState<"text" | "raw">("text");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-card rounded-xl shadow-lg w-full max-w-4xl max-h-[90vh] overflow-auto p-6">
        <header className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Resume Comparison</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="h-5 w-5" />
          </button>
        </header>
        <div className="flex gap-4 mb-4">
          <button
            onClick={() => setViewMode("text")}
            className={viewMode === "text" ? "bg-primary text-primary-foreground px-3 py-1 rounded" : "px-3 py-1"}
          >
            Text View
          </button>
          <button
            onClick={() => setViewMode("raw")}
            className={viewMode === "raw" ? "bg-primary text-primary-foreground px-3 py-1 rounded" : "px-3 py-1"}
          >
            Raw JSON
          </button>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <section className="border border-muted rounded p-2 overflow-auto">
            <h3 className="font-medium mb-2">Original</h3>
            {viewMode === "text" ? (
              <pre className="text-sm whitespace-pre-wrap">{original.text}</pre>
            ) : (
              <pre className="text-xs whitespace-pre-wrap">{JSON.stringify(original, null, 2)}</pre>
            )}
          </section>
          <section className="border border-muted rounded p-2 overflow-auto">
            <h3 className="font-medium mb-2">Updated</h3>
            {viewMode === "text" ? (
              <pre className="text-sm whitespace-pre-wrap">{updated.text}</pre>
            ) : (
              <pre className="text-xs whitespace-pre-wrap">{JSON.stringify(updated, null, 2)}</pre>
            )}
          </section>
        </div>
        <footer className="flex justify-end mt-4 gap-2">
          <button onClick={onClose} className="px-4 py-2 border rounded bg-muted hover:bg-muted/80">
            Cancel
          </button>
          <button onClick={onDownload} className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90">
            Download Updated
          </button>
        </footer>
      </div>
    </div>
  );
};
