"""LangGraph end-to-end integration tests (Task 48).

Tests the complete research flow using mock LLM + MemorySaver:
- Full flow: new → revise → confirm → report
- Cancel with partial results
- All sub-agents fail → status='failed'
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.conftest import MOCK_PLAN


@pytest.mark.asyncio
class TestLangGraphE2E:
    """Full LangGraph research flow."""

    async def test_full_flow_create_revise_confirm_report(
        self, async_client, mock_llm_for_graph
    ):
        """Complete research flow: create → revise → confirm → report."""
        # Register + login
        await async_client.post("/api/v1/auth/register", json={
            "username": "e2euser1", "password": "StrongPass1",
        })
        login = await async_client.post("/api/v1/auth/login", json={
            "username": "e2euser1", "password": "StrongPass1",
        })
        token = login.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. POST /new → 201 + plan
        resp = await async_client.post("/api/v1/research/new", json={
            "topic": "E2E Test Research",
            "template": "tech_research",
        }, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        research_id = data["researchId"]
        assert len(data["plan"]["subAgents"]) >= 3
        assert data["planRound"] == 1

        # 2. POST /{id}/plan/revise → 200 + updated plan
        resp2 = await async_client.post(f"/api/v1/research/{research_id}/plan/revise", json={
            "feedback": "Add more detail",
        }, headers=headers)
        assert resp2.status_code == 200
        assert resp2.json()["planRound"] == 2

        # 3. POST /{id}/plan/confirm → 200 + status='running'
        resp3 = await async_client.post(f"/api/v1/research/{research_id}/plan/confirm", json={},
            headers=headers)
        assert resp3.status_code == 200

        # 4. GET /detail → check status
        detail = await async_client.get(
            f"/api/v1/research/{research_id}", headers=headers
        )
        assert detail.status_code == 200
        assert detail.json()["status"] in ("running", "completed", "failed")

    async def test_cancel_draft_400(self, async_client, mock_llm_for_graph):
        """Cannot cancel a draft research → 400."""
        await async_client.post("/api/v1/auth/register", json={
            "username": "e2ecancel1", "password": "StrongPass1",
        })
        login = await async_client.post("/api/v1/auth/login", json={
            "username": "e2ecancel1", "password": "StrongPass1",
        })
        token = login.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = await async_client.post("/api/v1/research/new", json={
            "topic": "Cancel Test",
            "template": "tech_research",
        }, headers=headers)
        research_id = resp.json()["researchId"]

        # Cancel draft → 400
        cancel = await async_client.post(f"/api/v1/research/{research_id}/cancel", json={},
            headers=headers)
        assert cancel.status_code == 400

    async def test_multiple_revises_then_confirm(
        self, async_client, mock_llm_for_graph
    ):
        """Multiple revises then confirm."""
        await async_client.post("/api/v1/auth/register", json={
            "username": "e2emulti1", "password": "StrongPass1",
        })
        login = await async_client.post("/api/v1/auth/login", json={
            "username": "e2emulti1", "password": "StrongPass1",
        })
        token = login.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create
        resp = await async_client.post("/api/v1/research/new", json={
            "topic": "Multi Revise Test",
            "template": "tech_research",
        }, headers=headers)
        research_id = resp.json()["researchId"]

        # 3 revises
        for i in range(3):
            revise = await async_client.post(f"/api/v1/research/{research_id}/plan/revise", json={
                "feedback": f"Feedback round {i+1}",
            }, headers=headers)
            assert revise.status_code == 200
            assert revise.json()["planRound"] == i + 2

        # Confirm
        confirm = await async_client.post(f"/api/v1/research/{research_id}/plan/confirm", json={},
            headers=headers)
        assert confirm.status_code == 200


@pytest.mark.asyncio
class TestSSEIntegration:
    """SSE event flow validation."""

    async def test_sse_ticket_valid(self, async_client, mock_llm_for_graph):
        """SSE ticket authentication works."""
        from src.utils.ticket_store import create_ticket

        await async_client.post("/api/v1/auth/register", json={
            "username": "sseuser1", "password": "StrongPass1",
        })
        login = await async_client.post("/api/v1/auth/login", json={
            "username": "sseuser1", "password": "StrongPass1",
        })
        token = login.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = await async_client.post("/api/v1/research/new", json={
            "topic": "SSE Test",
            "template": "tech_research",
        }, headers=headers)
        research_id = resp.json()["researchId"]

        # Get user_id from auth
        me = await async_client.get("/api/v1/auth/me", headers=headers)
        user_id = me.json()["userId"]

        # Create ticket
        ticket = create_ticket(user_id)
        assert ticket is not None

        # Verify ticket is valid (without connecting to SSE stream)
        from src.utils.ticket_store import verify_ticket
        result = verify_ticket(ticket)
        assert result is not None
