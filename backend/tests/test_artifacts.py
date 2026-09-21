import json
from typing import AsyncIterator, List
import pytest
import httpx

from backend.app.main import app
from backend.app.llm.base import BaseLLMProvider, LLMMessage
from backend.app.llm.router import model_router
from backend.app.skills.interactive import (
    build_interactive_artifact_prompt,
    INTERACTIVE_ARTIFACT_SYSTEM_PROMPT
)


class MockArtifactProvider(BaseLLMProvider):
    def __init__(self, model_name: str = "mock-artifact-v1"):
        super().__init__(model_name=model_name)

    async def generate(self, messages: List[LLMMessage], system_prompt: str = ""):
        raise NotImplementedError()

    async def stream(self, messages: List[LLMMessage], system_prompt: str = "") -> AsyncIterator[str]:
        html_tokens = [
            "```html\n<!DOCTYPE html>\n<html>\n<head>\n",
            "<style>body { font-family: sans-serif; background: #0f172a; color: white; }</style>\n",
            "</head>\n<body>\n",
            "<h1>Elena Verna Activation Calculator</h1>\n",
            "<p>Grounded in [Lenny Podcast — Elena Verna — B2B Growth and Activation Loops]</p>\n",
            "<input type='number' id='signups' value='1000' />\n",
            "<div id='result'>Activation: 25%</div>\n",
            "<script>\n",
            "document.getElementById('signups').addEventListener('input', function() {\n",
            "  document.getElementById('result').innerText = 'Activation: ' + (this.value * 0.25);\n",
            "});\n",
            "</script>\n</body>\n</html>\n```"
        ]
        for t in html_tokens:
            yield t

    async def is_available(self) -> bool:
        return True


@pytest.mark.anyio
async def test_interactive_artifact_prompt_compilation():
    """
    Verifies that the interactive artifact prompt compiler enforces
    single-file standalone HTML/CSS/JS constraints, zero-network sandbox rules,
    and transcript citation requirements.
    """
    mock_chunks = [
        {
            "id": "elena_chunk_1",
            "source_title": "B2B Growth, PLG, and Activation Loops",
            "guest": "Elena Verna",
            "url": "https://www.lennyspodcast.com/elena-verna",
            "content": "Activation is the moment a user experiences core value. In PLG, measure the time to value."
        }
    ]
    sys_prompt, messages = build_interactive_artifact_prompt(
        topic="PLG Activation Rate Benchmark Calculator",
        retrieved_chunks=mock_chunks
    )

    # 1. Verify prompt rules
    assert "SINGLE-FILE COMPOSITIONAL CONTRACT" in sys_prompt
    assert "<!DOCTYPE html>" in sys_prompt
    assert "zero-network sandbox" in sys_prompt
    assert "[Lenny Podcast — Guest Name — Episode Title]" in sys_prompt

    # 2. Verify evidence isolation
    assert len(messages) == 1
    content = messages[0].content
    assert "<transcript_evidence>" in content
    assert "Elena Verna" in content
    assert "<tool_request>" in content
    assert "PLG Activation Rate Benchmark Calculator" in content


@pytest.mark.anyio
async def test_interactive_artifact_prompt_empty_chunks():
    """
    Verifies that empty transcript chunks generate the clear archive refusal block.
    """
    sys_prompt, messages = build_interactive_artifact_prompt(
        topic="Rocket Propulsion Dynamics",
        retrieved_chunks=[]
    )
    assert "[NO MATCHING TRANSCRIPT EXCERPTS FOUND IN ARCHIVE]" in messages[0].content


