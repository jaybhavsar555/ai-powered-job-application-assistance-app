import axios, { type InternalAxiosRequestConfig } from 'axios';
import { useAuthStore, waitForAuthHydration } from '@/store/auth';

/** Same-origin /api/v1 → Next rewrite → Docker backend :8001 */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api/v1';
const API_BASE = API_BASE_URL;

const AUTH_TIMEOUT_MS = 6_000;

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30_000,
  headers: {
    'Content-Type': 'application/json',
  },
});

function isAuthEndpoint(url?: string): boolean {
  if (!url) return false;
  return /\/auth\/(login|register|demo|me|credentials)/.test(url);
}

let sessionRefresh: Promise<string | null> | null = null;

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error.response?.status;
    const original = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;
    if (status !== 401 || !original || original._retry || isAuthEndpoint(original.url)) {
      return Promise.reject(error);
    }
    original._retry = true;
    const nextToken = await refreshSession();
    if (!nextToken) {
      return Promise.reject(error);
    }
    original.headers = original.headers || {};
    original.headers.Authorization = `Bearer ${nextToken}`;
    return api.request(original);
  }
);

/** Human-readable message from axios / fetch failures */
export function getApiErrorMessage(err: unknown, fallback = 'Request failed'): string {
  if (!err || typeof err !== 'object') return fallback;
  const anyErr = err as {
    message?: string;
    code?: string;
    response?: { status?: number; data?: { detail?: string } };
  };
  const detail = anyErr.response?.data?.detail;
  if (detail && /could not validate credentials/i.test(String(detail))) {
    return 'Session expired — sign in again (or wait a moment for a new demo session).';
  }
  if (detail) return String(detail);
  if (anyErr.response?.status === 401 || anyErr.response?.status === 403) {
    return 'Not authenticated — sign in again.';
  }
  if (anyErr.response?.status && anyErr.response.status >= 500) {
    return `API error ${anyErr.response.status} — check Docker backend on :8001`;
  }
  if (anyErr.message === 'Network Error' || anyErr.code === 'ERR_NETWORK') {
    return 'Cannot reach API — is Docker backend up? (docker compose up -d api)';
  }
  if (anyErr.message) return anyErr.message;
  return fallback;
}

export function authHeaders(): Record<string, string> {
  const token = useAuthStore.getState().token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function applyTokenResponse(data: {
  access_token: string;
  user_id?: string;
  id?: string;
  email: string;
  role?: string;
}): Promise<string> {
  const id = data.user_id || data.id || '';
  useAuthStore.getState().setAuth(data.access_token, {
    id,
    email: data.email,
    role: data.role,
  });
  return data.access_token;
}

export async function ensureDemoAuth(force = false): Promise<string | null> {
  const existing = useAuthStore.getState().token;
  if (existing && !force) return existing;

  const { data } = await axios.post<{
    access_token: string;
    user_id: string;
    email: string;
    role?: string;
  }>(`${API_BASE}/auth/demo`, null, { timeout: AUTH_TIMEOUT_MS });

  return applyTokenResponse(data);
}

async function tokenIsValid(token: string): Promise<boolean> {
  try {
    const { data } = await axios.get<{
      id: string;
      email: string;
      role?: string;
    }>(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      timeout: AUTH_TIMEOUT_MS,
    });
    useAuthStore.getState().setAuth(token, {
      id: data.id,
      email: data.email,
      role: data.role,
    });
    return true;
  } catch (err) {
    if (axios.isAxiosError(err) && err.response?.status === 401) {
      return false;
    }
    // Network / API down / timeout — keep the stored token; pages will show connection errors.
    return true;
  }
}

/** Single-flight refresh used by axios + fetch after a 401. */
export async function refreshSession(): Promise<string | null> {
  if (!sessionRefresh) {
    sessionRefresh = (async () => {
      try {
        return await ensureDemoAuth(true);
      } catch {
        useAuthStore.getState().logout();
        return null;
      } finally {
        sessionRefresh = null;
      }
    })();
  }
  return sessionRefresh;
}

/**
 * After persist hydration: keep a valid JWT, or mint a demo session if the
 * stored token is missing/expired (SECRET_KEY change, Docker rebuild, etc.).
 */
export async function ensureValidSession(): Promise<string | null> {
  await waitForAuthHydration();
  const token = useAuthStore.getState().token;
  if (token && (await tokenIsValid(token))) {
    return token;
  }
  if (token) {
    useAuthStore.getState().logout();
  }
  try {
    return await ensureDemoAuth(true);
  } catch {
    return null;
  }
}

/** fetch() with Authorization + one retry after a 401 (stale JWT). */
export async function apiFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  const token = useAuthStore.getState().token;
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  let res = await fetch(input, { ...init, headers });
  if (res.status === 401 && !isAuthEndpoint(input)) {
    const next = await refreshSession();
    if (next) {
      headers.set('Authorization', `Bearer ${next}`);
      res = await fetch(input, { ...init, headers });
    }
  }
  return res;
}

export default api;
