"""Local registry of agents built by WaveAgent, scoped per WaveAssist UID.

Maps uid -> slug -> deploy metadata so re-deploying the same agent is idempotent
(routes create-vs-upgrade) without a server-side stable identity. Stored at
~/.waveassist/waveagent.json as { "<uid>": { "<slug>": {...} } }.

UID-scoping makes this safe for the HOSTED (multi-tenant) server too: each user's
agents are isolated by their UID. (A single hosted instance persists this file
locally; horizontal scaling would move it to server-side storage — a follow-up.)
"""
from __future__ import annotations

import json
import re

from . import config

REGISTRY_PATH = config.CONFIG_DIR / "waveagent.json"


def slugify(name: str) -> str:
    """Turn an assistant name into a lowercase snake_case slug."""
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return slug or "agent"


def _load() -> dict:
    try:
        data = json.loads(REGISTRY_PATH.read_text())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save(data: dict) -> None:
    config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(data, indent=2))


def get(uid: str, slug: str) -> dict | None:
    return _load().get(uid, {}).get(slug)


def put(uid: str, slug: str, entry: dict) -> None:
    data = _load()
    by_slug = data.setdefault(uid, {})
    by_slug[slug] = {**by_slug.get(slug, {}), **entry}
    _save(data)


def all_agents(uid: str | None) -> dict:
    if not uid:
        return {}
    return _load().get(uid, {})
