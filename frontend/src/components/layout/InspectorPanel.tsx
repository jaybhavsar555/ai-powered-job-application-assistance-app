"use client";

import React from "react";
import { Info, GitCommit, FileCode2, Clock, DollarSign, Zap } from "lucide-react";
import { useWorkflowStore } from "@/hooks/useWorkflowStore";

export function InspectorPanel() {
  const { activeNode, nodeTelemetry } = useWorkflowStore();
  
  const telemetry = activeNode ? nodeTelemetry[activeNode] : null;

  if (!activeNode) {
    return (
      <aside className="w-80 bg-card border-l border-border hidden xl:flex flex-col">
        <div className="h-14 border-b border-border flex items-center px-4 bg-muted/20">
          <h3 className="font-semibold text-sm">Node Inspector</h3>
        </div>
        <div className="flex-1 p-4 flex items-center justify-center text-muted-foreground text-sm">
          Select a node or start workflow...
        </div>
      </aside>
    );
  }

  // Format evidence if exists
  const evidenceKey = telemetry?.evidence ? Object.keys(telemetry.evidence)[0] : null;
  const evidenceValue = evidenceKey ? JSON.stringify(telemetry.evidence[evidenceKey]).substring(0, 100) : null;

  return (
    <aside className="w-80 bg-card border-l border-border hidden xl:flex flex-col">
      <div className="h-14 border-b border-border flex items-center px-4 bg-muted/20">
        <h3 className="font-semibold text-sm">Node Inspector</h3>
      </div>
      
      <div className="flex-1 overflow-auto p-4 space-y-6">
        {/* Active Node Info */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-primary font-medium text-sm">
            <Info className="h-4 w-4" />
            <span>{activeNode}</span>
          </div>
        </div>

        {/* Telemetry Data */}
        <div className="space-y-3 pt-4 border-t border-border">
          <h4 className="text-xs font-semibold uppercase text-muted-foreground tracking-wider">Telemetry</h4>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-muted/50 p-2.5 rounded-lg border border-border/50">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
                <Clock className="h-3 w-3" /> Latency
              </div>
              <span className="text-sm font-medium">{telemetry?.latency_ms ? `${(telemetry.latency_ms / 1000).toFixed(2)}s` : '--'}</span>
            </div>
            <div className="bg-muted/50 p-2.5 rounded-lg border border-border/50">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
                <DollarSign className="h-3 w-3" /> Cost
              </div>
              <span className="text-sm font-medium">{telemetry?.cost ? `$${telemetry.cost.toFixed(4)}` : '--'}</span>
            </div>
            <div className="bg-muted/50 p-2.5 rounded-lg border border-border/50">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
                <FileCode2 className="h-3 w-3" /> Tokens
              </div>
              <span className="text-sm font-medium">{telemetry?.tokens ? `${telemetry.tokens} tkns` : '--'}</span>
            </div>
          </div>
        </div>

        {/* Evidence Panel */}
        {evidenceKey && (
          <div className="space-y-3 pt-4 border-t border-border">
            <h4 className="text-xs font-semibold uppercase text-muted-foreground tracking-wider">Evidence</h4>
            <div className="bg-primary/5 border border-primary/20 rounded-lg p-3">
              <div className="flex items-start gap-2">
                <GitCommit className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                <div className="space-y-1">
                  <p className="text-xs font-medium text-foreground capitalize">{evidenceKey.replace(/_/g, ' ')}</p>
                  <p className="text-[11px] text-muted-foreground break-words">{evidenceValue}...</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
