import pytest
from langchain_core.runnables import RunnableLambda
from rich.console import Console

import cli
from research.agents import Chains
from research.config import Settings
from research.graph import ResearchState, ResearchTools, build_graph, route_after_critique
from research.schemas import Critique, Draft, SearchPlan, SearchQuery, Source

SETTINGS = Settings(mistral_api_key="m", tavily_api_key="t")


def critique(overall=8, **kw):
    scores = dict(accuracy=overall, coverage=overall, citation_quality=overall, clarity=overall, recency=overall)
    return Critique(overall=overall, **scores, **kw)


def state(**kw) -> ResearchState:
    base: ResearchState = {"topic": "T", "started_at": 100.0}
    return {**base, **kw}


def drafts(*critiques) -> list[Draft]:
    return [Draft(version=i + 1, report=f"draft {i + 1}", critique=c) for i, c in enumerate(critiques)]


# --- routing --------------------------------------------------------------


@pytest.mark.parametrize(
    "case, st, now, expected",
    [
        ("passing score finishes", state(drafts=drafts(critique(8))), 110.0, "finalize"),
        ("weak score rewrites", state(drafts=drafts(critique(5))), 110.0, "write"),
        (
            "weak score with missing evidence researches more",
            state(drafts=drafts(critique(5, needs_more_research=True)), research_rounds=0),
            110.0,
            "search_and_read",
        ),
        (
            "one follow-up round is allowed",
            state(drafts=drafts(critique(5, needs_more_research=True)), research_rounds=1),
            110.0,
            "search_and_read",
        ),
        (
            "a second follow-up rewrites instead",
            state(drafts=drafts(critique(5, needs_more_research=True)), research_rounds=2),
            110.0,
            "write",
        ),
        (
            "revision budget spent finishes",
            state(drafts=drafts(critique(5), critique(5), critique(5)), revisions=2),
            110.0,
            "finalize",
        ),
        ("time budget spent finishes", state(drafts=drafts(critique(5))), 331.0, "finalize"),
        ("no critique finishes", state(drafts=[Draft(version=1, report="r")]), 110.0, "finalize"),
    ],
)
def test_route_after_critique(case, st, now, expected):
    assert route_after_critique(st, SETTINGS, now) == expected, case


def test_time_budget_is_measured_from_the_start_of_the_run():
    st = state(drafts=drafts(critique(5)), started_at=100.0)
    assert route_after_critique(st, SETTINGS, 100.0 + SETTINGS.time_budget_s) == "write"
    assert route_after_critique(st, SETTINGS, 101.0 + SETTINGS.time_budget_s) == "finalize"


# --- fakes ----------------------------------------------------------------


def fake_chains(reports, critiques, plan=None):
    plan = plan or SearchPlan(queries=[SearchQuery(query="q1", topic="general")])
    seen = {"write": 0, "critique": 0}

    def write(data):
        seen["write"] += 1
        return reports[min(seen["write"], len(reports)) - 1]

    def judge(data):
        seen["critique"] += 1
        return critiques[min(seen["critique"], len(critiques)) - 1]

    chains = Chains(
        planner=RunnableLambda(lambda d: plan),
        writer=RunnableLambda(write),
        critic=RunnableLambda(judge),
    )
    return chains


def result(url, score=0.9, title=None):
    return {"url": url, "title": title or url, "content": "snippet", "score": score}


def fake_tools(pages_per_query, fail_urls=()):
    """pages_per_query: query string -> list of URLs that query finds."""
    searched: list[SearchQuery] = []

    def search(q: SearchQuery) -> list[dict]:
        searched.append(q)
        return [result(u) for u in pages_per_query.get(q.query, [])]

    def read(results, start_id):
        sources = []
        for r in results:
            if r["url"] in fail_urls:
                continue  # a page that could not be read is skipped
            sources.append(
                Source(
                    id=start_id + len(sources),
                    url=r["url"],
                    title=r["title"],
                    domain=r["url"].split("/")[2],
                    content=f"body of {r['url']}",
                    score=r["score"],
                )
            )
        return sources

    t = ResearchTools(search=search, read=read)
    t.searched = searched  # type: ignore[attr-defined]
    return t


def run(chains, tools_, settings=SETTINGS, topic="T"):
    return build_graph(chains, tools_, settings).invoke({"topic": topic})


# --- full runs ------------------------------------------------------------


