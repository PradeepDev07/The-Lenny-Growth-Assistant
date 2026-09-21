import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy import select

from backend.app.llm.base import LLMMessage, LLMResponse
from backend.app.llm.ollama_provider import OllamaProvider
from backend.app.llm.gemini_provider import GeminiProvider
from backend.app.llm.openrouter_provider import OpenRouterProvider
from backend.app.llm.router import TaskRouter
from backend.app.db.session import init_db, async_session_factory
from backend.app.models.entities import RoutingLogModel


@pytest.mark.anyio
async def test_llm_response_normalization():
    resp = LLMResponse(
        text="Grounded answer based on Brian Balfour",
        prompt_tokens=150,
        completion_tokens=60,
        latency_ms=250.5,
        provider="ollama",
        model="llama3.2:3b",
        fallback_used=False
    )
    assert resp.text == "Grounded answer based on Brian Balfour"
    assert resp.latency_ms == 250.5
    assert resp.provider == "ollama"
    assert resp.fallback_used is False


@pytest.mark.anyio
async def test_provider_availability_checks():
    # Without keys
    gemini_no_key = GeminiProvider(api_key="")
    assert await gemini_no_key.is_available() is False

    openrouter_no_key = OpenRouterProvider(api_key="")
    assert await openrouter_no_key.is_available() is False

    # With keys
    gemini_with_key = GeminiProvider(api_key="fake-gemini-key")
    assert await gemini_with_key.is_available() is True


@pytest.mark.anyio
async def test_task_router_chain_order():
    router = TaskRouter()

    # Essay generation prioritizes strong model (OpenRouter)
    essay_chain = router.get_chain_for_task("essay_generation")
    assert isinstance(essay_chain[0], OpenRouterProvider)
    assert isinstance(essay_chain[1], GeminiProvider)
    assert isinstance(essay_chain[2], OllamaProvider)

    # Retrieval QA prioritizes fast long-context model (Gemini)
    qa_chain = router.get_chain_for_task("retrieval_qa")
    assert isinstance(qa_chain[0], GeminiProvider)
    assert isinstance(qa_chain[1], OpenRouterProvider)
    assert isinstance(qa_chain[2], OllamaProvider)

    # Offline demo mode uses Ollama exclusively
    offline_chain = router.get_chain_for_task("offline_demo_mode")
    assert len(offline_chain) == 1
    assert isinstance(offline_chain[0], OllamaProvider)


@pytest.mark.anyio
async def test_cascading_fallback_and_telemetry():
    """
    Simulates primary provider failure to verify that TaskRouter:
    1. Catches the error.
    2. Cascades to the secondary/local provider.
    3. Flags response.fallback_used = True.
    4. Writes an audit record to routing_logs.
    """
    await init_db()
    router = TaskRouter()

    # Mock Gemini as configured but failing with a network timeout
    mock_gemini = AsyncMock(spec=GeminiProvider)
    mock_gemini.is_available.return_value = True
    mock_gemini.generate.side_effect = RuntimeError("503 Service Unavailable: Gemini overloaded")
    mock_gemini.__class__.__name__ = "GeminiProvider"
    mock_gemini.model_name = "gemini-2.5-flash"

    # Mock Ollama as available and succeeding
    mock_ollama = AsyncMock(spec=OllamaProvider)
    mock_ollama.is_available.return_value = True
    mock_ollama.generate.return_value = LLMResponse(
        text="Fallback response from local Ollama",
        prompt_tokens=40,
        completion_tokens=20,
        latency_ms=180.0,
        provider="ollama",
        model="llama3.2:3b",
        fallback_used=False
    )
    mock_ollama.__class__.__name__ = "OllamaProvider"
    mock_ollama.model_name = "llama3.2:3b"

    # Replace chain with [failing Gemini, succeeding Ollama]
    with patch.object(router, "get_chain_for_task", return_value=[mock_gemini, mock_ollama]):
        async with async_session_factory() as db:
            response = await router.generate(
                task="retrieval_qa",
                messages=[LLMMessage(role="user", content="Explain growth loops")],
                db=db
            )

            # Assert fallback succeeded
            assert response.text == "Fallback response from local Ollama"
            assert response.provider == "ollama"
            assert response.fallback_used is True

            # Assert telemetry record was committed to the database
            result = await db.execute(
                select(RoutingLogModel)
                .where(RoutingLogModel.task == "retrieval_qa")
                .order_by(RoutingLogModel.created_at.desc())
            )
            log = result.scalars().first()
            assert log is not None
            assert log.provider == "ollama"
            assert log.model == "llama3.2:3b"
            assert log.fallback_used is True
