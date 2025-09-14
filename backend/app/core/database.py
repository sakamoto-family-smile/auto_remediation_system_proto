"""
データベース接続・セッション管理
"""

from typing import AsyncGenerator

import structlog
from sqlalchemy import event, pool
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

# データベースエンジン作成
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLiteの場合は特別な設定
    engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=pool.StaticPool,
        connect_args={"check_same_thread": False},
        echo=settings.DEBUG,
    )
else:
    # PostgreSQL等の場合（非同期エンジン用）
    engine = create_async_engine(
        settings.DATABASE_URL,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,
        echo=settings.DEBUG,
    )

# セッションファクトリー
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """SQLAlchemyベースクラス"""
    pass


# データベース接続ログ
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """データベース接続時の設定"""
    logger.info("Database connection established")


@event.listens_for(engine.sync_engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """コネクションプールからの接続取得ログ"""
    logger.debug("Database connection checked out from pool")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    データベースセッション依存性注入用ジェネレータ

    Yields:
        AsyncSession: データベースセッション
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    データベース初期化
    テーブル作成とマイグレーション実行
    """
    try:
        # テーブル作成（開発環境のみ）
        if settings.DEBUG:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created")

        logger.info("Database initialization completed")

    except Exception as e:
        logger.error("Database initialization failed", error=str(e))
        raise


async def close_db() -> None:
    """データベース接続クローズ"""
    await engine.dispose()
    logger.info("Database connections closed")
