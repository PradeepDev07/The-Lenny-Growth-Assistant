from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.db.repository import SessionRepository
from backend.app.schemas.session import ErrorResponse, ArtifactResponse
from backend.app.schemas.skill import EssayRequest, InteractiveArtifactRequest
from backend.app.skills.ship30 import stream_ship30_essay
from backend.app.skills.interactive import stream_interactive_artifact

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


@router.post(
    "/api/skills/artifact",
    summary="Generate and stream an interactive HTML/JS tool or calculator via Server-Sent Events",
    description="Builds an interactive single-page calculator or framework visualizer grounded in Lenny's Podcast transcripts.",
    responses={
        404: {"model": ErrorResponse, "description": "Session not found if session_id provided"},
        200: {
            "content": {"text/event-stream": {}},
            "description": "SSE stream yielding HTML code tokens and ending with 'data: {\"event\": \"done\", \"artifact_id\": ...}'"
        }
    }
)
async def generate_interactive_artifact_endpoint(
    payload: InteractiveArtifactRequest,
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
        stream_interactive_artifact(
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
    "/api/artifacts/{artifact_id}/raw",
    summary="Serve sandboxed raw artifact HTML with strict Content-Security-Policy headers",
    description="Renders raw HTML artifacts safely in a sandboxed iframe with connect-src 'none' to block network exfiltration.",
    responses={
        404: {"model": ErrorResponse},
        200: {"content": {"text/html": {}}}
    }
)
async def get_artifact_raw_endpoint(
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

    # Wrap markdown in simple styled container if user requests raw preview of markdown
    if artifact.type == "markdown":
        html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #1e293b; background: #f8fafc; }}
pre {{ background: #0f172a; color: #f8fafc; padding: 16px; border-radius: 8px; overflow-x: auto; white-space: pre-wrap; }}
</style>
</head>
<body>
<pre>{artifact.content}</pre>
</body>
</html>"""
    else:
        html_body = artifact.content

    # Strict Content Security Policy:
    # 1. default-src 'none' blocks default fallback
    # 2. script-src 'unsafe-inline' allows calculator logic
    # 3. style-src 'unsafe-inline' allows embedded CSS
    # 4. img-src data: allows inline base64 images
    # 5. connect-src 'none' blocks ALL outbound network requests (fetch, XHR, WebSockets)
    # 6. frame-ancestors allows embedding only in host frontend
    csp = (
        "default-src 'none'; "
        "script-src 'unsafe-inline'; "
        "style-src 'unsafe-inline'; "
        "img-src data:; "
        "connect-src 'none'; "
        "frame-ancestors 'self' http://localhost:3000 http://127.0.0.1:3000;"
    )

    return HTMLResponse(
        content=html_body,
        media_type="text/html",
        headers={
            "Content-Security-Policy": csp,
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-cache, no-store, must-revalidate"
        }
    )


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

