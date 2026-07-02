"""Execution engine — thin wrapper around LangGraph research graph.

All business logic (plan generation, sub-agent execution, aggregation,
cancellation) is handled inside the graph nodes (research_graph.py).
This module only provides the external API that the router calls.
"""

import asyncio
import uuid

import structlog

from src.repos.research_repo import ResearchRepository
from src.services.research_graph import get_research_graph

logger = structlog.get_logger()

# asyncio.Event per research_id for real-time cancel signalling.
# Sub-agent subgraph checks these each round (sub_agent_graph.py).
cancel_signals: dict[uuid.UUID, asyncio.Event] = {}


async def cancel_execution(research_id: uuid.UUID) -> None:
    """Signal the execution engine to cancel.

    Two-layer hybrid cancel (RULE-RES-009):
    1. asyncio.Event — real-time signal (sub-agent checks each round)
    2. graph.aupdate_state — persistent signal (crash-recovery safe)
    """
    if research_id not in cancel_signals:
        cancel_signals[research_id] = asyncio.Event()
    cancel_signals[research_id].set()

    # Persistent cancel via graph state
    try:
        graph = await get_research_graph()
        config = {"configurable": {"thread_id": str(research_id)}}
        await graph.aupdate_state(config, {"cancel_requested": True})
    except Exception:
        pass  # graph may not be running; ignore


async def check_cancelled(research_id: uuid.UUID) -> bool:
    """Check if execution has been cancelled."""
    return cancel_signals.get(research_id, asyncio.Event()).is_set()


async def run_research(db_session_factory, research_id: uuid.UUID) -> None:
    """Background task: resume graph with confirm action.

    Called by confirm_plan via asyncio.create_task().
    Uses Command(resume={"action":"confirm"}) to resume from interrupt().
    """
    cancel_signals[research_id] = asyncio.Event()

    graph = await get_research_graph()
    config = {
        "configurable": {
            "thread_id": str(research_id),
            "db_session_factory": db_session_factory,
        }
    }

    try:
        from langgraph.types import Command
        await graph.ainvoke(Command(resume={"action": "confirm"}), config)
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
        await asyncio.get_event_loop().call_exception_handler({
            "message": f"exec_engine_error: {e}",
        }) if False else None  # suppress double-log
    finally:
        cancel_signals.pop(research_id, None)


async def start_research_graph(
    db_session_factory, topic: str, template: str, user_id: uuid.UUID
) -> dict:
    """Start new research graph (called by POST /new).

    Runs graph until interrupt() → returns plan.
    Pre-generates research_id so plan_generation_node can use it for DB record.
    """
    graph = await get_research_graph()
    research_id = uuid.uuid4()
    config = {
        "configurable": {
            "thread_id": str(research_id),
            "db_session_factory": db_session_factory,
        }
    }

    result = await graph.ainvoke(
        {
            "topic": topic,
            "template": template,
            "user_id": user_id,
            "research_id": research_id,
        },
        config,
    )
    # Graph pauses at human_review interrupt → return plan + research_id
    return {
        "research_id": research_id,
        "plan": result["plan"],
        "plan_round": result["plan_round"],
    }


async def resume_research_graph(
    db_session_factory, research_id: uuid.UUID, action: str, feedback: str | None = None
) -> dict:
    """Resume graph with user action (called by POST /revise only).

    action='revise' → plan_revision → back to interrupt → return new plan.
    action='confirm' is NOT used here — confirm uses run_research() as background task.
    """
    graph = await get_research_graph()
    config = {
        "configurable": {
            "thread_id": str(research_id),
            "db_session_factory": db_session_factory,
        }
    }

    resume_value: dict = {"action": action}
    if feedback:
        resume_value["feedback"] = feedback

    from langgraph.types import Command
    result = await graph.ainvoke(Command(resume=resume_value), config)

    # Graph is back at interrupt → return new plan
    return {"plan": result["plan"], "plan_round": result["plan_round"]}


async def recover_research(db_session_factory, research_id: uuid.UUID) -> None:
    """Recover a crashed research from checkpoint.

    Called on app startup for status='running' researches.
    Uses ainvoke(None) to continue from last checkpoint (NOT interrupt resume).
    """
    graph = await get_research_graph()
    config = {
        "configurable": {
            "thread_id": str(research_id),
            "db_session_factory": db_session_factory,
        }
    }
    await graph.ainvoke(None, config)
