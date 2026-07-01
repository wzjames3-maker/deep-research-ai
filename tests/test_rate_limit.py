import pytest
from fastapi import FastAPI, Depends
from httpx import AsyncClient, ASGITransport
from src.errors import AppException, app_exception_handler
from src.middleware.rate_limiter import RateLimit, _store


@pytest.fixture(autouse=True)
def _clear_store():
    _store.clear()
    yield
    _store.clear()


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_exception_handler(AppException, app_exception_handler)

    @app.post("/test/5min", dependencies=[Depends(RateLimit(5))])
    async def endpoint_5min():
        return {"status": "ok"}

    @app.post("/test/10min", dependencies=[Depends(RateLimit(10))])
    async def endpoint_10min():
        return {"status": "ok"}

    return app


@pytest.mark.asyncio
async def test_rate_limit_within_bounds():
    app = _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for i in range(5):
            r = await client.post("/test/5min")
            assert r.status_code == 200, f"request {i + 1}: expected 200 got {r.status_code}"
            assert "x-ratelimit-remaining" in r.headers


@pytest.mark.asyncio
async def test_rate_limit_exceeded():
    app = _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(5):
            r = await client.post("/test/5min")
            assert r.status_code == 200

        r = await client.post("/test/5min")
        assert r.status_code == 429
        body = r.json()
        assert body["code"] == "RATE_LIMITED"
        assert "x-ratelimit-remaining" in r.headers
        assert "x-ratelimit-reset" in r.headers


@pytest.mark.asyncio
async def test_rate_limit_different_routes():
    app = _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(5):
            r = await client.post("/test/5min")
            assert r.status_code == 200

        r = await client.post("/test/10min")
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_different_ips():
    app = _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(5):
            r = await client.post("/test/5min", headers={"X-Forwarded-For": "1.2.3.4"})
            assert r.status_code == 200

        r = await client.post("/test/5min", headers={"X-Forwarded-For": "1.2.3.4"})
        assert r.status_code == 429

        r = await client.post("/test/5min", headers={"X-Forwarded-For": "5.6.7.8"})
        assert r.status_code == 200
