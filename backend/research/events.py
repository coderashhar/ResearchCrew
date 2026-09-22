"""The event stream a run emits while it works.

A run takes minutes, so the client watches it happen rather than waiting
on one response. Graph node updates are translated here into a small,
stable vocabulary the UI can render.
"""

import json
from typing import Iterator, Literal

from pydantic import BaseModel

from research.citations import used_ids
from research.schemas import Critique, SearchQuery, Source

EventName = Literal["run", "plan", "sources", "draft", "critique", "final", "error"]


class Event(BaseModel):
    name: EventName
    data: dict


class SourceSummary(BaseModel):
    """A source without its body text: the UI shows this while reading."""

    id: int
    title: str
    domain: str
    url: str

    @classmethod
    def of(cls, s: Source) -> "SourceSummary":
        return cls(id=s.id, title=s.title, domain=s.domain, url=s.url)


def run_started(run_id: str) -> Event:
    return Event(name="run", data={"id": run_id})


def failed(message: str) -> Event:
    return Event(name="error", data={"message": message})


def from_update(node: str, state: dict) -> Iterator[Event]:
    """Translate one graph node's state update into client events."""
    if node == "plan":
        queries: list[SearchQuery] = state.get("queries", [])
        yield Event(name="plan", data={"queries": [q.model_dump() for q in queries]})

    elif node == "search_and_read":
        sources: list[Source] = state.get("sources", [])
        yield Event(
            name="sources",
            data={
                "added": [SourceSummary.of(s).model_dump() for s in sources],
                "round": state.get("research_rounds", 1),
            },
        )

    elif node == "write":
        for draft in state.get("drafts", []):
            yield Event(
                name="draft",
                data={"version": draft.version, "report": draft.report},
            )

    elif node == "critique":
        for draft in state.get("drafts", []):
            if draft.critique:
                yield Event(
                    name="critique",
                    data={
                        "version": draft.version,
                        "critique": draft.critique.model_dump(),
                    },
                )


def final_event(state: dict, elapsed_s: float) -> Event:
    """The finished run: report, the sources it cites, and every draft."""
    report = state.get("report", "")
    cited = set(used_ids(report))
    drafts = state.get("drafts", [])
    critique: Critique | None = drafts[-1].critique if drafts else None
    return Event(
        name="final",
        data={
            "report": report,
            "score": critique.overall if critique else None,
            "sources": [
                SourceSummary.of(s).model_dump()
                for s in state.get("sources", [])
                if s.id in cited
            ],
            "drafts": [d.model_dump() for d in drafts],
            "elapsed_s": round(elapsed_s, 1),
        },
    )


def to_sse(event: Event) -> str:
    return f"event: {event.name}\ndata: {json.dumps(event.data, default=str)}\n\n"


def heartbeat() -> str:
    """A comment line: keeps idle proxies from closing the connection."""
    return ": keep-alive\n\n"
