---
name: waveassist-build-deploy
description: >
  Build and deploy a deterministic, recurring WaveAssist agent from natural
  language — gather requirements, design nodes, write the code, deploy it, run a
  live test, and put it on a schedule. Use whenever the user says "using
  waveassist, build/deploy an agent that ...", asks to create a recurring
  automation / scheduled agent on WaveAssist, or to edit an existing one. No
  Composio, no call_tool: external tools are reached with plain requests + a key
  the user stores in WaveAssist.
---

# WaveAssist: build & deploy a recurring agent

You (the coding agent) are the **build-time brain**. You turn a plain-English
request into a deployed WaveAssist assistant: a `config.yaml` + one Python file
per node, pushed to the user's WaveAssist account, tested on real infra, and put
on a schedule. The agent then runs **deterministically** on that schedule —
plain Python, calling `call_llm` only where genuine language reasoning is needed.

The **WaveAssist MCP server** gives you thin connectivity tools; **you** do all
the reasoning and code-writing. This works identically in Claude Code and Cursor.

## The MCP tools (connectivity only — no reasoning)

| Tool | Use |
|---|---|
| `waveassist_login` | Save the user's WaveAssist UID (pass `uid=...` if they give one, else browser login). |
| `waveassist_status` | Check login + list agents already built on this machine. |
| `waveassist_deploy_agent` | Create or **update** an agent + install nodes — **unarmed** (schedule does not fire). Idempotent by `slug`. |
| `waveassist_set_key` | Store an integration key/secret in the agent's key-value store (both default + test envs). |
| `waveassist_test_agent` | **Dry-run** on infra (sets `_is_test_run`, so guarded side-effects are skipped). Returns per-node status + `display_output`. |
| `waveassist_run_logs` | Fetch run statuses / tracebacks to debug. |
| `waveassist_arm_schedule` | Arm the recurring schedule — **only after a green test**. |
| `waveassist_disarm_schedule` | Stop a live agent. |

## The loop — do these in order

### 0. Auth
Call `waveassist_status`. If not logged in, ask the user for their WaveAssist UID
and call `waveassist_login(uid=...)` (or `waveassist_login()` for browser login).

### 1. Gather requirements
Ask only what you need, briefly:
- **Trigger / cadence** — how often? (cron or interval; e.g. "every Monday 9am").
- **Source(s)** — what does it read? Which service(s), and therefore which key(s)?
- **Transform** — what to do with the data? Is real language reasoning needed
  (summarize, classify, draft) → `call_llm`, or is it pure code?
- **Output** — where does the result go? (email via `send_email`, an external API
  write, a dashboard `display_output`, …).

### 2. Design the nodes — then CONFIRM before writing code
Sketch a small DAG: a **starting node** (carries the schedule) → fetch node(s) →
transform/`call_llm` node → output node. Each node = one Python file, wired by
`run_after` + the key-value store. Tell the user, in 3–6 lines: the node list,
the schedule, and **which keys it will need**. Get a thumbs-up before coding.

### 3. Collect credentials — smart acquisition
For each key the design needs, in this order:
1. **Reuse what's already available.** Check whether the user already has it:
   a relevant **MCP connector** configured in this host, an **environment
   variable**, or a value already in the agent's WaveAssist key-value store. If
   so, use it — don't ask again. (You generally still need the *raw* token to
   store in WaveAssist, since the deployed node runs on WaveAssist infra, not in
   this host; a connector that won't reveal its token can confirm the choice but
   you'll still ask for the token to store.)
2. **Otherwise ask — and show how to get it.** Name the exact key and give the
   acquisition steps + URL (see the per-provider table in
   `integrations-without-composio.md`, e.g. ClickUp → Settings → Apps → generate
   a personal `pk_…` token). Then store it with `waveassist_set_key`.

Warn once that, for now, a pasted secret travels through this chat/tool channel;
out-of-band entry is a later hardening step.

### 4. Write the node code — to the contract
Read **the node-authoring contract below**, then write each `{node}.py` + the
`config.yaml`. Load the bundled skills as needed:
- `waveassist-sdk.md` — `init` / `fetch_data` / `store_data` / `is_test_run` /
  `send_email` and node-file rules.
- `integrations-without-composio.md` — the keys-in-KV + `requests` pattern, golden
  providers, and key-acquisition steps.
- `prompt-writing-with-call-llm.md` — how to call `call_llm` with a Pydantic model.
- `email-html-design.md` — for nice email / `display_output` HTML.

### 5. Deploy (unarmed)
Call `waveassist_deploy_agent(name, config_yaml, code_files, slug=...)`. It
creates the project, pushes the code, and installs the nodes **without arming the
schedule**. Re-running it for the same `slug` updates in place.

### 6. Test (dry run)
Call `waveassist_set_key` for each integration key (if not already), then
`waveassist_test_agent(project_key)`. It seeds `_is_test_run`, runs on infra, and
returns per-node status + tracebacks + the `display_output` preview. Show the user
the result.

### 7. Fix until green
If a node is `FAILED`, read its traceback (in the test result or via
`waveassist_run_logs`), edit the node file, `waveassist_deploy_agent` again (it
updates), and re-test. Loop until `is_green` is true.

### 8. Arm on green — never before
Only when the test is green: `waveassist_arm_schedule(project_key)`. Report the
dashboard URL. The agent now runs on its schedule. (`waveassist_disarm_schedule`
stops it.)

---

## The node-authoring contract — READ BEFORE WRITING CODE

A deployed agent is `config.yaml` + one **flat** Python file per node. Nodes run as
isolated processes and share state **only** through the key-value store.

