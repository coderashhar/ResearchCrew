"""Web search and reading.

Plain functions rather than LLM tool-calling agents: which queries to run
is decided by the planner, and which pages to read is a ranking problem,
so neither needs a model in the loop.
"""

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
