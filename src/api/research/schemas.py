from enum import Enum
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class ResearchTemplateEnum(str, Enum):
    tech_research = "tech_research"
    competitive_analysis = "competitive_analysis"
    literature_review = "literature_review"
    custom = "custom"


# ── Request Schemas ──────────────────────────────────────────────


class NewResearchRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=500)
    template: ResearchTemplateEnum


class ReviseRequest(BaseModel):
    feedback: str = Field(min_length=1, max_length=1000)


# ── Response Schemas ─────────────────────────────────────────────


class SubAgentPlanItem(BaseModel):
    name: str
    goal: str
    searchDirection: str


class PlanWrapper(BaseModel):
    subAgents: list[SubAgentPlanItem]


class NewResearchResponse(BaseModel):
    researchId: UUID
    plan: PlanWrapper
    planRound: int


class ReviseResponse(BaseModel):
    plan: PlanWrapper
    planRound: int


class ConfirmResponse(BaseModel):
    researchId: UUID
    status: str
    streamUrl: str


class SubAgentResultItem(BaseModel):
    name: str
    goal: str
    status: str
    findings: str
    visitedUrls: list[str]
    tokenUsed: int


class ResearchResponse(BaseModel):
    researchId: UUID
    topic: str
    template: str
    status: str
    plan: dict | None = None
    planRound: int = 1
    subAgentResults: list[SubAgentResultItem] = []
    totalTokens: int = 0
    createdAt: datetime | None = None
    startedAt: datetime | None = None
    completedAt: datetime | None = None


class ReportResponse(BaseModel):
    researchId: UUID
    topic: str
    template: str
    status: str
    plan: dict | None = None
    reportMarkdown: str | None = None
    subAgentResults: list[SubAgentResultItem] = []
    totalTokens: int = 0
    createdAt: datetime | None = None
    startedAt: datetime | None = None
    completedAt: datetime | None = None


class ResearchHistoryItem(BaseModel):
    researchId: UUID
    topic: str
    template: str
    status: str
    totalTokens: int = 0
    createdAt: datetime | None = None


class HistoryResponse(BaseModel):
    items: list[ResearchHistoryItem]
    total: int
    page: int
    pageSize: int


class DeleteResponse(BaseModel):
    deleted: bool = True


class TokenStatsResponse(BaseModel):
    todayTokens: int = 0
    weekTokens: int = 0
    totalResearches: int = 0
    avgTokensPerResearch: int = 0


class CancelResponse(BaseModel):
    researchId: UUID
    status: str
