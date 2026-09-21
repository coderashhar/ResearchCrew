"""Web search and reading.

Plain functions rather than LLM tool-calling agents: which queries to run
is decided by the planner, and which pages to read is a ranking problem,
so neither needs a model in the loop.
"""

import logging
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
from tavily.errors import TimeoutError as TavilyTimeoutError
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from research.config import Settings
from research.schemas import SearchQuery, Source

log = logging.getLogger(__name__)

MAX_SOURCE_CHARS = 4000


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


@_retry
def _extract(client: TavilyClient, urls: list[str]) -> dict:
    return client.extract(urls, format="markdown")


def _scrape_fallback(url: str) -> str:
    """Plain HTTP + BeautifulSoup, for pages Tavily could not extract."""
    resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    if not text:
        raise ValueError("page has no text")
    return text


def _try_scrape(url: str) -> str | None:
    try:
        return _scrape_fallback(url)
    except Exception as exc:  # any failure just drops this one source
        log.warning("Skipping source %s: %s", url, exc)
        return None


def read_sources(
    client: TavilyClient,
    results: list[dict],
    start_id: int = 1,
    max_chars: int = MAX_SOURCE_CHARS,
) -> list[Source]:
    """Read selected results into numbered sources.

    One batched Tavily extract call; pages it fails on are scraped
    directly in parallel. A page that fails both ways is skipped rather
    than failing the run. Ids are assigned in ``results`` order, so the
    best-ranked source gets the lowest number.
    """
    urls = [r["url"] for r in results]
    if not urls:
        return []

    content: dict[str, str] = {}
    try:
        for item in _extract(client, urls).get("results", []):
            if item.get("raw_content"):
                content[item["url"]] = item["raw_content"]
    except Exception as exc:
        log.warning("Tavily extract failed, scraping all %d pages: %s", len(urls), exc)

    missing = [u for u in urls if u not in content]
    if missing:
        with ThreadPoolExecutor(max_workers=6) as pool:
            for url, text in zip(missing, pool.map(_try_scrape, missing)):
                if text:
                    content[url] = text

    sources: list[Source] = []
    for r in results:
        text = content.get(r["url"])
        if not text:
            continue
        sources.append(
            Source(
                id=start_id + len(sources),
                url=r["url"],
                title=r.get("title") or r["url"],
                domain=domain_of(r["url"]),
                content=text[:max_chars],
                score=r.get("score") or 0.0,
            )
        )
    return sources
