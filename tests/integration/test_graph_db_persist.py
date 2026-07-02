"""Integration tests verifying graph nodes correctly persist to DB.

These tests use REAL DB sessions (not mocks) to catch bugs that
mock-based unit tests miss:
- _run_sub_agents updating DB status in real-time
- aggregate_node setting completed_at
- sub_agent_round SSE including name field
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from src.services.research_graph import compile_research_graph
from src.repos.research_repo import ResearchRepository
from src.repos.sub_agent_result_repo import SubAgentResultRepository


MOCK_PLAN_3 = [
    {"name": "Alpha", "goal": "Goal A", "searchDirection": "query A"},
    {"name": "Beta", "goal": "Goal B", "searchDirection": "query B"},
    {"name": "Gamma", "goal": "Goal C", "searchDirection": "query C"},
]


def _make_mock_llm():
    llm = MagicMock()
    llm.generate_plan = AsyncMock(return_value=(MOCK_PLAN_3, 500))
    llm.revise_plan = AsyncMock(return_value=(MOCK_PLAN_3, 300))
    llm.aggregate_report = AsyncMock(return_value=("# Test Report", 200))
    llm.sub_agent_search = AsyncMock(return_value={
        "sufficient": True, "findings": "test findings", "new_search_query": "",
    })
    return llm


def _mock_sub_graph_result(agent_def, status="completed"):
    """Create a mock sub-graph that returns a completed result."""
    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value={
        "status": status,
        "findings": f"Findings for {agent_def['name']}",
        "token_used": 100,
        "has_error": status == "failed",
        "visited_urls": ["http://example.com"],
        "rounds_completed": 2,
    })
    return mock_graph


# ---------------------------------------------------------------------------
# Test: dispatch_node updates sub-agent status in DB
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_run_sub_agents_persists_to_db(test_db, test_engine):
    """dispatch_node must update each sub-agent's DB record after _run_sub_agents."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    from src.models.user import User
    from src.models.research import Research

    # Create user, research, and sub-agent results in DB
    user = User(username=f"test_{uuid4().hex[:6]}", password_hash="hashed")
    test_db.add(user)
    await test_db.flush()

    research = Research(user_id=user.id, topic="Test", template="tech_research")
    research.plan_json = MOCK_PLAN_3
    research.plan_round = 1
    research.status = "running"
    test_db.add(research)
    await test_db.flush()

    sa_repo = SubAgentResultRepository(test_db)
    await sa_repo.bulk_create(research.id, [
        {"agent_name": a["name"], "agent_goal": a["goal"], "search_direction": a["searchDirection"]}
        for a in MOCK_PLAN_3
    ])
    await test_db.commit()

    rid = research.id
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    # Patch build_sub_agent_graph so sub-agents return completed instantly
    def mock_build_graph(**kwargs):
        return MagicMock(ainvoke=AsyncMock(side_effect=lambda state, **kw: {
            "status": "completed",
            "findings": f"Findings for {state['agent_def']['name']}",
            "token_used": 100,
            "has_error": False,
            "visited_urls": ["http://example.com"],
            "rounds_completed": 2,
        }))

    with patch("src.services.sub_agent_graph.build_sub_agent_graph", side_effect=mock_build_graph):
        llm = _make_mock_llm()
        graph = compile_research_graph(
            llm_service_override=llm,
            db_session_factory=session_factory,
            checkpointer=MemorySaver(),
        )
        config = {"configurable": {"thread_id": str(rid), "db_session_factory": session_factory}}
        state = {
            "research_id": rid, "user_id": user.id, "topic": "Test", "template": "tech_research",
            "plan": [], "plan_round": 0, "feedback": None, "_action": None,
            "sub_agent_results": [], "cancel_requested": False,
            "report_markdown": "", "total_tokens": 0, "status": "pending", "error_message": None,
        }
        # First invoke: plan gen → interrupt
        await graph.ainvoke(state, config)
        # Second invoke: dispatch → sub-agents → aggregate
        await graph.ainvoke(Command(resume={"action": "confirm"}), config)

    # Verify DB records — dispatch_node should have persisted sub-agent results
    async with session_factory() as verify_session:
        sa_repo = SubAgentResultRepository(verify_session)
        db_results = await sa_repo.find_by_research(rid)

        assert len(db_results) == 3
        for r in db_results:
            assert r.status == "completed", f"{r.agent_name}: expected completed, got {r.status}"
            assert r.findings_text, f"{r.agent_name}: findings should not be empty"
            assert r.token_used == 100
            assert r.completed_at is not None


