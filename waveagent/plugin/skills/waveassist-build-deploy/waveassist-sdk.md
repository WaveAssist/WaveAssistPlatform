---
name: waveassist-sdk
description: Core WaveAssist SDK patterns — how nodes are structured, why they're structured that way, and the primitives (init, fetch_data, store_data, call_tool) that glue them together.
type: reference
---

# WaveAssist SDK

## What WaveAssist is (the runtime model)

WaveAssist runs **scheduled Python assistants**. An assistant is a
directory with a `config.yaml` declaring its *nodes*, and one Python
file per node. The runtime executes each node as a **fresh Python
process**, piping state between nodes through a key-value store
(DataRun). Nodes don't share memory; they share KV state.

```
  USER / SCHEDULE ───▶  runtime ──▶  node_a.py     (fresh process)
                                     └─▶ fetch_data → do work → store_data
                            │
                            ▼
                         node_b.py     (fresh process — new interpreter)
                         └─▶ fetch_data → do work → store_data
```

Everything about how you structure a node flows from this model:

- **Fresh interpreter per node** → no in-memory caches across nodes.
- **Shared KV store (`DataRun`)** → the only supported cross-node
  handoff.
- **Python subprocess** → `print()` is captured as the run log. A normal
  unhandled `Exception` is caught by the worker and marks the node as
  failed (run still *completes*). But **`sys.exit()` / `exit()` /
  `raise SystemExit` does NOT cleanly end a node** — `SystemExit` is a
  `BaseException`, not an `Exception`, so the worker never catches it and
  never records completion, leaving the node stuck "STARTED" (see "How
  the runtime wraps your node" below). Let orchestration fall through.

## Node file structure — the rules and the WHY

### How the runtime wraps your node

You write a node as a **flat script**, but the platform does not run it
flat. Before execution, `get_code_for_node`
(`WaveAssistApi/.../Utils/utils.py`) wraps the *entire* file into a
function — literally `def run_task():\n` followed by your code indented
one level — and the worker (`WaveAssistWorkerEngine/Engine/TaskRunner.py`)
`exec()`s that, then *calls* `run_task()`, wrapped in `except SyntaxError
/ NameError / Exception`. Two consequences flow from this:

- **No top-level `return`.** In the flat file you write, a top-level
  `return` is a `SyntaxError` (tooling parses the un-wrapped file as a
  module). It only becomes legal *after* wrapping. So never put a
  `return` at module level; structure with `if/elif/else` so the file
  falls through to its end. (Helpers may `return` — after wrapping they
  are nested functions.)
- **No `exit()` / `sys.exit()` / `raise SystemExit`.** These raise
  `SystemExit`, a `BaseException` — **not** an `Exception` — so the
  worker's `except Exception` does **not** catch it. It propagates out of
  `run_task()` *before* the worker can record `TASK_COMPLETED`, leaving
  the node **stuck in "STARTED" status forever**. To stop early on an
  expected/recoverable condition, write your `display_output` and let
  orchestration fall through. To mark the node *failed*, `raise` a normal
  `Exception` — that the worker catches and records as completed-with-error.

### No `__main__` guard

```python
# WRONG
if __name__ == "__main__":
    main()

# RIGHT
# orchestration runs at module import; no guard.
fetch_data("x")
...
store_data("y", ...)
```

**Why:** the runtime invokes a node by running the file as a script —
i.e., it behaves like `__name__ == "__main__"`. But the runtime and
our own tests sometimes *import* the module (e.g. to patch internals).
If orchestration is guarded, imports silently do nothing and the node
appears to succeed with no output. By running orchestration at module
load, both `python node.py` and `import node` produce the same effect.

The side-effect-on-import is why `tests/conftest.py` sets fake `uid`
and `project_key` env vars before any test imports a node — so
`waveassist.init()` succeeds and the node shortcuts to a no-op.

### No cross-file imports between nodes

```python
# WRONG — in node_b.py:
from node_a import some_helper

# RIGHT — duplicate the helper into each node that needs it.
def some_helper(...): ...
```

**Why:** each node runs in a fresh worker with its own `sys.path`. The
deployer packages each node file individually — *sibling node files
are not guaranteed to be importable*. Cross-file imports work in
development (everything is on the local `sys.path`), then fail in
production with `ModuleNotFoundError` at the exact moment you don't
want surprises.

Duplicate helpers across nodes as a deliberate trade-off. The
duplication is small; the isolation guarantee is valuable.

### Helpers at the top, flat orchestration at the bottom

```python
# constants
DEFAULT_MODEL = "anthropic/claude-sonnet-4.6"

# pydantic schemas
class MyResult(BaseModel): ...

# helper functions
def build_prompt(...): ...
def compose_output(...): ...

# flat orchestration at the bottom
print("Node starting...")
x = waveassist.fetch_data("x", default={})
result = build_prompt(x)
...
waveassist.store_data("y", result, data_type="json")
print("Node done.")
```

**Why:** helpers are testable in isolation (imports don't trigger
them). Orchestration is a linear recipe so anyone can read it
top-to-bottom and know what the node does. The layout mirrors how you
read the node's `print()` output in the run log.

### `waveassist.init()` at module load (just after imports)

```python
import waveassist
# ...other imports...
waveassist.init()
```

**Why:** every SDK call below this line — `fetch_data`, `store_data`,
`call_tool`, `call_llm` — needs the login token and project key
resolved. `init()` reads them from env (worker-provisioned in prod;
`.env` in dev). Calling it early gives a clean failure at top-of-file
if creds aren't set, instead of 300 lines later.

Use `waveassist.init(check_credits=True)` in downstream nodes (it
raises only when `credits_available` is exactly `"0"`; missing key is
treated as available). The first node in a chain that needs a
credit-spending call should use
`waveassist.check_credits_and_notify(required_credits, assistant_name)`
and abort if it returns `False`.

### `print()` over loggers

The runtime captures stdout for the run log. `print()` is the
ergonomic choice. Plain messages like `"WaveMaker: fetching actions..."`
are fine. Avoid `logging.basicConfig` — it competes with the runtime's
own logger setup.

## The primitives

### `init(uid=None, project_key=None, check_credits=False)`

Resolves creds from args or env (`uid`, `project_key`). Must be called
before any data/LLM/tool calls. Safe to call multiple times.

### `fetch_data(key, default=None, run_based=False)`

Read a KV value. **Always pass `default=`** — missing keys return the
default; API failures also return the default. Without it you'll get
tracebacks you can't recover from.

```python
prompt_history = waveassist.fetch_data("prompt_history", default=[])
spec           = waveassist.fetch_data("intent_spec",   default={})
name           = waveassist.fetch_data("user_name",     default="")
```

**DataFrame gotcha:** `fetch_data("df") or pd.DataFrame()` raises
`"The truth value of a DataFrame is ambiguous."` Always use
`default=pd.DataFrame()` instead.

`run_based=True` scopes the key to the current run (cleared between
runs). Use for artefacts like `display_output`.

### `display_output` shape (dashboard contract)

The WaveAssist dashboard renders a run's "View Output" by reading
`display_output` and looking for `html_content` (a string of HTML).
**If `html_content` isn't present, the dashboard shows a fallback
message instead of your output** — even if other useful fields are set.

Always store a dict shaped like this:

```python
display_output = {
    "html_content": "<h2>Title</h2><p>Body...</p>",  # REQUIRED — what the dashboard renders
    # Anything else you want to keep alongside (status, structured data,
    # links, channel name, etc.) — these are kept for debugging / programmatic
    # consumers but the dashboard ignores them.
    "type": "success",
    "channel_name": "wavemarker",
}
store_data("display_output", display_output, run_based=True, data_type="json")
```

Keep the HTML self-contained and inline-styled (no external CSS, no
script tags). The dashboard renders it inside an existing modal — keep
font sizes reasonable (`font-size: 14px–24px`). For a notification-style
output, an `<h2>` + `<p>` (or a `<ul>` of summary lines) is enough.

**Failure / preview cases must also set `html_content`:**

```python
# Test-run preview (when is_test_run() is True)
display_output = {
    "html_content": (
        "<h2>Preview: Slack message ready to send</h2>"
        "<p>This is a test run. The digest below would be posted to "
        "<b>#wavemarker</b>:</p>"
        f"<pre style='white-space: pre-wrap;'>{escape(digest_text)}</pre>"
    ),
    "type": "preview",
}

# Hard failure (auth missing, API error, etc.)
display_output = {
    "html_content": (
        "<h2>Could not post digest</h2>"
        "<p>Reconnect your Slack account in the assistant settings, then "
        "re-run.</p>"
    ),
    "type": "error",
}
```

### `store_data(key, value, data_type=None, run_based=False)`

Write a KV value. **Always pass `data_type`** so retrieval coerces
back to the right type:

```python
store_data("intent_spec",  spec_dict,  data_type="json")
store_data("user_prompt",  prompt,     data_type="string")
store_data("ohlc_df",      df,         data_type="dataframe")
```

`data_type` values: `"json"`, `"string"`, `"dataframe"`. Without it,
downstream nodes must add `isinstance` checks.

Returns `True` / `False`. Non-fatal failures are common; check the
return if it matters.

### `call_tool(action_slug, arguments)`

Execute a Composio action through the WaveAssist backend. The caller's
connection is resolved automatically from the uid.

```python
result = waveassist.call_tool("SLACK_LIST_CONVERSATIONS", {})
# → {"test_preview": False, "result": {...raw provider response...}}
```

**Test-run gating:** when `is_test_run()` is `True`, write-type
actions are NOT sent to the provider. Instead the intended call is
stored under a generated `test_preview_*` KV key and you get back
`{"test_preview": True, "key": "...", "action_slug": ..., "arguments": ...}`.
Reads are unaffected.

Raises `RuntimeError` on any failure envelope; catch with generic
`Exception`.

### `call_llm(model, prompt, response_model, ...)`

Structured LLM call with Pydantic-enforced output. See the dedicated
skill `prompt-writing-with-call-llm.md` for everything this does.

Routes through **OpenRouter** by default. A project can store an
`llm_models` registry to route individual models to Azure (chat or the
Responses API), a Claude subscription (`claude_cli_token`, runs headless on
the WaveAssist cloud workers), the local Claude CLI, or OpenRouter — per
model, no code change. See the provider note in
`prompt-writing-with-call-llm.md`.

### `is_test_run()` / `check_credits_and_notify()` / `send_email()`

- `is_test_run()` — returns `True` during the user's "dry-run preview"
  phase. Branch on it if a node has side effects you want gated.
- `check_credits_and_notify(required, assistant_name)` — returns
  `False` when the user is out of credits; the SDK handles the
  notification. The first node in a chain should check it, and on `False`
  store a clear `display_output` and then **skip the rest of the work via
  `if/else`** (do NOT `exit(0)` — see "How the runtime wraps your node").
  If you want the run recorded as failed, `raise Exception(...)` *after*
  storing the `display_output` (a normal `Exception` is caught by the
  worker; `SystemExit` is not).
- `send_email(subject, html_content, attachment_file=..., raise_on_failure=True)`
  — use for the final notification. On final/notification nodes, pass
  `raise_on_failure=False` and **always** also `store_data("display_output",
  display_output, run_based=True, data_type="json")` so the run isn't
  lost if email fails.

## Error handling

Wrap tool/LLM/HTTP calls in `try / except Exception`. Catching the
generic class is fine — the SDK raises `RuntimeError` /
`LLMCallError` / `LLMFormatError` and you typically have one
fallback path for "it didn't work." Only specialize when you have a
different flow per exception type (rare).

```python
try:
    raw = waveassist.call_tool(slug, args)
except Exception as exc:
    print(f"call_tool failed: {exc}")
    return fallback_result()
```

## Worked example — a minimal node

A complete node that reads a user prompt, asks an LLM to summarize it,
and stores the summary:

```python
"""
Example node — summarize the user_prompt using an LLM.
"""
from typing import Literal
import waveassist
from pydantic import BaseModel, Field

DEFAULT_MODEL = "anthropic/claude-sonnet-4.6"
waveassist.init()


class Summary(BaseModel):
    status: Literal["ready", "empty"]
    summary: str = Field(description="2-3 sentence plain-English summary.")
    tone: Literal["formal", "casual", "technical"]


def build_prompt(user_prompt: str) -> str:
    return f"""<role>
You are a summariser. Produce a short, faithful summary of the input.
</role>

<input>
{user_prompt}
</input>

Return a Summary.
"""


# orchestration
print("Example: starting...")
user_prompt = waveassist.fetch_data("user_prompt", default="")
model = waveassist.fetch_data("model_name", default=DEFAULT_MODEL)

if not user_prompt.strip():
    out = Summary(status="empty", summary="", tone="casual").model_dump()
else:
    try:
        result = waveassist.call_llm(
            model=model,
            prompt=build_prompt(user_prompt),
            response_model=Summary,
            max_tokens=600,
            temperature=0.2,
            should_retry=True,
        )
        out = result.model_dump()
    except Exception as exc:
        print(f"LLM failed: {exc}")
        out = Summary(status="empty", summary="", tone="casual").model_dump()

waveassist.store_data("summary", out, data_type="json")
print(f"Example: stored summary (status={out['status']}).")
```

Every WaveAssist node follows this shape: constants → schemas →
helpers → orchestration.

## Common pitfalls (checklist)

- [ ] I passed `default=` to every `fetch_data`.
- [ ] I passed `data_type=` to every `store_data`.
- [ ] No `if __name__ == "__main__":` guard.
- [ ] No `from sibling_node import ...`.
- [ ] No `exit()`/`sys.exit()`/`raise SystemExit`; no top-level `return` — let orchestration fall through to the end (those leave the node stuck "STARTED"; raise a normal `Exception` if you truly need to fail).
- [ ] Orchestration is flat at the bottom, helpers at the top.
- [ ] `waveassist.init()` is called before any SDK call.
- [ ] Errors from tool/LLM/HTTP calls are caught; the node still writes *something* to KV so downstream nodes see a sensible state.
- [ ] Print statements describe what's happening, not what has failed abstractly.

## See also

- `prompt-writing-with-call-llm.md` — everything about `call_llm`.
- `waveassist-integrations.md` — everything about toolkit discovery
  and `call_tool`.
