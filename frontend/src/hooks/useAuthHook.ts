import { useContext } from "react";
import { AuthContext } from "../contexts/AuthContext";
import type { AuthContextType } from "../contexts/AuthContext";

/**
 * Custom hook for accessing authentication context
 *
 * This hook provides a type-safe way to access the authentication state
 * and actions throughout the application. It automatically handles the
 * context validation and throws an error if used outside of an AuthProvider.
 *
 * @returns {AuthContextType} The authentication context containing:
 *   - Authentication state (user data, isAuthenticated, etc.)
 *   - login(): Function to authenticate a user
 *   - logout(): Function to sign out the current user
 *   - checkAuthStatus(): Function to verify authentication status
 *
 * @throws {Error} When used outside of an AuthProvider component
 *
 */
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);

  // Ensure the hook is used within an AuthProvider
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }

  return context;
}
