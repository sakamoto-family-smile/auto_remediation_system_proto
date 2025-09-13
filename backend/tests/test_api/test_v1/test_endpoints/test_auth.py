"""
認証エンドポイントのテスト
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

from app.schemas.auth import LoginRequest


class TestAuthEndpoints:
    """認証エンドポイントテストクラス"""

    @pytest.mark.asyncio
    async def test_should_return_token_when_valid_firebase_token_provided(
        self, async_client: AsyncClient, mock_firebase_user
    ):
        """有効なFirebaseトークンでアクセストークンを取得できること"""
        # Arrange
        login_data = {"firebase_token": "valid-firebase-token"}

        with patch("app.services.auth_service.auth.verify_id_token") as mock_verify:
            with patch("app.services.user_service.UserService.get_or_create_user") as mock_get_user:
                mock_verify.return_value = mock_firebase_user
                mock_get_user.return_value = AsyncMock(
                    id="test-user-id",
                    email="test@example.com",
                    role="developer",
                )

                # Act
                response = await async_client.post("/api/v1/auth/token", json=login_data)

                # Assert
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert "access_token" in data
                assert data["token_type"] == "bearer"
                assert "user" in data
                assert data["user"]["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_should_return_401_when_invalid_firebase_token_provided(
        self, async_client: AsyncClient
    ):
        """無効なFirebaseトークンで401エラーが返されること"""
        # Arrange
        login_data = {"firebase_token": "invalid-firebase-token"}

        with patch("app.services.auth_service.auth.verify_id_token") as mock_verify:
            mock_verify.side_effect = Exception("Invalid token")

            # Act
            response = await async_client.post("/api/v1/auth/token", json=login_data)

            # Assert
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_should_return_422_when_missing_firebase_token(
        self, async_client: AsyncClient
    ):
        """Firebaseトークンが不足している場合に422エラーが返されること"""
        # Arrange
        login_data = {}

        # Act
        response = await async_client.post("/api/v1/auth/token", json=login_data)

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_should_return_current_user_when_authenticated(
        self, async_client: AsyncClient
    ):
        """認証済みユーザーの情報を取得できること"""
        # Arrange
        with patch("app.services.auth_service.AuthService.get_current_user") as mock_get_current:
            with patch("app.services.user_service.UserService.get_user_by_id") as mock_get_user:
                mock_get_current.return_value = {"user_id": "test-user-id"}
                mock_get_user.return_value = AsyncMock(
                    id="test-user-id",
                    email="test@example.com",
                    role="developer",
                )

                # Act
                response = await async_client.get(
                    "/api/v1/auth/me",
                    headers={"Authorization": "Bearer valid-token"}
                )

                # Assert
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_should_return_401_when_no_token_provided(
        self, async_client: AsyncClient
    ):
        """トークンが提供されていない場合に401エラーが返されること"""
        # Act
        response = await async_client.get("/api/v1/auth/me")

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_should_refresh_token_when_authenticated(
        self, async_client: AsyncClient
    ):
        """認証済みユーザーがトークンを更新できること"""
        # Arrange
        with patch("app.services.auth_service.AuthService.get_current_user") as mock_get_current:
            with patch("app.services.user_service.UserService.get_user_by_id") as mock_get_user:
                mock_get_current.return_value = {"user_id": "test-user-id"}
                mock_get_user.return_value = AsyncMock(
                    id="test-user-id",
                    email="test@example.com",
                    role="developer",
                )

                # Act
                response = await async_client.post(
                    "/api/v1/auth/refresh",
                    headers={"Authorization": "Bearer valid-token"}
                )

                # Assert
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert "access_token" in data
                assert data["token_type"] == "bearer"
                assert "user" in data
