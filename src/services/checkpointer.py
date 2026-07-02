"""LangGraph PostgresSaver checkpointer initialization.

Provides a singleton AsyncPostgresSaver instance for graph checkpoint persistence.
Tables (checkpoints, checkpoint_blobs, checkpoint_writes) are auto-created by setup().
"""

import structlog
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from src.config import settings

logger = structlog.get_logger()

_checkpointer: AsyncPostgresSaver | None = None
_saver_ctx: object | None = None


async def get_checkpointer() -> AsyncPostgresSaver:
    """Return singleton AsyncPostgresSaver, creating it on first call.

    Calls setup() to ensure checkpoint tables exist.
    Stores the context manager reference to prevent GC from closing
    the psycopg connection pool prematurely.
    """
    global _checkpointer, _saver_ctx
    if _checkpointer is None:
        conn_string = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        _saver_ctx = AsyncPostgresSaver.from_conn_string(conn_string)
        _checkpointer = await _saver_ctx.__aenter__()
        await _checkpointer.setup()
        logger.info("checkpointer_initialized", tables=["checkpoints", "checkpoint_blobs", "checkpoint_writes"])
    return _checkpointer


async def close_checkpointer() -> None:
    """Close the checkpointer connection pool (called on app shutdown)."""
    global _checkpointer, _saver_ctx
    if _saver_ctx is not None:
        try:
            await _saver_ctx.__aexit__(None, None, None)
        except Exception as e:
            logger.warning("checkpointer_close_error", error=str(e))
        _saver_ctx = None
    _checkpointer = None
    logger.info("checkpointer_closed")
