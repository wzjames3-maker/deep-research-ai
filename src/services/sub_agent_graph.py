"""Sub-agent Subgraph implementation (LangGraph StateGraph).

This module implements the sub-agent search loop:
START → init → search → dedup → analyze → (conditional) → complete → END

The conditional edge routes back to 'search' if:
- sufficient=false AND rounds_completed < 4
Otherwise routes to 'complete'.
"""

import asyncio
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from src.config import settings
from src.services.graph_state import SubAgentState
from src.services.mcp_client import MCPSearchClient, SearchResult, _normalize_url
from src.services import llm_service
from src.services.sse_manager import sse_manager
import structlog

logger = structlog.get_logger()

# Module-level cancel signals per research_id
cancel_signals: dict[str, asyncio.Event] = {}

# Module-level MCP client (initialized lazily)
_mcp_client: MCPSearchClient | None = None

# Module-level LLM service override (for testing)
_llm_service_override: Any = None


def get_mcp_client() -> MCPSearchClient:
    """Get or create the MCP client singleton."""
    global _mcp_client
    if _mcp_client is not None:
        return _mcp_client
    _mcp_client = MCPSearchClient(settings.BRAVE_MCP_URL)
    return _mcp_client


def get_cancel_event(research_id: str) -> asyncio.Event:
    """Get or create cancel event for a research_id."""
    if research_id not in cancel_signals:
        cancel_signals[research_id] = asyncio.Event()
    return cancel_signals[research_id]


def set_cancel(research_id: str) -> None:
    """Signal cancellation for a research."""
    event = get_cancel_event(research_id)
    event.set()


def clear_cancel(research_id: str) -> None:
    """Clear cancel signal for a research."""
    if research_id in cancel_signals:
        del cancel_signals[research_id]


# ---------------------------------------------------------------------------
# Node implementations
# ---------------------------------------------------------------------------

async def init_node(state: SubAgentState, config: RunnableConfig) -> dict:
    """Initialize sub-agent: mark running, push SSE start event."""
    research_id = str(state["research_id"])
    agent_def = state["agent_def"]

    # Initialize cancel event for this research
    get_cancel_event(research_id)

    # Push SSE start event
    await sse_manager.push_event(
        state["research_id"],
        "sub_agent_start",
        {
            "subAgentId": research_id,
            "name": agent_def.get("name", "Unknown"),
            "goal": agent_def.get("goal", ""),
            "status": "running",
        },
    )

    return {
        "status": "running",
        "visited_urls": [],
        "findings": "",
        "rounds_completed": 0,
        "token_used": 0,
        "has_error": False,
        "sufficient": False,
    }


async def search_node(state: SubAgentState, config: RunnableConfig) -> dict:
    """Call MCP search with current search_direction."""
    research_id = str(state["research_id"])

    # Check cancel signal before searching
    cancel_event = get_cancel_event(research_id)
    if cancel_event.is_set():
        logger.info("sub_agent_cancelled_before_search", research_id=research_id)
        return {"status": "cancelled"}

    mcp_client = get_mcp_client()
    search_direction = state["search_direction"]

    try:
        results = await mcp_client.search(search_direction)
        return {"search_results": results, "status": "running"}
    except Exception as e:
        logger.error("sub_agent_search_failed", research_id=research_id, error=str(e))
        return {"status": "failed", "has_error": True, "search_results": []}


async def dedup_node(state: SubAgentState, config: RunnableConfig) -> dict:
    """URL dedup: normalize + filter against visited_urls."""
    search_results: list[SearchResult] = state.get("search_results", [])
    visited_urls: list[str] = list(state.get("visited_urls", []))
    visited_set = {_normalize_url(u) for u in visited_urls}

    new_results: list[SearchResult] = []
    for result in search_results:
        normalized = _normalize_url(result.url)
        if normalized not in visited_set:
            visited_set.add(normalized)
            visited_urls.append(result.url)
            new_results.append(result)

    return {
        "search_results": new_results,
        "visited_urls": visited_urls,
    }


