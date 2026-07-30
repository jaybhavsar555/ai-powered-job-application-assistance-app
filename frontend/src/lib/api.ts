import axios from 'axios';
import { useAuthStore } from '@/store/auth';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
    }
    return Promise.reject(error);
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
  if (anyErr.response?.data?.detail) return String(anyErr.response.data.detail);
  if (anyErr.response?.status === 401 || anyErr.response?.status === 403) {
    return 'Not authenticated — refreshing demo session…';
  }
  if (anyErr.response?.status && anyErr.response.status >= 500) {
    return `API error ${anyErr.response.status} — check backend logs on :8001`;
  }
  if (anyErr.message === 'Network Error' || anyErr.code === 'ERR_NETWORK') {
    return 'Cannot reach API (is the backend running on :8001?)';
  }
  if (anyErr.message) return anyErr.message;
  return fallback;
}

export async function ensureDemoAuth(force = false): Promise<string | null> {
  const existing = useAuthStore.getState().token;
  if (existing && !force) return existing;

  const base = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api/v1';
  const { data } = await axios.post<{
    access_token: string;
    user_id: string;
    email: string;
  }>(`${base}/auth/demo`);

  useAuthStore.getState().setAuth(data.access_token, {
    id: data.user_id,
    email: data.email,
  });
  return data.access_token;
}

export default api;
