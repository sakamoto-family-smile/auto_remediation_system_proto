"""
認証エンドポイント
"""

from typing import Any, Dict

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService
from app.services.user_service import UserService

router = APIRouter()
security = HTTPBearer()
logger = structlog.get_logger()


@router.post("/token", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login_for_access_token(
    login_request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Firebase IDトークンを使用してJWTアクセストークンを取得

    Args:
        login_request: ログインリクエスト（Firebase IDトークン含む）
        db: データベースセッション

    Returns:
        TokenResponse: JWTアクセストークンとユーザー情報
    """
    try:
        auth_service = AuthService()
        user_service = UserService(db)

        # Firebase IDトークン検証
        firebase_user = await auth_service.verify_firebase_token(
            login_request.firebase_token
        )

        # ユーザー取得または作成
        user = await user_service.get_or_create_user(
            google_id=firebase_user["uid"],
            email=firebase_user["email"],
        )

        # JWTトークン生成
        access_token = auth_service.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )

        logger.info(
            "User authenticated successfully",
            user_id=str(user.id),
            email=user.email,
        )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )

    except AuthenticationError as e:
        logger.warning("Authentication failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error("Login failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error",
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: Dict[str, Any] = Depends(AuthService.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    現在のユーザー情報取得

    Args:
        current_user: 現在のユーザー（JWT認証済み）
        db: データベースセッション

    Returns:
        UserResponse: ユーザー情報
    """
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_id(current_user["user_id"])

        if not user:
            raise AuthenticationError("User not found")

        return UserResponse.model_validate(user)

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Get current user failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User service error",
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    current_user: Dict[str, Any] = Depends(AuthService.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    アクセストークン更新

    Args:
        current_user: 現在のユーザー（JWT認証済み）
        db: データベースセッション

    Returns:
        TokenResponse: 新しいJWTアクセストークンとユーザー情報
    """
    try:
        auth_service = AuthService()
        user_service = UserService(db)

        user = await user_service.get_user_by_id(current_user["user_id"])

        if not user:
            raise AuthenticationError("User not found")

        # 新しいJWTトークン生成
        access_token = auth_service.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Token refresh failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh service error",
        )
