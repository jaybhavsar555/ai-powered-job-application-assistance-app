"use client";

import { useCallback, useEffect, useState } from "react";
import { Cpu, Cloud, Zap, Loader2 } from "lucide-react";
import api, { getApiErrorMessage } from "@/lib/api";

type Provider = "openai" | "ollama" | "mock";

type LlmStatus = {
  provider: Provider;
  model: string;
  force_mock: boolean;
  openai_configured: boolean;
  openai_model_default: string;
  ollama_model_default: string;
  ollama_base_url: string;
  message?: string;
};

const OPTIONS: {
  id: Provider;
  label: string;
  icon: typeof Cloud;
  hint: string;
}[] = [
  { id: "openai", label: "OpenAI", icon: Cloud, hint: "Cloud — fast" },
  { id: "ollama", label: "Ollama", icon: Cpu, hint: "Local — warms model on switch" },
  { id: "mock", label: "Mock", icon: Zap, hint: "Instant demo" },
];

export function LlmProviderSwitch() {
  const [status, setStatus] = useState<LlmStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get<LlmStatus>("/llm/provider");
      setStatus(data);
      setError(null);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Could not load LLM provider"));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const select = async (provider: Provider) => {
    if (busy || status?.provider === provider) return;
    if (provider === "openai" && status && !status.openai_configured) {
      setError("Set OPENAI_API_KEY in backend/.env first");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const { data } = await api.put<LlmStatus>("/llm/provider", { provider });
      setStatus(data);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Failed to switch LLM provider"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col items-end gap-1 min-w-0">
      <div className="inline-flex items-center rounded-lg border border-border bg-card p-0.5 gap-0.5">
        {OPTIONS.map(({ id, label, icon: Icon, hint }) => {
          const active = status?.provider === id;
          return (
            <button
              key={id}
              type="button"
              title={hint}
              disabled={busy || !status}
              onClick={() => select(id)}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors disabled:opacity-50 ${
                active
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              }`}
            >
              {busy && active ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Icon className="h-3.5 w-3.5" />
              )}
              {label}
            </button>
          );
        })}
      </div>
      <p className="text-[10px] text-muted-foreground truncate max-w-[280px]">
        {error ? (
          <span className="text-red-400">{error}</span>
        ) : status ? (
          <>
            Active: <span className="text-foreground">{status.provider}</span> ·{" "}
            {status.model}
          </>
        ) : (
          "Loading LLM…"
        )}
      </p>
    </div>
  );
}
