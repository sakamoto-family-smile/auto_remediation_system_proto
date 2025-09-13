"""
ユーザー管理サービス
"""

import uuid
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User, Organization
from app.core.exceptions import NotFoundError, DatabaseError

logger = structlog.get_logger()


class UserService:
    """ユーザー管理サービス"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """
        ユーザーID でユーザー取得

        Args:
            user_id: ユーザーID

        Returns:
            Optional[User]: ユーザー情報（存在しない場合None）
        """
        try:
            stmt = select(User).where(User.id == user_id).options(
                selectinload(User.organization)
            )
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                logger.debug("User retrieved successfully", user_id=str(user_id))

            return user

        except Exception as e:
            logger.error("Failed to get user by ID", user_id=str(user_id), error=str(e))
            raise DatabaseError(f"Failed to get user: {str(e)}", "get_user_by_id")

    async def get_user_by_google_id(self, google_id: str) -> Optional[User]:
        """
        Google ID でユーザー取得

        Args:
            google_id: Google ID

        Returns:
            Optional[User]: ユーザー情報（存在しない場合None）
        """
        try:
            stmt = select(User).where(User.google_id == google_id).options(
                selectinload(User.organization)
            )
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                logger.debug("User retrieved by Google ID", google_id=google_id)

            return user

        except Exception as e:
            logger.error("Failed to get user by Google ID", google_id=google_id, error=str(e))
            raise DatabaseError(f"Failed to get user: {str(e)}", "get_user_by_google_id")

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        メールアドレスでユーザー取得

        Args:
            email: メールアドレス

        Returns:
            Optional[User]: ユーザー情報（存在しない場合None）
        """
        try:
            stmt = select(User).where(User.email == email).options(
                selectinload(User.organization)
            )
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                logger.debug("User retrieved by email", email=email)

            return user

        except Exception as e:
            logger.error("Failed to get user by email", email=email, error=str(e))
            raise DatabaseError(f"Failed to get user: {str(e)}", "get_user_by_email")

    async def create_user(
        self,
        google_id: str,
        email: str,
        role: str = "developer",
        organization_id: Optional[uuid.UUID] = None
    ) -> User:
        """
        ユーザー作成

        Args:
            google_id: Google ID
            email: メールアドレス
            role: ユーザーロール
            organization_id: 組織ID

        Returns:
            User: 作成されたユーザー
        """
        try:
            user = User(
                google_id=google_id,
                email=email,
                role=role,
                organization_id=organization_id,
            )

            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)

            logger.info(
                "User created successfully",
                user_id=str(user.id),
                email=email,
                role=role,
            )

            return user

        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to create user", email=email, error=str(e))
            raise DatabaseError(f"Failed to create user: {str(e)}", "create_user")

    async def get_or_create_user(
        self,
        google_id: str,
        email: str,
        role: str = "developer"
    ) -> User:
        """
        ユーザー取得または作成

        Args:
            google_id: Google ID
            email: メールアドレス
            role: ユーザーロール（新規作成時のみ）

        Returns:
            User: 既存または新規作成されたユーザー
        """
        # 既存ユーザー確認
        user = await self.get_user_by_google_id(google_id)
        if user:
            # メールアドレス更新（変更された場合）
            if user.email != email:
                user.email = email
                await self.db.commit()
                logger.info("User email updated", user_id=str(user.id), new_email=email)

            return user

        # 組織の自動判定（メールドメインベース）
        organization_id = await self._get_organization_by_domain(email)

        # 新規ユーザー作成
        return await self.create_user(
            google_id=google_id,
            email=email,
            role=role,
            organization_id=organization_id,
        )

    async def update_user_role(self, user_id: uuid.UUID, new_role: str) -> User:
        """
        ユーザーロール更新

        Args:
            user_id: ユーザーID
            new_role: 新しいロール

        Returns:
            User: 更新されたユーザー
        """
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                raise NotFoundError("User", str(user_id))

            old_role = user.role
            user.role = new_role

            await self.db.commit()
            await self.db.refresh(user)

            logger.info(
                "User role updated",
                user_id=str(user_id),
                old_role=old_role,
                new_role=new_role,
            )

            return user

        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to update user role", user_id=str(user_id), error=str(e))
            raise DatabaseError(f"Failed to update user role: {str(e)}", "update_user_role")

    async def _get_organization_by_domain(self, email: str) -> Optional[uuid.UUID]:
        """
        メールドメインから組織ID取得

        Args:
            email: メールアドレス

        Returns:
            Optional[uuid.UUID]: 組織ID（該当する組織がない場合None）
        """
        try:
            domain = email.split("@")[1] if "@" in email else None
            if not domain:
                return None

            stmt = select(Organization).where(Organization.google_domain == domain)
            result = await self.db.execute(stmt)
            organization = result.scalar_one_or_none()

            if organization:
                logger.debug("Organization found for domain", domain=domain, org_id=str(organization.id))
                return organization.id

            return None

        except Exception as e:
            logger.warning("Failed to get organization by domain", email=email, error=str(e))
            return None
