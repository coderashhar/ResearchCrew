import socket

import pytest

# Keys the app reads. Cleared for every test so a developer's real .env or
# shell exports can never leak into assertions or trigger paid API calls.
APP_ENV_VARS = (
    "MISTRAL_API_KEY",
    "TAVILY_API_KEY",
    "DATABASE_URL",
    "WRITER_MODEL",
    "CRITIC_MODEL",
    "CLIENT_HASH_SALT",
    "PASS_SCORE",
    "MAX_REVISIONS",
    "TIME_BUDGET_S",
)


class NetworkBlockedError(RuntimeError):
    pass


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in APP_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _block_network(request, monkeypatch):
    """Fail fast on any real socket unless the test is marked integration.

    Unit tests must mock Tavily, Mistral and Postgres. A test that silently
    reaches the network is slow, flaky and spends real API credit.
    """
    if request.node.get_closest_marker("integration"):
        return

    def guard(*args, **kwargs):
        raise NetworkBlockedError(
            f"Network access in unit test {request.node.nodeid}; "
            "mock the client or mark the test @pytest.mark.integration"
        )

    monkeypatch.setattr(socket, "socket", guard)
    monkeypatch.setattr(socket, "create_connection", guard)
