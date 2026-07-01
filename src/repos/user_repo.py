from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, username: str, password_hash: str) -> User:
        cleaned = User.clean_username(username)
        user = User(username=cleaned, password_hash=password_hash)
        self.db.add(user)
        await self.db.flush()
        return user

    async def find_by_id(self, user_id: UUID) -> User | None:
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_username(self, username: str) -> User | None:
        cleaned = User.clean_username(username)
        stmt = select(User).where(func.lower(User.username) == cleaned)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_by_username(self, username: str) -> bool:
        cleaned = User.clean_username(username)
        stmt = select(User.id).where(func.lower(User.username) == cleaned)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def save(self, user: User) -> None:
        self.db.add(user)
        await self.db.flush()
