"""Shared fixtures for obs tests.

Provides:
- ``free_port``: returns a random available TCP port to avoid port 8000 collisions
  when multiple tests or a background server is already bound.
"""

from __future__ import annotations

import socket

import pytest


def get_free_port() -> int:
    """Return an ephemeral TCP port that is currently free on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def free_port() -> int:
    """Pytest fixture: a random free TCP port."""
    return get_free_port()
