"use client";

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider as NextThemesProvider } from 'next-themes';
import { type ThemeProviderProps } from 'next-themes/dist/types';
import { useEffect, useState } from 'react';
import { ensureDemoAuth } from '@/lib/api';
import { useAuthStore } from '@/store/auth';

function AuthBootstrap({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const token = useAuthStore((s) => s.token);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        // Prefer existing session (email login). Only auto-demo when none.
        if (!useAuthStore.getState().token) {
          await ensureDemoAuth();
        }
      } catch (e) {
        console.warn('[AuthBootstrap] demo login failed — is the API running?', e);
      } finally {
        if (!cancelled) setReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (!ready) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background text-muted-foreground text-sm">
        Connecting to Career OS…
      </div>
    );
  }

  return <>{children}</>;
}

export function Providers({ children, ...props }: ThemeProviderProps) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000,
        retry: 1,
      },
    },
  }));

  return (
    <NextThemesProvider {...props}>
      <QueryClientProvider client={queryClient}>
        <AuthBootstrap>{children}</AuthBootstrap>
      </QueryClientProvider>
    </NextThemesProvider>
  );
}
