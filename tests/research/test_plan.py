import json
from unittest.mock import patch, AsyncMock

import pytest

from src.errors import PlanGenerationFailedError
from src.models.research_plan_feedback import ResearchPlanFeedback

# Mock exec_engine.run_research to prevent real LLM/MCP calls in tests
_MOCK_RUN_RESEARCH = patch(
    "src.services.exec_engine.run_research",
    new_callable=AsyncMock,
)

# ── Helper Functions ─────────────────────────────────────────────


async def _register_and_login(async_client, suffix: str = "1"):
    """Register a user and return auth token."""
    username = f"planuser{suffix}"
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


async def _create_draft_research(async_client, token: str, topic: str = "测试主题"):
    """Create a draft research with mocked LLM."""
    mock_plan = [
        {"name": "Agent1", "goal": "Goal1", "searchDirection": "Dir1"},
        {"name": "Agent2", "goal": "Goal2", "searchDirection": "Dir2"},
        {"name": "Agent3", "goal": "Goal3", "searchDirection": "Dir3"},
    ]
    with patch(
        "src.api.research.service_plan.llm_service.generate_plan",
        new_callable=AsyncMock,
        return_value=(mock_plan, 100),
    ):
        resp = await async_client.post(
            "/api/v1/research/new",
            json={"topic": topic, "template": "tech_research"},
            headers={"Authorization": f"Bearer {token}"},
        )
    return resp


# ── Test Class ───────────────────────────────────────────────────


