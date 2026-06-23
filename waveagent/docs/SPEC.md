# WaveAgent — Spec

> Build & deploy deterministic, recurring WaveAssist agents from inside your
> coding agent (Claude Code or Cursor), in plain English. No Composio, no
> `call_tool`. The host coding agent is the build-time brain; WaveAssist runs the
> deployed agent on a schedule.

Status: **v1 implemented; live-tested green (ClickUp→weekly email).** Date: 2026-06-03.

---

## 1. What this is

A new top-level product, `WA/WaveAgent/`, delivered as **three layers in one repo**:

1. **A portable SKILL bundle** (`skill/`) — the build-time *brain*. Markdown the
   host agent follows: the orchestration loop, the node-authoring contract, the
   keys-in-KV integration pattern. Works identically in Claude Code and Cursor.
2. **A thin MCP server** (`mcp/`) — the *connectivity*. ~8 typed tools that wrap
   existing WaveAssist HTTP endpoints. **Zero reasoning lives here** so behaviour
   is identical across hosts.
3. **Packaging** — a Claude Code **plugin** (`plugin/`) as the one-command
   installer, and a **Cursor mirror** (`cursor/`: `.cursor/mcp.json` + skills).

The user says, e.g.:

> *"using waveassist, with my UID, build an agent that reads my ClickUp and emails
> me a weekly summary."*

…and the host agent gathers requirements, designs WaveMaker-style nodes, confirms,
writes the node code, creates a WaveAssist project, deploys it **unarmed**, runs a
**live test**, and only **arms the schedule on a green test**.

### Relationship to the existing WaveMaker
`WA/Assistants/WaveMaker/` is the *server-side* 11-node LLM pipeline that generates
assistants on WaveAssist's infra (currently paused). WaveAgent is a **new parallel
surface** that moves the generation *brain* into the host coding agent and **reuses
WaveMaker's skills verbatim** + the same deploy endpoints. It does **not** rewrite
the server pipeline.

---

## 2. Hard constraints (from the user)

- **No Composio. No `call_tool`.** Generated nodes talk to external tools with
  plain `requests` + an API key the user puts into the WaveAssist KV store —
  exactly the shipping GitZoid pattern (it hits the GitHub REST API with a token
  pulled from the KV store).
- **`call_llm` is allowed and encouraged** for *runtime* reasoning inside
  generated nodes. It routes through WaveAssist's own server-side OpenRouter key,
  so generated nodes need **no** user LLM key. (Projects that want to bring their
  own — Azure, a Claude subscription via `claude_cli_token`, or a specific
  OpenRouter key — can set a per-model `llm_models` registry; see the SDK README.)
- **Auth by WaveAssist UID** obtained at login.
- **Cross-host:** must work in Claude Code **and** Cursor.

## 3. Scope: v1 = "make it work, then test it"

Per the user's decision, v1 builds **only what is needed to work end-to-end**, runs
against the **existing** API (UID auth), and is **tested live**. The
security-driven hardening is explicitly **deferred to a later phase**.

### In scope (v1)
- The SKILL bundle, the MCP server (thin tools over existing endpoints), the plugin +
  Cursor mirror.
- Open natural-language generation ("open is best, as long as it works"). Reliability
  is enforced **structurally**: the schedule is never armed until a live test passes.
- Smart credential collection: reuse already-available keys (existing MCP
  connectors / env / KV) before asking; when asking, **show how to acquire** the key.
- Live E2E demo: **ClickUp → weekly email**.

### Deferred to the hardening phase (NOT in v1)
- Scoped, revocable WaveAssist API key (replacing raw-UID auth) — **security**.
- Write-only "secret" KV type + out-of-band dashboard entry — **security**.
- Server-side validate-only endpoint (compile/import/key-consistency).
- `set_schedule_enabled` / `start_enabled` endpoints (a softer pause/resume than
  `stop_deployment` + re-`deploy_project`).
- Per-key rate limiting.

The hardening phase is the **gate to public launch**; v1 is for a **private beta**.

---

