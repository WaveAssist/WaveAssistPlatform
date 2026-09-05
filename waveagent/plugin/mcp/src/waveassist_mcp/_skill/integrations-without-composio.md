---
name: integrations-without-composio
description: How a generated WaveAssist node connects to any external tool using plain requests + a user API key from the KV store — no Composio, no call_tool. Load for any node that touches an external service.
type: reference
---

# Integrations without Composio

A generated WaveAssist node talks to an external tool with **plain
`requests` + a user API key that lives in the KV store**. There is no
Composio, no `call_tool`, no catalog. The node:

1. reads the key from the KV store via `fetch_data`,
2. guards (with an error `display_output`) if the key is missing —
   **without an early `exit()`/`return`**; it sets an error flag and lets
   the happy path be skipped so the file still falls through to the end
   (see "Why no `exit()`/`return`" below),
3. calls the provider's REST API with `requests` + the right auth header,
4. classifies HTTP errors (401/403/429/5xx) into a helpful message,
5. stores the result to KV for the next node.

This is exactly how GitZoid hits the GitHub REST API. GitZoid is the
canonical template — its node code is quoted verbatim below.

> Composio used to handle two things for free: per-user auth, and
> automatic test-run gating on writes. **Both are now your job.** Auth
> is a key you read from KV (this doc). Test-gating is a manual
> `is_test_run()` branch on every side effect (see §2). Don't forget
> the second one — without Composio, nothing stops a dry-run from
> POSTing to the user's real account.

Everything in `waveassist-sdk.md` still applies: flat script, no
`def main`, no `__main__` guard, `init()` right after imports, always
pass `default=` to `fetch_data` and `data_type=` to `store_data`, and
every node — including failure paths — must write a `display_output`
with `html_content`.

## 1. The core pattern

Read the key, guard, call, classify, store. This is the canonical shape
GitZoid's `post_comment.py` uses (the token read, the guard, the
`Authorization` header, the status-code classification):

```python
import html
import requests
import waveassist

API_BASE = "https://api.clickup.com/api/v2"   # the provider's REST base
PROVIDER_TOKEN_KEY = "clickup_token"          # KV key (see §3)
PROVIDER_NAME = "ClickUp"
SETTINGS_HINT = (
    "Generate a personal token at "
    "https://app.clickup.com/settings/apps and save it in the "
    "assistant settings."
)

waveassist.init()


def error_output(message: str) -> dict:
    """Standard error display_output. Always include html_content."""
    return {
        "html_content": (
            "<div style=\"font-family:Inter,-apple-system,sans-serif;"
            "color:#0f172a;max-width:640px;padding:16px;\">"
            f"<h2 style=\"font-size:18px;color:#b91c1c;margin:0 0 8px;\">"
            f"Could not reach {html.escape(PROVIDER_NAME)}</h2>"
            f"<p style=\"font-size:14px;line-height:1.45;\">{html.escape(message)}</p>"
            "</div>"
        ),
        "type": "error",
    }


def classify_http_error(status_code: int, body: str) -> str:
    """Turn a non-2xx status into a user-facing reason."""
    if status_code in (401, 403):
        return (
            f"{PROVIDER_NAME} rejected the API key (HTTP {status_code}). "
            f"The token may be wrong, expired, or missing a scope. {SETTINGS_HINT}"
        )
    if status_code == 429:
        return f"{PROVIDER_NAME} rate-limited the request (HTTP 429). Try again later."
    if 500 <= status_code < 600:
        return f"{PROVIDER_NAME} had a server error (HTTP {status_code}). Transient — retry next run."
    return f"{PROVIDER_NAME} returned HTTP {status_code}: {body[:300]}"


# --- orchestration ---
# Branch with if/elif/else so the file FALLS THROUGH to the end on every
# path. Do NOT use exit()/sys.exit()/raise SystemExit, and do NOT use a
# top-level return — see "Why no exit()/return" below. On any failure,
# write the error display_output and let the happy path be skipped.
token = waveassist.fetch_data(PROVIDER_TOKEN_KEY, default="")

if not token:
    # Guard: key missing. Write the error output; happy path is skipped.
    print(f"Missing {PROVIDER_TOKEN_KEY}; cannot call {PROVIDER_NAME}.")
    waveassist.store_data(
        "display_output",
        error_output(f"No {PROVIDER_NAME} API key is connected. {SETTINGS_HINT}"),
        run_based=True,
        data_type="json",
    )
    # No early exit — downstream nodes simply find no new KV data.
else:
    headers = {"Authorization": token, "Content-Type": "application/json"}
    resp = None
    try:
        resp = requests.get(f"{API_BASE}/team", headers=headers, timeout=30)
    except requests.RequestException as exc:
        print(f"Network error calling {PROVIDER_NAME}: {exc}")
        waveassist.store_data(
            "display_output",
            error_output(f"Network error reaching {PROVIDER_NAME}: {exc}"),
            run_based=True, data_type="json",
        )

    if resp is None:
        pass  # network error already reported above; fall through to the end.
    elif resp.status_code != 200:
        reason = classify_http_error(resp.status_code, resp.text)
        print(reason)
        waveassist.store_data(
            "display_output", error_output(reason), run_based=True, data_type="json",
        )
    else:
        teams = resp.json().get("teams", [])
        waveassist.store_data("clickup_teams", teams, data_type="json")
        print(f"Fetched {len(teams)} ClickUp teams.")
```

