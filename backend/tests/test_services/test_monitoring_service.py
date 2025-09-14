"""
監視サービスのunit test
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

from app.services.monitoring_service import MonitoringService, AlertRule


class TestMonitoringService:
    """監視サービステストクラス"""

    @pytest.fixture
    def mock_db(self):
        """モックデータベースセッション"""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        return mock_db

    @pytest.fixture
    def mock_slack_service(self):
        """モックSlackサービス"""
        mock_slack = Mock()
        mock_slack.is_configured.return_value = True
        mock_slack.send_error_notification = AsyncMock(return_value={"success": True})
        mock_slack.send_remediation_notification = AsyncMock(return_value={"success": True})
        return mock_slack

    @pytest.fixture
    def monitoring_service(self, mock_db, mock_slack_service):
        """監視サービスインスタンス"""
        return MonitoringService(db=mock_db, slack_service=mock_slack_service)

    @pytest.fixture
    def test_alert_rule(self):
        """テスト用アラートルール"""
        return AlertRule(
            name="test_rule",
            condition="critical_errors",
            threshold=5,
            time_window=10,
            severity="high",
            channels=["test-channel"],
            enabled=True
        )

    def test_alert_rule_creation(self):
        """アラートルール作成テスト"""
        # Act
        rule = AlertRule(
            name="test_rule",
            condition="error_rate",
            threshold=10,
            time_window=15,
            severity="medium",
            channels=["alerts"],
            enabled=True
        )

        # Assert
        assert rule.name == "test_rule"
        assert rule.condition == "error_rate"
        assert rule.threshold == 10
        assert rule.time_window == 15
        assert rule.severity == "medium"
        assert rule.channels == ["alerts"]
        assert rule.enabled is True
        assert rule.last_triggered is None

    def test_setup_default_rules(self, monitoring_service):
        """デフォルトルール設定テスト"""
        # Assert
        assert len(monitoring_service.alert_rules) == 4
        
        rule_names = [rule.name for rule in monitoring_service.alert_rules]
        assert "critical_error_spike" in rule_names
        assert "high_error_rate" in rule_names
        assert "service_error_spike" in rule_names
        assert "remediation_failure_rate" in rule_names

    @pytest.mark.asyncio
    async def test_start_monitoring(self, monitoring_service):
        """監視開始テスト"""
        # Act
        await monitoring_service.start_monitoring()

        # Assert
        assert monitoring_service._monitoring_task is not None
        assert not monitoring_service._monitoring_task.done()

        # Cleanup
        await monitoring_service.stop_monitoring()

    @pytest.mark.asyncio
    async def test_stop_monitoring(self, monitoring_service):
        """監視停止テスト"""
        # Arrange
        await monitoring_service.start_monitoring()
        assert monitoring_service._monitoring_task is not None

        # Act
        await monitoring_service.stop_monitoring()

        # Assert
        assert monitoring_service._monitoring_task.cancelled()

    @pytest.mark.asyncio
    async def test_check_critical_errors_above_threshold(self, monitoring_service, mock_db):
        """クリティカルエラーチェック（閾値超過）テスト"""
        # Arrange
        mock_result = Mock()
        mock_result.scalar.return_value = 5  # Above threshold of 3
        mock_db.execute.return_value = mock_result

        since = datetime.utcnow() - timedelta(minutes=5)

        # Act
        result = await monitoring_service._check_critical_errors(since, 3)

        # Assert
        assert result is True
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_critical_errors_below_threshold(self, monitoring_service, mock_db):
        """クリティカルエラーチェック（閾値以下）テスト"""
        # Arrange
        mock_result = Mock()
        mock_result.scalar.return_value = 2  # Below threshold of 3
        mock_db.execute.return_value = mock_result

        since = datetime.utcnow() - timedelta(minutes=5)

        # Act
        result = await monitoring_service._check_critical_errors(since, 3)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_check_error_rate_above_threshold(self, monitoring_service, mock_db):
        """エラー率チェック（閾値超過）テスト"""
        # Arrange
        mock_result = Mock()
        mock_result.scalar.return_value = 15  # Above threshold of 10
        mock_db.execute.return_value = mock_result

        since = datetime.utcnow() - timedelta(minutes=10)

        # Act
        result = await monitoring_service._check_error_rate(since, 10)

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_check_service_errors_with_spike(self, monitoring_service, mock_db):
        """サービスエラーチェック（スパイクあり）テスト"""
        # Arrange
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            ("service1", 8),  # Above threshold of 5
            ("service2", 6),  # Above threshold of 5
        ]
        mock_db.execute.return_value = mock_result

        since = datetime.utcnow() - timedelta(minutes=15)

        # Act
        result = await monitoring_service._check_service_errors(since, 5)

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_evaluate_rule_critical_errors_trigger(self, monitoring_service):
        """ルール評価（クリティカルエラー発火）テスト"""
        # Arrange
        rule = AlertRule(
            name="test_critical",
            condition="critical_errors",
            threshold=3,
            time_window=5,
            severity="critical"
        )

        with patch.object(monitoring_service, '_check_critical_errors') as mock_check:
            mock_check.return_value = True

            # Act
            result = await monitoring_service._evaluate_rule(rule)

            # Assert
            assert result is True
            mock_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_evaluate_rule_no_trigger(self, monitoring_service):
        """ルール評価（発火なし）テスト"""
        # Arrange
        rule = AlertRule(
            name="test_no_trigger",
            condition="critical_errors",
            threshold=3,
            time_window=5,
            severity="critical"
        )

        with patch.object(monitoring_service, '_check_critical_errors') as mock_check:
            mock_check.return_value = False

            # Act
            result = await monitoring_service._evaluate_rule(rule)

            # Assert
            assert result is False

    @pytest.mark.asyncio
    async def test_trigger_alert(self, monitoring_service, test_alert_rule):
        """アラート発火テスト"""
        # Arrange
        with patch.object(monitoring_service, '_get_alert_metrics') as mock_metrics, \
             patch.object(monitoring_service, '_send_alert_notification') as mock_send:
            
            mock_metrics.return_value = {"total_errors": 10}

            # Act
            await monitoring_service._trigger_alert(test_alert_rule)

            # Assert
            assert f"{test_alert_rule.name}" in monitoring_service.active_alerts
            assert test_alert_rule.last_triggered is not None
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_resolve_alert(self, monitoring_service, test_alert_rule):
        """アラート解決テスト"""
        # Arrange
        alert_key = f"{test_alert_rule.name}"
        monitoring_service.active_alerts.add(alert_key)

        with patch.object(monitoring_service, '_send_resolution_notification') as mock_send:
            # Act
            await monitoring_service._resolve_alert(test_alert_rule)

            # Assert
            assert alert_key not in monitoring_service.active_alerts
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_alert_metrics(self, monitoring_service, mock_db):
        """アラートメトリクス取得テスト"""
        # Arrange
        test_rule = AlertRule(
            name="test_metrics",
            condition="error_rate",
            threshold=10,
            time_window=30
        )

        # Mock database results
        mock_total_result = Mock()
        mock_total_result.scalar.return_value = 25
        
        mock_severity_result = Mock()
        mock_severity_result.fetchall.return_value = [
            ("critical", 5),
            ("high", 10),
            ("medium", 10)
        ]
        
        mock_service_result = Mock()
        mock_service_result.fetchall.return_value = [
            ("service1", 15),
            ("service2", 10)
        ]

        mock_db.execute.side_effect = [
            mock_total_result,
            mock_severity_result,
            mock_service_result
        ]

        # Act
        metrics = await monitoring_service._get_alert_metrics(test_rule)

        # Assert
        assert metrics["total_errors"] == 25
        assert metrics["severity_breakdown"]["critical"] == 5
        assert metrics["top_services"]["service1"] == 15
        assert metrics["threshold"] == 10
        assert metrics["condition"] == "error_rate"

    @pytest.mark.asyncio
    async def test_add_alert_rule_success(self, monitoring_service):
        """アラートルール追加成功テスト"""
        # Arrange
        new_rule = AlertRule(
            name="new_test_rule",
            condition="custom_condition",
            threshold=5,
            time_window=10
        )
        initial_count = len(monitoring_service.alert_rules)

        # Act
        result = await monitoring_service.add_alert_rule(new_rule)

        # Assert
        assert result is True
        assert len(monitoring_service.alert_rules) == initial_count + 1
        assert any(rule.name == "new_test_rule" for rule in monitoring_service.alert_rules)

    @pytest.mark.asyncio
    async def test_add_alert_rule_duplicate(self, monitoring_service, test_alert_rule):
        """アラートルール追加（重複）テスト"""
        # Arrange
        monitoring_service.alert_rules.append(test_alert_rule)
        duplicate_rule = AlertRule(
            name=test_alert_rule.name,  # Same name
            condition="different_condition",
            threshold=1,
            time_window=1
        )

        # Act
        result = await monitoring_service.add_alert_rule(duplicate_rule)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_alert_rule_success(self, monitoring_service, test_alert_rule):
        """アラートルール削除成功テスト"""
        # Arrange
        monitoring_service.alert_rules.append(test_alert_rule)
        monitoring_service.active_alerts.add(f"{test_alert_rule.name}")
        initial_count = len(monitoring_service.alert_rules)

        # Act
        result = await monitoring_service.remove_alert_rule(test_alert_rule.name)

        # Assert
        assert result is True
        assert len(monitoring_service.alert_rules) == initial_count - 1
        assert f"{test_alert_rule.name}" not in monitoring_service.active_alerts

    @pytest.mark.asyncio
    async def test_remove_alert_rule_not_found(self, monitoring_service):
        """アラートルール削除（見つからない）テスト"""
        # Act
        result = await monitoring_service.remove_alert_rule("non_existent_rule")

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_get_monitoring_status(self, monitoring_service):
        """監視ステータス取得テスト"""
        # Arrange
        monitoring_service.active_alerts.add("test_alert")

        # Act
        status = await monitoring_service.get_monitoring_status()

        # Assert
        assert "monitoring_active" in status
        assert status["active_alerts"] == 1
        assert status["alert_rules_count"] == 4  # Default rules
        assert status["total_rules"] == 4
        assert "test_alert" in status["active_alert_names"]
        assert "last_check" in status

    @pytest.mark.asyncio
    async def test_get_system_health_metrics(self, monitoring_service, mock_db):
        """システムヘルスメトリクス取得テスト"""
        # Arrange
        mock_results = [
            Mock(scalar=lambda: 50),    # total_errors_24h
            Mock(scalar=lambda: 5),     # total_errors_1h
            Mock(scalar=lambda: 8),     # critical_errors
            Mock(scalar=lambda: 35),    # resolved_errors
        ]
        mock_db.execute.side_effect = mock_results

        # Act
        metrics = await monitoring_service.get_system_health_metrics()

        # Assert
        assert metrics["errors_24h"] == 50
        assert metrics["errors_1h"] == 5
        assert metrics["critical_errors_24h"] == 8
        assert metrics["resolved_errors_24h"] == 35
        assert metrics["resolution_rate_24h"] == 70.0  # 35/50 * 100
        assert "timestamp" in metrics
        assert "monitoring_active" in metrics
