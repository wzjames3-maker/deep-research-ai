from uuid import UUID
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.base import get_db
from src.models.user import User
from src.errors import TokenInvalidError, AccountLockedError
from src.utils.jwt import verify_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = verify_token(token)

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise TokenInvalidError("Token 无效")

    try:
        user_id = UUID(user_id_str)
    except (ValueError, TypeError):
        raise TokenInvalidError("Token 无效")

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise TokenInvalidError("用户不存在")

    if user.check_and_auto_unlock():
        await db.commit()
        await db.refresh(user)

    return user


async def require_not_locked(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.status == "locked":
        raise AccountLockedError("账户已锁定")
    return current_user
