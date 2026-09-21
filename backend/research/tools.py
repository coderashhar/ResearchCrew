"""Web search and reading.

Plain functions rather than LLM tool-calling agents: which queries to run
is decided by the planner, and which pages to read is a ranking problem,
so neither needs a model in the loop.
"""

from collections.abc import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests
from tavily import TavilyClient
from tavily.errors import TimeoutError as TavilyTimeoutError
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from research.config import Settings
from research.schemas import SearchQuery


def make_client(settings: Settings) -> TavilyClient:
    return TavilyClient(api_key=settings.tavily_api_key)


def _is_transient(exc: BaseException) -> bool:
    """Network blips and 5xx are worth retrying; 4xx (bad key, quota) are not."""
    if isinstance(exc, (TavilyTimeoutError, requests.ConnectionError, requests.Timeout)):
        return True
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        return exc.response.status_code >= 500
    return False


_retry = retry(
    retry=retry_if_exception(_is_transient),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, max=4),
    reraise=True,
)


@_retry
def search(client: TavilyClient, q: SearchQuery, max_results: int = 6) -> list[dict]:
    """Run one planned query. ``days`` is sent only when the plan sets it."""
    params: dict = {"query": q.query, "topic": q.topic, "max_results": max_results}
    if q.days is not None:
        params["days"] = q.days
    return client.search(**params).get("results", [])


def normalize_url(url: str) -> str:
    """Canonical form for duplicate detection: no fragment, no utm_* tracking."""
    parts = urlsplit(url.strip())
    query = urlencode(
        [(k, v) for k, v in parse_qsl(parts.query) if not k.lower().startswith("utm_")]
    )
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, query, ""))


def domain_of(url: str) -> str:
    host = urlsplit(url).netloc.lower().split(":")[0]
    return host.removeprefix("www.")


def select_sources(
    results: Iterable[dict], existing_urls: Iterable[str] = (), n: int = 6
) -> list[dict]:
    """Pick the ``n`` highest-scoring results, at most one per domain.

    One page per domain keeps a single site from dominating the report.
    URLs already read in an earlier round are skipped.
    """
    seen_urls = {normalize_url(u) for u in existing_urls}
    seen_domains: set[str] = set()
    picked: list[dict] = []
    for r in sorted(results, key=lambda r: r.get("score") or 0.0, reverse=True):
        url = r.get("url")
        if not url:
            continue
        norm, domain = normalize_url(url), domain_of(url)
        if norm in seen_urls or domain in seen_domains:
            continue
        seen_urls.add(norm)
        seen_domains.add(domain)
        picked.append(r)
        if len(picked) == n:
            break
    return picked
