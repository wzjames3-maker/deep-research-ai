"""
Research 全流程集成测试
AC-RES-001 ~ 024
"""
import pytest
from unittest.mock import AsyncMock, patch
from tests.integration.conftest import MOCK_PLAN


class TestResearchEndToEnd:
    """真正的端到端全流程串联测试."""

    @pytest.mark.asyncio
    async def test_full_research_lifecycle(self, async_client, auth_headers, db_session):
        """新建→修改×2→确认→执行完成→报告→Token统计→软删除: 单测串联完整流程."""
        # ── Step 1: 新建研究 ──
        with patch("src.api.research.service_plan.llm_service.generate_plan",
                   new_callable=AsyncMock, return_value=(MOCK_PLAN, 500)):
            r = await async_client.post("/api/v1/research/new", json={
                "topic": "AI 市场趋势分析",
                "template": "tech_research",
            }, headers=auth_headers)
        assert r.status_code == 201
        create_data = r.json()
        research_id = create_data["researchId"]
        assert create_data["planRound"] == 1
        assert 3 <= len(create_data["plan"]["subAgents"]) <= 5

        # ── Step 2: 修改计划 × 2 → planRound 递增 ──
        revised_plan_1 = [
            {"name": "revised_1", "goal": "目标1", "searchDirection": "dir1"},
            {"name": "revised_2", "goal": "目标2", "searchDirection": "dir2"},
        ]
        with patch("src.api.research.service_plan.llm_service.revise_plan",
                   new_callable=AsyncMock, return_value=(revised_plan_1, 200)):
            r = await async_client.post(
                f"/api/v1/research/{research_id}/plan/revise",
                json={"feedback": "增加对比分析"},
                headers=auth_headers,
            )
        assert r.status_code == 200
        assert r.json()["planRound"] == 2

        revised_plan_2 = [
            {"name": "revised_2_1", "goal": "目标A", "searchDirection": "dirA"},
        ]
        with patch("src.api.research.service_plan.llm_service.revise_plan",
                   new_callable=AsyncMock, return_value=(revised_plan_2, 150)):
            r = await async_client.post(
                f"/api/v1/research/{research_id}/plan/revise",
                json={"feedback": "简化为一个方向"},
                headers=auth_headers,
            )
        assert r.status_code == 200
        assert r.json()["planRound"] == 3

        # ── Step 3: 确认计划 → running ──
        with patch("src.services.exec_engine.run_research", new_callable=AsyncMock):
            r = await async_client.post(
                f"/api/v1/research/{research_id}/plan/confirm",
                headers=auth_headers,
            )
        assert r.status_code == 200
        assert r.json()["status"] == "running"
        assert "streamUrl" in r.json()

        # ── Step 4: 模拟执行完成（直接更新 DB）──
        from uuid import UUID
        from datetime import datetime, timezone
        from src.repos.research_repo import ResearchRepository
        repo = ResearchRepository(db_session)
        research = await repo.find_by_id(UUID(research_id))
        research.status = "completed"
        research.report_markdown = "# AI 市场趋势分析报告\n\n## 摘要\n这是一份完整的分析报告。"
        research.completed_at = datetime.now(timezone.utc)
        await db_session.commit()

        # ── Step 5: Polling 详情 → 确认状态为 completed ──
        r = await async_client.get(f"/api/v1/research/{research_id}", headers=auth_headers)
        assert r.status_code == 200
        detail = r.json()
        assert detail["status"] == "completed"

        # ── Step 6: 查看报告 → 非空 ──
        r = await async_client.get(f"/api/v1/research/{research_id}/report", headers=auth_headers)
        assert r.status_code == 200
        report_data = r.json()
        assert report_data["reportMarkdown"] is not None
        assert len(report_data["reportMarkdown"]) > 0
        assert "AI 市场趋势分析报告" in report_data["reportMarkdown"]

        # ── Step 7: Token 统计 → 累计值正确 ──
        r = await async_client.get("/api/v1/research/stats/tokens", headers=auth_headers)
        assert r.status_code == 200
        stats = r.json()
        assert stats["todayTokens"] >= 0
        assert stats["totalResearches"] >= 1
        # 500(plan) + 200(revise1) + 150(revise2) = 850 至少
        assert stats["todayTokens"] >= 850

        # ── Step 8: 历史列表包含该研究 ──
        r = await async_client.get("/api/v1/research/history", headers=auth_headers)
        assert r.status_code == 200
        ids = [item["researchId"] for item in r.json()["items"]]
        assert research_id in ids

        # ── Step 9: 软删除 ──
        r = await async_client.delete(f"/api/v1/research/{research_id}", headers=auth_headers)
        assert r.status_code == 200

        # ── Step 10: 软删除后历史列表不包含 ──
        r = await async_client.get("/api/v1/research/history", headers=auth_headers)
        assert r.status_code == 200
        ids = [item["researchId"] for item in r.json()["items"]]
        assert research_id not in ids


