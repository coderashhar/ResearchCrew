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


LOOPBACK = {"127.0.0.1", "::1", "localhost", ""}


@pytest.fixture(autouse=True)
def _block_network(request, monkeypatch):
    """Fail fast on any outbound connection unless the test is integration.

    Unit tests must mock Tavily, Mistral and Postgres: a test that
    silently reaches the network is slow, flaky and spends API credit.
    Loopback stays open, since TestClient and asyncio use it internally.
    """
    if request.node.get_closest_marker("integration"):
        return

    real_connect = socket.socket.connect
    real_create = socket.create_connection

    def host_of(address):
        return address[0] if isinstance(address, tuple) else str(address)

    def guard(address):
        if host_of(address) not in LOOPBACK:
            raise NetworkBlockedError(
                f"Network access in unit test {request.node.nodeid}; "
                "mock the client or mark the test @pytest.mark.integration"
            )

    def connect(self, address):
        guard(address)
        return real_connect(self, address)

    def create_connection(address, *args, **kwargs):
        guard(address)
        return real_create(address, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket, "create_connection", create_connection)
