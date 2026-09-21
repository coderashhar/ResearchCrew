"""Data contracts passed between research steps and to the API.

Planner and critic schemas double as LLM structured-output schemas, so
field descriptions are written for the model as much as for readers.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

Score = Annotated[int, Field(ge=1, le=10)]


class SearchQuery(BaseModel):
    query: str = Field(min_length=1, description="A focused web search query.")
    topic: Literal["general", "news"] = Field(
        description="'news' for recent events and announcements; 'general' for "
        "background, explanations and evergreen topics."
    )
    days: int | None = Field(
        default=None,
        ge=1,
        le=365,
        description="Only for news: how many days back to search. Omit for general.",
    )


class SearchPlan(BaseModel):
    queries: list[SearchQuery] = Field(
        min_length=1,
        max_length=5,
        description="3-4 complementary queries that together cover the topic.",
    )


class Source(BaseModel):
    id: int = Field(ge=1, description="Citation number, rendered as [id].")
    url: str
    title: str
    domain: str
    content: str
    score: float = 0.0


class UnsupportedClaim(BaseModel):
    claim: str = Field(description="The claim as written in the report.")
    source_id: int | None = Field(
        default=None, description="The source it cites, or null if uncited."
    )
    reason: str = Field(description="Why the cited source does not support it.")


class Critique(BaseModel):
    accuracy: Score = Field(description="Claims match what the sources say.")
    coverage: Score = Field(description="Important aspects of the topic are covered.")
    citation_quality: Score = Field(description="Claims are cited to the right source.")
    clarity: Score = Field(description="Structure and writing are clear.")
    recency: Score = Field(description="Information is current where it matters.")
    overall: Score
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(
        default_factory=list, description="Specific, actionable improvements."
    )
    unsupported_claims: list[UnsupportedClaim] = Field(default_factory=list)
    needs_more_research: bool = Field(
        default=False,
        description="True only if gaps cannot be fixed from the current sources.",
    )
    followup_queries: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="Searches that would fill the gaps, when needs_more_research.",
    )


class Draft(BaseModel):
    version: int = Field(ge=1)
    report: str
    critique: Critique | None = None
