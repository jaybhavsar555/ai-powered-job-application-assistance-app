import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: string;
  email: string;
  role?: string;
}

interface AuthState {
  token: string | null;
  user: User | null;
  hasHydrated: boolean;
  setAuth: (token: string, user: User) => void;
  logout: () => void;
  setHasHydrated: (value: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      hasHydrated: false,
      setAuth: (token, user) => set({ token, user }),
      logout: () => set({ token: null, user: null }),
      setHasHydrated: (value) => set({ hasHydrated: value }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ token: state.token, user: state.user }),
      onRehydrateStorage: () => () => {
        // Defer so `useAuthStore` is fully assigned (TDZ-safe). Do not use
        // `.persist` APIs here — they can be missing under Turbopack/HMR.
        setTimeout(() => {
          useAuthStore.setState({ hasHydrated: true });
        }, 0);
      },
    }
  )
);

/**
 * Wait until localStorage session has been read.
 * Never touches `store.persist` (undefined under some Turbopack loads).
 */
export function waitForAuthHydration(timeoutMs = 800): Promise<void> {
  if (useAuthStore.getState().hasHydrated) {
    return Promise.resolve();
  }

  return new Promise((resolve) => {
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      useAuthStore.setState({ hasHydrated: true });
      resolve();
    };

    const unsub = useAuthStore.subscribe((s) => {
      if (s.hasHydrated) {
        unsub();
        finish();
      }
    });

    if (useAuthStore.getState().hasHydrated) {
      unsub();
      finish();
      return;
    }

    setTimeout(() => {
      unsub();
      finish();
    }, timeoutMs);
  });
}
