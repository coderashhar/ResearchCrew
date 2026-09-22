"""HTTP API for research runs.

A run takes minutes, so POST /api/research streams what the agents are
doing as server-sent events instead of holding one silent response open.
Every run is saved, and GET /api/runs/{id} serves it afterwards.
"""

import logging
import queue
import threading
import time
from typing import Any, Callable, Iterator
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from research import events
from research.agents import build_chains
from research.config import Settings, get_settings, load_env
from research.db import RunStore, client_hash

from research.graph import ResearchTools, build_graph
from research.tools import make_client

log = logging.getLogger(__name__)

HEARTBEAT_S = 10.0
MAX_RUNS_PER_HOUR = 5
SENTINEL = object()

GraphFactory = Callable[[Settings], Any]


class ResearchRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=300)


def default_graph(settings: Settings) -> Any:
    return build_graph(
        build_chains(settings),
        ResearchTools.from_client(make_client(settings)),
        settings,
    )


def client_ip(request: Request) -> str:
    """Vercel terminates TLS upstream, so the socket peer is a proxy."""
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or (request.client.host if request.client else "")


def _run_events(graph: Any, topic: str, out: queue.Queue) -> None:
    """Drive the graph on a worker thread, pushing events as they happen."""
    try:
        for mode, payload in graph.stream(
            {"topic": topic}, stream_mode=["updates", "values"]
        ):
            if mode == "updates":
                for node, state in payload.items():
                    for event in events.from_update(node, state):
                        out.put(event)
            else:
                out.put(("state", payload))
    except Exception as exc:  # the client gets an error event, not a dead stream
        log.exception("Research run failed")
        out.put(events.failed(str(exc)))
    finally:
        out.put(SENTINEL)


def create_app(
    settings: Settings | None = None,
    store: RunStore | None = None,
    graph_factory: GraphFactory = default_graph,
) -> FastAPI:
    app = FastAPI(title="ResearchCrew API")

    def get_store() -> RunStore:
        nonlocal store
        if store is None:
            if not settings or not settings.database_url:
                raise HTTPException(503, "DATABASE_URL is not configured")
            store = RunStore(settings.database_url)
        return store

    def get_config() -> Settings:
        nonlocal settings
        if settings is None:
            load_env()
            settings = get_settings()
        return settings

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/api/research")
    def research(
        body: ResearchRequest,
        request: Request,
        config: Settings = Depends(get_config),
        runs: RunStore = Depends(get_store),
    ) -> StreamingResponse:
        caller = client_hash(client_ip(request), config.client_hash_salt)
        if runs.runs_in_last_hour(caller) >= MAX_RUNS_PER_HOUR:
            raise HTTPException(
                429,
                f"At most {MAX_RUNS_PER_HOUR} runs per hour.",
                headers={"Retry-After": "3600"},
            )

        run_id = runs.create_run(body.topic, client_hash=caller)
        stream = _stream_run(graph_factory(config), runs, run_id, body.topic)
        return StreamingResponse(
            stream,
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: UUID, runs: RunStore = Depends(get_store)) -> dict:
        record = runs.get_run(run_id)
        if record is None:
            raise HTTPException(404, "No such run")
        return record.model_dump(mode="json")

    return app


def _stream_run(graph: Any, runs: RunStore, run_id: UUID, topic: str) -> Iterator[str]:
    started = time.monotonic()
    out: queue.Queue = queue.Queue()
    worker = threading.Thread(target=_run_events, args=(graph, topic, out), daemon=True)
    worker.start()

    yield events.to_sse(events.run_started(str(run_id)))

    state: dict = {}
    failure: str | None = None
    while True:
        try:
            item = out.get(timeout=HEARTBEAT_S)
        except queue.Empty:
            # Agents can work for a minute without producing an event; an
            # idle HTTP/1.1 connection may be closed in the meantime.
            yield events.heartbeat()
            continue

        if item is SENTINEL:
            break
        if isinstance(item, tuple):
            state = item[1]
            continue
        if item.name == "error":
            failure = item.data["message"]
        yield events.to_sse(item)

    elapsed = time.monotonic() - started
    if failure is not None:
        runs.fail_run(run_id, failure)
        return

    final = events.final_event(state, elapsed)
    runs.finish_run(
        run_id,
        report=final.data["report"],
        score=final.data["score"],
        drafts=state.get("drafts", []),
        sources=state.get("sources", []),
        queries=state.get("queries", []),
        elapsed_s=elapsed,
    )
    yield events.to_sse(final)


app = create_app()
