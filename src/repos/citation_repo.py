import uuid
from datetime import datetime, timezone
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.citation import Citation


class CitationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def bulk_create(
        self, research_id: uuid.UUID, citations: list[dict]
    ) -> list[Citation]:
        """Create multiple citation records for a research.

        Each dict should have: citation_number, url, title, snippet, source_agent
        """
        created = []
        for c in citations:
            citation = Citation(
                research_id=research_id,
                citation_number=c["citation_number"],
                url=c["url"],
                title=c.get("title", ""),
                snippet=c.get("snippet", ""),
                source_agent=c.get("source_agent", ""),
                accessed_at=datetime.now(timezone.utc),
            )
            self.db.add(citation)
            created.append(citation)
        await self.db.flush()
        return created

    async def find_by_research(self, research_id: uuid.UUID) -> list[Citation]:
        """Get all citations for a research, ordered by citation_number."""
        stmt = (
            select(Citation)
            .where(Citation.research_id == research_id)
            .order_by(Citation.citation_number)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_research(self, research_id: uuid.UUID) -> None:
        """Delete all citations for a research."""
        stmt = delete(Citation).where(Citation.research_id == research_id)
        await self.db.execute(stmt)
        await self.db.flush()
