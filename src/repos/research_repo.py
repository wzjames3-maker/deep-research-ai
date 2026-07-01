import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.research import Research


class ResearchRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: uuid.UUID, topic: str, template: str) -> Research:
        research = Research(user_id=user_id, topic=topic, template=template)
        self.db.add(research)
        await self.db.flush()
        return research

    async def find_by_id(self, research_id: uuid.UUID) -> Research | None:
        stmt = (
            select(Research)
            .where(Research.id == research_id, Research.deleted_at.is_(None))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_user(
        self, user_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[Research], int]:
        base_query = select(Research).where(
            Research.user_id == user_id,
            Research.deleted_at.is_(None),
        )
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one() or 0

        stmt = (
            base_query
            .order_by(Research.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def find_active_by_user(self, user_id: uuid.UUID) -> Research | None:
        stmt = (
            select(Research)
            .where(
                Research.user_id == user_id,
                Research.deleted_at.is_(None),
                Research.status.in_(["draft", "running"]),  # confirmed 为瞬态不持久化
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def has_running_by_user(self, user_id: uuid.UUID) -> bool:
        """Check if user has a running research (for concurrent limit RULE-RES-001)."""
        stmt = select(Research.id).where(
            Research.user_id == user_id,
            Research.deleted_at.is_(None),
            Research.status == "running",
        ).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_token_stats(self, user_id: uuid.UUID) -> dict:
        """Get token usage statistics for a user."""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)

        stmt = select(
            func.coalesce(
                func.sum(case(
                    (Research.created_at >= today_start, Research.total_tokens),
                    else_=0,
                )), 0
            ).label("today_tokens"),
            func.coalesce(
                func.sum(case(
                    (Research.created_at >= week_ago, Research.total_tokens),
                    else_=0,
                )), 0
            ).label("week_tokens"),
            func.count(Research.id).label("total_researches"),
            func.coalesce(
                func.avg(case(
                    (Research.status == "completed", Research.total_tokens),
                    else_=None,
                )), 0
            ).label("avg_tokens"),
        ).where(
            Research.user_id == user_id,
            Research.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        row = result.one()
        return {
            "todayTokens": int(row.today_tokens),
            "weekTokens": int(row.week_tokens),
            "totalResearches": int(row.total_researches),
            "avgTokensPerResearch": int(row.avg_tokens) if row.avg_tokens else 0,
        }

    async def save(self, research: Research) -> None:
        self.db.add(research)
        await self.db.flush()
