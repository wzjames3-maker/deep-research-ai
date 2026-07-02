import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# Import shared mock data from root conftest
from tests.conftest import MOCK_PLAN, MOCK_PLAN_REVISED  # noqa: F401


@pytest_asyncio.fixture
async def registered_user(async_client):
    """注册一个用户并返回 {username, password, userId, token}."""
    username = f"intuser_{uuid4().hex[:6]}"
    password = "TestPass123"
    resp = await async_client.post("/api/v1/auth/register", json={
        "username": username, "password": password,
    })
    assert resp.status_code == 201
    data = resp.json()
    return {
        "username": username,
        "password": password,
        "userId": data["userId"],
        "token": data["token"],
    }


@pytest_asyncio.fixture
async def auth_headers(registered_user):
    """返回认证请求头."""
    return {"Authorization": f"Bearer {registered_user['token']}"}


@pytest_asyncio.fixture
async def draft_research(async_client, auth_headers, mock_llm_for_graph):
    """创建一个 draft 状态的研究（mock LLM，graph 仍创建 DB 记录）."""
    resp = await async_client.post("/api/v1/research/new", json={
        "topic": "AI 市场趋势分析",
        "template": "tech_research",
    }, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()
