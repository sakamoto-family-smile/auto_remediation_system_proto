/**
 * 認証フック
 */

import { createContext, useContext } from 'react';
import { AuthContextType } from '@/types/auth';

export const AuthContext = createContext<AuthContextType | null>(null);

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
