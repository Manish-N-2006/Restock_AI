const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  
  const headers = {
    'Content-Type': 'application/json',
    'X-ReStockAI-User': 'manager', // Default to manager role for Cedar Authorization
    ...options.headers,
  };
  
  const response = await fetch(url, { ...options, headers });
  
  if (!response.ok) {
    let errorMsg = `API Error: ${response.status} ${response.statusText}`;
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        errorMsg = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
      }
    } catch (e) {
      // If parsing fails, use standard error message
    }
    throw new Error(errorMsg);
  }
  
  return response.json() as Promise<T>;
}