## 4. The build model (what a deployed agent is)

A deployed WaveAssist assistant is a **GitHub repo** of:

- `config.yaml` — `name`, `description`, optional `requirements` (pip list),
  `nodes[]`, `variables[]`. Each node: `key`, `name`, `file_name` ({key}.py),
  `starting_node` (exactly one true), `run_after` (list), and on the starting node a
  `schedule` block (`{cron, timezone}` or `{interval: {every, period}}`). A
  `type: schedule` variable mirrors the cadence for the dashboard.
- one **flat** `{node}.py` per node — **no `def main`, no `if __name__` guard**
  (the validator rejects the guard; the worker wraps the file). Order: imports →
  `waveassist.init()` → constants → Pydantic schemas → helpers → flat orchestration.
- a generated `README.md`.

**Note:** only packages baked into the WaveAssist worker image are available at
runtime (`requests`, `pandas`, `openai`, `pydantic`, `httpx`, `aiohttp`,
`beautifulsoup4`, `lxml`, `yfinance`, `ta`, `weasyprint`, `boto3`, `pymongo`,
`PyYAML`, `crawlee` + the standard library). The `requirements:` list is currently
**NOT** installed at deploy, so a generated node must only import from that set or
the stdlib.

Nodes wire **only** via `config.yaml` `run_after` + the KV store
(`fetch_data`/`store_data`). No orchestrator file, no cross-node imports.

**Secrets / integration keys (post-Composio):** the user puts a token into the KV
store once; the node reads it at the top and guards:

```python
import requests, waveassist
waveassist.init()
token = waveassist.fetch_data("clickup_token", default="")
if not token:
    waveassist.store_data("display_output",
        {"html_content": "<p>Missing ClickUp token</p>", "type": "error"},
        run_based=True, data_type="json")
else:
    tasks = requests.get("https://api.clickup.com/api/v2/...",
                         headers={"Authorization": token}).json()
    waveassist.store_data("clickup_tasks", tasks, data_type="json")
```

**Mandatory output contract:** the final node must
`store_data("display_output", {"html_content": "<inline-styled HTML>", "type": "success"}, run_based=True, data_type="json")`.

**Side-effect gating (critical without Composio):** every node that writes/sends
must branch on `waveassist.is_test_run()` so a dry run never fires a real
email/write.

---

## 5. The WaveAssist API (verified contracts)

Base: `https://api.waveassist.io`. Full details in `docs/api-contracts.md`. The
load-bearing facts the client must respect:

- **All endpoints return HTTP 200.** Branch on the JSON `"success"` field
  (`"1"`/`"0"`), never the HTTP status. `success`/`status` are **strings**.