class TestResearchCreate:
    """研究创建场景."""

    @pytest.mark.asyncio
    async def test_create_research_success(self, async_client, auth_headers):
        """AC-RES-001: 正常发起研究 → 201, 含 3-5 sub-agents."""
        with patch("src.api.research.service_plan.llm_service.generate_plan",
                   new_callable=AsyncMock, return_value=(MOCK_PLAN, 500)):
            r = await async_client.post("/api/v1/research/new", json={
                "topic": "React 19 新特性分析",
                "template": "tech_research",
            }, headers=auth_headers)
        assert r.status_code == 201
        data = r.json()
        assert "researchId" in data
        assert data["planRound"] == 1
        sub_agents = data["plan"]["subAgents"]
        assert 3 <= len(sub_agents) <= 5
        for sa in sub_agents:
            assert "name" in sa
            assert "goal" in sa
            assert "searchDirection" in sa

    @pytest.mark.asyncio
    async def test_concurrent_research_409(self, async_client, auth_headers, db_session):
        """AC-RES-002: 已有 running 研究 → 409."""
        # Step 1: 通过 API 创建研究
        with patch("src.api.research.service_plan.llm_service.generate_plan",
                   new_callable=AsyncMock, return_value=(MOCK_PLAN, 500)):
            r = await async_client.post("/api/v1/research/new", json={
                "topic": "第一个研究",
                "template": "tech_research",
            }, headers=auth_headers)
        assert r.status_code == 201
        research_id = r.json()["researchId"]

        # Step 2: 通过 API 确认计划（使其变为 running）
        with patch("src.services.exec_engine.run_research", new_callable=AsyncMock):
            r = await async_client.post(
                f"/api/v1/research/{research_id}/plan/confirm",
                headers=auth_headers,
            )
        assert r.status_code == 200
        assert r.json()["status"] == "running"

        # Step 3: 尝试创建第二个研究 → 409
        with patch("src.api.research.service_plan.llm_service.generate_plan",
                   new_callable=AsyncMock, return_value=(MOCK_PLAN, 500)):
            r = await async_client.post("/api/v1/research/new", json={
                "topic": "另一个主题",
                "template": "tech_research",
            }, headers=auth_headers)
        assert r.status_code == 409
        assert r.json()["code"] == "RESEARCH_IN_PROGRESS"


class TestResearchPlanRevise:
    """计划修改场景."""

    @pytest.mark.asyncio
    async def test_revise_plan_increments_round(self, async_client, auth_headers, draft_research):
        """AC-RES-003: 修改计划 → planRound 递增."""
        research_id = draft_research["researchId"]

        revised_plan = [
            {"name": "revised_agent_1", "goal": "新目标1", "searchDirection": "direction1"},
            {"name": "revised_agent_2", "goal": "新目标2", "searchDirection": "direction2"},
        ]

        with patch("src.api.research.service_plan.llm_service.revise_plan",
                   new_callable=AsyncMock, return_value=(revised_plan, 200)):
            r = await async_client.post(
                f"/api/v1/research/{research_id}/plan/revise",
                json={"feedback": "增加一个对比竞品的子任务"},
                headers=auth_headers,
            )
        assert r.status_code == 200
        data = r.json()
        assert data["planRound"] == 2  # 第 1 次修改后，当前是第 2 轮
        assert len(data["plan"]["subAgents"]) == 2

    @pytest.mark.asyncio
    async def test_revise_11th_rejected_400(self, async_client, auth_headers, draft_research, db_session):
        """AC-RES-004: 第 11 次修改 → 400 TOO_MANY_REVISIONS."""
        research_id = draft_research["researchId"]

        # 手动插入 10 条 feedback 记录
        from src.repos.plan_feedback_repo import ResearchPlanFeedbackRepository
        from uuid import UUID
        fb_repo = ResearchPlanFeedbackRepository(db_session)

        research_uuid = UUID(research_id)
        for i in range(10):
            await fb_repo.create(
                research_id=research_uuid,
                round=i + 1,
                feedback=f"feedback {i}",
                plan_snapshot=MOCK_PLAN,
            )
        await db_session.commit()

        revised_plan = MOCK_PLAN
        with patch("src.api.research.service_plan.llm_service.revise_plan",
                   new_callable=AsyncMock, return_value=(revised_plan, 200)):
            r = await async_client.post(
                f"/api/v1/research/{research_id}/plan/revise",
                json={"feedback": "第 11 次修改"},
                headers=auth_headers,
            )
        assert r.status_code == 400
        assert r.json()["code"] == "TOO_MANY_REVISIONS"


