import React from "react";
import {
  Check,
  X,
  FileText,
  Loader2,
  Sparkles,
  RotateCcw,
  SkipForward,
} from "lucide-react";

import type { StructuredResumeData } from "@/types/resume";

interface ApprovalCardProps {
  title: string;
  originalText: string;
  proposedText: string;
  proposedData?: StructuredResumeData;
  evidence: string;
  onApprove?: (editedText?: string, editedData?: StructuredResumeData) => void;
  onReject?: () => void;
  onReevaluate?: (editedData: StructuredResumeData) => Promise<void>;
  /** Soft skip — leave pending / revisit later */
  onSkip?: () => void;
  /** Ask agent to revise (optional — parent may open Canvas) */
  onRevise?: () => void;
  status?: "pending" | "approved" | "rejected" | "saving" | "skipped";
  disabled?: boolean;
  /** When true, hide the low-value "OLD" placeholder and show draft-only layout */
  isNewDraft?: boolean;
  /** 0–100 confidence for the recommendation meter */
  confidence?: number;
  confidenceLabel?: string;
}

function ConfidenceMeter({
  value,
  label,
}: {
  value: number;
  label?: string;
}) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-2 text-[11px] uppercase tracking-wider text-muted-foreground">
        <span>{label || "Confidence"}</span>
        <span className="tabular-nums font-medium text-foreground">
          {clamped}%
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-muted overflow-hidden">
        <div
          className="h-full rounded-full bg-foreground/80 transition-[width] duration-500 ease-out"
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}