**Why no `exit()`/`return` — the `run_task()` wrapping.** Before running
a node, the platform wraps the *entire* flat node file into a function:
`get_code_for_node` (`WaveAssistApi/.../Utils/utils.py`,
`def run_task():` + your code indented one level), and the worker
(`WaveAssistWorkerEngine/Engine/TaskRunner.py`) does `exec(...)` then
calls `run_task()`, wrapped in `except SyntaxError / NameError /
Exception`. The catch: `SystemExit` (raised by `exit()`, `sys.exit()`,
or `raise SystemExit`) is a **`BaseException`, not an `Exception`** — so
it is **not caught**. It propagates out of `run_code()` and out of
`run()` *before* the worker logs `TASK_COMPLETED`, leaving the node
**stuck in "STARTED" status forever** (verified live: a node that did
`raise SystemExit(0)` after writing `display_output` never completed;
rewriting it to fall through made it SUCCESS). A top-level `return` is
also wrong in the *flat* file — tooling parses the un-wrapped file as a
module, where a top-level `return` is a `SyntaxError`. So: structure the
orchestration with `if/elif/else` and `try/except` so it always reaches
the end and finishes normally. (Helper functions may `return` freely —
after wrapping they are nested functions, so their `return` is legal.)

**What about marking a node *failed*?** If you genuinely want the run
recorded as failed (a real code bug / broken invariant), raise a normal
`Exception` (or `RuntimeError`) — that IS caught by the worker, which
records the run as completed-with-error. That's what GitZoid does when a
token vanishes *mid-pipeline* after upstream nodes already produced work
to post: it writes the error `display_output`, then `raise Exception(...)`.
But for an expected, recoverable state (missing key, provider 4xx/5xx),
don't raise at all — write the error `display_output` and fall through,
so the run completes green with a readable output and downstream nodes
find no new KV data (their `fetch_data(..., default=...)` no-ops).

> **Read the token defensively.** GitZoid does
> `access_token = waveassist.fetch_data("github_access_token") or ""` —
> the `or ""` collapses both a missing key and an explicit `None` to the
> empty string the guard checks. Use `default=""` and/or `or ""`.

## 2. The `is_test_run()` rule (mandatory for every side effect)

Composio used to auto-gate writes during a dry run. That is gone. **Now,
every node that performs a side effect — sending email, POSTing,
PUTting, PATCHing, DELETEing, or otherwise mutating an external service —
MUST branch on `waveassist.is_test_run()` and skip the real write.**

Reads (GET) run normally in a test run. Only writes are gated.

