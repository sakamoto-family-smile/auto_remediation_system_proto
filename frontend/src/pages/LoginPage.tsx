/**
 * ログインページ
 */

import React, { useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Container,
  Typography,
  Alert,
} from '@mui/material';
import { Google as GoogleIcon } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { FirebaseService } from '@/services/firebase';

export const LoginPage: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleGoogleLogin = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Googleサインイン
      const firebaseUser = await FirebaseService.signInWithGoogle();
      const idToken = await firebaseUser.getIdToken();

      // バックエンドにログイン
      await login(idToken);

      // ダッシュボードにリダイレクト
      navigate('/dashboard');
    } catch (error) {
      console.error('Login error:', error);
      setError('ログインに失敗しました。もう一度お試しください。');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Card sx={{ width: '100%', maxWidth: 400 }}>
          <CardContent sx={{ p: 4 }}>
            <Box sx={{ textAlign: 'center', mb: 4 }}>
              <Typography variant="h4" component="h1" gutterBottom>
                Auto Remediation System
              </Typography>
              <Typography variant="body1" color="text.secondary">
                エラー自動調査・改修システム
              </Typography>
            </Box>

            {error && (
              <Alert severity="error" sx={{ mb: 3 }}>
                {error}
              </Alert>
            )}

            <Button
              fullWidth
              variant="contained"
              size="large"
              startIcon={
                isLoading ? (
                  <CircularProgress size={20} color="inherit" />
                ) : (
                  <GoogleIcon />
                )
              }
              onClick={handleGoogleLogin}
              disabled={isLoading}
              sx={{
                py: 1.5,
                textTransform: 'none',
                fontSize: '1.1rem',
              }}
            >
              {isLoading ? 'ログイン中...' : 'Googleでログイン'}
            </Button>

            <Typography
              variant="caption"
              color="text.secondary"
              sx={{
                display: 'block',
                textAlign: 'center',
                mt: 3,
                px: 2,
              }}
            >
              ログインすることで、利用規約とプライバシーポリシーに同意したものとみなされます。
            </Typography>
          </CardContent>
        </Card>
      </Box>
    </Container>
  );
};
