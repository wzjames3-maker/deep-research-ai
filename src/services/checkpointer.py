"""LangGraph PostgresSaver checkpointer initialization.

Provides a singleton AsyncPostgresSaver instance for graph checkpoint persistence.
Tables (checkpoints, checkpoint_blobs, checkpoint_writes) are auto-created by setup().
"""

import structlog
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from src.config import settings

logger = structlog.get_logger()

_checkpointer: AsyncPostgresSaver | None = None


async def get_checkpointer() -> AsyncPostgresSaver:
    """Return singleton AsyncPostgresSaver, creating it on first call.

    Calls setup() to ensure checkpoint tables exist.
    """
    global _checkpointer
    if _checkpointer is None:
        # Convert SQLAlchemy asyncpg URL to psycopg-compatible URL
        # postgresql+asyncpg://... -> postgresql://...
        conn_string = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        # AsyncPostgresSaver.from_conn_string is an async context manager
        saver = AsyncPostgresSaver.from_conn_string(conn_string)
        _checkpointer = await saver.__aenter__()
        await _checkpointer.setup()
        logger.info("checkpointer_initialized", tables=["checkpoints", "checkpoint_blobs", "checkpoint_writes"])
    return _checkpointer


async def close_checkpointer() -> None:
    """Close the checkpointer connection pool (called on app shutdown)."""
    global _checkpointer
    if _checkpointer is not None:
        # The checkpointer was created via __aenter__, so we need to __aexit__ it
        # But since we stored the inner object, we just close the underlying pool
        try:
            if hasattr(_checkpointer, 'close'):
                await _checkpointer.close()
        except Exception as e:
            logger.warning("checkpointer_close_error", error=str(e))
        _checkpointer = None
        logger.info("checkpointer_closed")