```python
def build_task_payload(...) -> dict:
    return {"name": "...", "description": "..."}


payload = build_task_payload(...)

if waveassist.is_test_run():
    # Dry run: do NOT call the provider. Preview what WOULD happen.
    print("Test run: skipping real ClickUp write.")
    preview = (
        "<div style=\"font-family:Inter,-apple-system,sans-serif;padding:16px;\">"
        "<h2 style=\"font-size:18px;\">Preview: ClickUp task ready to create</h2>"
        "<p style=\"font-size:14px;\">This is a test run. When enabled, this task "
        "would be created:</p>"
        f"<pre style=\"white-space:pre-wrap;font-size:12px;\">{html.escape(str(payload))}</pre>"
        "</div>"
    )
    waveassist.store_data(
        "display_output", {"html_content": preview, "type": "preview"},
        run_based=True, data_type="json",
    )
else:
    # Real run: perform the write.
    resp = requests.post(
        f"{API_BASE}/list/{list_id}/task", headers=headers, json=payload, timeout=30,
    )
    # ...classify_http_error / store result exactly as in §1...
```

**Why this is non-negotiable:** without the branch, a user's "preview
before I turn this on" dry run would create real tasks, send real
messages, or fire real webhooks. The test run is supposed to be safe.
Outbound email via `waveassist.send_email` is also a side effect —
gate it the same way (preview the HTML instead of sending). GETs to
read data do not need gating.

## 3. KV key naming + config.yaml mapping

The dashboard collects a credential because `config.yaml` declares a
`variable`. The node reads it from KV under a **`<provider>_<thing>`,
lowercase, snake_case** key. Match the two exactly — a typo means the
node reads `""` and guards out forever.

Conventions seen in production:

| Provider | KV key the node reads | Notes |
|---|---|---|
| GitHub | `github_access_token` | GitZoid's auth token. Also `github_selected_resources` for the picked repos. |
| ClickUp | `clickup_token` | Personal API token, sent raw in `Authorization`. |
| Notion | `notion_token` | Internal integration token, sent as `Bearer`. |
| Generic | `<provider>_token` / `<provider>_api_key` | Pick one and use it consistently. |

GitZoid's `config.yaml` declares a typed `github` variable; the platform
provisions the connection and the node reads `github_access_token` and
`github_selected_resources` from KV. For a plain API key, declare a
`password`-type variable so the dashboard renders a masked input:

```yaml
variables:
  - name: clickup_token
    key: clickup_token            # <-- becomes the KV key the node reads
    display_name: ClickUp API token
    type: password                # masked input in the dashboard
    value: ""                     # REQUIRED on every variable (use "" for secrets)
    is_optional: false
    helper_message: "Settings → Apps → Generate (personal API token)."
```

The `key` here is the exact string you pass to
`waveassist.fetch_data("clickup_token", default="")`. Keep them
identical. If a node also needs a non-secret choice (a list id, a model
name), add a separate plain variable — don't overload the token field.

## 4. Golden providers

Each entry: API base, auth header shape, one real endpoint call,
response handling. All use the §1 skeleton (guard the key, classify
errors); only the base/header/endpoint differ.

### ClickUp (REST, personal token, raw in header)

- **Base:** `https://api.clickup.com/api/v2`
- **Auth header:** `{"Authorization": token}` — **raw token, no `Bearer`
  prefix.** This trips people up; ClickUp does not use Bearer.
- **Read example — your teams (workspaces):**

```python
headers = {"Authorization": token}
resp = requests.get("https://api.clickup.com/api/v2/team", headers=headers, timeout=30)
# resp.json() -> {"teams": [{"id": "...", "name": "..."}, ...]}
```

- **Write example (gate behind `is_test_run()`):** `POST
  /list/{list_id}/task` with `json={"name": "...", "description": "..."}`.
  Success is HTTP 200, body has the created task's `id`.

### GitHub (REST, token)

