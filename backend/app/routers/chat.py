from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.db.repository import SessionRepository
from backend.app.schemas.session import ChatRequest, ErrorResponse
from backend.app.rag.engine import stream_rag_chat

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post(
    "",
    summary="Stream conversational RAG response via Server-Sent Events (SSE)",
    description="Validates session, retrieves grounded transcript excerpts, and streams tokens.",
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
        200: {
            "content": {"text/event-stream": {}},
            "description": "Server-Sent Events stream: yields 'data: {\"token\": \"...\"}' and finishes with 'data: {\"event\": \"done\", ...}'"
        }
    }
)
async def chat_endpoint(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db_session)
):
    # Verify session exists before starting the stream
    session = await SessionRepository.get_session(db=db, session_id=payload.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SESSION_NOT_FOUND",
                "message": f"Session with ID '{payload.session_id}' does not exist"
            }
        )

    # Return StreamingResponse with SSE content type
    return StreamingResponse(
        stream_rag_chat(
            session_id=payload.session_id,
            user_query=payload.message,
            db=db,
            provider_override=payload.provider_override
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Prevents Nginx/proxy buffering
        }
    )
