"use client";

import { useCallback, useEffect, useState } from "react";
import { HelpCircle, Loader2, Plus, RefreshCw, Trash2, Sparkles, Edit2, Check, X } from "lucide-react";
import api, { getApiErrorMessage } from "@/lib/api";

interface ScreeningQA {
  id: string;
  question: string;
  answer: string;
  tags: string[];
  updated_at?: string | null;
}

function QAItem({ item, onDelete, onUpdate }: { item: ScreeningQA; onDelete: (id: string) => void; onUpdate: (id: string, q: string, a: string, t: string) => Promise<void> }) {
  const [isEditing, setIsEditing] = useState(false);
  const [question, setQuestion] = useState(item.question);
  const [answer, setAnswer] = useState(item.answer);
  const [tags, setTags] = useState((item.tags || []).join(", "));
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    await onUpdate(item.id, question, answer, tags);
    setSaving(false);
    setIsEditing(false);
  };

  if (isEditing) {
    return (
      <li className="rounded-lg border bg-muted/30 p-4 space-y-3">
        <input value={question} onChange={e => setQuestion(e.target.value)} className="w-full text-sm font-medium border rounded px-2 py-1 bg-background" placeholder="Question" />
        <textarea value={answer} onChange={e => setAnswer(e.target.value)} className="w-full text-sm border rounded px-2 py-1 bg-background resize-y" rows={2} placeholder="Answer" />
        <input value={tags} onChange={e => setTags(e.target.value)} className="w-full text-xs border rounded px-2 py-1 bg-background" placeholder="Tags (comma separated)" />
        <div className="flex gap-2 justify-end pt-1">
          <button type="button" onClick={() => setIsEditing(false)} className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs hover:bg-muted text-muted-foreground"><X className="w-3 h-3"/> Cancel</button>
          <button type="button" onClick={handleSave} disabled={saving} className="inline-flex items-center gap-1 rounded bg-primary text-primary-foreground px-2 py-1 text-xs"><Check className="w-3 h-3"/> Save</button>
        </div>
      </li>
    );
  }

  return (
    <li className="rounded-lg border bg-card p-4 flex gap-3 justify-between group">
      <div className="min-w-0 space-y-1">
        <p className="text-sm font-medium text-foreground">{item.question}</p>
        <p className="text-sm text-muted-foreground whitespace-pre-wrap">{item.answer}</p>
        {item.tags?.length > 0 && (
          <div className="flex flex-wrap gap-1 pt-1">
            {item.tags.map((t) => (
              <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground border border-border">{t}</span>
            ))}
          </div>
        )}
      </div>
      <div className="flex flex-col gap-2 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
        <button type="button" onClick={() => setIsEditing(true)} className="text-muted-foreground hover:text-foreground"><Edit2 className="h-4 w-4" /></button>
        <button type="button" onClick={() => onDelete(item.id)} className="text-muted-foreground hover:text-destructive"><Trash2 className="h-4 w-4" /></button>
      </div>
    </li>
  );
}

export default function ScreeningQAPage() {
  const [items, setItems] = useState<ScreeningQA[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [tags, setTags] = useState("");
  const [saving, setSaving] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchItems = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get<ScreeningQA[]>("/screening-qa/");
      setItems(data);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Failed to load screening Q&A"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || !answer.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await api.post("/screening-qa/", {
        question: question.trim(),
        answer: answer.trim(),
        tags: tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
      });
      setQuestion("");
      setAnswer("");
      setTags("");
      await fetchItems();
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Failed to save Q&A"));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    setError(null);
    try {
      await api.delete(`/screening-qa/${id}`);
      setItems((prev) => prev.filter((x) => x.id !== id));
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Failed to delete"));
    } finally {
      setDeletingId(null);
    }
  };

  const handleUpdate = async (id: string, q: string, a: string, t: string) => {
    setError(null);
    try {
      await api.patch(`/screening-qa/${id}`, {
        question: q.trim(),
        answer: a.trim(),
        tags: t.split(",").map((x) => x.trim()).filter(Boolean),
      });
      await fetchItems();
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Failed to update"));
    }
  };

  const handleSeed = async () => {
    setSeeding(true);
    setError(null);
    try {
      const { data } = await api.post<{ created: number; note?: string }>(
        "/screening-qa/seed-defaults"
      );
      await fetchItems();
      if (data.note) {
        /* keep quiet — list refresh is enough */
      }
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Failed to seed defaults"));
    } finally {
      setSeeding(false);
    }
  };

  return (
    <div className="p-4 md:p-8 max-w-3xl mx-auto space-y-6 animate-in fade-in duration-500">
      <header className="space-y-2">
        <div className="flex items-center gap-2 text-primary">
          <HelpCircle className="h-6 w-6" />
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Screening Q&A
          </h1>
        </div>
        <p className="text-sm text-muted-foreground max-w-xl">
          Save answers once — Career OS and the Chrome autofill extension reuse them on
          Greenhouse / Lever / Workday. Never auto-submits; you always click Submit.
        </p>
      </header>

      <form
        onSubmit={handleCreate}
        className="rounded-xl border bg-card p-5 space-y-3 shadow-sm"
      >
        <label className="block space-y-1">
          <span className="text-xs font-medium text-muted-foreground">Question</span>
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. Are you authorized to work in the US?"
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            required
          />
        </label>
        <label className="block space-y-1">
          <span className="text-xs font-medium text-muted-foreground">Answer</span>
          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Yes"
            rows={3}
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm resize-y"
            required
          />
        </label>
        <label className="block space-y-1">
          <span className="text-xs font-medium text-muted-foreground">
            Tags (comma-separated, optional)
          </span>
          <input
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            placeholder="work auth, salary, notice"
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
          />
        </label>
        <div className="flex items-center gap-2 pt-1">
          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-md bg-primary text-primary-foreground px-3 py-2 text-sm font-medium disabled:opacity-50"
          >
            {saving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Plus className="h-4 w-4" />
            )}
            Save answer
          </button>
          <button
            type="button"
            onClick={handleSeed}
            disabled={seeding}
            className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm font-medium hover:bg-muted disabled:opacity-50"
          >
            {seeding ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            Seed common answers
          </button>
          <button
            type="button"
            onClick={() => fetchItems()}
            className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm text-muted-foreground hover:text-foreground"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>
      </form>

      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 rounded-lg bg-muted animate-pulse" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="text-sm text-muted-foreground border rounded-lg p-6 text-center space-y-3">
          <p>
            No saved answers yet. Seed common ATS questions (work auth, notice,
            salary…) then edit them to match you — empty bank = extension fills
            nothing.
          </p>
          <button
            type="button"
            onClick={handleSeed}
            disabled={seeding}
            className="inline-flex items-center gap-2 rounded-md bg-primary text-primary-foreground px-3 py-2 text-sm font-medium disabled:opacity-50"
          >
            {seeding ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            Seed common answers
          </button>
        </div>
      ) : (
        <ul className="space-y-3">
          {items.map((item) => (
            <QAItem key={item.id} item={item} onDelete={handleDelete} onUpdate={handleUpdate} />
          ))}
        </ul>
      )}
    </div>
  );
}
