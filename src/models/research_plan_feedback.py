import uuid
from datetime import datetime
from sqlalchemy import Integer, DateTime, Text, ForeignKey, text as sa_text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.models.base import Base


class ResearchPlanFeedback(Base):
    __tablename__ = "research_plan_feedbacks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa_text("gen_random_uuid()"),
    )
    research_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("researches.id"), nullable=False
    )
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    user_feedback: Mapped[str] = mapped_column(Text, nullable=False)
    plan_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa_text("NOW()"), nullable=False
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "researchId": str(self.research_id),
            "round": self.round,
            "userFeedback": self.user_feedback,
            "planSnapshot": self.plan_snapshot,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
