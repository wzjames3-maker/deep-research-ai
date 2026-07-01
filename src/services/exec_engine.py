import asyncio
import uuid
from datetime import datetime, timezone
from typing import TypedDict

import structlog

from src.config import settings
from src.models.research import Research
from src.models.sub_agent_result import SubAgentResult
from src.repos.research_repo import ResearchRepository
from src.repos.sub_agent_result_repo import SubAgentResultRepository
from src.services import llm_service
from src.services.mcp_client import MCPSearchClient, SearchResult
from src.services.sse_manager import sse_manager

logger = structlog.get_logger()

cancel_signals: dict[uuid.UUID, asyncio.Event] = {}


class ResearchState(TypedDict):
    research_id: uuid.UUID
    topic: str
    template: str
    sub_agents: list[dict]
    sub_agent_results: dict
    status: str


async def cancel_execution(research_id: uuid.UUID) -> None:
    """Signal the execution engine to cancel."""
    if research_id not in cancel_signals:
        cancel_signals[research_id] = asyncio.Event()
    cancel_signals[research_id].set()


async def check_cancelled(research_id: uuid.UUID) -> bool:
    """Check if execution has been cancelled."""
    return cancel_signals.get(research_id, asyncio.Event()).is_set()


async def run_research(db_session_factory, research_id: uuid.UUID) -> None:
    """Main execution entry point for a research."""
    cancel_signals[research_id] = asyncio.Event()

    try:
        async with db_session_factory() as db:
            repo = ResearchRepository(db)
            research = await repo.find_by_id(research_id)
            if research is None:
                return

            plan = research.plan_json or []
            topic = research.topic
            template = research.template

        # Push plan_confirm event (single source — only engine pushes this)
        await sse_manager.push_event(
            research_id,
            "plan_confirm",
            {"status": "confirmed", "researchId": str(research_id)},
        )

        # Run sub-agents in parallel
        sub_agent_tasks = []
        for sa_plan in plan:
            task = asyncio.create_task(
                _run_sub_agent(db_session_factory, research_id, sa_plan, topic)
            )
            sub_agent_tasks.append(task)

        results = await asyncio.gather(*sub_agent_tasks, return_exceptions=True)

        # Check cancellation — generate partial report if possible (P0-4)
        if await check_cancelled(research_id):
            await _handle_cancel_aggregation(
                db_session_factory, research_id, topic, plan
            )
            return

        # Aggregate results
        await _aggregate_results(db_session_factory, research_id, topic, plan, results)

    except Exception as e:
        logger.error("exec_engine_error", research_id=str(research_id), error=str(e))
        try:
            async with db_session_factory() as db:
                repo = ResearchRepository(db)
                research = await repo.find_by_id(research_id)
                if research:
                    research.mark_failed(f"执行引擎错误: {e}")
                    await db.commit()
        except Exception:
            pass
        await sse_manager.push_event(
            research_id, "error", {"status": "failed", "error": str(e)}
        )
    finally:
        cancel_signals.pop(research_id, None)


async def _handle_cancel_aggregation(
    db_session_factory,
    research_id: uuid.UUID,
    topic: str,
    plan: list[dict],
) -> None:
    """Handle cancellation: generate partial report if any sub-agents completed."""
    async with db_session_factory() as db:
        repo = ResearchRepository(db)
        research = await repo.find_by_id(research_id)
        if research is None:
            return

        sa_repo = SubAgentResultRepository(db)
        sub_results = await sa_repo.find_by_research(research_id)
        completed = [sa for sa in sub_results if sa.status == "completed"]

        if not completed:
            # 无已完成结果 → 直接标记 cancelled，不生成报告
            if research.status == "running":
                research.status = "cancelled"
                await db.commit()
            await sse_manager.push_event(
                research_id,
                "error",
                {"status": "cancelled", "researchId": str(research_id)},
            )
            return

        # 有已完成结果 → 生成部分报告 (AC-RES-013, RULE-RES-009)
        findings_parts = []
        for sa in completed:
            findings_parts.append(
                f"## {sa.agent_name}\n\n{sa.findings_text or ''}\n\n"
                f"来源: {', '.join(sa.visited_urls) if sa.visited_urls else '无'}"
            )

        cancelled_names = [
            sa.agent_name for sa in sub_results if sa.status == "cancelled"
        ]
        if cancelled_names:
            findings_parts.append(
                f"\n> 注意: 研究被用户中断。共 {len(sub_results)} 个子课题，"
                f"其中 {len(cancelled_names)} 个（{', '.join(cancelled_names)}）被取消。"
            )

        sub_agent_findings = "\n\n---\n\n".join(findings_parts)

        # Push aggregation_start so frontend shows progress during partial report generation
        await sse_manager.push_event(
            research_id,
            "aggregation_start",
            {
                "status": "aggregating",
                "completedAgents": len(completed),
                "totalAgents": len(sub_results),
            },
        )

        report, report_tokens = await llm_service.aggregate_report(
            topic, plan, sub_agent_findings
        )

        research.report_markdown = report
        research.update_total_tokens()
        research.total_tokens += report_tokens  # 报告 token 在 sub-agent 总和之上累加
        research.status = "cancelled"
        research.completed_at = datetime.now(timezone.utc)
        await db.commit()

        await sse_manager.push_event(
            research_id,
            "report_complete",
            {
                "status": "cancelled",
                "reportMarkdown": report,
                "totalTokens": research.total_tokens,
            },
        )


