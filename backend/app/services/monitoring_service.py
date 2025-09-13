"""
リアルタイムエラー監視サービス
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import DatabaseError
from app.models.error import ErrorIncident
from app.services.error_service import ErrorService
from app.services.slack_service import SlackService

logger = structlog.get_logger()
settings = get_settings()


class AlertRule:
    """アラートルール"""

    def __init__(
        self,
        name: str,
        condition: str,
        threshold: int,
        time_window: int,  # minutes
        severity: str = "medium",
        channels: Optional[List[str]] = None,
        enabled: bool = True,
    ):
        self.name = name
        self.condition = condition
        self.threshold = threshold
        self.time_window = time_window
        self.severity = severity
        self.channels = channels or []
        self.enabled = enabled
        self.last_triggered = None


class MonitoringService:
    """リアルタイムエラー監視サービス"""

    def __init__(self, db: AsyncSession, slack_service: Optional[SlackService] = None):
        self.db = db
        self.slack_service = slack_service or SlackService()
        self.alert_rules: List[AlertRule] = []
        self.active_alerts: Set[str] = set()
        self._monitoring_task = None
        self._setup_default_rules()

    def _setup_default_rules(self):
        """デフォルトアラートルール設定"""
        self.alert_rules = [
            AlertRule(
                name="critical_error_spike",
                condition="critical_errors",
                threshold=3,
                time_window=5,
                severity="critical",
                channels=["alerts-critical"],
            ),
            AlertRule(
                name="high_error_rate",
                condition="error_rate",
                threshold=10,
                time_window=10,
                severity="high",
                channels=["alerts-high"],
            ),
            AlertRule(
                name="service_error_spike",
                condition="service_errors",
                threshold=5,
                time_window=15,
                severity="medium",
                channels=["alerts-medium"],
            ),
            AlertRule(
                name="remediation_failure_rate",
                condition="remediation_failures",
                threshold=3,
                time_window=30,
                severity="high",
                channels=["alerts-remediation"],
            ),
        ]

    async def start_monitoring(self):
        """監視開始"""
        if self._monitoring_task and not self._monitoring_task.done():
            logger.warning("Monitoring already running")
            return

        logger.info("Starting error monitoring service")
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())

    async def stop_monitoring(self):
        """監視停止"""
        if self._monitoring_task and not self._monitoring_task.done():
            logger.info("Stopping error monitoring service")
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

    async def _monitoring_loop(self):
        """監視メインループ"""
        try:
            while True:
                await self._check_alert_rules()
                await asyncio.sleep(60)  # 1分間隔で監視
        except asyncio.CancelledError:
            logger.info("Monitoring loop cancelled")
        except Exception as e:
            logger.error("Monitoring loop error", error=str(e))

    async def _check_alert_rules(self):
        """アラートルールチェック"""
        try:
            for rule in self.alert_rules:
                if not rule.enabled:
                    continue

                should_trigger = await self._evaluate_rule(rule)

                if should_trigger:
                    await self._trigger_alert(rule)
                else:
                    # アラートが解決された場合
                    alert_key = f"{rule.name}"
                    if alert_key in self.active_alerts:
                        await self._resolve_alert(rule)

        except Exception as e:
            logger.error("Failed to check alert rules", error=str(e))

    async def _evaluate_rule(self, rule: AlertRule) -> bool:
        """ルール評価"""
        try:
            time_window_start = datetime.utcnow() - timedelta(minutes=rule.time_window)

            if rule.condition == "critical_errors":
                return await self._check_critical_errors(time_window_start, rule.threshold)
            elif rule.condition == "error_rate":
                return await self._check_error_rate(time_window_start, rule.threshold)
            elif rule.condition == "service_errors":
                return await self._check_service_errors(time_window_start, rule.threshold)
            elif rule.condition == "remediation_failures":
                return await self._check_remediation_failures(time_window_start, rule.threshold)

            return False

        except Exception as e:
            logger.error("Failed to evaluate rule", rule_name=rule.name, error=str(e))
            return False

    async def _check_critical_errors(self, since: datetime, threshold: int) -> bool:
        """クリティカルエラー数チェック"""
        try:
            stmt = select(func.count(ErrorIncident.id)).where(
                ErrorIncident.severity == "critical",
                ErrorIncident.created_at >= since,
            )
            result = await self.db.execute(stmt)
            count = result.scalar() or 0

            return count >= threshold

        except Exception as e:
            logger.error("Failed to check critical errors", error=str(e))
            return False

    async def _check_error_rate(self, since: datetime, threshold: int) -> bool:
        """エラー発生率チェック"""
        try:
            stmt = select(func.count(ErrorIncident.id)).where(
                ErrorIncident.created_at >= since,
            )
            result = await self.db.execute(stmt)
            count = result.scalar() or 0

            # 時間窓での発生率を計算（簡略化）
            return count >= threshold

        except Exception as e:
            logger.error("Failed to check error rate", error=str(e))
            return False

    async def _check_service_errors(self, since: datetime, threshold: int) -> bool:
        """サービス別エラー数チェック"""
        try:
            # 特定サービスで閾値を超えるエラーがあるかチェック
            stmt = (
                select(ErrorIncident.service_name, func.count(ErrorIncident.id))
                .where(ErrorIncident.created_at >= since)
                .group_by(ErrorIncident.service_name)
                .having(func.count(ErrorIncident.id) >= threshold)
            )
            result = await self.db.execute(stmt)
            services_with_errors = result.fetchall()

            return len(services_with_errors) > 0

        except Exception as e:
            logger.error("Failed to check service errors", error=str(e))
            return False

    async def _check_remediation_failures(self, since: datetime, threshold: int) -> bool:
        """改修失敗率チェック"""
        try:
            # TODO: RemediationAttemptモデルを使用して失敗率をチェック
            # 現在は簡略化実装
            return False

        except Exception as e:
            logger.error("Failed to check remediation failures", error=str(e))
            return False

    async def _trigger_alert(self, rule: AlertRule):
        """アラート発火"""
        try:
            alert_key = f"{rule.name}"

            # 重複アラートを防ぐ
            if alert_key in self.active_alerts:
                return

            self.active_alerts.add(alert_key)
            rule.last_triggered = datetime.utcnow()

            # アラートメトリクスを取得
            metrics = await self._get_alert_metrics(rule)

            # Slack通知
            if self.slack_service.is_configured():
                for channel in rule.channels:
                    await self._send_alert_notification(channel, rule, metrics)

            logger.warning(
                "Alert triggered",
                rule_name=rule.name,
                severity=rule.severity,
                metrics=metrics,
            )

        except Exception as e:
            logger.error("Failed to trigger alert", rule_name=rule.name, error=str(e))

    async def _resolve_alert(self, rule: AlertRule):
        """アラート解決"""
        try:
            alert_key = f"{rule.name}"

            if alert_key in self.active_alerts:
                self.active_alerts.remove(alert_key)

                # 解決通知
                if self.slack_service.is_configured():
                    for channel in rule.channels:
                        await self._send_resolution_notification(channel, rule)

                logger.info("Alert resolved", rule_name=rule.name)

        except Exception as e:
            logger.error("Failed to resolve alert", rule_name=rule.name, error=str(e))

    async def _get_alert_metrics(self, rule: AlertRule) -> Dict[str, Any]:
        """アラートメトリクス取得"""
        try:
            time_window_start = datetime.utcnow() - timedelta(minutes=rule.time_window)

            # 基本メトリクス
            total_errors_stmt = select(func.count(ErrorIncident.id)).where(
                ErrorIncident.created_at >= time_window_start
            )
            total_errors_result = await self.db.execute(total_errors_stmt)
            total_errors = total_errors_result.scalar() or 0

            # 重要度別
            severity_stmt = (
                select(ErrorIncident.severity, func.count(ErrorIncident.id))
                .where(ErrorIncident.created_at >= time_window_start)
                .group_by(ErrorIncident.severity)
            )
            severity_result = await self.db.execute(severity_stmt)
            severity_breakdown = {
                severity: count for severity, count in severity_result.fetchall()
            }

            # サービス別
            service_stmt = (
                select(ErrorIncident.service_name, func.count(ErrorIncident.id))
                .where(ErrorIncident.created_at >= time_window_start)
                .group_by(ErrorIncident.service_name)
                .order_by(func.count(ErrorIncident.id).desc())
                .limit(5)
            )
            service_result = await self.db.execute(service_stmt)
            top_services = {
                service: count for service, count in service_result.fetchall()
            }

            return {
                "time_window_minutes": rule.time_window,
                "total_errors": total_errors,
                "severity_breakdown": severity_breakdown,
                "top_services": top_services,
                "threshold": rule.threshold,
                "condition": rule.condition,
            }

        except Exception as e:
            logger.error("Failed to get alert metrics", error=str(e))
            return {}

    async def _send_alert_notification(
        self, channel: str, rule: AlertRule, metrics: Dict[str, Any]
    ):
        """アラート通知送信"""
        try:
            alert_data = {
                "error_type": f"Monitoring Alert: {rule.name}",
                "severity": rule.severity,
                "service_name": "monitoring_system",
                "environment": "production",
                "error_message": f"Alert rule '{rule.name}' triggered with threshold {rule.threshold}",
                "id": str(uuid.uuid4()),
                "created_at": datetime.utcnow().isoformat(),
                "metrics": metrics,
            }

            await self.slack_service.send_error_notification(
                channel=channel,
                incident_data=alert_data,
                severity=rule.severity,
            )

        except Exception as e:
            logger.error("Failed to send alert notification", error=str(e))

    async def _send_resolution_notification(self, channel: str, rule: AlertRule):
        """解決通知送信"""
        try:
            if not self.slack_service.is_configured():
                return

            resolution_data = {
                "error_type": f"Alert Resolved: {rule.name}",
                "service_name": "monitoring_system",
                "id": str(uuid.uuid4()),
            }

            remediation_data = {
                "explanation": f"Alert rule '{rule.name}' has been resolved",
                "service_used": "monitoring_system",
            }

            await self.slack_service.send_remediation_notification(
                channel=channel,
                incident_data=resolution_data,
                remediation_data=remediation_data,
                status="resolved",
            )

        except Exception as e:
            logger.error("Failed to send resolution notification", error=str(e))

    async def get_monitoring_status(self) -> Dict[str, Any]:
        """監視ステータス取得"""
        try:
            return {
                "monitoring_active": self._monitoring_task and not self._monitoring_task.done(),
                "active_alerts": len(self.active_alerts),
                "alert_rules_count": len([r for r in self.alert_rules if r.enabled]),
                "total_rules": len(self.alert_rules),
                "active_alert_names": list(self.active_alerts),
                "last_check": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error("Failed to get monitoring status", error=str(e))
            return {"error": str(e)}

    async def add_alert_rule(self, rule: AlertRule) -> bool:
        """アラートルール追加"""
        try:
            # 重複チェック
            existing_rule = next((r for r in self.alert_rules if r.name == rule.name), None)
            if existing_rule:
                logger.warning("Alert rule already exists", rule_name=rule.name)
                return False

            self.alert_rules.append(rule)
            logger.info("Alert rule added", rule_name=rule.name)
            return True

        except Exception as e:
            logger.error("Failed to add alert rule", rule_name=rule.name, error=str(e))
            return False

    async def remove_alert_rule(self, rule_name: str) -> bool:
        """アラートルール削除"""
        try:
            rule_to_remove = next((r for r in self.alert_rules if r.name == rule_name), None)
            if not rule_to_remove:
                logger.warning("Alert rule not found", rule_name=rule_name)
                return False

            self.alert_rules.remove(rule_to_remove)

            # アクティブアラートからも削除
            alert_key = f"{rule_name}"
            if alert_key in self.active_alerts:
                self.active_alerts.remove(alert_key)

            logger.info("Alert rule removed", rule_name=rule_name)
            return True

        except Exception as e:
            logger.error("Failed to remove alert rule", rule_name=rule_name, error=str(e))
            return False

    async def get_system_health_metrics(self) -> Dict[str, Any]:
        """システムヘルスメトリクス取得"""
        try:
            now = datetime.utcnow()
            last_24h = now - timedelta(hours=24)
            last_1h = now - timedelta(hours=1)

            # 24時間のエラー統計
            total_errors_24h_stmt = select(func.count(ErrorIncident.id)).where(
                ErrorIncident.created_at >= last_24h
            )
            total_errors_24h_result = await self.db.execute(total_errors_24h_stmt)
            total_errors_24h = total_errors_24h_result.scalar() or 0

            # 1時間のエラー統計
            total_errors_1h_stmt = select(func.count(ErrorIncident.id)).where(
                ErrorIncident.created_at >= last_1h
            )
            total_errors_1h_result = await self.db.execute(total_errors_1h_stmt)
            total_errors_1h = total_errors_1h_result.scalar() or 0

            # クリティカルエラー
            critical_errors_stmt = select(func.count(ErrorIncident.id)).where(
                ErrorIncident.severity == "critical",
                ErrorIncident.created_at >= last_24h,
            )
            critical_errors_result = await self.db.execute(critical_errors_stmt)
            critical_errors = critical_errors_result.scalar() or 0

            # 解決済みエラー
            resolved_errors_stmt = select(func.count(ErrorIncident.id)).where(
                ErrorIncident.status == "resolved",
                ErrorIncident.created_at >= last_24h,
            )
            resolved_errors_result = await self.db.execute(resolved_errors_stmt)
            resolved_errors = resolved_errors_result.scalar() or 0

            # 解決率計算
            resolution_rate = (resolved_errors / total_errors_24h * 100) if total_errors_24h > 0 else 0

            return {
                "timestamp": now.isoformat(),
                "errors_24h": total_errors_24h,
                "errors_1h": total_errors_1h,
                "critical_errors_24h": critical_errors,
                "resolved_errors_24h": resolved_errors,
                "resolution_rate_24h": round(resolution_rate, 2),
                "active_alerts": len(self.active_alerts),
                "monitoring_active": self._monitoring_task and not self._monitoring_task.done(),
            }

        except Exception as e:
            logger.error("Failed to get system health metrics", error=str(e))
            return {"error": str(e)}
