/**
 * 認証プロバイダーコンポーネント
 */

import React, { ReactNode, useEffect, useState } from 'react';
import { User as FirebaseUser } from 'firebase/auth';
import { AuthContext } from '@/hooks/useAuth';
import { AuthState, User } from '@/types/auth';
import { apiService } from '@/services/api';
import { FirebaseService } from '@/services/firebase';

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    accessToken: null,
    isAuthenticated: false,
    isLoading: true,
  });

  useEffect(() => {
    // 認証状態の初期化
    const initAuth = async () => {
      const storedToken = localStorage.getItem('access_token');
      if (storedToken) {
        try {
          const userResponse = await apiService.getCurrentUser();
          const user: User = {
            id: userResponse.id,
            email: userResponse.email,
            role: userResponse.role,
            organizationId: userResponse.organization_id,
          };

          setAuthState({
            user,
            accessToken: storedToken,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (error) {
          console.error('Failed to get current user:', error);
          localStorage.removeItem('access_token');
          setAuthState({
            user: null,
            accessToken: null,
            isAuthenticated: false,
            isLoading: false,
          });
        }
      } else {
        setAuthState({
          user: null,
          accessToken: null,
          isAuthenticated: false,
          isLoading: false,
        });
      }
    };

    // Firebase認証状態の監視
    const unsubscribe = FirebaseService.onAuthStateChanged(
      (firebaseUser: FirebaseUser | null) => {
        if (!firebaseUser && authState.isAuthenticated) {
          // Firebaseからサインアウトされた場合
          logout();
        }
      }
    );

    initAuth();

    return () => unsubscribe();
  }, []);

  const login = async (firebaseToken: string): Promise<void> => {
    try {
      setAuthState((prev) => ({ ...prev, isLoading: true }));

      const tokenResponse = await apiService.login({ firebase_token: firebaseToken });

      // トークンをローカルストレージに保存
      localStorage.setItem('access_token', tokenResponse.access_token);

      const user: User = {
        id: tokenResponse.user.id,
        email: tokenResponse.user.email,
        role: tokenResponse.user.role,
        organizationId: tokenResponse.user.organization_id,
      };

      setAuthState({
        user,
        accessToken: tokenResponse.access_token,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error) {
      console.error('Login failed:', error);
      setAuthState({
        user: null,
        accessToken: null,
        isAuthenticated: false,
        isLoading: false,
      });
      throw error;
    }
  };

  const logout = (): void => {
    localStorage.removeItem('access_token');
    FirebaseService.signOut().catch(console.error);

    setAuthState({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      isLoading: false,
    });
  };

  const refreshToken = async (): Promise<void> => {
    try {
      const tokenResponse = await apiService.refreshToken();
      localStorage.setItem('access_token', tokenResponse.access_token);

      const user: User = {
        id: tokenResponse.user.id,
        email: tokenResponse.user.email,
        role: tokenResponse.user.role,
        organizationId: tokenResponse.user.organization_id,
      };

      setAuthState((prev) => ({
        ...prev,
        user,
        accessToken: tokenResponse.access_token,
      }));
    } catch (error) {
      console.error('Token refresh failed:', error);
      logout();
      throw error;
    }
  };

  const contextValue = {
    ...authState,
    login,
    logout,
    refreshToken,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};
