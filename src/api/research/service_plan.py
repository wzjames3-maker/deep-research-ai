import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.errors import (
    ResearchInProgressError,
    PlanGenerationFailedError,
    NotFoundError,
    ForbiddenError,
    InvalidStatusError,
    TooManyRevisionsError,
    ReportNotReadyError,
)
from src.models.research import Research
from src.models.user import User
from src.repos.research_repo import ResearchRepository
from src.repos.plan_feedback_repo import ResearchPlanFeedbackRepository

logger = structlog.get_logger()

MAX_REVISIONS = 10


def _build_plan_response(plan_json: list[dict]) -> dict:
    """Normalize plan_json into API response format."""
    sub_agents = plan_json if isinstance(plan_json, list) else []
    return {
        "subAgents": [
            {
                "name": sa.get("name", ""),
                "goal": sa.get("goal", ""),
                "searchDirection": sa.get("searchDirection", ""),
            }
            for sa in sub_agents
        ]
    }


def _build_sub_agent_results(research: Research) -> list[dict]:
    """Build sub-agent result items from model."""
    return [
        {
            "name": sa.agent_name,
            "goal": sa.agent_goal,
            "status": sa.status,
            "findings": sa.findings_text or "",
            "visitedUrls": sa.visited_urls or [],
            "tokenUsed": sa.token_used,
        }
        for sa in research.sub_agent_results
    ]


# ── API-RES-001: POST /new ──────────────────────────────────────


def _make_session_factory(db: AsyncSession) -> async_sessionmaker:
    """Create an async session factory from the current DB session's engine."""
    engine = db.bind
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_research(
    db: AsyncSession, user: User, topic: str, template: str
) -> dict:
    """POST /new — Start new research graph (runs to interrupt, returns plan)."""
    repo = ResearchRepository(db)

    # RULE-RES-001: 仅 running 阻塞新研究（draft 不阻塞）
    if await repo.has_running_by_user(user.id):
        raise ResearchInProgressError("当前有一个进行中的研究")

    # V1.1.0: delegate to LangGraph via exec_engine
    from src.services.exec_engine import start_research_graph

    session_factory = _make_session_factory(db)
    try:
        result = await start_research_graph(session_factory, topic, template, user.id)
    except Exception as e:
        logger.error("create_research_graph_failed", error=str(e))
        raise PlanGenerationFailedError("研究计划生成失败，请重试")

    return {
        "researchId": str(result["research_id"]),
        "plan": _build_plan_response(result["plan"]),
        "planRound": result["plan_round"],
    }


# ── API-RES-002: POST /revise ───────────────────────────────────


async def revise_plan(
    db: AsyncSession, user: User, research_id, feedback: str
) -> dict:
    """POST /revise — Resume graph with revise action."""
    repo = ResearchRepository(db)
    research = await repo.find_by_id(research_id)

    if research is None:
        raise NotFoundError("研究记录不存在")
    if research.user_id != user.id:
        raise ForbiddenError("无权操作该研究")
    if research.status != "draft":
        raise InvalidStatusError("当前状态不允许修改计划")

    # 检查修改轮次
    fb_repo = ResearchPlanFeedbackRepository(db)
    revision_count = await fb_repo.count_by_research(research.id)
    if revision_count >= MAX_REVISIONS:
        raise TooManyRevisionsError(
            f"已达最大修改轮次（{MAX_REVISIONS}轮），请确认当前计划或重新发起研究"
        )

    # V1.1.0: delegate to LangGraph via exec_engine
    from src.services.exec_engine import resume_research_graph

    session_factory = _make_session_factory(db)
    result = await resume_research_graph(session_factory, research_id, "revise", feedback)

    return {
        "plan": _build_plan_response(result["plan"]),
        "planRound": result["plan_round"],
    }


# ── API-RES-003: POST /confirm ──────────────────────────────────


