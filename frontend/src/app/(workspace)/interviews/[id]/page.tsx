"use client";

import { useCallback, useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import api from "@/lib/api";
import { Loader2, Sparkles, BookOpen, MessageSquare, Send, Zap, Building2 } from "lucide-react";

interface PrepData {
  company_dossier: string;
  technical_drills: { topic: string; question: string; suggested_answer: string }[];
  behavioral_drills: { behavioral_theme: string; question: string; star_mapping: string }[];
  pitch_ideas: { title: string; description: string }[];
}

export default function InterviewPrepPage() {
  const { id } = useParams() as { id: string };
  const [prep, setPrep] = useState<PrepData | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [activeTab, setActiveTab] = useState<"dossier" | "simulator">("dossier");
  const [error, setError] = useState<string | null>(null);
  
  // Chat state
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const fetchPrep = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get(`/applications/${id}/interview-prep`);
      if (res.data.status === "ok" && res.data.interview_prep) {
        setPrep(res.data.interview_prep);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void fetchPrep();
  }, [fetchPrep]);

  useEffect(() => {
    if (activeTab === "simulator" && messages.length === 0) {
      setMessages([{ role: "assistant", content: "Hello! I'm ready to begin our mock interview. First, could you tell me a little bit about yourself and your background?" }]);
    }
  }, [activeTab, messages.length]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleGenerate() {
    try {
      setGenerating(true);
      setError(null);
      const res = await api.post(`/applications/${id}/interview-prep`);
      setPrep(res.data.interview_prep);
    } catch (e) {
      console.error(e);
      setError(
        "Could not generate the prep guide (AI may be busy). Retry in a moment, or switch LLM in Canvas."
      );
    } finally {
      setGenerating(false);
    }
  }

  async function handleSendMessage(e: React.FormEvent) {
    e.preventDefault();
    if (!inputValue.trim()) return;

    const newMessages = [...messages, { role: "user", content: inputValue }];
    setMessages(newMessages);
    setInputValue("");
    setChatLoading(true);

    try {
      const res = await api.post(`/applications/${id}/mock-interview`, {
        messages: newMessages
      });
      setMessages([...newMessages, { role: "assistant", content: res.data.reply }]);
    } catch (e) {
      console.error(e);
      setMessages([...newMessages, { role: "assistant", content: "Sorry, I lost my connection. Could we try again?" }]);
    } finally {
      setChatLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full min-h-[500px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!prep) {
    return (
      <div className="max-w-3xl mx-auto py-12 px-4 text-center">
        <Sparkles className="h-12 w-12 text-primary mx-auto mb-4" />
        <h1 className="text-3xl font-bold mb-2">Interview Prep Module</h1>
        <p className="text-muted-foreground mb-8">
          Generate a deeply personalized company dossier, product pitch ideas, and targeted technical/behavioral drills based on your exact resume and this job description.
        </p>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="bg-primary text-primary-foreground px-6 py-3 rounded-md font-medium inline-flex items-center gap-2 hover:bg-primary/90 disabled:opacity-50"
        >
          {generating ? <Loader2 className="h-5 w-5 animate-spin" /> : <Zap className="h-5 w-5" />}
          {generating ? "Generating Your Guide..." : "Generate Prep Guide"}
        </button>
        {error && (
          <p className="mt-4 text-sm text-destructive max-w-md mx-auto">{error}</p>
        )}
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 h-full flex flex-col">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">Interview Prep</h1>
          <p className="text-muted-foreground mt-1">Personalized guide & mock simulator</p>
        </div>
        <div className="flex bg-muted p-1 rounded-lg">
          <button
            onClick={() => setActiveTab("dossier")}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === "dossier" ? "bg-background shadow text-foreground" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <BookOpen className="h-4 w-4 inline-block mr-2" />
            Dossier & Drills
          </button>
          <button
            onClick={() => setActiveTab("simulator")}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === "simulator" ? "bg-background shadow text-foreground" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <MessageSquare className="h-4 w-4 inline-block mr-2" />
            Mock Simulator
          </button>
        </div>
      </div>

      {activeTab === "dossier" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 overflow-y-auto pb-12">
          {/* Left Column */}
          <div className="space-y-8">
            <section className="bg-card border border-border p-6 rounded-xl shadow-sm">
              <h2 className="text-xl font-bold flex items-center gap-2 mb-4">
                <Building2 className="text-primary h-5 w-5" /> Company Cheat Sheet
              </h2>
              <div className="prose prose-sm dark:prose-invert">
                {prep.company_dossier}
              </div>
            </section>

            <section className="bg-card border border-border p-6 rounded-xl shadow-sm">
              <h2 className="text-xl font-bold flex items-center gap-2 mb-4">
                <Sparkles className="text-yellow-500 h-5 w-5" /> Product Pitch Ideas
              </h2>
              <p className="text-sm text-muted-foreground mb-4">Proactively pitch these ideas during your interview to stand out.</p>
              <div className="space-y-4">
                {prep.pitch_ideas?.map((pitch, i) => (
                  <div key={i} className="border border-border/50 bg-muted/20 p-4 rounded-lg">
                    <h3 className="font-semibold text-foreground mb-1">{pitch.title}</h3>
                    <p className="text-sm text-muted-foreground">{pitch.description}</p>
                  </div>
                ))}
              </div>
            </section>
          </div>

          {/* Right Column */}
          <div className="space-y-8">
            <section className="bg-card border border-border p-6 rounded-xl shadow-sm">
              <h2 className="text-xl font-bold text-red-500 flex items-center gap-2 mb-4">
                <Zap className="h-5 w-5" /> Targeted Technical Drills
              </h2>
              <div className="space-y-4">
                {prep.technical_drills?.map((drill, i) => (
                  <div key={i} className="border-b border-border pb-4 last:border-0 last:pb-0">
                    <span className="text-xs font-semibold text-red-500 uppercase tracking-wider">{drill.topic}</span>
                    <h3 className="font-medium text-foreground mt-1 mb-2">{drill.question}</h3>
                    <p className="text-sm text-muted-foreground bg-muted/30 p-3 rounded">{drill.suggested_answer}</p>
                  </div>
                ))}
              </div>
            </section>

            <section className="bg-card border border-border p-6 rounded-xl shadow-sm">
              <h2 className="text-xl font-bold text-blue-500 flex items-center gap-2 mb-4">
                <BookOpen className="h-5 w-5" /> Behavioral Mapping (STAR)
              </h2>
              <div className="space-y-4">
                {prep.behavioral_drills?.map((drill, i) => (
                  <div key={i} className="border-b border-border pb-4 last:border-0 last:pb-0">
                    <span className="text-xs font-semibold text-blue-500 uppercase tracking-wider">{drill.behavioral_theme}</span>
                    <h3 className="font-medium text-foreground mt-1 mb-2">{drill.question}</h3>
                    <div className="text-sm text-muted-foreground bg-blue-500/10 p-3 rounded border border-blue-500/20">
                      <span className="font-semibold text-blue-500 block mb-1">Use this experience:</span>
                      {drill.star_mapping}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </div>
      )}

      {activeTab === "simulator" && (
        <div className="flex-1 bg-card border border-border rounded-xl shadow-sm overflow-hidden flex flex-col h-[600px]">
          <div className="bg-muted px-6 py-4 border-b border-border flex items-center justify-between">
            <div>
              <h2 className="font-semibold">Mock Interview Simulator</h2>
              <p className="text-xs text-muted-foreground">The AI will roleplay as the Hiring Manager and evaluate your answers.</p>
            </div>
            <span className="flex h-3 w-3 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
            </span>
          </div>
          
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[80%] rounded-2xl px-5 py-3 ${
                  m.role === "user" 
                    ? "bg-primary text-primary-foreground rounded-tr-sm" 
                    : "bg-muted text-foreground rounded-tl-sm"
                }`}>
                  <p className="text-sm whitespace-pre-wrap">{m.content}</p>
                </div>
              </div>
            ))}
            {chatLoading && (
              <div className="flex justify-start">
                <div className="bg-muted text-foreground rounded-2xl rounded-tl-sm px-5 py-3 flex items-center gap-2">
                  <span className="h-2 w-2 bg-foreground/40 rounded-full animate-bounce"></span>
                  <span className="h-2 w-2 bg-foreground/40 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                  <span className="h-2 w-2 bg-foreground/40 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <form onSubmit={handleSendMessage} className="p-4 border-t border-border bg-background">
            <div className="relative">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Type your answer (STAR format recommended)..."
                disabled={chatLoading}
                className="w-full bg-muted border-transparent focus:border-primary focus:ring-1 focus:ring-primary rounded-full pl-6 pr-12 py-4 text-sm disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={chatLoading || !inputValue.trim()}
                className="absolute right-2 top-2 p-2 bg-primary text-primary-foreground rounded-full hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
