"""Main Research Graph implementation (LangGraph StateGraph).

This module implements the main research workflow:
START → plan_generation → human_review (interrupt) → route_after_review
    → (revise) plan_revision → human_review (loop)
    → (confirm) dispatch → sub_agent_graph (×N) → check_cancel → aggregate → END

Task 39: plan_generation_node, human_review_node, plan_revision_node, route_after_review
Task 40: dispatch_node, aggregate_node, partial_aggregate_node, compile_research_graph
"""

import json
from typing import Any
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

from src.services.graph_state import ResearchState
from src.services import llm_service
from src.services.sse_manager import sse_manager
from src.repos.research_repo import ResearchRepository
from src.repos.sub_agent_result_repo import SubAgentResultRepository
from src.repos.plan_feedback_repo import ResearchPlanFeedbackRepository
from src.models.research import Research

import structlog

logger = structlog.get_logger()

# Maximum number of plan revisions allowed (RULE-RES-003)
MAX_REVISIONS = 10

# Module-level LLM service override (for testing)
_llm_service_override: Any = None

# Module-level MCP client override (for testing)
_mcp_client_override: Any = None


def _get_llm_service():
    """Get LLM service (real or override for testing)."""
    return _llm_service_override if _llm_service_override is not None else llm_service


# ---------------------------------------------------------------------------
# Plan Generation Node
# ---------------------------------------------------------------------------

async def plan_generation_node(state: ResearchState, config: RunnableConfig) -> dict:
    """Generate research plan using LLM.

    Creates Research record and SubAgentResult records in DB.
    Returns updated state with plan, plan_round, status, research_id.
    """
    db_session_factory = config["configurable"]["db_session_factory"]
    topic = state["topic"]
    template = state["template"]
    user_id = state["user_id"]
    research_id = state.get("research_id")

    # Generate plan using LLM
    llm = _get_llm_service()
    plan, plan_tokens = await llm.generate_plan(topic, template)

    # Ensure plan has 3-5 sub-agents (RULE-RES-002)
    if len(plan) < 3:
        logger.warning("plan_too_few_agents", count=len(plan))
    elif len(plan) > 5:
        logger.warning("plan_too_many_agents", count=len(plan))
        plan = plan[:5]

    session = await db_session_factory().__aenter__()
    try:
        repo = ResearchRepository(session)

        # Check if research_id already exists (for pre-generated IDs)
        if research_id:
            existing = await repo.find_by_id(research_id)
            if existing:
                # Update existing record
                existing.plan_json = plan
                existing.plan_round = 1
                existing.total_tokens = plan_tokens
                await session.commit()
                return {
                    "plan": plan,
                    "plan_round": 1,
                    "total_tokens": plan_tokens,
                    "status": "draft",
                }

        # Create new Research record with pre-generated ID
        research = await repo.create(user_id=user_id, topic=topic, template=template)
        if research_id:
            research.id = research_id  # Use pre-generated ID from exec_engine
        research.plan_json = plan
        research.plan_round = 1
        research.total_tokens = plan_tokens
        research.status = "draft"

        # Create SubAgentResult records (pending)
        sa_repo = SubAgentResultRepository(session)
        sub_agents = [
            {
                "agent_name": agent_def.get("name", ""),
                "agent_goal": agent_def.get("goal", ""),
                "search_direction": agent_def.get("searchDirection", ""),
            }
            for agent_def in plan
        ]
        await sa_repo.bulk_create(research.id, sub_agents)

        await session.commit()

        return {
            "research_id": research.id,
            "plan": plan,
            "plan_round": 1,
            "total_tokens": plan_tokens,
            "status": "draft",
        }
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# ---------------------------------------------------------------------------
# Human Review Node (interrupt)
# ---------------------------------------------------------------------------

async def human_review_node(state: ResearchState) -> dict:
    """Pause graph execution, wait for user action.

    Uses LangGraph interrupt() to pause execution.
    API layer resumes with Command(resume={...}).

    Resume value format:
    - {"action": "confirm"} → proceed to dispatch
    - {"action": "revise", "feedback": "..."} → proceed to plan_revision
    """
    # Push plan to SSE for real-time updates
    research_id = state.get("research_id")
    if research_id:
        await sse_manager.push_event(
            research_id,
            "plan_ready",
            {
                "plan": state["plan"],
                "plan_round": state["plan_round"],
                "status": "awaiting_review",
            },
        )

    # Interrupt and wait for user action
    user_action = interrupt({
        "plan": state["plan"],
        "plan_round": state["plan_round"],
        "status": "awaiting_review",
    })

    # user_action comes from Command(resume={...})
    if isinstance(user_action, dict):
        action = user_action.get("action", "confirm")
        feedback = user_action.get("feedback")
    else:
        action = "confirm"
        feedback = None

    return {
        "_action": action,
        "feedback": feedback,
    }


