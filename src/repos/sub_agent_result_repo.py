import uuid
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.sub_agent_result import SubAgentResult


class SubAgentResultRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def bulk_create(
        self, research_id: uuid.UUID, sub_agents: list[dict]
    ) -> list[SubAgentResult]:
        results = []
        for sa in sub_agents:
            result = SubAgentResult(
                research_id=research_id,
                agent_name=sa["agent_name"],
                agent_goal=sa["agent_goal"],
                search_direction=sa["search_direction"],
            )
            self.db.add(result)
            results.append(result)
        await self.db.flush()
        return results

    async def find_by_research(self, research_id: uuid.UUID) -> list[SubAgentResult]:
        stmt = (
            select(SubAgentResult)
            .where(SubAgentResult.research_id == research_id)
            .order_by(SubAgentResult.created_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_research(self, research_id: uuid.UUID) -> None:
        stmt = delete(SubAgentResult).where(
            SubAgentResult.research_id == research_id
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def save(self, result: SubAgentResult) -> None:
        self.db.add(result)
        await self.db.flush()
