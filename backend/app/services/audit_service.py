"""
監査ログサービス
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DatabaseError
from app.models.audit import AuditLog
from app.models.user import User

logger = structlog.get_logger()


class AuditService:
    """監査ログサービス"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_action(
        self,
        user_id: Optional[uuid.UUID],
        action: str,
        resource_type: str,
        resource_id: Optional[uuid.UUID] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        アクション監査ログ記録

        Args:
            user_id: ユーザーID（システムアクションの場合はNone）
            action: アクション名
            resource_type: リソースタイプ
            resource_id: リソースID
            details: 詳細情報
            ip_address: IPアドレス
            user_agent: ユーザーエージェント

        Returns:
            AuditLog: 作成された監査ログ
        """
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent,
            )

            self.db.add(audit_log)
            await self.db.commit()
            await self.db.refresh(audit_log)

            logger.info(
                "Audit log created",
                log_id=str(audit_log.id),
                user_id=str(user_id) if user_id else "system",
                action=action,
                resource_type=resource_type,
            )

            return audit_log

        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to create audit log", error=str(e))
            raise DatabaseError(f"Failed to create audit log: {str(e)}", "log_action")

    async def get_audit_logs(
        self,
        user_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """
        監査ログ取得

        Args:
            user_id: ユーザーIDフィルター
            action: アクションフィルター
            resource_type: リソースタイプフィルター
            resource_id: リソースIDフィルター
            start_date: 開始日時
            end_date: 終了日時
            limit: 取得件数上限
            offset: オフセット

        Returns:
            List[AuditLog]: 監査ログリスト
        """
        try:
            stmt = select(AuditLog).order_by(desc(AuditLog.created_at))

            # フィルター適用
            if user_id:
                stmt = stmt.where(AuditLog.user_id == user_id)
            if action:
                stmt = stmt.where(AuditLog.action == action)
            if resource_type:
                stmt = stmt.where(AuditLog.resource_type == resource_type)
            if resource_id:
                stmt = stmt.where(AuditLog.resource_id == resource_id)
            if start_date:
                stmt = stmt.where(AuditLog.created_at >= start_date)
            if end_date:
                stmt = stmt.where(AuditLog.created_at <= end_date)

            stmt = stmt.limit(limit).offset(offset)

            result = await self.db.execute(stmt)
            audit_logs = result.scalars().all()

            logger.debug(
                "Audit logs retrieved",
                count=len(audit_logs),
                filters={
                    "user_id": str(user_id) if user_id else None,
                    "action": action,
                    "resource_type": resource_type,
                },
            )

            return list(audit_logs)

        except Exception as e:
            logger.error("Failed to get audit logs", error=str(e))
            raise DatabaseError(f"Failed to get audit logs: {str(e)}", "get_audit_logs")

    async def get_user_activity_summary(
        self,
        user_id: uuid.UUID,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        ユーザーアクティビティサマリー取得

        Args:
            user_id: ユーザーID
            days: 集計期間（日数）

        Returns:
            Dict[str, Any]: アクティビティサマリー
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            # 総アクション数
            total_actions_stmt = select(func.count(AuditLog.id)).where(
                AuditLog.user_id == user_id,
                AuditLog.created_at >= start_date,
            )
            total_actions_result = await self.db.execute(total_actions_stmt)
            total_actions = total_actions_result.scalar() or 0

            # アクション別集計
            actions_stmt = (
                select(AuditLog.action, func.count(AuditLog.id))
                .where(
                    AuditLog.user_id == user_id,
                    AuditLog.created_at >= start_date,
                )
                .group_by(AuditLog.action)
                .order_by(desc(func.count(AuditLog.id)))
            )
            actions_result = await self.db.execute(actions_stmt)
            actions_by_type = {action: count for action, count in actions_result.fetchall()}

            # リソースタイプ別集計
            resources_stmt = (
                select(AuditLog.resource_type, func.count(AuditLog.id))
                .where(
                    AuditLog.user_id == user_id,
                    AuditLog.created_at >= start_date,
                )
                .group_by(AuditLog.resource_type)
                .order_by(desc(func.count(AuditLog.id)))
            )
            resources_result = await self.db.execute(resources_stmt)
            resources_by_type = {
                resource_type: count for resource_type, count in resources_result.fetchall()
            }

            # 最近のアクティビティ
            recent_logs = await self.get_audit_logs(
                user_id=user_id,
                start_date=start_date,
                limit=10,
            )

            summary = {
                "user_id": str(user_id),
                "period_days": days,
                "total_actions": total_actions,
                "actions_by_type": actions_by_type,
                "resources_by_type": resources_by_type,
                "recent_activity": [
                    {
                        "action": log.action,
                        "resource_type": log.resource_type,
                        "resource_id": str(log.resource_id) if log.resource_id else None,
                        "created_at": log.created_at.isoformat(),
                    }
                    for log in recent_logs
                ],
            }

            logger.info(
                "User activity summary generated",
                user_id=str(user_id),
                total_actions=total_actions,
                period_days=days,
            )

            return summary

        except Exception as e:
            logger.error("Failed to get user activity summary", error=str(e))
            raise DatabaseError(
                f"Failed to get user activity summary: {str(e)}",
                "get_user_activity_summary",
            )

    async def get_system_activity_summary(
        self, days: int = 7
    ) -> Dict[str, Any]:
        """
        システムアクティビティサマリー取得

        Args:
            days: 集計期間（日数）

        Returns:
            Dict[str, Any]: システムアクティビティサマリー
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            # 総アクション数
            total_actions_stmt = select(func.count(AuditLog.id)).where(
                AuditLog.created_at >= start_date
            )
            total_actions_result = await self.db.execute(total_actions_stmt)
            total_actions = total_actions_result.scalar() or 0

            # ユーザーアクション vs システムアクション
            user_actions_stmt = select(func.count(AuditLog.id)).where(
                AuditLog.created_at >= start_date,
                AuditLog.user_id.isnot(None),
            )
            user_actions_result = await self.db.execute(user_actions_stmt)
            user_actions = user_actions_result.scalar() or 0

            system_actions = total_actions - user_actions

            # 日別アクティビティ
            daily_activity_stmt = (
                select(
                    func.date(AuditLog.created_at).label('date'),
                    func.count(AuditLog.id).label('count')
                )
                .where(AuditLog.created_at >= start_date)
                .group_by(func.date(AuditLog.created_at))
                .order_by(func.date(AuditLog.created_at))
            )
            daily_activity_result = await self.db.execute(daily_activity_stmt)
            daily_activity = [
                {
                    "date": date.isoformat(),
                    "count": count
                }
                for date, count in daily_activity_result.fetchall()
            ]

            # 上位アクション
            top_actions_stmt = (
                select(AuditLog.action, func.count(AuditLog.id))
                .where(AuditLog.created_at >= start_date)
                .group_by(AuditLog.action)
                .order_by(desc(func.count(AuditLog.id)))
                .limit(10)
            )
            top_actions_result = await self.db.execute(top_actions_stmt)
            top_actions = {action: count for action, count in top_actions_result.fetchall()}

            # アクティブユーザー数
            active_users_stmt = select(func.count(func.distinct(AuditLog.user_id))).where(
                AuditLog.created_at >= start_date,
                AuditLog.user_id.isnot(None),
            )
            active_users_result = await self.db.execute(active_users_stmt)
            active_users = active_users_result.scalar() or 0

            summary = {
                "period_days": days,
                "total_actions": total_actions,
                "user_actions": user_actions,
                "system_actions": system_actions,
                "active_users": active_users,
                "daily_activity": daily_activity,
                "top_actions": top_actions,
                "generated_at": datetime.utcnow().isoformat(),
            }

            logger.info(
                "System activity summary generated",
                total_actions=total_actions,
                period_days=days,
            )

            return summary

        except Exception as e:
            logger.error("Failed to get system activity summary", error=str(e))
            raise DatabaseError(
                f"Failed to get system activity summary: {str(e)}",
                "get_system_activity_summary",
            )

    async def log_error_incident_action(
        self,
        user_id: Optional[uuid.UUID],
        action: str,
        incident_id: uuid.UUID,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """
        エラーインシデントアクション記録

        Args:
            user_id: ユーザーID
            action: アクション（created, analyzed, remediated, etc.）
            incident_id: インシデントID
            details: 詳細情報

        Returns:
            AuditLog: 監査ログ
        """
        return await self.log_action(
            user_id=user_id,
            action=f"incident_{action}",
            resource_type="error_incident",
            resource_id=incident_id,
            details=details,
        )

    async def log_remediation_action(
        self,
        user_id: Optional[uuid.UUID],
        action: str,
        attempt_id: uuid.UUID,
        incident_id: uuid.UUID,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """
        改修アクション記録

        Args:
            user_id: ユーザーID
            action: アクション（created, approved, executed, etc.）
            attempt_id: 改修試行ID
            incident_id: インシデントID
            details: 詳細情報

        Returns:
            AuditLog: 監査ログ
        """
        remediation_details = {
            "incident_id": str(incident_id),
            **(details or {}),
        }

        return await self.log_action(
            user_id=user_id,
            action=f"remediation_{action}",
            resource_type="remediation_attempt",
            resource_id=attempt_id,
            details=remediation_details,
        )

    async def log_authentication_action(
        self,
        user_id: Optional[uuid.UUID],
        action: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        認証アクション記録

        Args:
            user_id: ユーザーID
            action: アクション（login, logout, failed_login, etc.）
            details: 詳細情報
            ip_address: IPアドレス
            user_agent: ユーザーエージェント

        Returns:
            AuditLog: 監査ログ
        """
        return await self.log_action(
            user_id=user_id,
            action=f"auth_{action}",
            resource_type="authentication",
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def cleanup_old_logs(self, days_to_keep: int = 90) -> int:
        """
        古い監査ログのクリーンアップ

        Args:
            days_to_keep: 保持日数

        Returns:
            int: 削除されたログ数
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

            # 削除対象のログ数を取得
            count_stmt = select(func.count(AuditLog.id)).where(
                AuditLog.created_at < cutoff_date
            )
            count_result = await self.db.execute(count_stmt)
            logs_to_delete = count_result.scalar() or 0

            if logs_to_delete > 0:
                # 古いログを削除
                delete_stmt = AuditLog.__table__.delete().where(
                    AuditLog.created_at < cutoff_date
                )
                await self.db.execute(delete_stmt)
                await self.db.commit()

                logger.info(
                    "Old audit logs cleaned up",
                    deleted_count=logs_to_delete,
                    cutoff_date=cutoff_date.isoformat(),
                )

            return logs_to_delete

        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to cleanup old audit logs", error=str(e))
            raise DatabaseError(f"Failed to cleanup old logs: {str(e)}", "cleanup_old_logs")
