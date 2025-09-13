"""
チャット関連スキーマ
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ChatMessageCreate(BaseModel):
    """チャットメッセージ作成スキーマ"""
    role: str = Field(..., description="メッセージロール (user/assistant)")
    content: str = Field(..., min_length=1, description="メッセージ内容")


class ChatMessageResponse(BaseModel):
    """チャットメッセージレスポンススキーマ"""
    id: uuid.UUID
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatSessionCreate(BaseModel):
    """チャットセッション作成スキーマ"""
    initial_message: Optional[str] = Field(
        None, description="初期メッセージ（オプション）"
    )


class ChatSessionResponse(BaseModel):
    """チャットセッションレスポンススキーマ"""
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageResponse] = Field(
        default_factory=list, description="メッセージリスト"
    )

    class Config:
        from_attributes = True


class ChatSessionListResponse(BaseModel):
    """チャットセッション一覧レスポンススキーマ"""
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    message_count: int = Field(description="メッセージ数")
    last_message: Optional[str] = Field(
        None, description="最後のメッセージ（プレビュー用）"
    )

    class Config:
        from_attributes = True


class ChatCompletionRequest(BaseModel):
    """チャット完了リクエストスキーマ"""
    message: str = Field(..., min_length=1, description="ユーザーメッセージ")
    session_id: Optional[uuid.UUID] = Field(
        None, description="セッションID（新規の場合はNone）"
    )


class ChatCompletionResponse(BaseModel):
    """チャット完了レスポンススキーマ"""
    session_id: uuid.UUID = Field(description="セッションID")
    user_message: ChatMessageResponse = Field(description="ユーザーメッセージ")
    assistant_message: ChatMessageResponse = Field(description="アシスタントメッセージ")
