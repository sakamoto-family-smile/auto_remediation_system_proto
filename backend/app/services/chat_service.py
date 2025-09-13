"""
チャット管理サービス
"""

import uuid
from typing import List, Optional

import structlog
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.exceptions import DatabaseError, NotFoundError
from app.models.chat import ChatMessage, ChatSession
from app.models.user import User

logger = structlog.get_logger()
settings = get_settings()


class ChatService:
    """チャット管理サービス"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(
        self, user_id: uuid.UUID, initial_message: Optional[str] = None
    ) -> ChatSession:
        """
        チャットセッション作成

        Args:
            user_id: ユーザーID
            initial_message: 初期メッセージ（オプション）

        Returns:
            ChatSession: 作成されたセッション
        """
        try:
            session = ChatSession(user_id=user_id)
            self.db.add(session)
            await self.db.flush()  # IDを取得するためにflush

            # 初期メッセージがある場合は追加
            if initial_message:
                await self.add_message(
                    session_id=session.id,
                    role="user",
                    content=initial_message,
                )

            await self.db.commit()
            await self.db.refresh(session)

            logger.info(
                "Chat session created",
                session_id=str(session.id),
                user_id=str(user_id),
                has_initial_message=bool(initial_message),
            )

            return session

        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Failed to create chat session",
                user_id=str(user_id),
                error=str(e),
            )
            raise DatabaseError(
                f"Failed to create chat session: {str(e)}", "create_session"
            )

    async def get_session(self, session_id: uuid.UUID) -> Optional[ChatSession]:
        """
        チャットセッション取得

        Args:
            session_id: セッションID

        Returns:
            Optional[ChatSession]: セッション情報（存在しない場合None）
        """
        try:
            stmt = (
                select(ChatSession)
                .where(ChatSession.id == session_id)
                .options(
                    selectinload(ChatSession.messages),
                    selectinload(ChatSession.user),
                )
            )
            result = await self.db.execute(stmt)
            session = result.scalar_one_or_none()

            if session:
                logger.debug(
                    "Chat session retrieved", session_id=str(session_id)
                )

            return session

        except Exception as e:
            logger.error(
                "Failed to get chat session",
                session_id=str(session_id),
                error=str(e),
            )
            raise DatabaseError(
                f"Failed to get chat session: {str(e)}", "get_session"
            )

    async def get_user_sessions(
        self, user_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> List[ChatSession]:
        """
        ユーザーのチャットセッション一覧取得

        Args:
            user_id: ユーザーID
            limit: 取得件数上限
            offset: オフセット

        Returns:
            List[ChatSession]: セッション一覧
        """
        try:
            stmt = (
                select(ChatSession)
                .where(ChatSession.user_id == user_id)
                .order_by(desc(ChatSession.updated_at))
                .limit(limit)
                .offset(offset)
                .options(selectinload(ChatSession.messages))
            )
            result = await self.db.execute(stmt)
            sessions = result.scalars().all()

            logger.debug(
                "User chat sessions retrieved",
                user_id=str(user_id),
                count=len(sessions),
            )

            return list(sessions)

        except Exception as e:
            logger.error(
                "Failed to get user chat sessions",
                user_id=str(user_id),
                error=str(e),
            )
            raise DatabaseError(
                f"Failed to get user chat sessions: {str(e)}",
                "get_user_sessions",
            )

    async def add_message(
        self, session_id: uuid.UUID, role: str, content: str
    ) -> ChatMessage:
        """
        チャットメッセージ追加

        Args:
            session_id: セッションID
            role: メッセージロール (user/assistant)
            content: メッセージ内容

        Returns:
            ChatMessage: 追加されたメッセージ
        """
        try:
            # セッション存在確認
            session = await self.get_session(session_id)
            if not session:
                raise NotFoundError("ChatSession", str(session_id))

            message = ChatMessage(
                session_id=session_id,
                role=role,
                content=content,
            )

            self.db.add(message)
            await self.db.commit()
            await self.db.refresh(message)

            # セッションの更新日時を更新
            await self.db.refresh(session)

            logger.info(
                "Chat message added",
                session_id=str(session_id),
                message_id=str(message.id),
                role=role,
                content_length=len(content),
            )

            return message

        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Failed to add chat message",
                session_id=str(session_id),
                role=role,
                error=str(e),
            )
            raise DatabaseError(
                f"Failed to add chat message: {str(e)}", "add_message"
            )

    async def delete_session(self, session_id: uuid.UUID) -> bool:
        """
        チャットセッション削除

        Args:
            session_id: セッションID

        Returns:
            bool: 削除成功の場合True
        """
        try:
            session = await self.get_session(session_id)
            if not session:
                raise NotFoundError("ChatSession", str(session_id))

            await self.db.delete(session)
            await self.db.commit()

            logger.info("Chat session deleted", session_id=str(session_id))
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Failed to delete chat session",
                session_id=str(session_id),
                error=str(e),
            )
            raise DatabaseError(
                f"Failed to delete chat session: {str(e)}", "delete_session"
            )

    async def get_session_messages(
        self, session_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> List[ChatMessage]:
        """
        セッションのメッセージ一覧取得

        Args:
            session_id: セッションID
            limit: 取得件数上限
            offset: オフセット

        Returns:
            List[ChatMessage]: メッセージ一覧
        """
        try:
            stmt = (
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at)
                .limit(limit)
                .offset(offset)
            )
            result = await self.db.execute(stmt)
            messages = result.scalars().all()

            logger.debug(
                "Session messages retrieved",
                session_id=str(session_id),
                count=len(messages),
            )

            return list(messages)

        except Exception as e:
            logger.error(
                "Failed to get session messages",
                session_id=str(session_id),
                error=str(e),
            )
            raise DatabaseError(
                f"Failed to get session messages: {str(e)}",
                "get_session_messages",
            )
