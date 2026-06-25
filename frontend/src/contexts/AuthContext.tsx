import React, { createContext, useContext, useState, useEffect } from "react";
import { api } from "../services/api";

interface UserProfile {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
}

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
  error: string | null;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // 1. Verify token and load user profile on mount
  useEffect(() => {
    const initializeAuth = async () => {
      const savedToken = localStorage.getItem("token");
      if (savedToken) {
        try {
          const profile = await api.getMe(savedToken);
          setToken(savedToken);
          setUser(profile);
        } catch (err) {
          console.error("Token verification failed, clearing credentials", err);
          localStorage.removeItem("token");
        }
      }
      setLoading(false);
    };
    initializeAuth();
  }, []);

  const login = async (email: string, password: string) => {
    setError(null);
    setLoading(true);
    try {
      const formData = new URLSearchParams();
      formData.append("username", email); // OAuth2PasswordRequestForm expects username
      formData.append("password", password);
      
      const response = await api.login(formData);
      const accessToken = response.access_token;
      
      // Store token on disk
      localStorage.setItem("token", accessToken);
      setToken(accessToken);
      
      // Fetch full user profile
      const profile = await api.getMe(accessToken);
      setUser(profile);
    } catch (err: any) {
      setError(err.message || "Login failed. Please check your credentials.");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const register = async (email: string, password: string, fullName: string) => {
    setError(null);
    setLoading(true);
    try {
      await api.register({
        email,
        password,
        full_name: fullName,
      });
      // Automatically log in the user after successful registration
      await login(email, password);
    } catch (err: any) {
      setError(err.message || "Registration failed.");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem("token");
    setToken(null);
    setUser(null);
    setError(null);
  };

  const clearError = () => setError(null);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login,
        register,
        logout,
        error,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
