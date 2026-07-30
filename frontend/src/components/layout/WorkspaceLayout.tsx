import React from "react";
import { WorkspaceNav } from "./WorkspaceNav";
import { InspectorPanel } from "./InspectorPanel";
import { TerminalLog } from "./TerminalLog";

export function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen w-full bg-background overflow-hidden text-foreground">
      {/* Left Sidebar (Nav) */}
      <WorkspaceNav />

      {/* Main Center Area */}
      <div className="flex flex-col flex-1 min-w-0 border-l border-r border-border">
        {/* Top Header */}
        <header className="flex h-14 items-center justify-between border-b border-border bg-muted/20 px-4">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm">Application #9021</span>
            <span className="text-muted-foreground text-xs bg-muted px-2 py-0.5 rounded">Active</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="h-6 w-6 rounded-full bg-blue-500/20 border border-blue-500/50 flex items-center justify-center text-xs text-blue-400">
              JS
            </div>
          </div>
        </header>

        {/* Center Canvas / Main Content */}
        <main className="flex-1 overflow-auto relative flex flex-col min-h-0">
          {children}
        </main>

        {/* Bottom Terminal (Collapsible) */}
        <TerminalLog />
      </div>

      {/* Right Inspector Panel */}
      <InspectorPanel />
    </div>
  );
}