# ---------------------------------------------------------------------------
# Plan Revision Node
# ---------------------------------------------------------------------------

async def plan_revision_node(state: ResearchState, config: RunnableConfig) -> dict:
    """Revise plan based on user feedback.

    Checks revision limit (RULE-RES-003: max 10 revisions).
    Calls LLM to revise plan, updates DB records.
    """
    db_session_factory = config["configurable"]["db_session_factory"]
    feedback = state.get("feedback", "")
    current_plan = state["plan"]
    topic = state["topic"]
    research_id = state["research_id"]
    plan_round = state["plan_round"]

    # Check revision limit (RULE-RES-003)
    if plan_round >= MAX_REVISIONS:
        logger.warning("max_revisions_reached", plan_round=plan_round)
        from src.errors import TooManyRevisionsError
        raise TooManyRevisionsError(f"Maximum {MAX_REVISIONS} revisions reached")

    # Call LLM to revise plan
    llm = _get_llm_service()
    new_plan, revise_tokens = await llm.revise_plan(topic, current_plan, feedback)

    # Ensure plan has 3-5 sub-agents
    if len(new_plan) < 3:
        logger.warning("revised_plan_too_few_agents", count=len(new_plan))
    elif len(new_plan) > 5:
        logger.warning("revised_plan_too_many_agents", count=len(new_plan))
        new_plan = new_plan[:5]

    new_round = plan_round + 1
    total_tokens = state.get("total_tokens", 0) + revise_tokens

    async with db_session_factory() as session:
        repo = ResearchRepository(session)
        research = await repo.find_by_id(research_id)
        if research:
            research.plan_json = new_plan
            research.plan_round = new_round
            research.total_tokens = total_tokens
            await session.flush()

            # Delete old SubAgentResult records
            sa_repo = SubAgentResultRepository(session)
            await sa_repo.delete_by_research(research_id)

            # Create new SubAgentResult records
            sub_agents = [
                {
                    "agent_name": agent_def.get("name", ""),
                    "agent_goal": agent_def.get("goal", ""),
                    "search_direction": agent_def.get("searchDirection", ""),
                }
                for agent_def in new_plan
            ]
            await sa_repo.bulk_create(research_id, sub_agents)

            # Save feedback snapshot
            feedback_repo = ResearchPlanFeedbackRepository(session)
            await feedback_repo.create(
                research_id=research_id,
                round=new_round,
                feedback=feedback,
                plan_snapshot={"plan": new_plan},
            )

            await session.commit()

    return {
        "plan": new_plan,
        "plan_round": new_round,
        "total_tokens": total_tokens,
    }


# ---------------------------------------------------------------------------
# Conditional Edge: route_after_review
# ---------------------------------------------------------------------------

def route_after_review(state: ResearchState) -> str:
    """Route to revision or dispatch based on user action.

    Returns:
        "plan_revision" if action is "revise"
        "dispatch" if action is "confirm" (or default)
    """
    action = state.get("_action", "confirm")
    if action == "revise":
        return "plan_revision"
    return "dispatch"


# ---------------------------------------------------------------------------
# Dispatch Node (runs sub-agents)
# ---------------------------------------------------------------------------

async def _run_sub_agents(
    research_id: UUID,
    topic: str,
    plan: list[dict],
    mcp_client: Any = None,
    llm_svc: Any = None,
) -> list[dict]:
    """Run all sub-agents and collect results.

    This function is the integration point with the sub-agent subgraph.
    It can be mocked in tests via patch("src.services.research_graph._run_sub_agents").
    """
    from src.services.sub_agent_graph import build_sub_agent_graph

    results = []
    for agent_def in plan:
        try:
            sub_graph = build_sub_agent_graph(
                mcp_client=mcp_client,
                llm_service=llm_svc,
                checkpointer=None,
            )
            initial_state = {
                "research_id": research_id,
                "topic": topic,
                "agent_def": agent_def,
                "search_direction": agent_def.get("searchDirection", ""),
                "visited_urls": [],
                "findings": "",
                "rounds_completed": 0,
                "sufficient": False,
                "token_used": 0,
                "status": "pending",
                "has_error": False,
                "search_results": [],
            }
            result = await sub_graph.ainvoke(initial_state)
            results.append({
                "name": agent_def.get("name", ""),
                "status": result.get("status", "completed"),
                "findings": result.get("findings", ""),
                "token_used": result.get("token_used", 0),
                "has_error": result.get("has_error", False),
            })
        except Exception as e:
            logger.error("sub_agent_execution_error", agent=agent_def.get("name"), error=str(e))
            results.append({
                "name": agent_def.get("name", ""),
                "status": "failed",
                "findings": "",
                "token_used": 0,
                "has_error": True,
            })
    return results


