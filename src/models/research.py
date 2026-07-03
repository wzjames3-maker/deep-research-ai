import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Enum, Text, ForeignKey, select, func, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.models.base import Base


class Research(Base):
    __tablename__ = "researches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa_text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    template: Mapped[str] = mapped_column(
        Enum(
            "tech_research",
            "competitive_analysis",
            "literature_review",
            "custom",
            name="research_template",
            create_type=False,
        ),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Enum(
            "draft",
            "confirmed",
            "running",
            "completed",
            "failed",
            "cancelled",
            name="research_status",
            create_type=False,
        ),
        default="draft",
        server_default="draft",
        nullable=False,
    )
    plan_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    report_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_tokens: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa_text("NOW()"), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa_text("NOW()"),
        onupdate=sa_text("NOW()"),
        nullable=False,
    )

    sub_agent_results: Mapped[list["SubAgentResult"]] = relationship(
        "SubAgentResult", back_populates="research", lazy="selectin"
    )
    citations: Mapped[list["Citation"]] = relationship(
        "Citation", back_populates="research", lazy="selectin",
        order_by="Citation.citation_number",
    )

    @property
    def is_active(self) -> bool:
        # confirmed 为 V1 瞬态（不持久化），此处不检查
        return self.status in ("draft", "running")

    def soft_delete(self) -> None:
        self.deleted_at = datetime.now(timezone.utc)

    def mark_failed(self, reason: str) -> None:
        self.status = "failed"
        self.error_message = reason
        self.completed_at = datetime.now(timezone.utc)

    def has_any_completed_sub_agents(self) -> bool:
        return any(sa.status == "completed" for sa in self.sub_agent_results)

    @staticmethod
    async def has_active_research(db: AsyncSession, user_id: uuid.UUID) -> bool:
        """Check if user has any active research (draft OR running).

        NOTE: For RULE-RES-001 concurrency control, use ResearchRepository.has_running_by_user()
        instead — draft does NOT block new research creation.
        This method is for UI display (e.g., showing active research badge).
        """
        stmt = select(Research.id).where(
            Research.user_id == user_id,
            Research.deleted_at.is_(None),
            Research.status.in_(["draft", "running"]),
        ).limit(1)
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def count_revisions(db: AsyncSession, research_id: uuid.UUID) -> int:
        from src.models.research_plan_feedback import ResearchPlanFeedback
        stmt = select(func.count(ResearchPlanFeedback.id)).where(
            ResearchPlanFeedback.research_id == research_id
        )
        result = await db.execute(stmt)
        return result.scalar_one() or 0

    def update_total_tokens(self) -> None:
        self.total_tokens = sum(sa.token_used for sa in self.sub_agent_results)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "userId": str(self.user_id),
            "topic": self.topic,
            "template": self.template,
            "status": self.status,
            "planJson": self.plan_json,
            "reportMarkdown": self.report_markdown,
            "totalTokens": self.total_tokens,
            "errorMessage": self.error_message,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }
