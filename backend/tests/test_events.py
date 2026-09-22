import json

from research import events
from research.schemas import Critique, Draft, SearchQuery, Source


def source(i=1, domain="a.com"):
    return Source(
        id=i, url=f"https://{domain}/p{i}", title=f"T{i}", domain=domain, content="body text"
    )


def critique(overall=8):
    return Critique(
        accuracy=overall,
        coverage=overall,
        citation_quality=overall,
        clarity=overall,
        recency=overall,
        overall=overall,
    )


def emit(node, state):
    return list(events.from_update(node, state))


def test_plan_update_lists_queries():
    [event] = emit("plan", {"queries": [SearchQuery(query="q", topic="news", days=7)]})
    assert event.name == "plan"
    assert event.data["queries"] == [{"query": "q", "topic": "news", "days": 7}]


def test_sources_update_summarises_without_body_text():
    [event] = emit("search_and_read", {"sources": [source()], "research_rounds": 2})
    assert event.name == "sources"
    assert event.data["round"] == 2
    assert event.data["added"] == [
        {"id": 1, "title": "T1", "domain": "a.com", "url": "https://a.com/p1"}
    ]
    assert "body text" not in json.dumps(event.data), "page text is too big to stream"


def test_write_update_carries_the_draft():
    [event] = emit("write", {"drafts": [Draft(version=2, report="v2 [1]")]})
    assert (event.name, event.data) == ("draft", {"version": 2, "report": "v2 [1]"})


def test_critique_update_carries_scores():
    draft = Draft(version=1, report="r", critique=critique(6))
    [event] = emit("critique", {"drafts": [draft]})
    assert event.name == "critique"
    assert event.data["version"] == 1
    assert event.data["critique"]["overall"] == 6


def test_unjudged_draft_emits_nothing():
    assert emit("critique", {"drafts": [Draft(version=1, report="r")]}) == []


def test_unknown_node_emits_nothing():
    assert emit("finalize", {"report": "r"}) == []


def test_final_event_lists_only_cited_sources():
    state = {
        "report": "Claim [2].\n\n## Sources\n[2] ...",
        "sources": [source(1), source(2, "b.com")],
        "drafts": [Draft(version=1, report="Claim [2].", critique=critique(9))],
    }
    event = events.final_event(state, elapsed_s=12.34)
    assert event.name == "final"
    assert [s["id"] for s in event.data["sources"]] == [2]
    assert event.data["score"] == 9
    assert event.data["elapsed_s"] == 12.3
    assert len(event.data["drafts"]) == 1


def test_final_event_survives_a_run_with_no_drafts():
    event = events.final_event({"report": "", "sources": []}, elapsed_s=1.0)
    assert event.data["score"] is None


def test_sse_framing():
    text = events.to_sse(events.run_started("abc"))
    assert text == 'event: run\ndata: {"id": "abc"}\n\n'


def test_error_event():
    assert events.failed("boom").data == {"message": "boom"}


def test_heartbeat_is_a_comment():
    assert events.heartbeat().startswith(":")
