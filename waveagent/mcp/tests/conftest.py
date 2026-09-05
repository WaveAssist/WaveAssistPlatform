"""Shared test fixtures for the WaveAssist MCP server tests.

Key concern: ``config.CONFIG_DIR`` is computed at *import time* from the
``WAVEASSIST_HOME`` env var, and ``registry.REGISTRY_PATH`` is in turn derived
from ``config.CONFIG_DIR`` at import time. So the env vars MUST be set before
those modules are first imported (or the modules must be reloaded afterwards).

We do both: we set the env at module-import time (collection) so the very first
import already sees a temp home, and we provide an autouse fixture that points
``WAVEASSIST_HOME`` at a per-test ``tmp_path`` and reloads ``config`` +
``registry`` so each test gets an isolated, throwaway home dir. Nothing ever
touches the real ``~/.waveassist``.
"""
from __future__ import annotations

import importlib
import os
import tempfile

import pytest

# Set a safe default BEFORE waveassist_mcp.* gets imported anywhere, so the
# first import never resolves CONFIG_DIR to the real ~/.waveassist.
os.environ.setdefault("WAVEASSIST_HOME", tempfile.mkdtemp(prefix="wa_home_"))
os.environ.setdefault("WAVEASSIST_UID", "test-uid-1234")

API_BASE = "https://api.waveassist.io"


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Point WAVEASSIST_HOME at a fresh tmp_path and reload config/registry so
    CONFIG_DIR / REGISTRY_PATH resolve under it. Also pins WAVEASSIST_UID."""
    monkeypatch.setenv("WAVEASSIST_HOME", str(tmp_path))
    monkeypatch.setenv("WAVEASSIST_UID", "test-uid-1234")
    # Make sure we hit prod base in tests (respx mocks it) regardless of a
    # developer's local override.
    monkeypatch.delenv("WAVEASSIST_API_BASE", raising=False)
    monkeypatch.delenv("WAVEASSIST_APP_BASE", raising=False)

    from waveassist_mcp import config, registry

    # Only config + registry carry import-time state derived from CONFIG_DIR
    # (config.CONFIG_DIR, then registry.REGISTRY_PATH). Reload them in
    # dependency order so both resolve under this tmp_path.
    #
    # IMPORTANT: do NOT reload client/server here. importlib.reload rebuilds a
    # module's classes (e.g. WaveAssistError) with a *new* identity, which would
    # break `isinstance`/`pytest.raises` against the names the test modules
    # imported at collection time. reload() mutates config/registry *in place*,
    # so server's `config`/`registry` bindings (and client's `config` use, which
    # only calls functions at runtime) keep working without reloading them.
    importlib.reload(config)
    importlib.reload(registry)

    assert str(config.CONFIG_DIR) == str(tmp_path)
    assert str(registry.REGISTRY_PATH).startswith(str(tmp_path))

    yield


@pytest.fixture
def uid():
    return "test-uid-1234"


def envelope(data, *, success="1", message=None, status=None):
    """Build the standard WaveAssist response envelope (always HTTP 200)."""
    body = {"success": success}
    if success == "1":
        body["data"] = data
    if message is not None:
        body["message"] = message
    if status is not None:
        body["status"] = status
    return body
