import uuid
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock
from uuid import uuid4

import pytest

from src.models.research import Research
from src.models.sub_agent_result import SubAgentResult


MOCK_PLAN = [
    {"name": "A1", "goal": "G1", "searchDirection": "D1"},
    {"name": "A2", "goal": "G2", "searchDirection": "D2"},
    {"name": "A3", "goal": "G3", "searchDirection": "D3"},
]


async def _register_and_login(async_client, suffix: str = "h1"):
    username = f"histuser{suffix}"
    password = "TestPass1"
    await async_client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": password},
    )
    resp = await async_client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    return resp.json()["token"]


async def _create_research_via_api(async_client, token, topic="测试主题"):
    """Create research via API (requires mock_llm_for_graph fixture to be active)."""
    resp = await async_client.post(
        "/api/v1/research/new",
        json={"topic": topic, "template": "tech_research"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp


@pytest.mark.asyncio
class TestResearchHistory:
    # ── 历史列表 ──

    async def test_list_history(self, async_client, mock_llm_for_graph):
        """创建 3 条研究 → 历史返回 3 条, 按时间倒序"""
        token = await _register_and_login(async_client, "lh1")

        for i in range(3):
            await _create_research_via_api(async_client, token, f"主题{i}")

        resp = await async_client.get(
            "/api/v1/research/history",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 3
        assert len(data["items"]) >= 3

        # 按时间倒序
        created_times = [item["createdAt"] for item in data["items"]]
        assert created_times == sorted(created_times, reverse=True)

    async def test_list_history_empty(self, async_client):
        """无研究 → 返回空列表 + total=0"""
        token = await _register_and_login(async_client, "le1")

        resp = await async_client.get(
            "/api/v1/research/history",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_list_history_pagination(self, async_client, test_db):
        """创建 25 条, pageSize=20 → items=20, total=25"""
        token = await _register_and_login(async_client, "pg1")

        # 获取 user_id
        login_resp = await async_client.post(
            "/api/v1/auth/login",
            json={"username": "histuserpg1", "password": "TestPass1"},
        )
        from src.utils.jwt import decode_token

        payload = decode_token(token)
        user_id = uuid.UUID(payload["sub"])

        # 直接插入 25 条研究记录（绕过 LLM）
        for i in range(25):
            research = Research(
                user_id=user_id,
                topic=f"分页主题{i}",
                template="tech_research",
                status="draft",
                plan_json=MOCK_PLAN,
            )
            test_db.add(research)
        await test_db.commit()

        # 第一页
        resp = await async_client.get(
            "/api/v1/research/history?page=1&pageSize=20",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 20
        assert data["total"] >= 25
        assert data["page"] == 1
        assert data["pageSize"] == 20

        # 第二页
        resp2 = await async_client.get(
            "/api/v1/research/history?page=2&pageSize=20",
            headers={"Authorization": f"Bearer {token}"},
        )
        data2 = resp2.json()
        assert len(data2["items"]) >= 5

    # ── 软删除 ──

    async def test_soft_delete(self, async_client, mock_llm_for_graph):
        """DELETE → 200, 历史不再返回该记录"""
        token = await _register_and_login(async_client, "sd1")
        resp = await _create_research_via_api(async_client, token, "待删除主题")
        rid = resp.json()["researchId"]

        # 删除
        del_resp = await async_client.delete(
            f"/api/v1/research/{rid}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert del_resp.status_code == 200
        assert del_resp.json()["deleted"] is True

        # 历史中不再返回
        hist_resp = await async_client.get(
            "/api/v1/research/history",
            headers={"Authorization": f"Bearer {token}"},
        )
        items = hist_resp.json()["items"]
        assert all(item["researchId"] != rid for item in items)

        # 详情也返回 404
        detail_resp = await async_client.get(
            f"/api/v1/research/{rid}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert detail_resp.status_code == 404

    async def test_soft_delete_not_found(self, async_client):
        """不存在 → 404"""
        token = await _register_and_login(async_client, "sdn1")
        fake_id = "00000000-0000-0000-0000-000000000000"

        resp = await async_client.delete(
            f"/api/v1/research/{fake_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    # ── Token 统计 ──

    async def test_token_stats(self, async_client, test_db):
        """有 completed 研究 → todayTokens > 0, avgTokensPerResearch 合理"""
        token = await _register_and_login(async_client, "ts1")

        # 获取 user_id
        from src.utils.jwt import decode_token

        payload = decode_token(token)
        user_id = uuid.UUID(payload["sub"])

        # 插入一条 completed 研究 + sub-agent 带 token
        research = Research(
            user_id=user_id,
            topic="统计主题",
            template="tech_research",
            status="completed",
            plan_json=MOCK_PLAN,
            total_tokens=5000,
            completed_at=datetime.now(timezone.utc),
        )
        test_db.add(research)
        await test_db.flush()

        sa = SubAgentResult(
            research_id=research.id,
            agent_name="StatsAgent",
            agent_goal="G",
            search_direction="D",
            status="completed",
            token_used=5000,
            findings_text="some findings",
        )
        test_db.add(sa)
        await test_db.commit()

        resp = await async_client.get(
            "/api/v1/research/stats/tokens",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["todayTokens"] >= 5000
        assert data["totalResearches"] >= 1
        assert data["avgTokensPerResearch"] >= 5000
