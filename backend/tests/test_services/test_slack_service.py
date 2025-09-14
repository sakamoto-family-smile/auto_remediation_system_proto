"""
Slack サービスのunit test
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import json

from app.services.slack_service import SlackService


class TestSlackService:
    """Slack サービステストクラス"""

    @pytest.fixture
    def mock_slack_client(self):
        """モックSlackクライアント"""
        mock_client = Mock()
        mock_client.chat_postMessage = Mock()
        mock_client.chat_update = Mock()
        mock_client.reactions_add = Mock()
        return mock_client

    @pytest.fixture
    def slack_service(self, mock_slack_client):
        """Slack サービスインスタンス"""
        with patch('app.services.slack_service.WebClient') as mock_web_client:
            mock_web_client.return_value = mock_slack_client
            service = SlackService(bot_token="test-token")
            service.client = mock_slack_client
            return service

    @pytest.fixture
    def incident_data(self):
        """テスト用インシデントデータ"""
        return {
            "id": "test-incident-123",
            "error_type": "ValueError",
            "severity": "high",
            "service_name": "test-service",
            "environment": "production",
            "error_message": "Test error message",
            "created_at": "2024-01-01T00:00:00Z",
        }

    @pytest.fixture
    def remediation_data(self):
        """テスト用改修データ"""
        return {
            "explanation": "Fixed the ValueError by adding proper validation",
            "pr_url": "https://github.com/test/repo/pull/123",
            "service_used": "vertex_ai",
        }

    @pytest.mark.asyncio
    async def test_send_error_notification_success(
        self, slack_service, mock_slack_client, incident_data
    ):
        """エラー通知送信成功テスト"""
        # Arrange
        mock_slack_client.chat_postMessage.return_value = {
            "ts": "1234567890.123456",
            "permalink": "https://test.slack.com/archives/C123/p1234567890123456",
        }

        # Act
        result = await slack_service.send_error_notification(
            channel="test-channel",
            incident_data=incident_data,
            severity="high"
        )

        # Assert
        assert result["success"] is True
        assert result["channel"] == "test-channel"
        assert result["timestamp"] == "1234567890.123456"
        mock_slack_client.chat_postMessage.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_error_notification_no_client(self):
        """クライアント未初期化時のエラー通知テスト"""
        # Arrange
        service = SlackService(bot_token=None)

        # Act
        result = await service.send_error_notification(
            channel="test-channel",
            incident_data={"id": "test"},
            severity="high"
        )

        # Assert
        assert result["success"] is False
        assert "Slack client not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_send_remediation_notification_success(
        self, slack_service, mock_slack_client, incident_data, remediation_data
    ):
        """改修通知送信成功テスト"""
        # Arrange
        mock_slack_client.chat_postMessage.return_value = {
            "ts": "1234567890.123456",
        }

        # Act
        result = await slack_service.send_remediation_notification(
            channel="test-channel",
            incident_data=incident_data,
            remediation_data=remediation_data,
            status="completed"
        )

        # Assert
        assert result["success"] is True
        assert result["channel"] == "test-channel"
        mock_slack_client.chat_postMessage.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_approval_request_success(
        self, slack_service, mock_slack_client, incident_data, remediation_data
    ):
        """承認リクエスト送信成功テスト"""
        # Arrange
        mock_slack_client.chat_postMessage.return_value = {
            "ts": "1234567890.123456",
        }
        approvers = ["user1", "user2"]

        # Act
        result = await slack_service.send_approval_request(
            channel="test-channel",
            incident_data=incident_data,
            remediation_data=remediation_data,
            approvers=approvers
        )

        # Assert
        assert result["success"] is True
        assert result["channel"] == "test-channel"
        mock_slack_client.chat_postMessage.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_message_success(self, slack_service, mock_slack_client):
        """メッセージ更新成功テスト"""
        # Arrange
        mock_slack_client.chat_update.return_value = {"ts": "1234567890.123456"}
        blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "Updated"}}]

        # Act
        result = await slack_service.update_message(
            channel="test-channel",
            timestamp="1234567890.123456",
            blocks=blocks,
            text="Updated message"
        )

        # Assert
        assert result["success"] is True
        assert result["timestamp"] == "1234567890.123456"
        mock_slack_client.chat_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_reaction_success(self, slack_service, mock_slack_client):
        """リアクション追加成功テスト"""
        # Arrange
        mock_slack_client.reactions_add.return_value = {"ok": True}

        # Act
        result = await slack_service.add_reaction(
            channel="test-channel",
            timestamp="1234567890.123456",
            reaction="thumbsup"
        )

        # Assert
        assert result["success"] is True
        mock_slack_client.reactions_add.assert_called_once()

    def test_get_severity_style(self, slack_service):
        """重要度スタイル取得テスト"""
        # Test all severity levels
        assert slack_service._get_severity_style("critical") == ("danger", "🔥")
        assert slack_service._get_severity_style("high") == ("warning", "⚠️")
        assert slack_service._get_severity_style("medium") == ("good", "🟡")
        assert slack_service._get_severity_style("low") == ("#36a64f", "🟢")
        assert slack_service._get_severity_style("unknown") == ("good", "🔵")

    def test_build_error_notification_blocks(self, slack_service, incident_data):
        """エラー通知ブロック構築テスト"""
        # Act
        blocks = slack_service._build_error_notification_blocks(
            incident_data, "high", "⚠️"
        )

        # Assert
        assert len(blocks) == 5  # header, section, message, actions, context
        assert blocks[0]["type"] == "header"
        assert "⚠️ エラーインシデント発生" in blocks[0]["text"]["text"]
        assert blocks[1]["type"] == "section"
        assert blocks[2]["type"] == "section"
        assert blocks[3]["type"] == "actions"
        assert blocks[4]["type"] == "context"

    def test_build_remediation_notification_blocks(
        self, slack_service, incident_data, remediation_data
    ):
        """改修通知ブロック構築テスト"""
        # Act
        blocks = slack_service._build_remediation_notification_blocks(
            incident_data, remediation_data, "completed", "✅"
        )

        # Assert
        assert len(blocks) >= 2  # header, section, and potentially more for completed
        assert blocks[0]["type"] == "header"
        assert "✅ 自動改修完了" in blocks[0]["text"]["text"]

    def test_build_approval_request_blocks(
        self, slack_service, incident_data, remediation_data
    ):
        """承認リクエストブロック構築テスト"""
        # Arrange
        approvers = ["user1", "user2"]

        # Act
        blocks = slack_service._build_approval_request_blocks(
            incident_data, remediation_data, approvers
        )

        # Assert
        assert len(blocks) == 5  # header, intro, fields, message, actions
        assert blocks[0]["type"] == "header"
        assert "🔍 改修承認リクエスト" in blocks[0]["text"]["text"]
        assert blocks[4]["type"] == "actions"
        
        # Check that approve and reject buttons are present
        actions = blocks[4]["elements"]
        button_texts = [action["text"]["text"] for action in actions if action["type"] == "button"]
        assert "承認" in button_texts
        assert "却下" in button_texts

    def test_is_configured_with_token(self):
        """トークン有りの設定確認テスト"""
        with patch('app.services.slack_service.WebClient'):
            service = SlackService(bot_token="test-token")
            assert service.is_configured() is True

    def test_is_configured_without_token(self):
        """トークン無しの設定確認テスト"""
        service = SlackService(bot_token=None)
        assert service.is_configured() is False
