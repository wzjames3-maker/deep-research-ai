import pytest
import time
from datetime import datetime, timedelta, timezone
from src.utils.ticket_store import verify_ticket, _store


class TestMeRefreshTicket:
    @pytest.mark.asyncio
    async def test_me_success(self, async_client):
        await async_client.post("/api/v1/auth/register", json={
            "username": "metest1", "password": "TestPass1"
        })
        login_resp = await async_client.post("/api/v1/auth/login", json={
            "username": "metest1", "password": "TestPass1"
        })
        token = login_resp.json()["token"]

        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "metest1"
        assert data["status"] == "active"
        assert isinstance(data["userId"], str)

    @pytest.mark.asyncio
    async def test_me_token_invalid(self, async_client):
        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert response.status_code == 401
        assert response.json()["code"] == "TOKEN_INVALID"

    @pytest.mark.asyncio
    async def test_refresh_success(self, async_client):
        await async_client.post("/api/v1/auth/register", json={
            "username": "refreshtest1", "password": "TestPass1"
        })
        login_resp = await async_client.post("/api/v1/auth/login", json={
            "username": "refreshtest1", "password": "TestPass1"
        })
        old_token = login_resp.json()["token"]

        response = await async_client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {old_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["token"], str)
        assert data["token"] != old_token
        assert data["expiresIn"] == 86400
        assert len(data["token"].split(".")) == 3

    @pytest.mark.asyncio
    async def test_refresh_when_locked(self, async_client, db_session):
        await async_client.post("/api/v1/auth/register", json={
            "username": "refreshlock1", "password": "TestPass1"
        })
        login_resp = await async_client.post("/api/v1/auth/login", json={
            "username": "refreshlock1", "password": "TestPass1"
        })
        token = login_resp.json()["token"]

        from src.repos.user_repo import UserRepository
        repo = UserRepository(db_session)
        user = await repo.find_by_username("refreshlock1")
        user.status = "locked"
        user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
        await db_session.commit()

        response = await async_client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403
        assert response.json()["code"] == "ACCOUNT_LOCKED"

    @pytest.mark.asyncio
    async def test_ticket_success(self, async_client):
        await async_client.post("/api/v1/auth/register", json={
            "username": "tickettest1", "password": "TestPass1"
        })
        login_resp = await async_client.post("/api/v1/auth/login", json={
            "username": "tickettest1", "password": "TestPass1"
        })
        token = login_resp.json()["token"]

        response = await async_client.post(
            "/api/v1/auth/ticket",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["expiresIn"] == 30
        ticket = data["ticket"]
        parts = ticket.split("-")
        assert len(parts) == 5

        user_id = verify_ticket(ticket)
        assert user_id is not None

    @pytest.mark.asyncio
    async def test_ticket_expired(self, async_client):
        """ticket 过期后验证应返回 None (AC-AUTH-015)"""
        await async_client.post("/api/v1/auth/register", json={
            "username": "ticketexpire1", "password": "TestPass1"
        })
        login_resp = await async_client.post("/api/v1/auth/login", json={
            "username": "ticketexpire1", "password": "TestPass1"
        })
        token = login_resp.json()["token"]

        response = await async_client.post(
            "/api/v1/auth/ticket",
            headers={"Authorization": f"Bearer {token}"}
        )
        data = response.json()
        ticket = data["ticket"]

        # 手动将 ticket 过期时间设为过去
        if ticket in _store:
            uid, _ = _store[ticket]
            _store[ticket] = (uid, time.time() - 1)

        result = verify_ticket(ticket)
        assert result is None

    @pytest.mark.asyncio
    async def test_refresh_old_token_still_usable(self, async_client):
        """AC-AUTH-014: 刷新后旧 Token 在短期内仍可使用"""
        await async_client.post("/api/v1/auth/register", json={
            "username": "oldtokenok1", "password": "TestPass1"
        })
        login_resp = await async_client.post("/api/v1/auth/login", json={
            "username": "oldtokenok1", "password": "TestPass1"
        })
        old_token = login_resp.json()["token"]

        # Refresh to get new token
        refresh_resp = await async_client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {old_token}"}
        )
        assert refresh_resp.status_code == 200
        new_token = refresh_resp.json()["token"]
        assert new_token != old_token

        # Old token should still work for /me
        me_old = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {old_token}"}
        )
        assert me_old.status_code == 200
        assert me_old.json()["username"] == "oldtokenok1"

        # New token should also work
        me_new = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_token}"}
        )
        assert me_new.status_code == 200

    @pytest.mark.asyncio
    async def test_ticket_invalid(self, async_client):
        response = await async_client.post(
            "/api/v1/auth/ticket",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401