- **Base:** `https://api.github.com`
- **Auth header:** `{"Authorization": f"Bearer {token}", "Accept":
  "application/vnd.github+json"}`. GitHub accepts both `Bearer <token>`
  and the legacy `token <token>` — GitZoid uses `token` in
  `fetch_pull_requests.py` and `Bearer` in `post_comment.py`; both work.
- **Read example — open PRs (verbatim from GitZoid):**

```python
headers = {
    "Authorization": f"token {access_token}",
    "Accept": "application/vnd.github+json",
}
prs_url = f"https://api.github.com/repos/{repo_path}/pulls"
params = {"state": "open", "sort": "created", "direction": "desc", "per_page": 100}
response = requests.get(prs_url, headers=headers, params=params)
if response.status_code != 200:
    print(f"Failed to fetch PRs for {repo_path}: {response.status_code}")
    return [], False
open_prs = response.json()
```

- **Write example — post a PR comment (GitHub auth + write-call pattern).**
  You MUST add the `is_test_run()` gate yourself. Note GitZoid's own
  `post_comment.py` does **not** gate its write, so don't copy it as a gating
  exemplar — the canonical gating example is `examples/clickup-weekly/email_summary.py`.

```python
if waveassist.is_test_run():
    waveassist.store_data("display_output",  # preview only — never POST on a dry run
        {"html_content": "<p>Preview: would post a PR comment.</p>", "type": "preview"},
        run_based=True, data_type="json")
else:
    url = f"https://api.github.com/repos/{repo_path}/issues/{pr_number}/comments"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    resp = requests.post(url, headers=headers, json={"body": body})
    if resp.status_code != 201:
        print(f"Failed to post comment (HTTP {resp.status_code}): {resp.json()}")
```

### Notion (REST, Bearer token)

- **Base:** `https://api.notion.com/v1`
- **Auth header:** `{"Authorization": f"Bearer {token}",
  "Notion-Version": "2022-06-28", "Content-Type": "application/json"}`.
  The **`Notion-Version` header is required** — omit it and every call
  400s.
- **Read example — query a database:**

```python
headers = {
    "Authorization": f"Bearer {token}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}
resp = requests.post(
    f"https://api.notion.com/v1/databases/{database_id}/query",
    headers=headers, json={}, timeout=30,
)
# resp.json()["results"] -> list of page objects
```

- **Write example (gate):** `POST /pages` with a `parent` + `properties`
  payload. Success is HTTP 200.

### Gmail / email

**Outbound (the common case): do NOT call the Gmail API.** Use the SDK:

```python
waveassist.send_email(
    subject="WaveAssist: your digest",
    html_content=html_body,        # built per email-html-design.md
    raise_on_failure=False,        # on final/notification nodes
)
# Then ALWAYS also store display_output so the run isn't lost if email fails.
waveassist.store_data(
    "display_output", {"html_content": html_body, "type": "success"},
    run_based=True, data_type="json",
)
```

`send_email` needs no key — WaveAssist owns delivery. It is still a side
effect: in a test run, preview the HTML instead of sending (§2).

**Inbound (reading a mailbox): this needs the Gmail API, which is OAuth,
not a static key.** A personal token in a header will not work. If a node
must read Gmail, flag that an OAuth connection is required and surface it
to the host agent — don't fabricate a `gmail_token` key. For most
assistants, outbound `send_email` is all you need.

### Generic REST template

For any provider not listed, fill in three blanks — base, header shape,
endpoint — and reuse the §1 skeleton unchanged:

```python
API_BASE = "https://api.<provider>.com/<version>"
headers = {"Authorization": f"Bearer {token}"}   # or {"X-Api-Key": token}, or raw token

resp = requests.get(f"{API_BASE}/<resource>", headers=headers, timeout=30)
if resp.status_code != 200:
    reason = classify_http_error(resp.status_code, resp.text)
    # ...write error_output (in an if/else so the happy path is skipped);
    #    do NOT exit() — fall through to the end (see §1's "Why no exit()").
    print(reason)
    waveassist.store_data(
        "display_output", error_output(reason), run_based=True, data_type="json",
    )
else:
    data = resp.json()
    waveassist.store_data("<provider>_data", data, data_type="json")
```

