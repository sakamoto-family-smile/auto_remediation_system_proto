"""
Webhook エンドポイントのunit test
"""

import pytest
import json
import hmac
import hashlib
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestWebhookEndpoints:
    """Webhook エンドポイントテストクラス"""

    def test_github_webhook_valid_signature(self):
        """GitHub Webhook有効署名テスト"""
        # Arrange
        payload = {"action": "opened", "number": 1}
        payload_json = json.dumps(payload)
        secret = "test-secret"
        signature = "sha256=" + hmac.new(
            secret.encode(), payload_json.encode(), hashlib.sha256
        ).hexdigest()

        with patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value.GITHUB_WEBHOOK_SECRET = secret

            # Act
            response = client.post(
                "/api/v1/webhooks/github",
                data=payload_json,
                headers={
                    "X-Hub-Signature-256": signature,
                    "X-GitHub-Event": "pull_request",
                    "Content-Type": "application/json"
                }
            )

            # Assert
            assert response.status_code == 200
            assert response.json()["message"] == "GitHub webhook processed successfully"

    def test_github_webhook_invalid_signature(self):
        """GitHub Webhook無効署名テスト"""
        # Arrange
        payload = {"action": "opened", "number": 1}
        payload_json = json.dumps(payload)
        invalid_signature = "sha256=invalid_signature"

        with patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value.GITHUB_WEBHOOK_SECRET = "test-secret"

            # Act
            response = client.post(
                "/api/v1/webhooks/github",
                data=payload_json,
                headers={
                    "X-Hub-Signature-256": invalid_signature,
                    "X-GitHub-Event": "pull_request",
                    "Content-Type": "application/json"
                }
            )

            # Assert
            assert response.status_code == 401
            assert "Invalid signature" in response.json()["detail"]

    def test_github_webhook_missing_signature(self):
        """GitHub Webhook署名なしテスト"""
        # Arrange
        payload = {"action": "opened", "number": 1}
        payload_json = json.dumps(payload)

        # Act
        response = client.post(
            "/api/v1/webhooks/github",
            data=payload_json,
            headers={
                "X-GitHub-Event": "pull_request",
                "Content-Type": "application/json"
            }
        )

        # Assert
        assert response.status_code == 400
        assert "Missing signature" in response.json()["detail"]

    def test_github_webhook_push_event(self):
        """GitHub Webhook pushイベントテスト"""
        # Arrange
        payload = {
            "ref": "refs/heads/main",
            "commits": [
                {
                    "id": "abc123",
                    "message": "Fix bug in user service",
                    "author": {"name": "Test User"}
                }
            ]
        }
        payload_json = json.dumps(payload)
        secret = "test-secret"
        signature = "sha256=" + hmac.new(
            secret.encode(), payload_json.encode(), hashlib.sha256
        ).hexdigest()

        with patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value.GITHUB_WEBHOOK_SECRET = secret

            # Act
            response = client.post(
                "/api/v1/webhooks/github",
                data=payload_json,
                headers={
                    "X-Hub-Signature-256": signature,
                    "X-GitHub-Event": "push",
                    "Content-Type": "application/json"
                }
            )

            # Assert
            assert response.status_code == 200
            result = response.json()
            assert result["event_type"] == "push"
            assert result["processed"] is True

    def test_slack_webhook_valid_token(self):
        """Slack Webhook有効トークンテスト"""
        # Arrange
        payload = {
            "token": "test-token",
            "team_id": "T123456",
            "channel_id": "C123456",
            "user_id": "U123456",
            "text": "test message"
        }

        with patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value.SLACK_VERIFICATION_TOKEN = "test-token"

            # Act
            response = client.post(
                "/api/v1/webhooks/slack",
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            # Assert
            assert response.status_code == 200
            assert response.json()["message"] == "Slack webhook processed successfully"

    def test_slack_webhook_invalid_token(self):
        """Slack Webhook無効トークンテスト"""
        # Arrange
        payload = {
            "token": "invalid-token",
            "team_id": "T123456",
            "channel_id": "C123456",
            "user_id": "U123456",
            "text": "test message"
        }

        with patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value.SLACK_VERIFICATION_TOKEN = "test-token"

            # Act
            response = client.post(
                "/api/v1/webhooks/slack",
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            # Assert
            assert response.status_code == 401
            assert "Invalid token" in response.json()["detail"]

    def test_slack_webhook_interactive_component(self):
        """Slack Webhook インタラクティブコンポーネントテスト"""
        # Arrange
        interactive_payload = {
            "type": "interactive_message",
            "actions": [
                {
                    "name": "approve",
                    "type": "button",
                    "value": "approval_123"
                }
            ],
            "user": {"id": "U123456", "name": "testuser"},
            "channel": {"id": "C123456", "name": "alerts"}
        }
        
        payload = {
            "token": "test-token",
            "payload": json.dumps(interactive_payload)
        }

        with patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value.SLACK_VERIFICATION_TOKEN = "test-token"

            # Act
            response = client.post(
                "/api/v1/webhooks/slack",
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            # Assert
            assert response.status_code == 200
            result = response.json()
            assert result["type"] == "interactive_message"
            assert result["processed"] is True

    def test_slack_webhook_url_verification(self):
        """Slack Webhook URL検証テスト"""
        # Arrange
        payload = {
            "token": "test-token",
            "challenge": "test-challenge-123",
            "type": "url_verification"
        }

        with patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value.SLACK_VERIFICATION_TOKEN = "test-token"

            # Act
            response = client.post(
                "/api/v1/webhooks/slack",
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            # Assert
            assert response.status_code == 200
            assert response.json()["challenge"] == "test-challenge-123"

    def test_generic_webhook_with_auth_header(self):
        """汎用 Webhook認証ヘッダーありテスト"""
        # Arrange
        payload = {
            "event_type": "error_detected",
            "service": "user-service",
            "error": "Database connection failed"
        }

        # Act
        response = client.post(
            "/api/v1/webhooks/generic",
            json=payload,
            headers={
                "Authorization": "Bearer test-token",
                "Content-Type": "application/json"
            }
        )

        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["message"] == "Generic webhook processed successfully"
        assert result["payload_type"] == "error_detected"

    def test_generic_webhook_without_auth(self):
        """汎用 Webhook認証なしテスト"""
        # Arrange
        payload = {
            "event_type": "system_health",
            "status": "healthy"
        }

        # Act
        response = client.post(
            "/api/v1/webhooks/generic",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["message"] == "Generic webhook processed successfully"
        assert result["auth_provided"] is False

    def test_generic_webhook_malformed_json(self):
        """汎用 Webhook不正JSONテスト"""
        # Act
        response = client.post(
            "/api/v1/webhooks/generic",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )

        # Assert
        assert response.status_code == 422  # Validation error

    def test_github_webhook_issues_event(self):
        """GitHub Webhook issuesイベントテスト"""
        # Arrange
        payload = {
            "action": "opened",
            "issue": {
                "number": 123,
                "title": "Bug: Application crashes on startup",
                "body": "The application crashes when starting up with error...",
                "labels": [{"name": "bug"}, {"name": "priority:high"}]
            },
            "repository": {
                "name": "test-repo",
                "full_name": "user/test-repo"
            }
        }
        payload_json = json.dumps(payload)
        secret = "test-secret"
        signature = "sha256=" + hmac.new(
            secret.encode(), payload_json.encode(), hashlib.sha256
        ).hexdigest()

        with patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value.GITHUB_WEBHOOK_SECRET = secret

            # Act
            response = client.post(
                "/api/v1/webhooks/github",
                data=payload_json,
                headers={
                    "X-Hub-Signature-256": signature,
                    "X-GitHub-Event": "issues",
                    "Content-Type": "application/json"
                }
            )

            # Assert
            assert response.status_code == 200
            result = response.json()
            assert result["event_type"] == "issues"
            assert result["action"] == "opened"
            assert result["issue_number"] == 123

    def test_webhook_processing_error_handling(self):
        """Webhook処理エラーハンドリングテスト"""
        # Arrange
        payload = {"invalid": "payload structure"}
        payload_json = json.dumps(payload)
        secret = "test-secret"
        signature = "sha256=" + hmac.new(
            secret.encode(), payload_json.encode(), hashlib.sha256
        ).hexdigest()

        with patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value.GITHUB_WEBHOOK_SECRET = secret

            # Mock processing to raise an exception
            with patch("app.api.v1.endpoints.webhooks.process_github_webhook") as mock_process:
                mock_process.side_effect = Exception("Processing error")

                # Act
                response = client.post(
                    "/api/v1/webhooks/github",
                    data=payload_json,
                    headers={
                        "X-Hub-Signature-256": signature,
                        "X-GitHub-Event": "unknown_event",
                        "Content-Type": "application/json"
                    }
                )

                # Assert
                # The endpoint should handle the error gracefully
                # and return a success response to avoid webhook retries
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_webhook_async_processing(self):
        """Webhook非同期処理テスト"""
        # This would test the async processing of webhooks
        # in a real implementation
        pass

    def test_webhook_rate_limiting(self):
        """Webhook レート制限テスト"""
        # This would test rate limiting for webhook endpoints
        # to prevent abuse
        pass

    def test_webhook_duplicate_detection(self):
        """Webhook重複検出テスト"""
        # This would test detection and handling of duplicate webhook events
        # using event IDs or timestamps
        pass
