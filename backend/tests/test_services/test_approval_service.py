"""
承認サービスのunit test
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

from app.services.approval_service import ApprovalService, ApprovalStatus, ApprovalType


class TestApprovalService:
    """承認サービステストクラス"""

    @pytest.fixture
    def mock_db(self):
        """モックデータベースセッション"""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        return mock_db

    @pytest.fixture
    def mock_slack_service(self):
        """モックSlackサービス"""
        mock_slack = Mock()
        mock_slack.is_configured.return_value = True
        mock_slack.send_approval_request = AsyncMock(return_value={"success": True})
        mock_slack.send_error_notification = AsyncMock(return_value={"success": True})
        return mock_slack

    @pytest.fixture
    def approval_service(self, mock_db, mock_slack_service):
        """承認サービスインスタンス"""
        return ApprovalService(db=mock_db, slack_service=mock_slack_service)

    @pytest.fixture
    def incident_id(self):
        """テスト用インシデントID"""
        return uuid.uuid4()

    @pytest.fixture
    def remediation_data(self):
        """テスト用改修データ"""
        return {
            "explanation": "Fixed the issue by adding proper validation",
            "fixed_code": "def validate_input(value): return value is not None",
            "confidence_score": 0.95,
        }

    @pytest.mark.asyncio
    async def test_request_approval_manual_success(
        self, approval_service, incident_id, remediation_data
    ):
        """手動承認リクエスト成功テスト"""
        # Arrange
        with patch.object(approval_service, '_get_incident') as mock_get_incident, \
             patch.object(approval_service, '_get_approval_config') as mock_get_config, \
             patch.object(approval_service, '_create_approval_record') as mock_create_record:

            mock_get_incident.return_value = {
                "id": str(incident_id),
                "error_type": "ValueError",
                "severity": "high",
                "service_name": "test-service",
                "environment": "production",
            }
            mock_get_config.return_value = {
                "default_approvers": ["admin", "tech-lead"],
                "auto_approve_timeout": 60,
            }
            mock_create_record.return_value = {
                "id": "approval-123",
                "incident_id": str(incident_id),
                "approvers": ["admin", "tech-lead"],
                "status": ApprovalStatus.PENDING,
            }

            # Act
            result = await approval_service.request_approval(
                incident_id=incident_id,
                remediation_data=remediation_data,
                approval_type=ApprovalType.MANUAL,
                slack_channel="test-channel"
            )

            # Assert
            assert result["id"] == "approval-123"
            assert result["status"] == ApprovalStatus.PENDING
            mock_get_incident.assert_called_once_with(incident_id)
            mock_create_record.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_approval_automatic_success(
        self, approval_service, incident_id, remediation_data
    ):
        """自動承認リクエスト成功テスト"""
        # Arrange
        with patch.object(approval_service, '_get_incident') as mock_get_incident, \
             patch.object(approval_service, '_get_approval_config') as mock_get_config, \
             patch.object(approval_service, '_create_approval_record') as mock_create_record, \
             patch.object(approval_service, '_auto_approve') as mock_auto_approve:

            mock_get_incident.return_value = {
                "id": str(incident_id),
                "severity": "low",
            }
            mock_get_config.return_value = {
                "default_approvers": ["admin"],
                "auto_approve_timeout": 60,
            }
            mock_create_record.return_value = {
                "id": "approval-123",
                "status": ApprovalStatus.PENDING,
            }
            mock_auto_approve.return_value = {
                "approved": True,
                "approval_type": "automatic",
            }

            # Act
            result = await approval_service.request_approval(
                incident_id=incident_id,
                remediation_data=remediation_data,
                approval_type=ApprovalType.AUTOMATIC
            )

            # Assert
            assert result["approved"] is True
            assert result["approval_type"] == "automatic"
            mock_auto_approve.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_approval_emergency_success(
        self, approval_service, incident_id, remediation_data
    ):
        """緊急承認リクエスト成功テスト"""
        # Arrange
        with patch.object(approval_service, '_get_incident') as mock_get_incident, \
             patch.object(approval_service, '_get_approval_config') as mock_get_config, \
             patch.object(approval_service, '_create_approval_record') as mock_create_record, \
             patch.object(approval_service, '_emergency_approve') as mock_emergency_approve:

            mock_get_incident.return_value = {
                "id": str(incident_id),
                "severity": "critical",
            }
            mock_get_config.return_value = {
                "default_approvers": ["admin", "tech-lead", "security-team"],
                "auto_approve_timeout": 30,
            }
            mock_create_record.return_value = {
                "id": "approval-123",
                "status": ApprovalStatus.PENDING,
            }
            mock_emergency_approve.return_value = {
                "approved": True,
                "approval_type": "emergency",
            }

            # Act
            result = await approval_service.request_approval(
                incident_id=incident_id,
                remediation_data=remediation_data,
                approval_type=ApprovalType.EMERGENCY,
                slack_channel="critical-alerts"
            )

            # Assert
            assert result["approved"] is True
            assert result["approval_type"] == "emergency"
            mock_emergency_approve.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_approval_response_approve(self, approval_service):
        """承認レスポンス処理（承認）テスト"""
        # Arrange
        approval_id = "approval-123"
        approver_id = "user-456"

        with patch.object(approval_service, '_get_approval_record') as mock_get_record, \
             patch.object(approval_service, '_approve_remediation') as mock_approve, \
             patch.object(approval_service, '_log_approval_action') as mock_log:

            mock_get_record.return_value = {
                "id": approval_id,
                "status": ApprovalStatus.PENDING,
                "approvers": ["user-456", "user-789"],
            }
            mock_approve.return_value = {
                "approved": True,
                "approved_by": approver_id,
                "message": "Remediation approved successfully",
            }

            # Act
            result = await approval_service.process_approval_response(
                approval_id=approval_id,
                approver_id=approver_id,
                action="approve",
                comment="Looks good to me"
            )

            # Assert
            assert result["approved"] is True
            assert result["approved_by"] == approver_id
            mock_approve.assert_called_once()
            mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_approval_response_reject(self, approval_service):
        """承認レスポンス処理（却下）テスト"""
        # Arrange
        approval_id = "approval-123"
        approver_id = "user-456"

        with patch.object(approval_service, '_get_approval_record') as mock_get_record, \
             patch.object(approval_service, '_reject_remediation') as mock_reject, \
             patch.object(approval_service, '_log_approval_action') as mock_log:

            mock_get_record.return_value = {
                "id": approval_id,
                "status": ApprovalStatus.PENDING,
                "approvers": ["user-456", "user-789"],
            }
            mock_reject.return_value = {
                "approved": False,
                "rejected_by": approver_id,
                "message": "Remediation rejected",
            }

            # Act
            result = await approval_service.process_approval_response(
                approval_id=approval_id,
                approver_id=approver_id,
                action="reject",
                comment="Needs more testing"
            )

            # Assert
            assert result["approved"] is False
            assert result["rejected_by"] == approver_id
            mock_reject.assert_called_once()
            mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_approval_response_unauthorized(self, approval_service):
        """承認レスポンス処理（権限なし）テスト"""
        # Arrange
        approval_id = "approval-123"
        approver_id = "unauthorized-user"

        with patch.object(approval_service, '_get_approval_record') as mock_get_record:
            mock_get_record.return_value = {
                "id": approval_id,
                "status": ApprovalStatus.PENDING,
                "approvers": ["user-456", "user-789"],  # unauthorized-user is not in the list
            }

            # Act & Assert
            with pytest.raises(Exception):  # DatabaseErrorでラップされるため
                await approval_service.process_approval_response(
                    approval_id=approval_id,
                    approver_id=approver_id,
                    action="approve"
                )

    @pytest.mark.asyncio
    async def test_process_approval_response_already_processed(self, approval_service):
        """承認レスポンス処理（既に処理済み）テスト"""
        # Arrange
        approval_id = "approval-123"
        approver_id = "user-456"

        with patch.object(approval_service, '_get_approval_record') as mock_get_record:
            mock_get_record.return_value = {
                "id": approval_id,
                "status": ApprovalStatus.APPROVED,  # Already processed
                "approvers": ["user-456"],
            }

            # Act & Assert
            with pytest.raises(Exception):  # DatabaseErrorでラップされるため
                await approval_service.process_approval_response(
                    approval_id=approval_id,
                    approver_id=approver_id,
                    action="approve"
                )

    @pytest.mark.asyncio
    async def test_get_approval_status(self, approval_service):
        """承認ステータス取得テスト"""
        # Arrange
        approval_id = "approval-123"

        with patch.object(approval_service, '_get_approval_record') as mock_get_record:
            mock_get_record.return_value = {
                "id": approval_id,
                "incident_id": "incident-456",
                "status": ApprovalStatus.APPROVED,
                "approval_type": ApprovalType.MANUAL,
                "approvers": ["user-123"],
                "approved_by": "user-123",
                "approved_at": "2024-01-01T12:00:00Z",
                "expires_at": "2024-01-01T13:00:00Z",
                "comment": "Approved after review",
            }

            # Act
            result = await approval_service.get_approval_status(approval_id)

            # Assert
            assert result["id"] == approval_id
            assert result["status"] == ApprovalStatus.APPROVED
            assert result["approved_by"] == "user-123"
            assert result["comment"] == "Approved after review"

    def test_get_approval_config_critical_severity(self, approval_service):
        """クリティカル重要度の承認設定取得テスト"""
        # Arrange
        incident = {
            "severity": "critical",
            "environment": "production",
        }

        # Act
        result = approval_service._get_approval_config(incident, ApprovalType.MANUAL)

        # Assert
        assert isinstance(result, dict)
        assert "default_approvers" in result
        assert "auto_approve_timeout" in result
        # クリティカルな場合は複数承認者が必要
        assert len(result["default_approvers"]) >= 2

    @pytest.mark.asyncio
    async def test_check_expired_approvals(self, approval_service):
        """期限切れ承認チェックテスト"""
        # Arrange
        with patch.object(approval_service, '_expire_approval') as mock_expire:
            # Act
            result = await approval_service.check_expired_approvals()

            # Assert
            assert isinstance(result, list)
            # Mock implementation returns empty list, so no expirations to process
