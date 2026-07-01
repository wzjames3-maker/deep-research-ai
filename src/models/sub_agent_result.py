import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Enum, Text, ForeignKey, text as sa_text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.models.base import Base


class SubAgentResult(Base):
    __tablename__ = "sub_agent_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa_text("gen_random_uuid()"),
    )
    research_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("researches.id"), nullable=False
    )
    agent_name: Mapped[str] = mapped_column(String(200), nullable=False)
    agent_goal: Mapped[str] = mapped_column(Text, nullable=False)
    search_direction: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(
            "pending",
            "running",
            "completed",
            "failed",
            "cancelled",
            name="sub_agent_status",
            create_type=False,
        ),
        default="pending",
        server_default="pending",
        nullable=False,
    )
    rounds_completed: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    visited_urls: Mapped[list] = mapped_column(
        JSONB, default=list, server_default=sa_text("'[]'::jsonb"), nullable=False
    )
    findings_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_used: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa_text("NOW()"), nullable=False
    )

    research: Mapped["Research"] = relationship(
        "Research", back_populates="sub_agent_results"
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "agentName": self.agent_name,
            "agentGoal": self.agent_goal,
            "searchDirection": self.search_direction,
            "status": self.status,
            "roundsCompleted": self.rounds_completed,
            "visitedUrls": self.visited_urls,
            "findings": self.findings_text,
            "tokenUsed": self.token_used,
            "errorMessage": self.error_message,
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
        }
