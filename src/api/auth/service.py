import math
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from src.models.user import User
from src.repos.user_repo import UserRepository
from src.utils.bcrypt import hash_password, verify_password
from src.utils.jwt import create_token
from src.errors import UsernameExistsError, InvalidCredentialsError, AccountLockedError, TokenInvalidError


async def register_user(db: AsyncSession, username: str, password: str) -> tuple[User, str]:
    password_hash = hash_password(password)
    repo = UserRepository(db)

    try:
        user = await repo.create(username, password_hash)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise UsernameExistsError("该账号已被注册")

    token = create_token(user.id, user.username)
    return user, token


async def login_user(db: AsyncSession, username: str, password: str, remember_me: bool = False) -> tuple[User, str]:
    cleaned = User.clean_username(username)
    repo = UserRepository(db)

    user = await repo.find_by_username(cleaned)
    if user is None:
        raise InvalidCredentialsError("账号或密码错误")

    user.check_and_auto_unlock()
    if user.status == "locked":
        if user.locked_until:
            minutes = math.ceil((user.locked_until - datetime.now(timezone.utc)).total_seconds() / 60)
        else:
            minutes = 15
        raise AccountLockedError(f"账户已锁定，请 {max(minutes, 0)} 分钟后重试")

    if not verify_password(password, user.password_hash):
        user.increment_failed_login()
        await repo.save(user)
        await db.commit()
        raise InvalidCredentialsError("账号或密码错误")

    user.reset_failed_login()
    user.remember_me = remember_me
    await repo.save(user)
    await db.commit()

    expires_delta = 604800 if remember_me else 86400
    token = create_token(user.id, user.username, expires_delta)
    return user, token


async def refresh_user_token(db: AsyncSession, user: User) -> tuple[str, int]:
    repo = UserRepository(db)
    db_user = await repo.find_by_id(user.id)
    if db_user is None:
        raise TokenInvalidError("用户不存在")

    db_user.check_and_auto_unlock()
    if db_user.status == "locked":
        if db_user.locked_until:
            minutes = math.ceil((db_user.locked_until - datetime.now(timezone.utc)).total_seconds() / 60)
        else:
            minutes = 15
        raise AccountLockedError(f"账户已锁定，请 {max(minutes, 0)} 分钟后重试", http_status=403)

    token = create_token(db_user.id, db_user.username)
    await db.commit()
    return token, 86400
