"use client";

import React from "react";
import { FileText, Terminal, Wand2 } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { WorkspaceNav } from "./WorkspaceNav";
import { InspectorPanel } from "./InspectorPanel";
import { TerminalLog } from "./TerminalLog";
import { useTerminalStore } from "@/store/terminal";

export function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  const { open, toggleTerminal } = useTerminalStore();
  const pathname = usePathname();

  return (
    <div className="flex h-screen w-full bg-background overflow-hidden text-foreground">
      <WorkspaceNav />

      <div className="flex flex-col flex-1 min-w-0 border-l border-r border-border">
        <header className="flex h-14 items-center justify-between border-b border-border bg-muted/20 px-4 gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <Link
              href="/tailor"
              className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium border transition-colors ${
                pathname.startsWith("/tailor")
                  ? "border-primary/40 bg-primary/10 text-foreground"
                  : "border-border text-muted-foreground hover:text-foreground hover:bg-muted"
              }`}
            >
              <Wand2 className="h-3.5 w-3.5" />
              Tailor JD
            </Link>
            <Link
              href="/resumes"
              className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium border transition-colors ${
                pathname.startsWith("/resumes")
                  ? "border-primary/40 bg-primary/10 text-foreground"
                  : "border-border text-muted-foreground hover:text-foreground hover:bg-muted"
              }`}
            >
              <FileText className="h-3.5 w-3.5" />
              Resume Studio
            </Link>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={toggleTerminal}
              className={`flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-md border transition-colors ${
                open
                  ? "border-primary/40 bg-primary/10 text-foreground"
                  : "border-border text-muted-foreground hover:text-foreground hover:bg-muted"
              }`}
              title="Toggle live logs (Ctrl+`)"
              aria-pressed={open}
              aria-label="Toggle live agent execution logs"
            >
              <Terminal className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Logs</span>
            </button>
            <div className="h-6 w-6 rounded-full bg-blue-500/20 border border-blue-500/50 flex items-center justify-center text-xs text-blue-400">
              JS
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-auto relative flex flex-col min-h-0 os-scrollbar os-scrollbar-auto">
          {children}
        </main>

        <TerminalLog />
      </div>

      <InspectorPanel />
    </div>
  );
}
