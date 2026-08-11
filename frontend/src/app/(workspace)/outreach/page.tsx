"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Send,
  CheckCircle,
  Copy,
  Mail,
  Building2,
  User,
  RefreshCw,
  Paperclip,
  Eye,
  Save,
  FileStack,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { usePanelStore } from "@/store/panelStore";

/** Navigate outside React state rules (mailto / in-app CTA). */
function hardNavigate(url: string) {
  window.location.assign(url);
}

interface Attachment {
  kind: string;
  name: string;
  exists: boolean;
  download_url?: string | null;
  preview_url?: string | null;
}

interface Message {
  id: string;
  created_at: string;
  content: string;
  message_type: string;
  status: string;
  recruiter_name: string | null;
  recruiter_email: string | null;
  recruiter_linkedin: string | null;
  role_title: string | null;
  company_name: string | null;
  subject_line?: string | null;
  body?: string | null;
  has_tailored_resume?: boolean;
  application_id?: string | null;
  job_id?: string | null;
  attachments?: Attachment[];
  package_hint?: string | null;
}

function parseSubjectBody(content: string): { subject: string; body: string } {
  const text = (content || "").trim();
  if (/^subject:/i.test(text)) {
    const idx = text.indexOf("\n");
    const first = idx >= 0 ? text.slice(0, idx) : text;
    const subject = first.replace(/^subject:\s*/i, "").trim();
    const body = idx >= 0 ? text.slice(idx + 1).replace(/^\n/, "") : "";
    return { subject, body };
  }
  return { subject: "", body: text };
}

