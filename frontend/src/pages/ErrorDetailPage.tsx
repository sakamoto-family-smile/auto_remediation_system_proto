/**
 * エラー詳細ページ
 */

import React, { useState, useEffect } from 'react';
import {
  AppBar,
  Box,
  Button,
  Card,
  CardContent,
  CardActions,
  Chip,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  IconButton,
  Paper,
  Tab,
  Tabs,
  Toolbar,
  Typography,
  Alert,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  BugReport as BugIcon,
  Build as BuildIcon,
  Code as CodeIcon,
  Timeline as TimelineIcon,
  Assessment as AssessmentIcon,
  GitHub as GitHubIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { apiService } from '@/services/api';
import { ErrorIncidentResponse, RemediationResponse } from '@/types/api';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <div hidden={value !== index}>
    {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
  </div>
);

export const ErrorDetailPage: React.FC = () => {
  const { incidentId } = useParams<{ incidentId: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();

  // State
  const [incident, setIncident] = useState<ErrorIncidentResponse | null>(null);
  const [remediationAttempts, setRemediationAttempts] = useState<RemediationResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);
  const [analyzing, setAnalyzing] = useState(false);
  const [remediating, setRemediating] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [remediationDialogOpen, setRemediationDialogOpen] = useState(false);

  // データ取得
  const fetchIncidentDetails = async () => {
    if (!incidentId) return;

    try {
      setLoading(true);
      setError(null);

      const incidentData = await apiService.getErrorIncident(incidentId);
      setIncident(incidentData);

      // TODO: 改修試行履歴の取得APIを実装後に追加
      // const attempts = await apiService.getRemediationAttempts(incidentId);
      // setRemediationAttempts(attempts);

    } catch (err) {
      console.error('Failed to fetch incident details:', err);
      setError('エラーインシデントの詳細取得に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidentDetails();
  }, [incidentId]);

  // イベントハンドラー
  const handleBack = () => {
    navigate('/errors');
  };

  const handleAnalyze = async () => {
    if (!incidentId) return;

    try {
      setAnalyzing(true);
      const result = await apiService.analyzeError({ incident_id: incidentId });
      setAnalysisResult(result);
      setTabValue(1); // 解析結果タブに切り替え
    } catch (err) {
      console.error('Failed to analyze incident:', err);
      setError('エラー解析に失敗しました');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleRemediate = async () => {
    if (!incidentId) return;

    try {
      setRemediating(true);
      const _result = await apiService.remediateError({ incident_id: incidentId });

      // 改修結果を表示
      setRemediationDialogOpen(true);

      // データを再取得
      await fetchIncidentDetails();

    } catch (err) {
      console.error('Failed to remediate incident:', err);
      setError('エラー改修に失敗しました');
    } finally {
      setRemediating(false);
    }
  };

  const handleStatusUpdate = async (newStatus: string) => {
    if (!incidentId) return;

    try {
      await apiService.updateIncidentStatus(incidentId, newStatus);
      await fetchIncidentDetails(); // データ再取得
    } catch (err) {
      console.error('Failed to update status:', err);
      setError('ステータス更新に失敗しました');
    }
  };

  // 重要度の色を取得
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'error';
      case 'high': return 'warning';
      case 'medium': return 'info';
      case 'low': return 'success';
      default: return 'default';
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!incident) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">エラーインシデントが見つかりません</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* ヘッダー */}
      <AppBar position="static">
        <Toolbar>
          <IconButton
            edge="start"
            color="inherit"
            onClick={handleBack}
            sx={{ mr: 2 }}
          >
            <ArrowBackIcon />
          </IconButton>
          <BugIcon sx={{ mr: 1 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            エラー詳細: {incident.error_type}
          </Typography>
          <Typography variant="body2" sx={{ mr: 2 }}>
            {user?.email}
          </Typography>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ flexGrow: 1, py: 2 }}>
        {/* エラー表示 */}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* 基本情報カード */}
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Grid container spacing={2}>
              <Grid item xs={12} md={8}>
                <Typography variant="h5" gutterBottom>
                  {incident.error_type}
                </Typography>
                <Typography variant="body1" color="text.secondary" paragraph>
                  {incident.error_message}
                </Typography>

                <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                  <Chip
                    label={incident.severity}
                    color={getSeverityColor(incident.severity) as any}
                  />
                  <Chip label={incident.status} variant="outlined" />
                  <Chip label={incident.environment} variant="outlined" />
                  <Chip label={incident.service_name} variant="outlined" />
                </Box>
              </Grid>

              <Grid item xs={12} md={4}>
                <Typography variant="subtitle2" color="text.secondary">
                  発生回数
                </Typography>
                <Typography variant="h4" color="error">
                  {incident.occurrence_count}
                </Typography>

                <Typography variant="subtitle2" color="text.secondary" sx={{ mt: 1 }}>
                  最終発生時刻
                </Typography>
                <Typography variant="body2">
                  {new Date(incident.last_occurred).toLocaleString('ja-JP')}
                </Typography>
              </Grid>
            </Grid>
          </CardContent>

          <CardActions>
            <Button
              startIcon={<AssessmentIcon />}
              onClick={handleAnalyze}
              disabled={analyzing}
              color="info"
            >
              {analyzing ? <CircularProgress size={20} /> : 'エラー解析'}
            </Button>
            <Button
              startIcon={<BuildIcon />}
              onClick={handleRemediate}
              disabled={remediating}
              color="warning"
            >
              {remediating ? <CircularProgress size={20} /> : '自動改修'}
            </Button>
            <Button
              onClick={() => handleStatusUpdate(incident.status === 'open' ? 'investigating' : 'resolved')}
              variant="outlined"
            >
              ステータス更新
            </Button>
          </CardActions>
        </Card>

        {/* タブコンテンツ */}
        <Paper>
          <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
            <Tab label="詳細情報" icon={<CodeIcon />} />
            <Tab label="解析結果" icon={<AssessmentIcon />} />
            <Tab label="改修履歴" icon={<TimelineIcon />} />
          </Tabs>

          {/* 詳細情報タブ */}
          <TabPanel value={tabValue} index={0}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom>
                  エラー情報
                </Typography>
                <List>
                  <ListItem>
                    <ListItemText
                      primary="ファイルパス"
                      secondary={incident.file_path || 'N/A'}
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="行番号"
                      secondary={incident.line_number || 'N/A'}
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="プログラミング言語"
                      secondary={incident.language || 'N/A'}
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="初回発生"
                      secondary={new Date(incident.first_occurred).toLocaleString('ja-JP')}
                    />
                  </ListItem>
                </List>
              </Grid>

              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom>
                  スタックトレース
                </Typography>
                <Paper sx={{ p: 2, backgroundColor: '#f5f5f5', maxHeight: 300, overflow: 'auto' }}>
                  <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap' }}>
                    {incident.stack_trace || 'スタックトレースなし'}
                  </Typography>
                </Paper>
              </Grid>
            </Grid>
          </TabPanel>

          {/* 解析結果タブ */}
          <TabPanel value={tabValue} index={1}>
            {analysisResult ? (
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Typography variant="h6" gutterBottom>
                    解析結果
                  </Typography>
                  <List>
                    <ListItem>
                      <ListItemIcon>
                        <AssessmentIcon color="info" />
                      </ListItemIcon>
                      <ListItemText
                        primary="信頼度スコア"
                        secondary={`${(analysisResult.confidence_score * 100).toFixed(1)}%`}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText
                        primary="推定修正時間"
                        secondary={`${analysisResult.estimated_fix_time || 'N/A'} 分`}
                      />
                    </ListItem>
                  </List>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Typography variant="h6" gutterBottom>
                    推奨対応
                  </Typography>
                  <List>
                    {analysisResult.recommendations?.map((rec: string, index: number) => (
                      <ListItem key={index}>
                        <ListItemIcon>
                          <CheckCircleIcon color="success" />
                        </ListItemIcon>
                        <ListItemText primary={rec} />
                      </ListItem>
                    ))}
                  </List>
                </Grid>
              </Grid>
            ) : (
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <Typography variant="body1" color="text.secondary">
                  エラー解析を実行してください
                </Typography>
              </Box>
            )}
          </TabPanel>

          {/* 改修履歴タブ */}
          <TabPanel value={tabValue} index={2}>
            {remediationAttempts.length > 0 ? (
              <List>
                {remediationAttempts.map((attempt, index) => (
                  <ListItem key={attempt.id}>
                    <ListItemIcon>
                      <TimelineIcon />
                    </ListItemIcon>
                    <ListItemText
                      primary={`改修試行 #${index + 1}`}
                      secondary={`${attempt.status} - ${new Date(attempt.created_at).toLocaleString('ja-JP')}`}
                    />
                  </ListItem>
                ))}
              </List>
            ) : (
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <Typography variant="body1" color="text.secondary">
                  改修履歴がありません
                </Typography>
              </Box>
            )}
          </TabPanel>
        </Paper>
      </Container>

      {/* 改修完了ダイアログ */}
      <Dialog
        open={remediationDialogOpen}
        onClose={() => setRemediationDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <CheckCircleIcon color="success" sx={{ mr: 1 }} />
            自動改修完了
          </Box>
        </DialogTitle>
        <DialogContent>
          <Typography>
            エラーの自動改修が完了しました。
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 1 }}>
            修正内容を確認し、必要に応じてプルリクエストをレビューしてください。
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRemediationDialogOpen(false)}>
            閉じる
          </Button>
          <Button variant="contained" startIcon={<GitHubIcon />}>
            PRを確認
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
