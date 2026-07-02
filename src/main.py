from contextlib import asynccontextmanager
import asyncio
import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from src.models.base import engine
from src.api.router import router
from src.middleware.cors import setup_cors
from src.errors import AppException, app_exception_handler
from src.middleware.rate_limiter import cleanup_expired_entries
from src.utils.logging import RequestIdMiddleware, setup_logging
from src.services.checkpointer import get_checkpointer, close_checkpointer


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    cleanup_task = asyncio.create_task(cleanup_expired_entries())
    await get_checkpointer()  # Initialize LangGraph checkpoint tables
    yield
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    await close_checkpointer()  # Close checkpoint connection pool


def create_app() -> FastAPI:
    app = FastAPI(
        title="DeepResearch Agent",
        version="1.0.0",
        lifespan=lifespan,
    )

    setup_cors(app)

    app.add_middleware(RequestIdMiddleware)

    app.include_router(router)

    app.add_exception_handler(AppException, app_exception_handler)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        for error in exc.errors():
            loc = error.get("loc", [])
            field = str(loc[-1]) if loc else ""
            if "username" in field:
                return JSONResponse(
                    status_code=400,
                    content={"code": "INVALID_USERNAME", "message": "账号格式无效（3-50字符，仅字母数字下划线）"},
                )
            if "password" in field:
                return JSONResponse(
                    status_code=400,
                    content={"code": "INVALID_PASSWORD", "message": "密码长度应为8-64字符，且至少包含1个字母和1个数字"},
                )
        return JSONResponse(
            status_code=400,
            content={"code": "INVALID_USERNAME", "message": "请求参数无效"},
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        structlog.get_logger().error("unhandled_exception", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"code": "INTERNAL_ERROR", "message": "服务器内部错误"},
        )

    @app.get("/health")
    @app.get("/api/v1/health")
    async def health():
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return {"status": "ok", "service": "deepresearch"}
        except Exception:
            return {"status": "degraded", "service": "deepresearch"}

    return app


app = create_app()
