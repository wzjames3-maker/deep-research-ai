"""
Auth 集成测试 — 完整流程覆盖
AC-AUTH-001 ~ 016, EC-AUTH-001 ~ 008
"""
import pytest
import time
from datetime import datetime, timedelta, timezone
from tests.integration.conftest import MOCK_PLAN


class TestAuthHappyPath:
    """完整 Happy Path: 注册 → 登录 → /me → /refresh → /ticket."""

    @pytest.mark.asyncio
    async def test_full_auth_flow(self, async_client):
        """AC-AUTH-001→004→013→014→015: 完整认证流程."""
        # Step 1: Register
        reg = await async_client.post("/api/v1/auth/register", json={
            "username": "flowuser1", "password": "StrongPass1",
        })
        assert reg.status_code == 201
        reg_data = reg.json()
        assert reg_data["username"] == "flowuser1"
        assert reg_data["expiresIn"] == 86400
        assert len(reg_data["token"].split(".")) == 3
        token = reg_data["token"]

        # Step 2: Login
        login = await async_client.post("/api/v1/auth/login", json={
            "username": "flowuser1", "password": "StrongPass1",
        })
        assert login.status_code == 200
        token = login.json()["token"]

        # Step 3: GET /me
        me = await async_client.get("/api/v1/auth/me",
                                     headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["username"] == "flowuser1"
        assert me.json()["status"] == "active"

        # Step 4: POST /refresh
        old_token = token
        refresh = await async_client.post("/api/v1/auth/refresh",
                                           headers={"Authorization": f"Bearer {old_token}"})
        assert refresh.status_code == 200
        new_token = refresh.json()["token"]
        assert new_token != old_token
        assert refresh.json()["expiresIn"] == 86400

        # Step 5: 旧 token 仍可用（5s grace）
        me_old = await async_client.get("/api/v1/auth/me",
                                         headers={"Authorization": f"Bearer {old_token}"})
        assert me_old.status_code == 200

        # Step 6: 新 token 可用
        me_new = await async_client.get("/api/v1/auth/me",
                                         headers={"Authorization": f"Bearer {new_token}"})
        assert me_new.status_code == 200

        # Step 7: POST /ticket
        ticket_resp = await async_client.post("/api/v1/auth/ticket",
                                               headers={"Authorization": f"Bearer {new_token}"})
        assert ticket_resp.status_code == 200
        ticket_data = ticket_resp.json()
        assert ticket_data["expiresIn"] == 30
        assert len(ticket_data["ticket"].split("-")) == 5


class TestAuthRegistration:
    """注册场景覆盖."""

    @pytest.mark.asyncio
    async def test_register_duplicate_409(self, async_client):
        """AC-AUTH-003: 重复注册 → 409."""
        await async_client.post("/api/v1/auth/register", json={
            "username": "dupeflow1", "password": "StrongPass1",
        })
        resp = await async_client.post("/api/v1/auth/register", json={
            "username": "DupeFlow1", "password": "StrongPass1",
        })
        assert resp.status_code == 409
        assert resp.json()["code"] == "USERNAME_EXISTS"

    @pytest.mark.asyncio
    async def test_register_trim_lowercase(self, async_client):
        """AC-AUTH-001: username 自动 trim + lowercase."""
        resp = await async_client.post("/api/v1/auth/register", json={
            "username": " TrimUser ", "password": "StrongPass1",
        })
        assert resp.status_code == 201
        assert resp.json()["username"] == "trimuser"

    @pytest.mark.asyncio
    async def test_register_weak_password_400(self, async_client):
        """AC-AUTH-002: 弱密码 → 400."""
        resp = await async_client.post("/api/v1/auth/register", json={
            "username": "weakuser1", "password": "123",
        })
        assert resp.status_code == 400
        assert resp.json()["code"] == "INVALID_PASSWORD"


class TestAuthLocking:
    """账户锁定场景."""

    @pytest.mark.asyncio
    async def test_lock_after_5_fail_then_423(self, async_client, db_session):
        """AC-AUTH-007/008: 连续 5 次错误 → locked → 正确密码 → 423."""
        # Register
        await async_client.post("/api/v1/auth/register", json={
            "username": "lockflow1", "password": "StrongPass1",
        })

        # 5 次错误密码 — 每次必须是 401（不能是 429，否则说明 rate limiter 干扰）
        for i in range(5):
            r = await async_client.post("/api/v1/auth/login", json={
                "username": "lockflow1", "password": "wrongwrong1",
            })
            assert r.status_code == 401, (
                f"attempt {i+1}: expected 401, got {r.status_code}. "
                f"If 429, rate limiter is interfering (login limit=10, but register also counts)."
            )

        # 第 6 次用正确密码 → 423（账户已锁定）
        r = await async_client.post("/api/v1/auth/login", json={
            "username": "lockflow1", "password": "StrongPass1",
        })
        assert r.status_code == 423
        assert r.json()["code"] == "ACCOUNT_LOCKED"

    @pytest.mark.asyncio
    async def test_auto_unlock_after_expiry(self, async_client, db_session):
        """AC-AUTH-009: 锁定期满 → 自动解锁."""
        await async_client.post("/api/v1/auth/register", json={
            "username": "unlockflow1", "password": "StrongPass1",
        })

        # 手动设置 locked + 已过期
        from src.repos.user_repo import UserRepository
        repo = UserRepository(db_session)
        user = await repo.find_by_username("unlockflow1")
        user.status = "locked"
        user.locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)
        user.failed_login_count = 5
        await db_session.commit()

        # 正确密码 → 200
        r = await async_client.post("/api/v1/auth/login", json={
            "username": "unlockflow1", "password": "StrongPass1",
        })
        assert r.status_code == 200
        assert r.json()["username"] == "unlockflow1"


class TestAuthToken:
    """Token 场景."""

    @pytest.mark.asyncio
    async def test_invalid_token_401(self, async_client):
        """AC-AUTH-010: 无效 token → 401."""
        r = await async_client.get("/api/v1/auth/me",
                                    headers={"Authorization": "Bearer bad.token.here"})
        assert r.status_code == 401
        assert r.json()["code"] == "TOKEN_INVALID"

    @pytest.mark.asyncio
    async def test_refresh_locked_403(self, async_client, registered_user, db_session):
        """AC-AUTH-014: 锁定账号 refresh → 403."""
        from src.repos.user_repo import UserRepository
        repo = UserRepository(db_session)
        user = await repo.find_by_username(registered_user["username"])
        user.status = "locked"
        user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
        await db_session.commit()

        r = await async_client.post("/api/v1/auth/refresh",
                                     headers={"Authorization": f"Bearer {registered_user['token']}"})
        assert r.status_code == 403
        assert r.json()["code"] == "ACCOUNT_LOCKED"


class TestAuthTicket:
    """Ticket 场景."""

    @pytest.mark.asyncio
    async def test_ticket_valid_then_expired(self, async_client, registered_user):
        """AC-AUTH-015: ticket 有效 → 30s 后过期."""
        from src.utils.ticket_store import verify_ticket, _store

        token = registered_user["token"]
        r = await async_client.post("/api/v1/auth/ticket",
                                     headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        ticket = r.json()["ticket"]

        # 立即验证 → 有效
        uid = verify_ticket(ticket)
        assert uid is not None

        # 手动模拟过期
        if ticket in _store:
            uid_orig, _ = _store[ticket]
            _store[ticket] = (uid_orig, time.time() - 1)

        uid_expired = verify_ticket(ticket)
        assert uid_expired is None
