"""
認証関連スキーマ
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """ユーザー基底スキーマ"""
    email: EmailStr
    role: str = Field(default="developer", description="ユーザーロール")


class UserResponse(UserBase):
    """ユーザー情報レスポンス"""
    id: uuid.UUID
    google_id: str
    organization_id: Optional[uuid.UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """認証トークンレスポンス"""
    access_token: str = Field(description="JWTアクセストークン")
    token_type: str = Field(default="bearer", description="トークンタイプ")
    user: UserResponse = Field(description="ユーザー情報")


class LoginRequest(BaseModel):
    """ログインリクエスト"""
    firebase_token: str = Field(description="Firebase IDトークン")


class OrganizationBase(BaseModel):
    """組織基底スキーマ"""
    name: str = Field(max_length=255, description="組織名")
    google_domain: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Google Workspace ドメイン"
    )


class OrganizationResponse(OrganizationBase):
    """組織情報レスポンス"""
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
