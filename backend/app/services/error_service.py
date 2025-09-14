"""
エラー管理サービス
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import DatabaseError, NotFoundError
from app.models.error import ErrorIncident, RemediationAttempt

logger = structlog.get_logger()


class ErrorService:
    """エラー管理サービス"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_incident(
        self,
        error_type: str,
        severity: str,
        service_name: str,
        environment: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
        language: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ErrorIncident:
        """
        エラーインシデント作成

        Args:
            error_type: エラータイプ
            severity: 重要度
            service_name: サービス名
            environment: 環境
            error_message: エラーメッセージ
            stack_trace: スタックトレース
            file_path: ファイルパス
            line_number: 行番号
            language: プログラミング言語
            metadata: 追加メタデータ

        Returns:
            ErrorIncident: 作成されたインシデント
        """
        try:
            # 既存の同様インシデントをチェック
            existing_incident = await self._find_similar_incident(
                error_type, service_name, environment, error_message
            )

            if existing_incident:
                # 既存インシデントの発生回数を更新
                existing_incident.occurrence_count += 1
                await self.db.commit()
                await self.db.refresh(existing_incident)

                logger.info(
                    "Updated existing incident",
                    incident_id=str(existing_incident.id),
                    occurrence_count=existing_incident.occurrence_count,
                )

                return existing_incident

            # 新規インシデント作成
            incident = ErrorIncident(
                error_type=error_type,
                severity=severity,
                service_name=service_name,
                environment=environment,
                error_message=error_message,
                stack_trace=stack_trace,
                file_path=file_path,
                line_number=line_number,
                language=language,
                occurrence_count=1,
                status="open"  # デフォルトステータスを設定
            )

            self.db.add(incident)
            await self.db.commit()
            await self.db.refresh(incident)

            logger.info(
                "Error incident created",
                incident_id=str(incident.id),
                error_type=error_type,
                severity=severity,
                service_name=service_name,
            )

            return incident

        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Failed to create error incident",
                error_type=error_type,
                service_name=service_name,
                error=str(e),
            )
            raise DatabaseError(
                f"Failed to create error incident: {str(e)}", "create_incident"
            )

    async def get_incident(self, incident_id: uuid.UUID) -> Optional[ErrorIncident]:
        """
        エラーインシデント取得

        Args:
            incident_id: インシデントID

        Returns:
            Optional[ErrorIncident]: インシデント情報
        """
        try:
            stmt = (
                select(ErrorIncident)
                .where(ErrorIncident.id == incident_id)
                .options(selectinload(ErrorIncident.remediation_attempts))
            )
            result = await self.db.execute(stmt)
            incident = result.scalar_one_or_none()

            if incident:
                logger.debug(
                    "Error incident retrieved", incident_id=str(incident_id)
                )

            return incident

        except Exception as e:
            logger.error(
                "Failed to get error incident",
                incident_id=str(incident_id),
                error=str(e),
            )
            raise DatabaseError(
                f"Failed to get error incident: {str(e)}", "get_incident"
            )

    async def get_incidents(
        self,
        service_name: Optional[str] = None,
        environment: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ErrorIncident]:
        """
        エラーインシデント一覧取得

        Args:
            service_name: サービス名フィルター
            environment: 環境フィルター
            severity: 重要度フィルター
            status: ステータスフィルター
            limit: 取得件数上限
            offset: オフセット

        Returns:
            List[ErrorIncident]: インシデント一覧
        """
        try:
            stmt = select(ErrorIncident).order_by(desc(ErrorIncident.last_occurred))

            # フィルター適用
            if service_name:
                stmt = stmt.where(ErrorIncident.service_name == service_name)
            if environment:
                stmt = stmt.where(ErrorIncident.environment == environment)
            if severity:
                stmt = stmt.where(ErrorIncident.severity == severity)
            if status:
                stmt = stmt.where(ErrorIncident.status == status)

            stmt = stmt.limit(limit).offset(offset)

            result = await self.db.execute(stmt)
            incidents = result.scalars().all()

            logger.debug(
                "Error incidents retrieved",
                count=len(incidents),
                filters={
                    "service_name": service_name,
                    "environment": environment,
                    "severity": severity,
                    "status": status,
                },
            )

            return list(incidents)

        except Exception as e:
            logger.error("Failed to get error incidents", error=str(e))
            raise DatabaseError(
                f"Failed to get error incidents: {str(e)}", "get_incidents"
            )

    async def get_incidents_with_count(
        self,
        service_name: Optional[str] = None,
        environment: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[ErrorIncident], int]:
        """
        エラーインシデント一覧と総件数を取得

        Args:
            service_name: サービス名フィルター
            environment: 環境フィルター
            severity: 重要度フィルター
            status: ステータスフィルター
            limit: 取得件数上限
            offset: オフセット

        Returns:
            tuple[List[ErrorIncident], int]: インシデント一覧と総件数
        """
        try:
            # 基本クエリ
            base_stmt = select(ErrorIncident)

            # フィルター適用
            if service_name:
                base_stmt = base_stmt.where(ErrorIncident.service_name == service_name)
            if environment:
                base_stmt = base_stmt.where(ErrorIncident.environment == environment)
            if severity:
                base_stmt = base_stmt.where(ErrorIncident.severity == severity)
            if status:
                base_stmt = base_stmt.where(ErrorIncident.status == status)

            # 総件数取得
            count_stmt = select(func.count()).select_from(base_stmt.subquery())
            count_result = await self.db.execute(count_stmt)
            total_count = count_result.scalar()

            # ページング適用してデータ取得
            incidents_stmt = base_stmt.order_by(desc(ErrorIncident.last_occurred)).limit(limit).offset(offset)
            incidents_result = await self.db.execute(incidents_stmt)
            incidents = incidents_result.scalars().all()

            logger.debug(
                "Error incidents with count retrieved",
                count=len(incidents),
                total_count=total_count,
                filters={
                    "service_name": service_name,
                    "environment": environment,
                    "severity": severity,
                    "status": status,
                },
            )

            return list(incidents), total_count

        except Exception as e:
            logger.error("Failed to get error incidents with count", error=str(e))
            raise DatabaseError(
                f"Failed to get error incidents with count: {str(e)}", "get_incidents_with_count"
            )

    async def update_incident_status(
        self, incident_id: uuid.UUID, status: str
    ) -> ErrorIncident:
        """
        インシデントステータス更新

        Args:
            incident_id: インシデントID
            status: 新しいステータス

        Returns:
            ErrorIncident: 更新されたインシデント
        """
        try:
            incident = await self.get_incident(incident_id)
            if not incident:
                raise NotFoundError("ErrorIncident", str(incident_id))

            incident.status = status
            await self.db.commit()
            await self.db.refresh(incident)

            logger.info(
                "Incident status updated",
                incident_id=str(incident_id),
                new_status=status,
            )

            return incident

        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Failed to update incident status",
                incident_id=str(incident_id),
                status=status,
                error=str(e),
            )
            raise DatabaseError(
                f"Failed to update incident status: {str(e)}",
                "update_incident_status",
            )

    async def create_remediation_attempt(
        self,
        incident_id: uuid.UUID,
        remediation_type: str,
        description: Optional[str] = None,
    ) -> RemediationAttempt:
        """
        改修試行作成

        Args:
            incident_id: インシデントID
            remediation_type: 改修タイプ
            description: 改修説明

        Returns:
            RemediationAttempt: 作成された改修試行
        """
        try:
            # インシデント存在確認
            incident = await self.get_incident(incident_id)
            if not incident:
                raise NotFoundError("ErrorIncident", str(incident_id))

            attempt = RemediationAttempt(
                incident_id=incident_id,
                remediation_type=remediation_type,
                description=description,
            )

            self.db.add(attempt)
            await self.db.commit()
            await self.db.refresh(attempt)

            logger.info(
                "Remediation attempt created",
                attempt_id=str(attempt.id),
                incident_id=str(incident_id),
                remediation_type=remediation_type,
            )

            return attempt

        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Failed to create remediation attempt",
                incident_id=str(incident_id),
                remediation_type=remediation_type,
                error=str(e),
            )
            raise DatabaseError(
                f"Failed to create remediation attempt: {str(e)}",
                "create_remediation_attempt",
            )

    async def get_remediation_attempt(
        self, attempt_id: uuid.UUID
    ) -> Optional[RemediationAttempt]:
        """
        改修試行取得

        Args:
            attempt_id: 改修試行ID

        Returns:
            Optional[RemediationAttempt]: 改修試行情報
        """
        try:
            stmt = select(RemediationAttempt).where(
                RemediationAttempt.id == attempt_id
            )
            result = await self.db.execute(stmt)
            attempt = result.scalar_one_or_none()

            if attempt:
                logger.debug(
                    "Remediation attempt retrieved", attempt_id=str(attempt_id)
                )

            return attempt

        except Exception as e:
            logger.error(
                "Failed to get remediation attempt",
                attempt_id=str(attempt_id),
                error=str(e),
            )
            raise DatabaseError(
                f"Failed to get remediation attempt: {str(e)}",
                "get_remediation_attempt",
            )

    async def update_remediation_attempt(
        self,
        attempt_id: uuid.UUID,
        status: Optional[str] = None,
        analysis_result: Optional[Dict[str, Any]] = None,
        fix_code: Optional[str] = None,
        test_results: Optional[Dict[str, Any]] = None,
        pr_url: Optional[str] = None,
    ) -> RemediationAttempt:
        """
        改修試行更新

        Args:
            attempt_id: 改修試行ID
            status: ステータス
            analysis_result: 解析結果
            fix_code: 修正コード
            test_results: テスト結果
            pr_url: PR URL

        Returns:
            RemediationAttempt: 更新された改修試行
        """
        try:
            attempt = await self.get_remediation_attempt(attempt_id)
            if not attempt:
                raise NotFoundError("RemediationAttempt", str(attempt_id))

            if status is not None:
                attempt.status = status
            if analysis_result is not None:
                attempt.analysis_result = analysis_result
            if fix_code is not None:
                attempt.fix_code = fix_code
            if test_results is not None:
                attempt.test_results = test_results
            if pr_url is not None:
                attempt.pr_url = pr_url

            await self.db.commit()
            await self.db.refresh(attempt)

            logger.info(
                "Remediation attempt updated",
                attempt_id=str(attempt_id),
                status=status,
            )

            return attempt

        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Failed to update remediation attempt",
                attempt_id=str(attempt_id),
                error=str(e),
            )
            raise DatabaseError(
                f"Failed to update remediation attempt: {str(e)}",
                "update_remediation_attempt",
            )

    async def _find_similar_incident(
        self, error_type: str, service_name: str, environment: str, error_message: str
    ) -> Optional[ErrorIncident]:
        """
        類似インシデント検索（内部メソッド）

        Args:
            error_type: エラータイプ
            service_name: サービス名
            environment: 環境
            error_message: エラーメッセージ

        Returns:
            Optional[ErrorIncident]: 類似インシデント
        """
        try:
            stmt = select(ErrorIncident).where(
                ErrorIncident.error_type == error_type,
                ErrorIncident.service_name == service_name,
                ErrorIncident.environment == environment,
                ErrorIncident.error_message == error_message,
                ErrorIncident.status.in_(["open", "investigating"]),
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.warning(
                "Failed to find similar incident",
                error_type=error_type,
                service_name=service_name,
                error=str(e),
            )
            return None
