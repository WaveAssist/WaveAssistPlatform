# WaveAssist MCP — connectivity, run-now, run-confirmation, input-types

**Date:** 2026-06-08
**Status:** Approved design (pending spec review)
**Scope:** `mcp/` only. No changes to WaveAssistApi or WaveAssistDashboard.

## 1. Context & motivation

A demo of the WaveAgent build/deploy flow worked end to end, but surfaced four
rough edges. All four are addressed entirely inside the MCP server (`mcp/`); the
backend already exposes everything needed.

The MCP server today exposes 9 tools (`server.py`) and a thin HTTP client
(`client.py`) over the WaveAssist API. The build reasoning lives in the bundled
skill (`mcp/src/waveassist_mcp/_skill/`, also mirrored in `skill/`). Findings from
reading the backend (`WaveAssistApi`) and dashboard (`WaveAssistDashboard`):

- **No connectivity / live project list.** `waveassist_status` only lists the
  *local* registry (agents built on this machine). There is no "is my UID valid"
  check and no live account project list. **But** `manage/fetch_all_projects/`
  already exists (POST `uid`, READ access, returns `project_array`) — no login,
  no GitHub, no super-admin. So this is buildable now.
- **Deploy ≠ run, and arm ≠ run-now.** `deploy_agent` installs nodes unarmed;
  `arm_schedule` (`deploy_project`) creates a recurring `PeriodicTask` that only
  fires on its next cron tick. The only immediate execution is `test_agent`
  (`run_dag` against the `_test` env with `_is_test_run=true`) — a *dry* run.
  There is no tool to run the **live** agent once, now.
- **Test-before-arm is not enforced.** `SKILL.md` says "arm on green — never
  before," but nothing in code checks it. The real goal: the build flow should
  always run the agent at least once and **confirm SUCCESS** before arming.
- **Input types are under-documented.** The dashboard (`InputFactory.tsx`)
  supports a rich set of variable `type:` values; the build guide documents only
  `password` and `schedule`, so the build agent never uses `number`, `boolean`,
  `select`, `url`, `textarea`, etc.

### Decisions locked during brainstorming
- **Authoring path stays GitHub-based.** The direct node API (`manage/create_node/`,
  `manage/update_code/`) is **super-admin gated** (`validate_super_admin`,
  manage_views.py:671, :877), so it is not usable for normal users. The
  GitHub/WaveMaker path (`materialize_assistant` → `deploy_template` →
  `upgrade_assistant`) remains the only user-accessible way to author node code.
  No change here.
- **Integrations use direct keys, not OAuth, not Composio.** The OAuth provider
  input types in the dashboard are temporary / not fully wired; only GitHub,
  ClickUp, and HubSpot work, and even those are better reached with a direct
  PAT/API key (durable, no refresh) for unattended scheduled runs. If a provider
  is OAuth-only with no key option, declare it "not supported yet" — do **not**
  broker tokens via Composio in the host.
- **Run-now is a separate tool**, not folded into arm.
- **arm warning checks live** via `fetch_dag_runs`, not local state.

## 2. Goals / non-goals

**Goals**
1. A read-only tool to verify the UID and list live projects.
2. A tool to run the live agent once, immediately (distinct from dry-run test
   and from arming).
3. Make the build flow always confirm a successful run before arming, with a
   non-blocking warning on `arm_schedule` if no green run is found live.
4. Document the full, working set of variable input types and the direct-key
   integration rule in the build guide.

**Non-goals**
- No backend (WaveAssistApi) or dashboard changes.
- No hard block on `arm_schedule` (warn only).
- No switch to the direct node API; no OAuth; no Composio.
- No new variable input *types* (dashboard already has enough).

## 3. Change 1 — `waveassist_list_projects` (connectivity + live list)

**Client:** add `WaveAssistClient.fetch_all_projects(uid) -> list`:
- `POST /manage/fetch_all_projects/`, form-encoded, field `uid`.
- Returns `data["project_array"]` (list of project dicts), `[]` if absent.

**Tool:** `waveassist_list_projects() -> dict`:
- Resolve UID (`_require_uid()`); call `fetch_all_projects`.
- Return `{ok, count, projects: [{project_key, name, ...}], uid: <masked>}`.
- A successful return *is* the connectivity check (valid UID ⇒ list returned;
  invalid UID ⇒ backend error envelope surfaced via `_err`).
- Keep the field set small and stable (project_key, name, plus whatever
  `get_dict()` returns that is obviously useful — do not dump everything).

No separate `ping` tool — `list_projects` covers both needs.

## 4. Change 2 — `waveassist_run_agent` (live one-off run)

**Tool:** `waveassist_run_agent(project_key, start_node_key="", timeout_seconds=120) -> dict`.

Behaviour mirrors `test_agent` but against the **default** (live) environment with
the test flag **off**:
1. `env = f"{project_key}_default"`.
2. Baseline existing runs (`fetch_dag_runs`) to identify the new one.
3. `set_data_for_key(... "_is_test_run", "false", "string")` on `env`.
4. `run_dag(uid, project_key, env, start_node_key or None)`.
5. Poll `fetch_dag_runs` / `fetch_node_runs` until terminal or timeout (same
   correlation-by-newest-fresh-run logic as `test_agent`).
