import pytest
from uuid import uuid4
from src.models.user import User


class TestRegister:
    @pytest.mark.asyncio
    async def test_register_success(self, async_client):
        response = await async_client.post("/api/v1/auth/register", json={
            "username": "newuser",
            "password": "StrongPass1"
        })
        assert response.status_code == 201
        data = response.json()
        assert isinstance(data["userId"], str)
        assert data["username"] == "newuser"
        segments = data["token"].split(".")
        assert len(segments) == 3
        assert data["expiresIn"] == 86400

    @pytest.mark.asyncio
    async def test_register_weak_password(self, async_client):
        response = await async_client.post("/api/v1/auth/register", json={
            "username": "testuser",
            "password": "1234"
        })
        assert response.status_code == 400
        assert response.json()["code"] == "INVALID_PASSWORD"

    @pytest.mark.asyncio
    async def test_register_short_username(self, async_client):
        response = await async_client.post("/api/v1/auth/register", json={
            "username": "ab",
            "password": "StrongPass1"
        })
        assert response.status_code == 400
        assert response.json()["code"] == "INVALID_USERNAME"

    @pytest.mark.asyncio
    async def test_register_invalid_username_chars(self, async_client):
        response = await async_client.post("/api/v1/auth/register", json={
            "username": "user@name!",
            "password": "StrongPass1"
        })
        assert response.status_code == 400
        assert response.json()["code"] == "INVALID_USERNAME"

    @pytest.mark.asyncio
    async def test_register_duplicate_case_insensitive(self, async_client, db_session):
        user = User(
            id=uuid4(),
            username="dupe",
            password_hash="$2b$12$deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
            status="active",
        )
        db_session.add(user)
        await db_session.commit()

        response = await async_client.post("/api/v1/auth/register", json={
            "username": "Dupe",
            "password": "StrongPass1"
        })
        assert response.status_code == 409
        assert response.json()["code"] == "USERNAME_EXISTS"

    @pytest.mark.asyncio
    async def test_register_duplicate_exact(self, async_client, db_session):
        user = User(
            id=uuid4(),
            username="dupe2",
            password_hash="$2b$12$deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
            status="active",
        )
        db_session.add(user)
        await db_session.commit()

        response = await async_client.post("/api/v1/auth/register", json={
            "username": "dupe2",
            "password": "StrongPass1"
        })
        assert response.status_code == 409
        assert response.json()["code"] == "USERNAME_EXISTS"

    @pytest.mark.asyncio
    async def test_register_trim_and_lowercase(self, async_client):
        response = await async_client.post("/api/v1/auth/register", json={
            "username": " ZhangSan ",
            "password": "StrongPass1"
        })
        assert response.status_code == 201
        assert response.json()["username"] == "zhangsan"

    @pytest.mark.asyncio
    async def test_register_case_insensitive_login_hint(self, async_client):
        response = await async_client.post("/api/v1/auth/register", json={
            "username": "ZHANGSAN2",
            "password": "StrongPass1"
        })
        assert response.status_code == 201
        assert response.json()["username"] == "zhangsan2"

    @pytest.mark.asyncio
    async def test_register_rate_limit_real_endpoint(self, async_client):
        """AC-AUTH-016: POST /auth/register > 5 次/分钟 → 第 6 次返回 429"""
        for i in range(5):
            r = await async_client.post("/api/v1/auth/register", json={
                "username": f"ratelimituser{i}",
                "password": "StrongPass1"
            })
            assert r.status_code in (201, 409), f"request {i+1}: expected 201/409 got {r.status_code}"

        r = await async_client.post("/api/v1/auth/register", json={
            "username": "ratelimituser_extra",
            "password": "StrongPass1"
        })
        assert r.status_code == 429
        assert r.json()["code"] == "RATE_LIMITED"
