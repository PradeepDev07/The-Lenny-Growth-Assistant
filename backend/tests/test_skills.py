import json
from typing import AsyncIterator, List
import pytest
import httpx

from backend.app.main import app
from backend.app.llm.base import BaseLLMProvider, LLMMessage
from backend.app.llm.router import model_router
from backend.app.skills.ship30 import build_ship30_prompt, SHIP30_SYSTEM_PROMPT


class MockEssayProvider(BaseLLMProvider):
    def __init__(self, model_name: str = "mock-model-v1"):
        super().__init__(model_name=model_name)

    async def generate(self, messages: List[LLMMessage], system_prompt: str = ""):
        raise NotImplementedError()

    async def stream(self, messages: List[LLMMessage], system_prompt: str = "") -> AsyncIterator[str]:
        tokens = [
            "# The Hidden Math of Growth Loops\n\n",
            "Most product teams obsess over top-of-funnel acquisition while hemorrhaging 80% of signups.\n\n",
            "Funnels end. Loops compound.\n\n",
            "According to Brian Balfour in [Lenny Podcast — Brian Balfour — Growth Loops and Retention Mechanics], ",
            "sustainable growth comes from reinvesting output into input.\n\n",
            "### 3 Actionable Steps:\n1. Audit cohort decay.\n2. Map reinvestment loops.\n3. Align metrics."
        ]
        for t in tokens:
            yield t

    async def is_available(self) -> bool:
        return True


@pytest.mark.anyio
async def test_ship30_prompt_compilation():
    """
    Verifies that the Ship 30 prompt builder compiles all 6 required structural
    stages, citation rules, and XML boundaries.
    """
    mock_chunks = [
        {
            "id": "balfour_chunk_1",
            "source_title": "Growth Loops and Retention Mechanics",
            "guest": "Brian Balfour",
            "url": "https://www.lennyspodcast.com/brian-balfour",
            "content": "A growth loop is a closed system where input produces output that can be reinvested into more input."
        }
    ]
    sys_prompt, messages = build_ship30_prompt(
        topic="Growth Loops vs Traditional Funnels",
        retrieved_chunks=mock_chunks
    )

    # 1. Verify system prompt includes Ship 30 composition stages
    assert "THE HOOK (Exactly 1 sentence)" in sys_prompt
    assert "THE 1-3-1 CADENCE" in sys_prompt
    assert "THE PM / FOUNDER OBSERVED NARRATIVE" in sys_prompt
    assert "THE CORE FRAMEWORK BREAKDOWN" in sys_prompt
    assert "PRACTICAL APPLICATION: 3 ACTIONABLE TAKEAWAYS" in sys_prompt
    assert "THE ANCHOR CONCLUSION" in sys_prompt
    assert "[Lenny Podcast — Guest Name — Episode Title]" in sys_prompt

    # 2. Verify evidence isolation
    assert len(messages) == 1
    content = messages[0].content
    assert "<transcript_evidence>" in content
    assert "Guest: Brian Balfour" in content
    assert "<essay_topic>" in content
    assert "Growth Loops vs Traditional Funnels" in content


@pytest.mark.anyio
async def test_ship30_prompt_empty_chunks():
    """
    Verifies that when no chunks match, the prompt cleanly indicates empty evidence.
    """
    sys_prompt, messages = build_ship30_prompt(topic="Quantum Mechanics", retrieved_chunks=[])
    assert "[NO MATCHING TRANSCRIPT EXCERPTS FOUND IN ARCHIVE]" in messages[0].content


