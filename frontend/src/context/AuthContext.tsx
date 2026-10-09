import React, { createContext, useContext, useState, useEffect } from 'react';
import { UserSession, getStoredUser, getStoredToken, AuthService, setOnUnauthorizedListener } from '../services/api';

interface AuthContextType {
  user: UserSession | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<UserSession>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserSession | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    // Initial load from local session
    const storedUser = getStoredUser();
    const storedToken = getStoredToken();
    if (storedUser && storedToken) {
      setUser(storedUser);
      setToken(storedToken);
    }
    setIsLoading(false);

    // Register token expiration / 401 callback
    setOnUnauthorizedListener(() => {
      setUser(null);
      setToken(null);
    });
  }, []);

  const login = async (username: string, password: string): Promise<UserSession> => {
    setIsLoading(true);
    try {
      const session = await AuthService.login(username, password);
      setUser(session);
      setToken(session.token);
      return session;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    AuthService.logout();
    setUser(null);
    setToken(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user && !!token,
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