6. Fetch `display_output` (run-based, then fallback) for the new run.
7. Return `{ok, overall, is_green, run_id, dag_key, nodes:[...], display_output_preview}`.

This is real execution — side-effects fire. The docstring must say so explicitly
and note arm still only governs the recurring schedule.

**Refactor:** `test_agent` and `run_agent` share ~90% logic. Extract a private
helper `_run_and_poll(client, uid, project_key, env, start_node_key, timeout)`
returning the structured result; `test_agent` calls it with `env=_test` and sets
the flag `true`, `run_agent` with `env=_default` and flag `false`. Keeps both
tools thin and behaviour identical.

## 5. Change 3 — run-confirmation flow + soft arm warning

**Skill (`SKILL.md` + bundled `_skill/SKILL.md`):** rewrite steps 6–8 so the loop
is explicit and success-confirming:
- After deploy, **always** run at least once: dry `test_agent` first; optionally
  a live `run_agent` when the user wants to see real output.
- Read logs / per-node status and **confirm `overall == SUCCESS`** before arming.
  "Confirm success is the goal" is the written gate.
- Only then `arm_schedule`. State plainly that arm schedules the recurring run on
  its cron — it does not run immediately; use `run_agent` for an immediate live run.

**Code (`arm_schedule`):** add a non-blocking pre-arm check.
- Before arming, call `fetch_dag_runs` for both `{project_key}_test` and
  `{project_key}_default`.
- If neither environment has any run with `status == "SUCCESS"`, include
  `warning: "No successful run found for this project (test or live). Arming
  anyway — run waveassist_test_agent / waveassist_run_agent and confirm green
  first."` in the (still `ok: true`) result.
- Never blocks; arming proceeds regardless. One extra read call, no new state.

## 6. Change 4 — input-types documentation + integration rule

Add a **"Variable types"** subsection to the build guide (`SKILL.md` config.yaml
schema area, and the bundled copy). Document the **common, working** set with a
one-line "when to use" each:

| type | use |
|---|---|
| `text` (default) | free text |
| `password` / `secret` | API keys / tokens (masked) |
| `number` | numeric input |
| `boolean` / `toggle` | on/off |
| `select` / `dropdown` | one of `options:` |
| `multiselect` | many of `options:` |
| `list` / `chips` | free list of strings |
| `email` / `url` / `tel` | validated text |
| `textarea` | long text |
| `schedule` | cron/interval picker (supports preset `options:`) |

Plus a short note: domain selectors `stock` / `crypto` / `commodity` exist for
finance agents. The full list lives in `WaveAssistDashboard/InputFactory.tsx`.

**Integration rule (explicit in the guide):**
- Reach every external service with `requests` + a **direct key** read from KV
  (`type: password`/`secret` variable). This is the existing no-Composio pattern.
- **Do not use OAuth provider input types** (`slack`, `gmail`, `jira`, …) — they
  are not fully wired; only GitHub, ClickUp, HubSpot partially work, and even
  those should use a direct PAT/API key for durable unattended runs.
- If a provider is **OAuth-only with no API-key option**, tell the user it is not
  supported yet. Never broker a token via Composio in the host.

## 7. Files touched (all under `mcp/`, plus mirrored skill)

- `mcp/src/waveassist_mcp/client.py` — add `fetch_all_projects`.
- `mcp/src/waveassist_mcp/server.py` — add `waveassist_list_projects`,
  `waveassist_run_agent`; extract `_run_and_poll`; add arm warning.
- `mcp/src/waveassist_mcp/_skill/SKILL.md` — steps 6–8 rewrite, variable-types
  table, integration rule.
- `skill/SKILL.md` — keep mirrored copy in sync.
- `mcp/tests/test_tools.py`, `mcp/tests/test_client.py` — tests (below).
- `mcp/README.md` / top-level docs — list the two new tools.

## 8. Testing

- `client.fetch_all_projects` — mock the form POST; assert it returns
  `project_array` and `[]` on a missing/empty envelope.
- `waveassist_list_projects` — success path (count + masked uid) and
  not-authenticated path (`_require_uid` raises → `ok:false`).
- `_run_and_poll` / `waveassist_run_agent` — mock the run/poll sequence; assert
  it sets `_is_test_run=false` on `_default`, returns `is_green` on SUCCESS, and
  surfaces a node traceback on FAILED.
- `arm_schedule` warning — mock `fetch_dag_runs` returning no SUCCESS ⇒ result
  contains `warning`; returning a SUCCESS ⇒ no warning.
- Reuse existing `conftest.py` HTTP mocking patterns.

## 9. Out of scope / future

- Relaxing the super-admin gate on `manage/create_node/` to enable a
  GitHub-free authoring path (backend change).
- Fully wiring OAuth provider integrations (backend/dashboard).
- Out-of-band secret entry (noted as a later hardening step in current docs).
