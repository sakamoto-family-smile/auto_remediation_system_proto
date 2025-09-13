"""
カスタム例外クラス
"""

import datetime
from typing import Any, Dict, Optional


class CustomException(Exception):
    """カスタム例外基底クラス"""

    def __init__(
        self,
        detail: str,
        error_code: str,
        status_code: int = 500,
        headers: Optional[Dict[str, Any]] = None,
    ):
        self.detail = detail
        self.error_code = error_code
        self.status_code = status_code
        self.headers = headers
        self.timestamp = datetime.datetime.utcnow()
        super().__init__(detail)


class AuthenticationError(CustomException):
    """認証エラー"""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            detail=detail,
            error_code="AUTHENTICATION_FAILED",
            status_code=401,
        )


class AuthorizationError(CustomException):
    """認可エラー"""

    def __init__(self, detail: str = "Access denied"):
        super().__init__(
            detail=detail,
            error_code="ACCESS_DENIED",
            status_code=403,
        )


class NotFoundError(CustomException):
    """リソース未発見エラー"""

    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            detail=f"{resource} with id '{resource_id}' not found",
            error_code="RESOURCE_NOT_FOUND",
            status_code=404,
        )


class ValidationError(CustomException):
    """バリデーションエラー"""

    def __init__(self, detail: str, field: str = None):
        error_detail = f"Validation failed: {detail}"
        if field:
            error_detail += f" (field: {field})"

        super().__init__(
            detail=error_detail,
            error_code="VALIDATION_ERROR",
            status_code=422,
        )


class ExternalServiceError(CustomException):
    """外部サービスエラー"""

    def __init__(self, service: str, detail: str):
        super().__init__(
            detail=f"{service} service error: {detail}",
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
        )


class RemediationError(CustomException):
    """改修処理エラー"""

    def __init__(self, detail: str, incident_id: str = None):
        error_detail = f"Remediation failed: {detail}"
        if incident_id:
            error_detail += f" (incident: {incident_id})"

        super().__init__(
            detail=error_detail,
            error_code="REMEDIATION_FAILED",
            status_code=500,
        )


class CursorCLIError(CustomException):
    """cursor-cli実行エラー"""

    def __init__(self, detail: str, command: str = None):
        error_detail = f"cursor-cli error: {detail}"
        if command:
            error_detail += f" (command: {command})"

        super().__init__(
            detail=error_detail,
            error_code="CURSOR_CLI_ERROR",
            status_code=500,
        )


class GitHubAPIError(CustomException):
    """GitHub API エラー"""

    def __init__(self, detail: str, status_code: int = 502):
        super().__init__(
            detail=f"GitHub API error: {detail}",
            error_code="GITHUB_API_ERROR",
            status_code=status_code,
        )


class SlackAPIError(CustomException):
    """Slack API エラー"""

    def __init__(self, detail: str):
        super().__init__(
            detail=f"Slack API error: {detail}",
            error_code="SLACK_API_ERROR",
            status_code=502,
        )


class DatabaseError(CustomException):
    """データベースエラー"""

    def __init__(self, detail: str, operation: str = None):
        error_detail = f"Database error: {detail}"
        if operation:
            error_detail += f" (operation: {operation})"

        super().__init__(
            detail=error_detail,
            error_code="DATABASE_ERROR",
            status_code=500,
        )