- Auth = a **`uid`** field in the body/query (no header/JWT for app endpoints).
- Several endpoints are **form-encoded only** (`login`, `create_project`,
  `deploy_template`, `deploy_project`, `run_dag`'s `start_node_key`). Others accept
  form or JSON.

### The flow the MCP tools implement

| Step | Endpoint | Notes |
|---|---|---|
| Login | `POST /login/` + poll `GET /cli_login/session/<id>/status` | Browser handshake → uid → `~/.waveassist/config.json` |
| Create project | `POST /manage/create_project/` | `project_key` must be unique; creates `<key>_default` + `<key>_test` envs; seeds `uid`/`mongo_url`/`open_router_key` |
| Push code | `POST /api/v1/wavemaker/materialize_assistant` | `code_files {filename: src}`, `config_yaml` (string), `assistant_name`, `readme_md`; `existing_repo_url` → update mode. Returns **`repo_url`** only |
| Install nodes | `POST /template/deploy_template/` | `repo_url` + optional `target_project_key` (regex `^[a-z0-9_]+_[a-f0-9]{4}$`). **Refuses if target has nodes** → use upgrade. Installs nodes **unarmed** |
| Update existing | `POST /assistant/upgrade/` + `POST /assistant/check_update/` | Re-creates nodes from latest commit on `Project.github_url` |
| Store key | `POST /data/set_data_for_key/` | `data_run_key` (env) required, no default; write to both `<key>_default` and `<key>_test` |
| Seed test flag | `POST /data/set_data_for_key/` | `data_key=_is_test_run`, value `true`, into `<key>_test` |
| Test run | `POST /deploy/run_dag/` | `data_run_key=<key>_test`. Fire-once. Returns `{dag, run_id}` — **no per-node status** |
| Poll status | `POST /runs/fetch_dag_runs/` + `POST /runs/fetch_node_runs/` | Per-node status + tracebacks for self-fix |
| Arm schedule | `POST /deploy/deploy_project/` | Creates `PeriodicTask(enabled=True)`. Call only after a green test; ensure `_is_test_run=false` in `<key>_default` |
| Disarm | `POST /deploy/stop_deployment/` | Tears down the deployment |

**No backend change is required for v1.** "Deploy disabled → test → enable" maps to
`deploy_template` (unarmed) → `run_dag` (test) → `deploy_project` (arm).

---

## 6. MCP tool surface (thin, typed, no reasoning)

| Tool | Wraps | Purpose |
|---|---|---|
| `waveassist_login` | login + cli status poll | Browser CLI-login → save uid locally |
| `waveassist_status` | (local config only) | whoami (uid present + api/app base) + locally-registered agents (local config only; no API call) |
| `waveassist_list_projects` | fetch_all_projects | List the account's **live** projects (uid is the token); doubles as the connectivity check |
| `waveassist_deploy_agent` | create_project + materialize + deploy_template **or** materialize(update) + upgrade_assistant | **Idempotent** by a stable local registry (`~/.waveassist/waveagent.json`). Deploys **unarmed**. Returns `{ok, mode: "created"|"updated", slug, project_key, repo_url, env_default, env_test, dashboard_url}` |
| `waveassist_set_key` | set_data_for_key (×2 envs) | Store an integration key into `<key>_default` **and** `<key>_test` |
| `waveassist_test_agent` | seed `_is_test_run=true` + run_dag + poll runs | Dry-run on infra (TEST env); return per-node status, tracebacks, and any `display_output` preview |
| `waveassist_run_agent` | seed `_is_test_run=false` + run_dag + poll runs | **Live** one-off run now (DEFAULT env); side-effects fire. Distinct from arming |
| `waveassist_run_logs` | fetch_dag_runs / fetch_node_runs | Debug a run for self-fix |
| `waveassist_arm_schedule` | deploy_project | Arm the recurring schedule after a green run (fires on next cron tick, not now); warns if no green run on record |
| `waveassist_disarm_schedule` | stop_deployment | Pause/stop a live agent |

State: a local registry `~/.waveassist/waveagent.json` maps a logical agent slug →
`{project_key, repo_url, env_default, env_test}` so deploy is idempotent and edits
route to upgrade. (Server-side stable identity is a hardening-phase concern.)

---

## 7. The SKILL bundle (the brain)

`skill/SKILL.md` — the orchestration loop:

1. **Auth** — ensure a credential (call `waveassist_login` if missing).
2. **Gather** — conversational requirements: schedule/cadence; data source(s) +
   which keys; the transform/`call_llm` step; output/destination.
3. **Design nodes** — propose a node graph (starting node w/ schedule → fetch →
   transform/`call_llm` → output) and **confirm with the user before writing code**.
4. **Collect keys (smart)** — the *credential-acquisition subroutine*:
   - First **reuse what's available**: check the host's connected MCP
     connectors/servers, environment variables, and existing KV values for the
     needed credential; if present, use it (skip the ask).
   - Only if missing, **ask the user — and show how to acquire it** (provider-
     specific steps + URL, e.g. ClickUp personal token page).
   - Store via `waveassist_set_key` (with a "this enters chat context" caveat until
     the hardening phase adds out-of-band entry).
5. **Write code** — flat `{node}.py` + `config.yaml` following
   `waveassist-sdk.md`, `prompt-writing-with-call-llm.md`, `email-html-design.md`,
   and `integrations-without-composio.md`. Always: `is_test_run()` guards on side
   effects; the `display_output` contract.
6. **Create + deploy unarmed** — `waveassist_deploy_agent`.
7. **Run + confirm** — always run at least once and confirm `SUCCESS`:
   `waveassist_test_agent` (dry), and `waveassist_run_agent` for a real run when the
   user wants live output. Show node statuses + output preview.
8. **Self-fix** — on failure, read tracebacks, edit nodes, re-deploy (upgrade),
   re-run. Loop until green.
9. **Arm** — `waveassist_arm_schedule` only on green (arming schedules the recurring
   run; it does not fire immediately). Report dashboard URL.

**Guarantee:** the schedule should **never be armed before a green run** — this is how
"open generation" stays "as long as it works." Arm enforces this with a non-blocking
warning when no green run is on record.

`skill/` also contains:
- `waveassist-sdk.md`, `prompt-writing-with-call-llm.md`, `email-html-design.md` —
  **copied verbatim** from `WA/Assistants/WaveMaker/skills/`.
- `integrations-without-composio.md` — **new.** The GitZoid pattern as canonical
  template + 3–4 golden worked providers (ClickUp, GitHub, Gmail/email, generic
  REST), each with key-acquisition instructions. Replaces the Composio-centric
  `waveassist-integrations.md`.

---

## 8. Packaging

- **Claude Code plugin** (`plugin/`): `.claude-plugin/plugin.json` +
  `marketplace.json` bundling the MCP server (command to launch it) and the skill.
  One-command install. (A `userConfig` credential prompt is **deferred** — the
  current `plugin.json` ships none.) Credentials are supplied at runtime instead:
  users authenticate by calling the `waveassist_login` tool with their UID (or by
  setting `WAVEASSIST_UID`).
- **Cursor mirror** (`cursor/`): `.cursor/mcp.json` (same server) + the skill
  written into `.cursor/skills/`. No logic in hooks (Cursor has none) — everything
  lives in the tool or the skill.
- **MCP server runtime:** Python + FastMCP, launchable via `uvx`/`python -m`,
  stdio transport (works in both hosts).

---

## 9. Demo target (the v1 proof)

**ClickUp → weekly email.** Two nodes:
- `fetch_clickup` (starting node, `cron: "0 9 * * 1"`): read `clickup_token` from
  KV, pull tasks via the ClickUp REST API, `store_data` them.
- `email_summary` (`run_after: [fetch_clickup]`): optionally `call_llm` to
  summarize, build inline-styled HTML, `is_test_run()`-guard the send,
  `waveassist.send_email(...)`, write `display_output`.

Live-tested against test UID `2fec42dd…3ccf` end-to-end:
generate → `set_key` → `deploy_agent` (unarmed) → `test_agent` (dry run) → confirm
green → `arm_schedule`.

---

## 10. Risks & how v1 handles them

| Risk | v1 handling |
|---|---|
| Unscoped UID auth | Acceptable for private beta; scoped key is the hardening-phase public gate |
| Plaintext KV secrets / keys in chat | Warn in v1; out-of-band entry + write-only type in hardening phase |
| No local sandbox | Deploy-unarmed → `run_dag` test → arm-on-green; `is_test_run()` guards stop test sends |
| Generation quality | Test-before-arm (v1) + golden reference patterns; server-side validator deferred |
| Re-deploy duplicates | Idempotent `deploy_agent` via local registry; routes create vs upgrade |
| Cross-host drift | Only MCP + SKILL are portable; nothing critical in hooks |

---

## 11. Build sequence

1. Scaffold repo + FastMCP skeleton + config/credential resolution.
2. WaveAssist API client (envelope handling, per-endpoint encoding).
3. MCP tools (login, status, deploy_agent, set_key, test_agent, run_logs,
   arm/disarm).
4. SKILL bundle (orchestration + integrations-without-composio + copy 3 skills).
5. Packaging (plugin + Cursor mirror + install README).
6. Mocked unit tests.
7. Live E2E: ClickUp → weekly email against the test UID.
8. README + memory + report.
