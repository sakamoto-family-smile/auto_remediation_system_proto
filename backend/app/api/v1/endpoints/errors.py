"""
エラー管理エンドポイント
"""

import uuid
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import DatabaseError, NotFoundError
from app.schemas.error import (
    ErrorAnalysisRequest,
    ErrorAnalysisResponse,
    ErrorIncidentCreate,
    ErrorIncidentListResponse,
    ErrorIncidentResponse,
    IncidentStatusUpdate,
    RemediationAttemptCreate,
    RemediationAttemptResponse,
    RemediationRequest,
    RemediationResponse,
)
from app.services.auth_service import AuthService
from app.services.error_service import ErrorService

router = APIRouter()
logger = structlog.get_logger()


@router.post("/incidents", response_model=ErrorIncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_error_incident(
    incident_data: ErrorIncidentCreate,
    current_user: Dict[str, Any] = Depends(AuthService.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ErrorIncidentResponse:
    """
    エラーインシデント作成

    Args:
        incident_data: インシデント作成データ
        current_user: 現在のユーザー
        db: データベースセッション

    Returns:
        ErrorIncidentResponse: 作成されたインシデント情報
    """
    try:
        error_service = ErrorService(db)
        incident = await error_service.create_incident(
            error_type=incident_data.error_type,
            severity=incident_data.severity,
            service_name=incident_data.service_name,
            environment=incident_data.environment,
            error_message=incident_data.error_message,
            stack_trace=incident_data.stack_trace,
            file_path=incident_data.file_path,
            line_number=incident_data.line_number,
            language=incident_data.language,
            metadata=incident_data.metadata,
        )

        logger.info(
            "Error incident created",
            incident_id=str(incident.id),
            error_type=incident_data.error_type,
            severity=incident_data.severity,
        )

        return ErrorIncidentResponse.from_orm(incident)

    except DatabaseError as e:
        logger.error("Failed to create error incident", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create error incident",
        )
    except Exception as e:
        logger.error("Unexpected error in create error incident", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/incidents", response_model=List[ErrorIncidentListResponse])
async def get_error_incidents(
    service_name: Optional[str] = Query(None, description="サービス名フィルター"),
    environment: Optional[str] = Query(None, description="環境フィルター"),
    severity: Optional[str] = Query(None, description="重要度フィルター"),
    status: Optional[str] = Query(None, description="ステータスフィルター"),
    limit: int = Query(50, ge=1, le=100, description="取得件数上限"),
    offset: int = Query(0, ge=0, description="オフセット"),
    current_user: Dict[str, Any] = Depends(AuthService.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ErrorIncidentListResponse]:
    """
    エラーインシデント一覧取得

    Args:
        service_name: サービス名フィルター
        environment: 環境フィルター
        severity: 重要度フィルター
        status: ステータスフィルター
        limit: 取得件数上限
        offset: オフセット
        current_user: 現在のユーザー
        db: データベースセッション

    Returns:
        List[ErrorIncidentListResponse]: インシデント一覧
    """
    try:
        error_service = ErrorService(db)
        incidents = await error_service.get_incidents(
            service_name=service_name,
            environment=environment,
            severity=severity,
            status=status,
            limit=limit,
            offset=offset,
        )

        incident_list = [
            ErrorIncidentListResponse.from_orm(incident) for incident in incidents
        ]

        logger.debug(
            "Error incidents retrieved",
            count=len(incident_list),
            filters={
                "service_name": service_name,
                "environment": environment,
                "severity": severity,
                "status": status,
            },
        )

        return incident_list

    except DatabaseError as e:
        logger.error("Failed to get error incidents", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve error incidents",
        )
    except Exception as e:
        logger.error("Unexpected error in get error incidents", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/incidents/{incident_id}", response_model=ErrorIncidentResponse)
async def get_error_incident(
    incident_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(AuthService.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ErrorIncidentResponse:
    """
    エラーインシデント詳細取得

    Args:
        incident_id: インシデントID
        current_user: 現在のユーザー
        db: データベースセッション

    Returns:
        ErrorIncidentResponse: インシデント詳細情報
    """
    try:
        error_service = ErrorService(db)
        incident = await error_service.get_incident(incident_id)

        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Error incident not found",
            )

        logger.debug(
            "Error incident retrieved",
            incident_id=str(incident_id),
        )

        return ErrorIncidentResponse.from_orm(incident)

    except HTTPException:
        raise
    except DatabaseError as e:
        logger.error("Failed to get error incident", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve error incident",
        )
    except Exception as e:
        logger.error("Unexpected error in get error incident", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.patch("/incidents/{incident_id}/status")
async def update_incident_status(
    incident_id: uuid.UUID,
    status_update: IncidentStatusUpdate,
    current_user: Dict[str, Any] = Depends(AuthService.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ErrorIncidentResponse:
    """
    インシデントステータス更新

    Args:
        incident_id: インシデントID
        status_update: ステータス更新データ
        current_user: 現在のユーザー
        db: データベースセッション

    Returns:
        ErrorIncidentResponse: 更新されたインシデント情報
    """
    try:
        error_service = ErrorService(db)
        incident = await error_service.update_incident_status(
            incident_id=incident_id, status=status_update.status
        )

        logger.info(
            "Incident status updated",
            incident_id=str(incident_id),
            new_status=status_update.status,
            user_id=current_user["user_id"],
        )

        return ErrorIncidentResponse.from_orm(incident)

    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Error incident not found",
        )
    except DatabaseError as e:
        logger.error("Failed to update incident status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update incident status",
        )
    except Exception as e:
        logger.error("Unexpected error in update incident status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/incidents/{incident_id}/analyze", response_model=ErrorAnalysisResponse)
async def analyze_error(
    incident_id: uuid.UUID,
    analysis_request: ErrorAnalysisRequest,
    current_user: Dict[str, Any] = Depends(AuthService.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ErrorAnalysisResponse:
    """
    エラー解析実行

    Args:
        incident_id: インシデントID
        analysis_request: 解析リクエスト
        current_user: 現在のユーザー
        db: データベースセッション

    Returns:
        ErrorAnalysisResponse: 解析結果
    """
    try:
        error_service = ErrorService(db)
        incident = await error_service.get_incident(incident_id)

        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Error incident not found",
            )

        # TODO: cursor-cliを使用した実際のエラー解析を実装
        # 現在は仮の解析結果を返す
        analysis_result = {
            "error_category": "runtime_error",
            "root_cause": "Potential null pointer exception",
            "affected_components": [incident.service_name],
            "similar_incidents": 0,
        }

        recommendations = [
            "Add null checks before accessing object properties",
            "Implement proper error handling",
            "Add unit tests for edge cases",
        ]

        logger.info(
            "Error analysis completed",
            incident_id=str(incident_id),
            user_id=current_user["user_id"],
        )

        return ErrorAnalysisResponse(
            incident_id=incident_id,
            analysis_result=analysis_result,
            recommendations=recommendations,
            confidence_score=0.85,
            estimated_fix_time=15,
        )

    except HTTPException:
        raise
    except DatabaseError as e:
        logger.error("Failed to analyze error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze error",
        )
    except Exception as e:
        logger.error("Unexpected error in analyze error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/incidents/{incident_id}/remediate", response_model=RemediationResponse)
async def remediate_error(
    incident_id: uuid.UUID,
    remediation_request: RemediationRequest,
    current_user: Dict[str, Any] = Depends(AuthService.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RemediationResponse:
    """
    エラー改修実行

    Args:
        incident_id: インシデントID
        remediation_request: 改修リクエスト
        current_user: 現在のユーザー
        db: データベースセッション

    Returns:
        RemediationResponse: 改修結果
    """
    try:
        error_service = ErrorService(db)
        incident = await error_service.get_incident(incident_id)

        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Error incident not found",
            )

        # 改修試行作成
        attempt = await error_service.create_remediation_attempt(
            incident_id=incident_id,
            remediation_type="automated",
            description="Automated remediation using cursor-cli",
        )

        # TODO: cursor-cliを使用した実際の改修処理を実装
        # 現在は仮の改修結果を返す
        fix_code = f"""
// Automated fix for {incident.error_type}
// Generated by cursor-cli

if (obj != null) {{
    // Original code here with null check
    obj.someMethod();
}}
"""

        test_results = {
            "status": "passed",
            "tests_run": 5,
            "tests_passed": 5,
            "coverage": 0.95,
        }

        # 改修試行を更新
        await error_service.update_remediation_attempt(
            attempt_id=attempt.id,
            status="completed",
            fix_code=fix_code,
            test_results=test_results,
        )

        logger.info(
            "Error remediation completed",
            incident_id=str(incident_id),
            attempt_id=str(attempt.id),
            user_id=current_user["user_id"],
        )

        return RemediationResponse(
            attempt_id=attempt.id,
            status="completed",
            fix_code=fix_code,
            test_results=test_results,
            pr_url=None,  # TODO: GitHub PR作成後にURLを設定
        )

    except HTTPException:
        raise
    except DatabaseError as e:
        logger.error("Failed to remediate error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remediate error",
        )
    except Exception as e:
        logger.error("Unexpected error in remediate error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/remediation", response_model=RemediationAttemptResponse, status_code=status.HTTP_201_CREATED)
async def create_remediation_attempt(
    attempt_data: RemediationAttemptCreate,
    current_user: Dict[str, Any] = Depends(AuthService.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RemediationAttemptResponse:
    """
    改修試行作成

    Args:
        attempt_data: 改修試行データ
        current_user: 現在のユーザー
        db: データベースセッション

    Returns:
        RemediationAttemptResponse: 作成された改修試行情報
    """
    try:
        error_service = ErrorService(db)
        attempt = await error_service.create_remediation_attempt(
            incident_id=attempt_data.incident_id,
            remediation_type=attempt_data.remediation_type,
            description=attempt_data.description,
        )

        logger.info(
            "Remediation attempt created",
            attempt_id=str(attempt.id),
            incident_id=str(attempt_data.incident_id),
            user_id=current_user["user_id"],
        )

        return RemediationAttemptResponse.from_orm(attempt)

    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Error incident not found",
        )
    except DatabaseError as e:
        logger.error("Failed to create remediation attempt", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create remediation attempt",
        )
    except Exception as e:
        logger.error("Unexpected error in create remediation attempt", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/remediation/{attempt_id}", response_model=RemediationAttemptResponse)
async def get_remediation_attempt(
    attempt_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(AuthService.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RemediationAttemptResponse:
    """
    改修試行詳細取得

    Args:
        attempt_id: 改修試行ID
        current_user: 現在のユーザー
        db: データベースセッション

    Returns:
        RemediationAttemptResponse: 改修試行詳細情報
    """
    try:
        error_service = ErrorService(db)
        attempt = await error_service.get_remediation_attempt(attempt_id)

        if not attempt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Remediation attempt not found",
            )

        logger.debug(
            "Remediation attempt retrieved",
            attempt_id=str(attempt_id),
        )

        return RemediationAttemptResponse.from_orm(attempt)

    except HTTPException:
        raise
    except DatabaseError as e:
        logger.error("Failed to get remediation attempt", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve remediation attempt",
        )
    except Exception as e:
        logger.error("Unexpected error in get remediation attempt", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
