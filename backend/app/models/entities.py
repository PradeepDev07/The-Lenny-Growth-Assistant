import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class SessionModel(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New Conversation")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    user_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships with CASCADE DELETE
    messages: Mapped[List["MessageModel"]] = relationship(
        "MessageModel",
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="MessageModel.created_at.asc()"
    )
    artifacts: Mapped[List["ArtifactModel"]] = relationship(
        "ArtifactModel",
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ArtifactModel.created_at.asc()"
    )


class MessageModel(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # "user", "assistant", "system"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    model_info: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    session: Mapped["SessionModel"] = relationship("SessionModel", back_populates="messages")


class ArtifactModel(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    message_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # "markdown", "html"
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model_info: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    session: Mapped["SessionModel"] = relationship("SessionModel", back_populates="artifacts")


class RoutingLogModel(Base):
    __tablename__ = "routing_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    task: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
