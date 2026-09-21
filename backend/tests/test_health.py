import pytest
from httpx import ASGITransport, AsyncClient
from backend.app.main import app
from backend.app.config import settings


@pytest.mark.anyio
async def test_root_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert data["version"] == settings.APP_VERSION


@pytest.mark.anyio
async def test_health_endpoint_contract():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        
        # Verify required contract fields
        assert "status" in data
        assert isinstance(data["db"], bool)
        assert isinstance(data["ollama"], bool)
        assert isinstance(data["cloud_llm_configured"], bool)
        assert data["version"] == settings.APP_VERSION


@pytest.mark.anyio
async def test_config_endpoint_no_secrets_leaked():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/config")
        assert response.status_code == 200
        data = response.json()
        
        # Assert required structure
        assert "providers" in data
        assert "ollama" in data["providers"]
        assert "gemini" in data["providers"]
        assert "openrouter" in data["providers"]
        assert "task_routing" in data
        assert "cors_origins" in data
        
        # Crucial security assertion: No raw secret keys exist anywhere in the payload
        response_text = response.text.lower()
        assert "api_key" not in response_text
        assert "secret" not in response_text
        assert "password" not in response_text


@pytest.mark.anyio
async def test_cors_headers():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
