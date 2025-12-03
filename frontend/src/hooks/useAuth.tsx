import { useState, useEffect, useMemo, useCallback } from "react";
import type { ReactNode } from "react";
import { jwtDecode } from "jwt-decode";
import type { AuthState } from "../types/auth";
import { AuthContext } from "../contexts/AuthContext";
import type { AuthContextType } from "../contexts/AuthContext";
import { setAuthToken, clearAuthToken } from "../services/api/auth";

// Props interface for AuthProvider component - accepts child components to wrap with auth context
interface AuthProviderProps {
  readonly children: ReactNode; // Child components that will have access to auth context
}

// localStorage key for persisting auth state
const AUTH_STORAGE_KEY = "clash_royale_auth";

/**
 * Parse JWT token to extract expiration time using jwt-decode library
 * @param token JWT token string
 * @returns expiration timestamp in milliseconds, or null if parsing fails
 */
function parseJWTExpiration(token: string): number | null {
  try {
    const decoded = jwtDecode<{ exp?: number }>(token);

    // Extract exp claim (expiration time in seconds since Unix epoch)
    if (decoded.exp && typeof decoded.exp === "number") {
      return decoded.exp * 1000; // Convert to milliseconds
    }

    return null;
  } catch {
    return null;
  }
}

/**
 * Authentication provider component that manages auth state and persists it to localStorage
 */
export function AuthProvider({ children }: AuthProviderProps) {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
  });

  // Restore auth state from localStorage on app start
  useEffect(() => {
    const savedAuth = localStorage.getItem(AUTH_STORAGE_KEY);
    if (savedAuth) {
      try {
        const parsed: AuthState = JSON.parse(savedAuth);
        // Check if token is still valid (not expired)
        if (parsed.expiresAt && parsed.expiresAt > Date.now()) {
          setAuthState(parsed);
          if (parsed.authToken) {
            setAuthToken(parsed.authToken);
          }
        } else {
          // Token expired, clear it
          localStorage.removeItem(AUTH_STORAGE_KEY);
        }
      } catch {
        // Invalid saved data, clear it
        localStorage.removeItem(AUTH_STORAGE_KEY);
      }
    }
  }, []);

  // Login user with token, reading expiration from JWT or using fallback time
  const login = useCallback((token: string, expiresInMinutes = 30) => {
    // Try to parse actual expiration from JWT token
    const jwtExpiration = parseJWTExpiration(token);
    const expiresAt =
      jwtExpiration || Date.now() + expiresInMinutes * 60 * 1000;

    const newAuthState: AuthState = {
      isAuthenticated: true,
      authToken: token,
      expiresAt,
    };

    setAuthState(newAuthState);
    setAuthToken(token);
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(newAuthState));
  }, []);

  // Logout user and clear all auth data
  const logout = useCallback(() => {
    setAuthState({ isAuthenticated: false });
    clearAuthToken();
    localStorage.removeItem(AUTH_STORAGE_KEY);
  }, []);

  // Check if user is authenticated and token hasn't expired
  const checkAuthStatus = useCallback((): boolean => {
    if (!authState.isAuthenticated || !authState.expiresAt) {
      return false;
    }

    // Check if token is expired
    if (authState.expiresAt <= Date.now()) {
      logout(); // Auto-logout expired tokens
      return false;
    }

    return true;
  }, [authState.isAuthenticated, authState.expiresAt, logout]);

  // Memoized context value to prevent unnecessary re-renders
  const contextValue: AuthContextType = useMemo(
    () => ({
      ...authState,
      login,
      logout,
      checkAuthStatus,
    }),
    [authState, login, logout, checkAuthStatus]
  );

  // Wrap children with AuthContext.Provider to make auth state available to all child components
  return (
    <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>
  );
}