async def dispatch_node(state: ResearchState, config: RunnableConfig) -> dict:
    """Dispatch sub-agents and collect results.

    Calls _run_sub_agents which executes each sub-agent subgraph.
    Returns state update with accumulated sub_agent_results.
    """
    plan = state["plan"]
    research_id = state["research_id"]
    topic = state["topic"]

    # Push SSE: plan confirmed
    await sse_manager.push_event(
        research_id, "plan_confirm",
        {"status": "confirmed", "researchId": str(research_id)},
    )

    # Run sub-agents
    mcp = _mcp_client_override
    results = await _run_sub_agents(
        research_id, topic, plan,
        mcp_client=mcp,
        llm_svc=_get_llm_service(),
    )

    # Calculate total tokens from sub-agents
    total_sa_tokens = sum(r.get("token_used", 0) for r in results)

    return {
        "sub_agent_results": results,
        "total_tokens": state.get("total_tokens", 0) + total_sa_tokens,
    }


# ---------------------------------------------------------------------------
# Conditional Edge: check_cancel
# ---------------------------------------------------------------------------

def check_cancel(state: ResearchState) -> str:
    """Route to aggregate or partial_aggregate based on cancel_requested."""
    if state.get("cancel_requested", False):
        return "partial_aggregate"
    return "aggregate"


# ---------------------------------------------------------------------------
# Aggregate Node
# ---------------------------------------------------------------------------

async def aggregate_node(state: ResearchState, config: RunnableConfig) -> dict:
    """Aggregate all sub-agent results into final report.

    RULE-RES-008:
    - All failed → status='failed', SSE error
    - Partial success → aggregate available findings
    - All completed → full report
    """
    db_session_factory = config["configurable"]["db_session_factory"]
    research_id = state["research_id"]
    topic = state["topic"]
    plan = state["plan"]

    results = state.get("sub_agent_results", [])
    completed = [r for r in results if r.get("status") != "failed"]
    failed_count = len(results) - len(completed)

    # All failed → no report
    if not completed:
        async with db_session_factory() as session:
            repo = ResearchRepository(session)
            research = await repo.find_by_id(research_id)
            if research:
                research.status = "failed"
                research.error_message = "All sub-agents failed"
                await session.commit()

        await sse_manager.push_event(
            research_id, "error",
            {"message": "All sub-agents failed", "researchId": str(research_id)},
        )
        return {
            "status": "failed",
            "error_message": "All sub-agents failed",
        }

    # Push SSE: aggregation start
    await sse_manager.push_event(
        research_id, "aggregation_start",
        {"researchId": str(research_id), "agentCount": len(completed)},
    )

    # Build findings text from completed sub-agents
    findings_parts = []
    for r in completed:
        name = r.get("name", "Unknown")
        findings = r.get("findings", "")
        if findings:
            findings_parts.append(f"## {name}\n\n{findings}")
    findings_text = "\n\n---\n\n".join(findings_parts)

    # Call LLM to aggregate
    llm = _get_llm_service()
    report, report_tokens = await llm.aggregate_report(topic, plan, findings_text)

    # Truncate to 50000 chars (AC-RES-020)
    if len(report) > 50000:
        report = report[:50000 - 20] + "\n\n...(report truncated)"

    total_tokens = state.get("total_tokens", 0) + report_tokens

    # Update DB
    async with db_session_factory() as session:
        repo = ResearchRepository(session)
        research = await repo.find_by_id(research_id)
        if research:
            research.report_markdown = report
            research.total_tokens = total_tokens
            research.status = "completed"
            await session.commit()

    # Push SSE: report complete
    await sse_manager.push_event(
        research_id, "report_complete",
        {"researchId": str(research_id), "status": "completed"},
    )

    return {
        "report_markdown": report,
        "status": "completed",
        "total_tokens": total_tokens,
    }


# ---------------------------------------------------------------------------
# Partial Aggregate Node (cancel handling)
# ---------------------------------------------------------------------------

