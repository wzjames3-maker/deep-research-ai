import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, text as sa_text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from src.models.base import Base


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa_text("gen_random_uuid()"),
    )
    research_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("researches.id", ondelete="CASCADE"), nullable=False
    )
    citation_number: Mapped[int] = mapped_column(Integer, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    snippet: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_agent: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    research: Mapped["Research"] = relationship(
        "Research", back_populates="citations"
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "citationNumber": self.citation_number,
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "sourceAgent": self.source_agent,
            "accessedAt": self.accessed_at.isoformat() if self.accessed_at else None,
        }
