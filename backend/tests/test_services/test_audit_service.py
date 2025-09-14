"""
監査サービスのunit test
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

from app.services.audit_service import AuditService
from app.models.audit import AuditLog


class TestAuditService:
    """監査サービステストクラス"""

    @pytest.fixture
    def mock_db(self):
        """モックデータベースセッション"""
        mock_db = AsyncMock()
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.execute = AsyncMock()
        return mock_db

    @pytest.fixture
    def audit_service(self, mock_db):
        """監査サービスインスタンス"""
        return AuditService(db=mock_db)

    @pytest.fixture
    def user_id(self):
        """テスト用ユーザーID"""
        return uuid.uuid4()

    @pytest.fixture
    def resource_id(self):
        """テスト用リソースID"""
        return uuid.uuid4()

    @pytest.mark.asyncio
    async def test_log_action_success(self, audit_service, mock_db, user_id, resource_id):
        """アクション記録成功テスト"""
        # Arrange
        action = "test_action"
        resource_type = "test_resource"
        details = {"key": "value"}
        ip_address = "192.168.1.1"
        user_agent = "Test Agent"

        # Act
        result = await audit_service.log_action(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Assert
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

        # Check that the AuditLog was created with correct parameters
        added_log = mock_db.add.call_args[0][0]
        assert isinstance(added_log, AuditLog)
        assert added_log.user_id == user_id
        assert added_log.action == action
        assert added_log.resource_type == resource_type
        assert added_log.resource_id == resource_id
        assert added_log.details == details
        assert added_log.ip_address == ip_address
        assert added_log.user_agent == user_agent

    @pytest.mark.asyncio
    async def test_log_action_system_user(self, audit_service, mock_db, resource_id):
        """システムユーザーアクション記録テスト"""
        # Act
        result = await audit_service.log_action(
            user_id=None,  # System action
            action="system_action",
            resource_type="system_resource",
            resource_id=resource_id
        )

        # Assert
        added_log = mock_db.add.call_args[0][0]
        assert added_log.user_id is None

    @pytest.mark.asyncio
    async def test_log_action_database_error(self, audit_service, mock_db, user_id):
        """アクション記録データベースエラーテスト"""
        # Arrange
        mock_db.commit.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception):  # DatabaseError would be raised in actual implementation
            await audit_service.log_action(
                user_id=user_id,
                action="test_action",
                resource_type="test_resource"
            )

        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_audit_logs_no_filters(self, audit_service, mock_db):
        """監査ログ取得（フィルターなし）テスト"""
        # Arrange
        mock_logs = [
            Mock(spec=AuditLog),
            Mock(spec=AuditLog),
            Mock(spec=AuditLog)
        ]
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_logs
        mock_db.execute.return_value = mock_result

        # Act
        result = await audit_service.get_audit_logs()

        # Assert
        assert len(result) == 3
        assert result == mock_logs
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_audit_logs_with_filters(self, audit_service, mock_db, user_id, resource_id):
        """監査ログ取得（フィルターあり）テスト"""
        # Arrange
        mock_logs = [Mock(spec=AuditLog)]
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_logs
        mock_db.execute.return_value = mock_result

        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()

        # Act
        result = await audit_service.get_audit_logs(
            user_id=user_id,
            action="test_action",
            resource_type="test_resource",
            resource_id=resource_id,
            start_date=start_date,
            end_date=end_date,
            limit=50,
            offset=10
        )

        # Assert
        assert len(result) == 1
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_activity_summary(self, audit_service, mock_db, user_id):
        """ユーザーアクティビティサマリー取得テスト"""
        # Arrange
        # Mock total actions
        mock_total_result = Mock()
        mock_total_result.scalar.return_value = 25
        
        # Mock actions by type
        mock_actions_result = Mock()
        mock_actions_result.fetchall.return_value = [
            ("login", 10),
            ("create_incident", 8),
            ("approve_remediation", 7)
        ]
        
        # Mock resources by type
        mock_resources_result = Mock()
        mock_resources_result.fetchall.return_value = [
            ("error_incident", 15),
            ("remediation_attempt", 10)
        ]

        # Mock recent logs
        mock_recent_logs = [
            Mock(
                action="login",
                resource_type="authentication",
                resource_id=uuid.uuid4(),
                created_at=datetime.utcnow()
            )
        ]

        mock_db.execute.side_effect = [
            mock_total_result,
            mock_actions_result,
            mock_resources_result
        ]

        # Mock get_audit_logs for recent activity
        audit_service.get_audit_logs = AsyncMock(return_value=mock_recent_logs)

        # Act
        result = await audit_service.get_user_activity_summary(user_id, days=30)

        # Assert
        assert result["user_id"] == str(user_id)
        assert result["period_days"] == 30
        assert result["total_actions"] == 25
        assert result["actions_by_type"]["login"] == 10
        assert result["resources_by_type"]["error_incident"] == 15
        assert len(result["recent_activity"]) == 1

    @pytest.mark.asyncio
    async def test_get_system_activity_summary(self, audit_service, mock_db):
        """システムアクティビティサマリー取得テスト"""
        # Arrange
        mock_results = [
            Mock(scalar=lambda: 100),  # total_actions
            Mock(scalar=lambda: 70),   # user_actions
            Mock(scalar=lambda: 15),   # active_users
        ]
        
        # Mock daily activity
        mock_daily_result = Mock()
        mock_daily_result.fetchall.return_value = [
            (datetime.utcnow().date(), 20),
            ((datetime.utcnow() - timedelta(days=1)).date(), 15)
        ]
        
        # Mock top actions
        mock_top_actions_result = Mock()
        mock_top_actions_result.fetchall.return_value = [
            ("login", 30),
            ("create_incident", 25),
            ("approve_remediation", 20)
        ]

        mock_db.execute.side_effect = [
            mock_results[0],  # total_actions
            mock_results[1],  # user_actions
            mock_daily_result,  # daily_activity
            mock_top_actions_result,  # top_actions
            mock_results[2],  # active_users
        ]

        # Act
        result = await audit_service.get_system_activity_summary(days=7)

        # Assert
        assert result["period_days"] == 7
        assert result["total_actions"] == 100
        assert result["user_actions"] == 70
        assert result["system_actions"] == 30  # 100 - 70
        assert result["active_users"] == 15
        assert len(result["daily_activity"]) == 2
        assert result["top_actions"]["login"] == 30

    @pytest.mark.asyncio
    async def test_log_error_incident_action(self, audit_service, user_id, resource_id):
        """エラーインシデントアクション記録テスト"""
        # Arrange
        audit_service.log_action = AsyncMock(return_value=Mock())

        # Act
        result = await audit_service.log_error_incident_action(
            user_id=user_id,
            action="created",
            incident_id=resource_id,
            details={"severity": "high"}
        )

        # Assert
        audit_service.log_action.assert_called_once_with(
            user_id=user_id,
            action="incident_created",
            resource_type="error_incident",
            resource_id=resource_id,
            details={"severity": "high"}
        )

    @pytest.mark.asyncio
    async def test_log_remediation_action(self, audit_service, user_id):
        """改修アクション記録テスト"""
        # Arrange
        attempt_id = uuid.uuid4()
        incident_id = uuid.uuid4()
        audit_service.log_action = AsyncMock(return_value=Mock())

        # Act
        result = await audit_service.log_remediation_action(
            user_id=user_id,
            action="executed",
            attempt_id=attempt_id,
            incident_id=incident_id,
            details={"success": True}
        )

        # Assert
        audit_service.log_action.assert_called_once_with(
            user_id=user_id,
            action="remediation_executed",
            resource_type="remediation_attempt",
            resource_id=attempt_id,
            details={
                "incident_id": str(incident_id),
                "success": True
            }
        )

    @pytest.mark.asyncio
    async def test_log_authentication_action(self, audit_service, user_id):
        """認証アクション記録テスト"""
        # Arrange
        audit_service.log_action = AsyncMock(return_value=Mock())
        ip_address = "192.168.1.1"
        user_agent = "Test Browser"

        # Act
        result = await audit_service.log_authentication_action(
            user_id=user_id,
            action="login",
            details={"method": "google_oauth"},
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Assert
        audit_service.log_action.assert_called_once_with(
            user_id=user_id,
            action="auth_login",
            resource_type="authentication",
            details={"method": "google_oauth"},
            ip_address=ip_address,
            user_agent=user_agent
        )

    @pytest.mark.asyncio
    async def test_cleanup_old_logs_with_deletions(self, audit_service, mock_db):
        """古いログクリーンアップ（削除あり）テスト"""
        # Arrange
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 50  # 50 logs to delete
        mock_db.execute.side_effect = [mock_count_result, None]  # count, then delete

        # Act
        result = await audit_service.cleanup_old_logs(days_to_keep=90)

        # Assert
        assert result == 50
        assert mock_db.execute.call_count == 2  # count + delete
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_old_logs_no_deletions(self, audit_service, mock_db):
        """古いログクリーンアップ（削除なし）テスト"""
        # Arrange
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 0  # No logs to delete
        mock_db.execute.return_value = mock_count_result

        # Act
        result = await audit_service.cleanup_old_logs(days_to_keep=90)

        # Assert
        assert result == 0
        assert mock_db.execute.call_count == 1  # only count query
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_old_logs_database_error(self, audit_service, mock_db):
        """古いログクリーンアップエラーテスト"""
        # Arrange
        mock_db.execute.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception):  # DatabaseError would be raised in actual implementation
            await audit_service.cleanup_old_logs(days_to_keep=90)

        mock_db.rollback.assert_called_once()
