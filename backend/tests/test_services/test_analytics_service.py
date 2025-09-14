"""
分析サービスのunit test
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

from app.services.analytics_service import AnalyticsService


class TestAnalyticsService:
    """分析サービステストクラス"""

    @pytest.fixture
    def mock_db(self):
        """モックデータベースセッション"""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        return mock_db

    @pytest.fixture
    def analytics_service(self, mock_db):
        """分析サービスインスタンス"""
        return AnalyticsService(db=mock_db)

    @pytest.mark.asyncio
    async def test_get_error_trends_basic(self, analytics_service):
        """エラー傾向分析基本テスト"""
        # Arrange
        with_mock_methods = [
            '_get_daily_error_counts',
            '_get_severity_statistics',
            '_get_error_type_statistics',
            '_get_service_statistics',
            '_get_resolution_statistics',
            '_analyze_trends'
        ]

        for method_name in with_mock_methods:
            setattr(analytics_service, method_name, AsyncMock(return_value={}))

        # Act
        result = await analytics_service.get_error_trends(days=30)

        # Assert
        assert "period" in result
        assert result["period"]["days"] == 30
        assert "daily_errors" in result
        assert "severity_statistics" in result
        assert "error_type_statistics" in result
        assert "service_statistics" in result
        assert "resolution_statistics" in result
        assert "trend_analysis" in result
        assert "generated_at" in result

    @pytest.mark.asyncio
    async def test_get_error_trends_with_filters(self, analytics_service):
        """エラー傾向分析フィルターありテスト"""
        # Arrange
        with_mock_methods = [
            '_get_daily_error_counts',
            '_get_severity_statistics',
            '_get_error_type_statistics',
            '_get_service_statistics',
            '_get_resolution_statistics',
            '_analyze_trends'
        ]

        for method_name in with_mock_methods:
            setattr(analytics_service, method_name, AsyncMock(return_value={}))

        # Act
        result = await analytics_service.get_error_trends(
            days=7,
            service_name="test-service",
            environment="production"
        )

        # Assert
        assert result["filters"]["service_name"] == "test-service"
        assert result["filters"]["environment"] == "production"
        assert result["period"]["days"] == 7

    @pytest.mark.asyncio
    async def test_get_daily_error_counts(self, analytics_service, mock_db):
        """日別エラー数取得テスト"""
        # Arrange
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            (datetime(2024, 1, 1).date(), 10),
            (datetime(2024, 1, 2).date(), 15),
            (datetime(2024, 1, 3).date(), 8)
        ]
        mock_db.execute.return_value = mock_result

        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 3)

        # Act
        result = await analytics_service._get_daily_error_counts(
            start_date, end_date, None, None
        )

        # Assert
        assert len(result) == 3
        assert result[0]["date"] == "2024-01-01"
        assert result[0]["count"] == 10
        assert result[1]["count"] == 15
        assert result[2]["count"] == 8

    @pytest.mark.asyncio
    async def test_get_severity_statistics(self, analytics_service, mock_db):
        """重要度統計取得テスト"""
        # Arrange
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            ("critical", 5),
            ("high", 12),
            ("medium", 20),
            ("low", 8)
        ]
        mock_db.execute.return_value = mock_result

        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()

        # Act
        result = await analytics_service._get_severity_statistics(
            start_date, end_date, None, None
        )

        # Assert
        assert result["critical"] == 5
        assert result["high"] == 12
        assert result["medium"] == 20
        assert result["low"] == 8

    @pytest.mark.asyncio
    async def test_get_error_type_statistics(self, analytics_service, mock_db):
        """エラータイプ統計取得テスト"""
        # Arrange
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            ("ValueError", 15, 150),
            ("TypeError", 10, 80),
            ("KeyError", 8, 60),
        ]
        mock_db.execute.return_value = mock_result

        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()

        # Act
        result = await analytics_service._get_error_type_statistics(
            start_date, end_date, None, None
        )

        # Assert
        assert len(result) == 3
        assert result[0]["error_type"] == "ValueError"
        assert result[0]["incident_count"] == 15
        assert result[0]["total_occurrences"] == 150
        assert result[1]["error_type"] == "TypeError"

    @pytest.mark.asyncio
    async def test_get_service_statistics(self, analytics_service, mock_db):
        """サービス統計取得テスト"""
        # Arrange
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            ("service-a", 25, 250, 8),
            ("service-b", 18, 180, 6),
            ("service-c", 12, 120, 4),
        ]
        mock_db.execute.return_value = mock_result

        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()

        # Act
        result = await analytics_service._get_service_statistics(
            start_date, end_date, None
        )

        # Assert
        assert len(result) == 3
        assert result[0]["service_name"] == "service-a"
        assert result[0]["incident_count"] == 25
        assert result[0]["total_occurrences"] == 250
        assert result[0]["unique_error_types"] == 8

    @pytest.mark.asyncio
    async def test_get_resolution_statistics(self, analytics_service, mock_db):
        """解決統計取得テスト"""
        # Arrange
        mock_results = [
            Mock(scalar=lambda: 50),  # total incidents
            Mock(scalar=lambda: 35),  # resolved incidents
        ]
        mock_db.execute.side_effect = mock_results

        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()

        # Act
        result = await analytics_service._get_resolution_statistics(
            start_date, end_date, None, None
        )

        # Assert
        assert result["total_incidents"] == 50
        assert result["resolved_incidents"] == 35
        assert result["resolution_rate"] == 70.0  # 35/50 * 100

    @pytest.mark.asyncio
    async def test_get_resolution_statistics_zero_incidents(self, analytics_service, mock_db):
        """解決統計取得（インシデント0件）テスト"""
        # Arrange
        mock_results = [
            Mock(scalar=lambda: 0),  # total incidents
            Mock(scalar=lambda: 0),  # resolved incidents
        ]
        mock_db.execute.side_effect = mock_results

        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()

        # Act
        result = await analytics_service._get_resolution_statistics(
            start_date, end_date, None, None
        )

        # Assert
        assert result["total_incidents"] == 0
        assert result["resolved_incidents"] == 0
        assert result["resolution_rate"] == 0

    def test_analyze_trends_increasing(self, analytics_service):
        """トレンド分析（増加傾向）テスト"""
        # Arrange
        daily_errors = [
            {"date": "2024-01-01", "count": 5},
            {"date": "2024-01-02", "count": 8},
            {"date": "2024-01-03", "count": 12},
            {"date": "2024-01-04", "count": 15},
        ]

        # Act
        result = analytics_service._analyze_trends(daily_errors)

        # Assert
        assert result["trend"] == "increasing"
        assert result["first_half_average"] == 6.5  # (5+8)/2
        assert result["second_half_average"] == 13.5  # (12+15)/2
        assert result["change_percentage"] > 0

    def test_analyze_trends_decreasing(self, analytics_service):
        """トレンド分析（減少傾向）テスト"""
        # Arrange
        daily_errors = [
            {"date": "2024-01-01", "count": 15},
            {"date": "2024-01-02", "count": 12},
            {"date": "2024-01-03", "count": 8},
            {"date": "2024-01-04", "count": 5},
        ]

        # Act
        result = analytics_service._analyze_trends(daily_errors)

        # Assert
        assert result["trend"] == "decreasing"
        assert result["first_half_average"] == 13.5  # (15+12)/2
        assert result["second_half_average"] == 6.5  # (8+5)/2
        assert result["change_percentage"] < 0

    def test_analyze_trends_stable(self, analytics_service):
        """トレンド分析（安定）テスト"""
        # Arrange
        daily_errors = [
            {"date": "2024-01-01", "count": 10},
            {"date": "2024-01-02", "count": 10},
            {"date": "2024-01-03", "count": 10},
            {"date": "2024-01-04", "count": 10},
        ]

        # Act
        result = analytics_service._analyze_trends(daily_errors)

        # Assert
        assert result["trend"] == "stable"
        assert abs(result["change_percentage"]) < 10  # Small change

    def test_analyze_trends_insufficient_data(self, analytics_service):
        """トレンド分析（データ不足）テスト"""
        # Arrange
        daily_errors = [
            {"date": "2024-01-01", "count": 10}
        ]

        # Act
        result = analytics_service._analyze_trends(daily_errors)

        # Assert
        assert result["trend"] == "insufficient_data"

    @pytest.mark.asyncio
    async def test_get_remediation_effectiveness(self, analytics_service):
        """改修効果分析テスト"""
        # Arrange
        mock_methods = [
            '_get_remediation_statistics',
            '_get_remediation_success_rate',
            '_get_average_fix_time',
            '_get_error_recurrence_rate',
            '_get_remediation_type_effectiveness'
        ]

        for method_name in mock_methods:
            setattr(analytics_service, method_name, AsyncMock(return_value={}))

        # Act
        result = await analytics_service.get_remediation_effectiveness(days=30)

        # Assert
        assert "period" in result
        assert result["period"]["days"] == 30
        assert "remediation_statistics" in result
        assert "success_rate" in result
        assert "average_fix_time_hours" in result
        assert "recurrence_rate" in result
        assert "remediation_type_effectiveness" in result
        assert "generated_at" in result

    @pytest.mark.asyncio
    async def test_get_service_health_report(self, analytics_service):
        """サービス健全性レポートテスト"""
        # Arrange
        service_name = "test-service"
        mock_methods = [
            '_get_service_basic_stats',
            '_get_service_error_frequency',
            '_get_service_severity_distribution',
            '_get_service_top_errors',
            '_get_service_remediation_stats',
            '_calculate_service_health_score',
            '_generate_service_recommendations'
        ]

        for method_name in mock_methods:
            if method_name == '_calculate_service_health_score':
                setattr(analytics_service, method_name, AsyncMock(return_value=85.5))
            elif method_name == '_generate_service_recommendations':
                setattr(analytics_service, method_name, AsyncMock(return_value=["recommendation1"]))
            else:
                setattr(analytics_service, method_name, AsyncMock(return_value={}))

        # Act
        result = await analytics_service.get_service_health_report(service_name, days=7)

        # Assert
        assert result["service_name"] == service_name
        assert result["period"]["days"] == 7
        assert result["health_score"] == 85.5
        assert "basic_statistics" in result
        assert "error_frequency" in result
        assert "severity_distribution" in result
        assert "top_errors" in result
        assert "remediation_statistics" in result
        assert len(result["recommendations"]) == 1

    @pytest.mark.asyncio
    async def test_generate_executive_summary(self, analytics_service):
        """エグゼクティブサマリー生成テスト"""
        # Arrange
        mock_methods = [
            '_get_overall_statistics',
            '_get_key_metrics',
            '_get_stability_metrics',
            '_get_efficiency_metrics',
            '_get_period_comparison',
            '_generate_insights',
            '_generate_action_items'
        ]

        for method_name in mock_methods:
            if method_name in ['_generate_insights', '_generate_action_items']:
                setattr(analytics_service, method_name, AsyncMock(return_value=["item1", "item2"]))
            else:
                setattr(analytics_service, method_name, AsyncMock(return_value={}))

        # Act
        result = await analytics_service.generate_executive_summary(days=30)

        # Assert
        assert result["period"]["days"] == 30
        assert "overall_statistics" in result
        assert "key_metrics" in result
        assert "stability_metrics" in result
        assert "efficiency_metrics" in result
        assert "period_comparison" in result
        assert len(result["insights"]) == 2
        assert len(result["action_items"]) == 2
        assert "generated_at" in result