# ---------------------------------------------------------------------------
# Test: aggregate_node sets completed_at
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_aggregate_node_sets_completed_at(test_db, test_engine):
    """aggregate_node must set completed_at on the research record."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    from src.models.user import User

    user = User(username=f"test_{uuid4().hex[:6]}", password_hash="hashed")
    test_db.add(user)
    await test_db.commit()
    user_id = user.id
    research_id = uuid4()

    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    # Run full graph (plan → interrupt → confirm → aggregate)
    mock_sub_results = [
        {"name": a["name"], "status": "completed", "findings": f"F {a['name']}",
         "token_used": 100, "has_error": False, "visited_urls": [], "rounds_completed": 2}
        for a in MOCK_PLAN_3
    ]

    with patch("src.services.research_graph._run_sub_agents", return_value=mock_sub_results):
        llm = _make_mock_llm()
        graph = compile_research_graph(
            llm_service_override=llm,
            db_session_factory=session_factory,
            checkpointer=MemorySaver(),
        )
        config = {"configurable": {"thread_id": str(research_id), "db_session_factory": session_factory}}
        state = {
            "research_id": research_id, "user_id": user_id, "topic": "Test", "template": "tech_research",
            "plan": [], "plan_round": 0, "feedback": None, "_action": None,
            "sub_agent_results": [], "cancel_requested": False,
            "report_markdown": "", "total_tokens": 0, "status": "pending", "error_message": None,
        }
        await graph.ainvoke(state, config)
        await graph.ainvoke(Command(resume={"action": "confirm"}), config)

    async with session_factory() as verify_session:
        repo = ResearchRepository(verify_session)
        r = await repo.find_by_id(research_id)
        assert r is not None
        assert r.status == "completed"
        assert r.completed_at is not None
        assert r.report_markdown


# ---------------------------------------------------------------------------
# Test: partial_aggregate_node sets completed_at on cancel
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_partial_aggregate_sets_completed_at(test_db, test_engine):
    """partial_aggregate_node must set completed_at when research is cancelled."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    from src.models.user import User

    user = User(username=f"test_{uuid4().hex[:6]}", password_hash="hashed")
    test_db.add(user)
    await test_db.commit()
    user_id = user.id
    research_id = uuid4()

    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    mock_sub_results = [
        {"name": a["name"], "status": "completed", "findings": f"F {a['name']}",
         "token_used": 100, "has_error": False, "visited_urls": [], "rounds_completed": 2}
        for a in MOCK_PLAN_3
    ]
    mock_sub_results[2]["status"] = "failed"
    mock_sub_results[2]["has_error"] = True

    with patch("src.services.research_graph._run_sub_agents", return_value=mock_sub_results):
        llm = _make_mock_llm()
        graph = compile_research_graph(
            llm_service_override=llm,
            db_session_factory=session_factory,
            checkpointer=MemorySaver(),
        )
        config = {"configurable": {"thread_id": str(research_id), "db_session_factory": session_factory}}
        state = {
            "research_id": research_id, "user_id": user_id, "topic": "Test", "template": "tech_research",
            "plan": [], "plan_round": 0, "feedback": None, "_action": None,
            "sub_agent_results": [], "cancel_requested": True,
            "report_markdown": "", "total_tokens": 0, "status": "pending", "error_message": None,
        }
        await graph.ainvoke(state, config)
        await graph.ainvoke(Command(resume={"action": "confirm"}), config)

    async with session_factory() as verify_session:
        repo = ResearchRepository(verify_session)
        r = await repo.find_by_id(research_id)
        assert r is not None
        assert r.status == "cancelled"
        assert r.completed_at is not None


# ---------------------------------------------------------------------------
# Test: sub_agent_round SSE includes name
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_sub_agent_round_sse_includes_name():
    """sub_agent_round event must include agent name for frontend matching."""
    from src.services.sub_agent_graph import analyze_node
    from src.services.sse_manager import sse_manager

    research_id = uuid4()
    captured_events = []

    original_push = sse_manager.push_event

    async def capture_push(rid, event_type, data):
        if event_type == "sub_agent_round":
            captured_events.append(data)
        return await original_push(rid, event_type, data)

    with patch.object(sse_manager, "push_event", side_effect=capture_push):
        mock_llm = MagicMock()
        mock_llm.sub_agent_search = AsyncMock(return_value={
            "sufficient": True, "findings": "test", "new_search_query": "",
        })

        state = {
            "research_id": research_id,
            "topic": "Test",
            "agent_def": {"name": "TestAgent", "goal": "Test", "searchDirection": "query"},
            "search_direction": "query",
            "visited_urls": [],
            "findings": "",
            "rounds_completed": 0,
            "sufficient": False,
            "token_used": 0,
            "status": "running",
            "has_error": False,
            "search_results": [],
        }

        with patch("src.services.sub_agent_graph._llm_service_override", mock_llm):
            await analyze_node(state, {"configurable": {}})

    assert len(captured_events) == 1
    event = captured_events[0]
    assert "name" in event
    assert event["name"] == "TestAgent"
