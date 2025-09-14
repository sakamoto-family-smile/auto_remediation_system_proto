/**
 * エラー管理ページ
 */

import React, { useState, useEffect } from 'react';
import {
  AppBar,
  Box,
  Chip,
  Container,
  Dialog,
  DialogContent,
  DialogTitle,
  FormControl,
  Grid,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Toolbar,
  Typography,
  Alert,
  CircularProgress,
  Pagination,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Refresh as RefreshIcon,
  FilterList as FilterIcon,
  BugReport as BugIcon,
  Build as BuildIcon,
  Visibility as ViewIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { apiService } from '@/services/api';
import { ErrorIncidentListResponse } from '@/types/api';

interface FilterState {
  service_name: string;
  environment: string;
  severity: string;
  status: string;
}

export const ErrorsPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  // State
  const [incidents, setIncidents] = useState<ErrorIncidentListResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedIncident, setSelectedIncident] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filters, setFilters] = useState<FilterState>({
    service_name: '',
    environment: '',
    severity: '',
    status: '',
  });

  // データ取得
  const fetchIncidents = async () => {
    try {
      setLoading(true);
      setError(null);

      const data = await apiService.getErrorIncidents({
        ...filters,
        limit: 20,
        offset: (page - 1) * 20,
      });

      setIncidents(data.items);
      setTotalPages(Math.ceil(data.total_count / 20));

    } catch (err) {
      console.error('Failed to fetch incidents:', err);
      setError('エラーインシデントの取得に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidents();
  }, [page, filters]);

  // イベントハンドラー
  const handleBack = () => {
    navigate('/dashboard');
  };

  const handleRefresh = () => {
    fetchIncidents();
  };

  const handleFilterChange = (key: keyof FilterState, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPage(1); // フィルター変更時はページをリセット
  };

  const handleViewIncident = (incidentId: string) => {
    setSelectedIncident(incidentId);
    setDialogOpen(true);
  };

  const handleAnalyzeIncident = async (incidentId: string) => {
    try {
      await apiService.analyzeError({ incident_id: incidentId });
      // 成功時の処理（通知など）
      fetchIncidents(); // リフレッシュ
    } catch (err) {
      console.error('Failed to analyze incident:', err);
      setError('エラー解析に失敗しました');
    }
  };

  const handleRemediateIncident = async (incidentId: string) => {
    try {
      await apiService.remediateError({ incident_id: incidentId });
      // 成功時の処理（通知など）
      fetchIncidents(); // リフレッシュ
    } catch (err) {
      console.error('Failed to remediate incident:', err);
      setError('エラー改修に失敗しました');
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

  // ステータスの色を取得
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open': return 'error';
      case 'investigating': return 'warning';
      case 'resolved': return 'success';
      case 'closed': return 'default';
      default: return 'default';
    }
  };

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
            エラー管理
          </Typography>
          <IconButton color="inherit" onClick={handleRefresh}>
            <RefreshIcon />
          </IconButton>
          <Typography variant="body2" sx={{ ml: 2 }}>
            {user?.email}
          </Typography>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ flexGrow: 1, py: 2 }}>
        {/* フィルター */}
        <Paper sx={{ p: 2, mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <FilterIcon sx={{ mr: 1 }} />
            <Typography variant="h6">フィルター</Typography>
          </Box>

          <Grid container spacing={2}>
            <Grid item xs={12} sm={3}>
              <FormControl fullWidth size="small">
                <InputLabel>サービス名</InputLabel>
                <Select
                  value={filters.service_name}
                  onChange={(e) => handleFilterChange('service_name', e.target.value)}
                  label="サービス名"
                >
                  <MenuItem value="">すべて</MenuItem>
                  <MenuItem value="backend-api">Backend API</MenuItem>
                  <MenuItem value="frontend">Frontend</MenuItem>
                  <MenuItem value="database">Database</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={3}>
              <FormControl fullWidth size="small">
                <InputLabel>環境</InputLabel>
                <Select
                  value={filters.environment}
                  onChange={(e) => handleFilterChange('environment', e.target.value)}
                  label="環境"
                >
                  <MenuItem value="">すべて</MenuItem>
                  <MenuItem value="development">Development</MenuItem>
                  <MenuItem value="staging">Staging</MenuItem>
                  <MenuItem value="production">Production</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={3}>
              <FormControl fullWidth size="small">
                <InputLabel>重要度</InputLabel>
                <Select
                  value={filters.severity}
                  onChange={(e) => handleFilterChange('severity', e.target.value)}
                  label="重要度"
                >
                  <MenuItem value="">すべて</MenuItem>
                  <MenuItem value="critical">Critical</MenuItem>
                  <MenuItem value="high">High</MenuItem>
                  <MenuItem value="medium">Medium</MenuItem>
                  <MenuItem value="low">Low</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={3}>
              <FormControl fullWidth size="small">
                <InputLabel>ステータス</InputLabel>
                <Select
                  value={filters.status}
                  onChange={(e) => handleFilterChange('status', e.target.value)}
                  label="ステータス"
                >
                  <MenuItem value="">すべて</MenuItem>
                  <MenuItem value="open">Open</MenuItem>
                  <MenuItem value="investigating">Investigating</MenuItem>
                  <MenuItem value="resolved">Resolved</MenuItem>
                  <MenuItem value="closed">Closed</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </Paper>

        {/* エラー表示 */}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* インシデント一覧 */}
        <Paper>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>エラータイプ</TableCell>
                      <TableCell>サービス</TableCell>
                      <TableCell>環境</TableCell>
                      <TableCell>重要度</TableCell>
                      <TableCell>ステータス</TableCell>
                      <TableCell>発生回数</TableCell>
                      <TableCell>最終発生</TableCell>
                      <TableCell>アクション</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {incidents.map((incident) => (
                      <TableRow key={incident.id}>
                        <TableCell>
                          <Typography variant="body2" fontWeight="bold">
                            {incident.error_type}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {incident.error_message.length > 50
                              ? `${incident.error_message.substring(0, 50)}...`
                              : incident.error_message}
                          </Typography>
                        </TableCell>
                        <TableCell>{incident.service_name}</TableCell>
                        <TableCell>
                          <Chip
                            label={incident.environment}
                            size="small"
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={incident.severity}
                            size="small"
                            color={getSeverityColor(incident.severity) as any}
                          />
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={incident.status}
                            size="small"
                            color={getStatusColor(incident.status) as any}
                          />
                        </TableCell>
                        <TableCell>{incident.occurrence_count}</TableCell>
                        <TableCell>
                          {new Date(incident.last_occurred).toLocaleString('ja-JP')}
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', gap: 1 }}>
                            <IconButton
                              size="small"
                              onClick={() => handleViewIncident(incident.id)}
                              title="詳細表示"
                            >
                              <ViewIcon />
                            </IconButton>
                            <IconButton
                              size="small"
                              onClick={() => handleAnalyzeIncident(incident.id)}
                              title="エラー解析"
                              color="info"
                            >
                              <BugIcon />
                            </IconButton>
                            <IconButton
                              size="small"
                              onClick={() => handleRemediateIncident(incident.id)}
                              title="自動改修"
                              color="warning"
                            >
                              <BuildIcon />
                            </IconButton>
                          </Box>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>

              {/* ページネーション */}
              {totalPages > 1 && (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
                  <Pagination
                    count={totalPages}
                    page={page}
                    onChange={(_, newPage) => setPage(newPage)}
                    color="primary"
                  />
                </Box>
              )}
            </>
          )}
        </Paper>
      </Container>

      {/* インシデント詳細ダイアログ */}
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          エラーインシデント詳細
        </DialogTitle>
        <DialogContent>
          <Typography>
            インシデントID: {selectedIncident}
          </Typography>
          <Typography color="text.secondary">
            詳細情報の表示機能は実装中です。
          </Typography>
        </DialogContent>
      </Dialog>
    </Box>
  );
};
