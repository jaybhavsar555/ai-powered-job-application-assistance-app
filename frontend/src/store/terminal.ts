import { create } from "zustand";
import { persist } from "zustand/middleware";

export type TerminalSize = "compact" | "default" | "tall" | "maximized";

interface TerminalUiState {
  open: boolean;
  size: TerminalSize;
  openTerminal: () => void;
  closeTerminal: () => void;
  toggleTerminal: () => void;
  setSize: (size: TerminalSize) => void;
  cycleSize: () => void;
}

const SIZE_ORDER: TerminalSize[] = ["compact", "default", "tall", "maximized"];

export const useTerminalStore = create<TerminalUiState>()(
  persist(
    (set, get) => ({
      open: true,
      size: "default",
      openTerminal: () => set({ open: true }),
      closeTerminal: () => set({ open: false }),
      toggleTerminal: () => set({ open: !get().open }),
      setSize: (size) => set({ open: true, size }),
      cycleSize: () => {
        const current = get().size;
        const idx = SIZE_ORDER.indexOf(current);
        const next = SIZE_ORDER[(idx + 1) % SIZE_ORDER.length];
        set({ open: true, size: next });
      },
    }),
    { name: "career-os-terminal-ui" }
  )
);
