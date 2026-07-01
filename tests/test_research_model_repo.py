import pytest
from uuid import uuid4
from sqlalchemy import select, func
from src.models.user import User
from src.models.research import Research
from src.models.sub_agent_result import SubAgentResult
from src.models.research_plan_feedback import ResearchPlanFeedback
from src.repos.research_repo import ResearchRepository
from src.repos.sub_agent_result_repo import SubAgentResultRepository
from src.repos.plan_feedback_repo import ResearchPlanFeedbackRepository


async def _create_user(db_session) -> User:
    user = User(id=uuid4(), username=f"test_{uuid4().hex[:8]}", password_hash="hash", status="active")
    db_session.add(user)
    await db_session.commit()
    return user


class TestResearchModel:
    @pytest.mark.asyncio
    async def test_create_research_status_draft(self, db_session):
        user = await _create_user(db_session)
        repo = ResearchRepository(db_session)
        research = await repo.create(user.id, "AI trends", "tech_research")
        await db_session.commit()
        assert research.status == "draft"
        assert research.topic == "AI trends"
        assert research.template == "tech_research"

    @pytest.mark.asyncio
    async def test_find_by_id(self, db_session):
        user = await _create_user(db_session)
        repo = ResearchRepository(db_session)
        r = await repo.create(user.id, "Test", "custom")
        await db_session.commit()

        found = await repo.find_by_id(r.id)
        assert found is not None
        assert found.id == r.id

    @pytest.mark.asyncio
    async def test_find_by_id_excludes_deleted(self, db_session):
        user = await _create_user(db_session)
        repo = ResearchRepository(db_session)
        r = await repo.create(user.id, "Test", "custom")
        await db_session.commit()

        r.soft_delete()
        await db_session.commit()

        found = await repo.find_by_id(r.id)
        assert found is None

    @pytest.mark.asyncio
    async def test_find_active_by_user(self, db_session):
        user = await _create_user(db_session)
        repo = ResearchRepository(db_session)

        r = await repo.create(user.id, "Active", "tech_research")
        await db_session.commit()

        active = await repo.find_active_by_user(user.id)
        assert active is not None
        assert active.id == r.id

    @pytest.mark.asyncio
    async def test_find_active_by_user_none(self, db_session):
        user = await _create_user(db_session)
        repo = ResearchRepository(db_session)

        active = await repo.find_active_by_user(user.id)
        assert active is None

    @pytest.mark.asyncio
    async def test_find_by_user_pagination(self, db_session):
        user = await _create_user(db_session)
        repo = ResearchRepository(db_session)
        for i in range(5):
            r = await repo.create(user.id, f"Topic {i}", "custom")
        await db_session.commit()

        results, total = await repo.find_by_user(user.id, page=1, page_size=3)
        assert len(results) == 3
        assert total == 5

    @pytest.mark.asyncio
    async def test_has_active_research(self, db_session):
        user = await _create_user(db_session)
        repo = ResearchRepository(db_session)
        r = await repo.create(user.id, "Active", "tech_research")
        await db_session.commit()

        assert await Research.has_active_research(db_session, user.id) is True

    @pytest.mark.asyncio
    async def test_has_active_research_false(self, db_session):
        user = await _create_user(db_session)
        assert await Research.has_active_research(db_session, user.id) is False

    @pytest.mark.asyncio
    async def test_soft_delete(self, db_session):
        user = await _create_user(db_session)
        repo = ResearchRepository(db_session)
        r = await repo.create(user.id, "ToDelete", "custom")
        await db_session.commit()

        r.soft_delete()
        await db_session.commit()
        assert r.deleted_at is not None

    @pytest.mark.asyncio
    async def test_mark_failed(self, db_session):
        user = await _create_user(db_session)
        repo = ResearchRepository(db_session)
        r = await repo.create(user.id, "Fail", "tech_research")
        await db_session.commit()

        r.mark_failed("Test failure reason")
        await db_session.commit()
        assert r.status == "failed"
        assert r.error_message == "Test failure reason"
        assert r.completed_at is not None

    @pytest.mark.asyncio
    async def test_update_total_tokens(self, db_session):
        user = await _create_user(db_session)
        repo = ResearchRepository(db_session)
        r = await repo.create(user.id, "Tokens", "tech_research")
        await db_session.commit()

        sa_repo = SubAgentResultRepository(db_session)
        agents = [
            {"agent_name": "A1", "agent_goal": "G1", "search_direction": "D1"},
            {"agent_name": "A2", "agent_goal": "G2", "search_direction": "D2"},
        ]
        results = await sa_repo.bulk_create(r.id, agents)
        results[0].token_used = 100
        results[1].token_used = 200
        await db_session.commit()

        await db_session.refresh(r, ["sub_agent_results"])
        r.update_total_tokens()
        assert r.total_tokens == 300

    @pytest.mark.asyncio
    async def test_sub_agent_bulk_create(self, db_session):
        user = await _create_user(db_session)
        repo = ResearchRepository(db_session)
        r = await repo.create(user.id, "Bulk", "tech_research")
        await db_session.commit()

        sa_repo = SubAgentResultRepository(db_session)
        agents = [
            {"agent_name": "A1", "agent_goal": "G1", "search_direction": "D1"},
            {"agent_name": "A2", "agent_goal": "G2", "search_direction": "D2"},
            {"agent_name": "A3", "agent_goal": "G3", "search_direction": "D3"},
        ]
        results = await sa_repo.bulk_create(r.id, agents)
        await db_session.commit()

        assert len(results) == 3
        for res in results:
            assert res.research_id == r.id
            assert res.status == "pending"

    @pytest.mark.asyncio
    async def test_plan_feedback_create_and_count(self, db_session):
        user = await _create_user(db_session)
        repo = ResearchRepository(db_session)
        r = await repo.create(user.id, "Feedback", "custom")
        await db_session.commit()

        fb_repo = ResearchPlanFeedbackRepository(db_session)
        await fb_repo.create(r.id, 1, "Needs more detail", {"plan": "v1"})
        await fb_repo.create(r.id, 2, "Looks good", {"plan": "v2"})
        await db_session.commit()

        count = await fb_repo.count_by_research(r.id)
        assert count == 2

    @pytest.mark.asyncio
    async def test_count_revisions(self, db_session):
        user = await _create_user(db_session)
        repo = ResearchRepository(db_session)
        r = await repo.create(user.id, "Revisions", "custom")
        await db_session.commit()

        fb_repo = ResearchPlanFeedbackRepository(db_session)
        await fb_repo.create(r.id, 1, "Rev 1", {})
        await fb_repo.create(r.id, 2, "Rev 2", {})
        await fb_repo.create(r.id, 3, "Rev 3", {})
        await db_session.commit()

        count = await Research.count_revisions(db_session, r.id)
        assert count == 3
