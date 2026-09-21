from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.db.repository import SessionRepository
from backend.app.schemas.session import ErrorResponse, ArtifactResponse
from backend.app.schemas.skill import EssayRequest
from backend.app.skills.ship30 import stream_ship30_essay

router = APIRouter(tags=["Skills & Artifacts"])


@router.post(
    "/api/skills/essay",
    summary="Generate and stream a grounded Ship 30 for 30 essay via Server-Sent Events",
    description="Transforms podcast insights into an atomic Ship 30 for 30 essay (~1,250 words) with Hook, 1-3-1 cadence, narrative, framework breakdown, and 3 actionable takeaways.",
    responses={
        404: {"model": ErrorResponse, "description": "Session not found if session_id provided"},
        200: {
            "content": {"text/event-stream": {}},
            "description": "SSE stream yielding tokens and ending with 'data: {\"event\": \"done\", \"artifact_id\": ...}'"
        }
    }
)
async def generate_essay_endpoint(
    payload: EssayRequest,
    db: AsyncSession = Depends(get_db_session)
):
    if payload.session_id:
        session = await SessionRepository.get_session(db=db, session_id=payload.session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "SESSION_NOT_FOUND",
                    "message": f"Session with ID '{payload.session_id}' does not exist"
                }
            )

    return StreamingResponse(
        stream_ship30_essay(
            topic=payload.topic,
            session_id=payload.session_id,
            db=db,
            provider_override=payload.provider_override
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get(
    "/api/artifacts/{artifact_id}",
    response_model=ArtifactResponse,
    summary="Get artifact details and content",
    responses={404: {"model": ErrorResponse}}
)
async def get_artifact_endpoint(
    artifact_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    artifact = await SessionRepository.get_artifact(db=db, artifact_id=artifact_id)
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ARTIFACT_NOT_FOUND",
                "message": f"Artifact with ID '{artifact_id}' does not exist"
            }
        )
    return ArtifactResponse.model_validate(artifact)


@router.get(
    "/api/sessions/{session_id}/artifacts",
    response_model=List[ArtifactResponse],
    summary="List all artifacts generated within a session",
    responses={404: {"model": ErrorResponse}}
)
async def list_session_artifacts_endpoint(
    session_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    session = await SessionRepository.get_session(db=db, session_id=session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SESSION_NOT_FOUND",
                "message": f"Session with ID '{session_id}' does not exist"
            }
        )
    artifacts = await SessionRepository.get_artifacts(db=db, session_id=session_id)
    return [ArtifactResponse.model_validate(a) for a in artifacts]
