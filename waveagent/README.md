# WaveAgent

**Build & deploy deterministic, recurring [WaveAssist](https://waveassist.io)
agents from inside your coding agent — Claude Code or Cursor — in plain English.**

> *"using waveassist, with my UID, build an agent that reads my ClickUp and emails
> me a weekly summary"*

…and your coding agent gathers the requirements, designs the nodes, writes the
code, deploys it to your WaveAssist account, runs a **live test**, and puts it on a
schedule — only going live once the test is green.

No Composio. No `call_tool`. You connect any tool by putting an API key in
WaveAssist's key-value store; generated nodes read it with plain `requests`.
Runtime language reasoning uses `call_llm` (WaveAssist's own LLM key — you don't
provide one).

---

## How it works — the host agent is the brain

WaveAgent has three layers, shipped together:

1. **A portable SKILL** (`skill/`) — the build-time brain your coding agent
   follows: the orchestration loop, the node-authoring contract, the keys-in-KV
   integration pattern. Identical behaviour in Claude Code and Cursor.
2. **A thin MCP server** (`mcp/`) — ~8 typed tools wrapping the WaveAssist HTTP
   API. **No reasoning lives here.**
3. **Packaging** — a Claude Code **plugin** (`plugin/`) for one-command install,
   and a **Cursor mirror** (`cursor/`).

```
You ──▶ coding agent (Claude Code / Cursor)
            │  reads SKILL  →  designs nodes, writes Python, confirms with you
            ▼
        WaveAssist MCP server (thin tools)
            │  create · materialize→GitHub · install · set keys · test · arm
            ▼
        WaveAssist  ──▶  your agent runs on a schedule (deterministic Python + call_llm)
```

## Using it

Three ways to install — see **[INSTALL.md](INSTALL.md)** for full steps.

- **Claude Code (plugin):** `/plugin marketplace add WaveAssist/WaveAgent` →
  `/plugin install waveassist@waveassist-marketplace` (auto-loads server + skill). → [§A](INSTALL.md#a-claude-code-plugin)
- **Cursor (MCP + skill):** add `uvx waveassist-mcp` to `.cursor/mcp.json`, then copy
  the `waveassist-build-deploy` skill folder into `.cursor/skills/`. → [§B](INSTALL.md#b-cursor-mcp--skill)
- **Any other MCP host:** add `uvx waveassist-mcp` to the host config, then load the
  skill yourself (read `skill/SKILL.md`) — generic hosts don't auto-load it. → [§C](INSTALL.md#c-any-other-mcp-host-claude-desktop-windsurf-vs-code-custom)

Then, everywhere: **authenticate** (`waveassist_login` with your UID), then say
**"using waveassist, build an agent that …"**.

## Publishing

Maintainer path (see **[INSTALL.md §D](INSTALL.md#d-publishing-maintainer--what-you-must-do-so-the-above-works)**):

- **Standalone GitHub repo** (`gh repo create WaveAssist/WaveAgent --public …`) →
  enables the Claude Code marketplace. No Anthropic approval — the root
  `.claude-plugin/marketplace.json` resolves directly.
- **PyPI publish** (`cd mcp && python3 -m build` → `twine upload`) → enables
  `uvx waveassist-mcp` for Cursor and generic hosts.
- **Future releases:** bump the version **in lockstep** across all 4 files
  (`plugin/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`,
  `mcp/pyproject.toml`, `plugin/mcp/pyproject.toml`), then commit, tag, re-upload.
  PyPI versions are immutable.

## What the agent does, step by step

1. **Auth** — `waveassist_login` with your WaveAssist UID.
2. **Gather** — cadence, sources + keys, the transform, the output.
3. **Design nodes** — proposes a small DAG and **confirms with you** before coding.
4. **Collect keys (smart)** — reuses any key already available (host MCP
   connectors / env / KV) before asking; when it must ask, it shows you exactly
   **how to get the token**.
5. **Write code** — flat `{node}.py` + `config.yaml`, to the contract.
6. **Deploy unarmed** — code is pushed and installed, but the schedule does not
   fire yet.
7. **Test** — a real dry-run on WaveAssist infra (side-effects gated by
   `is_test_run()`), with per-node status + an output preview.
8. **Fix** until green.
9. **Arm** the schedule — only on a green test.

## Quick start

See **[INSTALL.md](INSTALL.md)** for Claude Code and Cursor setup. In short:

1. Add the MCP server (plugin install in Claude Code, or `.cursor/mcp.json` in
   Cursor) and load the skill.
2. In chat: **"using waveassist, log me in with uid `<your-uid>`"** → then
   **"build an agent that …"**.

## Proven end-to-end

The included example — **[`examples/clickup-weekly/`](examples/clickup-weekly/)**
(ClickUp → weekly email) — was generated to the contract and run through the full
pipeline against a live WaveAssist account: **create → materialize → install →
update → set key → dry-run test (green) → arm schedule.** It's the golden template
the SKILL teaches.

## Status (v1)

- **For:** a **private beta** — auth is by WaveAssist UID, which is fine for trusted
  users.
- **Working now:** the whole build→test→deploy→schedule loop against the existing
  WaveAssist API, with open natural-language generation kept reliable by the
  *never-arm-before-a-green-test* rule.
- **Deferred to a hardening phase (the gate to public launch):** a scoped/revocable
  API key (vs raw UID), a write-only "secret" KV type + out-of-band key entry, a
  server-side validate-only endpoint, and per-key rate limiting. See
  [docs/SPEC.md](docs/SPEC.md) §3.

## Layout

| Path | What |
|---|---|
| `skill/` | The SKILL bundle (the brain): `SKILL.md` + 4 reference skills |
| `mcp/` | The Python MCP server (`waveassist_mcp`) + tests |
| `plugin/` | Claude Code plugin (manifest + bundled skill + MCP config) |
| `cursor/` | Cursor mirror (`mcp.json` + skills) |
| `examples/clickup-weekly/` | Working golden example agent |
| `docs/SPEC.md` | Full design + scope + the two-part plan |
| `docs/api-contracts.md` | Verified WaveAssist HTTP contracts |
| `INSTALL.md` | Install for Claude Code + Cursor |

## Notes for WaveAssist maintainers

- The node runtime wraps each flat node file into `def run_task():` and calls it
  (`WaveAssistApi/.../Utils/utils.py:get_code_for_node`); the worker
  (`WaveAssistWorkerEngine/Engine/TaskRunner.py`) catches only `Exception`. So a
  node must **never** use `exit()`/`sys.exit()`/`raise SystemExit` — a `SystemExit`
  (a `BaseException`) propagates past the completion log and the node is stuck
  `STARTED`. The bundled skills teach the fall-through idiom. ⚠️ The upstream
  `Assistants/WaveMaker/skills/waveassist-sdk.md` (lines ~31, ~260) still has the
  old, incorrect `sys.exit()`/`exit(0)` guidance and should be corrected at source.
- The `requirements:` list in `config.yaml` is **not** installed at deploy, so a
  generated node may only import packages baked into the worker image (`requests`,
  `pandas`, `openai`, `pydantic`, `httpx`, `aiohttp`, `beautifulsoup4`, `lxml`,
  `yfinance`, `ta`, `weasyprint`, `boto3`, `pymongo`, `PyYAML`, `crawlee`) or the
  standard library.
