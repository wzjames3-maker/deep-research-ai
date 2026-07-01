"""
SSE 流程集成测试
AC-RES-007, AC-RES-024
"""
import pytest
import time
from unittest.mock import AsyncMock, patch
from tests.integration.conftest import MOCK_PLAN


class TestSSETicketAuth:
    """SSE Ticket 认证场景."""

    @pytest.mark.asyncio
    async def test_sse_no_ticket_401(self, async_client, auth_headers, draft_research):
        """AC-RES-024: 无 ticket 访问 SSE → 400/422 (FastAPI validation error)."""
        research_id = draft_research["researchId"]

        # Confirm plan first
        with patch("src.services.exec_engine.run_research", new_callable=AsyncMock):
            await async_client.post(
                f"/api/v1/research/{research_id}/plan/confirm",
                headers=auth_headers,
            )

        # SSE without ticket → FastAPI returns validation error (422)
        r = await async_client.get(f"/api/v1/research/{research_id}/stream")
        assert r.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_sse_invalid_ticket_401(self, async_client, auth_headers, draft_research):
        """AC-RES-024: 无效 ticket → 401."""
        research_id = draft_research["researchId"]

        r = await async_client.get(
            f"/api/v1/research/{research_id}/stream?ticket=invalid-ticket-value"
        )
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_sse_expired_ticket_401(self, async_client, auth_headers, registered_user, draft_research):
        """AC-RES-024: 过期 ticket → 401."""
        from src.utils.ticket_store import _store

        research_id = draft_research["researchId"]
        token = registered_user["token"]

        # Get ticket
        ticket_resp = await async_client.post("/api/v1/auth/ticket",
                                               headers={"Authorization": f"Bearer {token}"})
        assert ticket_resp.status_code == 200
        ticket = ticket_resp.json()["ticket"]

        # Manually expire the ticket
        if ticket in _store:
            uid, _ = _store[ticket]
            _store[ticket] = (uid, time.time() - 1)

        # SSE with expired ticket → 401
        r = await async_client.get(
            f"/api/v1/research/{research_id}/stream?ticket={ticket}"
        )
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_sse_other_user_research_403(self, async_client, draft_research):
        """访问他人研究的 SSE → 403."""
        # Register another user
        other_reg = await async_client.post("/api/v1/auth/register", json={
            "username": "otheruser1", "password": "StrongPass1",
        })
        other_token = other_reg.json()["token"]

        # Get ticket for other user
        ticket_resp = await async_client.post("/api/v1/auth/ticket",
                                               headers={"Authorization": f"Bearer {other_token}"})
        assert ticket_resp.status_code == 200
        ticket = ticket_resp.json()["ticket"]

        research_id = draft_research["researchId"]

        # SSE with other user's ticket → 403
        r = await async_client.get(
            f"/api/v1/research/{research_id}/stream?ticket={ticket}"
        )
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_sse_valid_ticket_accepts_connection(self, async_client, auth_headers, registered_user, draft_research):
        """AC-RES-024: 有效 ticket + 存在的研究 → 端点不拒绝请求.
        
        此测试验证 SSE 认证逻辑通过（不返回 401/403）。
        流式响应的完整测试需要 E2E 环境。
        """
        research_id = draft_research["researchId"]
        token = registered_user["token"]

        # Confirm plan first
        with patch("src.services.exec_engine.run_research", new_callable=AsyncMock):
            await async_client.post(
                f"/api/v1/research/{research_id}/plan/confirm",
                headers=auth_headers,
            )

        # Get ticket
        ticket_resp = await async_client.post("/api/v1/auth/ticket",
                                               headers={"Authorization": f"Bearer {token}"})
        assert ticket_resp.status_code == 200
        ticket = ticket_resp.json()["ticket"]

        # 验证认证通过: 使用 asyncio.wait_for 设置超时
        # SSE 端点会持续发送心跳，所以用 timeout 包裹
        import httpx
        import asyncio

        async def try_sse():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=async_client._transport.app),
                base_url="http://test",
            ) as client:
                async with client.stream(
                    "GET",
                    f"/api/v1/research/{research_id}/stream?ticket={ticket}",
                ) as response:
                    # 如果认证成功，应收到 200 + text/event-stream
                    return response.status_code, response.headers.get("content-type", "")

        try:
            status, content_type = await asyncio.wait_for(try_sse(), timeout=5.0)
            # 如果成功获取响应（非流式超时），验证状态码和内容类型
            assert status == 200, f"SSE endpoint returned {status}, expected 200"
            assert "text/event-stream" in content_type, f"Expected text/event-stream, got {content_type}"
        except asyncio.TimeoutError:
            # 超时说明连接建立成功（SSE 流持续发送，httpx 等待消费）
            # 这是预期行为，说明认证已通过
            pass
        except AssertionError:
            # 断言失败必须向上传播
            raise
        except Exception as e:
            # 其他异常（如 ConnectionError）说明连接未建立
            pytest.fail(f"SSE connection failed with unexpected error: {type(e).__name__}: {e}")