export function ApprovalCard({
  title,
  originalText,
  proposedText,
  proposedData,
  evidence,
  onApprove,
  onReject,
  onSkip,
  onRevise,
  onReevaluate,
  status = "pending",
  disabled = false,
  isNewDraft = false,
  confidence,
  confidenceLabel,
}: ApprovalCardProps) {
  const [isEditing, setIsEditing] = React.useState(false);
  const [editedText, setEditedText] = React.useState(proposedText);
  const [editedSummary, setEditedSummary] = React.useState(proposedData?.summary || "");
  const [editedBullets, setEditedBullets] = React.useState<string[]>(proposedData?.tailored_bullets || []);
  const [isReevaluating, setIsReevaluating] = React.useState(false);

  // Sync state if props change externally (only when not editing)
  React.useEffect(() => {
    if (!isEditing) {
      setEditedText(proposedText);
      setEditedSummary(proposedData?.summary || "");
      setEditedBullets(proposedData?.tailored_bullets || []);
    }
  }, [proposedText, proposedData, isEditing]);

  const decided =
    status === "approved" || status === "rejected" || status === "skipped";
  const saving = status === "saving";
  const showDiff = !isNewDraft && Boolean(originalText?.trim());
  const busy = disabled || saving;

  const handleApprove = () => {
    if (onApprove) {
      if (proposedData && isEditing) {
        onApprove(undefined, { summary: editedSummary, tailored_bullets: editedBullets });
      } else {
        onApprove(isEditing ? editedText : undefined);
      }
    }
  };

  const handleReevaluate = async () => {
    if (onReevaluate) {
      setIsReevaluating(true);
      try {
        await onReevaluate({ summary: editedSummary, tailored_bullets: editedBullets });
      } finally {
        setIsReevaluating(false);
      }
    }
  };

  return (
    <div
      className={`border border-border rounded-xl bg-card overflow-hidden shadow-sm ${
        decided ? "opacity-95" : ""
      }`}
    >
      <div className="flex items-center justify-between p-4 border-b border-border bg-muted/40 gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <Sparkles className="h-4 w-4 text-primary shrink-0" />
          <h4 className="font-semibold text-base text-foreground truncate">
            {title}
          </h4>
          {status === "approved" && (
            <span className="text-[11px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30">
              Approved
            </span>
          )}
          {status === "rejected" && (
            <span className="text-[11px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-red-500/15 text-red-700 dark:text-red-300 border border-red-500/30">
              Rejected
            </span>
          )}
          {status === "skipped" && (
            <span className="text-[11px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-muted text-muted-foreground border border-border">
              Skipped
            </span>
          )}
        </div>
      </div>

      <div className="p-5 space-y-4">
        {typeof confidence === "number" && (
          <ConfidenceMeter value={confidence} label={confidenceLabel} />
        )}

        {showDiff && (
          <div className="rounded-lg border border-border bg-muted/30 p-4">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
              Previous
            </p>
            <p className="text-sm leading-relaxed text-muted-foreground whitespace-pre-wrap break-words">
              {originalText}
            </p>
          </div>
        )}

        <div className="rounded-lg border border-border bg-muted/20 p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-2 flex justify-between items-center">
            <span>{isNewDraft || !showDiff ? "Proposed draft" : "Proposed changes"}</span>
            {isEditing && <span className="text-primary">Editing Mode</span>}
          </p>
          {isEditing && proposedData ? (
            <div className="space-y-4 mt-2">
              <div>
                <label className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Summary</label>
                <textarea
                  value={editedSummary}
                  onChange={(e) => setEditedSummary(e.target.value)}
                  className="w-full min-h-[100px] p-3 text-[14px] leading-6 bg-background border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-primary/50 font-mono resize-y mt-1"
                />
              </div>
              <div>
                <label className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Bullets</label>
                <div className="space-y-2 mt-1">
                  {editedBullets.map((bullet, i) => (
                    <textarea
                      key={i}
                      value={bullet}
                      onChange={(e) => {
                        const newBullets = [...editedBullets];
                        newBullets[i] = e.target.value;
                        setEditedBullets(newBullets);
                      }}
                      className="w-full min-h-[60px] p-2 text-[14px] leading-5 bg-background border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-primary/50 font-mono resize-y"
                    />
                  ))}
                </div>
              </div>
            </div>
          ) : isEditing ? (
            <textarea
              value={editedText}
              onChange={(e) => setEditedText(e.target.value)}
              className="w-full min-h-[200px] p-3 text-[15px] leading-7 bg-background border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-primary/50 font-mono resize-y"
              placeholder="Enter your manual edits here..."
            />
          ) : (
            <div className="text-[15px] leading-7 text-foreground whitespace-pre-wrap break-words">
              {proposedText}
            </div>
          )}
        </div>

        <div className="p-4 rounded-lg border border-border bg-muted/50">
          <div className="flex items-start gap-3">
            <FileText className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
            <div className="space-y-1.5 min-w-0">
              <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                Why this change
              </span>
              <p className="text-sm text-foreground leading-relaxed">
                {evidence}
              </p>
            </div>
          </div>
        </div>

        {!decided && (
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <button
              type="button"
              onClick={handleApprove}
              disabled={busy}
              className="inline-flex items-center gap-1.5 text-sm font-medium px-3 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              {saving ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Check className="h-4 w-4" />
              )}
              {isEditing ? "Save & Accept" : "Accept"}
            </button>
            {!isEditing && (
              <button
                type="button"
                onClick={() => setIsEditing(true)}
                disabled={busy}
                className="inline-flex items-center gap-1.5 text-sm font-medium px-3 py-2 rounded-md border border-border hover:bg-muted transition-colors disabled:opacity-50"
              >
                <FileText className="h-4 w-4" />
                Edit manually
              </button>
            )}
            {isEditing && onReevaluate && (
              <button
                type="button"
                onClick={handleReevaluate}
                disabled={busy || isReevaluating}
                className="inline-flex items-center gap-1.5 text-sm font-medium px-3 py-2 rounded-md border border-border hover:bg-muted transition-colors disabled:opacity-50 text-indigo-500 dark:text-indigo-400"
              >
                {isReevaluating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4" />
                )}
                Re-evaluate Score
              </button>
            )}
            {onRevise && (
              <button
                type="button"
                onClick={onRevise}
                disabled={busy}
                className="inline-flex items-center gap-1.5 text-sm font-medium px-3 py-2 rounded-md border border-border hover:bg-muted transition-colors disabled:opacity-50"
              >
                <RotateCcw className="h-4 w-4" />
                Revise
              </button>
            )}
            {onSkip && (
              <button
                type="button"
                onClick={onSkip}
                disabled={busy}
                className="inline-flex items-center gap-1.5 text-sm font-medium px-3 py-2 rounded-md border border-border text-muted-foreground hover:bg-muted transition-colors disabled:opacity-50"
              >
                <SkipForward className="h-4 w-4" />
                Skip for now
              </button>
            )}
            <button
              type="button"
              onClick={onReject}
              disabled={busy}
              className="inline-flex items-center gap-1.5 text-sm font-medium px-3 py-2 rounded-md text-destructive border border-destructive/40 hover:bg-destructive/10 transition-colors disabled:opacity-50 ml-auto"
            >
              {saving ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <X className="h-4 w-4" />
              )}
              Reject
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
