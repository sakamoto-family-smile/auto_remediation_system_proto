"""
pytest設定とフィクスチャー
"""

import asyncio
import os
from typing import AsyncGenerator, Generator
from fastapi import FastAPI

import pytest
import pytest_asyncio
import httpx
from httpx import AsyncClient
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# テスト用環境変数設定
os.environ.update({
    "SECRET_KEY": "test-secret-key-for-testing-only",
    "DEBUG": "true",
    "ENVIRONMENT": "test",
    "DATABASE_URL": "sqlite+aiosqlite:///./test.db",
    "GOOGLE_CLOUD_PROJECT": "test-project",
    "GCP_PROJECT_ID": "test-project",
    "FIREBASE_PROJECT_ID": "test-firebase-project",
    "FIREBASE_WEB_API_KEY": "test-api-key",
    "GITHUB_TOKEN": "test-github-token",
    "GITHUB_WEBHOOK_SECRET": "test-github-webhook-secret",
    "SLACK_BOT_TOKEN": "",  # 空文字にしてテストでNoneが効くようにする
    "SLACK_VERIFICATION_TOKEN": "test-slack-verification-token",
    "CURSOR_API_KEY": "test-cursor-api-key",
    "FRONTEND_URL": "http://localhost:3000",
    "VERTEX_AI_LOCATION": "us-central1",
    "VERTEX_AI_MODEL_NAME": "claude-3-sonnet@20240229",
})

from app.core.database import Base, get_db
from app.main import app as fastapi_app


# テスト用データベースURL（SQLiteインメモリ）
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    イベントループフィクスチャー（セッションスコープ）
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """
    テスト用データベースエンジンフィクスチャー
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
    )

    # テーブル作成
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # クリーンアップ
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    テスト用データベースセッションフィクスチャー
    """
    async_session_maker = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest.fixture
def app() -> FastAPI:
    """
    テスト用FastAPIアプリケーションフィクスチャー
    """
    return fastapi_app


@pytest.fixture
def client(app: FastAPI, test_session: AsyncSession) -> Generator[TestClient, None, None]:
    """
    テスト用FastAPIクライアントフィクスチャー
    """
    def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # クリーンアップ
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client(app: FastAPI, test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    テスト用非同期HTTPクライアントフィクスチャー
    """
    def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db

    # AsyncClient を使用してFastAPIアプリとの統合
    async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    # クリーンアップ
    app.dependency_overrides.clear()


@pytest.fixture
def mock_firebase_user():
    """
    モックFirebaseユーザーデータフィクスチャー
    """
    return {
        "uid": "test-firebase-uid",
        "email": "test@example.com",
        "email_verified": True,
        "name": "Test User",
    }


@pytest.fixture
def mock_jwt_token():
    """
    モックJWTトークンフィクスチャー
    """
    return "mock-jwt-token"
