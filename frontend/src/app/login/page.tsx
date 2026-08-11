"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { useAuthStore } from "@/store/auth";
import { getApiErrorMessage } from "@/lib/api";

const API = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

type SeedAccount = { role: string; email: string; password: string };

export default function LoginPage() {
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("demo@example.com");
  const [password, setPassword] = useState("Demo1234!");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [accounts, setAccounts] = useState<SeedAccount[]>([]);

  useEffect(() => {
    axios
      .get<{ accounts: SeedAccount[] }>(`${API}/auth/credentials`)
      .then((r) => setAccounts(r.data.accounts || []))
      .catch(() => setAccounts([]));
  }, []);

  const applyAuth = (data: {
    access_token: string;
    user_id: string;
    email: string;
    role?: string;
  }) => {
    setAuth(data.access_token, {
      id: data.user_id,
      email: data.email,
      role: data.role || "user",
    });
    router.push("/canvas");
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const path = mode === "login" ? "/auth/login" : "/auth/register";
      const { data } = await axios.post(`${API}${path}`, { email, password });
      applyAuth(data);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, mode === "login" ? "Login failed" : "Register failed"));
    } finally {
      setBusy(false);
    }
  };

  const useDemo = async () => {
    setBusy(true);
    setError(null);
    try {
      const { data } = await axios.post(`${API}/auth/demo`);
      applyAuth(data);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Demo login failed"));
    } finally {
      setBusy(false);
    }
  };

  const fillAccount = (acct: SeedAccount) => {
    setMode("login");
    setEmail(acct.email);
    setPassword(acct.password);
    setError(null);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4 py-8">
      <div className="w-full max-w-md border border-border rounded-2xl bg-card p-6 space-y-5 shadow-xl">
        <div className="space-y-1">
          <div className="h-9 w-9 rounded-lg bg-primary text-primary-foreground flex items-center justify-center font-bold">
            OS
          </div>
          <h1 className="text-2xl font-bold tracking-tight pt-2">
            {mode === "login" ? "Sign in" : "Create account"}
          </h1>
          <p className="text-sm text-muted-foreground">
            Phase 12 auth — roles: admin · demo · user
          </p>
        </div>

        {accounts.length > 0 && (
          <div className="rounded-lg border border-border bg-muted/30 p-3 space-y-2">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              Seed accounts (click to fill)
            </p>
            {accounts.map((acct) => (
              <button
                key={acct.email}
                type="button"
                onClick={() => fillAccount(acct)}
                className="w-full text-left text-xs rounded-md px-2 py-1.5 hover:bg-muted transition-colors font-mono"
              >
                <span className="text-sky-400">{acct.role}</span>
                {" · "}
                {acct.email}
                {" / "}
                <span className="text-muted-foreground">{acct.password}</span>
              </button>
            ))}
          </div>
        )}

        <form onSubmit={submit} className="space-y-3">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-primary"
          />
          <input
            type="password"
            required
            minLength={mode === "register" ? 8 : 1}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={mode === "register" ? "Password (min 8 chars)" : "Password"}
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-primary"
          />
          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-md bg-primary text-primary-foreground py-2.5 text-sm font-medium disabled:opacity-50"
          >
            {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Register"}
          </button>
        </form>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <button
            type="button"
            className="hover:text-foreground underline"
            onClick={() => setMode(mode === "login" ? "register" : "login")}
          >
            {mode === "login" ? "Need an account? Register" : "Have an account? Sign in"}
          </button>
          <button type="button" className="hover:text-foreground underline" onClick={useDemo} disabled={busy}>
            Continue as demo
          </button>
        </div>
      </div>
    </div>
  );
}
