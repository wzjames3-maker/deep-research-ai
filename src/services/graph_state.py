"""LangGraph State Schema definitions.

ResearchState: main graph state (TypedDict + Annotated reducer).
SubAgentState: sub-agent subgraph state.
"""

from typing import Annotated, TypedDict
from uuid import UUID

import operator


class ResearchState(TypedDict):
    """Main graph state for the research workflow.

    `sub_agent_results` uses Annotated[list[dict], operator.add] reducer
    so that Send API fan-out results are appended, not overwritten.
    """

    research_id: UUID
    user_id: UUID
    topic: str
    template: str
    plan: list[dict]
    plan_round: int
    feedback: str | None
    _action: str | None  # interrupt resume value: "confirm" | "revise"
    sub_agent_results: Annotated[list[dict], operator.add]
    cancel_requested: bool
    report_markdown: str
    total_tokens: int
    status: str
    error_message: str | None


class SubAgentState(TypedDict):
    """Sub-agent subgraph state.

    Each Send() carries an independent SubAgentState
    with its own agent_def, search direction, and findings.
    """

    research_id: UUID
    topic: str
    agent_def: dict  # {name, goal, searchDirection}
    search_direction: str
    visited_urls: list[str]
    findings: str
    rounds_completed: int
    sufficient: bool
    token_used: int
    status: str
    has_error: bool
    search_results: list  # latest round results (transient, not persisted)
