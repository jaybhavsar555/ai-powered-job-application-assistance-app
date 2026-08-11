"use client";

import Link from "next/link";
import {
  AlertCircle,
  CheckCircle2,
  CircleDashed,
  Loader2,
  RotateCcw,
} from "lucide-react";

export type AgentTaskStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "needs_input"
  | "reapply";

export type AgentTaskRowProps = {
  title: string;
  subtitle?: string;
  meta?: string;
  status: AgentTaskStatus;
  href?: string;
  actionLabel?: string;
  badge?: string;
  className?: string;
  onClick?: () => void;
};

function statusIcon(status: AgentTaskStatus) {
  switch (status) {
    case "running":
      return <Loader2 className="h-4 w-4 animate-spin text-foreground" />;
    case "completed":
      return <CheckCircle2 className="h-4 w-4 text-emerald-600" />;
    case "failed":
      return <AlertCircle className="h-4 w-4 text-destructive" />;
    case "needs_input":
      return <AlertCircle className="h-4 w-4 text-amber-600" />;
    case "reapply":
      return <RotateCcw className="h-4 w-4 text-sky-600" />;
    default:
      return <CircleDashed className="h-4 w-4 text-muted-foreground" />;
  }
}

function statusTone(status: AgentTaskStatus): string {
  switch (status) {
    case "running":
      return "border-foreground/15 bg-muted/40";
    case "completed":
      return "border-emerald-500/25 bg-emerald-500/5";
    case "failed":
      return "border-destructive/30 bg-destructive/5";
    case "needs_input":
      return "border-amber-500/30 bg-amber-500/5";
    case "reapply":
      return "border-sky-500/30 bg-sky-500/5";
    default:
      return "border-border bg-card";
  }
}

function defaultAction(status: AgentTaskStatus): string {
  switch (status) {
    case "needs_input":
      return "Fix →";
    case "failed":
      return "Retry →";
    case "reapply":
      return "Reapply →";
    case "completed":
      return "View →";
    case "running":
      return "Open →";
    default:
      return "Start →";
  }
}

export function AgentTaskRow({
  title,
  subtitle,
  meta,
  status,
  href,
  actionLabel,
  badge,
  className = "",
  onClick,
}: AgentTaskRowProps) {
  const body = (
    <div
      className={`flex items-center justify-between gap-3 rounded-lg border px-4 py-3 transition-colors hover:bg-muted/50 ${statusTone(
        status
      )} ${className}`}
    >
      <div className="flex items-start gap-3 min-w-0">
        <span className="mt-0.5 shrink-0">{statusIcon(status)}</span>
        <div className="min-w-0 space-y-0.5">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-medium text-foreground truncate">
              {title}
            </p>
            {badge && (
              <span className="text-[10px] uppercase tracking-wider text-muted-foreground border border-border rounded px-1.5 py-0.5">
                {badge}
              </span>
            )}
          </div>
          {(subtitle || meta) && (
            <p className="text-xs text-muted-foreground truncate">
              {[subtitle, meta].filter(Boolean).join(" · ")}
            </p>
          )}
        </div>
      </div>
      <span className="text-xs font-medium text-primary shrink-0">
        {actionLabel || defaultAction(status)}
      </span>
    </div>
  );

  if (href) {
    return (
      <Link href={href} className="block" onClick={onClick}>
        {body}
      </Link>
    );
  }

  if (onClick) {
    return (
      <button type="button" className="w-full text-left" onClick={onClick}>
        {body}
      </button>
    );
  }

  return body;
}

/** Map Tracker / Inbox stage strings to AgentTaskStatus */
export function stageToTaskStatus(stage?: string | null): AgentTaskStatus {
  const s = (stage || "").toLowerCase();
  if (s === "ready" || s.includes("applied")) return "pending";
  if (s === "needs input" || s === "needs_input") return "needs_input";
  if (s === "failed") return "failed";
  if (s === "reapply") return "reapply";
  if (s === "researching") return "running";
  return "pending";
}