def test_weak_draft_is_revised_and_final_report_lists_only_cited_sources():
    chains = fake_chains(
        reports=["Thin claim [1].", "Better claim [1] and [2]."],
        critiques=[critique(5), critique(8)],
    )
    tools_ = fake_tools({"q1": ["https://a.com/p", "https://b.com/p", "https://c.com/p"]})

    final = run(chains, tools_)

    assert [(d.version, d.critique.overall) for d in final["drafts"]] == [(1, 5), (2, 8)]
    assert final["revisions"] == 1
    assert final["report"].startswith("Better claim [1] and [2].")
    assert "## Sources" in final["report"]
    assert "[1] [https://a.com/p]" in final["report"]
    assert "c.com" not in final["report"], "uncited source must not be listed"


def test_citations_to_missing_sources_are_stripped():
    chains = fake_chains(reports=["Real [1]. Invented [9]."], critiques=[critique(9)])
    final = run(chains, fake_tools({"q1": ["https://a.com/p"]}))
    assert "[9]" not in final["report"]
    assert "Invented." in final["report"]


def test_more_research_adds_sources_and_keeps_numbering_continuous():
    chains = fake_chains(
        reports=["v1 [1]", "v2 [1] [2]"],
        critiques=[critique(5, needs_more_research=True, followup_queries=["q2"]), critique(9)],
    )
    tools_ = fake_tools({"q1": ["https://a.com/p"], "q2": ["https://b.com/p"]})

    final = run(chains, tools_)

    assert [q.query for q in tools_.searched] == ["q1", "q2"]
    assert [(s.id, s.domain) for s in final["sources"]] == [(1, "a.com"), (2, "b.com")]
    assert final["research_rounds"] == 2


def test_already_read_urls_are_not_read_again():
    chains = fake_chains(
        reports=["v1 [1]", "v2 [1]"],
        critiques=[critique(5, needs_more_research=True, followup_queries=["q2"]), critique(9)],
    )
    tools_ = fake_tools({"q1": ["https://a.com/p"], "q2": ["https://a.com/p", "https://b.com/p"]})
    final = run(chains, tools_)
    assert [s.url for s in final["sources"]] == ["https://a.com/p", "https://b.com/p"]


def test_unreadable_page_does_not_stop_the_run():
    chains = fake_chains(reports=["v1 [1]"], critiques=[critique(9)])
    tools_ = fake_tools(
        {"q1": ["https://a.com/p", "https://b.com/p"]}, fail_urls=["https://a.com/p"]
    )
    final = run(chains, tools_)
    assert [s.domain for s in final["sources"]] == ["b.com"]
    assert final["report"].startswith("v1 [1]")


def test_revision_budget_stops_the_loop():
    chains = fake_chains(reports=["bad [1]"], critiques=[critique(4)])
    final = run(chains, fake_tools({"q1": ["https://a.com/p"]}))
    assert len(final["drafts"]) == SETTINGS.max_revisions + 1
    assert final["revisions"] == SETTINGS.max_revisions


def test_revision_prompt_receives_previous_draft_and_gaps():
    seen: list[dict] = []
    chains = fake_chains(reports=["v1 [1]", "v2 [1]"], critiques=[critique(5, gaps=["no dates"]), critique(9)])
    writer = chains.writer

    def spy(data):
        seen.append(data)
        return writer.invoke(data)

    run(Chains(planner=chains.planner, writer=RunnableLambda(spy), critic=chains.critic),
        fake_tools({"q1": ["https://a.com/p"]}))

    assert seen[0]["previous_draft"] == ""
    assert seen[1]["previous_draft"] == "v1 [1]"
    assert "no dates" in seen[1]["critique_notes"]
    assert "5/10" in seen[1]["critique_notes"]


def test_report_without_citations_has_no_sources_section():
    chains = fake_chains(reports=["No citations at all."], critiques=[critique(9)])
    final = run(chains, fake_tools({"q1": ["https://a.com/p"]}))
    assert final["report"] == "No citations at all."


# --- cli ------------------------------------------------------------------


def test_cli_streams_every_node_and_returns_the_report():
    chains = fake_chains(reports=["v1 [1]"], critiques=[critique(9)])
    graph = build_graph(chains, fake_tools({"q1": ["https://a.com/p"]}), SETTINGS)
    console = Console(record=True, width=100)

    report = cli.stream_run(graph, "T", console)

    output = console.export_text()
    for label in cli.LABELS.values():
        assert label in output
    assert "score 9/10" in output
    assert report.startswith("v1 [1]")


def test_cli_without_topic_exits_with_error(monkeypatch):
    monkeypatch.setattr(Console, "input", lambda self, *a, **kw: "")
    assert cli.main([]) == 2