async def _aggregate_results(
    db_session_factory,
    research_id: uuid.UUID,
    topic: str,
    plan: list[dict],
    results: list,
) -> None:
    """Aggregate sub-agent results and generate report."""
    async with db_session_factory() as db:
        repo = ResearchRepository(db)
        research = await repo.find_by_id(research_id)
        if research is None:
            return

        sa_repo = SubAgentResultRepository(db)
        sub_results = await sa_repo.find_by_research(research_id)

        completed = [sa for sa in sub_results if sa.status == "completed"]
        all_failed = all(sa.status == "failed" for sa in sub_results)

        if all_failed:
            research.status = "failed"
            research.error_message = "所有搜索源均未返回有效信息，请检查 MCP Server 状态后重试"
            research.completed_at = datetime.now(timezone.utc)
            await db.commit()
            await sse_manager.push_event(
                research_id,
                "error",
                {
                    "status": "failed",
                    "error": "所有搜索源均未返回有效信息",
                },
            )
            return

        # Generate report from completed results
        findings_parts = []
        for sa in completed:
            findings_parts.append(
                f"## {sa.agent_name}\n\n{sa.findings_text or '未找到相关信息'}\n\n"
                f"来源: {', '.join(sa.visited_urls) if sa.visited_urls else '无'}"
            )

        failed_names = [sa.agent_name for sa in sub_results if sa.status == "failed"]
        if failed_names:
            findings_parts.append(
                f"\n> 注意: 共 {len(sub_results)} 个子课题，其中 "
                f"{len(failed_names)} 个子课题（{', '.join(failed_names)}）未能完成。"
            )

        sub_agent_findings = "\n\n---\n\n".join(findings_parts)

        # Push aggregation_start event so frontend can show progress
        await sse_manager.push_event(
            research_id,
            "aggregation_start",
            {
                "status": "aggregating",
                "completedAgents": len(completed),
                "totalAgents": len(sub_results),
            },
        )

        report, report_tokens = await llm_service.aggregate_report(
            topic, plan, sub_agent_findings
        )

        research.report_markdown = report
        research.update_total_tokens()
        research.total_tokens += report_tokens  # 报告 token 在 sub-agent 总和之上累加
        research.status = "completed"
        research.completed_at = datetime.now(timezone.utc)
        await db.commit()

        await sse_manager.push_event(
            research_id,
            "report_complete",
            {
                "status": "completed",
                "reportMarkdown": report,
                "totalTokens": research.total_tokens,
            },
        )


