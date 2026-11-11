import { apiUrl } from './config';

export const AUTH_UNAUTHORIZED_EVENT = 'restockai:unauthorized';
const MUTATING_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

let csrfTokenInMemory: string | null = null;

export function setCsrfToken(token: string | null): void {
  csrfTokenInMemory = token && token.trim() ? token.trim() : null;
}

export function getCsrfToken(): string | null {
  return csrfTokenInMemory;
}

export interface ApiRequestInit extends RequestInit {
  skipAuthRedirect?: boolean;
}

export async function apiFetch(endpoint: string, options: ApiRequestInit = {}): Promise<Response> {
  const { skipAuthRedirect = false, ...fetchOptions } = options;
  const url = apiUrl(endpoint);
  const method = (fetchOptions.method || 'GET').toUpperCase();
  const headers = new Headers(fetchOptions.headers || {});

  if (MUTATING_METHODS.has(method)) {
    if (!headers.has('Content-Type') && !(fetchOptions.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json');
    }
    if (csrfTokenInMemory && !endpoint.startsWith('/api/auth/login') && !headers.has('X-CSRF-Token')) {
      headers.set('X-CSRF-Token', csrfTokenInMemory);
    }
  }

  const response = await fetch(url, {
    ...fetchOptions,
    method,
    headers,
    credentials: 'include',
  });

  if (response.status === 401 && !skipAuthRedirect && typeof window !== 'undefined') {
    setCsrfToken(null);
    window.dispatchEvent(new CustomEvent(AUTH_UNAUTHORIZED_EVENT));
  }

  return response;
}

export async function fetchApi<T>(endpoint: string, options: ApiRequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await apiFetch(endpoint, { ...options, headers });

  if (!response.ok) {
    let errorMsg = `API Error: ${response.status} ${response.statusText}`;
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        errorMsg = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
      }
    } catch {
      // If parsing fails, use standard error message
    }
    throw new Error(errorMsg);
  }

  return response.json() as Promise<T>;
}
