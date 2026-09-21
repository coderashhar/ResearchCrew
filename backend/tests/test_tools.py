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
