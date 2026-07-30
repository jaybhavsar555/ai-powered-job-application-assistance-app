import React from "react";
import { Terminal, Maximize2, X } from "lucide-react";

export function TerminalLog() {
  return (
    <div className="h-48 border-t border-border bg-card/50 flex flex-col">
      {/* Terminal Header */}
      <div className="flex items-center justify-between px-4 py-1.5 border-b border-border bg-muted/30">
        <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
          <Terminal className="h-3.5 w-3.5" />
          Live Agent Execution Logs
        </div>
        <div className="flex items-center gap-2">
          <button className="p-1 hover:bg-muted rounded text-muted-foreground">
            <Maximize2 className="h-3.5 w-3.5" />
          </button>
          <button className="p-1 hover:bg-muted rounded text-muted-foreground">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Terminal Body */}
      <div className="flex-1 overflow-auto p-4 font-mono text-[11px] leading-relaxed text-muted-foreground space-y-1">
        <div className="flex gap-4">
          <span className="text-blue-400">12:04:01</span>
          <span className="text-purple-400">[System]</span>
          <span className="text-foreground">Initializing Workflow Engine...</span>
        </div>
        <div className="flex gap-4">
          <span className="text-blue-400">12:04:02</span>
          <span className="text-green-400">[JobIntakeAgent]</span>
          <span className="text-foreground">Extracting DOM from https://example.com/job...</span>
        </div>
        <div className="flex gap-4">
          <span className="text-blue-400">12:04:05</span>
          <span className="text-green-400">[JobIntakeAgent]</span>
          <span className="text-muted-foreground">Extraction complete. Yielding Structured JSON.</span>
        </div>
        <div className="flex gap-4 opacity-50">
          <span className="text-blue-400">12:04:06</span>
          <span className="text-yellow-400">[ATSAnalyzer]</span>
          <span className="animate-pulse">Waiting for input context...</span>
        </div>
      </div>
    </div>
  );
}
