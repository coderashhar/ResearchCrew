from unittest.mock import MagicMock

import pytest
import requests
from tavily.errors import InvalidAPIKeyError
from tavily.errors import TimeoutError as TavilyTimeoutError
from tenacity import wait_none

from research import tools
from research.schemas import SearchQuery


@pytest.fixture(autouse=True)
def _no_retry_wait(monkeypatch):
    monkeypatch.setattr(tools.search.retry, "wait", wait_none())


def http_error(status):
    resp = requests.Response()
    resp.status_code = status
    return requests.HTTPError(response=resp)


def client_returning(*outcomes):
    client = MagicMock()
    client.search.side_effect = list(outcomes)
    return client


OK = {"results": [{"url": "https://a.com", "title": "A", "content": "c", "score": 0.9}]}


# --- search ---------------------------------------------------------------


def test_general_query_sends_topic_without_days():
    client = client_returning(OK)
    results = tools.search(client, SearchQuery(query="mRNA vaccines", topic="general"))
    client.search.assert_called_once_with(query="mRNA vaccines", topic="general", max_results=6)
    assert results == OK["results"]


def test_news_query_sends_days():
    client = client_returning(OK)
    tools.search(client, SearchQuery(query="AI Act", topic="news", days=14), max_results=4)
    client.search.assert_called_once_with(query="AI Act", topic="news", max_results=4, days=14)


def test_missing_results_key_returns_empty_list():
    assert tools.search(client_returning({}), SearchQuery(query="q", topic="general")) == []


@pytest.mark.parametrize(
    "transient", [TavilyTimeoutError(5), requests.ConnectionError(), http_error(503)]
)
def test_retries_transient_errors_then_succeeds(transient):
    client = client_returning(transient, transient, OK)
    assert tools.search(client, SearchQuery(query="q", topic="general")) == OK["results"]
    assert client.search.call_count == 3


def test_gives_up_after_three_attempts():
    client = client_returning(*[TavilyTimeoutError(5)] * 4)
    with pytest.raises(TavilyTimeoutError):
        tools.search(client, SearchQuery(query="q", topic="general"))
    assert client.search.call_count == 3


@pytest.mark.parametrize("permanent", [InvalidAPIKeyError("bad key"), http_error(404)])
def test_does_not_retry_permanent_errors(permanent):
    client = client_returning(permanent, OK)
    with pytest.raises(type(permanent)):
        tools.search(client, SearchQuery(query="q", topic="general"))
    assert client.search.call_count == 1


# --- select_sources -------------------------------------------------------


def result(url, score, title="t"):
    return {"url": url, "title": title, "content": "c", "score": score}


def test_same_domain_keeps_higher_score():
    picked = tools.select_sources(
        [result("https://a.com/low", 0.2), result("https://www.a.com/high", 0.9)]
    )
    assert [r["url"] for r in picked] == ["https://www.a.com/high"]


def test_tracking_params_and_fragments_collapse():
    picked = tools.select_sources(
        [
            result("https://a.com/post?utm_source=x", 0.9),
            result("https://a.com/post#section", 0.8),
        ]
    )
    assert len(picked) == 1


def test_existing_urls_excluded():
    picked = tools.select_sources(
        [result("https://a.com/p", 0.9), result("https://b.com/p", 0.5)],
        existing_urls=["https://a.com/p/?utm_medium=y"],
    )
    assert [r["url"] for r in picked] == ["https://b.com/p"]


def test_ranked_by_score_and_capped_at_n():
    results = [result(f"https://s{i}.com", i / 10) for i in range(10)]
    picked = tools.select_sources(results, n=3)
    assert [r["url"] for r in picked] == ["https://s9.com", "https://s8.com", "https://s7.com"]


def test_missing_url_or_score_is_tolerated():
    picked = tools.select_sources([{"title": "no url"}, {"url": "https://a.com"}])
    assert [r["url"] for r in picked] == ["https://a.com"]


