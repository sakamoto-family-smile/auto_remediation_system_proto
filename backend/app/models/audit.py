"""
監査・ログ管理モデル
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, TYPE_CHECKING

from sqlalchemy import String, DateTime, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.error import RemediationAttempt


class AuditLog(Base):
    """監査ログモデル"""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6対応で45文字
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    # リレーション
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="audit_logs"
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, user_id={self.user_id})>"

    @property
    def action_summary(self) -> str:
        """アクション概要"""
        summary = self.action
        if self.resource_type and self.resource_id:
            summary += f" on {self.resource_type}:{self.resource_id}"
        return summary


class PRReview(Base):
    """PRレビュー履歴モデル"""

    __tablename__ = "pr_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    remediation_attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("remediation_attempts.id"),
        nullable=False
    )
    github_pr_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reviewer_github_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    review_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )  # approved, changes_requested, commented
    review_comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    # リレーション
    remediation_attempt: Mapped["RemediationAttempt"] = relationship(
        "RemediationAttempt",
        back_populates="pr_reviews"
    )

    def __repr__(self) -> str:
        return f"<PRReview(id={self.id}, pr_number={self.github_pr_number}, status={self.review_status})>"

    @property
    def is_approved(self) -> bool:
        """承認済みかどうか"""
        return self.review_status == "approved"

    @property
    def needs_changes(self) -> bool:
        """変更要求があるかどうか"""
        return self.review_status == "changes_requested"