@pytest.mark.anyio
async def test_generate_interactive_artifact_endpoint_and_csp_headers(monkeypatch):
    """
    Tests:
    1. SSE streaming generation of HTML artifact
    2. Stripping of markdown code fences (```html)
    3. ArtifactModel persistence in DB as type="html"
    4. GET /api/artifacts/{id}/raw serving HTML with Content-Security-Policy headers
    """
    mock_provider = MockArtifactProvider()
    async def mock_get_streaming_provider(task: str):
        return mock_provider, False

    monkeypatch.setattr(model_router, "get_streaming_provider", mock_get_streaming_provider)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # 1. Create a session
        sess_resp = await client.post("/api/sessions", json={"title": "Calculator Session"})
        assert sess_resp.status_code == 201
        session_id = sess_resp.json()["id"]

        # 2. Call the interactive artifact streaming endpoint
        response = await client.post(
            "/api/skills/artifact",
            json={
                "topic": "activation loop and time to value metrics",
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
            for line in event.splitlines():
                if line.startswith("data: "):
                    payload = json.loads(line[6:])
                    if "token" in payload:
                        tokens.append(payload["token"])
                    elif payload.get("event") == "done":
                        done_data = payload

        assert done_data is not None
        assert done_data["event"] == "done"
        assert done_data["type"] == "html"
        artifact_id = done_data["artifact_id"]
        assert artifact_id is not None
        assert len(done_data["sources"]) > 0

        # 3. Retrieve the artifact metadata via standard JSON API
        art_resp = await client.get(f"/api/artifacts/{artifact_id}")
        assert art_resp.status_code == 200
        art_data = art_resp.json()
        assert art_data["type"] == "html"
        assert "<!DOCTYPE html>" in art_data["content"]
        # Verify markdown fences were cleanly stripped
        assert not art_data["content"].startswith("```")

        # 4. Probe the raw HTML sandbox endpoint /api/artifacts/{id}/raw
        raw_resp = await client.get(f"/api/artifacts/{artifact_id}/raw")
        assert raw_resp.status_code == 200
        assert "text/html" in raw_resp.headers.get("content-type", "")

        # Verify strict Content-Security-Policy (CSP) headers
        csp = raw_resp.headers.get("content-security-policy", "")
        assert "default-src 'none'" in csp
        assert "connect-src 'none'" in csp
        assert "script-src 'unsafe-inline'" in csp
        assert "style-src 'unsafe-inline'" in csp
        assert "img-src data:" in csp
        assert "frame-ancestors" in csp

        # Verify X-Content-Type-Options nosniff
        assert raw_resp.headers.get("x-content-type-options") == "nosniff"

        # Verify HTML content
        assert "Elena Verna Activation Calculator" in raw_resp.text
        assert "signups" in raw_resp.text


@pytest.mark.anyio
async def test_raw_endpoint_renders_markdown_safely():
    """
    Verifies that requesting the raw preview of a markdown artifact safely
    wraps it in an HTML container with identical CSP protection.
    """
    mock_provider = MockArtifactProvider()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # Create session and add a markdown artifact directly via session API
        sess_resp = await client.post("/api/sessions", json={"title": "Markdown Preview Test"})
        session_id = sess_resp.json()["id"]

        # Call essay endpoint to generate a markdown artifact
        from backend.tests.test_skills import MockEssayProvider
        from backend.app.llm.router import model_router
        mock_essay = MockEssayProvider()
        async def mock_get_essay_provider(task: str):
            return mock_essay, False

        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(model_router, "get_streaming_provider", mock_get_essay_provider)
            resp = await client.post(
                "/api/skills/essay",
                json={"topic": "growth loops", "session_id": session_id}
            )
            assert resp.status_code == 200

            # Extract artifact_id from SSE stream
            artifact_id = None
            for chunk in resp.text.split("\n\n"):
                if chunk.startswith("data: "):
                    data = json.loads(chunk[6:])
                    if data.get("event") == "done":
                        artifact_id = data.get("artifact_id")

            assert artifact_id is not None

            # Get raw preview
            raw_resp = await client.get(f"/api/artifacts/{artifact_id}/raw")
            assert raw_resp.status_code == 200
            assert "text/html" in raw_resp.headers.get("content-type", "")
            assert "connect-src 'none'" in raw_resp.headers.get("content-security-policy", "")
            assert "<pre>" in raw_resp.text


@pytest.mark.anyio
async def test_generate_artifact_refusal_on_irrelevant_topic():
    """
    Verifies that requesting an interactive tool on an out-of-domain topic
    gracefully refuses without writing an artifact.
    """
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/skills/artifact",
            json={"topic": "How to tune a vintage carburetor on a Harley Davidson"}
        )
        assert response.status_code == 200
        text = response.text
        assert "not covered in the archive" in text

        # Verify done event indicates no artifact
        done_event = None
        for chunk in text.split("\n\n"):
            if chunk.startswith("data: "):
                data = json.loads(chunk[6:])
                if data.get("event") == "done":
                    done_event = data

        assert done_event is not None
        assert done_event["artifact_id"] is None
        assert len(done_event["sources"]) == 0


@pytest.mark.anyio
async def test_artifact_raw_404_on_invalid_id():
    """
    Verifies that accessing an invalid artifact ID returns 404 with structured error JSON.
    """
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/api/artifacts/00000000-0000-0000-0000-000000000000/raw")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "ARTIFACT_NOT_FOUND"
