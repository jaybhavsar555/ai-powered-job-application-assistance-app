"use client";

import {
  Code2,
  FileSearch,
  Loader2,
  Mail,
  Search,
  Sparkles,
  Wrench,
} from "lucide-react";

export type ToolChipStatus = "idle" | "running" | "done" | "error";

export type ToolChipProps = {
  label: string;
  status?: ToolChipStatus;
  kind?: "tool" | "search" | "code" | "mail" | "file" | "agent";
  meta?: string;
  className?: string;
};

const KIND_ICON = {
  tool: Wrench,
  search: Search,
  code: Code2,
  mail: Mail,
  file: FileSearch,
  agent: Sparkles,
} as const;

export function ToolChip({
  label,
  status = "done",
  kind = "tool",
  meta,
  className = "",
}: ToolChipProps) {
  const Icon = KIND_ICON[kind] || Wrench;
  const running = status === "running";

  return (
    <span
      className={`inline-flex items-center gap-1.5 max-w-full rounded-md border px-2 py-1 text-xs transition-colors ${
        status === "error"
          ? "border-destructive/40 bg-destructive/5 text-destructive"
          : running
            ? "border-foreground/20 bg-muted text-foreground"
            : "border-border bg-card text-muted-foreground"
      } ${className}`}
      title={meta || label}
    >
      {running ? (
        <Loader2 className="h-3 w-3 animate-spin shrink-0" />
      ) : (
        <Icon className="h-3 w-3 shrink-0 opacity-70" />
      )}
      <span className="truncate font-medium">{label}</span>
      {meta && (
        <span className="text-[10px] opacity-70 tabular-nums shrink-0">
          {meta}
        </span>
      )}
    </span>
  );
}

interface ToolChipRowProps {
  chips: ToolChipProps[];
  summary?: string;
  className?: string;
}

export function ToolChipRow({
  chips,
  summary,
  className = "",
}: ToolChipRowProps) {
  if (!chips.length) return null;
  return (
    <div className={`space-y-1.5 ${className}`}>
      {summary && (
        <p className="text-[11px] text-muted-foreground">{summary}</p>
      )}
      <div className="flex flex-wrap gap-1.5">
        {chips.map((chip, i) => (
          <ToolChip key={`${chip.label}-${i}`} {...chip} />
        ))}
      </div>
    </div>
  );
}
