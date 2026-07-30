import React from 'react';
import { Check, X, GitCommit, FileText, Loader2 } from 'lucide-react';

interface ApprovalCardProps {
  title: string;
  originalText: string;
  proposedText: string;
  evidence: string;
  onApprove?: () => void;
  onReject?: () => void;
  status?: 'pending' | 'approved' | 'rejected' | 'saving';
  disabled?: boolean;
}

export function ApprovalCard({
  title,
  originalText,
  proposedText,
  evidence,
  onApprove,
  onReject,
  status = 'pending',
  disabled = false,
}: ApprovalCardProps) {
  const decided = status === 'approved' || status === 'rejected';
  const saving = status === 'saving';

  return (
    <div className={`border border-border rounded-xl bg-card overflow-hidden shadow-sm ${decided ? 'opacity-90' : ''}`}>
      <div className="flex items-center justify-between p-3 border-b border-border bg-muted/30 gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <GitCommit className="h-4 w-4 text-primary shrink-0" />
          <h4 className="font-semibold text-sm text-foreground truncate">{title}</h4>
          {status === 'approved' && (
            <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/20">
              Approved
            </span>
          )}
          {status === 'rejected' && (
            <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-red-500/15 text-red-400 border border-red-500/20">
              Rejected
            </span>
          )}
        </div>
        {!decided && (
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={onReject}
              disabled={disabled || saving}
              className="flex items-center gap-1 text-xs font-medium px-2 py-1 rounded text-red-500 hover:bg-red-500/10 transition-colors disabled:opacity-50"
            >
              {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <X className="h-3.5 w-3.5" />}
              Reject
            </button>
            <button
              onClick={onApprove}
              disabled={disabled || saving}
              className="flex items-center gap-1 text-xs font-medium px-2 py-1 rounded bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
              Approve
            </button>
          </div>
        )}
      </div>

      <div className="p-4 space-y-4">
        <div className="grid grid-cols-1 gap-2 font-mono text-xs">
          <div className="p-2.5 rounded bg-red-500/10 border border-red-500/20 text-red-400 relative">
            <span className="absolute -left-1.5 top-2.5 text-[10px] bg-background px-1 rounded border border-border">OLD</span>
            <span className="pl-4 break-words line-through opacity-80">{originalText}</span>
          </div>
          <div className="p-2.5 rounded bg-green-500/10 border border-green-500/20 text-green-400 relative">
            <span className="absolute -left-1.5 top-2.5 text-[10px] bg-background px-1 rounded border border-border">NEW</span>
            <span className="pl-4 break-words whitespace-pre-wrap">{proposedText}</span>
          </div>
        </div>

        <div className="p-3 bg-muted/40 rounded-lg border border-border/50">
          <div className="flex items-start gap-2">
            <FileText className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">AI Reasoning</span>
              <p className="text-xs text-foreground/80 leading-relaxed">{evidence}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
