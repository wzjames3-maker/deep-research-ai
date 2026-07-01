import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.research_plan_feedback import ResearchPlanFeedback


class ResearchPlanFeedbackRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        research_id: uuid.UUID,
        round: int,
        feedback: str,
        plan_snapshot: dict,
    ) -> ResearchPlanFeedback:
        entry = ResearchPlanFeedback(
            research_id=research_id,
            round=round,
            user_feedback=feedback,
            plan_snapshot=plan_snapshot,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def count_by_research(self, research_id: uuid.UUID) -> int:
        stmt = select(func.count(ResearchPlanFeedback.id)).where(
            ResearchPlanFeedback.research_id == research_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one() or 0
