import asyncio
import json
import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.research.schemas import (
    NewResearchRequest,
    NewResearchResponse,
    ReviseRequest,
    ReviseResponse,
    ConfirmResponse,
    ResearchResponse,
    ReportResponse,
    HistoryResponse,
    DeleteResponse,
    TokenStatsResponse,
    CancelResponse,
)
from src.api.research import service_plan
from src.middleware.auth import get_current_user, require_not_locked
from src.models.base import get_db
from src.models.user import User
from src.errors import NotFoundError, ForbiddenError, TokenInvalidError
from src.utils.ticket_store import verify_ticket
from src.repos.research_repo import ResearchRepository
from src.repos.sub_agent_result_repo import SubAgentResultRepository
from src.services.sse_manager import sse_manager
from src.services.exec_engine import cancel_signals, cancel_execution

logger = structlog.get_logger()

router = APIRouter()


# ── Fixed-path routes (MUST come before /{research_id}) ─────────


@router.post("/new", response_model=NewResearchResponse, status_code=201)
async def create_research(
    body: NewResearchRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_not_locked)],
):
    return await service_plan.create_research(db, current_user, body.topic, body.template)


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
):
    return await service_plan.get_history(db, current_user, page, pageSize)


@router.get("/stats/tokens", response_model=TokenStatsResponse)
async def get_token_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    return await service_plan.get_token_stats(db, current_user)


# ── Dynamic /{research_id} routes ───────────────────────────────


@router.post(
    "/{research_id}/plan/revise",
    response_model=ReviseResponse,
)
async def revise_plan(
    research_id: uuid.UUID,
    body: ReviseRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_not_locked)],
):
    return await service_plan.revise_plan(db, current_user, research_id, body.feedback)


@router.post(
    "/{research_id}/plan/confirm",
    response_model=ConfirmResponse,
)
async def confirm_plan(
    research_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_not_locked)],
):
    return await service_plan.confirm_plan(db, current_user, research_id)


@router.get(
    "/{research_id}",
    response_model=ResearchResponse,
)
async def get_research_detail(
    research_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    return await service_plan.get_research_detail(db, current_user, research_id)


@router.get(
    "/{research_id}/report",
    response_model=ReportResponse,
)
async def get_report(
    research_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    return await service_plan.get_research_report(db, current_user, research_id)


@router.get("/{research_id}/stream")
async def stream_research(
    research_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    ticket: Annotated[str, Query()],
):
    """SSE endpoint for real-time research progress updates."""
    user_id = verify_ticket(ticket)
    if user_id is None:
        raise TokenInvalidError("无效或过期的 ticket")

    repo = ResearchRepository(db)
    research = await repo.find_by_id(research_id)
    if research is None:
        raise NotFoundError("研究记录不存在")
    if research.user_id != user_id:
        raise ForbiddenError("无权访问该研究")

    async def event_generator():
        queue = await sse_manager.connect(research_id, user_id)
        try:
            # P2-1: 不在此处推送 plan_confirm，仅由 exec_engine 推送
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield {
                        "event": event.get("event", "message"),
                        "data": json.dumps(
                            event.get("data", {}), ensure_ascii=False
                        ),
                    }
                    if event.get("event") in ("report_complete", "error"):
                        break
                except asyncio.TimeoutError:
                    yield {
                        "event": "heartbeat",
                        "data": json.dumps({"type": "heartbeat"}),
                    }
        except asyncio.CancelledError:
            pass
        finally:
            sse_manager.disconnect(research_id, queue)

    from sse_starlette.sse import EventSourceResponse

    return EventSourceResponse(event_generator())


@router.post(
    "/{research_id}/cancel",
    response_model=CancelResponse,
)
async def cancel_research(
    research_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_not_locked)],
):
    from src.errors import InvalidStatusError

    repo = ResearchRepository(db)
    research = await repo.find_by_id(research_id)

    if research is None:
        raise NotFoundError("研究记录不存在")
    if research.user_id != current_user.id:
        raise ForbiddenError("无权操作该研究")
    if research.status != "running":
        raise InvalidStatusError("当前状态不允许取消")

    # 通知执行引擎取消
    if research_id not in cancel_signals:
        cancel_signals[research_id] = asyncio.Event()
    await cancel_execution(research_id)

    # P2-2: 等待引擎响应取消（最多 3 秒，比固定 0.5s 更可靠）
    try:
        for _ in range(30):  # 30 * 0.1s = 3s max
            await asyncio.sleep(0.1)
            await db.refresh(research)
            if research.status != "running":
                break
    except Exception:
        pass

    # 如果引擎仍在处理中，手动设置状态
    if research.status == "running":
        sa_repo = SubAgentResultRepository(db)
        sub_results = await sa_repo.find_by_research(research_id)
        has_started = any(sa.status in ("running", "completed") for sa in sub_results)

        if not has_started:
            research.status = "cancelled"
            for sa in sub_results:
                sa.status = "cancelled"
                await sa_repo.save(sa)
        else:
            research.status = "cancelled"

        await db.commit()
        await db.refresh(research)

    # P2-3: 清理 cancel signal（避免内存泄漏）
    cancel_signals.pop(research_id, None)

    return {"researchId": str(research.id), "status": research.status}


@router.delete(
    "/{research_id}",
    response_model=DeleteResponse,
)
async def delete_research(
    research_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_not_locked)],
):
    return await service_plan.soft_delete_research(db, current_user, research_id)
