"""
チャットエンドポイント
"""

import uuid
from typing import Any, Dict, List

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import DatabaseError, NotFoundError
from app.schemas.chat import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionListResponse,
    ChatSessionResponse,
)
from app.services.auth_service import AuthService
from app.services.chat_service import ChatService

router = APIRouter()
logger = structlog.get_logger()


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    session_data: ChatSessionCreate,
    current_user: Dict[str, Any] = Depends(AuthService.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatSessionResponse:
    """
    チャットセッション作成

    Args:
        session_data: セッション作成データ
        current_user: 現在のユーザー
        db: データベースセッション

    Returns:
        ChatSessionResponse: 作成されたセッション情報
    """
    try:
        chat_service = ChatService(db)
        session = await chat_service.create_session(
            user_id=uuid.UUID(current_user["user_id"]),
            initial_message=session_data.initial_message,
        )

        logger.info(
            "Chat session created",
            session_id=str(session.id),
            user_id=current_user["user_id"],
        )

        return ChatSessionResponse.model_validate(session)

    except DatabaseError as e:
        logger.error("Failed to create chat session", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create chat session",
        )
    except Exception as e:
        logger.error("Unexpected error in create chat session", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/sessions", response_model=List[ChatSessionListResponse])
async def get_chat_sessions(
    limit: int = Query(50, ge=1, le=100, description="取得件数上限"),
    offset: int = Query(0, ge=0, description="オフセット"),
    current_user: Dict[str, Any] = Depends(AuthService.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ChatSessionListResponse]:
    """
    ユーザーのチャットセッション一覧取得

    Args:
        limit: 取得件数上限
        offset: オフセット
        current_user: 現在のユーザー
        db: データベースセッション

    Returns:
        List[ChatSessionListResponse]: セッション一覧
    """
    try:
        chat_service = ChatService(db)
        sessions = await chat_service.get_user_sessions(
            user_id=uuid.UUID(current_user["user_id"]),
            limit=limit,
            offset=offset,
        )

        # レスポンス用にデータを変換
        session_list = []
        for session in sessions:
            last_message = None
            message_count = len(session.messages)

            if session.messages:
                last_message = session.messages[-1].content[:100]  # プレビュー用に短縮

            session_list.append(
                ChatSessionListResponse(
                    id=session.id,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    message_count=message_count,
                    last_message=last_message,
                )
            )

        logger.debug(
            "Chat sessions retrieved",
            user_id=current_user["user_id"],
            count=len(session_list),
        )

        return session_list

    except DatabaseError as e:
        logger.error("Failed to get chat sessions", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat sessions",
        )
    except Exception as e:
        logger.error("Unexpected error in get chat sessions", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(AuthService.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatSessionResponse:
    """
    チャットセッション詳細取得

    Args:
        session_id: セッションID
        current_user: 現在のユーザー
        db: データベースセッション

    Returns:
        ChatSessionResponse: セッション詳細情報
    """
    try:
        chat_service = ChatService(db)
        session = await chat_service.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found",
            )

        # ユーザー権限チェック
        if str(session.user_id) != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this chat session",
            )

        logger.debug(
            "Chat session retrieved",
            session_id=str(session_id),
            user_id=current_user["user_id"],
        )

        return ChatSessionResponse.model_validate(session)

    except HTTPException:
        raise
    except DatabaseError as e:
        logger.error("Failed to get chat session", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat session",
        )
    except Exception as e:
        logger.error("Unexpected error in get chat session", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def add_chat_message(
    session_id: uuid.UUID,
    message_data: ChatMessageCreate,
    current_user: Dict[str, Any] = Depends(AuthService.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatMessageResponse:
    """
    チャットメッセージ追加

    Args:
        session_id: セッションID
        message_data: メッセージデータ
        current_user: 現在のユーザー
        db: データベースセッション

    Returns:
        ChatMessageResponse: 追加されたメッセージ
    """
    try:
        chat_service = ChatService(db)

        # セッション存在確認と権限チェック
        session = await chat_service.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found",
            )

        if str(session.user_id) != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this chat session",
            )

        message = await chat_service.add_message(
            session_id=session_id,
            role=message_data.role,
            content=message_data.content,
        )

        logger.info(
            "Chat message added",
            session_id=str(session_id),
            message_id=str(message.id),
            role=message_data.role,
        )

        return ChatMessageResponse.model_validate(message)

    except HTTPException:
        raise
    except (DatabaseError, NotFoundError) as e:
        logger.error("Failed to add chat message", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add chat message",
        )
    except Exception as e:
        logger.error("Unexpected error in add chat message", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_session(
    session_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(AuthService.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    チャットセッション削除

    Args:
        session_id: セッションID
        current_user: 現在のユーザー
        db: データベースセッション
    """
    try:
        chat_service = ChatService(db)

        # セッション存在確認と権限チェック
        session = await chat_service.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found",
            )

        if str(session.user_id) != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this chat session",
            )

        await chat_service.delete_session(session_id)

        logger.info(
            "Chat session deleted",
            session_id=str(session_id),
            user_id=current_user["user_id"],
        )

    except HTTPException:
        raise
    except (DatabaseError, NotFoundError) as e:
        logger.error("Failed to delete chat session", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete chat session",
        )
    except Exception as e:
        logger.error("Unexpected error in delete chat session", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/completion", response_model=ChatCompletionResponse)
async def chat_completion(
    completion_request: ChatCompletionRequest,
    current_user: Dict[str, Any] = Depends(AuthService.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatCompletionResponse:
    """
    チャット完了（LLM応答生成）

    Args:
        completion_request: 完了リクエスト
        current_user: 現在のユーザー
        db: データベースセッション

    Returns:
        ChatCompletionResponse: チャット完了レスポンス
    """
    try:
        chat_service = ChatService(db)
        user_id = uuid.UUID(current_user["user_id"])

        # セッション取得または作成
        if completion_request.session_id:
            session = await chat_service.get_session(completion_request.session_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chat session not found",
                )

            # 権限チェック
            if str(session.user_id) != current_user["user_id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this chat session",
                )
        else:
            # 新規セッション作成
            session = await chat_service.create_session(user_id)

        # ユーザーメッセージ追加
        user_message = await chat_service.add_message(
            session_id=session.id,
            role="user",
            content=completion_request.message,
        )

        # TODO: ここでLLM（Vertex AI）を呼び出してアシスタントの応答を生成
        # 現在は仮の応答を返す
        assistant_response = f"ユーザーメッセージ「{completion_request.message}」を受信しました。LLM統合は今後実装予定です。"

        # アシスタントメッセージ追加
        assistant_message = await chat_service.add_message(
            session_id=session.id,
            role="assistant",
            content=assistant_response,
        )

        logger.info(
            "Chat completion processed",
            session_id=str(session.id),
            user_id=current_user["user_id"],
        )

        return ChatCompletionResponse(
            session_id=session.id,
            user_message=ChatMessageResponse.model_validate(user_message),
            assistant_message=ChatMessageResponse.model_validate(assistant_message),
        )

    except HTTPException:
        raise
    except (DatabaseError, NotFoundError) as e:
        logger.error("Failed to process chat completion", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat completion",
        )
    except Exception as e:
        logger.error("Unexpected error in chat completion", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
