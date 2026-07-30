import React from "react";
import { Check, X, FileText, Loader2, Sparkles } from "lucide-react";

interface ApprovalCardProps {
  title: string;
  originalText: string;
  proposedText: string;
  evidence: string;
  onApprove?: () => void;
  onReject?: () => void;
  status?: "pending" | "approved" | "rejected" | "saving";
  disabled?: boolean;
  /** When true, hide the low-value "OLD" placeholder and show draft-only layout */
  isNewDraft?: boolean;
}

export function ApprovalCard({
  title,
  originalText,
  proposedText,
  evidence,
  onApprove,
  onReject,
  status = "pending",
  disabled = false,
  isNewDraft = false,
}: ApprovalCardProps) {
  const decided = status === "approved" || status === "rejected";
  const saving = status === "saving";
  const showDiff = !isNewDraft && Boolean(originalText?.trim());

  return (
    <div
      className={`border border-border rounded-xl bg-card overflow-hidden shadow-sm ${
        decided ? "opacity-95" : ""
      }`}
    >
      <div className="flex items-center justify-between p-4 border-b border-border bg-muted/40 gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <Sparkles className="h-4 w-4 text-primary shrink-0" />
          <h4 className="font-semibold text-base text-foreground truncate">{title}</h4>
          {status === "approved" && (
            <span className="text-[11px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              Approved
            </span>
          )}
          {status === "rejected" && (
            <span className="text-[11px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-red-500/20 text-red-300 border border-red-500/30">
              Rejected
            </span>
          )}
        </div>
        {!decided && (
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={onReject}
              disabled={disabled || saving}
              className="flex items-center gap-1.5 text-sm font-medium px-3 py-1.5 rounded-md text-red-300 border border-red-500/40 hover:bg-red-500/15 transition-colors disabled:opacity-50"
            >
              {saving ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <X className="h-4 w-4" />
              )}
              Reject
            </button>
            <button
              type="button"
              onClick={onApprove}
              disabled={disabled || saving}
              className="flex items-center gap-1.5 text-sm font-medium px-3 py-1.5 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              {saving ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Check className="h-4 w-4" />
              )}
              Approve
            </button>
          </div>
        )}
      </div>

      <div className="p-5 space-y-4">
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

        <div className="rounded-lg border border-emerald-500/40 bg-emerald-950/40 p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-emerald-300/90 mb-2">
            {isNewDraft || !showDiff ? "Proposed draft" : "Proposed changes"}
          </p>
          <div className="text-[15px] leading-7 text-zinc-50 whitespace-pre-wrap break-words">
            {proposedText}
          </div>
        </div>

        <div className="p-4 rounded-lg border border-border bg-muted/50">
          <div className="flex items-start gap-3">
            <FileText className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
            <div className="space-y-1.5 min-w-0">
              <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                Why this change
              </span>
              <p className="text-sm text-foreground leading-relaxed">{evidence}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
