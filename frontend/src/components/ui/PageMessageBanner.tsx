"use client";

import { AlertCircle, CheckCircle, Info, X } from "lucide-react";

export type PageMessageTone = "error" | "success" | "info";

export type PageMessage = {
  tone: PageMessageTone;
  title: string;
  detail: string;
};

export function PageMessageBanner({
  message,
  onDismiss,
}: {
  message: PageMessage;
  onDismiss?: () => void;
}) {
  const tone = message.tone;
  return (
    <div
      role="status"
      className={`rounded-xl border px-4 py-3 text-sm flex items-start gap-3 ${
        tone === "error"
          ? "border-destructive/30 bg-destructive/10"
          : tone === "success"
            ? "border-emerald-500/30 bg-emerald-500/10"
            : "border-amber-500/30 bg-amber-500/10"
      }`}
    >
      {tone === "error" ? (
        <AlertCircle className="h-5 w-5 mt-0.5 shrink-0 text-destructive" />
      ) : tone === "success" ? (
        <CheckCircle className="h-5 w-5 mt-0.5 shrink-0 text-emerald-500" />
      ) : (
        <Info className="h-5 w-5 mt-0.5 shrink-0 text-amber-500" />
      )}
      <div className="min-w-0 flex-1 space-y-1">
        <p
          className={`font-semibold ${
            tone === "error"
              ? "text-destructive"
              : tone === "success"
                ? "text-emerald-700 dark:text-emerald-400"
                : "text-amber-700 dark:text-amber-400"
          }`}
        >
          {message.title}
        </p>
        <p className="text-muted-foreground leading-relaxed">{message.detail}</p>
      </div>
      {onDismiss && (
        <button
          type="button"
          aria-label="Dismiss message"
          onClick={onDismiss}
          className="text-muted-foreground hover:text-foreground shrink-0 p-1"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}

/** Map raw fetch/API errors into a readable banner. */
export function messageFromError(
  raw: unknown,
  title = "Something went wrong"
): PageMessage {
  const msg =
    raw instanceof Error
      ? raw.message
      : typeof raw === "string"
        ? raw
        : "Unexpected error";

  if (/abort|timeout/i.test(msg)) {
    return {
      tone: "error",
      title: "Request timed out",
      detail:
        "The API or AI provider took too long. Wait a moment and retry. Paste full text (not only a URL) when possible.",
    };
  }
  if (/Failed to fetch|network|ECONNRESET/i.test(msg)) {
    return {
      tone: "error",
      title: "Connection failed",
      detail:
        "Could not reach the API. Confirm Docker is up on :8001, then retry.",
    };
  }
  if (/401|credentials|unauthorized|validate/i.test(msg)) {
    return {
      tone: "error",
      title: "Session expired",
      detail: "Sign in again, then retry this action.",
    };
  }
  return { tone: "error", title, detail: msg || "Please retry." };
}
