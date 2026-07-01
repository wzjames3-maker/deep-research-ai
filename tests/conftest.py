import asyncio
import gc
import logging
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from src.config import settings
from src.models.base import Base, get_db
from src.main import create_app
from src.middleware.rate_limiter import _store as rate_limit_store
from src.utils.ticket_store import _store as ticket_store


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
