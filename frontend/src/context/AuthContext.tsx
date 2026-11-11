import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { AuthSession, fetchAuthSession, loginDemoSession, logoutDemoSession } from '../api/auth';
import { AUTH_UNAUTHORIZED_EVENT, setCsrfToken } from '../api/client';
import { officeTransport } from '../features/virtual-office/services/officeTransport';

interface AuthContextValue {
  session: AuthSession | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const clearSessionState = useCallback(() => {
    setCsrfToken(null);
    setSession(null);
    officeTransport.disconnect();
  }, []);

  const refreshSession = useCallback(async () => {
    try {
      const current = await fetchAuthSession();
      setSession(current && current.authenticated ? current : null);
      if (!current || !current.authenticated) {
        officeTransport.disconnect();
      }
    } catch {
      clearSessionState();
    } finally {
      setIsLoading(false);
    }
  }, [clearSessionState]);

  useEffect(() => {
    refreshSession();
  }, [refreshSession]);

  useEffect(() => {
    const handleUnauthorized = () => {
      clearSessionState();
      setIsLoading(false);
    };

    window.addEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized);
    return () => {
      window.removeEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized);
    };
  }, [clearSessionState]);

  const login = useCallback(async (password: string) => {
    const authenticated = await loginDemoSession(password);
    setSession(authenticated);
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutDemoSession();
    } finally {
      clearSessionState();
    }
  }, [clearSessionState]);

  return (
    <AuthContext.Provider
      value={{
        session,
        isAuthenticated: Boolean(session?.authenticated),
        isLoading,
        login,
        logout,
        refreshSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}

