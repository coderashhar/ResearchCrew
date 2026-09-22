"""The research loop as a LangGraph state machine.

plan -> search_and_read -> write -> critique, then the critique decides:
finish, rewrite from the same sources, or go read more. That decision is
what turns the score from a label into a quality gate.
"""

import time
from dataclasses import dataclass
from typing import Annotated, Any, Callable, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from tavily import TavilyClient

from research import tools
from research.agents import Chains
from research.citations import (
    build_sources_section,
    clean_citations,
    format_sources_block,
    used_ids,
)
from research.config import Settings
from research.schemas import Critique, Draft, SearchQuery, Source

# The opening round plus one follow-up. A second follow-up costs another
# search, read and rewrite, which the run's time budget rarely affords.
MAX_RESEARCH_ROUNDS = 2


def _merge_drafts(old: list[Draft], new: list[Draft]) -> list[Draft]:
    """Append drafts, but let a later write of the same version replace it.

    The critique node re-emits the draft it judged, with the critique
    attached, instead of mutating shared state.
    """
    by_version = {d.version: d for d in old}
    by_version.update({d.version: d for d in new})
    return [by_version[v] for v in sorted(by_version)]


def _append(old: list, new: list) -> list:
    return [*old, *new]


class ResearchState(TypedDict, total=False):
    topic: str
    started_at: float
    queries: Annotated[list[SearchQuery], _append]
    pending_queries: list[SearchQuery]
    sources: Annotated[list[Source], _append]
    drafts: Annotated[list[Draft], _merge_drafts]
    research_rounds: int
    revisions: int
    report: str


@dataclass
class ResearchTools:
    """Injection seam: tests pass fakes, production passes Tavily."""

    search: Callable[[SearchQuery], list[dict]]
    select: Callable[..., list[dict]] = tools.select_sources
    read: Callable[..., list[Source]] = tools.read_sources

    @classmethod
    def from_client(cls, client: TavilyClient) -> "ResearchTools":
        return cls(
            search=lambda q: tools.search(client, q),
            read=lambda results, start_id: tools.read_sources(client, results, start_id),
        )


def route_after_critique(
    state: ResearchState, settings: Settings, now: float
) -> Literal["finalize", "write", "search_and_read"]:
    """Decide what a critique means for the run.

    Pure function so the policy is testable without running the graph.
    """
    drafts = state.get("drafts", [])
    critique = drafts[-1].critique if drafts else None
    if critique is None:
        return "finalize"

    elapsed = now - state.get("started_at", now)
    out_of_time = elapsed > settings.time_budget_s
    if (
        critique.overall >= settings.pass_score
        or state.get("revisions", 0) >= settings.max_revisions
        or out_of_time
    ):
        return "finalize"
    if critique.needs_more_research and state.get("research_rounds", 0) < MAX_RESEARCH_ROUNDS:
        return "search_and_read"
    return "write"


def build_graph(chains: Chains, research_tools: ResearchTools, settings: Settings) -> Any:
    def plan(state: ResearchState) -> ResearchState:
        plan = chains.planner.invoke({"topic": state["topic"]})
        return {
            "started_at": state.get("started_at") or time.monotonic(),
            "queries": plan.queries,
            "pending_queries": plan.queries,
        }

    def search_and_read(state: ResearchState) -> ResearchState:
        sources = state.get("sources", [])
        results: list[dict] = []
        for query in state.get("pending_queries", []):
            results.extend(research_tools.search(query))
        picked = research_tools.select(results, existing_urls=[s.url for s in sources])
        new_sources = research_tools.read(picked, start_id=len(sources) + 1)
        return {
            "sources": new_sources,
            "pending_queries": [],
            "research_rounds": state.get("research_rounds", 0) + 1,
        }

    def write(state: ResearchState) -> ResearchState:
        drafts = state.get("drafts", [])
        previous = drafts[-1] if drafts else None
        report = chains.writer.invoke(
            {
                "topic": state["topic"],
                "sources_block": format_sources_block(state.get("sources", [])),
                "previous_draft": previous.report if previous else "",
                "critique_notes": _critique_notes(previous),
            }
        )
        return {
            "drafts": [Draft(version=len(drafts) + 1, report=report)],
            "revisions": state.get("revisions", 0) + (1 if previous else 0),
        }

    def critique(state: ResearchState) -> ResearchState:
        draft = state["drafts"][-1]
        result: Critique = chains.critic.invoke(
            {
                "report": draft.report,
                "sources_block": format_sources_block(state.get("sources", [])),
            }
        )
        judged = draft.model_copy(update={"critique": result})
        pending = (
            [SearchQuery(query=q, topic="general") for q in result.followup_queries]
            if result.needs_more_research
            else []
        )
        return {"drafts": [judged], "pending_queries": pending, "queries": pending}

    def finalize(state: ResearchState) -> ResearchState:
        sources = state.get("sources", [])
        report = state["drafts"][-1].report
        valid = {s.id for s in sources}
        cleaned = clean_citations(report, valid)
        section = build_sources_section(sources, used_ids(cleaned))
        return {"report": f"{cleaned.rstrip()}\n\n{section}" if section else cleaned}

    graph = StateGraph(ResearchState)
    graph.add_node("plan", plan)
    graph.add_node("search_and_read", search_and_read)
    graph.add_node("write", write)
    graph.add_node("critique", critique)
    graph.add_node("finalize", finalize)

    graph.add_edge(START, "plan")
    graph.add_edge("plan", "search_and_read")
    graph.add_edge("search_and_read", "write")
    graph.add_edge("write", "critique")
    graph.add_conditional_edges(
        "critique",
        lambda state: route_after_critique(state, settings, time.monotonic()),
        {"finalize": "finalize", "write": "write", "search_and_read": "search_and_read"},
    )
    graph.add_edge("finalize", END)
    return graph.compile()


def _critique_notes(draft: Draft | None) -> str:
    if draft is None or draft.critique is None:
        return ""
    c = draft.critique
    lines = [f"Score: {c.overall}/10", *(f"- {g}" for g in c.gaps)]
    lines += [
        f"- Unsupported: {u.claim} (cites {u.source_id or 'nothing'}): {u.reason}"
        for u in c.unsupported_claims
    ]
    return "\n".join(lines)
