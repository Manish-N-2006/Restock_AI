import { apiFetch, setCsrfToken } from './client';

export interface AuthSession {
  authenticated: boolean;
  user: string;
  role: string;
  expires_at: number;
  csrf_token?: string;
}

export async function fetchAuthSession(): Promise<AuthSession | null> {
  const res = await apiFetch('/api/auth/session', {
    method: 'GET',
    skipAuthRedirect: true,
  });

  if (res.status === 401) {
    setCsrfToken(null);
    return null;
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Session check failed (${res.status})`);
  }

  const data = (await res.json()) as AuthSession;
  setCsrfToken(data.csrf_token || null);
  return data;
}

export async function loginDemoSession(password: string): Promise<AuthSession> {
  const res = await apiFetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
    skipAuthRedirect: true,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Authentication failed');
  }

  const data = (await res.json()) as AuthSession;
  setCsrfToken(data.csrf_token || null);
  return data;
}

export async function logoutDemoSession(): Promise<void> {
  try {
    await apiFetch('/api/auth/logout', {
      method: 'POST',
      skipAuthRedirect: true,
    });
  } finally {
    setCsrfToken(null);
  }
}
