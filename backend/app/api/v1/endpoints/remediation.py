"""
改修管理エンドポイント
"""

import uuid
from typing import Any, Dict

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import DatabaseError, NotFoundError
from app.schemas.error import (
    RemediationAttemptResponse,
    RemediationStatusUpdate,
)
from app.services.auth_service import AuthService
from app.services.error_service import ErrorService

router = APIRouter()
logger = structlog.get_logger()


@router.patch("/attempts/{attempt_id}/status")
async def update_remediation_status(
    attempt_id: uuid.UUID,
    status_update: RemediationStatusUpdate,
    current_user: Dict[str, Any] = Depends(AuthService.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RemediationAttemptResponse:
    """
    改修試行ステータス更新

    Args:
        attempt_id: 改修試行ID
        status_update: ステータス更新データ
        current_user: 現在のユーザー
        db: データベースセッション

    Returns:
        RemediationAttemptResponse: 更新された改修試行情報
    """
    try:
        error_service = ErrorService(db)
        attempt = await error_service.update_remediation_attempt(
            attempt_id=attempt_id, status=status_update.status
        )

        logger.info(
            "Remediation attempt status updated",
            attempt_id=str(attempt_id),
            new_status=status_update.status,
            user_id=current_user["user_id"],
        )

        return RemediationAttemptResponse.model_validate(attempt)

    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Remediation attempt not found",
        )
    except DatabaseError as e:
        logger.error("Failed to update remediation status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update remediation status",
        )
    except Exception as e:
        logger.error(
            "Unexpected error in update remediation status", error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def remediation_health_check():
    """
    改修サービスヘルスチェック

    Returns:
        dict: ヘルスチェック結果
    """
    return {
        "status": "healthy",
        "service": "remediation-service",
        "version": "1.0.0",
    }
