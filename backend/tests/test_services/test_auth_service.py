"""
認証サービスのテスト
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import jwt
import pytest

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError
from app.services.auth_service import AuthService


class TestAuthService:
    """認証サービステストクラス"""

    @pytest.mark.asyncio
    async def test_should_verify_firebase_token_when_valid_token_provided(
        self, mock_firebase_user
    ):
        """有効なFirebaseトークンが検証されること"""
        # Arrange
        firebase_token = "valid-firebase-token"

        with patch("app.services.auth_service.auth.verify_id_token") as mock_verify:
            mock_verify.return_value = mock_firebase_user

            # Act
            result = await AuthService.verify_firebase_token(firebase_token)

            # Assert
            assert result == mock_firebase_user
            mock_verify.assert_called_once_with(firebase_token)

    @pytest.mark.asyncio
    async def test_should_raise_authentication_error_when_invalid_firebase_token(self):
        """無効なFirebaseトークンで認証エラーが発生すること"""
        # Arrange
        firebase_token = "invalid-firebase-token"

        with patch("app.services.auth_service.auth.verify_id_token") as mock_verify:
            mock_verify.side_effect = Exception("Invalid token")

            # Act & Assert
            with pytest.raises(AuthenticationError):
                await AuthService.verify_firebase_token(firebase_token)

    def test_should_create_access_token_with_correct_payload(self):
        """正しいペイロードでアクセストークンが作成されること"""
        # Arrange
        data = {"sub": "user-123", "email": "test@example.com"}

        # Act
        token = AuthService.create_access_token(data)

        # Assert
        settings = get_settings()
        decoded = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert decoded["sub"] == "user-123"
        assert decoded["email"] == "test@example.com"
        assert "exp" in decoded

    def test_should_create_access_token_with_custom_expiration(self):
        """カスタム有効期限でアクセストークンが作成されること"""
        # Arrange
        data = {"sub": "user-123"}
        custom_expiration = timedelta(minutes=30)

        # Act
        token = AuthService.create_access_token(data, custom_expiration)

        # Assert - トークンが正常に作成され、デコードできることを確認
        settings = get_settings()
        decoded = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        # 基本的なフィールドが存在することを確認
        assert "sub" in decoded
        assert "exp" in decoded
        assert decoded["sub"] == "user-123"

        # 有効期限が現在時刻より後であることを確認
        exp_time = datetime.fromtimestamp(decoded["exp"])
        now = datetime.utcnow()
        assert exp_time > now

    def test_should_verify_valid_access_token(self):
        """有効なアクセストークンが検証されること"""
        # Arrange
        data = {"sub": "user-123", "email": "test@example.com"}
        token = AuthService.create_access_token(data)

        # Act
        result = AuthService.verify_access_token(token)

        # Assert
        assert result["user_id"] == "user-123"
        assert result["email"] == "test@example.com"
        assert "exp" in result

    def test_should_raise_authentication_error_when_expired_token(self):
        """期限切れトークンで認証エラーが発生すること"""
        # Arrange
        data = {"sub": "user-123", "email": "test@example.com"}
        expired_delta = timedelta(minutes=-1)  # 1分前に期限切れ
        token = AuthService.create_access_token(data, expired_delta)

        # Act & Assert
        with pytest.raises(AuthenticationError) as exc_info:
            AuthService.verify_access_token(token)
        assert "expired" in str(exc_info.value).lower()

    def test_should_raise_authentication_error_when_invalid_token(self):
        """無効なトークンで認証エラーが発生すること"""
        # Arrange
        invalid_token = "invalid-token"

        # Act & Assert
        with pytest.raises(AuthenticationError, match="Invalid token"):
            AuthService.verify_access_token(invalid_token)

    def test_should_raise_authentication_error_when_token_missing_subject(self):
        """subjectが不足しているトークンで認証エラーが発生すること"""
        # Arrange
        settings = get_settings()
        data = {"email": "test@example.com"}  # subjectなし
        token = jwt.encode(
            data,
            settings.SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        # Act & Assert
        with pytest.raises(AuthenticationError) as exc_info:
            AuthService.verify_access_token(token)
        assert "missing subject" in str(exc_info.value)
