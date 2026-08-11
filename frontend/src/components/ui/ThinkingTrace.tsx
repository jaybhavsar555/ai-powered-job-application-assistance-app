"use client";

import { useState } from "react";
import {
  CheckCircle2,
  ChevronDown,
  Circle,
  Loader2,
  XCircle,
} from "lucide-react";

export type ThinkingStepStatus = "pending" | "running" | "success" | "error";

export type ThinkingStep = {
  id: string;
  label: string;
  detail?: string;
  status: ThinkingStepStatus;
  kind?: "step" | "reasoning" | "search" | "coding";
};

interface ThinkingTraceProps {
  title?: string;
  steps: ThinkingStep[];
  /** When true, expand the panel by default */
  defaultOpen?: boolean;
  className?: string;
}

function StepIcon({ status }: { status: ThinkingStepStatus }) {
  if (status === "running") {
    return <Loader2 className="h-3.5 w-3.5 animate-spin text-foreground" />;
  }
  if (status === "success") {
    return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />;
  }
  if (status === "error") {
    return <XCircle className="h-3.5 w-3.5 text-destructive" />;
  }
  return <Circle className="h-3.5 w-3.5 text-muted-foreground/50" />;
}

export function ThinkingTrace({
  title = "Thinking",
  steps,
  defaultOpen = true,
  className = "",
}: ThinkingTraceProps) {
  const [open, setOpen] = useState(defaultOpen);
  const running = steps.some((s) => s.status === "running");
  const done = steps.length > 0 && steps.every((s) => s.status === "success");

  return (
    <div
      className={`rounded-xl border border-border bg-card overflow-hidden ${className}`}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-3 px-4 py-3 text-left hover:bg-muted/40 transition-colors"
      >
        <div className="flex items-center gap-2 min-w-0">
          {running ? (
            <span className="relative flex h-2 w-2 shrink-0">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-foreground/40 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-foreground" />
            </span>
          ) : done ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
          ) : (
            <Circle className="h-4 w-4 text-muted-foreground shrink-0" />
          )}
          <span className="text-sm font-semibold text-foreground truncate">
            {title}
          </span>
          <span className="text-[11px] text-muted-foreground tabular-nums">
            {steps.filter((s) => s.status === "success").length}/{steps.length}
          </span>
        </div>
        <ChevronDown
          className={`h-4 w-4 text-muted-foreground shrink-0 transition-transform duration-200 ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>

      <div
        className={`grid transition-[grid-template-rows] duration-200 ease-out ${
          open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
        }`}
      >
        <div className="overflow-hidden">
          <ul className="px-4 pb-4 space-y-2 border-t border-border/60 pt-3">
            {steps.length === 0 ? (
              <li className="text-xs text-muted-foreground">No steps yet.</li>
            ) : (
              steps.map((step) => (
                <li
                  key={step.id}
                  className="flex items-start gap-2.5 text-sm animate-in fade-in duration-300"
                >
                  <span className="mt-0.5 shrink-0">
                    <StepIcon status={step.status} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span
                        className={
                          step.status === "running"
                            ? "font-medium text-foreground"
                            : "text-foreground"
                        }
                      >
                        {step.label}
                      </span>
                      {step.kind && step.kind !== "step" && (
                        <span className="text-[10px] uppercase tracking-wider text-muted-foreground border border-border rounded px-1.5 py-0.5">
                          {step.kind}
                        </span>
                      )}
                    </div>
                    {step.detail && (
                      <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
                        {step.detail}
                      </p>
                    )}
                  </div>
                </li>
              ))
            )}
          </ul>
        </div>
      </div>
    </div>
  );
}
