"""TDD RED tests for Sub-agent Subgraph (Task 36).

These tests verify the expected behavior of the sub-agent subgraph:
- search → dedup → analyze flow
- sufficient=true ends the loop
- sufficient=false loops back to search
- rounds limit (4 rounds hard limit)
- URL deduplication across rounds
- MCP search failure handling
- timeout handling
- cancel signal handling

All tests should FAIL (RED) because sub_agent_graph is not yet implemented.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import MemorySaver

from src.services.graph_state import SubAgentState
from src.services.mcp_client import SearchResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_mcp_client():
    """Mock MCP search client."""
    client = MagicMock()
    client.search = AsyncMock()
    return client


@pytest.fixture
def mock_llm_service():
    """Mock LLM service."""
    service = MagicMock()
    service.sub_agent_search = AsyncMock()
    return service


@pytest.fixture
def checkpointer():
    """In-memory checkpointer for unit tests."""
    return MemorySaver()


def _make_initial_state(**overrides) -> SubAgentState:
    """Create initial SubAgentState with sensible defaults."""
    state: SubAgentState = {
        "research_id": uuid4(),
        "topic": "Test Research Topic",
        "agent_def": {"name": "Agent1", "goal": "Test goal", "searchDirection": "test query"},
        "search_direction": "test query",
        "visited_urls": [],
        "findings": "",
        "rounds_completed": 0,
        "sufficient": False,
        "token_used": 0,
        "status": "pending",
        "has_error": False,
        "search_results": [],
    }
    state.update(overrides)
    return state


def _make_search_results(urls: list[str]) -> list[SearchResult]:
    """Create mock search results."""
    return [
        SearchResult(url=url, title=f"Title for {url}", snippet=f"Snippet for {url}")
        for url in urls
    ]


# ---------------------------------------------------------------------------
# Test 1: search → dedup → analyze normal flow
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_search_to_analyze_flow(mock_mcp_client, mock_llm_service, checkpointer):
    """Verify search → dedup → analyze flow executes correctly."""
    # This test will FAIL because build_sub_agent_graph is not implemented
    from src.services.sub_agent_graph import build_sub_agent_graph

    mock_mcp_client.search.return_value = _make_search_results(["https://example.com/a"])
    mock_llm_service.sub_agent_search.return_value = {
        "sufficient": True,
        "findings": "Test findings about the topic",
        "new_search_query": None,
        "token_used": 100,
    }

    graph = build_sub_agent_graph(
        mcp_client=mock_mcp_client,
        llm_service=mock_llm_service,
        checkpointer=checkpointer,
    )

    initial_state = _make_initial_state()
    config = {"configurable": {"thread_id": f"test-sa-{uuid4()}"}}

    result = await graph.ainvoke(initial_state, config)

    assert result["status"] == "completed"
    assert result["findings"] != ""
    assert result["rounds_completed"] >= 1


# ---------------------------------------------------------------------------
# Test 2: sufficient=true ends the loop
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_sufficient_true_ends_loop(mock_mcp_client, mock_llm_service, checkpointer):
    """When LLM returns sufficient=true, sub-agent should end after 1 round."""
    from src.services.sub_agent_graph import build_sub_agent_graph

    mock_mcp_client.search.return_value = _make_search_results(["https://example.com/1"])
    mock_llm_service.sub_agent_search.return_value = {
        "sufficient": True,
        "findings": "Sufficient information found",
        "new_search_query": None,
        "token_used": 50,
    }

    graph = build_sub_agent_graph(
        mcp_client=mock_mcp_client,
        llm_service=mock_llm_service,
        checkpointer=checkpointer,
    )

    initial_state = _make_initial_state()
    config = {"configurable": {"thread_id": f"test-sa-{uuid4()}"}}

    result = await graph.ainvoke(initial_state, config)

    assert result["sufficient"] is True
    assert result["rounds_completed"] == 1
    assert result["status"] == "completed"
    # MCP search should only be called once
    assert mock_mcp_client.search.call_count == 1


# ---------------------------------------------------------------------------
# Test 3: sufficient=false loops back to search
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_sufficient_false_loops_back(mock_mcp_client, mock_llm_service, checkpointer):
    """When LLM returns sufficient=false and rounds<4, should loop back to search."""
    from src.services.sub_agent_graph import build_sub_agent_graph

    mock_mcp_client.search.side_effect = [
        _make_search_results(["https://example.com/round1"]),
        _make_search_results(["https://example.com/round2"]),
    ]
    mock_llm_service.sub_agent_search.side_effect = [
        {"sufficient": False, "findings": "Partial info", "new_search_query": "refined query", "token_used": 50},
        {"sufficient": True, "findings": "Complete info", "new_search_query": None, "token_used": 60},
    ]

    graph = build_sub_agent_graph(
        mcp_client=mock_mcp_client,
        llm_service=mock_llm_service,
        checkpointer=checkpointer,
    )

    initial_state = _make_initial_state()
    config = {"configurable": {"thread_id": f"test-sa-{uuid4()}"}}

    result = await graph.ainvoke(initial_state, config)

    assert result["rounds_completed"] == 2
    assert result["sufficient"] is True
    assert mock_mcp_client.search.call_count == 2


# ---------------------------------------------------------------------------
# Test 4: rounds limit (4 rounds hard limit)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_rounds_limit(mock_mcp_client, mock_llm_service, checkpointer):
    """Sub-agent should stop after 4 rounds even if sufficient=false."""
    from src.services.sub_agent_graph import build_sub_agent_graph

    # Always return sufficient=false to force hitting the limit
    mock_mcp_client.search.return_value = _make_search_results(["https://example.com/x"])
    mock_llm_service.sub_agent_search.return_value = {
        "sufficient": False,
        "findings": "Still searching...",
        "new_search_query": "another query",
        "token_used": 30,
    }

    graph = build_sub_agent_graph(
        mcp_client=mock_mcp_client,
        llm_service=mock_llm_service,
        checkpointer=checkpointer,
    )

    initial_state = _make_initial_state()
    config = {"configurable": {"thread_id": f"test-sa-{uuid4()}"}}

    result = await graph.ainvoke(initial_state, config)

    assert result["rounds_completed"] == 4
    assert result["status"] == "completed"  # Forced completion due to limit
    assert mock_mcp_client.search.call_count == 4


# ---------------------------------------------------------------------------
# Test 5: URL deduplication across rounds
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_url_dedup_across_rounds(mock_mcp_client, mock_llm_service, checkpointer):
    """URLs from round 1 should be deduplicated in round 2."""
    from src.services.sub_agent_graph import build_sub_agent_graph

    # Round 1: A, B, C; Round 2: B, D, E (B is duplicate)
    mock_mcp_client.search.side_effect = [
        _make_search_results(["https://a.com", "https://b.com", "https://c.com"]),
        _make_search_results(["https://b.com", "https://d.com", "https://e.com"]),
    ]
    mock_llm_service.sub_agent_search.side_effect = [
        {"sufficient": False, "findings": "Round 1", "new_search_query": "query 2", "token_used": 40},
        {"sufficient": True, "findings": "Round 2", "new_search_query": None, "token_used": 50},
    ]

    graph = build_sub_agent_graph(
        mcp_client=mock_mcp_client,
        llm_service=mock_llm_service,
        checkpointer=checkpointer,
    )

    initial_state = _make_initial_state()
    config = {"configurable": {"thread_id": f"test-sa-{uuid4()}"}}

    result = await graph.ainvoke(initial_state, config)

    # visited_urls should contain deduplicated URLs
    visited = result["visited_urls"]
    # B should only appear once
    b_count = sum(1 for u in visited if "b.com" in u)
    assert b_count == 1
    # A, B, C, D, E should all be present
    assert len(visited) == 5


# ---------------------------------------------------------------------------
# Test 6: MCP search failure marks sub-agent as failed
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_mcp_search_failure_marks_failed(mock_mcp_client, mock_llm_service, checkpointer):
    """MCP search exception should mark sub-agent as failed."""
    from src.services.sub_agent_graph import build_sub_agent_graph

    mock_mcp_client.search.side_effect = Exception("MCP connection lost")

    graph = build_sub_agent_graph(
        mcp_client=mock_mcp_client,
        llm_service=mock_llm_service,
        checkpointer=checkpointer,
    )

    initial_state = _make_initial_state()
    config = {"configurable": {"thread_id": f"test-sa-{uuid4()}"}}

    result = await graph.ainvoke(initial_state, config)

    assert result["status"] == "failed"
    assert result["has_error"] is True


# ---------------------------------------------------------------------------
# Test 7: timeout marks sub-agent as failed
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_timeout_marks_failed(mock_mcp_client, mock_llm_service, checkpointer):
    """asyncio.timeout trigger should mark sub-agent as failed.
    
    Note: Timeout handling is done at the outer execution layer, not in the subgraph.
    This test verifies that if search fails, status is set to 'failed'.
    """
    from src.services.sub_agent_graph import build_sub_agent_graph

    # Simulate search failure (which would happen on timeout in real scenario)
    mock_mcp_client.search.side_effect = asyncio.TimeoutError("Search timed out")

    graph = build_sub_agent_graph(
        mcp_client=mock_mcp_client,
        llm_service=mock_llm_service,
        checkpointer=checkpointer,
    )

    initial_state = _make_initial_state()
    config = {"configurable": {"thread_id": f"test-sa-{uuid4()}"}}

    result = await graph.ainvoke(initial_state, config)

    assert result["status"] == "failed"
    assert result["has_error"] is True


# ---------------------------------------------------------------------------
# Test 8: cancel signal stops the loop
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cancel_signal_stops_loop(mock_mcp_client, mock_llm_service, checkpointer):
    """asyncio.Event cancel signal should stop the sub-agent loop."""
    from src.services.sub_agent_graph import build_sub_agent_graph, set_cancel

    research_id = uuid4()
    
    # Pre-set cancel signal before running
    set_cancel(str(research_id))

    mock_mcp_client.search.return_value = _make_search_results(["https://example.com/1"])
    mock_llm_service.sub_agent_search.return_value = {
        "sufficient": False,
        "findings": "Partial",
        "new_search_query": "next query",
        "token_used": 30,
    }

    graph = build_sub_agent_graph(
        mcp_client=mock_mcp_client,
        llm_service=mock_llm_service,
        checkpointer=checkpointer,
    )

    initial_state = _make_initial_state(research_id=research_id)
    config = {"configurable": {"thread_id": f"test-sa-{uuid4()}"}}

    result = await graph.ainvoke(initial_state, config)

    # Should be cancelled because cancel was set before search
    assert result["status"] == "cancelled"
