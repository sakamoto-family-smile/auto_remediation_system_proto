/**
 * 認証関連型定義
 */

export interface User {
  id: string;
  email: string;
  role: string;
  organizationId?: string;
}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface AuthContextType extends AuthState {
  login: (firebaseToken: string) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
}
