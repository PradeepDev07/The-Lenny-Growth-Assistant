from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.db.repository import SessionRepository
from backend.app.schemas.session import (
    SessionCreate,
    SessionResponse,
    SessionDetailResponse,
    MessageCreate,
    MessageResponse,
    ErrorResponse
)

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation session"
)
async def create_session(
    payload: SessionCreate,
    db: AsyncSession = Depends(get_db_session)
):
    session = await SessionRepository.create_session(
        db=db,
        title=payload.title,
        user_metadata=payload.metadata
    )
    return SessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=0
    )


@router.get(
    "",
    response_model=List[SessionResponse],
    summary="List conversation sessions"
)
async def list_sessions(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_session)
):
    results = await SessionRepository.list_sessions(db=db, limit=limit, offset=offset)
    return [
        SessionResponse(
            id=session.id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=msg_count
        )
        for session, msg_count in results
    ]


@router.get(
    "/{session_id}",
    response_model=SessionDetailResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get session details and full message history"
)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    session = await SessionRepository.get_session(db=db, session_id=session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SESSION_NOT_FOUND", "message": f"Session with ID '{session_id}' does not exist"}
        )
    return SessionDetailResponse.model_validate(session)


@router.delete(
    "/{session_id}",
    summary="Delete a session and cascade delete all its messages and artifacts",
    responses={404: {"model": ErrorResponse}}
)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    deleted = await SessionRepository.delete_session(db=db, session_id=session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SESSION_NOT_FOUND", "message": f"Session with ID '{session_id}' does not exist"}
        )
    return {"deleted": True, "id": session_id}


@router.post(
    "/{session_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a message to a session",
    responses={404: {"model": ErrorResponse}}
)
async def add_message(
    session_id: str,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db_session)
):
    # Verify session exists
    session = await SessionRepository.get_session(db=db, session_id=session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SESSION_NOT_FOUND", "message": f"Session with ID '{session_id}' does not exist"}
        )

    message = await SessionRepository.add_message(
        db=db,
        session_id=session_id,
        role=payload.role,
        content=payload.content,
        sources=payload.sources,
        model_info=payload.model_info
    )
    return MessageResponse.model_validate(message)
