/**
 * API型定義
 */

// 共通型
export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface ApiError {
  error_code: string;
  detail: string;
  timestamp?: string;
}

// 認証関連
export interface LoginRequest {
  firebase_token: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

export interface UserResponse {
  id: string;
  google_id: string;
  email: string;
  organization_id?: string;
  role: string;
  created_at: string;
}

// チャット関連
export interface ChatSessionCreate {
  initial_message?: string;
}

export interface ChatSessionResponse {
  id: string;
  user_id: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessageResponse[];
}

export interface ChatSessionListResponse {
  id: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  last_message?: string;
}

export interface ChatMessageCreate {
  role: string;
  content: string;
}

export interface ChatMessageResponse {
  id: string;
  role: string;
  content: string;
  created_at: string;
}

export interface ChatCompletionRequest {
  message: string;
  session_id?: string;
}

export interface ChatCompletionResponse {
  session_id: string;
  user_message: ChatMessageResponse;
  assistant_message: ChatMessageResponse;
}

// エラー管理関連
export interface ErrorIncidentCreate {
  error_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  service_name: string;
  environment: 'development' | 'staging' | 'production';
  error_message: string;
  stack_trace?: string;
  file_path?: string;
  line_number?: number;
  language?: string;
  metadata?: Record<string, any>;
}

export interface ErrorIncidentResponse {
  id: string;
  error_type: string;
  severity: string;
  service_name: string;
  environment: string;
  error_message: string;
  stack_trace?: string;
  file_path?: string;
  line_number?: number;
  language?: string;
  status: string;
  first_occurred: string;
  last_occurred: string;
  occurrence_count: number;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface ErrorIncidentListResponse {
  id: string;
  error_type: string;
  severity: string;
  service_name: string;
  environment: string;
  error_message: string;
  status: string;
  occurrence_count: number;
  last_occurred: string;
  created_at: string;
}

export interface ErrorAnalysisRequest {
  incident_id: string;
  include_context?: boolean;
}

export interface ErrorAnalysisResponse {
  incident_id: string;
  analysis_result: Record<string, any>;
  recommendations: string[];
  confidence_score: number;
  estimated_fix_time?: number;
}

export interface RemediationRequest {
  incident_id: string;
  auto_create_pr?: boolean;
  target_branch?: string;
}

export interface RemediationResponse {
  attempt_id: string;
  status: string;
  fix_code?: string;
  test_results?: Record<string, any>;
  pr_url?: string;
  estimated_completion?: string;
}

// ページネーション関連
export interface PaginatedErrorIncidentsResponse {
  items: ErrorIncidentListResponse[];
  total_count: number;
  limit: number;
  offset: number;
  has_next: boolean;
  has_prev: boolean;
}
