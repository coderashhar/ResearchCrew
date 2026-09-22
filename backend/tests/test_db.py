import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from research import db
from research.db import RunRecord, RunStore, client_hash, normalize_dsn
from research.schemas import Critique, Draft, SearchQuery, Source

# --- unit -----------------------------------------------------------------


def test_connect_timeout_added_when_missing():
    dsn = normalize_dsn("postgresql://u:p@host/db?sslmode=require")
    assert "connect_timeout=30" in dsn
    assert "sslmode=require" in dsn


def test_existing_connect_timeout_is_respected():
    dsn = normalize_dsn("postgresql://u:p@host/db?connect_timeout=5")
    assert "connect_timeout=5" in dsn
    assert "connect_timeout=30" not in dsn


def test_connect_timeout_added_to_url_without_query():
    assert normalize_dsn("postgresql://u:p@host/db").endswith("?connect_timeout=30")


def test_client_hash_is_stable_and_hides_the_address():
    ip = "203.0.113.7"
    assert client_hash(ip, "salt") == client_hash(ip, "salt")
    assert ip not in client_hash(ip, "salt")
    assert client_hash(ip, "salt") != client_hash(ip, "other-salt")
    assert client_hash(ip, "salt") != client_hash("203.0.113.8", "salt")


def test_run_record_round_trips_drafts_and_sources():
    critique = Critique(
        accuracy=8, coverage=8, citation_quality=8, clarity=8, recency=8, overall=8
    )
    record = RunRecord(
        id=uuid4(),
        topic="T",
        created_at=datetime.now(timezone.utc),
        status="done",
        final_report="report [1]",
        final_score=8,
        drafts=[Draft(version=1, report="report [1]", critique=critique)],
        sources=[Source(id=1, url="https://a.com", title="A", domain="a.com", content="body")],
        queries=[SearchQuery(query="q", topic="general")],
        elapsed_s=42.5,
    )
    assert RunRecord.model_validate_json(record.model_dump_json()) == record


def test_migrate_command_requires_the_subcommand(capsys):
    assert db.main([]) == 2
    assert "usage:" in capsys.readouterr().out


def test_migrate_command_needs_a_database_url(capsys, monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "m")
    monkeypatch.setenv("TAVILY_API_KEY", "t")
    monkeypatch.setattr(db, "RunStore", lambda *a, **kw: pytest.fail("must not connect"))
    assert db.main(["migrate"]) == 2
    assert "DATABASE_URL" in capsys.readouterr().out


# --- integration ----------------------------------------------------------

pytestmark_needs_db = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="set TEST_DATABASE_URL to a throwaway Neon branch to run these",
)


@pytest.fixture
def store():
    dsn = os.environ["TEST_DATABASE_URL"]
    store = RunStore(dsn, min_size=1)
    store.migrate()
    with store.pool.connection() as conn:
        conn.execute("delete from runs where topic like 'test:%'")
    yield store
    store.close()


@pytest.mark.integration
@pytestmark_needs_db
def test_migrate_is_idempotent(store):
    store.migrate()  # second run must not fail


@pytest.mark.integration
@pytestmark_needs_db
def test_create_finish_and_read_back_a_run(store):
    run_id = store.create_run("test:mRNA", client_hash="hash-a")
    store.finish_run(
        run_id,
        report="final [1]",
        score=9,
        drafts=[Draft(version=1, report="final [1]")],
        sources=[Source(id=1, url="https://a.com", title="A", domain="a.com", content="b")],
        queries=[SearchQuery(query="q", topic="news", days=7)],
        elapsed_s=12.0,
    )

    record = store.get_run(run_id)
    assert record.status == "done"
    assert record.final_report == "final [1]"
    assert record.final_score == 9
    assert [s.domain for s in record.sources] == ["a.com"]
    assert record.queries[0].days == 7
    assert record.elapsed_s == 12.0


@pytest.mark.integration
@pytestmark_needs_db
def test_failed_run_keeps_the_error(store):
    run_id = store.create_run("test:boom")
    store.fail_run(run_id, "Tavily timed out")
    record = store.get_run(run_id)
    assert (record.status, record.error) == ("error", "Tavily timed out")
    assert record.final_report is None


@pytest.mark.integration
@pytestmark_needs_db
def test_unknown_run_is_none(store):
    assert store.get_run(uuid4()) is None


@pytest.mark.integration
@pytestmark_needs_db
def test_hourly_count_is_per_client_and_recent_only(store):
    store.create_run("test:a", client_hash="hash-a")
    store.create_run("test:a2", client_hash="hash-a")
    store.create_run("test:b", client_hash="hash-b")
    old = store.create_run("test:old", client_hash="hash-a")
    with store.pool.connection() as conn:
        conn.execute(
            "update runs set created_at = %s where id = %s",
            (datetime.now(timezone.utc) - timedelta(hours=2), old),
        )

    assert store.runs_in_last_hour("hash-a") == 2
    assert store.runs_in_last_hour("hash-b") == 1
    assert store.runs_in_last_hour("hash-none") == 0
