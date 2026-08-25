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
      onRehydrateStorage: () => (state, error) => {
        if (error) {
          console.warn('[auth] persist rehydrate failed', error);
        }
        // Always mark hydrated so bootstrap cannot wait forever.
        useAuthStore.getState().setHasHydrated(true);
        if (state) {
          // no-op: persist already merged token/user
        }
      },
    }
  )
);

function alreadyHydrated(): boolean {
  return (
    useAuthStore.getState().hasHydrated ||
    Boolean(useAuthStore.persist?.hasHydrated?.())
  );
}

/**
 * Wait until localStorage session has been read.
 * Resolves immediately if already done; never waits more than `timeoutMs`.
 */
export function waitForAuthHydration(timeoutMs = 800): Promise<void> {
  if (alreadyHydrated()) {
    useAuthStore.getState().setHasHydrated(true);
    return Promise.resolve();
  }

  return new Promise((resolve) => {
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      useAuthStore.getState().setHasHydrated(true);
      resolve();
    };

    const unsubFinish = useAuthStore.persist.onFinishHydration(() => {
      unsubFinish();
      finish();
    });
    const unsubStore = useAuthStore.subscribe((s) => {
      if (s.hasHydrated) {
        unsubStore();
        finish();
      }
    });

    // Race: hydration may complete between the first check and the listeners.
    if (alreadyHydrated()) {
      unsubFinish();
      unsubStore();
      finish();
      return;
    }

    window.setTimeout(() => {
      unsubFinish();
      unsubStore();
      finish();
    }, timeoutMs);
  });
}