async def partial_aggregate_node(state: ResearchState, config: RunnableConfig) -> dict:
    """Handle cancellation: generate partial report or mark as cancelled.

    RULE-RES-009:
    - No completed sub-agents → status='cancelled', no report, SSE error
    - Has completed sub-agents → partial report, status='cancelled'
    """
    db_session_factory = config["configurable"]["db_session_factory"]
    research_id = state["research_id"]
    topic = state["topic"]
    plan = state["plan"]

    results = state.get("sub_agent_results", [])
    completed = [r for r in results if r.get("status") != "failed"]

    if not completed:
        # No completed sub-agents → bare cancel
        async with db_session_factory() as session:
            repo = ResearchRepository(session)
            research = await repo.find_by_id(research_id)
            if research:
                research.status = "cancelled"
                research.error_message = "Cancelled before any sub-agent completed"
                await session.commit()

        await sse_manager.push_event(
            research_id, "error",
            {"message": "Cancelled, no results available", "researchId": str(research_id)},
        )
        return {
            "status": "cancelled",
            "error_message": "Cancelled, no results available",
        }

    # Has partial results → generate partial report
    await sse_manager.push_event(
        research_id, "aggregation_start",
        {"researchId": str(research_id), "agentCount": len(completed), "partial": True},
    )

    findings_parts = []
    for r in completed:
        name = r.get("name", "Unknown")
        findings = r.get("findings", "")
        if findings:
            findings_parts.append(f"## {name}\n\n{findings}")
    findings_text = "\n\n---\n\n".join(findings_parts)

    llm = _get_llm_service()
    report, report_tokens = await llm.aggregate_report(topic, plan, findings_text)

    if len(report) > 50000:
        report = report[:50000 - 20] + "\n\n...(report truncated)"

    total_tokens = state.get("total_tokens", 0) + report_tokens

    async with db_session_factory() as session:
        repo = ResearchRepository(session)
        research = await repo.find_by_id(research_id)
        if research:
            research.report_markdown = report
            research.total_tokens = total_tokens
            research.status = "cancelled"
            await session.commit()

    await sse_manager.push_event(
        research_id, "report_complete",
        {"researchId": str(research_id), "status": "cancelled"},
    )

    return {
        "report_markdown": report,
        "status": "cancelled",
        "total_tokens": total_tokens,
    }


# ---------------------------------------------------------------------------
# Graph Compilation
# ---------------------------------------------------------------------------

def compile_research_graph(
    mcp_client: Any = None,
    llm_service_override: Any = None,
    db_session_factory: Any = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> Any:
    """Compile the main research graph.

    Graph flow:
    START → plan_generation → [check_cancel_early]
        → (cancel) partial_aggregate → END
        → (no cancel) human_review (interrupt) → [route_after_review]
            → (revise) plan_revision → human_review (loop)
            → (confirm) [check_cancel] → aggregate → END
            → (confirm+cancel) partial_aggregate → END

    Args:
        mcp_client: Optional MCP client for sub-agent graph
        llm_service_override: Optional LLM service override (for testing)
        db_session_factory: DB session factory
        checkpointer: Optional checkpointer for persistence

    Returns:
        Compiled LangGraph StateGraph
    """
    global _llm_service_override, _mcp_client_override
    if llm_service_override is not None:
        _llm_service_override = llm_service_override
    if mcp_client is not None:
        _mcp_client_override = mcp_client

    builder = StateGraph(ResearchState)

    # Add nodes
    builder.add_node("plan_generation", plan_generation_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("plan_revision", plan_revision_node)
    builder.add_node("dispatch", dispatch_node)
    builder.add_node("aggregate", aggregate_node)
    builder.add_node("partial_aggregate", partial_aggregate_node)

    # Entry point
    builder.set_entry_point("plan_generation")

    # Early cancel check: skip human_review if already cancelled
    builder.add_conditional_edges(
        "plan_generation",
        check_cancel,
        {"aggregate": "human_review", "partial_aggregate": "partial_aggregate"},
    )

    # Plan review routing
    builder.add_conditional_edges(
        "human_review",
        route_after_review,
        {"plan_revision": "plan_revision", "dispatch": "dispatch"},
    )
    builder.add_edge("plan_revision", "human_review")  # Loop back to review

    # Post-dispatch cancel check
    builder.add_conditional_edges(
        "dispatch",
        check_cancel,
        {"aggregate": "aggregate", "partial_aggregate": "partial_aggregate"},
    )

    # Terminal edges
    builder.add_edge("aggregate", END)
    builder.add_edge("partial_aggregate", END)

    # Compile with optional checkpointer
    if checkpointer:
        return builder.compile(checkpointer=checkpointer)
    return builder.compile()


# ---------------------------------------------------------------------------
# Graph Singleton (lazy init with PostgresSaver)
# ---------------------------------------------------------------------------

_compiled_graph = None


async def get_research_graph() -> Any:
    """Return singleton compiled graph, creating on first call.

    Uses PostgresSaver from checkpointer.py for production.
    For testing, use compile_research_graph(checkpointer=MemorySaver()) directly.
    """
    global _compiled_graph
    if _compiled_graph is None:
        from src.services.checkpointer import get_checkpointer
        checkpointer = await get_checkpointer()
        _compiled_graph = compile_research_graph(checkpointer=checkpointer)
    return _compiled_graph
