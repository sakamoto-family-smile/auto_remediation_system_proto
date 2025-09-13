"""
承認ワークフローサービス
"""

import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DatabaseError, NotFoundError
from app.models.audit import AuditLog
from app.models.error import ErrorIncident, RemediationAttempt
from app.services.slack_service import SlackService

logger = structlog.get_logger()


class ApprovalStatus(str, Enum):
    """承認ステータス"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalType(str, Enum):
    """承認タイプ"""
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    EMERGENCY = "emergency"


class ApprovalService:
    """承認ワークフローサービス"""

    def __init__(self, db: AsyncSession, slack_service: Optional[SlackService] = None):
        self.db = db
        self.slack_service = slack_service or SlackService()

    async def request_approval(
        self,
        incident_id: uuid.UUID,
        remediation_data: Dict[str, Any],
        approval_type: ApprovalType = ApprovalType.MANUAL,
        approvers: Optional[List[str]] = None,
        auto_approve_after: Optional[int] = None,
        slack_channel: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        承認リクエスト作成

        Args:
            incident_id: インシデントID
            remediation_data: 改修データ
            approval_type: 承認タイプ
            approvers: 承認者リスト
            auto_approve_after: 自動承認までの時間（分）
            slack_channel: Slack通知チャンネル

        Returns:
            Dict[str, Any]: 承認リクエスト情報
        """
        try:
            # インシデント取得
            incident = await self._get_incident(incident_id)

            # 承認ルールを適用
            approval_config = await self._get_approval_config(incident, approval_type)

            # 承認リクエストを記録
            approval_request = await self._create_approval_record(
                incident_id=incident_id,
                remediation_data=remediation_data,
                approval_type=approval_type,
                approvers=approvers or approval_config["default_approvers"],
                auto_approve_after=auto_approve_after or approval_config["auto_approve_timeout"],
            )

            # 自動承認の場合
            if approval_type == ApprovalType.AUTOMATIC:
                return await self._auto_approve(approval_request)

            # 緊急承認の場合
            if approval_type == ApprovalType.EMERGENCY:
                return await self._emergency_approve(approval_request, slack_channel)

            # 手動承認の場合はSlack通知
            if self.slack_service.is_configured() and slack_channel:
                slack_result = await self.slack_service.send_approval_request(
                    channel=slack_channel,
                    incident_data=incident,
                    remediation_data=remediation_data,
                    approvers=approval_request["approvers"],
                )
                approval_request["slack_message"] = slack_result

            logger.info(
                "Approval request created",
                incident_id=str(incident_id),
                approval_id=approval_request["id"],
                approval_type=approval_type,
            )

            return approval_request

        except Exception as e:
            logger.error("Failed to create approval request", error=str(e))
            raise DatabaseError(f"Approval request failed: {str(e)}", "request_approval")

    async def process_approval_response(
        self,
        approval_id: str,
        approver_id: str,
        action: str,
        comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        承認レスポンス処理

        Args:
            approval_id: 承認ID
            approver_id: 承認者ID
            action: アクション (approve/reject)
            comment: コメント

        Returns:
            Dict[str, Any]: 処理結果
        """
        try:
            # 承認記録を取得
            approval_record = await self._get_approval_record(approval_id)

            if approval_record["status"] != ApprovalStatus.PENDING:
                raise ValueError(f"Approval already {approval_record['status']}")

            # 承認者権限チェック
            if approver_id not in approval_record["approvers"]:
                raise ValueError("Unauthorized approver")

            # アクション処理
            if action == "approve":
                result = await self._approve_remediation(approval_record, approver_id, comment)
            elif action == "reject":
                result = await self._reject_remediation(approval_record, approver_id, comment)
            else:
                raise ValueError(f"Invalid action: {action}")

            # 監査ログ記録
            await self._log_approval_action(approval_record, approver_id, action, comment)

            logger.info(
                "Approval response processed",
                approval_id=approval_id,
                approver_id=approver_id,
                action=action,
            )

            return result

        except Exception as e:
            logger.error("Failed to process approval response", error=str(e))
            raise DatabaseError(f"Approval processing failed: {str(e)}", "process_approval_response")

    async def check_expired_approvals(self) -> List[Dict[str, Any]]:
        """
        期限切れ承認をチェック

        Returns:
            List[Dict[str, Any]]: 期限切れ承認リスト
        """
        try:
            # 期限切れ承認を検索（実装は簡略化）
            expired_approvals = []

            # TODO: データベースから期限切れの承認を取得
            # 現在は仮実装

            for approval in expired_approvals:
                await self._expire_approval(approval["id"])

            logger.info("Expired approvals processed", count=len(expired_approvals))

            return expired_approvals

        except Exception as e:
            logger.error("Failed to check expired approvals", error=str(e))
            return []

    async def get_approval_status(self, approval_id: str) -> Dict[str, Any]:
        """
        承認ステータス取得

        Args:
            approval_id: 承認ID

        Returns:
            Dict[str, Any]: 承認ステータス
        """
        try:
            approval_record = await self._get_approval_record(approval_id)

            return {
                "id": approval_record["id"],
                "incident_id": approval_record["incident_id"],
                "status": approval_record["status"],
                "approval_type": approval_record["approval_type"],
                "approvers": approval_record["approvers"],
                "approved_by": approval_record.get("approved_by"),
                "approved_at": approval_record.get("approved_at"),
                "expires_at": approval_record.get("expires_at"),
                "comment": approval_record.get("comment"),
            }

        except Exception as e:
            logger.error("Failed to get approval status", error=str(e))
            raise DatabaseError(f"Failed to get approval status: {str(e)}", "get_approval_status")

    async def _get_incident(self, incident_id: uuid.UUID) -> Dict[str, Any]:
        """インシデント取得"""
        try:
            stmt = select(ErrorIncident).where(ErrorIncident.id == incident_id)
            result = await self.db.execute(stmt)
            incident = result.scalar_one_or_none()

            if not incident:
                raise NotFoundError("ErrorIncident", str(incident_id))

            return {
                "id": str(incident.id),
                "error_type": incident.error_type,
                "severity": incident.severity,
                "service_name": incident.service_name,
                "environment": incident.environment,
                "error_message": incident.error_message,
                "created_at": incident.created_at.isoformat(),
            }

        except Exception as e:
            logger.error("Failed to get incident", incident_id=str(incident_id), error=str(e))
            raise

    async def _get_approval_config(
        self, incident: Dict[str, Any], approval_type: ApprovalType
    ) -> Dict[str, Any]:
        """承認設定取得"""
        # 重要度とサービスに基づく承認設定
        base_config = {
            "default_approvers": ["admin", "tech-lead"],
            "auto_approve_timeout": 60,  # 60分
            "require_multiple_approvers": False,
        }

        # 重要度別設定
        if incident["severity"] == "critical":
            base_config.update({
                "default_approvers": ["admin", "tech-lead", "security-team"],
                "auto_approve_timeout": 30,
                "require_multiple_approvers": True,
            })
        elif incident["severity"] == "high":
            base_config.update({
                "default_approvers": ["admin", "tech-lead"],
                "auto_approve_timeout": 45,
            })

        # 環境別設定
        if incident["environment"] == "production":
            base_config["require_multiple_approvers"] = True

        return base_config

    async def _create_approval_record(
        self,
        incident_id: uuid.UUID,
        remediation_data: Dict[str, Any],
        approval_type: ApprovalType,
        approvers: List[str],
        auto_approve_after: int,
    ) -> Dict[str, Any]:
        """承認記録作成"""
        approval_id = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(minutes=auto_approve_after)

        # 簡略化された承認記録（実際はデータベースに保存）
        approval_record = {
            "id": approval_id,
            "incident_id": str(incident_id),
            "remediation_data": remediation_data,
            "approval_type": approval_type,
            "status": ApprovalStatus.PENDING,
            "approvers": approvers,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at.isoformat(),
        }

        # TODO: データベースに実際に保存
        logger.debug("Approval record created", approval_id=approval_id)

        return approval_record

    async def _get_approval_record(self, approval_id: str) -> Dict[str, Any]:
        """承認記録取得"""
        # TODO: データベースから取得
        # 現在は仮実装
        approval_record = {
            "id": approval_id,
            "incident_id": "dummy-incident-id",
            "status": ApprovalStatus.PENDING,
            "approval_type": ApprovalType.MANUAL,
            "approvers": ["admin", "tech-lead"],
            "created_at": datetime.utcnow().isoformat(),
        }

        return approval_record

    async def _auto_approve(self, approval_request: Dict[str, Any]) -> Dict[str, Any]:
        """自動承認処理"""
        approval_request["status"] = ApprovalStatus.APPROVED
        approval_request["approved_by"] = "system"
        approval_request["approved_at"] = datetime.utcnow().isoformat()

        logger.info(
            "Automatic approval granted",
            approval_id=approval_request["id"],
        )

        return {
            "approved": True,
            "approval_type": "automatic",
            "approved_by": "system",
            "message": "Automatically approved based on configuration",
        }

    async def _emergency_approve(
        self, approval_request: Dict[str, Any], slack_channel: Optional[str]
    ) -> Dict[str, Any]:
        """緊急承認処理"""
        approval_request["status"] = ApprovalStatus.APPROVED
        approval_request["approved_by"] = "emergency_system"
        approval_request["approved_at"] = datetime.utcnow().isoformat()

        # 緊急承認の通知
        if self.slack_service.is_configured() and slack_channel:
            await self.slack_service.send_error_notification(
                channel=slack_channel,
                incident_data={"error_type": "Emergency approval granted"},
                severity="critical"
            )

        logger.warning(
            "Emergency approval granted",
            approval_id=approval_request["id"],
        )

        return {
            "approved": True,
            "approval_type": "emergency",
            "approved_by": "emergency_system",
            "message": "Emergency approval granted due to critical severity",
        }

    async def _approve_remediation(
        self, approval_record: Dict[str, Any], approver_id: str, comment: Optional[str]
    ) -> Dict[str, Any]:
        """改修承認処理"""
        approval_record["status"] = ApprovalStatus.APPROVED
        approval_record["approved_by"] = approver_id
        approval_record["approved_at"] = datetime.utcnow().isoformat()
        approval_record["comment"] = comment

        return {
            "approved": True,
            "approved_by": approver_id,
            "approved_at": approval_record["approved_at"],
            "comment": comment,
            "message": "Remediation approved successfully",
        }

    async def _reject_remediation(
        self, approval_record: Dict[str, Any], approver_id: str, comment: Optional[str]
    ) -> Dict[str, Any]:
        """改修却下処理"""
        approval_record["status"] = ApprovalStatus.REJECTED
        approval_record["rejected_by"] = approver_id
        approval_record["rejected_at"] = datetime.utcnow().isoformat()
        approval_record["comment"] = comment

        return {
            "approved": False,
            "rejected_by": approver_id,
            "rejected_at": approval_record["rejected_at"],
            "comment": comment,
            "message": "Remediation rejected",
        }

    async def _expire_approval(self, approval_id: str) -> None:
        """承認期限切れ処理"""
        # TODO: データベース更新
        logger.info("Approval expired", approval_id=approval_id)

    async def _log_approval_action(
        self,
        approval_record: Dict[str, Any],
        user_id: str,
        action: str,
        comment: Optional[str],
    ) -> None:
        """承認アクション監査ログ"""
        try:
            audit_log = AuditLog(
                user_id=uuid.UUID(user_id) if user_id != "system" else None,
                action=f"approval_{action}",
                resource_type="approval",
                resource_id=uuid.UUID(approval_record["id"]),
                details={
                    "incident_id": approval_record["incident_id"],
                    "action": action,
                    "comment": comment,
                    "approval_type": approval_record["approval_type"],
                },
            )

            self.db.add(audit_log)
            await self.db.commit()

            logger.info(
                "Approval action logged",
                approval_id=approval_record["id"],
                user_id=user_id,
                action=action,
            )

        except Exception as e:
            logger.error("Failed to log approval action", error=str(e))
            # 監査ログ失敗は処理を止めない
