"""Crash recovery integration tests (Task 48 / EC-RES-013).

Tests crash recovery using mock LLM + MemorySaver:
- Recovery during plan phase
- Cancel persists across crash
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from src.services.research_graph import compile_research_graph


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_mcp_client():
    client = AsyncMock()
    client.search = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_llm_service():
    service = AsyncMock()
    service.generate_plan = AsyncMock(return_value=(
        [{"name": "A1", "goal": "G1", "searchDirection": "q1"},
         {"name": "A2", "goal": "G2", "searchDirection": "q2"},
         {"name": "A3", "goal": "G3", "searchDirection": "q3"}],
        100,
    ))
    service.revise_plan = AsyncMock(return_value=(
        [{"name": "A1r", "goal": "G1r", "searchDirection": "q1r"},
         {"name": "A2r", "goal": "G2r", "searchDirection": "q2r"},
         {"name": "A3r", "goal": "G3r", "searchDirection": "q3r"}], 200,
    ))
    service.aggregate_report = AsyncMock(return_value=("# Recovered Report", 500))
    service.sub_agent_search = AsyncMock(return_value={
        "sufficient": True, "findings": "Test findings",
        "new_search_query": None, "token_used": 100,
    })
    return service


@pytest.fixture
def mock_db_session_factory():
    from unittest.mock import MagicMock
    factory = MagicMock()
    session = AsyncMock()
    added = []

    def mock_add(obj):
        added.append(obj)
    session.add = mock_add

    from unittest.mock import MagicMock
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalar_one.return_value = 0
    session.execute = AsyncMock(return_value=mock_result)

    async def mock_flush():
        for obj in added:
            if hasattr(obj, "id") and obj.id is None:
                obj.id = uuid4()
    session.flush = mock_flush
    session.commit = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    factory.return_value = cm
    return factory


def _make_initial_state(**overrides) -> dict:
    state = {
        "research_id": uuid4(),
        "user_id": uuid4(),
        "topic": "Crash Recovery Test",
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
# Test: crash during plan phase → recover
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_crash_recovery_plan_phase(
    mock_mcp_client, mock_llm_service, mock_db_session_factory
):
    """App crashes during plan phase → graph still at interrupt → resume works."""
    checkpointer = MemorySaver()

    # Graph 1: run to interrupt
    graph1 = compile_research_graph(
        mcp_client=mock_mcp_client,
        llm_service_override=mock_llm_service,
        db_session_factory=mock_db_session_factory,
        checkpointer=checkpointer,
    )

    thread_id = f"crash-plan-{uuid4()}"
    config = {"configurable": {"thread_id": thread_id, "db_session_factory": mock_db_session_factory}}

    await graph1.ainvoke(_make_initial_state(), config)

    # Simulate crash: discard graph1
    del graph1

    # Graph 2: new instance, same checkpointer
    graph2 = compile_research_graph(
        mcp_client=mock_mcp_client,
        llm_service_override=mock_llm_service,
        db_session_factory=mock_db_session_factory,
        checkpointer=checkpointer,
    )

    # Verify graph is still at interrupt
    state = await graph2.aget_state(config)
    assert state is not None
    assert state.values["status"] == "draft"

    # Resume with confirm
    result = await graph2.ainvoke(Command(resume={"action": "confirm"}), config)
    assert result["status"] == "completed"


# ---------------------------------------------------------------------------
# Test: cancel persists across crash
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cancel_persists_across_crash(
    mock_mcp_client, mock_llm_service, mock_db_session_factory
):
    """Cancel flag persists across crash → recovery routes to partial_aggregate."""
    checkpointer = MemorySaver()

    # Graph 1: run to interrupt + set cancel
    graph1 = compile_research_graph(
        mcp_client=mock_mcp_client,
        llm_service_override=mock_llm_service,
        db_session_factory=mock_db_session_factory,
        checkpointer=checkpointer,
    )

    thread_id = f"crash-cancel-{uuid4()}"
    config = {"configurable": {"thread_id": thread_id, "db_session_factory": mock_db_session_factory}}

    await graph1.ainvoke(_make_initial_state(), config)

    # Set cancel before crash
    await graph1.aupdate_state(config, {"cancel_requested": True})

    # Simulate crash
    del graph1

    # Graph 2: recover
    graph2 = compile_research_graph(
        mcp_client=mock_mcp_client,
        llm_service_override=mock_llm_service,
        db_session_factory=mock_db_session_factory,
        checkpointer=checkpointer,
    )

    # Verify cancel flag persisted
    state = await graph2.aget_state(config)
    assert state.values["cancel_requested"] is True

    # Resume with confirm → should route to partial_aggregate
    result = await graph2.ainvoke(Command(resume={"action": "confirm"}), config)
    assert result["cancel_requested"] is True
