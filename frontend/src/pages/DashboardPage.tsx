/**
 * ダッシュボードページ
 */

import React, { useState } from 'react';
import {
  AppBar,
  Box,
  Button,
  Container,
  Grid,
  IconButton,
  Menu,
  MenuItem,
  Paper,
  Toolbar,
  Typography,
  Card,
  CardContent,
  CardActions,
  Chip,
} from '@mui/material';
import {
  AccountCircle,
  Chat as ChatIcon,
  Error as ErrorIcon,
  Build as BuildIcon,
  Analytics as AnalyticsIcon,
} from '@mui/icons-material';
import { useAuth } from '@/hooks/useAuth';
import { useNavigate } from 'react-router-dom';

export const DashboardPage: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const handleMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
    handleClose();
  };

  const navigateToChat = () => {
    navigate('/chat');
  };

  const navigateToErrors = () => {
    navigate('/errors');
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      {/* ヘッダー */}
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Auto Remediation System
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <Typography variant="body2" sx={{ mr: 2 }}>
              {user?.email}
            </Typography>
            <Chip
              label={user?.role}
              size="small"
              color="secondary"
              sx={{ mr: 2 }}
            />
            <IconButton
              size="large"
              aria-label="account of current user"
              aria-controls="menu-appbar"
              aria-haspopup="true"
              onClick={handleMenu}
              color="inherit"
            >
              <AccountCircle />
            </IconButton>
            <Menu
              id="menu-appbar"
              anchorEl={anchorEl}
              anchorOrigin={{
                vertical: 'top',
                horizontal: 'right',
              }}
              keepMounted
              transformOrigin={{
                vertical: 'top',
                horizontal: 'right',
              }}
              open={Boolean(anchorEl)}
              onClose={handleClose}
            >
              <MenuItem onClick={handleLogout}>ログアウト</MenuItem>
            </Menu>
          </Box>
        </Toolbar>
      </AppBar>

      {/* メインコンテンツ */}
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          ダッシュボード
        </Typography>

        <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
          エラー自動調査・改修システムへようこそ
        </Typography>

        <Grid container spacing={3}>
          {/* チャット機能 */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <ChatIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6" component="h2">
                    AIチャット
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Claude Sonnet-4と対話してコードの問題を解決
                </Typography>
              </CardContent>
              <CardActions>
                <Button
                  size="small"
                  variant="contained"
                  onClick={navigateToChat}
                  startIcon={<ChatIcon />}
                >
                  チャットを開始
                </Button>
              </CardActions>
            </Card>
          </Grid>

          {/* エラー管理 */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <ErrorIcon color="error" sx={{ mr: 1 }} />
                  <Typography variant="h6" component="h2">
                    エラー管理
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  システムエラーの監視と管理
                </Typography>
              </CardContent>
              <CardActions>
                <Button
                  size="small"
                  variant="outlined"
                  onClick={navigateToErrors}
                  startIcon={<ErrorIcon />}
                >
                  エラー一覧
                </Button>
              </CardActions>
            </Card>
          </Grid>

          {/* 自動改修 */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <BuildIcon color="warning" sx={{ mr: 1 }} />
                  <Typography variant="h6" component="h2">
                    自動改修
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  cursor-cliによる自動コード修正
                </Typography>
                <Chip
                  label="開発中"
                  size="small"
                  color="warning"
                  sx={{ mt: 1 }}
                />
              </CardContent>
              <CardActions>
                <Button size="small" disabled startIcon={<BuildIcon />}>
                  近日公開
                </Button>
              </CardActions>
            </Card>
          </Grid>

          {/* 分析・レポート */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <AnalyticsIcon color="info" sx={{ mr: 1 }} />
                  <Typography variant="h6" component="h2">
                    分析・レポート
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  エラー傾向とシステム改善提案
                </Typography>
                <Chip
                  label="開発中"
                  size="small"
                  color="info"
                  sx={{ mt: 1 }}
                />
              </CardContent>
              <CardActions>
                <Button size="small" disabled startIcon={<AnalyticsIcon />}>
                  近日公開
                </Button>
              </CardActions>
            </Card>
          </Grid>
        </Grid>

        {/* 統計情報 */}
        <Paper sx={{ p: 3, mt: 4 }}>
          <Typography variant="h6" component="h3" gutterBottom>
            システム状況
          </Typography>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={4}>
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="h4" color="primary">
                  0
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  アクティブなエラー
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="h4" color="success.main">
                  0
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  改修済みエラー
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="h4" color="info.main">
                  0
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  チャットセッション
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </Paper>
      </Container>
    </Box>
  );
};
