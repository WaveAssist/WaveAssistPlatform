"""Configuration + credential resolution for the WaveAssist MCP server.

The credential is a WaveAssist user UID (obtained at login). For the private
beta this is the only auth the platform requires; a scoped/revocable key is a
hardening-phase concern (see docs/SPEC.md).

Resolution order for the UID:
    1. env WAVEASSIST_UID
    2. ~/.waveassist/config.json  ->  {"uid": "..."}
"""
from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULT_API_BASE = "https://api.waveassist.io"
DEFAULT_APP_BASE = "https://app.waveassist.io"

CONFIG_DIR = Path(os.environ.get("WAVEASSIST_HOME", str(Path.home() / ".waveassist")))
CONFIG_PATH = CONFIG_DIR / "config.json"


def api_base() -> str:
    return os.environ.get("WAVEASSIST_API_BASE", DEFAULT_API_BASE).rstrip("/")


def app_base() -> str:
    return os.environ.get("WAVEASSIST_APP_BASE", DEFAULT_APP_BASE).rstrip("/")


def _read_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text())
    except Exception:
        return {}


def load_uid() -> str | None:
    """Return the configured UID, or None if not logged in."""
    env_uid = os.environ.get("WAVEASSIST_UID")
    if env_uid:
        return env_uid.strip()
    uid = _read_config().get("uid")
    return uid.strip() if isinstance(uid, str) and uid.strip() else None


def save_uid(uid: str) -> Path:
    """Persist the UID to ~/.waveassist/config.json (merging existing keys)."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = _read_config()
    data["uid"] = uid.strip()
    CONFIG_PATH.write_text(json.dumps(data, indent=2))
    try:
        CONFIG_PATH.chmod(0o600)
    except Exception:
        pass
    return CONFIG_PATH


def dashboard_project_url(project_key: str) -> str:
    return f"{app_base()}/project/{project_key}"
