import socket
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))


@pytest.fixture
def no_network(monkeypatch):
    """Make any socket connection attempt fail loudly, so 'offline' is tested for real."""
    def boom(*a, **k):
        raise AssertionError("network access attempted while it is disabled")
    monkeypatch.setattr(socket.socket, "connect", boom)
    monkeypatch.setattr(socket.socket, "connect_ex", boom)
    monkeypatch.setattr(socket, "create_connection", boom)
    monkeypatch.setattr(socket, "getaddrinfo", boom)
    yield
