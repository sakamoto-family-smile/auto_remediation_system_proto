"""
エラー管理関連スキーマ
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ErrorIncidentCreate(BaseModel):
    """エラーインシデント作成スキーマ"""
    error_type: str = Field(..., description="エラータイプ")
    severity: str = Field(..., description="重要度 (low/medium/high/critical)")
    service_name: str = Field(..., description="サービス名")
    environment: str = Field(
        ..., description="環境 (development/staging/production)"
    )
    error_message: str = Field(..., description="エラーメッセージ")
    stack_trace: Optional[str] = Field(None, description="スタックトレース")
    file_path: Optional[str] = Field(None, description="エラー発生ファイルパス")
    line_number: Optional[int] = Field(None, description="エラー発生行番号")
    language: Optional[str] = Field(None, description="プログラミング言語")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="追加メタデータ"
    )


class ErrorIncidentResponse(BaseModel):
    """エラーインシデントレスポンススキーマ"""
    id: uuid.UUID
    error_type: str
    severity: str
    service_name: str
    environment: str
    error_message: str
    stack_trace: Optional[str]
    file_path: Optional[str]
    line_number: Optional[int]
    language: Optional[str]
    status: str
    first_occurred: datetime
    last_occurred: datetime
    occurrence_count: int
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ErrorIncidentListResponse(BaseModel):
    """エラーインシデント一覧レスポンススキーマ"""
    id: uuid.UUID
    error_type: str
    severity: str
    service_name: str
    environment: str
    error_message: str
    status: str
    occurrence_count: int
    last_occurred: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class RemediationAttemptCreate(BaseModel):
    """改修試行作成スキーマ"""
    incident_id: uuid.UUID = Field(..., description="インシデントID")
    remediation_type: str = Field(..., description="改修タイプ")
    description: Optional[str] = Field(None, description="改修説明")


class RemediationAttemptResponse(BaseModel):
    """改修試行レスポンススキーマ"""
    id: uuid.UUID
    incident_id: uuid.UUID
    remediation_type: str
    status: str
    description: Optional[str]
    analysis_result: Optional[Dict[str, Any]]
    fix_code: Optional[str]
    test_results: Optional[Dict[str, Any]]
    pr_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ErrorAnalysisRequest(BaseModel):
    """エラー解析リクエストスキーマ"""
    incident_id: uuid.UUID = Field(..., description="インシデントID")
    include_context: bool = Field(
        default=True, description="コンテキスト情報を含めるか"
    )


class ErrorAnalysisResponse(BaseModel):
    """エラー解析レスポンススキーマ"""
    incident_id: uuid.UUID
    analysis_result: Dict[str, Any] = Field(description="解析結果")
    recommendations: List[str] = Field(description="推奨対応")
    confidence_score: float = Field(description="信頼度スコア (0.0-1.0)")
    estimated_fix_time: Optional[int] = Field(
        None, description="推定修正時間（分）"
    )


class RemediationRequest(BaseModel):
    """改修リクエストスキーマ"""
    incident_id: uuid.UUID = Field(..., description="インシデントID")
    auto_create_pr: bool = Field(
        default=True, description="自動でPR作成するか"
    )
    target_branch: str = Field(
        default="main", description="対象ブランチ"
    )


class RemediationResponse(BaseModel):
    """改修レスポンススキーマ"""
    attempt_id: uuid.UUID = Field(description="改修試行ID")
    status: str = Field(description="改修ステータス")
    fix_code: Optional[str] = Field(None, description="修正コード")
    test_results: Optional[Dict[str, Any]] = Field(None, description="テスト結果")
    pr_url: Optional[str] = Field(None, description="PR URL")
    estimated_completion: Optional[datetime] = Field(
        None, description="完了予定時刻"
    )


class IncidentStatusUpdate(BaseModel):
    """インシデントステータス更新リクエストスキーマ"""
    status: str = Field(
        ..., description="新しいステータス (open/investigating/resolved/closed)"
    )


class RemediationStatusUpdate(BaseModel):
    """改修試行ステータス更新リクエストスキーマ"""
    status: str = Field(
        ..., description="新しいステータス (pending/in_progress/completed/failed)"
    )
