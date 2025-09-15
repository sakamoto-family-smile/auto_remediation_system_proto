"""
認証サービス
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import jwt
import structlog
import firebase_admin
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from firebase_admin import auth, credentials

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

logger = structlog.get_logger()
security = HTTPBearer()
settings = get_settings()

# Firebase Admin SDK初期化
firebase_initialized = False
if not firebase_admin._apps:
    try:
        # 1. 環境変数からJSON文字列を取得（Cloud Run推奨）
        firebase_json = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')
        if firebase_json:
            import json
            import tempfile
            # 一時ファイルに認証情報を書き込み
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                f.write(firebase_json)
                temp_cred_path = f.name

            cred = credentials.Certificate(temp_cred_path)
            firebase_admin.initialize_app(cred, {
                "projectId": settings.FIREBASE_PROJECT_ID,
            })
            firebase_initialized = True
            logger.info("Firebase Admin SDK initialized from environment variable")

            # 一時ファイルを削除
            os.unlink(temp_cred_path)

        # 2. 認証情報ファイルが存在する場合（ローカル開発）
        elif settings.FIREBASE_CREDENTIALS_PATH and os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred, {
                "projectId": settings.FIREBASE_PROJECT_ID,
            })
            firebase_initialized = True
            logger.info("Firebase Admin SDK initialized from credentials file")

        # 3. Application Default Credentials（GCPサービスアカウント）
        else:
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred, {
                "projectId": settings.FIREBASE_PROJECT_ID,
            })
            firebase_initialized = True
            logger.info("Firebase Admin SDK initialized with Application Default Credentials")

    except Exception as e:
        logger.warning(f"Firebase Admin SDK initialization failed: {e}")

# Firebase初期化が失敗した場合のフォールバック
if not firebase_initialized and not firebase_admin._apps:
    try:
        firebase_admin.initialize_app(credentials.Mock(), {
            "projectId": settings.FIREBASE_PROJECT_ID or "mock-project",
        })
        logger.info("Firebase Mock initialized for development")
    except Exception as e:
        logger.error(f"Firebase Mock initialization also failed: {e}")


class AuthService:
    """認証サービス"""

    @staticmethod
    async def verify_firebase_token(firebase_token: str) -> Dict[str, Any]:
        """
        Firebase IDトークンの検証

        Args:
            firebase_token: Firebase IDトークン

        Returns:
            Dict[str, Any]: デコードされたトークン情報

        Raises:
            AuthenticationError: 認証失敗時
        """
        try:
            decoded_token = auth.verify_id_token(firebase_token)

            logger.info(
                "Firebase token verified successfully",
                uid=decoded_token.get("uid"),
                email=decoded_token.get("email"),
            )

            return decoded_token

        except Exception as e:
            logger.warning("Firebase token verification failed", error=str(e))
            raise AuthenticationError(f"Invalid Firebase token: {str(e)}")

    @staticmethod
    def create_access_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        JWTアクセストークン生成

        Args:
            data: トークンに含めるデータ
            expires_delta: 有効期限（デフォルト: 60分）

        Returns:
            str: JWTアクセストークン
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.JWT_EXPIRE_MINUTES
            )

        to_encode.update({"exp": expire})

        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        logger.debug(
            "JWT token created",
            subject=data.get("sub"),
            expires_at=expire.isoformat(),
        )

        return encoded_jwt

    @staticmethod
    def verify_access_token(token: str) -> Dict[str, Any]:
        """
        JWTアクセストークンの検証

        Args:
            token: JWTアクセストークン

        Returns:
            Dict[str, Any]: デコードされたトークン情報

        Raises:
            AuthenticationError: 認証失敗時
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )

            user_id: str = payload.get("sub")
            if user_id is None:
                raise AuthenticationError("Invalid token: missing subject")

            return {
                "user_id": user_id,
                "email": payload.get("email"),
                "exp": payload.get("exp"),
            }

        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")
        except Exception as e:
            raise AuthenticationError(f"Token validation failed: {str(e)}")

    @staticmethod
    async def get_current_user(
        token: str = Depends(security),
    ) -> Dict[str, Any]:
        """
        現在のユーザー取得（依存性注入用）

        Args:
            token: HTTPBearer認証トークン

        Returns:
            Dict[str, Any]: 現在のユーザー情報

        Raises:
            HTTPException: 認証失敗時
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            user_info = AuthService.verify_access_token(token.credentials)
            return user_info

        except AuthenticationError:
            token_prefix = (
                token.credentials[:20] if token.credentials else None
            )
            logger.warning(
                "Authentication failed for request",
                token_prefix=token_prefix,
            )
            raise credentials_exception
