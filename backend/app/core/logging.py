"""
構造化ログ設定
"""

import logging
import sys
from typing import Any, Dict

import structlog

from app.core.config import get_settings

settings = get_settings()


def setup_logging() -> None:
    """構造化ログ設定"""

    # structlog設定
    structlog.configure(
        processors=[
            # 標準的なプロセッサー
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,

            # JSON出力（本番環境）またはコンソール出力（開発環境）
            structlog.dev.ConsoleRenderer() if settings.DEBUG
            else structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # 標準ログレベル設定
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )

    # 外部ライブラリのログレベル調整
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )


def get_correlation_id() -> str:
    """相関ID生成"""
    import uuid
    return str(uuid.uuid4())


def create_audit_log_entry(
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    details: Dict[str, Any],
    ip_address: str = None,
    user_agent: str = None,
) -> Dict[str, Any]:
    """
    監査ログエントリ作成

    Args:
        user_id: ユーザーID
        action: 実行アクション
        resource_type: リソースタイプ
        resource_id: リソースID
        details: 詳細情報
        ip_address: IPアドレス
        user_agent: ユーザーエージェント

    Returns:
        Dict[str, Any]: 監査ログエントリ
    """
    import datetime

    return {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "event_id": get_correlation_id(),
        "user_id": user_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "result": "success",  # デフォルト成功
    }