async def _run_sub_agent(
    db_session_factory, research_id: uuid.UUID, sa_plan: dict, topic: str = ""
) -> dict:
    """Run a single sub-agent with up to 4 rounds of search."""
    agent_name = sa_plan.get("name", "")
    search_direction = sa_plan.get("searchDirection", "")

    async with db_session_factory() as db:
        sa_repo = SubAgentResultRepository(db)
        sub_results = await sa_repo.find_by_research(research_id)
        sa_result = next(
            (sa for sa in sub_results if sa.agent_name == agent_name), None
        )
        if sa_result is None:
            return {"error": f"SubAgentResult not found for {agent_name}"}

        sa_result.status = "running"
        sa_result.started_at = datetime.now(timezone.utc)
        await sa_repo.save(sa_result)
        await db.commit()

    await sse_manager.push_event(
        research_id,
        "sub_agent_start",
        {
            "subAgentId": str(sa_result.id) if sa_result else "",
            "name": agent_name,
            "goal": sa_plan.get("goal", ""),
            "status": "running",
        },
    )

    visited_urls: set[str] = set()
    findings = ""
    rounds_completed = 0
    total_token = 0
    has_error = False  # P0-3: Track whether sub-agent encountered errors

    mcp_client = MCPSearchClient(settings.BRAVE_MCP_URL)

    # P1-2: timeout wraps the entire sub-agent execution (RULE-RES-007: 3 min)
    try:
        async with asyncio.timeout(settings.SUB_AGENT_TIMEOUT):
            for round_idx in range(4):
                if await check_cancelled(research_id):
                    break

                try:
                    search_results = await mcp_client.search(search_direction)
                except Exception:
                    logger.warning(
                        "mcp_search_failed",
                        agent=agent_name,
                        round=round_idx + 1,
                    )
                    has_error = True
                    break

                # URL dedup (RULE-RES-006)
                new_results = []
                for r in search_results:
                    from src.services.mcp_client import _normalize_url

                    normalized = _normalize_url(r.url)
                    if normalized not in visited_urls:
                        visited_urls.add(normalized)
                        new_results.append(r)

                await sse_manager.push_event(
                    research_id,
                    "sub_agent_round",
                    {
                        "subAgentId": str(sa_result.id) if sa_result else "",
                        "round": round_idx + 1,
                        "searchQuery": search_direction,
                    },
                )

                results_text = _format_search_results(new_results)
                llm_result, llm_tokens = await llm_service.sub_agent_search(
                    findings, results_text, search_direction, topic=topic
                )
                total_token += llm_tokens

                findings = llm_result.get("findings", findings)
                sufficient = llm_result.get("sufficient", True)
                new_keywords = llm_result.get("new_keywords", "")

                rounds_completed = round_idx + 1

                if sufficient:
                    break
                if new_keywords:
                    search_direction = new_keywords

    except asyncio.TimeoutError:
        logger.warning("sub_agent_timeout", agent=agent_name)
        has_error = True
    except Exception as e:
        logger.error("sub_agent_error", agent=agent_name, error=str(e))
        has_error = True

    # Update DB (P0-3: correct status based on has_error)
    try:
        async with db_session_factory() as db:
            sa_repo = SubAgentResultRepository(db)
            sub_results = await sa_repo.find_by_research(research_id)
            sa_result = next(
                (sa for sa in sub_results if sa.agent_name == agent_name), None
            )
            if sa_result:
                if await check_cancelled(research_id):
                    sa_result.status = "cancelled"
                elif has_error:
                    sa_result.status = "failed"
                    sa_result.error_message = "Sub-agent 执行过程中发生错误"
                    sa_result.findings_text = findings or ""
                else:
                    sa_result.status = "completed"
                    sa_result.findings_text = findings
                sa_result.completed_at = datetime.now(timezone.utc)
                sa_result.rounds_completed = rounds_completed
                sa_result.visited_urls = list(visited_urls)
                sa_result.token_used = total_token
                await sa_repo.save(sa_result)
                await db.commit()

        event_type = (
            "sub_agent_fail"
            if (sa_result and sa_result.status in ("failed", "cancelled"))
            else "sub_agent_complete"
        )
        await sse_manager.push_event(
            research_id,
            event_type,
            {
                "subAgentId": str(sa_result.id) if sa_result else "",
                "name": agent_name,
                "status": sa_result.status if sa_result else "unknown",
                "roundsUsed": rounds_completed,
                "preview": (findings or "")[:200],
                "tokenUsed": total_token,
                **(
                    {"error": sa_result.error_message}
                    if sa_result and sa_result.status == "failed"
                    else {}
                ),
            },
        )
    except Exception as e:
        logger.error("sub_agent_db_error", agent=agent_name, error=str(e))

    return {
        "name": agent_name,
        "findings": findings,
        "visited_urls": list(visited_urls),
        "token_used": total_token,
        "status": sa_result.status if sa_result else "unknown",
    }


def _format_search_results(results: list[SearchResult]) -> str:
    """Format search results into a readable string for LLM."""
    if not results:
        return "未找到相关搜索结果。"
    parts = []
    for i, r in enumerate(results, 1):
        parts.append(f"[{i}] {r.title}\nURL: {r.url}\n{r.snippet}")
    return "\n\n".join(parts)