def test_normalize_keeps_meaningful_query_params():
    assert tools.normalize_url("https://A.com/x/?id=3&utm_campaign=z#top") == "https://a.com/x?id=3"


# --- read_sources ---------------------------------------------------------

A, B, C = (result(f"https://{d}.com/p", s, title=d.upper()) for d, s in [("a", 0.9), ("b", 0.8), ("c", 0.7)])


def extract_client(extracted, failed=()):
    client = MagicMock()
    client.extract.return_value = {
        "results": [{"url": u, "raw_content": text} for u, text in extracted.items()],
        "failed_results": [{"url": u, "error": "blocked"} for u in failed],
    }
    return client


@pytest.fixture
def scrape(monkeypatch):
    """Replace the direct-HTTP fallback; URLs missing from .pages fail."""
    calls = []
    pages: dict[str, str] = {}

    def fake(url):
        calls.append(url)
        if url not in pages:
            raise requests.HTTPError("403")
        return pages[url]

    monkeypatch.setattr(tools, "_scrape_fallback", fake)
    fake.calls, fake.pages = calls, pages
    return fake


def test_extract_success_numbers_from_start_id(scrape):
    client = extract_client({A["url"]: "alpha", B["url"]: "beta"})
    sources = tools.read_sources(client, [A, B], start_id=4)
    client.extract.assert_called_once_with([A["url"], B["url"]], format="markdown")
    assert [(s.id, s.title, s.domain, s.content) for s in sources] == [
        (4, "A", "a.com", "alpha"),
        (5, "B", "b.com", "beta"),
    ]
    assert scrape.calls == []


def test_failed_url_uses_scrape_fallback(scrape):
    scrape.pages[B["url"]] = "beta from html"
    client = extract_client({A["url"]: "alpha"}, failed=[B["url"]])
    sources = tools.read_sources(client, [A, B])
    assert scrape.calls == [B["url"]]
    assert [s.content for s in sources] == ["alpha", "beta from html"]


def test_double_failure_skips_source_and_keeps_numbering_dense(scrape):
    client = extract_client({A["url"]: "alpha", C["url"]: "gamma"}, failed=[B["url"]])
    sources = tools.read_sources(client, [A, B, C])
    assert [(s.id, s.url) for s in sources] == [(1, A["url"]), (2, C["url"])]


def test_empty_extracted_content_falls_back(scrape):
    scrape.pages[A["url"]] = "scraped"
    sources = tools.read_sources(extract_client({A["url"]: ""}), [A])
    assert [s.content for s in sources] == ["scraped"]


def test_extract_outage_scrapes_everything(scrape, monkeypatch):
    monkeypatch.setattr(tools._extract.retry, "wait", wait_none())
    scrape.pages.update({A["url"]: "alpha", B["url"]: "beta"})
    client = MagicMock()
    client.extract.side_effect = TavilyTimeoutError(30)
    sources = tools.read_sources(client, [A, B])
    assert client.extract.call_count == 3
    assert [s.content for s in sources] == ["alpha", "beta"]


def test_content_truncated_to_4000_chars(scrape):
    sources = tools.read_sources(extract_client({A["url"]: "x" * 10_000}), [A])
    assert len(sources[0].content) == 4000


def test_no_results_makes_no_calls():
    client = MagicMock()
    assert tools.read_sources(client, []) == []
    client.extract.assert_not_called()


def test_scrape_fallback_strips_page_chrome(monkeypatch):
    resp = MagicMock(text="<html><nav>menu</nav><script>x()</script><p>Body text</p></html>")
    monkeypatch.setattr(tools.requests, "get", lambda *a, **kw: resp)
    assert tools._scrape_fallback("https://a.com") == "Body text"


def test_scrape_fallback_rejects_empty_page(monkeypatch):
    resp = MagicMock(text="<html><script>only()</script></html>")
    monkeypatch.setattr(tools.requests, "get", lambda *a, **kw: resp)
    with pytest.raises(ValueError):
        tools._scrape_fallback("https://a.com")
