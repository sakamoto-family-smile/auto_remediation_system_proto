"""
Webhook エンドポイント
"""

import hashlib
import hmac
import json
import uuid
from typing import Any, Dict

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import DatabaseError
from app.services.error_service import ErrorService

router = APIRouter()
logger = structlog.get_logger()
settings = get_settings()


@router.post("/github", status_code=status.HTTP_200_OK)
async def github_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    GitHub Webhook ハンドラー

    Args:
        request: FastAPI リクエスト
        db: データベースセッション

    Returns:
        Dict[str, Any]: 処理結果
    """
    try:
        # ペイロード取得
        payload = await request.body()
        signature = request.headers.get("X-Hub-Signature-256")
        event_type = request.headers.get("X-GitHub-Event")

        # 署名検証
        if not _verify_github_signature(payload, signature):
            logger.warning("Invalid GitHub webhook signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature",
            )

        # JSON解析
        try:
            data = json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload",
            )

        logger.info(
            "GitHub webhook received",
            event_type=event_type,
            repository=data.get("repository", {}).get("full_name"),
        )

        # イベント別処理
        result = await _handle_github_event(event_type, data, db)

        return {
            "status": "success",
            "event_type": event_type,
            "processed": True,
            **result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("GitHub webhook processing failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed",
        )


@router.post("/slack", status_code=status.HTTP_200_OK)
async def slack_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Slack Webhook ハンドラー

    Args:
        request: FastAPI リクエスト
        db: データベースセッション

    Returns:
        Dict[str, Any]: 処理結果
    """
    try:
        # ペイロード取得
        payload = await request.body()

        # Content-Typeチェック
        content_type = request.headers.get("Content-Type", "")

        if "application/json" in content_type:
            try:
                data = json.loads(payload.decode("utf-8"))
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON payload",
                )
        elif "application/x-www-form-urlencoded" in content_type:
            # Slackからのform-encodedデータを処理
            form_data = payload.decode("utf-8")
            # 簡単なパース（実際はurllib.parse.parse_qsを使用）
            data = {"text": form_data}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported content type",
            )

        logger.info("Slack webhook received", data_keys=list(data.keys()))

        # Slackイベント処理
        result = await _handle_slack_event(data, db)

        return {
            "status": "success",
            "processed": True,
            **result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Slack webhook processing failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed",
        )


