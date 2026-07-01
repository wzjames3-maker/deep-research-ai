import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from src.models.user import User


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, async_client, db_session):
        await async_client.post("/api/v1/auth/register", json={
            "username": "logintest1", "password": "TestPass1"
        })

        response = await async_client.post("/api/v1/auth/login", json={
            "username": "logintest1", "password": "TestPass1"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "logintest1"
        assert data["expiresIn"] == 86400
        assert isinstance(data["userId"], str)
        assert len(data["token"].split(".")) == 3

    @pytest.mark.asyncio
    async def test_login_remember_me(self, async_client):
        await async_client.post("/api/v1/auth/register", json={
            "username": "logintest2", "password": "TestPass1"
        })

        response = await async_client.post("/api/v1/auth/login", json={
            "username": "logintest2", "password": "TestPass1", "rememberMe": True
        })

        assert response.status_code == 200
        assert response.json()["expiresIn"] == 604800

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, async_client, db_session):
        await async_client.post("/api/v1/auth/register", json={
            "username": "logintest3", "password": "TestPass1"
        })

        response = await async_client.post("/api/v1/auth/login", json={
            "username": "logintest3", "password": "wrongpassword"
        })

        assert response.status_code == 401
        assert response.json()["code"] == "INVALID_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, async_client):
        response = await async_client.post("/api/v1/auth/login", json={
            "username": "no_such_user_42", "password": "TestPass1"
        })

        assert response.status_code == 401
        assert response.json()["code"] == "INVALID_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_login_account_locked_after_5_fail(self, async_client, db_session):
        await async_client.post("/api/v1/auth/register", json={
            "username": "logintest5", "password": "TestPass1"
        })

        from src.repos.user_repo import UserRepository
        repo = UserRepository(db_session)
        user = await repo.find_by_username("logintest5")
        user.failed_login_count = 4
        await db_session.commit()

        response5 = await async_client.post("/api/v1/auth/login", json={
            "username": "logintest5", "password": "wrong"
        })
        assert response5.status_code == 401

        response6 = await async_client.post("/api/v1/auth/login", json={
            "username": "logintest5", "password": "TestPass1"
        })
        assert response6.status_code == 423
        assert response6.json()["code"] == "ACCOUNT_LOCKED"

    @pytest.mark.asyncio
    async def test_login_correct_password_while_locked(self, async_client, db_session):
        await async_client.post("/api/v1/auth/register", json={
            "username": "logintest6", "password": "TestPass1"
        })

        from src.repos.user_repo import UserRepository
        repo = UserRepository(db_session)
        user = await repo.find_by_username("logintest6")
        user.status = "locked"
        user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
        user.failed_login_count = 5
        await db_session.commit()

        response = await async_client.post("/api/v1/auth/login", json={
            "username": "logintest6", "password": "TestPass1"
        })

        assert response.status_code == 423
        assert response.json()["code"] == "ACCOUNT_LOCKED"

    @pytest.mark.asyncio
    async def test_login_auto_unlock_after_expiry(self, async_client, db_session):
        await async_client.post("/api/v1/auth/register", json={
            "username": "logintest7", "password": "TestPass1"
        })

        from src.repos.user_repo import UserRepository
        repo = UserRepository(db_session)
        user = await repo.find_by_username("logintest7")
        user.status = "locked"
        user.locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)
        user.failed_login_count = 5
        await db_session.commit()

        response = await async_client.post("/api/v1/auth/login", json={
            "username": "logintest7", "password": "TestPass1"
        })

        assert response.status_code == 200
        assert response.json()["username"] == "logintest7"

    @pytest.mark.asyncio
    async def test_login_rate_limit(self, async_client):
        for _ in range(10):
            r = await async_client.post("/api/v1/auth/login", json={
                "username": "nobody", "password": "nobody"
            })
            assert r.status_code in (200, 401, 423)

        r = await async_client.post("/api/v1/auth/login", json={
            "username": "nobody", "password": "nobody"
        })
        assert r.status_code == 429
        assert r.json()["code"] == "RATE_LIMITED"

    @pytest.mark.asyncio
    async def test_login_empty_username(self, async_client):
        response = await async_client.post("/api/v1/auth/login", json={
            "username": "", "password": "TestPass1"
        })
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_login_empty_password(self, async_client):
        response = await async_client.post("/api/v1/auth/login", json={
            "username": "testuser", "password": ""
        })
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_login_username_case_insensitive(self, async_client):
        await async_client.post("/api/v1/auth/register", json={
            "username": "TestLogin", "password": "TestPass1"
        })

        response = await async_client.post("/api/v1/auth/login", json={
            "username": "testlogin", "password": "TestPass1"
        })

        assert response.status_code == 200
        assert response.json()["username"].lower() == "testlogin"