@pytest.mark.anyio
async def test_generate_essay_endpoint_streaming_and_artifact_persistence(monkeypatch):
    """
    Tests end-to-end SSE streaming of a Ship 30 essay, automatic database persistence
    as an ArtifactModel, and subsequent artifact retrieval endpoints.
    """
    # Force task router to return our mock provider for essay_generation
    mock_provider = MockEssayProvider()
    async def mock_get_streaming_provider(task: str):
        return mock_provider, False

    monkeypatch.setattr(model_router, "get_streaming_provider", mock_get_streaming_provider)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # 1. Create a session
        sess_resp = await client.post("/api/sessions", json={"title": "Essay Test Session"})
        assert sess_resp.status_code == 201
        session_id = sess_resp.json()["id"]

        # 2. Call the Ship 30 essay endpoint
        response = await client.post(
            "/api/skills/essay",
            json={
                "topic": "growth loops and retention mechanics",
                "session_id": session_id
            }
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        # Parse SSE stream
        raw_events = response.text.split("\n\n")
        tokens = []
        done_data = None

        for event in raw_events:
            if not event.strip():
                continue
            lines = event.splitlines()
            for line in lines:
                if line.startswith("data: "):
                    payload = json.loads(line[6:])
                    if "token" in payload:
                        tokens.append(payload["token"])
                    elif payload.get("event") == "done":
                        done_data = payload

        # Verify streamed tokens
        full_text = "".join(tokens)
        assert "The Hidden Math of Growth Loops" in full_text
        assert "Brian Balfour" in full_text

        # Verify done payload and artifact metadata
        assert done_data is not None
        assert done_data["event"] == "done"
        assert done_data["session_id"] == session_id
        artifact_id = done_data["artifact_id"]
        assert artifact_id is not None
        assert len(done_data["sources"]) > 0

        # 3. Fetch the created artifact by ID
        art_resp = await client.get(f"/api/artifacts/{artifact_id}")
        assert art_resp.status_code == 200
        art_data = art_resp.json()
        assert art_data["id"] == artifact_id
        assert art_data["session_id"] == session_id
        assert art_data["type"] == "markdown"
        assert "Ship 30 Essay:" in art_data["title"]
        assert art_data["content"] == full_text

        # 4. List artifacts in session
        list_art_resp = await client.get(f"/api/sessions/{session_id}/artifacts")
        assert list_art_resp.status_code == 200
        artifacts = list_art_resp.json()
        assert len(artifacts) == 1
        assert artifacts[0]["id"] == artifact_id

        # 5. Verify messages in session include user prompt and assistant essay
        detail_resp = await client.get(f"/api/sessions/{session_id}")
        assert detail_resp.status_code == 200
        msgs = detail_resp.json()["messages"]
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert "growth loops" in msgs[0]["content"]
        assert msgs[1]["role"] == "assistant"
        assert msgs[1]["content"] == full_text


@pytest.mark.anyio
async def test_generate_essay_auto_creates_session(monkeypatch):
    """
    Verifies that if session_id is omitted, the endpoint automatically creates
    a new session and attaches the artifact to it.
    """
    mock_provider = MockEssayProvider()
    async def mock_get_streaming_provider(task: str):
        return mock_provider, False

    monkeypatch.setattr(model_router, "get_streaming_provider", mock_get_streaming_provider)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/skills/essay",
            json={"topic": "Elena Verna activation loop"}
        )
        assert response.status_code == 200

        done_event = None
        for chunk in response.text.split("\n\n"):
            if chunk.startswith("data: "):
                payload = json.loads(chunk[6:])
                if payload.get("event") == "done":
                    done_event = payload

        assert done_event is not None
        assert done_event["session_id"] is not None
        assert done_event["artifact_id"] is not None

        # Verify session was created
        sess_resp = await client.get(f"/api/sessions/{done_event['session_id']}")
        assert sess_resp.status_code == 200
        assert "Ship 30:" in sess_resp.json()["title"]


@pytest.mark.anyio
async def test_generate_essay_refusal_on_unrelated_topic():
    """
    Verifies that when a topic does not match any podcast transcripts,
    the endpoint gracefully refuses and does not generate an artifact.
    """
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/skills/essay",
            json={"topic": "How to bake a sourdough bread loaf with wild yeast"}
        )
        assert response.status_code == 200
        text = response.text
        assert "not covered in the archive" in text

        # Parse done event
        done_event = None
        for chunk in text.split("\n\n"):
            if chunk.startswith("data: "):
                payload = json.loads(chunk[6:])
                if payload.get("event") == "done":
                    done_event = payload

        assert done_event is not None
        assert done_event["artifact_id"] is None
        assert len(done_event["sources"]) == 0


@pytest.mark.anyio
async def test_generate_essay_non_existent_session_returns_404():
    """
    Verifies that providing an invalid session_id returns HTTP 404 with standard error format.
    """
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/skills/essay",
            json={
                "topic": "Growth loops",
                "session_id": "00000000-0000-0000-0000-000000000000"
            }
        )
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "SESSION_NOT_FOUND"
