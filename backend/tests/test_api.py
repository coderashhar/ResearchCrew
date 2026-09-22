import json
import time
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

import main
from research.config import Settings
from research.db import RunRecord
from research.schemas import Critique, Draft, SearchQuery, Source

SETTINGS = Settings(
    mistral_api_key="m", tavily_api_key="t", database_url="postgresql://x", client_hash_salt="s"
)


def critique(overall=8):
    return Critique(
        accuracy=overall, coverage=overall, citation_quality=overall,
        clarity=overall, recency=overall, overall=overall,
    )


class FakeStore:
    """In-memory stand-in for RunStore, same method signatures."""

    def __init__(self):
        self.runs: dict[UUID, dict] = {}
        self.hourly = 0

    def runs_in_last_hour(self, client_hash):
        return self.hourly

    def create_run(self, topic, client_hash=None):
        run_id = uuid4()
        self.runs[run_id] = {"topic": topic, "status": "running", "client_hash": client_hash}
        return run_id

    def finish_run(self, run_id, *, report, score, drafts, sources, queries, elapsed_s):
        self.runs[run_id] |= {
            "status": "done", "final_report": report, "final_score": score,
            "drafts": list(drafts), "sources": list(sources), "queries": list(queries),
            "elapsed_s": elapsed_s,
        }

    def fail_run(self, run_id, error):
        self.runs[run_id] |= {"status": "error", "error": error}

    def get_run(self, run_id):
        row = self.runs.get(run_id)
        if row is None:
            return None
        from datetime import datetime, timezone

        return RunRecord(id=run_id, created_at=datetime.now(timezone.utc), **row)

    def only_run(self):
        return next(iter(self.runs.values()))


class FakeGraph:
    """Replays a scripted run; `delay` simulates a slow agent step."""

    def __init__(self, error=None, delay=0.0):
        self.error, self.delay = error, delay

    def stream(self, inputs, stream_mode=None):
        source = Source(id=1, url="https://a.com/p", title="A", domain="a.com", content="body")
        draft = Draft(version=1, report="Report [1].", critique=critique(9))
        yield "updates", {"plan": {"queries": [SearchQuery(query="q", topic="general")]}}
        yield "updates", {"search_and_read": {"sources": [source], "research_rounds": 1}}
        if self.delay:
            time.sleep(self.delay)
        if self.error:
            raise RuntimeError(self.error)
        yield "updates", {"write": {"drafts": [Draft(version=1, report="Report [1].")]}}
        yield "updates", {"critique": {"drafts": [draft]}}
        yield "values", {
            "report": "Report [1].\n\n## Sources\n[1] A",
            "sources": [source],
            "drafts": [draft],
            "queries": [SearchQuery(query="q", topic="general")],
        }


@pytest.fixture
def store():
    return FakeStore()


def client(store, graph=None):
    app = main.create_app(
        settings=SETTINGS, store=store, graph_factory=lambda s: graph or FakeGraph()
    )
    return TestClient(app)


def sse_events(text: str) -> list[tuple[str, dict]]:
    parsed = []
    for block in text.split("\n\n"):
        if block.startswith("event: "):
            name, data = block.split("\n", 1)
            parsed.append((name.removeprefix("event: "), json.loads(data.removeprefix("data: "))))
    return parsed


def run(client_, topic="mRNA vaccines"):
    response = client_.post("/api/research", json={"topic": topic})
    return response, sse_events(response.text)


# --- streaming ------------------------------------------------------------


def test_health():
    assert client(FakeStore()).get("/api/health").json() == {"status": "ok"}


def test_events_arrive_in_order(store):
    response, stream = run(client(store))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert [name for name, _ in stream] == ["run", "plan", "sources", "draft", "critique", "final"]


def test_run_event_matches_the_saved_run(store):
    _, stream = run(client(store))
    run_id = UUID(stream[0][1]["id"])
    assert run_id in store.runs


def test_finished_run_is_saved_with_report_and_score(store):
    _, stream = run(client(store))
    final = dict(stream)["final"]
    saved = store.only_run()
    assert saved["status"] == "done"
    assert saved["final_report"] == final["report"] == "Report [1].\n\n## Sources\n[1] A"
    assert saved["final_score"] == 9
    assert [s.domain for s in saved["sources"]] == ["a.com"]
    assert saved["elapsed_s"] >= 0


def test_graph_failure_sends_an_error_event_and_marks_the_run(store):
    _, stream = run(client(store, FakeGraph(error="Tavily is down")))
    assert [name for name, _ in stream][-1] == "error"
    assert dict(stream)["error"]["message"] == "Tavily is down"
    assert store.only_run()["status"] == "error"
    assert "final" not in dict(stream)


def test_heartbeat_keeps_a_slow_run_alive(store, monkeypatch):
    monkeypatch.setattr(main, "HEARTBEAT_S", 0.05)
    response = client(store, FakeGraph(delay=0.2)).post("/api/research", json={"topic": "T"})
    assert ": keep-alive" in response.text
    assert [name for name, _ in sse_events(response.text)][-1] == "final"


# --- validation and limits ------------------------------------------------


@pytest.mark.parametrize("topic", ["", " " * 0, "x" * 301])
def test_invalid_topic_is_rejected(store, topic):
    assert client(store).post("/api/research", json={"topic": topic}).status_code == 422


def test_rate_limit_blocks_the_sixth_run_in_an_hour(store):
    store.hourly = main.MAX_RUNS_PER_HOUR
    response = client(store).post("/api/research", json={"topic": "T"})
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "3600"
    assert store.runs == {}, "a blocked request must not create a run"


def test_forwarded_address_identifies_the_caller(store):
    seen = []
    store.runs_in_last_hour = lambda h: (seen.append(h), 0)[1]
    client(store).post(
        "/api/research", json={"topic": "T"}, headers={"x-forwarded-for": "203.0.113.7, 10.0.0.1"}
    )
    assert seen and "203.0.113.7" not in seen[0], "the address must be hashed"


# --- reading a saved run --------------------------------------------------


def test_saved_run_is_served_by_id(store):
    _, stream = run(client(store))
    run_id = stream[0][1]["id"]
    body = client(store).get(f"/api/runs/{run_id}").json()
    assert body["final_report"].startswith("Report [1].")
    assert body["drafts"][0]["critique"]["overall"] == 9


def test_unknown_run_is_404(store):
    assert client(store).get(f"/api/runs/{uuid4()}").status_code == 404


def test_malformed_run_id_is_422(store):
    assert client(store).get("/api/runs/not-a-uuid").status_code == 422
