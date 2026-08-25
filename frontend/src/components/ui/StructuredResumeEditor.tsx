"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2, Save, RotateCcw } from "lucide-react";
import type { StructuredResumeData } from "@/types/resume";

export type { StructuredResumeData };

interface StructuredResumeEditorProps {
  value: StructuredResumeData;
  onChange: (next: StructuredResumeData) => void;
  onSave?: (data: StructuredResumeData) => void | Promise<void>;
  onRescore?: (data: StructuredResumeData) => void | Promise<void>;
  disabled?: boolean;
  saving?: boolean;
  rescoreLabel?: string;
}

export function StructuredResumeEditor({
  value,
  onChange,
  onSave,
  onRescore,
  disabled = false,
  saving = false,
  rescoreLabel = "Re-score ATS",
}: StructuredResumeEditorProps) {
  const [summary, setSummary] = useState(value.summary || "");
  const [bullets, setBullets] = useState<string[]>(value.tailored_bullets || []);
  const [keywords, setKeywords] = useState<string[]>(value.added_keywords || []);
  const [keywordInput, setKeywordInput] = useState("");

  useEffect(() => {
    setSummary(value.summary || "");
    setBullets(value.tailored_bullets || []);
    setKeywords(value.added_keywords || []);
  }, [value]);

  const emit = (patch: Partial<StructuredResumeData>) => {
    const next: StructuredResumeData = {
      summary,
      tailored_bullets: bullets,
      added_keywords: keywords,
      ...patch,
    };
    onChange(next);
  };

  const updateBullet = (idx: number, text: string) => {
    const next = [...bullets];
    next[idx] = text;
    setBullets(next);
    emit({ tailored_bullets: next });
  };

  const addBullet = () => {
    const next = [...bullets, ""];
    setBullets(next);
    emit({ tailored_bullets: next });
  };

  const removeBullet = (idx: number) => {
    const next = bullets.filter((_, i) => i !== idx);
    setBullets(next);
    emit({ tailored_bullets: next });
  };

  const addKeyword = () => {
    const token = keywordInput.trim();
    if (!token || keywords.includes(token)) return;
    const next = [...keywords, token];
    setKeywords(next);
    setKeywordInput("");
    emit({ added_keywords: next });
  };

  const removeKeyword = (idx: number) => {
    const next = keywords.filter((_, i) => i !== idx);
    setKeywords(next);
    emit({ added_keywords: next });
  };

  const payload = (): StructuredResumeData => ({
    summary,
    tailored_bullets: bullets.filter(Boolean),
    added_keywords: keywords,
  });

  return (
    <div className="space-y-5 text-sm">
      <div className="space-y-2">
        <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Professional Summary
        </label>
        <textarea
          value={summary}
          onChange={(e) => {
            setSummary(e.target.value);
            emit({ summary: e.target.value });
          }}
          disabled={disabled}
          rows={4}
          className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm resize-y min-h-[88px]"
          placeholder="2–3 lines with top JD keywords…"
        />
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between gap-2">
          <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Experience Bullets
          </label>
          <button
            type="button"
            onClick={addBullet}
            disabled={disabled}
            className="inline-flex items-center gap-1 text-xs text-primary hover:underline disabled:opacity-50"
          >
            <Plus className="h-3 w-3" /> Add bullet
          </button>
        </div>
        <div className="space-y-2">
          {bullets.length === 0 && (
            <p className="text-xs text-muted-foreground">No bullets yet — add measurable achievements.</p>
          )}
          {bullets.map((b, i) => (
            <div key={i} className="flex gap-2 items-start">
              <textarea
                value={b}
                onChange={(e) => updateBullet(i, e.target.value)}
                disabled={disabled}
                rows={2}
                className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm resize-y"
              />
              <button
                type="button"
                onClick={() => removeBullet(i)}
                disabled={disabled}
                className="p-2 rounded-md text-muted-foreground hover:text-destructive hover:bg-muted"
                title="Remove bullet"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          ATS Keywords
        </label>
        <div className="flex flex-wrap gap-1.5 mb-2">
          {keywords.map((k, i) => (
            <span
              key={`${k}-${i}`}
              className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20"
            >
              {k}
              <button
                type="button"
                onClick={() => removeKeyword(i)}
                disabled={disabled}
                className="hover:text-destructive"
                aria-label={`Remove ${k}`}
              >
                ×
              </button>
            </span>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            value={keywordInput}
            onChange={(e) => setKeywordInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addKeyword())}
            disabled={disabled}
            placeholder="Add keyword (Enter)"
            className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm"
          />
          <button
            type="button"
            onClick={addKeyword}
            disabled={disabled || !keywordInput.trim()}
            className="px-3 py-2 rounded-lg border border-border text-sm hover:bg-muted disabled:opacity-50"
          >
            Add
          </button>
        </div>
      </div>

      {(onSave || onRescore) && (
        <div className="flex flex-wrap gap-2 pt-2 border-t border-border">
          {onRescore && (
            <button
              type="button"
              onClick={() => onRescore(payload())}
              disabled={disabled || saving}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-primary/40 text-primary text-sm font-medium hover:bg-primary/10 disabled:opacity-50"
            >
              <RotateCcw className="h-4 w-4" />
              {rescoreLabel}
            </button>
          )}
          {onSave && (
            <button
              type="button"
              onClick={() => onSave(payload())}
              disabled={disabled || saving}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium disabled:opacity-50"
            >
              <Save className="h-4 w-4" />
              {saving ? "Saving…" : "Save changes"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
