"use client";

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, useState, type ReactNode } from 'react';
import { ensureValidSession } from '@/lib/api';

function AuthBootstrap({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let done = false;
    const markReady = () => {
      if (done) return;
      done = true;
      setReady(true);
    };

    // Never block the UI if persist/API hangs (proxy to :8001, Strict Mode remount).
    const failOpen = window.setTimeout(markReady, 2_000);

    void (async () => {
      try {
        await ensureValidSession();
      } catch (e) {
        console.warn('[AuthBootstrap] session check failed — is the API running?', e);
      } finally {
        window.clearTimeout(failOpen);
        markReady();
      }
    })();

    return () => {
      window.clearTimeout(failOpen);
    };
  }, []);

  if (!ready) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background text-muted-foreground text-sm">
        Connecting to Career OS…
      </div>
    );
  }

  return <>{children}</>;
}

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            retry: 1,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <AuthBootstrap>{children}</AuthBootstrap>
    </QueryClientProvider>
  );
}
