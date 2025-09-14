"""
エラー・改修管理モデル
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, TYPE_CHECKING

from sqlalchemy import String, DateTime, ForeignKey, Text, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.audit import PRReview


class ErrorIncident(Base):
    """エラーインシデントモデル"""

    __tablename__ = "error_incidents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    error_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    line_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 'python', 'javascript', 'typescript'
    severity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'low', 'medium', 'high', 'critical'
    service_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    environment: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 'development', 'staging', 'production'
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)  # エラーの発生回数
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        default="detected"
    )  # detected, analyzing, fixing, pr_created, resolved

    # リレーション
    remediation_attempts: Mapped[List["RemediationAttempt"]] = relationship(
        "RemediationAttempt",
        back_populates="incident",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ErrorIncident(id={self.id}, type={self.error_type}, status={self.status})>"

    @property
    def is_resolved(self) -> bool:
        """解決済みかどうか"""
        return self.status == "resolved" and self.resolved_at is not None

    @property
    def error_summary(self) -> str:
        """エラー概要"""
        summary = f"{self.error_type or 'Unknown'}"
        if self.file_path:
            summary += f" in {self.file_path}"
        if self.line_number:
            summary += f":{self.line_number}"
        return summary


class RemediationAttempt(Base):
    """改修試行モデル"""

    __tablename__ = "remediation_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("error_incidents.id"),
        nullable=False
    )
    cursor_cli_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    analysis_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fix_suggestion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    test_results: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    github_pr_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        default="started"
    )  # started, analyzed, fixed, tested, pr_created, approved, failed
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # リレーション
    incident: Mapped["ErrorIncident"] = relationship(
        "ErrorIncident",
        back_populates="remediation_attempts"
    )
    pr_reviews: Mapped[List["PRReview"]] = relationship(
        "PRReview",
        back_populates="remediation_attempt",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<RemediationAttempt(id={self.id}, incident_id={self.incident_id}, status={self.status})>"

    @property
    def is_completed(self) -> bool:
        """完了済みかどうか"""
        return self.status in ["approved", "failed"] and self.completed_at is not None

    @property
    def is_successful(self) -> bool:
        """成功したかどうか"""
        return self.status == "approved"

    @property
    def duration_minutes(self) -> Optional[int]:
        """実行時間（分）"""
        if self.completed_at and self.created_at:
            delta = self.completed_at - self.created_at
            return int(delta.total_seconds() / 60)
        return None