export default function OutreachPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [sendingId, setSendingId] = useState<string | null>(null);
  const [regenId, setRegenId] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<
    Record<string, { subject: string; body: string; dirty: boolean }>
  >({});
  const token = useAuthStore((s) => s.token);
  const setPreview = usePanelStore((s) => s.setPreview);
  const openMobilePanel = usePanelStore((s) => s.openMobilePanel);

  useEffect(() => {
    const fetchMessages = async () => {
      try {
        setLoading(true);
        const res = await fetch("/api/v1/messages/", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data: Message[] = await res.json();
          setMessages(data);
          const next: Record<string, { subject: string; body: string; dirty: boolean }> =
            {};
          for (const msg of data) {
            const parsed = parseSubjectBody(msg.content);
            next[msg.id] = {
              subject: msg.subject_line || parsed.subject || "",
              body: msg.body || parsed.body || "",
              dirty: false,
            };
          }
          setDrafts(next);
        }
      } catch (err) {
        console.error("Failed to fetch messages", err);
      } finally {
        setLoading(false);
      }
    };

    if (token) fetchMessages();
  }, [token]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const openInGmail = (msg: Message) => {
    const d = drafts[msg.id];
    const subject =
      d?.subject ||
      msg.subject_line ||
      `${msg.role_title || "Open role"} at ${msg.company_name || "company"}`;
    const body = d?.body || msg.body || parseSubjectBody(msg.content).body;
    const to = msg.recruiter_email || "";
    window.open(
      `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(to)}&su=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`,
      "_blank"
    );
  };

  const handleRegenerate = async (id: string) => {
    try {
      setRegenId(id);
      const res = await fetch(`/api/v1/messages/${id}/regenerate`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || "Failed to regenerate draft");
        return;
      }
      const updated: Message = await res.json();
      setMessages((prev) => prev.map((m) => (m.id === id ? updated : m)));
      const parsed = parseSubjectBody(updated.content);
      setDrafts((prev) => ({
        ...prev,
        [id]: {
          subject: updated.subject_line || parsed.subject,
          body: updated.body || parsed.body,
          dirty: false,
        },
      }));
    } catch (err) {
      console.error(err);
      alert("Error regenerating draft");
    } finally {
      setRegenId(null);
    }
  };

  const handleSave = async (id: string) => {
    const d = drafts[id];
    if (!d) return;
    try {
      setSavingId(id);
      const res = await fetch(`/api/v1/messages/${id}`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ subject_line: d.subject, body: d.body }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || "Failed to save");
        return;
      }
      const updated: Message = await res.json();
      setMessages((prev) => prev.map((m) => (m.id === id ? updated : m)));
      setDrafts((prev) => ({
        ...prev,
        [id]: { ...prev[id], dirty: false },
      }));
    } catch (err) {
      console.error(err);
      alert("Error saving draft");
    } finally {
      setSavingId(null);
    }
  };

  const previewAttachment = async (att: Attachment) => {
    if (!att.preview_url || !token) return;
    try {
      const res = await fetch(att.preview_url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || "Preview failed — package the resume first");
        return;
      }
      const data = await res.json();
      setPreview({
        title: data.name || att.name,
        kind: data.kind || "pdf",
        fileUrl: data.file_url || att.download_url || "",
        text: data.text,
        note: data.note,
      });
      openMobilePanel("pdf");
    } catch (err) {
      console.error(err);
      alert("Could not open resume preview");
    }
  };

  const handleAutoSend = async (id: string, force = false) => {
    const d = drafts[id];
    if (d?.dirty) {
      await handleSave(id);
    }
    try {
      setSendingId(id);
      const qs = force ? "?force=true" : "";
      const res = await fetch(`/api/v1/messages/${id}/send${qs}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setMessages((prev) =>
            prev.map((m) => (m.id === id ? { ...m, status: "Sent" } : m))
          );
        } else if (data.package_required) {
          const go = window.confirm(
            `${data.message}\n\nOpen Approvals to package? (Cancel = send anyway)`
          );
          if (go && data.cta) {
            hardNavigate(data.cta);
          } else if (!go) {
            await handleAutoSend(id, true);
          }
        } else if (data.mailto) {
          hardNavigate(data.mailto);
          alert(
            (data.message || "Opened mailto.") +
              " After you send, click Mark sent."
          );
        } else {
          alert(data.message || "Could not send");
        }
      } else {
        const err = await res.json();
        alert(err.detail || "Failed to send email");
      }
    } catch (err) {
      console.error(err);
      alert("Error sending email");
    } finally {
      setSendingId(null);
    }
  };

  const handleMarkSent = async (id: string) => {
    try {
      setSendingId(id);
      const res = await fetch(`/api/v1/messages/${id}/mark-sent`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Mark sent failed");
      }
      setMessages((prev) =>
        prev.map((m) => (m.id === id ? { ...m, status: "Sent" } : m))
      );
    } catch (err) {
      alert(err instanceof Error ? err.message : "Mark sent failed");
    } finally {
      setSendingId(null);
    }
  };

  return (
    <div className="p-4 md:p-8 max-w-6xl mx-auto space-y-8 animate-in fade-in duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold tracking-tight mb-2">Outreach Queue</h1>
          <p className="text-muted-foreground text-lg">
            Human-sounding drafts from your JD + resume. Edit subject &amp; body, preview
            the tailored resume, then send.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="space-y-6">
          {[...Array(2)].map((_, i) => (
            <div key={i} className="h-64 rounded-xl bg-muted animate-pulse"></div>
          ))}
        </div>
      ) : messages.length === 0 ? (
        <div className="text-center py-20 border rounded-xl border-dashed bg-card/50 space-y-4">
          <Send className="mx-auto h-16 w-16 text-muted-foreground mb-4 opacity-50" />
          <h3 className="text-xl font-medium">No Drafts Yet</h3>
          <p className="text-muted-foreground mt-2 max-w-sm mx-auto">
            Run Canvas on a Wishlist job so Outreach can draft from company research +
            tailored resume.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link
              href="/jobs"
              className="inline-flex items-center rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted"
            >
              Jobs / Wishlist
            </Link>
            <Link
              href="/canvas"
              className="inline-flex items-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
            >
              Open Canvas
            </Link>
            <Link
              href="/tracker"
              className="inline-flex items-center rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted"
            >
              Tracker
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {messages.map((msg) => {
            const d = drafts[msg.id] || { subject: "", body: "", dirty: false };
            const resumeAtt =
              msg.attachments?.find((a) => a.kind === "resume_pdf" && a.exists) ||
              msg.attachments?.find((a) => a.kind === "resume_docx" && a.exists);
            const coverAtt =
              msg.attachments?.find((a) => a.kind === "cover_pdf" && a.exists) ||
              msg.attachments?.find((a) => a.kind === "cover_docx" && a.exists);

            return (
              <div
                key={msg.id}
                className="rounded-xl border bg-card shadow-sm overflow-hidden flex flex-col md:flex-row"
              >
                <div className="bg-muted/30 p-6 md:w-1/3 border-b md:border-b-0 md:border-r flex flex-col gap-6">
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3">
                      Recipient
                    </h4>
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold">
                        {(msg.recruiter_name || "H")[0]}
                      </div>
                      <div>
                        <p className="font-medium text-foreground">
                          {msg.recruiter_name || "Hiring Manager"}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {msg.recruiter_email || "No email found"}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3">
                      Context
                    </h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex items-start gap-2">
                        <Building2 className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
                        <span>{msg.company_name || "Unknown Company"}</span>
                      </div>
                      <div className="flex items-start gap-2">
                        <User className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
                        <span>{msg.role_title || "Unknown Role"}</span>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-lg border bg-background p-3 space-y-2">
                    <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                      <Paperclip className="h-3.5 w-3.5" /> Attach &amp; verify
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {msg.package_hint}
                    </p>
                    {resumeAtt ? (
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => previewAttachment(resumeAtt)}
                          className="inline-flex items-center gap-1 rounded-md border px-2.5 py-1.5 text-xs hover:bg-muted"
                        >
                          <Eye className="h-3.5 w-3.5" /> Preview resume
                        </button>
                        {resumeAtt.download_url && (
                          <a
                            href={resumeAtt.download_url}
                            className="inline-flex items-center gap-1 rounded-md border px-2.5 py-1.5 text-xs hover:bg-muted"
                            onClick={(e) => {
                              e.preventDefault();
                              fetch(resumeAtt.download_url!, {
                                headers: { Authorization: `Bearer ${token}` },
                              })
                                .then((r) => r.blob())
                                .then((blob) => {
                                  const url = URL.createObjectURL(blob);
                                  const a = document.createElement("a");
                                  a.href = url;
                                  a.download = resumeAtt.name;
                                  a.click();
                                  URL.revokeObjectURL(url);
                                });
                            }}
                          >
                            Download
                          </a>
                        )}
                      </div>
                    ) : (
                      <div className="flex flex-wrap gap-2">
                        {msg.job_id && (
                          <Link
                            href={`/canvas?job_id=${encodeURIComponent(msg.job_id)}`}
                            className="inline-flex items-center gap-1 rounded-md border px-2.5 py-1.5 text-xs hover:bg-muted"
                          >
                            Canvas
                          </Link>
                        )}
                        <Link
                          href="/jobs"
                          className="inline-flex items-center gap-1 rounded-md border px-2.5 py-1.5 text-xs hover:bg-muted"
                        >
                          <FileStack className="h-3.5 w-3.5" /> Package
                        </Link>
                      </div>
                    )}
                    {coverAtt && (
                      <button
                        type="button"
                        onClick={() => previewAttachment(coverAtt)}
                        className="inline-flex items-center gap-1 rounded-md border px-2.5 py-1.5 text-xs hover:bg-muted"
                      >
                        <Eye className="h-3.5 w-3.5" /> Preview cover
                      </button>
                    )}
                    {resumeAtt && (
                      <p className="text-[11px] text-muted-foreground font-mono truncate">
                        {resumeAtt.name}
                      </p>
                    )}
                  </div>

                  <div className="mt-auto pt-4 border-t">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Status:</span>
                      <span
                        className={`font-medium px-2 py-0.5 rounded-full ${
                          msg.status === "Draft"
                            ? "bg-yellow-500/10 text-yellow-600"
                            : "bg-green-500/10 text-green-600"
                        }`}
                      >
                        {msg.status}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="p-6 md:w-2/3 flex flex-col gap-3">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <h3 className="font-semibold text-lg">Draft ({msg.message_type})</h3>
                    <div className="flex gap-2 flex-wrap">
                      {msg.status !== "Sent" && (
                        <>
                          <button
                            onClick={() => handleRegenerate(msg.id)}
                            disabled={regenId === msg.id}
                            className="inline-flex items-center justify-center rounded-md text-xs font-medium border hover:bg-muted h-8 px-3 gap-1.5 disabled:opacity-50"
                          >
                            <RefreshCw
                              className={`h-3.5 w-3.5 ${regenId === msg.id ? "animate-spin" : ""}`}
                            />
                            {regenId === msg.id ? "Rewriting…" : "Rewrite (human tone)"}
                          </button>
                          <button
                            onClick={() => handleSave(msg.id)}
                            disabled={savingId === msg.id || !d.dirty}
                            className="inline-flex items-center justify-center rounded-md text-xs font-medium border hover:bg-muted h-8 px-3 gap-1.5 disabled:opacity-50"
                          >
                            <Save className="h-3.5 w-3.5" />
                            {savingId === msg.id ? "Saving…" : d.dirty ? "Save edits" : "Saved"}
                          </button>
                        </>
                      )}
                      <button
                        onClick={() => copyToClipboard(d.body)}
                        className="inline-flex items-center justify-center rounded-md text-xs font-medium border hover:bg-muted h-8 px-3 gap-1.5"
                      >
                        <Copy className="h-3.5 w-3.5" /> Copy body
                      </button>
                      {msg.message_type === "Email" && (
                        <button
                          onClick={() => openInGmail(msg)}
                          className="inline-flex items-center justify-center rounded-md text-xs font-medium bg-primary text-primary-foreground shadow hover:bg-primary/90 h-8 px-3 gap-1.5"
                        >
                          <Mail className="h-3.5 w-3.5" /> Open in Gmail
                        </button>
                      )}
                    </div>
                  </div>

                  <label className="block space-y-1">
                    <span className="text-xs font-medium text-muted-foreground">Subject</span>
                    <input
                      value={d.subject}
                      disabled={msg.status === "Sent"}
                      onChange={(e) =>
                        setDrafts((prev) => ({
                          ...prev,
                          [msg.id]: {
                            ...prev[msg.id],
                            subject: e.target.value,
                            dirty: true,
                          },
                        }))
                      }
                      className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm font-medium"
                      placeholder="Role at Company — Your Name"
                    />
                  </label>

                  <label className="block space-y-1 flex-1">
                    <span className="text-xs font-medium text-muted-foreground">
                      Body (edit freely before send)
                    </span>
                    <textarea
                      value={d.body}
                      disabled={msg.status === "Sent"}
                      onChange={(e) =>
                        setDrafts((prev) => ({
                          ...prev,
                          [msg.id]: {
                            ...prev[msg.id],
                            body: e.target.value,
                            dirty: true,
                          },
                        }))
                      }
                      rows={14}
                      className="w-full rounded-md border border-border bg-muted/30 px-3 py-3 text-sm leading-relaxed resize-y min-h-[240px]"
                    />
                  </label>

                  <div className="mt-2 flex justify-end gap-3 flex-wrap">
                    {msg.status !== "Sent" && (
                      <button
                        onClick={() => handleAutoSend(msg.id)}
                        disabled={sendingId === msg.id}
                        className="inline-flex items-center justify-center rounded-md text-sm font-medium bg-green-600 hover:bg-green-700 text-white h-9 px-4 gap-2 disabled:opacity-50"
                      >
                        {sendingId === msg.id ? (
                          <div className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        ) : (
                          <Send className="h-4 w-4" />
                        )}
                        {sendingId === msg.id ? "Sending..." : "Send / mailto"}
                      </button>
                    )}
                    <button
                      type="button"
                      disabled={sendingId === msg.id || msg.status === "Sent"}
                      className="inline-flex items-center justify-center rounded-md text-sm font-medium border hover:bg-muted text-muted-foreground h-9 px-4 gap-2 disabled:opacity-50"
                      onClick={() => handleMarkSent(msg.id)}
                    >
                      <CheckCircle className="h-4 w-4" /> Mark as Sent
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
