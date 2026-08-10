import { create } from "zustand";

export type PanelTab = "inspector" | "pdf";

export type PreviewKind = "pdf" | "docx" | "text" | "unsupported";

export interface DocumentPreview {
  title: string;
  kind: PreviewKind;
  /** Authenticated API path for download / PDF blob fetch */
  fileUrl: string;
  /** Extracted text for DOCX/TXT */
  text?: string | null;
  note?: string | null;
}

interface PanelState {
  activeTab: PanelTab;
  /** @deprecated prefer preview — kept for callers that only set a static URL */
  pdfUrl: string | null;
  pdfTitle: string | null;
  preview: DocumentPreview | null;
  mobileOpen: boolean;
  setActiveTab: (tab: PanelTab) => void;
  setPdfUrl: (url: string | null, title?: string | null) => void;
  setPreview: (preview: DocumentPreview | null) => void;
  closePdf: () => void;
  openMobilePanel: (tab?: PanelTab) => void;
  closeMobilePanel: () => void;
}

export const usePanelStore = create<PanelState>((set) => ({
  activeTab: "inspector",
  pdfUrl: null,
  pdfTitle: null,
  preview: null,
  mobileOpen: false,
  setActiveTab: (tab) => set({ activeTab: tab, mobileOpen: true }),
  setPdfUrl: (url, title = null) =>
    set({
      pdfUrl: url,
      pdfTitle: url ? title : null,
      preview: url
        ? {
            title: title || "Document",
            kind: "pdf",
            fileUrl: url,
            text: null,
            note: null,
          }
        : null,
      activeTab: url ? "pdf" : "inspector",
      mobileOpen: !!url,
    }),
  setPreview: (preview) =>
    set({
      preview,
      pdfUrl: preview?.fileUrl ?? null,
      pdfTitle: preview?.title ?? null,
      activeTab: preview ? "pdf" : "inspector",
      mobileOpen: !!preview,
    }),
  closePdf: () =>
    set({
      pdfUrl: null,
      pdfTitle: null,
      preview: null,
      activeTab: "inspector",
    }),
  openMobilePanel: (tab) =>
    set((s) => ({
      mobileOpen: true,
      activeTab: tab ?? s.activeTab,
    })),
  closeMobilePanel: () => set({ mobileOpen: false }),
}));
