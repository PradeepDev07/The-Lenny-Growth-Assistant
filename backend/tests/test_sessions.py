import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.app.main import app
from backend.app.db.session import init_db, async_session_factory
from backend.app.models.entities import MessageModel


@pytest.fixture(autouse=True)
async def setup_database():
    """Ensure database tables exist before each test."""
    await init_db()


@pytest.mark.anyio
async def test_session_lifecycle_and_cascade_deletion():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create a new session
        create_resp = await client.post(
            "/api/sessions",
            json={"title": "Brian Balfour Growth Loops Discussion", "metadata": {"tag": "growth"}}
        )
        assert create_resp.status_code == 201
        session_data = create_resp.json()
        session_id = session_data["id"]
        assert session_data["title"] == "Brian Balfour Growth Loops Discussion"
        assert session_data["message_count"] == 0

        # 2. List sessions and confirm presence
        list_resp = await client.get("/api/sessions")
        assert list_resp.status_code == 200
        sessions = list_resp.json()
        assert any(s["id"] == session_id for s in sessions)

        # 3. Add a user message
        msg1_resp = await client.post(
            f"/api/sessions/{session_id}/messages",
            json={
                "role": "user",
                "content": "What are the three main types of growth loops?"
            }
        )
        assert msg1_resp.status_code == 201
        msg1_data = msg1_resp.json()
        assert msg1_data["role"] == "user"
        assert msg1_data["session_id"] == session_id

        # 4. Add an assistant response with citations
        msg2_resp = await client.post(
            f"/api/sessions/{session_id}/messages",
            json={
                "role": "assistant",
                "content": "Brian Balfour identifies three dominant loops: Viral, Content, and Paid loops.",
                "sources": [
                    {
                        "episode": "Brian Balfour on Why Product Growth Loops Beat Funnels",
                        "guest": "Brian Balfour",
                        "chunk_index": 1
                    }
                ],
                "model_info": {"provider": "ollama", "model": "llama3.2:3b", "latency_ms": 320.5}
            }
        )
        assert msg2_resp.status_code == 201
        msg2_data = msg2_resp.json()
        assert msg2_data["role"] == "assistant"
        assert len(msg2_data["sources"]) == 1
        assert msg2_data["model_info"]["provider"] == "ollama"

        # 5. Fetch session detail and verify chronological order
        detail_resp = await client.get(f"/api/sessions/{session_id}")
        assert detail_resp.status_code == 200
        detail_data = detail_resp.json()
        assert len(detail_data["messages"]) == 2
        assert detail_data["messages"][0]["role"] == "user"
        assert detail_data["messages"][1]["role"] == "assistant"

        # 6. Verify list reflects message count == 2
        list_updated = await client.get("/api/sessions")
        matched = next(s for s in list_updated.json() if s["id"] == session_id)
        assert matched["message_count"] == 2

        # 7. Delete session
        del_resp = await client.delete(f"/api/sessions/{session_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["deleted"] is True

        # 8. Verify session is gone (404)
        get_deleted = await client.get(f"/api/sessions/{session_id}")
        assert get_deleted.status_code == 404
        assert get_deleted.json()["error"]["code"] == "SESSION_NOT_FOUND"

        # 9. Verify CASCADE DELETE: child messages are deleted from the database
        async with async_session_factory() as db:
            result = await db.execute(select(MessageModel).where(MessageModel.session_id == session_id))
            remaining_messages = result.scalars().all()
            assert len(remaining_messages) == 0, "Orphaned messages found! Cascade delete failed."


@pytest.mark.anyio
async def test_add_message_to_non_existent_session_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/sessions/non-existent-uuid/messages",
            json={"role": "user", "content": "Hello?"}
        )
        assert resp.status_code == 404
        data = resp.json()
        assert data["error"]["code"] == "SESSION_NOT_FOUND"
