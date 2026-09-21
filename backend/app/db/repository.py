from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.entities import SessionModel, MessageModel, ArtifactModel, RoutingLogModel


class SessionRepository:
    """
    Encapsulates all database operations for sessions, messages, and routing logs.
    """

    @staticmethod
    async def create_session(
        db: AsyncSession,
        title: Optional[str] = None,
        user_metadata: Optional[Dict[str, Any]] = None
    ) -> SessionModel:
        session = SessionModel(
            title=title or "New Conversation",
            user_metadata=user_metadata or {}
        )
        db.add(session)
        await db.flush()
        await db.refresh(session)
        return session

    @staticmethod
    async def list_sessions(
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0
    ) -> List[Tuple[SessionModel, int]]:
        """
        Returns sessions ordered by updated_at DESC along with message count.
        """
        # Subquery to count messages per session
        count_subq = (
            select(
                MessageModel.session_id,
                func.count(MessageModel.id).label("msg_count")
            )
            .group_by(MessageModel.session_id)
            .subquery()
        )

        query = (
            select(SessionModel, func.coalesce(count_subq.c.msg_count, 0))
            .outerjoin(count_subq, SessionModel.id == count_subq.c.session_id)
            .order_by(SessionModel.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(query)
        return [(row[0], int(row[1])) for row in result.all()]

    @staticmethod
    async def get_session(
        db: AsyncSession,
        session_id: str
    ) -> Optional[SessionModel]:
        """
        Fetches session with its messages eagerly loaded in chronological order.
        """
        query = (
            select(SessionModel)
            .where(SessionModel.id == session_id)
            .options(selectinload(SessionModel.messages))
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_session(
        db: AsyncSession,
        session_id: str
    ) -> bool:
        """
        Deletes session. Foreign key cascading removes related messages and artifacts.
        """
        session = await SessionRepository.get_session(db, session_id)
        if not session:
            return False
        await db.delete(session)
        await db.flush()
        return True

    @staticmethod
    async def add_message(
        db: AsyncSession,
        session_id: str,
        role: str,
        content: str,
        sources: Optional[List[Dict[str, Any]]] = None,
        model_info: Optional[Dict[str, Any]] = None
    ) -> MessageModel:
        """
        Appends a message to a session and updates the session's updated_at timestamp.
        """
        message = MessageModel(
            session_id=session_id,
            role=role,
            content=content,
            sources=sources or [],
            model_info=model_info or {}
        )
        db.add(message)

        # Update parent session updated_at
        session = await db.get(SessionModel, session_id)
        if session:
            session.updated_at = datetime.now(timezone.utc)
            db.add(session)

        await db.flush()
        await db.refresh(message)
        return message

    @staticmethod
    async def get_messages(
        db: AsyncSession,
        session_id: str,
        limit: int = 50
    ) -> List[MessageModel]:
        """
        Fetches messages strictly scoped to a session in chronological order.
        """
        query = (
            select(MessageModel)
            .where(MessageModel.session_id == session_id)
            .order_by(MessageModel.created_at.asc())
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def add_artifact(
        db: AsyncSession,
        session_id: str,
        type: str,
        title: str,
        content: str,
        message_id: Optional[str] = None,
        model_info: Optional[Dict[str, Any]] = None
    ) -> ArtifactModel:
        """
        Creates and persists an artifact associated with a session.
        """
        artifact = ArtifactModel(
            session_id=session_id,
            message_id=message_id,
            type=type,
            title=title,
            content=content,
            model_info=model_info or {}
        )
        db.add(artifact)
        await db.flush()
        await db.refresh(artifact)
        return artifact

    @staticmethod
    async def get_artifacts(
        db: AsyncSession,
        session_id: str
    ) -> List[ArtifactModel]:
        """
        Fetches all artifacts created within a session.
        """
        query = (
            select(ArtifactModel)
            .where(ArtifactModel.session_id == session_id)
            .order_by(ArtifactModel.created_at.asc())
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_artifact(
        db: AsyncSession,
        artifact_id: str
    ) -> Optional[ArtifactModel]:
        """
        Fetches a single artifact by ID.
        """
        query = select(ArtifactModel).where(ArtifactModel.id == artifact_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def log_routing(
        db: AsyncSession,
        task: str,
        provider: str,
        model: str,
        latency_ms: float,
        fallback_used: bool
    ) -> RoutingLogModel:
        entry = RoutingLogModel(
            task=task,
            provider=provider,
            model=model,
            latency_ms=latency_ms,
            fallback_used=fallback_used
        )
        db.add(entry)
        await db.flush()
        return entry

