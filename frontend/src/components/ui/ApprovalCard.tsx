import React from 'react';
import { Check, X, GitCommit, FileText } from 'lucide-react';

interface ApprovalCardProps {
  title: string;
  originalText: string;
  proposedText: string;
  evidence: string;
  onApprove?: () => void;
  onReject?: () => void;
}

export function ApprovalCard({ title, originalText, proposedText, evidence, onApprove, onReject }: ApprovalCardProps) {
  return (
    <div className="border border-border rounded-xl bg-card overflow-hidden shadow-sm">
      <div className="flex items-center justify-between p-3 border-b border-border bg-muted/30">
        <div className="flex items-center gap-2">
          <GitCommit className="h-4 w-4 text-primary" />
          <h4 className="font-semibold text-sm text-foreground">{title}</h4>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={onReject} className="flex items-center gap-1 text-xs font-medium px-2 py-1 rounded text-red-500 hover:bg-red-500/10 transition-colors">
            <X className="h-3.5 w-3.5" /> Reject
          </button>
          <button onClick={onApprove} className="flex items-center gap-1 text-xs font-medium px-2 py-1 rounded bg-primary text-primary-foreground hover:bg-primary/90 transition-colors">
            <Check className="h-3.5 w-3.5" /> Approve
          </button>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {/* Diff View */}
        <div className="grid grid-cols-1 gap-2 font-mono text-xs">
          <div className="p-2.5 rounded bg-red-500/10 border border-red-500/20 text-red-400 relative">
            <span className="absolute -left-1.5 top-2.5 text-[10px] bg-background px-1 rounded border border-border">OLD</span>
            <span className="pl-4 break-words line-through opacity-80">{originalText}</span>
          </div>
          <div className="p-2.5 rounded bg-green-500/10 border border-green-500/20 text-green-400 relative">
            <span className="absolute -left-1.5 top-2.5 text-[10px] bg-background px-1 rounded border border-border">NEW</span>
            <span className="pl-4 break-words">{proposedText}</span>
          </div>
        </div>

        {/* Evidence Panel */}
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
