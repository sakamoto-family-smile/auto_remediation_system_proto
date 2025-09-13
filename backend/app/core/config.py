"""
アプリケーション設定管理
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """アプリケーション設定"""

    # 基本設定
    DEBUG: bool = Field(default=False, description="デバッグモード")
    SECRET_KEY: str = Field(description="JWT署名用秘密鍵")
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000"],
        description="CORS許可オリジン",
    )

    # データベース設定
    DATABASE_URL: str = Field(description="PostgreSQL接続URL")
    DATABASE_POOL_SIZE: int = Field(default=20, description="データベース接続プールサイズ")
    DATABASE_MAX_OVERFLOW: int = Field(default=0, description="データベース接続最大オーバーフロー")

    # Google Cloud設定
    GOOGLE_CLOUD_PROJECT: str = Field(description="Google CloudプロジェクトID")
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = Field(
        default=None,
        description="Google Cloud認証情報ファイルパス"
    )

    # Vertex AI設定
    VERTEX_AI_LOCATION: str = Field(default="asia-northeast1", description="Vertex AIリージョン")
    VERTEX_AI_MODEL: str = Field(
        default="claude-3-sonnet@001",
        description="Vertex AI使用モデル"
    )

    # Firebase設定
    FIREBASE_PROJECT_ID: str = Field(description="Firebase プロジェクトID")
    FIREBASE_CREDENTIALS_PATH: Optional[str] = Field(
        default=None,
        description="Firebase認証情報ファイルパス"
    )

    # cursor-cli設定
    CURSOR_API_KEY: str = Field(description="cursor-cli APIキー")
    CURSOR_CLI_TIMEOUT: int = Field(default=300, description="cursor-cli実行タイムアウト（秒）")

    # GitHub設定
    GITHUB_TOKEN: str = Field(description="GitHub API トークン")
    GITHUB_WEBHOOK_SECRET: Optional[str] = Field(
        default=None,
        description="GitHub Webhook秘密鍵"
    )

    # Slack設定
    SLACK_BOT_TOKEN: Optional[str] = Field(
        default=None,
        description="Slack Bot トークン"
    )
    SLACK_SIGNING_SECRET: Optional[str] = Field(
        default=None,
        description="Slack署名検証秘密鍵"
    )
    SLACK_CHANNEL_ALERTS: str = Field(
        default="#dev-auto-fixes",
        description="Slackアラートチャンネル"
    )

    # 監視・ログ設定
    LOG_LEVEL: str = Field(default="INFO", description="ログレベル")
    ENABLE_AUDIT_LOG: bool = Field(default=True, description="監査ログ有効化")
    AUDIT_LOG_RETENTION_DAYS: int = Field(default=365, description="監査ログ保持日数")

    # システム設定
    MAX_CONCURRENT_REMEDIATIONS: int = Field(
        default=5,
        description="同時改修処理数上限"
    )
    REMEDIATION_TIMEOUT_MINUTES: int = Field(
        default=30,
        description="改修処理タイムアウト（分）"
    )

    # セキュリティ設定
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT署名アルゴリズム")
    JWT_EXPIRE_MINUTES: int = Field(default=60, description="JWT有効期限（分）")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """設定インスタンス取得（キャッシュ付き）"""
    return Settings()
