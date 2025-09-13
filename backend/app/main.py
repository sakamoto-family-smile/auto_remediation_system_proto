"""
エラー自動調査・改修システム - FastAPI メインアプリケーション
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.api.v1.api import api_router
from app.core.config import get_settings
from app.core.database import init_db
from app.core.exceptions import CustomException
from app.core.logging import setup_logging

# ログ設定
setup_logging()
logger = structlog.get_logger()

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """アプリケーションライフサイクル管理"""
    logger.info("Starting Auto Remediation System...")

    # データベース初期化
    await init_db()

    logger.info("Application startup complete")
    yield
    logger.info("Application shutdown")


# FastAPIアプリケーション作成
app = FastAPI(
    title="Auto Remediation System API",
    description="エラー自動調査・改修システムのバックエンドAPI",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# カスタム例外ハンドラー
@app.exception_handler(CustomException)
async def custom_exception_handler(request: Request, exc: CustomException):
    """カスタム例外ハンドラー"""
    logger.error(
        "Custom exception occurred",
        error_code=exc.error_code,
        detail=exc.detail,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "detail": exc.detail,
            "timestamp": exc.timestamp.isoformat(),
        },
    )


# バリデーション例外ハンドラー
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    """リクエストバリデーション例外ハンドラー"""
    logger.warning(
        "Validation error occurred",
        errors=exc.errors(),
        path=request.url.path,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error_code": "VALIDATION_ERROR",
            "detail": "Request validation failed",
            "errors": exc.errors(),
        },
    )


# HTTP例外ハンドラー
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP例外ハンドラー"""
    logger.warning(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": "HTTP_ERROR",
            "detail": exc.detail,
        },
    )


# グローバル例外ハンドラー
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """グローバル例外ハンドラー"""
    logger.error(
        "Unhandled exception occurred",
        exception=str(exc),
        path=request.url.path,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "detail": "Internal server error occurred",
        },
    )


# ヘルスチェックエンドポイント
@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    ヘルスチェックエンドポイント
    
    Returns:
        dict: サービス状態情報
    """
    return {
        "status": "healthy",
        "service": "auto-remediation-system",
        "version": "1.0.0",
    }


# API ルーター登録
app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )
