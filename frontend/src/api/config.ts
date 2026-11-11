const rawApiBase = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '');
const isLoopbackUrl = /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/i.test(rawApiBase);

// In Vite local dev, prefer same-origin relative /api & /ws proxy paths so HttpOnly
// SameSite=Lax cookies and WebSocket upgrades work identically on localhost or 127.0.0.1.
export const API_BASE_URL =
  import.meta.env.DEV && isLoopbackUrl ? '' : rawApiBase;

export function apiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return API_BASE_URL ? `${API_BASE_URL}${normalizedPath}` : normalizedPath;
}

export function resolveWsUrl(): string {
  const explicitWs = (import.meta.env.VITE_WS_URL || '').trim().replace(/\/+$/, '');
  const isExplicitLoopbackWs = /^wss?:\/\/(localhost|127\.0\.0\.1)(:\d+)?/i.test(explicitWs);

  if (explicitWs && !(import.meta.env.DEV && isExplicitLoopbackWs)) {
    return explicitWs.endsWith('/ws/office') || explicitWs.endsWith('/ws')
      ? explicitWs
      : `${explicitWs}/ws/office`;
  }
  if (API_BASE_URL && /^https?:\/\//i.test(API_BASE_URL)) {
    return `${API_BASE_URL.replace(/^http:/i, 'ws:').replace(/^https:/i, 'wss:')}/ws/office`;
  }
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}/ws/office`;
  }
  return '';
}
