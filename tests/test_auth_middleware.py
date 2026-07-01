import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from jose import jwt
from src.config import settings
from src.models.user import User
from src.middleware.auth import get_current_user
from src.errors import TokenInvalidError, AccountLockedError
from src.middleware.auth import require_not_locked


def _make_token(user_id: str, username: str, exp_delta: int = 3600) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": now,
        "exp": now + timedelta(seconds=exp_delta),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


@pytest.mark.asyncio
async def test_valid_token_returns_user(db_session):
    user = User(
        id=uuid4(), username="testuser1", password_hash="hash123", status="active"
    )
    db_session.add(user)
    await db_session.commit()

    token = _make_token(user.id, user.username)
    result = await get_current_user(token=token, db=db_session)

    assert result.id == user.id
    assert result.username == "testuser1"
    assert result.status == "active"


@pytest.mark.asyncio
async def test_invalid_signature(db_session):
    with pytest.raises(TokenInvalidError, match="Token 无效"):
        await get_current_user(token="invalid.token.here", db=db_session)


@pytest.mark.asyncio
async def test_expired_token(db_session):
    user = User(
        id=uuid4(), username="expireduser", password_hash="hash123", status="active"
    )
    db_session.add(user)
    await db_session.commit()

    token = _make_token(user.id, user.username, exp_delta=-3600)

    with pytest.raises(TokenInvalidError):
        await get_current_user(token=token, db=db_session)


@pytest.mark.asyncio
async def test_missing_sub_in_payload(db_session):
    now = datetime.now(timezone.utc)
    payload = {"username": "ghost", "iat": now, "exp": now + timedelta(hours=1)}
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

    with pytest.raises(TokenInvalidError):
        await get_current_user(token=token, db=db_session)


@pytest.mark.asyncio
async def test_user_not_found(db_session):
    fake_id = str(uuid4())
    token = _make_token(fake_id, "ghostuser")

    with pytest.raises(TokenInvalidError, match="用户不存在"):
        await get_current_user(token=token, db=db_session)


@pytest.mark.asyncio
async def test_locked_auto_unlock_expired(db_session):
    past_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    user = User(
        id=uuid4(),
        username="unlockme",
        password_hash="hash123",
        status="locked",
        failed_login_count=5,
        locked_until=past_time,
    )
    db_session.add(user)
    await db_session.commit()

    token = _make_token(user.id, user.username)
    result = await get_current_user(token=token, db=db_session)

    assert result.status == "active"
    assert result.failed_login_count == 0
    assert result.locked_until is None


@pytest.mark.asyncio
async def test_locked_user_pass_through_get_current_user(db_session):
    future_time = datetime.now(timezone.utc) + timedelta(minutes=10)
    user = User(
        id=uuid4(),
        username="lockeduser",
        password_hash="hash123",
        status="locked",
        failed_login_count=5,
        locked_until=future_time,
    )
    db_session.add(user)
    await db_session.commit()

    token = _make_token(user.id, user.username)
    result = await get_current_user(token=token, db=db_session)

    assert result.status == "locked"


@pytest.mark.asyncio
async def test_require_not_locked_raises(db_session):
    future_time = datetime.now(timezone.utc) + timedelta(minutes=10)
    user = User(
        id=uuid4(),
        username="blockeduser",
        password_hash="hash123",
        status="locked",
        failed_login_count=5,
        locked_until=future_time,
    )
    db_session.add(user)
    await db_session.commit()

    with pytest.raises(AccountLockedError):
        await require_not_locked(current_user=user)


@pytest.mark.asyncio
async def test_locked_with_none_locked_until(db_session):
    user = User(
        id=uuid4(),
        username="nolocktime",
        password_hash="hash123",
        status="locked",
        failed_login_count=3,
        locked_until=None,
    )
    db_session.add(user)
    await db_session.commit()

    token = _make_token(user.id, user.username)
    result = await get_current_user(token=token, db=db_session)

    assert result.status == "active"
    assert result.failed_login_count == 0


@pytest.mark.asyncio
async def test_token_with_invalid_sub_uuid(db_session):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "not-a-uuid",
        "username": "bad",
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

    with pytest.raises(TokenInvalidError):
        await get_current_user(token=token, db=db_session)