@pytest.mark.asyncio
class TestResearchPlan:
    # ── AC-RES-001: 正常发起研究 ──

    async def test_create_research_success(self, async_client):
        """正常发起 → 201, plan.subAgents ∈ [3,5], status='draft'"""
        token = await _register_and_login(async_client, "cs1")
        resp = await _create_draft_research(async_client, token)

        assert resp.status_code == 201
        data = resp.json()
        assert "researchId" in data
        assert 3 <= len(data["plan"]["subAgents"]) <= 5
        assert data["planRound"] == 1

    # ── AC-RES-002: 并发研究被拒绝 ──

    async def test_create_research_concurrent_rejected(self, async_client):
        """已有 running 的研究 → 409 RESEARCH_IN_PROGRESS"""
        token = await _register_and_login(async_client, "cc1")

        # Create + confirm first research → running
        resp1 = await _create_draft_research(async_client, token, "主题A")
        rid = resp1.json()["researchId"]
        with _MOCK_RUN_RESEARCH:
            await async_client.post(
                f"/api/v1/research/{rid}/plan/confirm",
                headers={"Authorization": f"Bearer {token}"},
            )

        # Try creating another research → 409
        resp2 = await _create_draft_research(async_client, token, "主题B")
        assert resp2.status_code == 409
        assert resp2.json()["code"] == "RESEARCH_IN_PROGRESS"

    # ── AC-RES-019: LLM 超时 → 500 ──

    async def test_create_research_llm_timeout(self, async_client):
        """LLM 超时 → 500 PLAN_GENERATION_FAILED"""
        token = await _register_and_login(async_client, "lt1")

        with patch(
            "src.api.research.service_plan.llm_service.generate_plan",
            new_callable=AsyncMock,
            side_effect=PlanGenerationFailedError("LLM 调用超时"),
        ):
            resp = await async_client.post(
                "/api/v1/research/new",
                json={"topic": "超时主题", "template": "tech_research"},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 500
        assert resp.json()["code"] == "PLAN_GENERATION_FAILED"

    # ── AC-RES-003: 修改计划 ──

    async def test_revise_plan_success(self, async_client):
        """反馈修改 → 200, planRound 递增, plan 更新"""
        token = await _register_and_login(async_client, "rv1")
        resp = await _create_draft_research(async_client, token)
        rid = resp.json()["researchId"]

        revised_plan = [
            {"name": "Revised1", "goal": "G1", "searchDirection": "D1"},
            {"name": "Revised2", "goal": "G2", "searchDirection": "D2"},
            {"name": "Revised3", "goal": "G3", "searchDirection": "D3"},
            {"name": "Revised4", "goal": "G4", "searchDirection": "D4"},
        ]
        with patch(
            "src.api.research.service_plan.llm_service.revise_plan",
            new_callable=AsyncMock,
            return_value=(revised_plan, 50),
        ):
            rev_resp = await async_client.post(
                f"/api/v1/research/{rid}/plan/revise",
                json={"feedback": "增加一个对比竞品"},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert rev_resp.status_code == 200
        data = rev_resp.json()
        assert len(data["plan"]["subAgents"]) == 4
        assert data["planRound"] == 2

    # ── AC-RES-004: 第 11 次修改被拒绝 ──

    async def test_revise_plan_too_many(self, async_client, test_db):
        """第 11 次修改 → 400 TOO_MANY_REVISIONS"""
        token = await _register_and_login(async_client, "tm1")
        resp = await _create_draft_research(async_client, token)
        rid = resp.json()["researchId"]

        # 直接插入 10 条 feedback 记录绕过 LLM 调用
        for i in range(10):
            fb = ResearchPlanFeedback(
                research_id=rid,
                round=i + 1,
                user_feedback=f"feedback_{i}",
                plan_snapshot={"subAgents": []},
            )
            test_db.add(fb)
        await test_db.commit()

        rev_resp = await async_client.post(
            f"/api/v1/research/{rid}/plan/revise",
            json={"feedback": "第 11 次"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert rev_resp.status_code == 400
        assert rev_resp.json()["code"] == "TOO_MANY_REVISIONS"

    # ── status ≠ draft 时修改 → 400 ──

    async def test_revise_plan_not_draft(self, async_client):
        """status≠'draft' 时修改 → 400 INVALID_STATUS"""
        token = await _register_and_login(async_client, "nd1")
        resp = await _create_draft_research(async_client, token)
        rid = resp.json()["researchId"]

        # Confirm → running
        with _MOCK_RUN_RESEARCH:
            await async_client.post(
                f"/api/v1/research/{rid}/plan/confirm",
                headers={"Authorization": f"Bearer {token}"},
            )

        rev_resp = await async_client.post(
            f"/api/v1/research/{rid}/plan/revise",
            json={"feedback": "不应该成功"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert rev_resp.status_code == 400
        assert rev_resp.json()["code"] == "INVALID_STATUS"

    # ── AC-RES-005: 确认计划 ──

    async def test_confirm_plan_success(self, async_client):
        """status='draft' → POST confirm → 200, status='running'"""
        token = await _register_and_login(async_client, "cf1")
        resp = await _create_draft_research(async_client, token)
        rid = resp.json()["researchId"]

        with _MOCK_RUN_RESEARCH:
            confirm_resp = await async_client.post(
                f"/api/v1/research/{rid}/plan/confirm",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert confirm_resp.status_code == 200
        data = confirm_resp.json()
        assert data["status"] == "running"
        assert "streamUrl" in data

    # ── 非 draft 状态确认 → 400 ──

    async def test_confirm_plan_not_draft(self, async_client):
        """非 draft 状态确认 → 400 INVALID_STATUS"""
        token = await _register_and_login(async_client, "cf2")
        resp = await _create_draft_research(async_client, token)
        rid = resp.json()["researchId"]

        # First confirm → running
        with _MOCK_RUN_RESEARCH:
            await async_client.post(
                f"/api/v1/research/{rid}/plan/confirm",
                headers={"Authorization": f"Bearer {token}"},
            )

        # Try confirm again → 400
        confirm_resp = await async_client.post(
            f"/api/v1/research/{rid}/plan/confirm",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert confirm_resp.status_code == 400
        assert confirm_resp.json()["code"] == "INVALID_STATUS"

    # ── AC-RES-022: 获取详情 — 草稿阶段 ──

    async def test_get_research_detail_draft(self, async_client):
        """status='draft' → GET /{id} → 含 plan, planRound"""
        token = await _register_and_login(async_client, "gd1")
        resp = await _create_draft_research(async_client, token)
        rid = resp.json()["researchId"]

        detail = await async_client.get(
            f"/api/v1/research/{rid}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert detail.status_code == 200
        data = detail.json()
        assert data["status"] == "draft"
        assert data["plan"] is not None
        assert data["planRound"] == 1

    # ── AC-RES-023: 获取详情 — 执行中 ──

    async def test_get_research_detail_running(self, async_client):
        """status='running' → GET /{id} → 含 subAgentResults"""
        token = await _register_and_login(async_client, "gd2")
        resp = await _create_draft_research(async_client, token)
        rid = resp.json()["researchId"]

        # Confirm → running
        with _MOCK_RUN_RESEARCH:
            await async_client.post(
                f"/api/v1/research/{rid}/plan/confirm",
                headers={"Authorization": f"Bearer {token}"},
            )

        detail = await async_client.get(
            f"/api/v1/research/{rid}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert detail.status_code == 200
        data = detail.json()
        assert data["status"] == "running"
        assert isinstance(data["subAgentResults"], list)

    # ── 不存在 / 已删除 → 404 ──

    async def test_get_research_not_found(self, async_client):
        """不存在/已删除 → 404"""
        token = await _register_and_login(async_client, "nf1")
        fake_id = "00000000-0000-0000-0000-000000000000"

        resp = await async_client.get(
            f"/api/v1/research/{fake_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    # ── 访问他人研究 → 403 ──

    async def test_get_research_unauthorized(self, async_client):
        """访问他人研究 → 403"""
        token1 = await _register_and_login(async_client, "ua1")
        token2 = await _register_and_login(async_client, "ua2")

        resp = await _create_draft_research(async_client, token1)
        rid = resp.json()["researchId"]

        # User2 尝试访问 User1 的研究
        resp2 = await async_client.get(
            f"/api/v1/research/{rid}",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert resp2.status_code == 403

    # ── AC-RES-006: 草稿恢复 ──

    async def test_draft_recovery(self, async_client):
        """status='draft' 的研究可获取并恢复"""
        token = await _register_and_login(async_client, "dr1")
        resp = await _create_draft_research(async_client, token)
        rid = resp.json()["researchId"]

        # 模拟用户刷新页面后获取详情
        detail = await async_client.get(
            f"/api/v1/research/{rid}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert detail.status_code == 200
        data = detail.json()
        assert data["status"] == "draft"
        assert data["plan"] is not None
        assert data["planRound"] >= 1
