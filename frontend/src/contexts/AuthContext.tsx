import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { AuthContextType } from '../types/api';

const AuthContext = createContext<AuthContextType | null>(null);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [user, setUser] = useState<string | null>(null);
  
  const login = (newToken: string) => {
    setToken(newToken);
    localStorage.setItem('token', newToken);
    
    // Decode token to get user info
    try {
      const payload = JSON.parse(atob(newToken.split('.')[1]));
      setUser(payload.sub);
    } catch (error) {
      console.error('Error decoding token:', error);
    }
  };
  
  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
  };
  
  const isAuthenticated = !!token;
  
  useEffect(() => {
    // Check token validity on mount
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const exp = payload.exp * 1000; // Convert to milliseconds
        
        if (Date.now() > exp) {
          logout(); // Token expired
        } else {
          setUser(payload.sub);
        }
      } catch (error) {
        logout(); // Invalid token
      }
    }
  }, [token]);
  
  return (
    <AuthContext.Provider value={{
      user,
      token,
      login,
      logout,
      isAuthenticated
    }}>
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
