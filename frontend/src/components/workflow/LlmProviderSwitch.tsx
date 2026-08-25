"use client";

import { useCallback, useEffect, useState } from "react";
import { Cpu, Cloud, Loader2, Ship } from "lucide-react";
import api, { getApiErrorMessage } from "@/lib/api";

type Provider = "openai" | "tokenharbor" | "ollama" | "mock";

type LlmStatus = {
  provider: Provider;
  model: string;
  force_mock: boolean;
  mock_allowed?: boolean;
  openai_configured: boolean;
  tokenharbor_configured?: boolean;
  openai_model_default: string;
  tokenharbor_model_default?: string;
  ollama_model_default: string;
  ollama_base_url: string;
  message?: string;
};

type ModelPreset = {
  provider: Provider;
  model: string;
  label: string;
  notes?: string;
  pull?: string | null;
};

const OPTIONS: {
  id: Provider;
  label: string;
  icon: typeof Cloud;
  hint: string;
}[] = [
  {
    id: "tokenharbor",
    label: "Token Harbor",
    icon: Ship,
    hint: "Kimi / DeepSeek free via one key — best easy upgrade",
  },
  { id: "openai", label: "OpenAI", icon: Cloud, hint: "Direct OpenAI — needs billing" },
  { id: "ollama", label: "Ollama", icon: Cpu, hint: "Local open models — free, private" },
];

export function LlmProviderSwitch() {
  const [status, setStatus] = useState<LlmStatus | null>(null);
  const [presets, setPresets] = useState<ModelPreset[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [{ data }, presetsRes] = await Promise.all([
        api.get<LlmStatus>("/llm/provider"),
        api.get<{ presets: ModelPreset[] }>("/llm/model-presets").catch(() => ({
          data: { presets: [] },
        })),
      ]);
      setStatus(data);
      setPresets(presetsRes.data.presets || []);
      setError(null);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Could not load LLM provider"));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const apply = async (provider: Provider, model?: string) => {
    if (busy) return;
    if (provider === "openai" && status && !status.openai_configured) {
      setError("Set OPENAI_API_KEY in backend/.env first");
      return;
    }
    if (provider === "tokenharbor" && status && !status.tokenharbor_configured) {
      setError("Set TOKENHARBOR_API_KEY in backend/.env for Kimi / DeepSeek free");
      return;
    }
    if (provider === "mock") {
      setError(
        "Mock LLM is disabled — fake agent output hides real failures. Use Token Harbor, Ollama, or OpenAI."
      );
      return;
    }
    if (
      status?.provider === provider &&
      (!model || status.model === model)
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const { data } = await api.put<LlmStatus>("/llm/provider", {
        provider,
        ...(model ? { model } : {}),
      });
      setStatus(data);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Failed to switch LLM provider"));
    } finally {
      setBusy(false);
    }
  };

  const relevantPresets = presets.filter((p) => {
    if (!status) return false;
    if (status.provider === "ollama") return p.provider === "ollama";
    if (status.provider === "tokenharbor") return p.provider === "tokenharbor";
    return false;
  });

  return (
    <div className="flex flex-col items-end gap-1.5 min-w-0">
      <div className="inline-flex items-center rounded-lg border border-border bg-card p-0.5 gap-0.5">
        {OPTIONS.map(({ id, label, icon: Icon, hint }) => {
          const active = status?.provider === id;
          return (
            <button
              key={id}
              type="button"
              title={hint}
              disabled={busy || !status}
              onClick={() => apply(id)}
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

      {relevantPresets.length > 0 && (
        <select
          aria-label="Model preset"
          disabled={busy || !status}
          value={status?.model || ""}
          onChange={(e) => {
            const preset = relevantPresets.find((p) => p.model === e.target.value);
            if (preset) void apply(preset.provider, preset.model);
          }}
          className="max-w-[280px] text-[11px] rounded-md border border-border bg-background px-2 py-1 text-muted-foreground"
        >
          {!relevantPresets.some((p) => p.model === status?.model) && status?.model && (
            <option value={status.model}>{status.model} (current)</option>
          )}
          {relevantPresets.map((p) => (
            <option key={`${p.provider}-${p.model}`} value={p.model} title={p.notes}>
              {p.label}
            </option>
          ))}
        </select>
      )}

      <p className="text-[10px] text-muted-foreground truncate max-w-[320px]">
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