async def analyze_node(state: SubAgentState, config: RunnableConfig) -> dict:
    """LLM analysis: assess sufficiency, extract findings."""
    research_id = str(state["research_id"])

    # Check cancel signal
    cancel_event = get_cancel_event(research_id)
    if cancel_event.is_set():
        return {"status": "cancelled"}

    # If already failed (from search_node), skip analysis
    if state.get("has_error"):
        return {"status": "failed"}

    search_results: list[SearchResult] = state.get("search_results", [])
    results_text = "\n\n".join(
        f"[{r.title}]({r.url})\n{r.snippet}" for r in search_results
    )

    try:
        # Use override if set (for testing), otherwise use real llm_service
        # Note: real llm_service.sub_agent_search returns (dict, int) tuple;
        # mock returns just a dict. Handle both formats.
        if _llm_service_override is not None:
            result = await _llm_service_override.sub_agent_search(
                findings=state.get("findings", ""),
                search_results=results_text,
                direction=state["search_direction"],
                topic=state["topic"],
            )
            if isinstance(result, tuple):
                analysis, tokens = result
            else:
                analysis = result
                tokens = analysis.get("token_used", 0)
        else:
            analysis, tokens = await llm_service.sub_agent_search(
                findings=state.get("findings", ""),
                search_results=results_text,
                direction=state["search_direction"],
                topic=state["topic"],
            )

        rounds_completed = state.get("rounds_completed", 0) + 1
        new_findings = analysis.get("findings", state.get("findings", ""))
        sufficient = analysis.get("sufficient", False)
        new_query = analysis.get("new_search_query")

        # Push SSE round event
        await sse_manager.push_event(
            state["research_id"],
            "sub_agent_round",
            {
                "subAgentId": research_id,
                "round": rounds_completed,
                "searchQuery": state["search_direction"],
            },
        )

        update: dict[str, Any] = {
            "findings": new_findings,
            "sufficient": sufficient,
            "rounds_completed": rounds_completed,
            "token_used": state.get("token_used", 0) + tokens,
        }

        # Update search direction if LLM provided new query
        if new_query and not sufficient:
            update["search_direction"] = new_query

        return update

    except Exception as e:
        logger.error("sub_agent_analyze_failed", research_id=research_id, error=str(e))
        return {"status": "failed", "has_error": True}


def route_after_analyze(state: SubAgentState) -> str:
    """Conditional edge: route to complete or back to search."""
    # If cancelled or failed, go to complete
    if state.get("status") in ("cancelled", "failed"):
        return "complete"

    # If sufficient or reached max rounds (4), go to complete
    if state.get("sufficient", False):
        return "complete"
    if state.get("rounds_completed", 0) >= 4:
        return "complete"

    # Otherwise, loop back to search
    return "search"


async def complete_node(state: SubAgentState, config: RunnableConfig) -> dict:
    """Update DB with final results, push SSE complete/fail event."""
    research_id = str(state["research_id"])
    agent_def = state["agent_def"]

    # Determine final status
    if state.get("status") == "cancelled":
        final_status = "cancelled"
    elif state.get("has_error"):
        final_status = "failed"
    else:
        final_status = "completed"

    # Push SSE complete/fail event
    event_type = "sub_agent_complete" if final_status == "completed" else "sub_agent_fail"
    event_data = {
        "subAgentId": research_id,
        "name": agent_def.get("name", "Unknown"),
        "status": final_status,
        "roundsUsed": state.get("rounds_completed", 0),
        "preview": state.get("findings", "")[:200],
        "tokenUsed": state.get("token_used", 0),
    }
    if final_status == "failed":
        event_data["error"] = "Search or analysis failed"

    await sse_manager.push_event(state["research_id"], event_type, event_data)

    # Clean up cancel signal
    clear_cancel(research_id)

    return {"status": final_status}


# ---------------------------------------------------------------------------
# Graph compilation
# ---------------------------------------------------------------------------

def build_sub_agent_graph(
    mcp_client: MCPSearchClient | None = None,
    llm_service: Any | None = None,
    checkpointer: Any = None,
    cancel_event: asyncio.Event | None = None,
) -> Any:
    """Build and compile the sub-agent subgraph.

    Args:
        mcp_client: Optional MCP client override (for testing)
        llm_service: Optional LLM service override (for testing)
        checkpointer: Optional checkpointer for persistence
        cancel_event: Optional cancel event (for testing)

    Returns:
        Compiled LangGraph StateGraph
    """
    global _mcp_client, _llm_service_override
    if mcp_client is not None:
        _mcp_client = mcp_client
    if llm_service is not None:
        _llm_service_override = llm_service

    builder = StateGraph(SubAgentState)

    # Add nodes
    builder.add_node("init", init_node)
    builder.add_node("search", search_node)
    builder.add_node("dedup", dedup_node)
    builder.add_node("analyze", analyze_node)
    builder.add_node("complete", complete_node)

    # Set entry point
    builder.set_entry_point("init")

    # Add edges
    builder.add_edge("init", "search")
    builder.add_edge("search", "dedup")
    builder.add_edge("dedup", "analyze")
    builder.add_conditional_edges(
        "analyze",
        route_after_analyze,
        {"search": "search", "complete": "complete"},
    )
    builder.add_edge("complete", END)

    # Compile with optional checkpointer
    if checkpointer:
        return builder.compile(checkpointer=checkpointer)
    return builder.compile()


def compile_sub_agent_graph(checkpointer: Any = None) -> Any:
    """Compile the sub-agent subgraph with default settings."""
    return build_sub_agent_graph(checkpointer=checkpointer)
