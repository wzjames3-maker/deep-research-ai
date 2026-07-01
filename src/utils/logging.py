import logging
import time
import uuid
from contextvars import ContextVar
from typing import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.config import settings

_request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    return _request_id_var.get() or "N/A"


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        _request_id_var.set(request_id)
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000

        logger = structlog.get_logger()
        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

        response.headers["X-Request-ID"] = request_id
        return response


def _filter_secrets(_logger, _method, event_dict: dict) -> dict:
    _secret_keys = {
        "password", "password_hash", "passwd",
        "token", "access_token", "refresh_token",
        "api_key", "apikey",
        "ticket",
        "authorization",
        "secret", "secret_key",
    }
    for key in list(event_dict):
        if key.lower() in _secret_keys:
            event_dict[key] = "***"
    return event_dict


def _add_service_and_request_id(_logger, _method, event_dict: dict) -> dict:
    event_dict["service"] = "deepresearch"
    event_dict["request_id"] = get_request_id()
    return event_dict


def setup_logging() -> None:
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    is_json = settings.LOG_FORMAT.lower() == "json"

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        _add_service_and_request_id,
        _filter_secrets,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if is_json:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.setLevel(log_level)

    root = logging.getLogger()
    root.handlers = [h for h in root.handlers if not isinstance(h.formatter, structlog.stdlib.ProcessorFormatter)]
    root.addHandler(handler)
    root.setLevel(log_level)

    for name in ("uvicorn.access", "uvicorn.error"):
        lib_logger = logging.getLogger(name)
        lib_logger.handlers = []
        lib_logger.propagate = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name or __name__)