async def confirm_plan(db: AsyncSession, user: User, research_id) -> dict:
    from datetime import datetime, timezone

    repo = ResearchRepository(db)
    research = await repo.find_by_id(research_id)

    if research is None:
        raise NotFoundError("研究记录不存在")
    if research.user_id != user.id:
        raise ForbiddenError("无权操作该研究")
    if research.status != "draft":
        raise InvalidStatusError("当前状态不允许确认计划")

    research.status = "running"
    research.started_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(research)

    # P0-1: 触发执行引擎后台运行
    import asyncio
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession as _AsyncSession
    from src.services.exec_engine import run_research

    engine = db.bind
    session_factory = async_sessionmaker(
        engine, class_=_AsyncSession, expire_on_commit=False
    )
    asyncio.create_task(run_research(session_factory, research.id))

    return {
        "researchId": str(research.id),
        "status": research.status,
        "streamUrl": f"/api/v1/research/{research.id}/stream",
    }


# ── API-RES-005: GET /detail ────────────────────────────────────


async def get_research_detail(db: AsyncSession, user: User, research_id) -> dict:
    repo = ResearchRepository(db)
    research = await repo.find_by_id(research_id)

    if research is None:
        raise NotFoundError("研究记录不存在")
    if research.user_id != user.id:
        raise ForbiddenError("无权访问该研究")

    fb_repo = ResearchPlanFeedbackRepository(db)
    revision_count = await fb_repo.count_by_research(research.id)

    return {
        "researchId": str(research.id),
        "topic": research.topic,
        "template": research.template,
        "status": research.status,
        "plan": _build_plan_response(research.plan_json) if research.plan_json else None,
        "planRound": revision_count + 1,
        "subAgentResults": _build_sub_agent_results(research),
        "totalTokens": research.total_tokens,
        "createdAt": research.created_at,
        "startedAt": research.started_at,
        "completedAt": research.completed_at,
    }


# ── API-RES-006: GET /report ────────────────────────────────────


async def get_research_report(db: AsyncSession, user: User, research_id) -> dict:
    repo = ResearchRepository(db)
    research = await repo.find_by_id(research_id)

    if research is None:
        raise NotFoundError("研究记录不存在")
    if research.user_id != user.id:
        raise ForbiddenError("无权访问该研究")

    # completed 和 cancelled（有部分报告的）都允许查看
    if research.status not in ("completed", "cancelled"):
        raise ReportNotReadyError("研究报告尚未生成")
    if research.status == "cancelled" and not research.report_markdown:
        raise ReportNotReadyError("研究报告尚未生成")

    fb_repo = ResearchPlanFeedbackRepository(db)
    revision_count = await fb_repo.count_by_research(research.id)

    return {
        "researchId": str(research.id),
        "topic": research.topic,
        "template": research.template,
        "status": research.status,
        "plan": _build_plan_response(research.plan_json) if research.plan_json else None,
        "reportMarkdown": research.report_markdown,
        "subAgentResults": _build_sub_agent_results(research),
        "totalTokens": research.total_tokens,
        "createdAt": research.created_at,
        "completedAt": research.completed_at,
    }


# ── API-RES-007: GET /history ───────────────────────────────────


async def get_history(
    db: AsyncSession, user: User, page: int = 1, page_size: int = 20
) -> dict:
    page_size = min(page_size, 100)
    repo = ResearchRepository(db)
    items, total = await repo.find_by_user(user.id, page=page, page_size=page_size)

    return {
        "items": [
            {
                "researchId": str(r.id),
                "topic": r.topic,
                "template": r.template,
                "status": r.status,
                "totalTokens": r.total_tokens,
                "createdAt": r.created_at,
            }
            for r in items
        ],
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


# ── API-RES-009: DELETE /{id} ───────────────────────────────────


async def soft_delete_research(db: AsyncSession, user: User, research_id) -> dict:
    repo = ResearchRepository(db)
    research = await repo.find_by_id(research_id)

    if research is None:
        raise NotFoundError("研究记录不存在")
    if research.user_id != user.id:
        raise ForbiddenError("无权操作该研究")

    research.soft_delete()
    await db.commit()

    # V1.1.0: clean up LangGraph checkpoint data
    try:
        from src.services.checkpointer import get_checkpointer
        checkpointer = await get_checkpointer()
        await checkpointer.adelete_thread(str(research_id))
    except Exception as e:
        logger.warning("checkpoint_cleanup_failed", research_id=str(research_id), error=str(e))

    return {"deleted": True}


# ── API-RES-010: GET /stats/tokens ──────────────────────────────


async def get_token_stats(db: AsyncSession, user: User) -> dict:
    repo = ResearchRepository(db)
    return await repo.get_token_stats(user.id)
