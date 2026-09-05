# WaveAgent Packaging Decisions & Schema Analysis

This document records the exact schemas used for WaveAgent's Claude Code plugin and Cursor integration, with citations to the official 2026 documentation.

## 1. Claude Code Plugin Schema (plugin.json)

**Location:** `/Users/shreyarao/Desktop/WaveAssist/WA/WaveAgent/plugin/.claude-plugin/plugin.json`

**Schema Used:** Claude Code 2026 Plugin Manifest (https://code.claude.com/docs/en/plugins.md)

### Fields Selected

| Field | Type | Required | Value | Rationale |
|-------|------|----------|-------|-----------|
| `name` | string | ✓ | `"waveassist"` | Plugin namespace; becomes prefix for skills (`/waveassist:skill-name`) |
| `displayName` | string | – | `"WaveAssist"` | Human-readable name shown in UI (Claude Code v2.1.143+) |
| `version` | string | – | `"0.1.0"` | Explicit version: users only get updates when bumped. Omit to use git commit SHA. |
| `description` | string | – | Product description | Shown in plugin manager |
| `author` | object | – | `{ "name": "WaveAssist" }` | Attribution |
| `homepage` | string | – | `"https://waveassist.io"` | Documentation link |
| `repository` | string | – | `"https://github.com/WaveAssist/WaveAgent"` | Source code link |
| `license` | string | – | `"MIT"` | SPDX identifier |
| `keywords` | array | – | tags | Searchability |
| `mcpServers` | object | – | See below | Bundled MCP server config |

**Decision:** We use explicit `version` pinning instead of git commit SHA because WaveAssist will have separate release cadences; we control when users get updates.

### MCP Server Bundled in plugin.json

**Schema:** Inline `mcpServers` object in `plugin.json` (alternative to separate `.mcp.json`)

**Field Format:**
```json
"mcpServers": {
  "waveassist": {
    "command": "uvx",
    "args": ["--from", "${CLAUDE_PLUGIN_ROOT}/mcp", "waveassist-mcp"],
    "env": {
      "WAVEASSIST_API_BASE": "https://api.waveassist.io",
      "WAVEASSIST_APP_BASE": "https://app.waveassist.io"
    }
  }
}
```

**Field Notes:**
- `command`: The executable, `"uvx"` (ships with `uv`).
- `args`: `["--from", "${CLAUDE_PLUGIN_ROOT}/mcp", "waveassist-mcp"]`. The MCP
  server source is **bundled inside the plugin** at `plugin/mcp/` (a copy of the
  `mcp/` package: `pyproject.toml`, `README.md`, `src/waveassist_mcp/`). `uvx
  --from <local dir>` makes `uv` build that local directory and run its
  `waveassist-mcp` console script. **No PyPI publish is needed.**
- `env`: Environment variables passed to the server. Supports variable expansion (`${VAR}`) in Claude Code v2.1.121+.
- **`${CLAUDE_PLUGIN_ROOT}` resolves at runtime** to the installed plugin's root
  directory, so `${CLAUDE_PLUGIN_ROOT}/mcp` points at the bundled server
  regardless of where the plugin was installed. This is why the server is
  self-contained — it requires only `uv`, not a published package or a hardcoded path.

**Citation:** [Claude Code Plugins Reference — MCP Servers](https://code.claude.com/docs/en/plugins.md#add-mcp-servers-to-your-plugin) and [MCP Configuration — Plugin-Provided MCP Servers](https://code.claude.com/docs/en/mcp.md#plugin-provided-mcp-servers)

### Skill Bundle Location

**Schema:** Skills stored in `plugin/skills/<skill-name>/SKILL.md`

**Location:** `/Users/shreyarao/Desktop/WaveAssist/WA/WaveAgent/plugin/skills/waveassist-build-deploy/`

**Contents:**
- `SKILL.md` — Main skill with YAML frontmatter + Markdown instructions
- Supporting `.md` files — `waveassist-sdk.md`, `integrations-without-composio.md`, etc.
- `examples/` — Golden example (clickup-weekly agent)

**Citation:** [Claude Code Plugins — Add Skills to Your Plugin](https://code.claude.com/docs/en/plugins.md#add-skills-to-your-plugin)

## 2. Marketplace Schema (marketplace.json)

**Location:** `/Users/shreyarao/Desktop/WaveAssist/WA/WaveAgent/.claude-plugin/marketplace.json` (REPO ROOT)

> **Correction:** This file lives at the **repo root** under `.claude-plugin/`,
> not under `plugin/`. `/plugin marketplace add WaveAssist/WaveAgent` fetches
> `.claude-plugin/marketplace.json` from the repository root, so that is the only
> location Claude Code reads it from. The plugin's own `.claude-plugin/` directory
> contains **only** `plugin.json`. The `$schema` key was also dropped — it pointed
> at an HTML docs page, not a JSON Schema, so it served no validation purpose.

**Schema Reference:** [Claude Code Plugin Marketplaces](https://code.claude.com/docs/en/plugin-marketplaces.md#marketplace-schema)

### Required Fields

| Field | Type | Choices | Value |
|-------|------|---------|-------|
| `name` | string | kebab-case | `"waveassist-marketplace"` |
| `owner` | object | `{ name, email? }` | `{ "name": "WaveAssist", "email": "support@waveassist.io" }` |
| `plugins` | array | Plugin entries | Array of plugin definitions |

### Plugin Entry Schema

| Field | Type | Required | Value |
|-------|------|----------|-------|
| `name` | string | ✓ | `"waveassist"` |
| `displayName` | string | – | `"WaveAssist"` |
| `source` | string \| object | ✓ | GitHub source object (see below) |
| `description` | string | – | Product description |
| `version` | string | – | `"0.1.0"` (optional; if set, overrides plugin.json) |
| `author` | object | – | Attribution |
| `homepage` | string | – | Doc link |
| `repository` | string | – | Source link |
| `license` | string | – | SPDX ID |
| `keywords` | array | – | Search tags |
| `category` | string | – | `"productivity"` |

### Source Format (GitHub Subdirectory)

```json
{
  "source": {
    "source": "github",
    "repo": "WaveAssist/WaveAgent",
    "path": "plugin"
  }
}
```

**Rationale:** The plugin source points to `WaveAssist/WaveAgent` repo, path `plugin`, because that's where the `.claude-plugin/plugin.json` lives. This is a **git-subdir** source pattern, allowing sparse checkout of just the plugin directory.

**Citation:** [Plugin Marketplaces — Git Subdirectories](https://code.claude.com/docs/en/plugin-marketplaces.md#git-subdirectories)

## 3. Cursor MCP Configuration (mcp.json)

**Location:** `/Users/shreyarao/Desktop/WaveAssist/WA/WaveAgent/cursor/mcp.json`

**Schema:** Standard Cursor MCP config (https://cursor.com/docs/mcp)

**Format:**
```json
{
  "mcpServers": {
    "waveassist": {
      "command": "uvx",
      "args": ["--from", "/ABSOLUTE/PATH/TO/WaveAgent/mcp", "waveassist-mcp"],
      "env": { ... }
    }
  }
}
```

**Usage:** Users copy this file to `.cursor/mcp.json` and replace
`/ABSOLUTE/PATH/TO` with their own WaveAgent checkout path.

**Decision:** Use the portable `uvx --from <local mcp dir>` form rather than a
hardcoded `/Users/shreyarao/...` venv path. Cursor has no `${CLAUDE_PLUGIN_ROOT}`
equivalent, so the user must supply the absolute checkout path once; `uvx` then
builds and runs the local `mcp/` package (requires `uv` installed). A Local-Dev
venv variant (`.venv/bin/python -m waveassist_mcp`, after
`cd mcp && python -m venv .venv && .venv/bin/pip install -e .`) is documented in
INSTALL.md as an alternative.

**Citation:** [Cursor Docs — MCP Configuration](https://cursor.com/docs/cli/mcp)

## 4. Cursor Skills Configuration

**Location:** `/Users/shreyarao/Desktop/WaveAssist/WA/WaveAgent/cursor/skills/waveassist-build-deploy/`

**Schema:** Cursor 2026 skills in `.cursor/skills/` (https://cursor.com/docs)

**Structure:**
```
.cursor/skills/
└── waveassist-build-deploy/
    ├── SKILL.md
    └── (supporting .md files)
```

**Discovery:** Cursor reads `.cursor/skills/` automatically. Minimum requirement: `SKILL.md` with frontmatter `description` field.

**Citation:** [Cursor Skills Configuration](https://cursor.com/docs) — Skills load from `.cursor/skills/<skill-name>/SKILL.md`

## 5. Key Schema Decisions

### Decision A: MCP Config Location

**Question:** Should MCP be in `plugin.json` (inline) or separate `.mcp.json`?

**Decision:** Inline in `plugin.json` for Claude Code.

**Rationale:**
- The documentation shows both patterns as valid (https://code.claude.com/docs/en/plugins.md#add-mcp-servers-to-your-plugin)
- Inline is simpler for distribution: users install the plugin, MCP is automatic.
- Separate `.mcp.json` is cleaner for complex multi-server setups.
- **We chose inline** because WaveAgent is a single, tightly-integrated MCP server — the plugin and server are co-distributed.

### Decision B: Version Management

**Question:** Explicit `version` string or git commit SHA?

**Decision:** Explicit `"0.1.0"` in both `plugin.json` and `marketplace.json`.

**Rationale:**
- The MCP server (`waveassist-mcp`) lives in a separate directory (`mcp/`) and has its own `pyproject.toml` versioning.
- The skill bundle (SKILL.md + supporting docs) is authored and tested as a unit.
- Explicit version ensures users get updates only when WaveAssist intentionally bumps the version.
- If we omitted `version`, every commit would trigger an update (git SHA), which is too frequent for a production product.

**Citation:** [Plugin Marketplaces — Version Resolution](https://code.claude.com/docs/en/plugin-marketplaces.md#version-resolution-and-release-channels)

### Decision C: MCP Command Format

**Question:** How to reference the MCP server executable?

**Decision:**
- **Claude Code (plugin):** `"uvx"` + `["--from", "${CLAUDE_PLUGIN_ROOT}/mcp", "waveassist-mcp"]` (server bundled under the plugin)
- **Cursor:** `"uvx"` + `["--from", "/ABSOLUTE/PATH/TO/WaveAgent/mcp", "waveassist-mcp"]`
- **Local-Dev (either host):** `/path/to/mcp/.venv/bin/python` + `["-m", "waveassist_mcp"]` after building the venv

**Rationale:**
- `uvx --from <local dir>` builds and runs a local package directory — no PyPI
  publish required. The Claude Code plugin ships the server source at
  `plugin/mcp/` and references it with `${CLAUDE_PLUGIN_ROOT}/mcp`, making the
  plugin fully self-contained; Cursor uses the user's checkout path.
- The Local-Dev venv path is a convenience alternative for iterating on the
  server source without rebuilding through `uvx`.
- The `pyproject.toml` defines a console script entry point: `waveassist-mcp = "waveassist_mcp.server:main"`, so `uvx` can find it.

**Citation:** [MCP — Installing MCP Servers — Option 3: stdio](https://code.claude.com/docs/en/mcp.md#option-3-add-a-local-stdio-server)

### Decision D: Environment Variables

**Question:** Which env vars does the MCP server honor?

**Decision:** Only `WAVEASSIST_API_BASE` and `WAVEASSIST_APP_BASE` in the bundled config.

**Rationale:**
- `WAVEASSIST_UID` is optional and typically saved to `~/.waveassist/config.json` by `waveassist_login()`.
- The MCP config provides defaults for API/app endpoints so users don't need to set them.
- Users can override with environment variables if using a custom WaveAssist instance.

**Citation:** [MCP — Environment Variable Expansion](https://code.claude.com/docs/en/mcp.md#environment-variable-expansion-in-mcpjson)

## 6. Field Questions and Answers

### Q: What's the difference between `displayName` and `name`?

**A:** 
- `name` (required): kebab-case identifier used for referencing (e.g., `/waveassist:skill`), must be unique, cannot have spaces.
- `displayName` (optional, v2.1.143+): Human-readable name shown in UI, can have spaces and mixed case. Falls back to `name` if omitted.

We set both for clarity: `"name": "waveassist"` and `"displayName": "WaveAssist"`.

### Q: Can skills be in `commands/` instead of `skills/`?

**A:** Yes. `commands/` uses flat `.md` files, while `skills/` uses directories with `SKILL.md`. The docs recommend `skills/` for new plugins. We use `skills/` for consistency with modern Claude Code patterns.

### Q: Does Cursor use `AGENTS.md` or `.cursor/skills/`?

**A:** Both. Cursor reads:
1. **AGENTS.md** (YAML rules for agent behavior)
2. **.cursor/skills/** (skill definitions, Cursor calls them "skills" or "instructions")
3. **Rules** from `.cursor/rules/`

We provide `.cursor/skills/` because that's how Cursor surfaces agent instructions (equivalent to Claude Code's skills).

**Citation:** [Cursor Docs](https://cursor.com/docs) — Skills load from `.cursor/skills/<skill-name>/SKILL.md`; rules from `.cursor/rules/`

### Q: Does the marketplace.json need `"$schema"`?

**A:** No. We **removed** it. The value previously pointed at an HTML docs page,
not a JSON Schema document, so it provided no validation and only added noise.
Claude Code ignores it at load time regardless.

### Q: Do we need to publish `waveassist-mcp` to PyPI?

**A:** No — that gap is resolved. The MCP server source is bundled inside the
plugin at `plugin/mcp/` and launched with `uvx --from ${CLAUDE_PLUGIN_ROOT}/mcp
waveassist-mcp`. `uvx` builds the local directory on demand, so the plugin works
straight from the marketplace with only `uv` installed. Cursor uses the same
form with the user's checkout path. PyPI publishing is no longer required.

## 7. File Paths Summary

**Absolute Paths Created:**

1. `/Users/shreyarao/Desktop/WaveAssist/WA/WaveAgent/.claude-plugin/marketplace.json` — Marketplace catalog (REPO ROOT — read by `/plugin marketplace add`)
2. `/Users/shreyarao/Desktop/WaveAssist/WA/WaveAgent/plugin/.claude-plugin/plugin.json` — Claude Code plugin manifest (the plugin's `.claude-plugin/` holds only this)
3. `/Users/shreyarao/Desktop/WaveAssist/WA/WaveAgent/plugin/mcp/` — Bundled MCP server (copy of `mcp/`: pyproject.toml, README.md, src/waveassist_mcp/)
4. `/Users/shreyarao/Desktop/WaveAssist/WA/WaveAgent/plugin/skills/waveassist-build-deploy/` — Bundled skill (copied from repo root)
5. `/Users/shreyarao/Desktop/WaveAssist/WA/WaveAgent/cursor/mcp.json` — Cursor MCP config (users copy to `.cursor/mcp.json`, edit the path)
6. `/Users/shreyarao/Desktop/WaveAssist/WA/WaveAgent/cursor/skills/waveassist-build-deploy/` — Cursor skill bundle
7. `/Users/shreyarao/Desktop/WaveAssist/WA/WaveAgent/scripts/check_bundles.sh` — Parity guard: bundles must match source
8. `/Users/shreyarao/Desktop/WaveAssist/WA/WaveAgent/INSTALL.md` — Installation guide

**Unchanged (Authoritative):**

- `/Users/shreyarao/Desktop/WaveAssist/WA/WaveAgent/skill/SKILL.md` — Master skill definition (plugin and Cursor copies reference this)
- `/Users/shreyarao/Desktop/WaveAssist/WA/WaveAgent/mcp/` — MCP server source
- `/Users/shreyarao/Desktop/WaveAssist/WA/WaveAgent/examples/clickup-weekly/` — Golden example

## 8. Documentation Citations

Official sources for all schema decisions:

1. **Claude Code Plugins** — https://code.claude.com/docs/en/plugins.md
2. **Plugin Marketplaces** — https://code.claude.com/docs/en/plugin-marketplaces.md
3. **MCP Integration** — https://code.claude.com/docs/en/mcp.md
4. **MCP in Plugins** — https://code.claude.com/docs/en/mcp.md#plugin-provided-mcp-servers
5. **Cursor MCP** — https://cursor.com/docs/cli/mcp
6. **Cursor Skills** — https://cursor.com/docs (skills in `.cursor/skills/`)

All field names, required/optional status, and defaults match the 2026 documentation as of June 3, 2026.
