import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type WorkspaceMode = 'simple' | 'advanced';

interface ModeState {
  mode: WorkspaceMode;
  setMode: (mode: WorkspaceMode) => void;
  toggleMode: () => void;
}

export const useModeStore = create<ModeState>()(
  persist(
    (set) => ({
      mode: 'simple',
      setMode: (mode) => set({ mode }),
      toggleMode: () => set((state) => ({ mode: state.mode === 'simple' ? 'advanced' : 'simple' })),
    }),
    {
      name: 'workspace-mode-storage',
    }
  )
);
