"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  Info,
  GitCommit,
  FileCode2,
  Clock,
  DollarSign,
  Zap,
  Save,
  Bot,
  Loader2,
} from "lucide-react";
import { useWorkflowStore } from "@/hooks/useWorkflowStore";
import api, { getApiErrorMessage } from "@/lib/api";

type AgentInfo = {
  name: string;
  label: string;
  description: string;
  capabilities: string[];
  system_prompt: string | null;
  configurable: boolean;
  role: string;
};

function findTelemetry(
  nodeTelemetry: Record<string, { latency_ms?: number; tokens?: number; cost?: number; evidence?: unknown; status: string }>,
  agentName: string | null
) {
  if (!agentName) return null;
  const norm = (s: string) => s.toLowerCase().replace(/[\s_]+/g, "");
  const target = norm(agentName);
  const direct = nodeTelemetry[agentName];
  if (direct) return direct;
  const hit = Object.entries(nodeTelemetry).find(([k]) => {
    const n = norm(k);
    return n === target || n.includes(target) || target.includes(n);
  });
  return hit?.[1] ?? null;
}

export function InspectorPanel() {
  const { activeNode, selectedNode, nodeTelemetry } = useWorkflowStore();
  const focusNode = selectedNode || activeNode;

  const [agent, setAgent] = useState<AgentInfo | null>(null);
  const [promptDraft, setPromptDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const telemetry = findTelemetry(nodeTelemetry, focusNode);

  useEffect(() => {
    if (!focusNode) {
      setAgent(null);
      setPromptDraft("");
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      setMessage(null);
      try {
        const { data } = await api.get<AgentInfo>(`/agents/${focusNode}`);
        if (cancelled) return;
        setAgent(data);
        setPromptDraft(data.system_prompt || "");
      } catch (err: unknown) {
        if (!cancelled) {
          setAgent(null);
          setError(getApiErrorMessage(err, "Could not load agent"));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [focusNode]);

  const evidencePretty = useMemo(() => {
    if (!telemetry?.evidence) return null;
    try {
      return JSON.stringify(telemetry.evidence, null, 2);
    } catch {
      return String(telemetry.evidence);
    }
  }, [telemetry?.evidence]);

  const savePrompt = async () => {
    if (!agent?.configurable || !focusNode) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const { data } = await api.put<{ system_prompt: string; persisted: boolean }>(
        `/agents/${focusNode}/prompt`,
        { system_prompt: promptDraft, persist: true }
      );
      setPromptDraft(data.system_prompt);
      setMessage(data.persisted ? "Prompt saved to YAML (next runs use it)." : "Prompt updated in memory.");
      setAgent((a) => (a ? { ...a, system_prompt: data.system_prompt } : a));
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Failed to save prompt"));
    } finally {
      setSaving(false);
    }
  };

  if (!focusNode) {
    return (
      <aside className="w-80 bg-card border-l border-border hidden xl:flex flex-col">
        <div className="h-14 border-b border-border flex items-center px-4 bg-muted/20">
          <h3 className="font-semibold text-sm">Node Inspector</h3>
        </div>
        <div className="flex-1 p-4 flex flex-col items-center justify-center text-center text-muted-foreground text-sm gap-2">
          <Bot className="w-8 h-8 opacity-40" />
          <p>Click a canvas agent to inspect what it does and edit its system prompt.</p>
        </div>
      </aside>
    );
  }

  return (
    <aside className="w-80 bg-card border-l border-border hidden xl:flex flex-col min-h-0">
      <div className="h-14 border-b border-border flex items-center justify-between px-4 bg-muted/20 shrink-0">
        <h3 className="font-semibold text-sm">Node Inspector</h3>
        {activeNode === focusNode && (
          <span className="text-[10px] uppercase tracking-wide text-primary font-medium">Running</span>
        )}
      </div>

      <div className="flex-1 overflow-auto p-4 space-y-5 os-scrollbar">
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading agent…
          </div>
        ) : (
          <>
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-primary font-medium text-sm">
                <Info className="h-4 w-4 shrink-0" />
                <span>{agent?.label || focusNode}</span>
              </div>
              <p className="text-[11px] text-muted-foreground font-mono">{focusNode}</p>
              {agent?.description && (
                <p className="text-xs text-muted-foreground leading-relaxed">{agent.description}</p>
              )}
              {agent?.capabilities?.length ? (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {agent.capabilities.map((c) => (
                    <span
                      key={c}
                      className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground border border-border"
                    >
                      {c}
                    </span>
                  ))}
                </div>
              ) : null}
            </div>

            <div className="space-y-3 pt-4 border-t border-border">
              <h4 className="text-xs font-semibold uppercase text-muted-foreground tracking-wider flex items-center gap-1.5">
                <Zap className="w-3 h-3" /> Last run telemetry
              </h4>
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-muted/50 p-2.5 rounded-lg border border-border/50">
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
                    <Clock className="h-3 w-3" /> Latency
                  </div>
                  <span className="text-sm font-medium">
                    {telemetry?.latency_ms != null ? `${(telemetry.latency_ms / 1000).toFixed(2)}s` : "—"}
                  </span>
                </div>
                <div className="bg-muted/50 p-2.5 rounded-lg border border-border/50">
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
                    <DollarSign className="h-3 w-3" /> Cost
                  </div>
                  <span className="text-sm font-medium">
                    {telemetry?.cost != null ? `$${telemetry.cost.toFixed(4)}` : "—"}
                  </span>
                </div>
                <div className="bg-muted/50 p-2.5 rounded-lg border border-border/50 col-span-2">
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
                    <FileCode2 className="h-3 w-3" /> Tokens / status
                  </div>
                  <span className="text-sm font-medium">
                    {telemetry?.tokens != null ? `${telemetry.tokens} tkns` : "—"}
                    {telemetry?.status ? ` · ${telemetry.status}` : ""}
                  </span>
                </div>
              </div>
            </div>

            {evidencePretty && (
              <div className="space-y-2 pt-4 border-t border-border">
                <h4 className="text-xs font-semibold uppercase text-muted-foreground tracking-wider flex items-center gap-1.5">
                  <GitCommit className="w-3 h-3" /> Evidence (last output)
                </h4>
                <pre className="text-[10px] leading-relaxed bg-muted/40 border border-border rounded-lg p-2.5 overflow-auto max-h-40 whitespace-pre-wrap break-words font-mono text-muted-foreground">
                  {evidencePretty}
                </pre>
              </div>
            )}

            {agent?.configurable && (
              <div className="space-y-2 pt-4 border-t border-border">
                <div className="flex items-center justify-between gap-2">
                  <h4 className="text-xs font-semibold uppercase text-muted-foreground tracking-wider">
                    System prompt
                  </h4>
                  <button
                    type="button"
                    onClick={savePrompt}
                    disabled={saving || promptDraft === (agent.system_prompt || "")}
                    className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-md bg-primary text-primary-foreground disabled:opacity-40"
                  >
                    {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                    Save
                  </button>
                </div>
                <textarea
                  value={promptDraft}
                  onChange={(e) => setPromptDraft(e.target.value)}
                  rows={10}
                  className="w-full text-[11px] leading-relaxed font-mono rounded-lg border border-border bg-background px-2.5 py-2 outline-none focus:ring-1 focus:ring-primary resize-y min-h-[140px]"
                  spellCheck={false}
                />
                <p className="text-[10px] text-muted-foreground">
                  Edits persist to <code className="text-[10px]">backend/app/core/prompts/{focusNode}.yaml</code>
                </p>
              </div>
            )}

            {agent && !agent.configurable && (
              <div className="pt-4 border-t border-border text-xs text-muted-foreground leading-relaxed">
                This step is UI/DB only — review drafts on <span className="text-foreground">/approvals</span>.
              </div>
            )}

            {message && <p className="text-[11px] text-emerald-400">{message}</p>}
            {error && <p className="text-[11px] text-red-400">{error}</p>}
          </>
        )}
      </div>
    </aside>
  );
}
