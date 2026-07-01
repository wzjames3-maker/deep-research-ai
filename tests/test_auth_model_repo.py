import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from src.models.user import User
from src.repos.user_repo import UserRepository


def test_clean_username():
    assert User.clean_username(" ZhangSan ") == "zhangsan"
    assert User.clean_username("admin") == "admin"
    assert User.clean_username("  Foo_Bar ") == "foo_bar"


def test_validate_username_valid():
    assert User.validate_username("user123") == "user123"
    assert User.validate_username("a_b_c") == "a_b_c"
    assert User.validate_username("admin") == "admin"


def test_validate_username_invalid():
    assert User.validate_username("ab") is None
    assert User.validate_username("a" * 51) is None
    assert User.validate_username("user.name") is None
    assert User.validate_username("user-name") is None
    assert User.validate_username("user name") is None
    assert User.validate_username("") is None


def test_increment_failed_login_locks_after_5():
    user = User(username="test", password_hash="hash", status="active", failed_login_count=0)
    for i in range(4):
        user.increment_failed_login()
        assert user.failed_login_count == i + 1
        assert user.status == "active"

    user.increment_failed_login()
    assert user.failed_login_count == 5
    assert user.status == "locked"
    assert user.locked_until is not None
    assert user.locked_until > datetime.now(timezone.utc)


def test_reset_failed_login():
    user = User(
        username="test", password_hash="hash",
        status="locked", failed_login_count=5,
        locked_until=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    user.reset_failed_login()
    assert user.failed_login_count == 0
    assert user.locked_until is None
    assert user.status == "active"


def test_check_and_auto_unlock_expired():
    user = User(
        username="test", password_hash="hash",
        status="locked", failed_login_count=5,
        locked_until=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    assert user.check_and_auto_unlock() is True
    assert user.status == "active"
    assert user.failed_login_count == 0
    assert user.locked_until is None


def test_check_and_auto_unlock_null_locked():
    user = User(
        username="test", password_hash="hash",
        status="locked", failed_login_count=5,
        locked_until=None,
    )
    assert user.check_and_auto_unlock() is True
    assert user.status == "active"


def test_check_and_auto_unlock_not_expired():
    user = User(
        username="test", password_hash="hash",
        status="locked", failed_login_count=5,
        locked_until=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    assert user.check_and_auto_unlock() is False
    assert user.status == "locked"


def test_check_and_auto_unlock_not_locked():
    user = User(
        username="test", password_hash="hash",
        status="active", failed_login_count=0,
    )
    assert user.check_and_auto_unlock() is False


def test_to_dict():
    user = User(
        id=uuid4(), username="testuser",
        password_hash="secret_hash",
        status="active",
    )
    d = user.to_dict()
    assert "password_hash" not in d
    assert d["username"] == "testuser"
    assert d["status"] == "active"
    assert "id" in d
    assert "created_at" in d


@pytest.mark.asyncio
async def test_repo_create_and_find(db_session):
    repo = UserRepository(db_session)
    user = await repo.create(" ZhangSan ", "hash123")
    assert user.username == "zhangsan"

    found = await repo.find_by_id(user.id)
    assert found is not None
    assert found.username == "zhangsan"


@pytest.mark.asyncio
async def test_repo_find_by_username_case_insensitive(db_session):
    repo = UserRepository(db_session)
    await repo.create("TestUser", "hash")

    found = await repo.find_by_username("tEsTuSeR")
    assert found is not None
    assert found.username == "testuser"

    found2 = await repo.find_by_username("TESTUSER")
    assert found2 is not None

    not_found = await repo.find_by_username("nonexistent")
    assert not_found is None


@pytest.mark.asyncio
async def test_repo_exists_by_username(db_session):
    repo = UserRepository(db_session)
    await repo.create("existing", "hash")

    assert await repo.exists_by_username("ExIsTiNg") is True
    assert await repo.exists_by_username("  EXISTING  ") is True
    assert await repo.exists_by_username("nonexistent") is False


@pytest.mark.asyncio
async def test_repo_save(db_session):
    repo = UserRepository(db_session)
    user = await repo.create("modify", "hash")
    user.failed_login_count = 3
    await repo.save(user)
    await db_session.commit()

    found = await repo.find_by_id(user.id)
    assert found.failed_login_count == 3
