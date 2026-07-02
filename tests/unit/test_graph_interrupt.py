"""Graph interrupt + resume专项测试 (Task 47 / AC-RES-026).

Tests cover:
- Multiple revise rounds
- Revise exceeds max rounds (TooManyRevisionsError)
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from src.errors import TooManyRevisionsError
from src.services.graph_state import ResearchState
from src.services.research_graph import compile_research_graph


MAX_REVISIONS = 10


@pytest.fixture
def mock_mcp_client():
    client = MagicMock()
    client.search = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_llm_service():
    service = MagicMock()
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
    service.aggregate_report = AsyncMock(return_value=("# Report", 500))
    service.sub_agent_search = AsyncMock(return_value={
        "sufficient": True,
        "findings": "Test findings",
        "new_search_query": None,
        "token_used": 100,
    })
    return service


@pytest.fixture
def mock_db_session_factory():
    factory = MagicMock()
    session = AsyncMock()
    added = []

    def mock_add(obj):
        added.append(obj)
    session.add = mock_add

    # Mock execute to return None for find_by_id queries
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


@pytest.fixture
def checkpointer():
    return MemorySaver()


def _make_initial_state(**overrides) -> dict:
    state = {
        "research_id": uuid4(),
        "user_id": uuid4(),
        "topic": "Test Topic",
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
# Test: multiple revise rounds
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_multiple_revise_rounds(
    mock_mcp_client, mock_llm_service, mock_db_session_factory, checkpointer
):
    """Revise → interrupt → revise → interrupt → confirm → complete."""
    graph = compile_research_graph(
        mcp_client=mock_mcp_client,
        llm_service_override=mock_llm_service,
        db_session_factory=mock_db_session_factory,
        checkpointer=checkpointer,
    )

    thread_id = f"test-multi-revise-{uuid4()}"
    config = {"configurable": {"thread_id": thread_id, "db_session_factory": mock_db_session_factory}}

    # First invoke → interrupt
    await graph.ainvoke(_make_initial_state(), config)

    # Revise round 1
    result1 = await graph.ainvoke(
        Command(resume={"action": "revise", "feedback": "More detail please"}),
        config,
    )
    assert result1["plan_round"] == 2

    # Revise round 2
    result2 = await graph.ainvoke(
        Command(resume={"action": "revise", "feedback": "Even more detail"}),
        config,
    )
    assert result2["plan_round"] == 3

    # Now confirm
    result3 = await graph.ainvoke(
        Command(resume={"action": "confirm"}),
        config,
    )
    assert result3["status"] == "completed"
    assert result3["report_markdown"] != ""


@pytest.mark.asyncio
async def test_revise_exceeds_max_rounds(
    mock_mcp_client, mock_llm_service, mock_db_session_factory, checkpointer
):
    """After MAX_REVISIONS rounds, TooManyRevisionsError should be raised."""
    graph = compile_research_graph(
        mcp_client=mock_mcp_client,
        llm_service_override=mock_llm_service,
        db_session_factory=mock_db_session_factory,
        checkpointer=checkpointer,
    )

    thread_id = f"test-max-rev-{uuid4()}"
    config = {"configurable": {"thread_id": thread_id, "db_session_factory": mock_db_session_factory}}

    await graph.ainvoke(_make_initial_state(), config)
    # 9 successful revises (plan_round goes 1→2→...→10)
    for i in range(9):
        result = await graph.ainvoke(
            Command(resume={"action": "revise", "feedback": f"revise {i+1}"}),
            config,
        )
        assert result["plan_round"] == i + 2
    # 10th revise triggers TooManyRevisionsError (plan_round=10 >= MAX_REVISIONS)
    with pytest.raises(TooManyRevisionsError):
        await graph.ainvoke(
            Command(resume={"action": "revise", "feedback": "revise 10"}),
            config,
        )