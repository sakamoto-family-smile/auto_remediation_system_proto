"""
API v1 ルーター
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, chat, errors, remediation, webhooks

api_router = APIRouter()

# 各エンドポイントを登録
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(errors.router, prefix="/errors", tags=["errors"])
api_router.include_router(remediation.router, prefix="/remediation", tags=["remediation"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
