/**
 * API サービス
 */

import axios, { AxiosInstance, AxiosResponse } from 'axios';
import {
  ApiError,
  TokenResponse,
  LoginRequest,
  UserResponse,
  ChatSessionResponse,
  ChatSessionListResponse,
  ChatCompletionRequest,
  ChatCompletionResponse,
  ErrorIncidentResponse,
  ErrorIncidentListResponse,
  ErrorIncidentCreate,
  ErrorAnalysisRequest,
  ErrorAnalysisResponse,
  RemediationRequest,
  RemediationResponse,
  PaginatedErrorIncidentsResponse,
} from '@/types/api';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: '/api/v1',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // リクエストインターセプター（認証トークン追加）
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // レスポンスインターセプター（エラーハンドリング）
    this.client.interceptors.response.use(
      (response: AxiosResponse) => response,
      (error) => {
        if (error.response?.status === 401) {
          // 認証エラーの場合はログアウト処理
          localStorage.removeItem('access_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // 認証API
  async login(loginRequest: LoginRequest): Promise<TokenResponse> {
    const response = await this.client.post<TokenResponse>('/auth/token', loginRequest);
    return response.data;
  }

  async getCurrentUser(): Promise<UserResponse> {
    const response = await this.client.get<UserResponse>('/auth/me');
    return response.data;
  }

  async refreshToken(): Promise<TokenResponse> {
    const response = await this.client.post<TokenResponse>('/auth/refresh');
    return response.data;
  }

  // チャットAPI
  async getChatSessions(limit = 50, offset = 0): Promise<ChatSessionListResponse[]> {
    const response = await this.client.get<ChatSessionListResponse[]>(
      `/chat/sessions?limit=${limit}&offset=${offset}`
    );
    return response.data;
  }

  async getChatSession(sessionId: string): Promise<ChatSessionResponse> {
    const response = await this.client.get<ChatSessionResponse>(`/chat/sessions/${sessionId}`);
    return response.data;
  }

  async createChatSession(initialMessage?: string): Promise<ChatSessionResponse> {
    const response = await this.client.post<ChatSessionResponse>('/chat/sessions', {
      initial_message: initialMessage,
    });
    return response.data;
  }

  async deleteChatSession(sessionId: string): Promise<void> {
    await this.client.delete(`/chat/sessions/${sessionId}`);
  }

  async chatCompletion(request: ChatCompletionRequest): Promise<ChatCompletionResponse> {
    const response = await this.client.post<ChatCompletionResponse>('/chat/completion', request);
    return response.data;
  }

  // エラー管理API
  async getErrorIncidents(params: {
    service_name?: string;
    environment?: string;
    severity?: string;
    status?: string;
    limit?: number;
    offset?: number;
  } = {}): Promise<PaginatedErrorIncidentsResponse> {
    const queryParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        queryParams.append(key, value.toString());
      }
    });

    const response = await this.client.get<PaginatedErrorIncidentsResponse>(
      `/errors/incidents?${queryParams.toString()}`
    );
    return response.data;
  }

  async getErrorIncident(incidentId: string): Promise<ErrorIncidentResponse> {
    const response = await this.client.get<ErrorIncidentResponse>(`/errors/incidents/${incidentId}`);
    return response.data;
  }

  async createErrorIncident(incident: ErrorIncidentCreate): Promise<ErrorIncidentResponse> {
    const response = await this.client.post<ErrorIncidentResponse>('/errors/incidents', incident);
    return response.data;
  }

  async updateIncidentStatus(incidentId: string, status: string): Promise<ErrorIncidentResponse> {
    const response = await this.client.patch<ErrorIncidentResponse>(
      `/errors/incidents/${incidentId}/status`,
      { status: status }
    );
    return response.data;
  }

  async analyzeError(request: ErrorAnalysisRequest): Promise<ErrorAnalysisResponse> {
    const response = await this.client.post<ErrorAnalysisResponse>(
      `/errors/incidents/${request.incident_id}/analyze`,
      request
    );
    return response.data;
  }

  async remediateError(request: RemediationRequest): Promise<RemediationResponse> {
    const response = await this.client.post<RemediationResponse>(
      `/errors/incidents/${request.incident_id}/remediate`,
      request
    );
    return response.data;
  }

  // ヘルスチェック
  async healthCheck(): Promise<{ status: string; service: string; version: string }> {
    const response = await this.client.get('/health');
    return response.data;
  }
}

export const apiService = new ApiService();
export default apiService;
