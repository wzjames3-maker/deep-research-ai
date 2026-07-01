import time
import asyncio
from fastapi import Request, Response, Depends
from src.errors import RateLimitedError
from src.middleware.auth import get_current_user
from src.models.user import User

_store: dict[str, list[float]] = {}
_lock = asyncio.Lock()


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


class RateLimit:
    def __init__(self, limit: int):
        self.limit = limit

    async def __call__(self, request: Request, response: Response):
        ip = _get_client_ip(request)
        path = request.url.path
        key = f"{path}:{ip}"
        now = time.time()

        async with _lock:
            timestamps = _store.get(key, [])
            timestamps = [t for t in timestamps if now - t < 60]
            remaining = self.limit - len(timestamps)

            if remaining <= 0:
                oldest = int(timestamps[0])
                reset = oldest + 60
                raise RateLimitedError(
                    "请求过于频繁，请稍后重试",
                    headers={
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset),
                    },
                )

            timestamps.append(now)
            _store[key] = timestamps
            remaining = self.limit - len(timestamps)

        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + 60))


class UserRateLimit:
    def __init__(self, limit: int):
        self.limit = limit

    async def __call__(self, request: Request, response: Response, current_user: User = Depends(get_current_user)):
        path = request.url.path
        key = f"{path}:user:{current_user.id}"
        now = time.time()

        async with _lock:
            timestamps = _store.get(key, [])
            timestamps = [t for t in timestamps if now - t < 60]
            remaining = self.limit - len(timestamps)

            if remaining <= 0:
                oldest = int(timestamps[0])
                reset = oldest + 60
                raise RateLimitedError(
                    "请求过于频繁，请稍后重试",
                    headers={
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset),
                    },
                )

            timestamps.append(now)
            _store[key] = timestamps
            remaining = self.limit - len(timestamps)

        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + 60))


async def cleanup_expired_entries():
    while True:
        await asyncio.sleep(300)
        now = time.time()
        async with _lock:
            stale = [k for k, v in _store.items() if not any(now - t < 60 for t in v)]
            for k in stale:
                del _store[k]