class TestResearchConfirm:
    """计划确认场景."""

    @pytest.mark.asyncio
    async def test_confirm_plan_200(self, async_client, auth_headers, draft_research):
        """AC-RES-005: 确认计划 → status='running', streamUrl 存在."""
        research_id = draft_research["researchId"]

        with patch("src.services.exec_engine.run_research", new_callable=AsyncMock):
            r = await async_client.post(
                f"/api/v1/research/{research_id}/plan/confirm",
                headers=auth_headers,
            )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "running"
        assert "streamUrl" in data
        assert research_id in data["streamUrl"]


class TestResearchDetail:
    """研究详情场景."""

    @pytest.mark.asyncio
    async def test_get_detail_draft(self, async_client, auth_headers, draft_research):
        """AC-RES-022: 草稿详情 → status='draft', plan.subAgents 存在."""
        research_id = draft_research["researchId"]

        r = await async_client.get(f"/api/v1/research/{research_id}", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "draft"
        assert data["plan"]["subAgents"] is not None
        assert len(data["plan"]["subAgents"]) == 3
        assert data["planRound"] == 1


class TestResearchHistory:
    """历史列表场景."""

    @pytest.mark.asyncio
    async def test_history_contains_research(self, async_client, auth_headers, draft_research):
        """AC-RES-015: 创建的研究出现在历史列表中."""
        r = await async_client.get("/api/v1/research/history", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        items = data["items"]
        ids = [item["researchId"] for item in items]
        assert draft_research["researchId"] in ids

    @pytest.mark.asyncio
    async def test_soft_delete_removes_from_history(self, async_client, auth_headers, draft_research):
        """AC-RES-015: 软删除后 → 历史列表不包含."""
        research_id = draft_research["researchId"]

        # Delete
        del_r = await async_client.delete(f"/api/v1/research/{research_id}", headers=auth_headers)
        assert del_r.status_code == 200

        # Verify removed from history
        hist = await async_client.get("/api/v1/research/history", headers=auth_headers)
        assert hist.status_code == 200
        ids = [item["researchId"] for item in hist.json()["items"]]
        assert research_id not in ids


class TestResearchTokenStats:
    """Token 统计场景."""

    @pytest.mark.asyncio
    async def test_token_stats_after_create(self, async_client, auth_headers, draft_research):
        """AC-RES-016: 创建研究后 → token 统计可见."""
        r = await async_client.get("/api/v1/research/stats/tokens", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "todayTokens" in data
        assert "weekTokens" in data
        assert "totalResearches" in data
        assert data["totalResearches"] >= 1


class TestResearchCancel:
    """研究中断场景."""

    @pytest.mark.asyncio
    async def test_cancel_running_research(self, async_client, auth_headers, draft_research):
        """AC-RES-012: 中断 running 研究 → status='cancelled'."""
        research_id = draft_research["researchId"]

        # Confirm first
        with patch("src.services.exec_engine.run_research", new_callable=AsyncMock):
            await async_client.post(
                f"/api/v1/research/{research_id}/plan/confirm",
                headers=auth_headers,
            )

        # Cancel
        r = await async_client.post(f"/api/v1/research/{research_id}/cancel", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_draft_400(self, async_client, auth_headers, draft_research):
        """draft 状态不能 cancel → 400."""
        research_id = draft_research["researchId"]

        r = await async_client.post(f"/api/v1/research/{research_id}/cancel", headers=auth_headers)
        assert r.status_code == 400


class TestResearchReport:
    """报告查看场景."""

    @pytest.mark.asyncio
    async def test_report_not_ready_for_draft(self, async_client, auth_headers, draft_research):
        """draft 状态 → 查看报告 → 400."""
        research_id = draft_research["researchId"]

        r = await async_client.get(f"/api/v1/research/{research_id}/report", headers=auth_headers)
        assert r.status_code == 400
        assert r.json()["code"] == "REPORT_NOT_READY"
