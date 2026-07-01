import asyncio
import gc
import logging
import sys
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from unittest.mock import AsyncMock, MagicMock, patch
from src.config import settings
from src.models.base import Base, get_db
from src.main import create_app
from src.middleware.rate_limiter import _store as rate_limit_store
from src.utils.ticket_store import _store as ticket_store


# ---------------------------------------------------------------------------
# Shared mock plan data
# ---------------------------------------------------------------------------
MOCK_PLAN = [
    {"name": "market_analyst", "goal": "分析市场规模", "searchDirection": "AI market size"},
    {"name": "tech_analyst", "goal": "分析技术趋势", "searchDirection": "AI technology trends"},
    {"name": "competitor_analyst", "goal": "分析竞争对手", "searchDirection": "AI competitors"},
]

MOCK_PLAN_REVISED = [
    {"name": "market_analyst", "goal": "分析市场规模（修订）", "searchDirection": "AI market size revised"},
    {"name": "tech_analyst", "goal": "分析技术趋势", "searchDirection": "AI technology trends"},
    {"name": "competitor_analyst", "goal": "分析竞争对手", "searchDirection": "AI competitors"},
    {"name": "strategy_analyst", "goal": "分析策略", "searchDirection": "AI strategy"},
]


@pytest.fixture
def mock_plan():
    return MOCK_PLAN


@pytest.fixture
def mock_llm_for_graph():
    """Mock LLM service at graph level so graph still creates DB records."""
    from langgraph.checkpoint.memory import MemorySaver
    from src.services.research_graph import compile_research_graph

    mock_llm = MagicMock()
    mock_llm.generate_plan = AsyncMock(return_value=(MOCK_PLAN, 500))
    mock_llm.revise_plan = AsyncMock(return_value=(MOCK_PLAN_REVISED, 300))
    mock_llm.aggregate_report = AsyncMock(return_value=("# Mock Report", 200))

    memory_saver = MemorySaver()
    test_graph = compile_research_graph(
        llm_service_override=mock_llm,
        checkpointer=memory_saver
    )

    with patch("src.services.exec_engine.get_research_graph", return_value=test_graph):
        yield {"llm": mock_llm}


# ---------------------------------------------------------------------------
# Windows event loop policy fix for psycopg
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# ---------------------------------------------------------------------------
# Suppress NullPool GC teardown noise (cosmetic only).
# ---------------------------------------------------------------------------
class _NullPoolGCFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if "garbage collector cleaning up" in msg or "Exception terminating connection" in msg:
            return False
        return True


logging.getLogger("sqlalchemy.pool.impl.NullPool").addFilter(_NullPoolGCFilter())


@pytest.fixture(autouse=True)
def _clear_stores():
    rate_limit_store.clear()
    ticket_store.clear()
    yield
    rate_limit_store.clear()
    ticket_store.clear()


@pytest.fixture(autouse=True)
def _reset_graph_singletons():
    """Reset graph and checkpointer singletons between tests."""
    import src.services.research_graph as rg
    import src.services.checkpointer as cp
    rg._compiled_graph = None
    cp._checkpointer = None
    yield
    rg._compiled_graph = None
    cp._checkpointer = None


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(settings.DATABASE_URL, echo=False, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _cleanup_db(test_engine):
    """Truncate all tables after each test for data isolation."""
    yield
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE'))


@pytest_asyncio.fixture
async def db_session(test_engine):
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    # Don't use `async with` — it calls session.close() during teardown which
    # may run after the event loop has begun shutting down, causing
    # "attached to a different loop" errors.  Instead, yield the session and
    # let the _gc_barrier fixture (below) clean up connections safely.
    session = async_session()
    yield session
    # Roll back any uncommitted work so the connection is in a clean state
    # before the barrier forces GC.
    try:
        await session.rollback()
    except Exception:
        pass


@pytest_asyncio.fixture
async def test_db(test_engine):
    """Direct database access for test setup (bypasses API layer)."""
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    session = async_session()
    yield session
    try:
        await session.rollback()
    except Exception:
        pass


@pytest_asyncio.fixture
async def async_client(test_engine):
    app = create_app()
    sessionmaker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with sessionmaker() as session:
            try:
                yield session
            finally:
                await session.rollback()
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GC Barrier — runs AFTER every test (autouse, function-scoped).
#
# Root cause: NullPool discards connections after use but relies on Python GC
# to actually terminate the underlying asyncpg connections.  If GC runs after
# the event loop has shut down, asyncpg's __del__ schedules cleanup tasks on
# a dead loop → RuntimeError.
#
# Fix: Force GC *while the event loop is still alive*, then give the loop one
# tick (asyncio.sleep(0)) to process the resulting cleanup tasks.
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(autouse=True)
async def _gc_barrier():
    """Force garbage collection while the event loop is still running."""
    yield
    # Break explicit references held by this fixture scope
    gc.collect()
    gc.collect()
    # Let the loop process any __del__-scheduled tasks (asyncpg terminate, etc.)
    await asyncio.sleep(0)
