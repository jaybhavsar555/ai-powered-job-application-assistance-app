"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import styles from "./DocxFormattedPreview.module.css";

type Props = {
  /** Authenticated API path or blob-capable URL */
  fileUrl: string;
  token: string | null;
  className?: string;
};

/**
 * Renders a .docx with Word-like formatting, scaled to fit the side panel.
 */
export function DocxFormattedPreview({ fileUrl, token, className }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const hostRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fitToPanel = () => {
    const scroll = scrollRef.current;
    const host = hostRef.current;
    if (!scroll || !host) return;

    const wrapper = host.querySelector(".docx-wrapper") as HTMLElement | null;
    if (!wrapper) return;

    // Reset before measuring natural size
    wrapper.style.transform = "";
    wrapper.style.width = "";
    host.style.height = "";
    host.style.width = "";

    const pages = Array.from(
      wrapper.querySelectorAll("section.docx")
    ) as HTMLElement[];
    if (pages.length === 0) return;

    const naturalWidth = Math.max(
      ...pages.map((p) => p.scrollWidth || p.offsetWidth),
      wrapper.scrollWidth
    );
    const available = Math.max(120, scroll.clientWidth - 16);
    const scale = Math.min(1, available / naturalWidth);

    if (scale < 0.999) {
      wrapper.style.transformOrigin = "top left";
      wrapper.style.transform = `scale(${scale})`;
      // Keep layout height correct after scale (transform doesn't affect flow)
      const naturalHeight = wrapper.scrollHeight;
      host.style.height = `${Math.ceil(naturalHeight * scale)}px`;
      host.style.width = `${Math.ceil(naturalWidth * scale)}px`;
    } else {
      wrapper.style.transform = "";
      host.style.height = "";
      host.style.width = "100%";
    }
  };

  useEffect(() => {
    let cancelled = false;
    const host = hostRef.current;

    async function renderDocx() {
      if (!host || !fileUrl) return;
      setLoading(true);
      setError(null);
      host.innerHTML = "";
      host.style.height = "";
      host.style.width = "";

      try {
        const headers: HeadersInit = {};
        if (fileUrl.startsWith("/api/") && token) {
          headers.Authorization = `Bearer ${token}`;
        }
        const res = await fetch(fileUrl, { headers });
        if (!res.ok) {
          throw new Error(`Failed to load DOCX (${res.status})`);
        }
        const buffer = await res.arrayBuffer();
        if (cancelled) return;

        const { renderAsync } = await import("docx-preview");
        await renderAsync(buffer, host, undefined, {
          className: "docx-preview-body",
          inWrapper: true,
          // Keep real page metrics so we can scale-to-fit the panel
          ignoreWidth: false,
          ignoreHeight: false,
          breakPages: true,
          renderHeaders: true,
          renderFooters: true,
          renderFootnotes: true,
          renderEndnotes: true,
          useBase64URL: true,
        });

        if (cancelled) return;
        // Layout after paint
        requestAnimationFrame(() => {
          if (!cancelled) fitToPanel();
        });
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Could not render this DOCX. Download to open in Word."
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void renderDocx();
    return () => {
      cancelled = true;
      if (host) host.innerHTML = "";
    };
  }, [fileUrl, token]);

  useEffect(() => {
    const scroll = scrollRef.current;
    if (!scroll || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => {
      fitToPanel();
    });
    ro.observe(scroll);
    return () => ro.disconnect();
  }, [loading, fileUrl]);

  return (
    <div className={`relative flex-1 min-h-0 flex flex-col ${className || ""}`}>
      {loading && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/60 text-sm text-muted-foreground gap-2">
          <Loader2 className="w-4 h-4 animate-spin" /> Rendering Word layout…
        </div>
      )}
      {error && !loading && (
        <div className="p-6 text-sm text-center text-muted-foreground space-y-2">
          <p>{error}</p>
          <p className="text-xs">Use Text mode or Download for the original file.</p>
        </div>
      )}
      <div
        ref={scrollRef}
        className={`${styles["docx-preview-scroll"]} os-scrollbar`}
      >
        <div ref={hostRef} className={styles["docx-preview-host"]} />
      </div>
    </div>
  );
}
