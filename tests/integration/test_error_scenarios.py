"""
边界场景集成测试
EC-AUTH/RES/FE 各模块边界
"""
import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from tests.integration.conftest import MOCK_PLAN


class TestParamValidation:
    """参数校验边界."""

    @pytest.mark.asyncio
    async def test_empty_topic_400(self, async_client, auth_headers):
        """空 topic → 400."""
        r = await async_client.post("/api/v1/research/new", json={
            "topic": "",
            "template": "tech_research",
        }, headers=auth_headers)
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_template_400(self, async_client, auth_headers):
        """无效 template → 400/422."""
        r = await async_client.post("/api/v1/research/new", json={
            "topic": "AI 趋势",
            "template": "not_a_valid_template",
        }, headers=auth_headers)
        assert r.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_feedback_too_long(self, async_client, auth_headers, draft_research):
        """超长 feedback → 400/422."""
        research_id = draft_research["researchId"]
        long_feedback = "x" * 5001  # 超过 5000 字符

        r = await async_client.post(
            f"/api/v1/research/{research_id}/plan/revise",
            json={"feedback": long_feedback},
            headers=auth_headers,
        )
        # Should be rejected or truncated
        assert r.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_register_empty_username(self, async_client):
        """空用户名 → 400."""
        r = await async_client.post("/api/v1/auth/register", json={
            "username": "", "password": "StrongPass1",
        })
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_register_special_password(self, async_client):
        """EC-AUTH-002: 含特殊字符的密码 → bcrypt 正常处理."""
        r = await async_client.post("/api/v1/auth/register", json={
            "username": "specialpass1", "password": "P@ss'w\\\"ord<>1",
        })
        assert r.status_code == 201

        # Login with same password should work
        login = await async_client.post("/api/v1/auth/login", json={
            "username": "specialpass1", "password": "P@ss'w\\\"ord<>1",
        })
        assert login.status_code == 200


class TestPermissions:
    """权限边界."""

    @pytest.mark.asyncio
    async def test_access_other_user_research_403(self, async_client, draft_research):
        """访问他人研究 → 403."""
        # Register another user
        other_reg = await async_client.post("/api/v1/auth/register", json={
            "username": "otheruser2", "password": "StrongPass1",
        })
        other_token = other_reg.json()["token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}

        research_id = draft_research["researchId"]

        # GET detail → 403
        r = await async_client.get(f"/api/v1/research/{research_id}", headers=other_headers)
        assert r.status_code == 403

        # DELETE → 403
        r = await async_client.delete(f"/api/v1/research/{research_id}", headers=other_headers)
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_access_other_user_report_403(self, async_client, draft_research):
        """查看他人报告 → 403."""
        other_reg = await async_client.post("/api/v1/auth/register", json={
            "username": "otheruser3", "password": "StrongPass1",
        })
        other_token = other_reg.json()["token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}

        research_id = draft_research["researchId"]
        r = await async_client.get(f"/api/v1/research/{research_id}/report", headers=other_headers)
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_revise_other_user_plan_403(self, async_client, draft_research):
        """修改他人计划 → 403."""
        other_reg = await async_client.post("/api/v1/auth/register", json={
            "username": "otheruser4", "password": "StrongPass1",
        })
        other_token = other_reg.json()["token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}

        research_id = draft_research["researchId"]
        r = await async_client.post(
            f"/api/v1/research/{research_id}/plan/revise",
            json={"feedback": "test"},
            headers=other_headers,
        )
        assert r.status_code == 403


class TestStatusTransition:
    """状态转换异常."""

    @pytest.mark.asyncio
    async def test_concurrent_research_409(self, async_client, auth_headers, mock_llm_for_graph):
        """并发保护: 已有 running 研究时新建 → 409."""
        # 创建并确认第一个研究
        r1 = await async_client.post("/api/v1/research/new", json={
            "topic": "第一个研究", "template": "tech_research",
        }, headers=auth_headers)
        assert r1.status_code == 201
        rid = r1.json()["researchId"]

        with patch("src.services.exec_engine.run_research", new_callable=AsyncMock):
            rc = await async_client.post(
                f"/api/v1/research/{rid}/plan/confirm", headers=auth_headers)
        assert rc.status_code == 200

        # 第二个研究 → 409
        r2 = await async_client.post("/api/v1/research/new", json={
            "topic": "第二个研究", "template": "tech_research",
        }, headers=auth_headers)
        assert r2.status_code == 409
        assert r2.json()["code"] == "RESEARCH_IN_PROGRESS"

    @pytest.mark.asyncio
    async def test_cancel_draft_400(self, async_client, auth_headers, draft_research):
        """draft 状态 cancel → 400."""
        research_id = draft_research["researchId"]
        r = await async_client.post(f"/api/v1/research/{research_id}/cancel", headers=auth_headers)
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_confirm_already_running_400(self, async_client, auth_headers, draft_research):
        """已确认的研究再次 confirm → 400."""
        research_id = draft_research["researchId"]

        # First confirm
        with patch("src.services.exec_engine.run_research", new_callable=AsyncMock):
            r1 = await async_client.post(
                f"/api/v1/research/{research_id}/plan/confirm",
                headers=auth_headers,
            )
        assert r1.status_code == 200

        # Second confirm → should fail (status is now 'running')
        r2 = await async_client.post(
            f"/api/v1/research/{research_id}/plan/confirm",
            headers=auth_headers,
        )
        assert r2.status_code == 400

    @pytest.mark.asyncio
    async def test_revise_running_plan_400(self, async_client, auth_headers, draft_research):
        """running 状态修改计划 → 400."""
        research_id = draft_research["researchId"]

        # Confirm to make it running
        with patch("src.services.exec_engine.run_research", new_callable=AsyncMock):
            await async_client.post(
                f"/api/v1/research/{research_id}/plan/confirm",
                headers=auth_headers,
            )

        # Revise → should fail
        r = await async_client.post(
            f"/api/v1/research/{research_id}/plan/revise",
            json={"feedback": "test"},
            headers=auth_headers,
        )
        assert r.status_code == 400


class TestNotFound:
    """资源不存在."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_research_404(self, async_client, auth_headers):
        """GET 不存在的 research → 404."""
        fake_id = str(uuid4())
        r = await async_client.get(f"/api/v1/research/{fake_id}", headers=auth_headers)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_research_404(self, async_client, auth_headers):
        """DELETE 不存在的 research → 404."""
        fake_id = str(uuid4())
        r = await async_client.delete(f"/api/v1/research/{fake_id}", headers=auth_headers)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_report_nonexistent_404(self, async_client, auth_headers):
        """GET report 不存在 → 404."""
        fake_id = str(uuid4())
        r = await async_client.get(f"/api/v1/research/{fake_id}/report", headers=auth_headers)
        assert r.status_code == 404
