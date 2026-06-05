# WaveAgent

**Build & deploy deterministic, recurring [WaveAssist](https://waveassist.io)
agents from inside your coding agent (Claude Code or Cursor) in plain English.**

> *"using waveassist, with my UID, build an agent that reads my ClickUp and emails
> me a weekly summary"*

…and your coding agent gathers the requirements, designs the nodes, writes the
code, deploys it to your WaveAssist account, runs a **live test**, and puts it on a
schedule. It goes live once the test is green.

No Composio. No `call_tool`. You connect any tool by putting an API key in
WaveAssist's key-value store, and generated nodes read it with plain `requests`.
Runtime language reasoning uses `call_llm` (WaveAssist's own LLM key, you don't
provide one).

---

## How it works (the host agent is the brain)

WaveAgent has three layers, shipped together:

1. **A portable SKILL** (`skill/`). The build-time brain your coding agent
   follows: the orchestration loop, the node-authoring contract, the keys-in-KV
   integration pattern. Identical behaviour in Claude Code and Cursor.
2. **A thin MCP server** (`mcp/`). ~8 typed tools wrapping the WaveAssist HTTP
   API. **No reasoning lives here.**
3. **Packaging.** a Claude Code **plugin** (`plugin/`) for one-command install,
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

You need a **WaveAssist UID** (get one at [app.waveassist.io](https://app.waveassist.io)).
Pick your tool below. Full detail in [INSTALL.md](INSTALL.md).

### Claude Code

Step 1. Add the hosted server (paste your UID).

```
claude mcp add --transport http waveassist https://mcp.waveassist.ai/mcp --header "Authorization: Bearer YOUR_UID"
```

Step 2. Add the build skill.

```
/plugin marketplace add WaveAssist/WaveAgent
/plugin install waveassist@waveassist-marketplace
```

Step 3. Build an agent (just describe it).

```
using waveassist, build an agent that emails me my GitHub issues every weekday at 9am
```

### Cursor

Step 1. Add the hosted server. Put this in `.cursor/mcp.json` (paste your UID).

```json
{
  "mcpServers": {
    "waveassist": {
      "url": "https://mcp.waveassist.ai/mcp",
      "headers": { "Authorization": "Bearer YOUR_UID" }
    }
  }
}
```

Step 2. Restart Cursor. Open Settings, go to MCP, confirm the `waveassist` server is ON.

Step 3. Build an agent.

```
using waveassist, build an agent that emails me a weekly summary of my ClickUp tasks
```

The agent loads the build instructions automatically by calling the
`waveassist_build_guide` tool. That is all you need. (Optional, for the smoothest
experience, copy the `cursor/skills/waveassist-build-deploy` folder into
`.cursor/skills/` so the guide is always in context.)

### Any other MCP host (Claude Desktop, Windsurf, VS Code, custom)

Step 1. Add the hosted server to the host MCP config (paste your UID).

```json
{
  "mcpServers": {
    "waveassist": {
      "url": "https://mcp.waveassist.ai/mcp",
      "headers": { "Authorization": "Bearer YOUR_UID" }
    }
  }
}
```

Step 2. Restart the host. Confirm the 8 `waveassist_` tools appear.

Step 3. Build an agent.

```
using waveassist, build an agent that posts a daily standup summary to Slack
```

Authentication is your UID in the `Authorization` header. There is no login step.
The agent fetches the build guide from the server, so the MCP URL is all you need.

## Publishing

It is already live. The server is hosted at `https://mcp.waveassist.ai/mcp` and the
public repo is at `github.com/WaveAssist/WaveAgent`. Full maintainer steps are in
[INSTALL.md](INSTALL.md) under "D. Publishing (maintainer)". In short:

1. Public GitHub repo. Enables the Claude Code marketplace. No Anthropic approval, because the root `.claude-plugin/marketplace.json` resolves directly.
2. Hosted server on Google Cloud Run, free tier. This is the zero-install path every host uses. Pushing to `main` with changes under `mcp/` auto-deploys it.
3. PyPI publish is optional. It only enables the self-run `uvx waveassist-mcp` path. The hosted URL does not need it.
4. For each release, bump the version in lockstep across four files: `plugin/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `mcp/pyproject.toml`, and `plugin/mcp/pyproject.toml`. Then commit, tag, and push.
  PyPI versions are immutable.

## What the agent does, step by step

1. **Auth.** `waveassist_login` with your WaveAssist UID.
2. **Gather.** cadence, sources + keys, the transform, the output.
3. **Design nodes.** proposes a small DAG and **confirms with you** before coding.
4. **Collect keys (smart).** reuses any key already available (host MCP
   connectors / env / KV) before asking. When it must ask, it shows you exactly
   **how to get the token**.
5. **Write code.** flat `{node}.py` + `config.yaml`, to the contract.
6. **Deploy unarmed.** code is pushed and installed, but the schedule does not
   fire yet.
7. **Test.** a real dry-run on WaveAssist infra (side-effects gated by
   `is_test_run()`), with per-node status + an output preview.
8. **Fix** until green.
9. **Arm** the schedule, only on a green test.

## Quick start

See **[INSTALL.md](INSTALL.md)** for Claude Code and Cursor setup. In short:

1. Add the MCP server (plugin install in Claude Code, or `.cursor/mcp.json` in
   Cursor) and load the skill.
2. In chat: **"using waveassist, log me in with uid `<your-uid>`"** → then
   **"build an agent that …"**.

## Proven end-to-end

The included example **[`examples/clickup-weekly/`](examples/clickup-weekly/)**
(ClickUp to weekly email) was generated to the contract and run through the full
pipeline against a live WaveAssist account: **create → materialize → install →
update → set key → dry-run test (green) → arm schedule.** It's the golden template
the SKILL teaches.

## Status (v1)

- **For:** a **private beta.** Auth is by WaveAssist UID, which is fine for trusted
  users.
- **Working now:** the whole build→test→deploy→schedule loop against the existing
  WaveAssist API, with open natural-language generation kept reliable by the
  *never-arm-before-a-green-test* rule.
- **Deferred to a hardening phase (the gate to public launch):** a scoped/revocable
  API key (vs raw UID), a write-only "secret" KV type + out-of-band key entry, a
  server-side validate-only endpoint, and per-key rate limiting. See
  [docs/SPEC.md](docs/SPEC.md), section 3.

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
  node must **never** use `exit()`/`sys.exit()`/`raise SystemExit`. A `SystemExit`
  (a `BaseException`) propagates past the completion log and the node is stuck
  `STARTED`. The bundled skills teach the fall-through idiom. ⚠️ The upstream
  `Assistants/WaveMaker/skills/waveassist-sdk.md` (lines ~31, ~260) still has the
  old, incorrect `sys.exit()`/`exit(0)` guidance and should be corrected at source.
- The `requirements:` list in `config.yaml` is **not** installed at deploy, so a
  generated node may only import packages baked into the worker image (`requests`,
  `pandas`, `openai`, `pydantic`, `httpx`, `aiohttp`, `beautifulsoup4`, `lxml`,
  `yfinance`, `ta`, `weasyprint`, `boto3`, `pymongo`, `PyYAML`, `crawlee`) or the
  standard library.