@router.post("/generic", status_code=status.HTTP_200_OK)
async def generic_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    汎用 Webhook ハンドラー

    Args:
        request: FastAPI リクエスト
        db: データベースセッション

    Returns:
        Dict[str, Any]: 処理結果
    """
    try:
        # ペイロード取得
        payload = await request.body()
        headers = dict(request.headers)

        # JSON解析試行
        try:
            data = json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError:
            data = {"raw_payload": payload.decode("utf-8")}

        logger.info(
            "Generic webhook received",
            content_length=len(payload),
            headers=headers,
        )

        # エラー情報が含まれている場合の自動インシデント作成
        if _is_error_webhook(data):
            incident_id = await _create_incident_from_webhook(data, db)
            return {
                "status": "success",
                "incident_created": True,
                "incident_id": str(incident_id),
            }

        return {
            "status": "success",
            "processed": True,
            "message": "Webhook received and logged",
        }

    except Exception as e:
        logger.error("Generic webhook processing failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed",
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def webhook_health_check():
    """
    Webhook サービスヘルスチェック

    Returns:
        dict: ヘルスチェック結果
    """
    return {
        "status": "healthy",
        "service": "webhook-service",
        "version": "1.0.0",
        "endpoints": ["github", "slack", "generic"],
    }


def _verify_github_signature(payload: bytes, signature: str) -> bool:
    """
    GitHub Webhook署名検証

    Args:
        payload: Webhookペイロード
        signature: GitHub署名

    Returns:
        bool: 署名が有効な場合True
    """
    if not signature or not settings.GITHUB_WEBHOOK_SECRET:
        return False

    try:
        # GitHub署名形式: sha256=<hash>
        if not signature.startswith("sha256="):
            return False

        expected_signature = signature[7:]  # "sha256="を除去

        # HMAC-SHA256で署名計算
        computed_signature = hmac.new(
            settings.GITHUB_WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_signature, computed_signature)

    except Exception as e:
        logger.error("GitHub signature verification failed", error=str(e))
        return False


async def _handle_github_event(
    event_type: str, data: Dict[str, Any], db: AsyncSession
) -> Dict[str, Any]:
    """
    GitHub イベント処理

    Args:
        event_type: イベントタイプ
        data: イベントデータ
        db: データベースセッション

    Returns:
        Dict[str, Any]: 処理結果
    """
    try:
        if event_type == "issues":
            # Issue関連イベント
            action = data.get("action")
            issue = data.get("issue", {})

            if action == "opened" and _is_error_issue(issue):
                # エラー関連のIssueの場合、インシデント作成
                incident_id = await _create_incident_from_issue(issue, db)
                return {"incident_created": True, "incident_id": str(incident_id)}

        elif event_type == "pull_request":
            # PR関連イベント
            action = data.get("action")
            pr = data.get("pull_request", {})

            if action in ["opened", "synchronize"] and _is_auto_fix_pr(pr):
                # 自動修正PRの場合、関連インシデントを更新
                await _update_incident_from_pr(pr, db)
                return {"incident_updated": True}

        elif event_type == "workflow_run":
            # GitHub Actions関連
            workflow = data.get("workflow_run", {})
            if workflow.get("conclusion") == "failure":
                # ワークフロー失敗の場合、エラーインシデント作成
                incident_id = await _create_incident_from_workflow_failure(workflow, db)
                return {"incident_created": True, "incident_id": str(incident_id)}

        return {"processed": True, "action_taken": False}

    except Exception as e:
        logger.error("GitHub event handling failed", error=str(e))
        return {"processed": False, "error": str(e)}


async def _handle_slack_event(
    data: Dict[str, Any], db: AsyncSession
) -> Dict[str, Any]:
    """
    Slack イベント処理

    Args:
        data: Slackイベントデータ
        db: データベースセッション

    Returns:
        Dict[str, Any]: 処理結果
    """
    try:
        # Slack URL verification
        if data.get("type") == "url_verification":
            return {"challenge": data.get("challenge")}

        # エラー報告メッセージの検出
        if _is_error_report(data):
            incident_id = await _create_incident_from_slack_message(data, db)
            return {"incident_created": True, "incident_id": str(incident_id)}

        return {"processed": True, "action_taken": False}

    except Exception as e:
        logger.error("Slack event handling failed", error=str(e))
        return {"processed": False, "error": str(e)}


def _is_error_webhook(data: Dict[str, Any]) -> bool:
    """エラーWebhookかどうか判定"""
    error_indicators = ["error", "exception", "failure", "crash", "bug"]

    # データ内にエラー関連のキーワードが含まれているかチェック
    data_str = json.dumps(data).lower()
    return any(indicator in data_str for indicator in error_indicators)


def _is_error_issue(issue: Dict[str, Any]) -> bool:
    """エラー関連のIssueかどうか判定"""
    title = issue.get("title", "").lower()
    body = issue.get("body", "").lower()
    labels = [label.get("name", "").lower() for label in issue.get("labels", [])]

    error_keywords = ["error", "bug", "exception", "crash", "failure"]

    return (
        any(keyword in title for keyword in error_keywords) or
        any(keyword in body for keyword in error_keywords) or
        any(keyword in " ".join(labels) for keyword in error_keywords)
    )


def _is_auto_fix_pr(pr: Dict[str, Any]) -> bool:
    """自動修正PRかどうか判定"""
    title = pr.get("title", "").lower()
    return "auto-fix" in title or "🤖" in pr.get("title", "")


def _is_error_report(data: Dict[str, Any]) -> bool:
    """エラー報告メッセージかどうか判定"""
    text = data.get("text", "").lower()
    return "error" in text or "bug" in text or "crash" in text


async def _create_incident_from_webhook(
    data: Dict[str, Any], db: AsyncSession
) -> uuid.UUID:
    """Webhookデータからインシデント作成"""
    error_service = ErrorService(db)

    incident = await error_service.create_incident(
        error_type="webhook_error",
        severity="medium",
        service_name=data.get("service", "unknown"),
        environment=data.get("environment", "unknown"),
        error_message=str(data.get("message", "Error reported via webhook")),
        metadata=data,
    )

    return incident.id


async def _create_incident_from_issue(
    issue: Dict[str, Any], db: AsyncSession
) -> uuid.UUID:
    """GitHub IssueからIncdient作成"""
    error_service = ErrorService(db)

    incident = await error_service.create_incident(
        error_type="github_issue",
        severity="medium",
        service_name="github",
        environment="production",
        error_message=issue.get("title", ""),
        metadata={
            "issue_number": issue.get("number"),
            "issue_url": issue.get("html_url"),
            "body": issue.get("body"),
        },
    )

    return incident.id


async def _create_incident_from_workflow_failure(
    workflow: Dict[str, Any], db: AsyncSession
) -> uuid.UUID:
    """GitHub Actions失敗からIncident作成"""
    error_service = ErrorService(db)

    incident = await error_service.create_incident(
        error_type="workflow_failure",
        severity="high",
        service_name="github_actions",
        environment="ci_cd",
        error_message=f"Workflow '{workflow.get('name')}' failed",
        metadata={
            "workflow_id": workflow.get("id"),
            "workflow_url": workflow.get("html_url"),
            "conclusion": workflow.get("conclusion"),
        },
    )

    return incident.id


async def _create_incident_from_slack_message(
    data: Dict[str, Any], db: AsyncSession
) -> uuid.UUID:
    """SlackメッセージからIncident作成"""
    error_service = ErrorService(db)

    incident = await error_service.create_incident(
        error_type="slack_report",
        severity="medium",
        service_name="slack",
        environment="production",
        error_message=data.get("text", "Error reported via Slack"),
        metadata=data,
    )

    return incident.id


async def _update_incident_from_pr(pr: Dict[str, Any], db: AsyncSession) -> None:
    """PRからIncident更新"""
    # TODO: PR情報に基づいてインシデントステータスを更新
    logger.info("Auto-fix PR detected", pr_number=pr.get("number"))
    pass
