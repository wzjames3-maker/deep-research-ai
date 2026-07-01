"""
Rate Limiter 集成测试 — 真实端点频控
Task 31: 4 个场景
"""
import pytest
from src.middleware.rate_limiter import _store as rate_limit_store


class TestRegisterRateLimit:
    """AC-AUTH-012: Register 端点: 5 次/分钟/IP."""

    @pytest.mark.asyncio
    async def test_register_6th_triggers_429(self, async_client):
        """连续 6 次注册 → 第 6 次 429."""
        username_prefix = "rlreg"
        for i in range(5):
            resp = await async_client.post("/api/v1/auth/register", json={
                "username": f"{username_prefix}_{i}",
                "password": "StrongPass1",
            })
            assert resp.status_code == 201, f"attempt {i + 1}: expected 201 got {resp.status_code}"

        resp = await async_client.post("/api/v1/auth/register", json={
            "username": f"{username_prefix}_5",
            "password": "StrongPass1",
        })
        assert resp.status_code == 429
        body = resp.json()
        assert body["code"] == "RATE_LIMITED"
        assert "x-ratelimit-remaining" in resp.headers
        assert "x-ratelimit-reset" in resp.headers


class TestLoginRateLimit:
    """AC-AUTH-012: Login 端点: 10 次/分钟/IP."""

    @pytest.mark.asyncio
    async def test_login_11th_triggers_429(self, async_client):
        """连续 11 次登录 → 第 11 次 429."""
        for i in range(11):
            resp = await async_client.post("/api/v1/auth/login", json={
                "username": "nonexistent",
                "password": "wrongpass1",
            })
            if i < 10:
                assert resp.status_code in (401, 429), f"attempt {i + 1}: got {resp.status_code}"
                if resp.status_code == 429:
                    pytest.fail(f"Rate limit triggered too early at attempt {i + 1}")
            else:
                assert resp.status_code == 429, f"attempt {i + 1}: expected 429 got {resp.status_code}"
                body = resp.json()
                assert body["code"] == "RATE_LIMITED"


class TestRateLimitDifferentIPs:
    """不同 IP 的频控独立性."""

    @pytest.mark.asyncio
    async def test_different_ip_independence(self, async_client):
        """IP A 用完配额 → 429; IP B 不受影响 → 201."""
        ip_a = "1.2.3.4"
        ip_b = "5.6.7.8"

        username_prefix_a = "ipauser"
        # IP A: exhaust register limit
        for i in range(5):
            resp = await async_client.post(
                "/api/v1/auth/register",
                json={"username": f"{username_prefix_a}_{i}", "password": "StrongPass1"},
                headers={"X-Forwarded-For": ip_a},
            )
            assert resp.status_code == 201, f"IP A attempt {i + 1}: got {resp.status_code}"

        # IP A: next request → 429
        resp = await async_client.post(
            "/api/v1/auth/register",
            json={"username": f"{username_prefix_a}_5", "password": "StrongPass1"},
            headers={"X-Forwarded-For": ip_a},
        )
        assert resp.status_code == 429

        # IP B: should still work (independent counter)
        resp = await async_client.post(
            "/api/v1/auth/register",
            json={"username": "ipbuser_1", "password": "StrongPass1"},
            headers={"X-Forwarded-For": ip_b},
        )
        assert resp.status_code == 201, f"IP B should be independent, got {resp.status_code}"


class TestRateLimitWindowReset:
    """窗口重置后恢复."""

    @pytest.mark.asyncio
    async def test_window_reset_allows_request(self, async_client):
        """耗尽配额 → 清除时间窗口 → 请求恢复."""
        username_prefix = "rlwin"

        # Exhaust the register limit
        for i in range(5):
            resp = await async_client.post("/api/v1/auth/register", json={
                "username": f"{username_prefix}_{i}",
                "password": "StrongPass1",
            })
            assert resp.status_code == 201, f"attempt {i + 1}: got {resp.status_code}"

        # 429
        resp = await async_client.post("/api/v1/auth/register", json={
            "username": f"{username_prefix}_5",
            "password": "StrongPass1",
        })
        assert resp.status_code == 429

        # Simulate window reset by clearing the store (equivalent to 60s passing)
        rate_limit_store.clear()

        # Next request should succeed
        resp = await async_client.post("/api/v1/auth/register", json={
            "username": "rlwin_after_reset",
            "password": "StrongPass1",
        })
        assert resp.status_code == 201, f"after window reset: expected 201, got {resp.status_code}"
