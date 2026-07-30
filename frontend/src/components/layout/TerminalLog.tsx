"use client";

import { useEffect, useMemo, useRef } from "react";
import {
  Terminal,
  Maximize2,
  Minimize2,
  Trash2,
  X,
  ChevronUp,
  ChevronsUpDown,
  PanelBottomOpen,
} from "lucide-react";
import { useWorkflowStore, type WorkflowEvent } from "@/hooks/useWorkflowStore";
import { useTerminalStore, type TerminalSize } from "@/store/terminal";

function formatTime(iso?: string) {
  try {
    return new Date(iso || Date.now()).toLocaleTimeString();
  } catch {
    return "--:--:--";
  }
}

function agentColor(type: string) {
  if (type === "AGENT_STARTED") return "text-sky-400";
  if (type === "AGENT_SUCCESS") return "text-emerald-400";
  if (type === "AGENT_ERROR" || type === "ERROR") return "text-red-400";
  if (type === "COMPLETED") return "text-violet-400";
  return "text-purple-400";
}

function describeEvent(evt: Record<string, unknown>): string {
  const type = String(evt.type || "EVENT");
  const node = String(evt.node || evt.agent || "System");

  if (type === "SYSTEM" && typeof evt.message === "string") {
    return evt.message;
  }
  if (type === "AGENT_STARTED") {
    return `Starting ${node}…`;
  }
  if (type === "AGENT_SUCCESS") {
    const latency = evt.latency_ms != null ? `${evt.latency_ms}ms` : "—";
    const tokens = evt.tokens != null ? `${evt.tokens} tkns` : "—";
    const cost = typeof evt.cost === "number" ? `$${evt.cost.toFixed(4)}` : "—";
    return `Completed · latency ${latency} · ${tokens} · cost ${cost}`;
  }
  if (type === "AGENT_ERROR" || type === "ERROR") {
    return `Error: ${evt.error || evt.message || "unknown failure"}`;
  }
  if (type === "COMPLETED") {
    return "Workflow completed. Review outputs in Approvals.";
  }
  if (typeof evt.message === "string") return evt.message;
  return JSON.stringify(evt);
}

function sizeClass(size: TerminalSize): string {
  switch (size) {
    case "compact":
      return "h-32";
    case "tall":
      return "h-80";
    case "maximized":
      return "h-[min(70vh,560px)]";
    default:
      return "h-48";
  }
}

function statusDot(workflowStatus: string) {
  if (workflowStatus === "running") return "bg-emerald-400 animate-pulse";
  if (workflowStatus === "error") return "bg-red-400";
  if (workflowStatus === "completed") return "bg-violet-400";
  return "bg-muted-foreground/40";
}

