# WaveAgent Installation Guide

Install WaveAgent in your editor or MCP host, then build and deploy recurring WaveAssist agents in plain English.

**You need a WaveAssist UID.** Get one at [app.waveassist.io](https://app.waveassist.io). On the hosted paths (Cursor and any MCP host) the UID in a header is the only auth. `uv` is needed only for the Claude Code plugin, which runs a bundled copy of the server.

---

## A. Claude Code

Step 1. Register the marketplace. This reads `.claude-plugin/marketplace.json` at the repo root.

```
/plugin marketplace add WaveAssist/WaveAgent
```

Step 2. Install the plugin. The install id is `waveassist@waveassist-marketplace` (plugin name `waveassist`, marketplace name `waveassist-marketplace`), not the owner/repo.

```
/plugin install waveassist@waveassist-marketplace
```

Step 3. Activate it. Reload or restart. This auto-starts the bundled MCP server and loads the `waveassist-build-deploy` skill.

```
/reload-plugins
```

Verify with `/mcp`. The `waveassist` server should be connected with its tools listed.

Step 4. Authenticate. In chat, say:

```
log me in to waveassist with uid YOUR_UID
```

This calls `waveassist_login` and saves your UID to `~/.waveassist/config.json`. You can also set `WAVEASSIST_UID` in your environment before launch.

Step 5. Build an agent. Just describe it.

```
using waveassist, build an agent that emails me my GitHub issues every weekday at 9am
```

Notes.
1. `uv` must be on your `PATH` at runtime. The plugin launches the server via `uvx` every session. Install it with `curl -LsSf https://astral.sh/uv/install.sh | sh`.
2. If `/plugin` is unknown, update Claude Code.
3. Installing alone does not activate mid-session. Reload with `/reload-plugins` or restart.

---

## B. Cursor

Step 1. Add the hosted server. Put this in `.cursor/mcp.json` for one project, or `~/.cursor/mcp.json` for every project. Paste your UID.

```json
{
  "mcpServers": {
    "waveassist": {
      "url": "https://mcp.waveassist.ai/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_UID"
      }
    }
  }
}
```

Step 2. Restart Cursor. Open Settings (Cmd+Shift+J), go to MCP, and confirm the `waveassist` server toggle is ON.

Step 3. Build an agent.

```
using waveassist, build an agent that emails me a weekly summary of my ClickUp tasks
```

The agent loads the build instructions on its own by calling the `waveassist_build_guide` tool, so the MCP URL is all you need. Auth is your UID in the header, with no login step.

Optional, for the smoothest experience: copy the skill folder so the guide is always in context.

```bash
cp -r cursor/skills/waveassist-build-deploy .cursor/skills/
```

Self-run alternative for contributors or offline use. Instead of the hosted URL, run the server locally with `"command": "uvx"` and `"args": ["--from", "/ABSOLUTE/PATH/TO/WaveAgent/mcp", "waveassist-mcp"]`. This needs `uv`, and you authenticate with the `waveassist_login` tool.

---

## C. Any other MCP host (Claude Desktop, Windsurf, VS Code, custom)

Step 1. Add the hosted server to the host MCP config. Paste your UID. For hosts with native remote-MCP support:

```json
{
  "mcpServers": {
    "waveassist": {
      "url": "https://mcp.waveassist.ai/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_UID"
      }
    }
  }
}
```

For hosts without native remote MCP (for example older Claude Desktop), bridge with `npx mcp-remote`. No Python needed.

```json
{
  "mcpServers": {
    "waveassist": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mcp.waveassist.ai/mcp",
               "--header", "Authorization: Bearer YOUR_UID"]
    }
  }
}
```

Step 2. Restart the host. Confirm the `waveassist_` tools appear.

Step 3. Build an agent.

```
using waveassist, build an agent that posts a daily standup summary to Slack
```

Auth is your UID in the header. There is no login step. The agent fetches the build guide from the server with `waveassist_build_guide`, so the MCP URL is all you need.

---

## D. Publishing (maintainer)

This is what makes the paths above work. The server is already hosted at `https://mcp.waveassist.ai/mcp` and the public repo is at `github.com/WaveAssist/WaveAgent`. This section is for repeating the setup or cutting a release.

Prereqs for a release. `gh auth login`. For the optional PyPI publish, also `python3 -m pip install --upgrade build twine` and a PyPI API token (`pypi-...`).

Step 1. Check parity and clean build artifacts.

```bash
bash scripts/check_bundles.sh
rm -rf mcp/dist mcp/src/*.egg-info
```

Step 2. Commit and push. The repo is standalone with its root at the dir containing `.claude-plugin/marketplace.json`.

```bash
git add -A && git commit -m "WaveAgent vX.Y.Z" && git push
```

Pushing to `main` with changes under `mcp/` auto-deploys the hosted server through the GitHub Action (see `.github/workflows/deploy-mcp.yml`). The public repo also makes the Claude Code marketplace install work. No Anthropic approval is needed, because `/plugin marketplace add WaveAssist/WaveAgent` resolves the root `.claude-plugin/marketplace.json` directly.

Step 3. Tag the release.

```bash
git tag vX.Y.Z && git push --tags
```

Step 4 (optional). Publish to PyPI. Not needed for the hosted URL. It only enables the self-run `uvx waveassist-mcp` path.

```bash
( cd mcp && python3 -m build )
python3 -m twine check mcp/dist/*
python3 -m twine upload mcp/dist/*
```

Future releases. Bump the version in lockstep across four files: `plugin/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `mcp/pyproject.toml`, and `plugin/mcp/pyproject.toml`. Run `scripts/check_bundles.sh` to confirm the bundles match. PyPI versions are immutable, so never reuse a version.

Hosting and CI/CD detail is in `docs/HOSTING.md` and `docs/DEPLOY_CLOUD_RUN.md`.

---

## Files structure

```
WaveAgent/
├── .claude-plugin/
│   └── marketplace.json             Marketplace catalog (read from repo root)
│
├── plugin/                          Claude Code plugin package
│   ├── .claude-plugin/
│   │   └── plugin.json              Plugin manifest (bundled MCP config)
│   ├── mcp/                         Self-contained MCP server (bundled copy)
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
├── cursor/                          Cursor package
│   ├── mcp.json                     MCP config (hosted URL + Bearer UID)
│   └── skills/waveassist-build-deploy/
│
├── mcp/                             MCP server source (authoritative)
│   ├── src/waveassist_mcp/          (includes _skill/ served by build_guide)
│   ├── Dockerfile                   Hosted server image
│   ├── pyproject.toml
│   └── README.md
│
├── skill/                           Authoritative skill source
│   ├── SKILL.md
│   ├── waveassist-sdk.md
│   ├── prompt-writing-with-call-llm.md
│   ├── email-html-design.md
│   └── integrations-without-composio.md
│
├── examples/clickup-weekly/         Golden example agent
│
├── scripts/check_bundles.sh         Parity guard: bundles must match source
│
├── .github/workflows/deploy-mcp.yml CI/CD: push to main auto-deploys the server
│
├── docs/
│   ├── SPEC.md
│   ├── api-contracts.md
│   ├── HOSTING.md
│   ├── DEPLOY_CLOUD_RUN.md
│   └── USAGE.html
│
├── render.yaml                      Alternative one-click host (Render)
├── INSTALL.md
├── PACKAGING_DECISIONS.md
└── README.md
```
