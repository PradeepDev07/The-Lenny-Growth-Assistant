import json
import pytest
from unittest.mock import AsyncMock, patch
from httpx import ASGITransport, AsyncClient

from backend.app.main import app
from backend.app.db.session import init_db, async_session_factory
from backend.app.db.repository import SessionRepository
from backend.app.rag.engine import build_grounding_prompt
from backend.app.llm.base import BaseLLMProvider


@pytest.mark.anyio
async def test_build_grounding_prompt_compilation():
    query = "What are the 3 types of growth loops?"
    chunks = [
        {
            "id": "ep-brian-01",
            "source_title": "Brian Balfour on Growth Loops",
            "guest": "Brian Balfour",
            "url": "https://lennyspodcast.com/brian",
            "content": "Brian: There are three dominant loops: Viral, Content, and Paid."
        }
    ]
    system, messages = build_grounding_prompt(query, history=[], retrieved_chunks=chunks)

    assert "CRITICAL OPERATING RULES" in system
    assert "<transcript_evidence>" in messages[0].content
    assert "Brian Balfour" in messages[0].content
    assert "<user_question>" in messages[0].content
    assert query in messages[0].content


@pytest.mark.anyio
async def test_build_grounding_prompt_empty_chunks():
    query = "How to bake a chocolate cake?"
    system, messages = build_grounding_prompt(query, history=[], retrieved_chunks=[])

    assert "[NO MATCHING TRANSCRIPT EXCERPTS FOUND IN ARCHIVE]" in messages[0].content
    assert query in messages[0].content


@pytest.mark.anyio
async def test_chat_non_existent_session_returns_404():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/chat",
            json={"session_id": "non-existent-session-id", "message": "Hello?"}
        )
        assert resp.status_code == 404
        data = resp.json()
        assert data["error"]["code"] == "SESSION_NOT_FOUND"


@pytest.mark.anyio
async def test_chat_grounded_streaming_and_persistence():
    """
    Tests complete streaming pipeline with simulated provider:
    1. SSE tokens received.
    2. Final done event with sources emitted.
    3. User and assistant messages persisted to database.
    """
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create session
        s_resp = await client.post("/api/sessions", json={"title": "RAG Chat Test"})
        session_id = s_resp.json()["id"]

        # Mock streaming provider
        mock_provider = AsyncMock(spec=BaseLLMProvider)
        mock_provider.is_available.return_value = True
        mock_provider.model_name = "test-model"

        async def mock_stream(*args, **kwargs):
            yield "Brian "
            yield "Balfour "
            yield "identifies "
            yield "growth "
            yield "loops [Lenny Podcast — Brian Balfour — Growth Loops]."

        mock_provider.stream = mock_stream

        with patch("backend.app.rag.engine.model_router.get_streaming_provider", return_value=(mock_provider, False)):
            resp = await client.post(
                "/api/chat",
                json={
                    "session_id": session_id,
                    "message": "What did Brian Balfour say about growth loops vs funnels?"
                }
            )
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]

            # Parse SSE lines
            tokens = []
            done_event = None
            for line in resp.text.split("\n"):
                line = line.strip()
                if line.startswith("data: "):
                    payload = json.loads(line[6:])
                    if "token" in payload:
                        tokens.append(payload["token"])
                    elif payload.get("event") == "done":
                        done_event = payload

            # Verify tokens streamed
            full_text = "".join(tokens)
            assert "Brian" in full_text
            assert "growth loops" in full_text

            # Verify termination payload
            assert done_event is not None
            assert len(done_event["sources"]) > 0
            assert any(s["guest"] == "Brian Balfour" for s in done_event["sources"])

            # Verify database persistence
            async with async_session_factory() as db:
                session = await SessionRepository.get_session(db, session_id)
                assert len(session.messages) == 2
                assert session.messages[0].role == "user"
                assert session.messages[0].content == "What did Brian Balfour say about growth loops vs funnels?"
                assert session.messages[1].role == "assistant"
                assert "Brian Balfour" in session.messages[1].content
                assert len(session.messages[1].sources) > 0


@pytest.mark.anyio
async def test_chat_refusal_when_retrieval_empty():
    """
    Tests that when an unrelated query retrieves 0 chunks, the assistant streams
    a grounded refusal and emits an empty sources array.
    """
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        s_resp = await client.post("/api/sessions", json={"title": "Refusal Test"})
        session_id = s_resp.json()["id"]

        mock_provider = AsyncMock(spec=BaseLLMProvider)
        mock_provider.is_available.return_value = True
        mock_provider.model_name = "test-model"

        async def mock_refusal_stream(*args, **kwargs):
            yield "I searched Lenny's Podcast transcripts, but this topic is not covered in the archive."

        mock_provider.stream = mock_refusal_stream

        with patch("backend.app.rag.engine.model_router.get_streaming_provider", return_value=(mock_provider, False)):
            resp = await client.post(
                "/api/chat",
                json={
                    "session_id": session_id,
                    "message": "How do I change the transmission fluid in a 1998 honda civic?"
                }
            )
            assert resp.status_code == 200

            tokens = []
            done_event = None
            for line in resp.text.split("\n"):
                line = line.strip()
                if line.startswith("data: "):
                    payload = json.loads(line[6:])
                    if "token" in payload:
                        tokens.append(payload["token"])
                    elif payload.get("event") == "done":
                        done_event = payload

            full_text = "".join(tokens)
            assert "not covered in the archive" in full_text
            assert done_event is not None
            assert done_event["sources"] == []