export function TerminalLog() {
  const { events, workflowStatus, reset } = useWorkflowStore();
  const { open, size, openTerminal, closeTerminal, cycleSize, setSize } =
    useTerminalStore();
  const bottomRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const lines = useMemo((): WorkflowEvent[] => {
    if (events.length === 0) {
      return [
        {
          type: "SYSTEM",
          node: "System",
          timestamp: new Date().toISOString(),
          message:
            'Workflow engine ready. Click “Simulate Application Flow” on Canvas to stream live logs.',
        },
      ];
    }
    return events.map((evt) => ({
      ...evt,
      message: describeEvent(evt as Record<string, unknown>),
    }));
  }, [events]);

  // Auto-open when a workflow starts so users don't miss live output
  useEffect(() => {
    if (workflowStatus === "running" && !open) {
      openTerminal();
    }
  }, [workflowStatus, open, openTerminal]);

  // Autoscroll to latest line
  useEffect(() => {
    if (!open) return;
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines.length, open, size]);

  // Keyboard: Ctrl/Cmd + ` toggles panel; Escape closes when focused in panel
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const isToggle =
        (e.ctrlKey || e.metaKey) && (e.key === "`" || e.code === "Backquote");
      if (isToggle) {
        e.preventDefault();
        useTerminalStore.getState().toggleTerminal();
        return;
      }
      if (e.key === "Escape" && open) {
        const active = document.activeElement;
        if (panelRef.current?.contains(active) || active === document.body) {
          closeTerminal();
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, closeTerminal]);

  // Closed: slim reopen strip
  if (!open) {
    return (
      <div className="shrink-0 border-t border-border bg-card/80 backdrop-blur-sm">
        <button
          type="button"
          onClick={openTerminal}
          className="w-full flex items-center justify-between gap-3 px-4 py-2 text-xs text-muted-foreground hover:text-foreground hover:bg-muted/40 transition-colors"
          title="Open live logs (Ctrl+`)"
          aria-label="Open live agent execution logs"
        >
          <span className="flex items-center gap-2 font-medium">
            <PanelBottomOpen className="h-3.5 w-3.5" />
            Live Agent Execution Logs
            <span className={`h-1.5 w-1.5 rounded-full ${statusDot(workflowStatus)}`} />
            <span className="uppercase tracking-wider text-[10px] tabular-nums">
              {workflowStatus}
            </span>
            {events.length > 0 && (
              <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded tabular-nums">
                {events.length} events
              </span>
            )}
          </span>
          <span className="flex items-center gap-1 text-[10px] uppercase tracking-wider">
            Open
            <ChevronUp className="h-3.5 w-3.5" />
          </span>
        </button>
      </div>
    );
  }

  return (
    <div
      ref={panelRef}
      role="log"
      aria-live="polite"
      aria-label="Live agent execution logs"
      className={`${sizeClass(size)} border-t border-border bg-[#0c0c0f] flex flex-col shrink-0 transition-[height] duration-200 ease-out`}
    >
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-border bg-muted/30 gap-2">
        <button
          type="button"
          onClick={closeTerminal}
          className="flex items-center gap-2 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors min-w-0"
          title="Collapse to strip (Esc or Ctrl+`)"
        >
          <Terminal className="h-3.5 w-3.5 shrink-0" />
          <span className="truncate">Live Agent Execution Logs</span>
          <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${statusDot(workflowStatus)}`} />
          <span className="text-[10px] uppercase tracking-wider tabular-nums shrink-0">
            {workflowStatus}
          </span>
        </button>

        <div className="flex items-center gap-0.5 shrink-0">
          <div className="hidden sm:flex items-center mr-1 rounded-md border border-border overflow-hidden">
            {(["compact", "default", "tall", "maximized"] as TerminalSize[]).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setSize(s)}
                className={`px-2 py-1 text-[10px] capitalize transition-colors ${
                  size === s
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                }`}
                title={`Size: ${s}`}
              >
                {s === "default" ? "md" : s.slice(0, 3)}
              </button>
            ))}
          </div>

          <button
            type="button"
            title="Clear logs"
            onClick={() => reset()}
            className="p-1.5 hover:bg-muted rounded text-muted-foreground hover:text-foreground transition-colors"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>

          <button
            type="button"
            title="Cycle panel size"
            onClick={cycleSize}
            className="p-1.5 hover:bg-muted rounded text-muted-foreground hover:text-foreground transition-colors sm:hidden"
          >
            <ChevronsUpDown className="h-3.5 w-3.5" />
          </button>

          <button
            type="button"
            title={size === "maximized" ? "Restore default size" : "Maximize"}
            onClick={() =>
              setSize(size === "maximized" ? "default" : "maximized")
            }
            className="p-1.5 hover:bg-muted rounded text-muted-foreground hover:text-foreground transition-colors"
          >
            {size === "maximized" ? (
              <Minimize2 className="h-3.5 w-3.5" />
            ) : (
              <Maximize2 className="h-3.5 w-3.5" />
            )}
          </button>

          <button
            type="button"
            title="Close panel (Esc)"
            onClick={closeTerminal}
            className="p-1.5 hover:bg-muted rounded text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-3 font-mono text-[11px] leading-relaxed space-y-1 os-scrollbar os-scrollbar-auto">
        {lines.map((line, idx) => {
          const type = String(line.type || "SYSTEM");
          const node = String(line.node || line.agent || "System");
          const waiting =
            workflowStatus === "running" &&
            idx === lines.length - 1 &&
            type === "AGENT_STARTED";

          return (
            <div
              key={`${line.timestamp}-${idx}`}
              className={`flex gap-3 ${waiting ? "opacity-80" : ""}`}
            >
              <span className="text-blue-400/90 shrink-0 tabular-nums w-[72px]">
                {formatTime(line.timestamp)}
              </span>
              <span className={`shrink-0 ${agentColor(type)}`}>[{node}]</span>
              <span
                className={`text-foreground/90 break-all ${waiting ? "animate-pulse" : ""}`}
              >
                {line.message}
                {waiting ? " ▍" : ""}
              </span>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      <div className="hidden sm:flex items-center justify-between px-3 py-0.5 border-t border-border/50 text-[10px] text-muted-foreground/70">
        <span>Ctrl+` toggle · Esc close</span>
        <span className="capitalize">{size}</span>
      </div>
    </div>
  );
}
