import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from uuid import uuid4

# 标准 mock plan（3 个 sub-agents）
MOCK_PLAN = [
    {"name": "market_analyst", "goal": "分析市场规模", "searchDirection": "AI market size"},
    {"name": "tech_analyst", "goal": "分析技术趋势", "searchDirection": "AI technology trends"},
    {"name": "competitor_analyst", "goal": "分析竞争对手", "searchDirection": "AI competitors"},
]


@pytest.fixture
def mock_plan():
    return MOCK_PLAN


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
async def draft_research(async_client, auth_headers):
    """创建一个 draft 状态的研究（使用 mock LLM）并返回 response data."""
    with patch("src.api.research.service_plan.llm_service.generate_plan",
               new_callable=AsyncMock, return_value=(MOCK_PLAN, 500)):
        resp = await async_client.post("/api/v1/research/new", json={
            "topic": "AI 市场趋势分析",
            "template": "tech_research",
        }, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()
