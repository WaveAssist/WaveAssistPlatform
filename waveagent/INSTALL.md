# WaveAgent Installation Guide

Install WaveAgent in your editor or MCP host, then build & deploy recurring WaveAssist agents in plain English.

> **Prerequisites**
> - **`uv`** must be installed — the MCP server launches via `uvx` (ships with `uv`).
>   Install it: `curl -LsSf https://astral.sh/uv/install.sh | sh`. `uv` must be on
>   your `PATH` at runtime (the server launches via `uvx` every session).
> - **A WaveAssist UID** — get one from [app.waveassist.io](https://app.waveassist.io).

---

## A. Claude Code (plugin)

1. **Register the marketplace** (reads `.claude-plugin/marketplace.json` at the repo root):
   ```
   /plugin marketplace add WaveAssist/WaveAgent
   ```
2. **Install the plugin** — the install id is `waveassist@waveassist-marketplace`
   (plugin name `waveassist`, marketplace name `waveassist-marketplace`),
   **NOT** the owner/repo:
   ```
   /plugin install waveassist@waveassist-marketplace
   ```
3. **Activate** — reload (or restart). This auto-starts the bundled MCP server
   (`uvx --from ${CLAUDE_PLUGIN_ROOT}/mcp waveassist-mcp`) and loads the
   `waveassist-build-deploy` skill:
   ```
   /reload-plugins
   ```
   Verify with `/mcp` — `waveassist` should be **connected** with **8 tools**.
4. **Authenticate** — in chat, say:
   ```
   log me in to waveassist with uid <YOUR_UID>
   ```
   This calls `waveassist_login` and persists to `~/.waveassist/config.json`.
   (Or set `WAVEASSIST_UID` in your environment before launch.)
5. **Build:**
   ```
   using waveassist, build an agent that <does X on a schedule>
   ```

**Gotchas**
- `uv` must be on `PATH` at runtime — the server launches via `uvx` every session.
- If `/plugin` is unknown, update Claude Code.
- Install alone doesn't activate mid-session — reload (`/reload-plugins`) or restart.

---

## B. Cursor (MCP + skill)

1. **Add the server** to `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global) —
   published form:
   ```json
   {
     "mcpServers": {
       "waveassist": {
         "command": "uvx",
         "args": ["waveassist-mcp"],
         "env": {
           "WAVEASSIST_API_BASE": "https://api.waveassist.io",
           "WAVEASSIST_APP_BASE": "https://app.waveassist.io"
         }
       }
     }
   }
   ```
2. **Install the skill** — copy the **whole** skill folder (sub-skills + `examples/`,
   not just `SKILL.md`) into a skills root at the **same scope** as your `mcp.json`:
   ```bash
   mkdir -p .cursor/skills && cp -r <checkout>/cursor/skills/waveassist-build-deploy .cursor/skills/
   ```
   (Or `~/.cursor/skills` for global.) Cursor auto-discovers any folder with a
   `SKILL.md` under `.cursor/skills/`. This is the **skills** mechanism — **NOT**
   `.cursor/rules` and **NOT** `AGENTS.md`.
3. **Restart Cursor.** Open Settings (**Cmd+Shift+J**) → **MCP** and confirm the
   `waveassist` server toggle is **ON** and shows its **8 tools**.
4. **Authenticate** — ask the agent to `Call waveassist_login with uid <YOUR_UID>`,
   then `Call waveassist_status` to confirm.
5. **Build:**
   ```
   using waveassist, build an agent that ...
   ```

> **Dev alternative (contributors).** End-users use `uvx waveassist-mcp` (from PyPI).
> The repo also ships a local-dev form for testing a checkout before publish — set
> `"args"` to `["--from", "/ABSOLUTE/PATH/TO/WaveAgent/mcp", "waveassist-mcp"]`.

---

## C. Any other MCP host (Claude Desktop, Windsurf, VS Code, custom)

1. **Add to the host's MCP config.** (Claude Desktop:
   Settings → Developer → Edit Config → `claude_desktop_config.json`.)
   ```json
   {
     "mcpServers": {
       "waveassist": {
         "command": "uvx",
         "args": ["waveassist-mcp"],
         "env": {
           "WAVEASSIST_UID": "<your-uid>"
         }
       }
     }
   }
   ```
   **Alternative without `uvx`:** `pip install waveassist-mcp`, then set
   `"command"` to the **absolute path** to that Python and `"args"` to
   `["-m", "waveassist_mcp"]`.
2. **Restart the host** and confirm the **8 `waveassist_` tools** appear.
3. **Authenticate** — call `waveassist_login(uid="<your-uid>")`
   (or set `WAVEASSIST_UID` in `env`).
4. **IMPORTANT LIMITATION — no skill auto-load.** A generic host won't auto-load
   the skill, and the MCP server is a thin pipe with **no reasoning**, so you
   **must supply the skill yourself**: clone the repo and tell the agent to
   *"read `skill/SKILL.md` and follow it"* (load the sub-skills too), **OR** paste
   `SKILL.md` into context. Without it, the agent has tools but not the node contract.
5. **Build:**
   ```
   using waveassist, build an agent that ...
   ```

---

## D. Publishing (maintainer — what YOU must do so the above works)

> **Prereqs to install/auth first** (currently missing locally): `uv`
> (`curl -LsSf https://astral.sh/uv/install.sh | sh`),
> `python3 -m pip install --upgrade build twine`, and `gh auth login`. You also
> need a **PyPI account + API token** (`pypi-...`). Note: WaveAgent is currently
> untracked inside the parent WaveAssist repo — it must become its **OWN
> standalone git repo** (root = the dir containing `.claude-plugin/marketplace.json`).

1. **Check parity + clean:**
   ```bash
   bash scripts/check_bundles.sh
   rm -rf mcp/dist mcp/src/*.egg-info
   ```
2. **Init the standalone repo:**
   ```bash
   git -C <WaveAgent> init && git -C <WaveAgent> add -A && git -C <WaveAgent> commit -m "WaveAgent v0.1.0"
   ```
3. **Create the public GitHub repo** (enables the Claude Code marketplace):
   ```bash
   gh repo create WaveAssist/WaveAgent --public --source=<WaveAgent> --remote=origin --push
   ```
   (Or create an empty public repo on github.com, then
   `git remote add origin … && git branch -M main && git push -u origin main`.)
   **No Anthropic approval needed** for a self-hosted marketplace —
   `/plugin marketplace add WaveAssist/WaveAgent` resolves the root
   `.claude-plugin/marketplace.json` directly.
4. **Build + publish to PyPI** (this is what makes `uvx waveassist-mcp` work for
   Cursor/generic users):
   ```bash
   ( cd mcp && python3 -m build )
   python3 -m twine check mcp/dist/*
   python3 -m twine upload mcp/dist/*   # username __token__, password the pypi-… token
   ```
   The name `waveassist-mcp` is verified available.
5. **Tag the release:**
   ```bash
   git tag v0.1.0 && git push --tags
   ```
6. **Verify:**
   - Claude Code: `/plugin marketplace add` → install → `/mcp` connected
     (runs from the **bundled** copy, not PyPI).
   - Cursor/generic: `uvx waveassist-mcp --help`.

**Future releases.** Bump the version **IN LOCKSTEP** in all four files:
`plugin/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`,
`mcp/pyproject.toml`, **and** `plugin/mcp/pyproject.toml` (keep the bundled copy in
sync — run `scripts/check_bundles.sh`). Then commit, push, tag, and re-run
build + `twine upload`. Claude Code users update via `/plugin marketplace update`;
`uvx` users get the latest from PyPI automatically (or pin
`uvx waveassist-mcp@X.Y.Z`). **PyPI versions are IMMUTABLE — never reuse a version.**

---

## Files structure

```
WaveAgent/
├── .claude-plugin/
│   └── marketplace.json             # Marketplace catalog (read from repo root)
│
├── plugin/                          # Claude Code plugin package
│   ├── .claude-plugin/
│   │   └── plugin.json              # Plugin manifest (bundled MCP config)
│   ├── mcp/                         # Self-contained MCP server (bundled copy)
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   └── src/waveassist_mcp/
│   └── skills/waveassist-build-deploy/
│       ├── SKILL.md
│       ├── waveassist-sdk.md
│       ├── prompt-writing-with-call-llm.md
│       ├── email-html-design.md
│       ├── integrations-without-composio.md
│       └── examples/clickup-weekly/
│
├── cursor/                          # Cursor package
│   ├── mcp.json                     # MCP config (published: uvx waveassist-mcp)
│   └── skills/waveassist-build-deploy/
│       ├── SKILL.md
│       ├── waveassist-sdk.md
│       ├── prompt-writing-with-call-llm.md
│       ├── email-html-design.md
│       ├── integrations-without-composio.md
│       └── examples/clickup-weekly/
│
├── mcp/                             # MCP server source (authoritative; → PyPI)
│   ├── src/waveassist_mcp/
│   ├── pyproject.toml
│   └── README.md
│
├── skill/                           # Authoritative skill source (repo root)
│   ├── SKILL.md
│   ├── waveassist-sdk.md
│   ├── prompt-writing-with-call-llm.md
│   ├── email-html-design.md
│   └── integrations-without-composio.md
│
├── examples/
│   └── clickup-weekly/              # Golden example agent
│
├── scripts/
│   └── check_bundles.sh             # Parity guard: bundles must match source
│
├── docs/
│   ├── SPEC.md
│   └── api-contracts.md
│
├── INSTALL.md
├── PACKAGING_DECISIONS.md           # Packaging/schema decisions (repo root)
└── README.md
```
