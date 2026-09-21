import os
import socket

import pytest

from tests.conftest import NetworkBlockedError


def test_network_is_blocked_in_unit_tests():
    with pytest.raises(NetworkBlockedError):
        socket.create_connection(("example.com", 80))


def test_app_env_vars_are_cleared(monkeypatch):
    assert "MISTRAL_API_KEY" not in os.environ
    assert "TAVILY_API_KEY" not in os.environ
