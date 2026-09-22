"""Storage for research runs.

A run costs a minute of model and search time, so it is saved: the API
returns a permalink, and the UI can reopen a report instead of paying to
regenerate it.

Run ``python -m research.db migrate`` to create the schema.
"""

import hashlib
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID, uuid4

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool
from pydantic import BaseModel

from research.schemas import Draft, SearchQuery, Source

MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"

# Neon suspends an idle branch; waking it measured ~3s and can run longer
# after a night idle. Postgres' default 5s connect timeout reports that as
# "could not connect", which reads as an outage rather than a cold start.
CONNECT_TIMEOUT_S = 30


class RunRecord(BaseModel):
    id: UUID
    topic: str
    created_at: datetime
    status: str
    final_report: str | None = None
    final_score: int | None = None
    drafts: list[Draft] = []
    sources: list[Source] = []
    queries: list[SearchQuery] = []
    elapsed_s: float | None = None
    error: str | None = None


def normalize_dsn(url: str, connect_timeout: int = CONNECT_TIMEOUT_S) -> str:
    """Guarantee a connect timeout long enough for a sleeping Neon branch."""
    parts = urlsplit(url)
    params = dict(parse_qsl(parts.query))
    params.setdefault("connect_timeout", str(connect_timeout))
    return urlunsplit(parts._replace(query=urlencode(params)))


def client_hash(ip: str, salt: str = "") -> str:
    """Identify a client for rate limiting without storing their address."""
    return hashlib.sha256(f"{salt}{ip}".encode()).hexdigest()


def _dump(items: Iterable[BaseModel]) -> Jsonb:
    return Jsonb([i.model_dump(mode="json") for i in items])


class RunStore:
    """Every query lives here; nothing else in the app talks to Postgres."""

    def __init__(self, dsn: str, min_size: int = 0, max_size: int = 4):
        self.pool = ConnectionPool(
            normalize_dsn(dsn),
            min_size=min_size,
            max_size=max_size,
            open=True,
            kwargs={"row_factory": dict_row},
        )

    def close(self) -> None:
        self.pool.close()

    def migrate(self) -> None:
        """Apply the schema. Idempotent, so it is safe on every boot."""
        sql = "\n".join(p.read_text() for p in sorted(MIGRATIONS.glob("*.sql")))
        with self.pool.connection() as conn:
            conn.execute(sql)

    def create_run(self, topic: str, client_hash: str | None = None) -> UUID:
        run_id = uuid4()
        with self.pool.connection() as conn:
            conn.execute(
                "insert into runs (id, topic, status, client_hash)"
                " values (%s, %s, 'running', %s)",
                (run_id, topic, client_hash),
            )
        return run_id

    def finish_run(
        self,
        run_id: UUID,
        *,
        report: str,
        score: int | None,
        drafts: Iterable[Draft],
        sources: Iterable[Source],
        queries: Iterable[SearchQuery],
        elapsed_s: float,
    ) -> None:
        with self.pool.connection() as conn:
            conn.execute(
                "update runs set status = 'done', final_report = %s, final_score = %s,"
                " drafts = %s, sources = %s, queries = %s, elapsed_s = %s"
                " where id = %s",
                (
                    report,
                    score,
                    _dump(drafts),
                    _dump(sources),
                    _dump(queries),
                    elapsed_s,
                    run_id,
                ),
            )

    def fail_run(self, run_id: UUID, error: str) -> None:
        with self.pool.connection() as conn:
            conn.execute(
                "update runs set status = 'error', error = %s where id = %s",
                (error[:2000], run_id),
            )

    def get_run(self, run_id: UUID) -> RunRecord | None:
        with self.pool.connection() as conn:
            row = conn.execute("select * from runs where id = %s", (run_id,)).fetchone()
        return RunRecord.model_validate(row) if row else None

    def runs_in_last_hour(self, client_hash: str) -> int:
        with self.pool.connection() as conn:
            row = conn.execute(
                "select count(*) as n from runs"
                " where client_hash = %s and created_at > now() - interval '1 hour'",
                (client_hash,),
            ).fetchone()
        return row["n"]


def main(argv: list[str] | None = None) -> int:
    from research.config import get_settings, load_env

    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] != ["migrate"]:
        print("usage: python -m research.db migrate")
        return 2

    load_env()
    dsn = get_settings().database_url
    if not dsn:
        print("DATABASE_URL is not set")
        return 2

    store = RunStore(dsn)
    try:
        store.migrate()
    finally:
        store.close()
    print("Migrations applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