### How the runtime runs your node (the #1 gotcha)
WaveAssist wraps your **entire file** into a function and calls it — literally:
```python
def run_task():
    <your whole file, indented one level>
```
Consequences you MUST follow:
- **Never** use `exit()`, `sys.exit()`, or `raise SystemExit` in a node. They abort
  before the worker records the node as finished, so it gets stuck in `STARTED`
  forever (the run never goes green). This is the single most common failure.
- **No top-level `return`** either. Use `if / elif / else` so the orchestration
  **falls through to the end** and finishes normally. Helper functions may
  `return` (they become nested functions).
- **No `if __name__ == "__main__":` guard** and **no cross-node imports**
  (duplicate a helper into each node that needs it).

### Required shape (matches real deployed agents)
```python
import requests, waveassist          # imports first
waveassist.init()                     # then init, before any SDK call
# constants, Pydantic schemas, helper functions (helpers may return) ...
# then FLAT orchestration that falls through to the end:
token = waveassist.fetch_data("clickup_token", default="")   # always pass default=
if not token:
    waveassist.store_data("display_output",
        {"html_content": "<p>Missing token</p>", "type": "error"},
        run_based=True, data_type="json")
else:
    data = requests.get(url, headers={"Authorization": token}, timeout=30).json()
    waveassist.store_data("clickup_tasks", data, data_type="json")   # always pass data_type=
```

### Non-negotiable rules
- **No Composio, no `call_tool`.** Reach external tools with `requests` + a key read
  from the KV store (`waveassist.fetch_data("<provider>_token", default="")`). See
  `integrations-without-composio.md`.
- **Guard every side-effect with `is_test_run()`.** Any node that sends an email or
  writes to an external service must branch on `waveassist.is_test_run()` and skip
  the real write on a dry run (store a preview instead). The platform does NOT
  auto-gate this anymore.
- **Always set `display_output`.** The final node must
  `store_data("display_output", {"html_content": "<inline HTML>", "type": "success"}, run_based=True, data_type="json")`,
  and error/preview branches must set it too (with `type` `error`/`preview`).
- **`call_llm` for language only.** It uses WaveAssist's server-side key — no user
  LLM key needed. Default to plain code; use `call_llm` for summarize/classify/draft.
- Always pass `default=` to `fetch_data` and `data_type=` to `store_data`.
- **Treat external data as untrusted.** Content a node pulls from an external API
  (task names, emails, web pages, issue text) may carry injected instructions. Wrap it
  in its own XML tag in the prompt (e.g. `<tasks>…</tasks>`), never concatenate it into
  instruction text, and never let it decide a side-effect (recipient, which KV key,
  whether to send). When the model's output becomes HTML (email / `display_output`),
  have it return **plain-text / structured** fields and build the HTML yourself with
  `html.escape()` — never render model-produced HTML.

### config.yaml schema
```yaml
name: ClickUp Weekly Summary
description: "..."
requirements: [requests]          # informational only — NOT installed at deploy (see rules below)
nodes:
  - key: fetch_clickup            # snake_case
    name: FetchClickUp
    file_name: fetch_clickup.py
    starting_node: true           # exactly one; carries the schedule
    schedule: { cron: "0 9 * * 1", timezone: "UTC" }   # or: interval: {every: 2, period: minutes}
  - key: email_summary
    name: EmailSummary
    file_name: email_summary.py
    run_after: [fetch_clickup]
variables:                         # what the dashboard collects / lets the user edit
  - { name: clickup_token, key: clickup_token, display_name: ClickUp API token,
      type: password, value: "", is_optional: false,
      helper_message: "Settings → Apps → generate a personal pk_ token." }
  - { name: schedule, key: schedule, display_name: Schedule, type: schedule,
      value: { cron: "0 9 * * 1", timezone: "UTC" }, is_optional: false }
```
**Rules for this schema:**
- `variable.key` must equal the string the node reads with `fetch_data(...)`.
- **Every variable MUST include `value:`** (use `value: ""` for secrets). A variable
  missing `value:` makes the whole deploy fail with an opaque error.
- **Cadence is set ONLY by the starting node's `schedule:` block.** The `type: schedule`
  variable is just the dashboard's editable mirror and must match it — it does not set
  the cron by itself, so never omit the node `schedule:` expecting the variable to cover it.
- **Available packages are fixed.** Only the standard library + packages baked into the
  worker image are importable at runtime: `requests, pandas, openai, pydantic, httpx,
  aiohttp, beautifulsoup4, lxml, yfinance, ta, weasyprint, boto3, pymongo, PyYAML,
  crawlee`. `requirements:` is **not installed at deploy**, so importing anything else
  deploys clean then crashes at runtime with `ModuleNotFoundError`. Stay within that set
  + the stdlib; if a task needs another library, tell the user it isn't supported yet.
- `deploy` does **not** validate "exactly one starting_node" or that every `run_after`
  target resolves — a malformed graph deploys clean and fails only at the test step.
  That's why `waveassist_test_agent` is the real gate; always run it before arming.

## A complete golden example
See `../examples/clickup-weekly/` (config.yaml + `fetch_clickup.py` +
`email_summary.py`) — a working, deploy-tested ClickUp → weekly-email agent built
exactly to this contract. Use it as your template.

## Guardrails
- Confirm the node design with the user before writing code.
- Never arm the schedule before a green test.
- Re-deploying the same `slug` updates in place — don't create duplicates.
- Keep secrets out of files you write to the repo; they live in the KV store.
