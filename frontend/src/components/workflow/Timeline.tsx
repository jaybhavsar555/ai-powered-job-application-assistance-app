"use client";

import { useMemo } from "react";
import { useWorkflowStore, type WorkflowEvent } from "@/hooks/useWorkflowStore";
import { ThinkingTrace, type ThinkingStep } from "@/components/ui/ThinkingTrace";
import { ToolChipRow, type ToolChipProps } from "@/components/ui/ToolChip";
import { Loader2 } from "lucide-react";

function eventLabel(evt: WorkflowEvent): string {
  return String(evt.node || evt.agent || evt.type || "Agent");
}

function eventToStepStatus(evt: WorkflowEvent): ThinkingStep["status"] {
  const t = (evt.type || "").toUpperCase();
  if (t.includes("ERROR") || t.includes("FAIL")) return "error";
  if (t.includes("SUCCESS") || t.includes("COMPLETED") || t.includes("END")) {
    return "success";
  }
  if (t.includes("START") || t.includes("RUNNING")) return "running";
  return "success";
}

function buildSteps(
  events: WorkflowEvent[],
  workflowStatus: string,
  activeNode: string | null
): ThinkingStep[] {
  const byNode = new Map<string, ThinkingStep>();

  for (const evt of events) {
    const label = eventLabel(evt);
    const id = label;
    const prev = byNode.get(id);
    const status = eventToStepStatus(evt);
    const detailParts: string[] = [];
    if (evt.message) detailParts.push(String(evt.message));
    if (typeof evt.latency_ms === "number") {
      detailParts.push(`${Math.round(evt.latency_ms)}ms`);
    }
    if (typeof evt.tokens === "number") {
      detailParts.push(`${evt.tokens} tok`);
    }
    byNode.set(id, {
      id,
      label,
      status:
        status === "running" || !prev
          ? status
          : status === "error"
            ? "error"
            : prev.status === "error"
              ? "error"
              : status,
      detail: detailParts.join(" · ") || prev?.detail,
      kind: "step",
    });
  }

  if (workflowStatus === "running" && activeNode) {
    const existing = byNode.get(activeNode);
    byNode.set(activeNode, {
      id: activeNode,
      label: activeNode,
      status: "running",
      detail: existing?.detail || "Running…",
      kind: "step",
    });
  }

  return Array.from(byNode.values());
}

function buildChips(
  events: WorkflowEvent[],
  nodeTelemetry: Record<string, { status: string; latency_ms?: number; tokens?: number }>
): ToolChipProps[] {
  const seen = new Set<string>();
  const chips: ToolChipProps[] = [];

  for (const evt of events) {
    const label = eventLabel(evt);
    if (seen.has(label)) continue;
    seen.add(label);
    const tel = nodeTelemetry[label];
    const t = (evt.type || "").toUpperCase();
    let status: ToolChipProps["status"] = "done";
    if (t.includes("ERROR")) status = "error";
    else if (t.includes("START") && !t.includes("SUCCESS")) status = "running";
    if (tel?.status === "running") status = "running";
    if (tel?.status === "error") status = "error";
    if (tel?.status === "success") status = "done";

    const metaParts: string[] = [];
    const latency = tel?.latency_ms ?? evt.latency_ms;
    const tokens = tel?.tokens ?? evt.tokens;
    if (typeof latency === "number") metaParts.push(`${Math.round(latency)}ms`);
    if (typeof tokens === "number") metaParts.push(`${tokens}t`);

    chips.push({
      label,
      status,
      kind: "agent",
      meta: metaParts.join(" ") || undefined,
    });
  }

  return chips;
}

export function Timeline() {
  const {
    events,
    workflowStatus: status,
    activeNode,
    nodeTelemetry,
  } = useWorkflowStore();

  const steps = useMemo(
    () => buildSteps(events, status, activeNode),
    [events, status, activeNode]
  );

  const chips = useMemo(
    () => buildChips(events, nodeTelemetry),
    [events, nodeTelemetry]
  );

  const title =
    status === "running"
      ? "Thinking"
      : status === "completed"
        ? "Run complete — awaiting approval"
        : status === "error"
          ? "Run failed"
          : "Execution timeline";

  return (
    <div className="flex flex-col gap-3 h-full min-h-[320px]">
      <div className="flex items-center justify-between gap-2 px-0.5">
        <h3 className="font-semibold text-lg flex items-center gap-2">
          Agent trace
          {status === "running" && (
            <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
          )}
        </h3>
        <span className="text-[11px] text-muted-foreground uppercase tracking-wider">
          {status}
        </span>
      </div>

      <ThinkingTrace
        title={title}
        steps={steps}
        defaultOpen
        className="flex-1 min-h-[200px] overflow-y-auto os-scrollbar os-scrollbar-auto"
      />

      <ToolChipRow
        chips={chips}
        summary={
          chips.length
            ? `${chips.length} agent call${chips.length === 1 ? "" : "s"}`
            : undefined
        }
      />

      {events.length === 0 && status === "idle" && (
        <p className="text-sm text-muted-foreground px-1">
          Select a job and run Simulate to see expandable thinking steps and tool
          chips.
        </p>
      )}
    </div>
  );
}