Auth header shapes you will meet: `Authorization: Bearer <token>` (most
common), `Authorization: <token>` (ClickUp), `X-Api-Key: <token>`, or a
`?api_key=<token>` query param (some legacy APIs). Check the provider's
docs for which; when unsure, `Bearer` is the safe default.

## 5. How to acquire each key (instructions for the host agent)

When the guard in §1 fires because a key is missing, the host agent
tells the user exactly where to get it. Use these verbatim:

- **ClickUp** — Click your avatar (bottom-left) → **Settings** → **Apps**
  → under *API Token*, click **Generate** → copy the `pk_...` token.
  Direct: <https://app.clickup.com/settings/apps>. Save it as the
  `clickup_token` setting.
- **GitHub** — **Settings** → **Developer settings** → **Personal access
  tokens** → **Fine-grained tokens** (or *Tokens (classic)*) →
  **Generate new token**, grant the `repo` scope, copy it.
  Direct: <https://github.com/settings/tokens>. (In WaveAssist, GitHub
  is usually connected via the typed `github` variable, not pasted.)
- **Notion** — <https://www.notion.so/my-integrations> → **New
  integration** → copy the *Internal Integration Secret*. Then, in
  Notion, open the database/page → **•••** → **Connections** → add your
  integration so it can see that page. Save the secret as `notion_token`.
- **Gmail (outbound)** — no key needed; `waveassist.send_email` handles
  delivery. **Inbound** requires a Google OAuth connection, not a pasted
  token — escalate rather than asking the user for a "key".
- **Generic provider** — usually under **Settings → API / Developers →
  API keys → Create/Generate**. Copy the key, save it as
  `<provider>_token` (or `<provider>_api_key`), matching the
  `config.yaml` variable `key`.

## 6. When to use `call_llm` vs plain code

**Default to plain code.** Anything deterministic — fetching, filtering,
mapping fields, building a payload, formatting HTML — is plain Python +
`requests`. It's faster, free, and reproducible.

**Use `waveassist.call_llm` only for genuine natural-language
reasoning** the API can't do: summarizing a PR diff, classifying
free-text sentiment, drafting prose, extracting structure from messy
text. GitZoid is the model split — `fetch_pull_requests.py` and
`post_comment.py` are pure `requests` (no LLM); only
`generate_review.py` calls `call_llm`, because writing a review is the
one natural-language step.

Don't reach for an LLM to parse JSON, pick a list item by a rule, or
template a string — that's code. See
`prompt-writing-with-call-llm.md` for the `call_llm` signature, Pydantic
response models, and prompt anatomy once you've decided a step genuinely
needs reasoning.

## Checklist

- [ ] Token read with `fetch_data("<provider>_token", default="")` (and/or `or ""`).
- [ ] Missing-key guard writes an error `display_output` (with `html_content`), then lets the happy path be **skipped via `if/else`** — **no `exit()`/`sys.exit()`/`raise SystemExit`, no top-level `return`** (those leave the node stuck "STARTED"; see §1).
- [ ] Orchestration falls through to the end on every path (use `if/elif/else` + `try/except`, not early exits).
- [ ] Correct auth header for the provider (Bearer vs raw vs `X-Api-Key`).
- [ ] HTTP errors classified (401/403 → bad key, 429 → rate limit, 5xx → transient).
- [ ] Every write (POST/PUT/PATCH/DELETE, `send_email`) is gated behind `is_test_run()` with a preview branch.
- [ ] Results stored with `data_type="json"` for the next node.
- [ ] `requests` calls pass `timeout=` and are wrapped against `requests.RequestException`.
- [ ] LLM only for natural-language steps; everything else is plain code.

## See also

- `waveassist-sdk.md` — `init`, `fetch_data`, `store_data`,
  `is_test_run`, `send_email`, node-file structure rules.
- `prompt-writing-with-call-llm.md` — when a step genuinely needs an LLM.
- `email-html-design.md` — house style for `display_output` / email HTML.
