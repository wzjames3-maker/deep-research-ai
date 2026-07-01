"""TDD RED tests for Main Research Graph (Task 37).

These tests verify the expected behavior of the main research graph:
- plan generation → interrupt → resume flow
- Send API parallel dispatch
- cancel routing (check_cancel → aggregate/partial_aggregate)
- checkpoint recovery
- state reducer accumulation

All tests should FAIL (RED) because research_graph is not yet implemented.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from src.services.graph_state import ResearchState


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_mcp_client():
    """Mock MCP search client."""
    client = MagicMock()
    client.search = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_llm_service():
    """Mock LLM service."""
    service = MagicMock()
    service.generate_plan = AsyncMock(return_value=(
        [
            {"name": "Agent1", "goal": "Goal 1", "searchDirection": "query 1"},
            {"name": "Agent2", "goal": "Goal 2", "searchDirection": "query 2"},
            {"name": "Agent3", "goal": "Goal 3", "searchDirection": "query 3"},
        ],
        100,  # tokens
    ))
    service.revise_plan = AsyncMock(return_value=(
        [
            {"name": "Agent1", "goal": "Goal 1 revised", "searchDirection": "query 1 revised"},
            {"name": "Agent2", "goal": "Goal 2", "searchDirection": "query 2"},
            {"name": "Agent3", "goal": "Goal 3", "searchDirection": "query 3"},
            {"name": "Agent4", "goal": "Goal 4", "searchDirection": "query 4"},
        ],
        150,  # tokens
    ))
    service.aggregate_report = AsyncMock(return_value=(
        "# Test Report\n\nAggregated findings.",
        500,  # tokens
    ))
    service.sub_agent_search = AsyncMock(return_value={
        "sufficient": True,
        "findings": "Test findings",
        "new_search_query": None,
        "token_used": 100,
    })
    return service


@pytest.fixture
def mock_db_session_factory():
    """Mock DB session factory that returns an async context manager."""
    from unittest.mock import AsyncMock, MagicMock
    from src.models.research import Research
    from uuid import uuid4
    
    factory = MagicMock()
    session = AsyncMock()
    
    # Track added objects to set their IDs
    added_objects = []
    
    def mock_add(obj):
        added_objects.append(obj)
    session.add = mock_add
    
    # Mock the execute method to return None for find_by_id queries
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalar_one.return_value = 0
    session.execute = AsyncMock(return_value=mock_result)
    
    # Mock flush to set IDs on added objects
    async def mock_flush():
        for obj in added_objects:
            if hasattr(obj, 'id') and obj.id is None:
                obj.id = uuid4()
    session.flush = mock_flush
    
    # Mock commit
    session.commit = AsyncMock()
    
    # Make it work as async context manager
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    factory.return_value = cm
    
    return factory


@pytest.fixture
def checkpointer():
    """In-memory checkpointer for unit tests."""
    return MemorySaver()


def _make_initial_state(**overrides) -> dict:
    """Create initial ResearchState with sensible defaults."""
    state = {
        "research_id": uuid4(),
        "user_id": uuid4(),
        "topic": "Test Research Topic",
        "template": "tech_research",
        "plan": [],
        "plan_round": 0,
        "feedback": None,
        "_action": None,
        "sub_agent_results": [],
        "cancel_requested": False,
        "report_markdown": "",
        "total_tokens": 0,
        "status": "pending",
        "error_message": None,
    }
    state.update(overrides)
    return state


# ---------------------------------------------------------------------------
# Test 1: plan generation to interrupt
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_plan_generation_to_interrupt(
    mock_mcp_client, mock_llm_service, mock_db_session_factory, checkpointer
):
    """Graph should run to human_review interrupt and return plan."""
    from src.services.research_graph import compile_research_graph

    graph = compile_research_graph(
        mcp_client=mock_mcp_client,
        llm_service_override=mock_llm_service,
        db_session_factory=mock_db_session_factory,
        checkpointer=checkpointer,
    )

    initial_state = _make_initial_state()
    thread_id = f"test-main-{uuid4()}"
    config = {"configurable": {"thread_id": thread_id, "db_session_factory": mock_db_session_factory}}

    result = await graph.ainvoke(initial_state, config)

    # Should have plan with 3-5 sub-agents
    assert len(result["plan"]) >= 3
    assert result["status"] == "draft"
    assert result["plan_round"] == 1


# ---------------------------------------------------------------------------
# Test 2: resume with confirm
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_resume_with_confirm(
    mock_mcp_client, mock_llm_service, mock_db_session_factory, checkpointer
):
    """Resume with confirm should dispatch sub-agents and aggregate."""
    from src.services.research_graph import compile_research_graph

    graph = compile_research_graph(
        mcp_client=mock_mcp_client,
        llm_service_override=mock_llm_service,
        db_session_factory=mock_db_session_factory,
        checkpointer=checkpointer,
    )

    thread_id = f"test-main-{uuid4()}"
    config = {"configurable": {"thread_id": thread_id, "db_session_factory": mock_db_session_factory}}

    # First invoke to interrupt
    initial_state = _make_initial_state()
    await graph.ainvoke(initial_state, config)

    # Resume with confirm
    result = await graph.ainvoke(
        Command(resume={"action": "confirm"}),
        config,
    )

    assert result["status"] == "completed"
    assert result["report_markdown"] != ""


# ---------------------------------------------------------------------------
# Test 3: resume with revise
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_resume_with_revise(
    mock_mcp_client, mock_llm_service, mock_db_session_factory, checkpointer
):
    """Resume with revise should revise plan and return to interrupt."""
    from src.services.research_graph import compile_research_graph

    graph = compile_research_graph(
        mcp_client=mock_mcp_client,
        llm_service_override=mock_llm_service,
        db_session_factory=mock_db_session_factory,
        checkpointer=checkpointer,
    )

    thread_id = f"test-main-{uuid4()}"
    config = {"configurable": {"thread_id": thread_id, "db_session_factory": mock_db_session_factory}}

    # First invoke to interrupt
    initial_state = _make_initial_state()
    await graph.ainvoke(initial_state, config)

    # Resume with revise
    result = await graph.ainvoke(
        Command(resume={"action": "revise", "feedback": "Add competitor comparison"}),
        config,
    )

    # Should have revised plan and be back at interrupt
    assert result["plan_round"] == 2
    assert len(result["plan"]) == 4  # Revised plan has 4 agents


# ---------------------------------------------------------------------------
# Test 4: revise then confirm (full flow)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_resume_revise_then_confirm(
    mock_mcp_client, mock_llm_service, mock_db_session_factory, checkpointer
):
    """Full flow: plan → interrupt → revise → interrupt → confirm → execute."""
    from src.services.research_graph import compile_research_graph

    graph = compile_research_graph(
        mcp_client=mock_mcp_client,
        llm_service_override=mock_llm_service,
        db_session_factory=mock_db_session_factory,
        checkpointer=checkpointer,
    )

    thread_id = f"test-main-{uuid4()}"
    config = {"configurable": {"thread_id": thread_id, "db_session_factory": mock_db_session_factory}}

    # Step 1: Initial plan generation → interrupt
    initial_state = _make_initial_state()
    result1 = await graph.ainvoke(initial_state, config)
    assert result1["plan_round"] == 1

    # Step 2: Revise → back to interrupt
    result2 = await graph.ainvoke(
        Command(resume={"action": "revise", "feedback": "More detail needed"}),
        config,
    )
    assert result2["plan_round"] == 2

    # Step 3: Confirm → execute
    result3 = await graph.ainvoke(
        Command(resume={"action": "confirm"}),
        config,
    )
    assert result3["status"] == "completed"


# ---------------------------------------------------------------------------
# Test 5: Send API parallel dispatch
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_send_api_parallel(
    mock_mcp_client, mock_llm_service, mock_db_session_factory, checkpointer
):
    """Confirm should dispatch 3 sub-agents in parallel via Send API."""
    from src.services.research_graph import compile_research_graph

    graph = compile_research_graph(
        mcp_client=mock_mcp_client,
        llm_service_override=mock_llm_service,
        db_session_factory=mock_db_session_factory,
        checkpointer=checkpointer,
    )

    thread_id = f"test-main-{uuid4()}"
    config = {"configurable": {"thread_id": thread_id, "db_session_factory": mock_db_session_factory}}

    initial_state = _make_initial_state()
    await graph.ainvoke(initial_state, config)

    result = await graph.ainvoke(
        Command(resume={"action": "confirm"}),
        config,
    )

    # sub_agent_results should have 3 entries (one per sub-agent)
    assert len(result["sub_agent_results"]) == 3


# ---------------------------------------------------------------------------
# Test 6: cancel routes to partial_aggregate
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_check_cancel_routes_to_partial_aggregate(
    mock_mcp_client, mock_llm_service, mock_db_session_factory, checkpointer
):
    """cancel_requested=True should route to partial_aggregate."""
    from src.services.research_graph import compile_research_graph

    mock_llm_service.aggregate_report = AsyncMock(return_value=(
        "# Partial Report\n\nBased on partial results.",
        200,
    ))

    graph = compile_research_graph(
        mcp_client=mock_mcp_client,
        llm_service_override=mock_llm_service,
        db_session_factory=mock_db_session_factory,
        checkpointer=checkpointer,
    )

    thread_id = f"test-main-{uuid4()}"
    config = {"configurable": {"thread_id": thread_id, "db_session_factory": mock_db_session_factory}}

    initial_state = _make_initial_state(cancel_requested=True)
    result = await graph.ainvoke(initial_state, config)

    # Should have partial report
    assert result["status"] == "cancelled"


# ---------------------------------------------------------------------------
# Test 7: normal routing to aggregate
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_check_cancel_normal_routes_to_aggregate(
    mock_mcp_client, mock_llm_service, mock_db_session_factory, checkpointer
):
    """cancel_requested=False should route to aggregate."""
    from src.services.research_graph import compile_research_graph

    graph = compile_research_graph(
        mcp_client=mock_mcp_client,
        llm_service_override=mock_llm_service,
        db_session_factory=mock_db_session_factory,
        checkpointer=checkpointer,
    )

    thread_id = f"test-main-{uuid4()}"
    config = {"configurable": {"thread_id": thread_id, "db_session_factory": mock_db_session_factory}}

    initial_state = _make_initial_state(cancel_requested=False)
    await graph.ainvoke(initial_state, config)

    result = await graph.ainvoke(
        Command(resume={"action": "confirm"}),
        config,
    )

    assert result["status"] == "completed"
    mock_llm_service.aggregate_report.assert_called_once()


# ---------------------------------------------------------------------------
# Test 8: all sub-agents failed
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_all_sub_agents_failed(
    mock_mcp_client, mock_llm_service, mock_db_session_factory, checkpointer
):
    """All sub-agents failed should result in status='failed'."""
    from src.services.research_graph import compile_research_graph

    # Mock sub-agent graph to return failed results
    mock_sub_agent_results = [
        {"name": f"Agent{i}", "status": "failed", "findings": "", "token_used": 0, "has_error": True}
        for i in range(3)
    ]

    graph = compile_research_graph(
        mcp_client=mock_mcp_client,
        llm_service_override=mock_llm_service,
        db_session_factory=mock_db_session_factory,
        checkpointer=checkpointer,
    )

    thread_id = f"test-main-{uuid4()}"
    config = {"configurable": {"thread_id": thread_id, "db_session_factory": mock_db_session_factory}}

    initial_state = _make_initial_state()
    await graph.ainvoke(initial_state, config)

    with patch("src.services.research_graph._run_sub_agents", return_value=mock_sub_agent_results):
        result = await graph.ainvoke(
            Command(resume={"action": "confirm"}),
            config,
        )

    assert result["status"] == "failed"
    assert result["error_message"] is not None


# ---------------------------------------------------------------------------
# Test 9: partial failure aggregate
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_partial_failure_aggregate(
    mock_mcp_client, mock_llm_service, mock_db_session_factory, checkpointer
):
    """2 completed + 1 failed should still aggregate successfully."""
    from src.services.research_graph import compile_research_graph

    mock_sub_agent_results = [
        {"name": "Agent1", "status": "completed", "findings": "Findings 1", "token_used": 100, "has_error": False},
        {"name": "Agent2", "status": "completed", "findings": "Findings 2", "token_used": 120, "has_error": False},
        {"name": "Agent3", "status": "failed", "findings": "", "token_used": 0, "has_error": True},
    ]

    graph = compile_research_graph(
        mcp_client=mock_mcp_client,
        llm_service_override=mock_llm_service,
        db_session_factory=mock_db_session_factory,
        checkpointer=checkpointer,
    )

    thread_id = f"test-main-{uuid4()}"
    config = {"configurable": {"thread_id": thread_id, "db_session_factory": mock_db_session_factory}}

    initial_state = _make_initial_state()
    await graph.ainvoke(initial_state, config)

    with patch("src.services.research_graph._run_sub_agents", return_value=mock_sub_agent_results):
        result = await graph.ainvoke(
            Command(resume={"action": "confirm"}),
            config,
        )

    assert result["status"] == "completed"
    assert result["report_markdown"] != ""


# ---------------------------------------------------------------------------
# Test 10: checkpoint recovery
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_checkpoint_recovery(
    mock_mcp_client, mock_llm_service, mock_db_session_factory, checkpointer
):
    """Graph should recover from checkpoint after interruption."""
    from src.services.research_graph import compile_research_graph

    graph = compile_research_graph(
        mcp_client=mock_mcp_client,
        llm_service_override=mock_llm_service,
        db_session_factory=mock_db_session_factory,
        checkpointer=checkpointer,
    )

    thread_id = f"test-main-{uuid4()}"
    config = {"configurable": {"thread_id": thread_id, "db_session_factory": mock_db_session_factory}}

    # Run to interrupt
    initial_state = _make_initial_state()
    result1 = await graph.ainvoke(initial_state, config)
    assert result1["plan_round"] == 1

    # Simulate "crash" by creating a new graph instance with same checkpointer
    graph2 = compile_research_graph(
        mcp_client=mock_mcp_client,
        llm_service_override=mock_llm_service,
        db_session_factory=mock_db_session_factory,
        checkpointer=checkpointer,
    )

    # Recover from checkpoint
    result2 = await graph2.ainvoke(None, config)

    # Should be at the same interrupt point
    assert result2["plan_round"] == 1


# ---------------------------------------------------------------------------
# Test 11: state reducer accumulates
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_state_reducer_accumulates(
    mock_mcp_client, mock_llm_service, mock_db_session_factory, checkpointer
):
    """Send API results should accumulate via operator.add reducer."""
    from src.services.research_graph import compile_research_graph

    graph = compile_research_graph(
        mcp_client=mock_mcp_client,
        llm_service_override=mock_llm_service,
        db_session_factory=mock_db_session_factory,
        checkpointer=checkpointer,
    )

    thread_id = f"test-main-{uuid4()}"
    config = {"configurable": {"thread_id": thread_id, "db_session_factory": mock_db_session_factory}}

    initial_state = _make_initial_state()
    await graph.ainvoke(initial_state, config)

    result = await graph.ainvoke(
        Command(resume={"action": "confirm"}),
        config,
    )

    # Reducer should accumulate, not overwrite
    assert len(result["sub_agent_results"]) == 3
    # Each result should be a separate dict
    for r in result["sub_agent_results"]:
        assert isinstance(r, dict)
        assert "name" in r


# ---------------------------------------------------------------------------
# Test 12: cancel_requested persisted in checkpoint
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cancel_requested_persisted_in_checkpoint(
    mock_mcp_client, mock_llm_service, mock_db_session_factory, checkpointer
):
    """cancel_requested should persist across checkpoint recovery."""
    from src.services.research_graph import compile_research_graph

    graph = compile_research_graph(
        mcp_client=mock_mcp_client,
        llm_service_override=mock_llm_service,
        db_session_factory=mock_db_session_factory,
        checkpointer=checkpointer,
    )

    thread_id = f"test-main-{uuid4()}"
    config = {"configurable": {"thread_id": thread_id, "db_session_factory": mock_db_session_factory}}

    # Run to interrupt
    initial_state = _make_initial_state()
    await graph.ainvoke(initial_state, config)

    # Update state with cancel_requested
    await graph.aupdate_state(config, {"cancel_requested": True})

    # Create new graph instance (simulating crash recovery)
    graph2 = compile_research_graph(
        mcp_client=mock_mcp_client,
        llm_service_override=mock_llm_service,
        db_session_factory=mock_db_session_factory,
        checkpointer=checkpointer,
    )

    # Get state from checkpoint
    state = await graph2.aget_state(config)

    # cancel_requested should be True
    assert state.values["cancel_requested"] is True
