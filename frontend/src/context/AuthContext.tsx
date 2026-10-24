import React, { createContext, useContext, useState, useEffect } from 'react';
import { User } from '../types';
import { api } from '../api/client';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isMaster: boolean;
  login: (data: { login: string; password: string }) => Promise<void>;
  register: (data: {
    first_name: string;
    last_name?: string;
    phone?: string;
    email?: string;
    password: string;
    role?: 'client' | 'master';
  }) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  updateProfile: (data: Partial<User>) => Promise<void>;

  // Guest Auth Trigger Modal
  isAuthModalOpen: boolean;
  authModalActionReason: string;
  authModalMode: 'login' | 'register';
  openAuthModal: (reason?: string, mode?: 'login' | 'register') => void;
  closeAuthModal: () => void;

  // Geolocation
  userCoords: { lat: number; lng: number } | null;
  requestUserLocation: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState<boolean>(false);
  const [authModalActionReason, setAuthModalActionReason] = useState<string>('');
  const [authModalMode, setAuthModalMode] = useState<'login' | 'register'>('login');
  const [userCoords, setUserCoords] = useState<{ lat: number; lng: number } | null>(null);

  const fetchCurrentUser = async () => {
    try {
      if (localStorage.getItem('ustasi_access_token')) {
        const userData = await api.getMe();
        setUser(userData);
      } else {
        setUser(null);
      }
    } catch {
      setUser(null);
      api.clearTokens();
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCurrentUser();

    const handleAuthExpired = () => {
      setUser(null);
      setIsAuthModalOpen(true);
      setAuthModalActionReason("Sessiya muddati tugadi. Iltimos, qayta kiring.");
    };

    window.addEventListener('ustasi:auth_expired', handleAuthExpired);
    return () => window.removeEventListener('ustasi:auth_expired', handleAuthExpired);
  }, []);

  const login = async (data: { login: string; password: string }) => {
    const res = await api.login(data);
    api.setTokens(res.tokens.access, res.tokens.refresh);
    setUser(res.user);
    setIsAuthModalOpen(false);
  };

  const register = async (data: {
    first_name: string;
    last_name?: string;
    phone?: string;
    email?: string;
    password: string;
    role?: 'client' | 'master';
  }) => {
    const res = await api.register(data);
    api.setTokens(res.tokens.access, res.tokens.refresh);
    setUser(res.user);
    setIsAuthModalOpen(false);
  };

  const logout = () => {
    api.clearTokens();
    setUser(null);
  };

  const refreshUser = async () => {
    await fetchCurrentUser();
  };

  const updateProfile = async (data: Partial<User>) => {
    const updated = await api.updateMe(data);
    setUser(prev => prev ? { ...prev, ...updated } : updated);
  };

  const openAuthModal = (
    reason: string = "Ushbu amalni bajarish uchun tizimga kiring",
    mode: 'login' | 'register' = 'login'
  ) => {
    setAuthModalActionReason(reason);
    setAuthModalMode(mode);
    setIsAuthModalOpen(true);
  };

  const closeAuthModal = () => {
    setIsAuthModalOpen(false);
  };

  const requestUserLocation = () => {
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setUserCoords({
            lat: pos.coords.latitude,
            lng: pos.coords.longitude,
          });
        },
        (err) => {
          console.warn("Geolocation rad etildi yoki xatolik:", err.message);
          // Default fallback coordinates: Tashkent center
          setUserCoords({ lat: 41.2995, lng: 69.2401 });
        },
        { timeout: 8000 }
      );
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        isMaster: user?.role === 'master',
        login,
        register,
        logout,
        refreshUser,
        updateProfile,
        isAuthModalOpen,
        authModalActionReason,
        authModalMode,
        openAuthModal,
        closeAuthModal,
        userCoords,
        requestUserLocation,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
