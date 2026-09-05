# WaveAssist API — HTTP Contracts

Extracted from the Django backend at `WaveAssistApi/`. Field names and paths are
quoted verbatim from the source. Where the code is ambiguous, it is called out
explicitly.

## Global conventions (read this first)

### Base host
- Production API base: **`https://api.waveassist.io`** (from
  `WaveAssistDashboard/src/services/base_service.tsx` → `BASE_URL`, and the SDK
  `waveassist/constants.py` → `API_BASE_URL`).
- Dashboard app: `https://app.waveassist.io`.
- `ALLOWED_HOSTS` in `settings.py` includes `'*'`, `api.waveassist.io`,
  `app.waveassist.io`, plus legacy `*.wavepredict.com` hosts.
- There is **no URL prefix / app include**. All routes are declared flat in
  `WaveAssistApi/urls.py`. Most endpoints live at the root (`/login/`,
  `/manage/...`, `/data/...`, `/deploy/...`, `/template/...`, `/assistant/...`).
  The only `/api/v1/...` routes are the Composio integrations catalog and
  `/api/v1/wavemaker/materialize_assistant`.

### Auth
- **Every endpoint is `@csrf_exempt`** (wrapped in `urls.py`). There are no DRF
  `authentication_classes` / `permission_classes` — this is plain Django function
  views, not DRF, despite occasional `request.data`-style naming.
- Auth is carried by the **`uid` field in the request body/query** (the WaveAssist
  user UUID, `User.uid`). There is **no bearer/JWT/header auth** for the main app
  endpoints. The validator (`Utils/validator.py`) looks up `User.objects.get(uid=uid)`
  and checks `AccessProvided` rows for project/data-run access.
  - Access levels (`Utils/constants.py`): `READ_GTE = 1`, `WRITE_GTE = 2`,
    `ADMIN_GTE = 3`.
- **Exception:** the CLI bundle endpoints (`/cli/project/<id>/push_bundle/`,
  `/pull_bundle/`) use an `Authorization: Bearer <uid>` header (the uid is the
  bearer token). Login itself uses a Firebase ID token.

### Body encoding
- `get_param(request, key, default)` (`Utils/utils.py`) resolves params in this
  order: for **GET** → query string only; for **non-GET** → `request.POST` first
  (form-encoded), then falls back to `json.loads(request.body)`. So most
  POST endpoints accept **either** `application/x-www-form-urlencoded` **or**
  `application/json`.
- Some views read `request.POST.get(...)` **directly** (not via `get_param`) —
  those are **form-encoded only** and will NOT see a JSON body. Noted per-endpoint.
  Notably `deploy_template`, `create_project`, `deploy_project`, `run_dag`'s
  `start_node_key`, and `login` read `request.POST` directly.

### Response envelope (`Utils/responseParser.py`)
- Success: `{"success": "1", "data": <data>, "status": <status>, "message": <msg>}`
- Error: `{"success": "0", "message": <msg>, "status": <error_code>}`
- **CRITICAL: the HTTP status code is almost always `200`.** `ResponseParser`
  uses `JsonResponse(dict)` with no `status=` kwarg, so even errors return
  **HTTP 200** with `"success": "0"` in the body. The second positional arg to
  `getParsedErrorMessage`/`getParsedSuccessMessage` is an **`error_code`/`status`
  string in the JSON body**, NOT the HTTP status. A client MUST branch on the
  JSON `success` field, not the HTTP status code. (A few places pass `404`/`401`
  as that arg — e.g. `cli_login_status`, `fetch_assistant` — but these still go
  into the body's `status` field and the response is still HTTP 200.)
- `success` / `status` are **strings** (`"1"`, `"0"`, `"200"`), not ints.

---

## CLI Login handshake (full flow)

Three pieces cooperate: the CLI (`waveassist/core.py login()`), the dashboard
login page, and two backend endpoints.

### 1. CLI starts a session
- The CLI generates a random `session_id = str(uuid.uuid4())` locally.
- It opens the browser to: **`https://app.waveassist.io/login?session_id=<session_id>`**.
- It then polls the status endpoint (below) once per second for up to 180s.

### 2. User logs in → `POST /login/`
- **Method:** POST
- **Path:** `/login/`
- **Auth:** Firebase ID token (no uid yet).
- **Body:** form-encoded (`request.POST.get` directly).
  - `firebase_token` (required) — Firebase ID token; verified via
    `firebase_admin.auth.verify_id_token`, yields `firebase_uid`.
  - `session_id` (optional) — when present, the dashboard passes the same
    `session_id` from the URL. `handle_cli_session` stores the resolved
    WaveAssist `uid` in the cache: `cache.set(f"cli_login_session:{session_id}", uid, timeout=300)` (5 min TTL).
- **Success response data:** `{"project_array": [...], "user_data": {... , "mongo_db_url": ...}}`.
  `user_data` contains `uid` (the WaveAssist user id the CLI ultimately wants).
- **Special cases:** if the user/account isn't fully set up, returns
  `data = GET_STARTED_DATA`, `status "S02"`, message `"User not found"` (still
  `success: "1"`). If Firebase verification fails → error envelope.

### 3. CLI polls status → `GET /cli_login/session/<session_id>/status`
- **Method:** GET
- **Path:** `/cli_login/session/<str:session_id>/status` (note: **no trailing slash**).
- **Auth:** none (the `session_id` is the capability).
- **Behavior:** reads `cache.get(f"cli_login_session:{session_id}")`.
  - If present → success envelope with **`data` = the uid string** (`{"success":"1","data":"<uid>", ...}`).
  - If absent → `getParsedErrorMessage("Not yet authenticated", 404)` →
    `{"success":"0","message":"Not yet authenticated","status":404}` (still HTTP 200).
- **CLI completion:** when `success == "1"` and `data` is non-empty, the CLI saves
  `{"uid": data}` to `~/.waveassist/config.json`. That uid is then used as the
  `Authorization: Bearer <uid>` for push/pull and as the `uid` param elsewhere.

---

## Project create — `manage_views.create_project`

- **Method:** POST
- **Path:** `/manage/create_project/`
- **Auth:** `uid` param. Gated by `user_object.can_create_projects` (returns
  error `"You do not have access to create projects."` if false). Also requires
  an `Account` with `account_uid == uid`.
- **Body:** form-encoded (reads `request.POST.get` directly — JSON body NOT supported here).
  - `uid` (required)
  - `project_key` (required) — lowercased server-side; must not contain spaces;
    must be unique per user.
  - `project_name` (required)
  - `is_premium` (optional, default `"0"`) — `bool(int(...))`.
  - `should_create_nodes` (optional, default `"0"`) — read but node bootstrap is
    disabled ("Default node bootstrap is intentionally disabled").
  - `template_key` (optional, default `""`) — stored on `Project.template_key`.
- **Side effects:** creates the Project, two `DataRuns` (environments):
  **`<project_key>_default`** (name "Default") and **`<project_key>_test`**
  (name "Test"), both `is_enabled=True`; grants the user `ADMIN_GTE` access; and
  seeds KV vars `uid`, `mongo_url`, `open_router_key` into both environments.
- **Success response:** `data = project_object.get_dict()`, which includes
  `project_key` (and other project fields). Message `"Project created successfully."`
- **Error response:** envelope with `success:"0"` (HTTP 200) for: user not found,
  account not found, no create permission, missing/duplicate/spaced key, etc.

---

## KV store write — `data_views.set_data_for_key`

- **Method:** POST (`@require_POST` → real HTTP 405 if not POST)
- **Path:** `/data/set_data_for_key/`
- **Auth:** `uid` + data-run access (`validate_user_and_data_run(request, READ_GTE)`).
  NOTE: only `READ_GTE` is required to **write** here.
- **Body:** form-encoded OR JSON (uses `get_param`).
- **Fields:**
  - `uid` (required)
  - `project_key` (required for the validator's project context; the validator
    actually keys off the data run, but callers always send it)
  - `data_run_key` **or** `environment_key` (one required) — the environment /
    Mongo collection name. `get_param('data_run_key') or get_param('environment_key')`.
    **No default** — if neither resolves to a valid enabled `DataRuns`, validation
    fails with `"Environment/DataRun not found"`. (Convention elsewhere: the
    default env is `<project_key>_default`; the SDK defaults `environment_key` to
    `f"{project_key}_default"`.)
  - `data_key` (required) — error `"Missing 'data_key' in request."` if empty.
  - `data` (the value to store)
  - `data_type` (optional, default `"json"`) — if `"json"`/`"dataframe"` and a
    string is passed, the server `json.loads` it.
  - `run_based` (optional, default `"0"`) — if `"1"` **and** `run_id` present,
    the effective key becomes `f"{data_key}_{run_id}"`.
  - `run_id` (optional) — only used when `run_based == "1"`.
- **Success response:** `data = {"data_key": <effective_key>}`, message `"Data saved successfully."`
- **Error response:** envelope `success:"0"` for validation/save failures.

---

## KV store read — `data_views.fetch_data_for_key`

- **Method:** GET (`@require_GET`)
- **Path:** `/data/fetch_data_for_key/`
- **Auth:** `uid` + data-run access (`READ_GTE`). Since it's GET, **all params are
  query-string** (`get_param` reads `request.GET` for GET).
- **Fields (query):** `uid`, `project_key`, `data_run_key` or `environment_key`,
  `data_key`, optional `run_based` (`"0"`/`"1"`), optional `run_id`. Same
  `run_based`/`run_id` key-mangling as the write path.
- **Success response:** `data = {"data": <value>, "data_type": <type>}`. For
  `json`/`dataframe` stored as strings, the server parses them back to objects.
- **Special cases:**
  - `data_key == "open_router_key"` is sourced from the Postgres `Account` model,
    not Mongo.
  - keys ending in `_access_token` trigger transparent OAuth refresh.
- **Error response:** `"Data not found"`, `"Missing 'data_key' in request"`, etc.
  (all `success:"0"`, HTTP 200).

### Path-style read — `data_views.fetch_data` (the GET `/data/fetch_data/<...>/` form)
- **Method:** GET (`@require_GET`)
- **Path:** `/data/fetch_data/<str:uid>/<str:project_key>/<str:data_run_key>/<str:data_key>/`
  (trailing slash **required**).
- **Auth:** uid is in the path. Internally injects the path segments into
  `request.GET` and calls `fetch_data_for_key`.
- **Success response:** **differs from the wrapper** — on success it returns the
  **bare data object** via `JsonResponse(response_data.get('data'), status=200)`
  (i.e. `{"data": ..., "data_type": ...}` WITHOUT the `success` envelope). On
  failure it returns the standard error envelope.
- This is the form the dashboard uses for direct data fetches
  (`project_services.tsx` builds `.../data/fetch_data/${uid}/${project_key}/${data_run_key}/${key}`).

---

## Materialize (WaveMaker GitHub push) — `wavemaker_views.materialize_assistant`

- **Method:** POST only (manual check; returns error envelope, not 405, on other methods)
- **Path:** **`/api/v1/wavemaker/materialize_assistant`** (NO trailing slash)
- **Auth:** `uid` param → `User.objects.get(uid=uid)`. For updates, additionally
  requires the target repo's GitHub description to contain the caller's
  `wm-owner:<sha256(uid)[:16]>` tag.
- **Body:** JSON if `content_type` contains `"json"`, else form-encoded (`request.POST`).
- **Fields:**
  - `uid` (required)
  - `assistant_name` (required) — used to slug the repo name on create.
  - `config_yaml` (required) — a **YAML string** (not an object); parsed with
    `yaml.safe_load`. Written to `config.yaml` in the repo.
  - `code_files` (required) — a **dict `{filename: python_source_string}`**. Must
    be a non-empty dict. Each key gets a `.py` suffix appended if missing. So the
    shape is `{node_key_or_filename: "<python source>"}`.
  - `readme_md` (optional) — written as `README.md` if present.
  - `existing_repo_url` (optional) — presence of this flips the call to **update**
    mode (pushes new commits to that repo). Must point at the WaveAssist GitHub
    account and pass the owner-tag check.
  - `existing_project_key` (optional) — accepted/parsed but not used for routing.
- **IMPORTANT — does NOT accept `target_project_key`.** This endpoint only owns
  the GitHub side. It returns a **`repo_url`**; it does **not** create a Project,
  does not return a `project_key`. The caller (worker) is expected to then call
  `/template/deploy_template/` (create) or `/assistant/upgrade/` (update),
  passing the returned `repo_url`.
- **Create-mode cap:** `MAX_WAVEMAKER_ASSISTANTS_PER_USER = 25` (counts deployed
  projects via `AccessProvided` at `ADMIN_GTE`).
- **Success response:** `data = {"repo_url": <url>, "is_update": <bool>, "files_pushed": <int>}`,
  message `"Assistant pushed to GitHub."`
- **Error response:** envelope `success:"0"` for missing fields, bad YAML, repo
  cap reached, GitHub failures, or unauthorized update.

---

## Deploy (install template into a project) — `template_views.deploy_template`

- **Method:** POST
- **Path:** `/template/deploy_template/` (trailing slash)
- **Auth:** `uid` param + `user_object.can_create_projects` gate.
- **Body:** form-encoded — reads `request.POST.get` directly (and **mutates**
  `request.POST` to forward to `create_project`). JSON body NOT supported.
- **Fields:**
  - `uid` (required)
  - `repo_url` (required) — the source GitHub repo (template or WaveMaker-built).
  - `should_install_requirements` (optional, default `"0"`) — when `"1"`, calls
    `configure_variables(uid, project_key, yaml_config)`.
  - `timezone` (optional, default `"UTC"`) — applied to created node schedules.
  - `target_project_key` (optional) — **YES, the caller can supply it.** When
    present it must match regex `^[a-z0-9_]+_[a-f0-9]{4}$` (i.e. exactly the
    `{slug}_{4-hex}` form `create_project` would have generated). Nodes are
    installed into that existing project instead of creating a new one. Requires
    `ADMIN_GTE` access to that project.
- **REFUSAL conditions (return error envelope, `success:"0"`):**
  - `target_project_key` present but **the target project already has any
    `Nodes`** → `"Target project already has nodes; use upgrade_assistant"`.
    This is the exact "refuses if target has nodes" condition.
  - `target_project_key` bad format, target project not found, or no `ADMIN_GTE`
    access.
  - User not found, no create permission, missing `repo_url`, invalid YAML.
- **Behavior when no `target_project_key`:** generates
  `project_key = f"{name.lower().replace(' ','_')}_{uuid4().hex[:4]}"`, calls
  `create_project`, then installs nodes.
- **Persists** `Project.github_url = repo_url` and `Project.deployed_commit_sha`.
- **Success response:** `data = project_object.get_dict()` (includes
  `project_key`), message `"Project created successfully."`
- **IMPORTANT — deploy_template does NOT start the schedule.** It only creates the
  `Nodes` rows (which carry `schedule_type` + interval/crontab). It does **not**
  call `deploy_project`, so **no `Deployments`/`DAG`/`PeriodicTask` is created and
  nothing is scheduled to fire** until a separate `/deploy/deploy_project/` call.
  See the dedicated schedule section below.

---

## Upgrade existing — `template_views.upgrade_assistant`

- **Method:** POST
- **Path:** `/assistant/upgrade/`
- **Auth:** `uid` + project access (`validate_user_and_project`, `ADMIN_GTE`).
- **Body:** uses `get_param`/`request.POST`. Fields: `uid`, `project_key`
  (required by validator), optional `data_run_key` (defaults to
  `f"{project_key}_default"` only if the project was already running), optional
  `timezone` (default `"UTC"`).
- **Behavior:** resolves source repo (curated `Assistants.github_url` via
  `template_key`, else `Project.github_url`); fetches latest commit SHA; if equal
  to `deployed_commit_sha` → error `"Already on the latest version."`; otherwise
  deletes & recreates nodes from the new YAML inside a transaction and updates
  `deployed_commit_sha`. If a deployment **was running**, it re-deploys via
  `deployment_views.deploy_project` (auto-generated `version` =
  `upgrade_<sha8>_<6hex>`).
- **Success response:** `data = {"new_sha": <sha>, "commit_message": <msg>}`,
  message `"Assistant upgraded successfully."`
- **Error response:** envelope for: no access, no upgrade source, already latest,
  fetch/validate/upgrade failures.

## Check update — `template_views.check_assistant_update`

- **Method:** POST (uses `get_param`; effectively form or JSON)
- **Path:** `/assistant/check_update/`
- **Auth:** `uid` + project access (`READ_GTE`).
- **Fields:** `uid`, `project_key`.
- **Success response:** `data = {"has_update": <bool>, "current_sha": <str>,
  "latest_sha": <str>, "latest_commit_message": <str>}`. If the project has no
  upgrade source, returns `{"has_update": False}` with `success:"1"`.

---

## Run / test — `deployment_views.run_dag`

- **Method:** POST
- **Path:** `/deploy/run_dag/`
- **Auth:** `uid` + project access (`ADMIN_GTE`) + data-run access (`ADMIN_GTE`).
- **Body:** form-encoded. `uid`/`project_key`/`data_run_key` via the validators
  (`get_param`); `start_node_key` is read via `request.POST.get` directly.
  (Dashboard sends it as `application/x-www-form-urlencoded` URLSearchParams.)
- **Fields:**
  - `uid` (required)
  - `project_key` (required)
  - `data_run_key` **or** `environment_key` (one required) — the environment to
    run against. There is **no default**; must resolve to an enabled `DataRuns`.
  - `start_node_key` (optional) — if omitted/empty, the server picks the project's
    single enabled `is_starting_node=True` node (errors if not exactly one).
- **Behavior:** validates the DAG, creates a one-off `DAG` row with key
  `DAG_<project_key>_<start_node_key>_test_run_<data_run_key>_<timestamp>`, and
  dispatches the Celery task `DAG_TASK = "celery_worker.run_dag"` to the account's
  `celery_queue`. This is a **fire-once** run (no `PeriodicTask`, not scheduled).
- **Success response:** `data = {"dag": dag_object.get_dict(), "run_id": <celery_task_id>}`.
  - `dag_object.get_dict()` = `{"key": <dag_key>, "is_running": <bool>}`.
  - `run_id` = the Celery `AsyncResult.id`. **There is no per-node status in this
    response** — node/dag statuses are fetched separately via
    `/runs/fetch_dag_runs/` and `/runs/fetch_node_runs/` (using `dag_run_id`).
- **Error response:** envelope for missing/invalid start node, DAG validation
  failure, no account/queue, etc.

### How a "test run" is designated (definitive)
There are **two independent notions of "test"**, and the backend `run_dag` view
does **not** itself set a test flag:

1. **A "Test" environment (DataRuns).** `create_project` always creates a second
   environment `<project_key>_test` (name "Test") alongside `<project_key>_default`.
   Running against `data_run_key = <project_key>_test` isolates data in a separate
   Mongo collection. The `_test_run_` substring inside the generated `dag_key` is
   **cosmetic** (every `run_dag` includes it) and does NOT gate behavior.

2. **The `_is_test_run` KV flag (the real dry-run switch).** The SDK
   (`waveassist/__init__.py`) exposes `is_test_run()`, which simply does
   `fetch_data("_is_test_run", default=False)` from the KV store and coerces it to
   a bool (`true`/`1`/`yes` → True). Constant: `_IS_TEST_RUN_KEY = "_is_test_run"`.
   - When `is_test_run()` is True, the SDK's `call_tool(...)` **gates writes**: it
     does not hit the external provider and instead stores the intended call under
     a `test_preview_*` key, returning `{"test_preview": True, ...}`. The backend
     tool executor (`integrations_view.execute_tool`) independently honors an
     `is_test_run` request param (`"1"/"true"/"yes"`) and skips writes.
   - **To trigger a test (dry) run vs a real run:** write `_is_test_run = true`
     (data_type `"string"` or a JSON bool) into the target environment's KV store
     via `POST /data/set_data_for_key/` (`data_key="_is_test_run"`,
     `data_run_key=<env>`) **before** calling `run_dag`. For a real run, set it to
     `false` or leave it unset (default False). The node code must call
     `waveassist.is_test_run()` / use `call_tool` for the gating to take effect —
     it is a **cooperative convention enforced in node code + SDK**, not a hard
     backend guarantee on arbitrary writes.
   - No code path in `WaveAssistApi` or the dashboard auto-sets `_is_test_run`;
     the dashboard's `runDAGApi` sends only `uid`, `project_key`, `data_run_key`,
     and optional `start_node_key`. Setting the flag is the caller's responsibility.

---

# ⭐ SCHEDULE ENABLE / DISABLE — definitive answer

**Question:** can you deploy an assistant in a disabled (non-firing) state and then
enable its schedule after a successful test?

### (a) Does `deploy_template` deploy without the schedule firing? — **YES.**
`deploy_template` only creates `Nodes` (with their `schedule_type` + interval/
crontab metadata). It does **not** create any `Deployments`, `DAG`, or
`django_celery_beat.PeriodicTask`. **Nothing is scheduled to fire** after
`deploy_template` alone. Scheduling only begins when `/deploy/deploy_project/` is
called: that view is what creates the `PeriodicTask` (with `enabled=True`) that
Celery Beat fires on the node's interval/crontab. So a freshly "deployed" template
(via `deploy_template`) is inherently in a **non-firing** state. You can run it
on demand with `/deploy/run_dag/` (one-off, unscheduled) for testing without ever
arming the schedule.

So the test-then-arm flow already works as: `deploy_template` → `run_dag` (test) →
`deploy_project` (arms the recurring schedule).

### (b) Is there an existing endpoint to enable/disable a *deployed* agent's schedule? — **NO dedicated toggle.**
There is **no** `enable`/`disable`/`pause`/`resume`/`toggle` endpoint. The only
schedule lifecycle endpoints are:
- `POST /deploy/deploy_project/` — **arms** the schedule (creates
  `Deployments` + `DAG` + `PeriodicTask(enabled=True)`). It first stops any prior
  running deployment for that project+data_run.
- `POST /deploy/stop_deployment/` — **disarms** a deployment. Internally
  (`utils.stop_deployment`) it sets `deployment.is_running=False`, and for each
  DAG sets `dag.periodic_task.enabled=False` and `dag.is_running=False`. This is
  the de-facto "disable schedule" — but it's keyed by **`deployment_key`**, it
  tears the deployment down rather than toggling a flag, and re-enabling means
  calling `deploy_project` again (with a new unique `version`).

Relevant model fields that exist today:
- `Nodes.is_enabled` (bool) and `Nodes.schedule_type` (`none`/`interval`/`crontab`)
  — gate whether a node is even eligible as a starting node. A node with
  `schedule_type="none"` is excluded from `deploy_project`'s starting nodes.
- `Deployments.is_running` (bool), `DAG.is_running` (bool),
  `django_celery_beat.PeriodicTask.enabled` (bool) — the actual on/off switches,
  but only manipulated via `deploy_project` / `stop_deployment`.
- **Note:** there is NO `is_enabled`/`dag_is_enabled` field on the current `DAG`
  model. Migration `0006` historically referenced such fields, but the live model
  in `models.py` only has `DAG.is_running`. Do not rely on a `DAG.is_enabled`.

### (c) Minimal functional addition to support "deploy disabled, enable after test"
The cleanest minimal addition, given the existing machinery:

- **Option 1 (reuse PeriodicTask.enabled — least new state):** add one endpoint,
  e.g. `POST /deploy/set_schedule_enabled/` taking `uid`, `project_key`,
  `data_run_key`, `enabled` (`"0"/"1"`), validated at `ADMIN_GTE`. It would look
  up the running `Deployments` for that project+data_run and flip every
  `dag.periodic_task.enabled` and `dag.is_running` to match — i.e. a softer,
  reversible version of `utils.stop_deployment` that doesn't set
  `deployment.is_running=False` or require a new `version` to re-arm. Add a
  small helper (e.g. `utils.set_deployment_schedule_enabled(deployment, enabled)`).
  Pair with an optional `start_enabled` (default `"1"`) param on `deploy_project`
  so an agent can be deployed with `PeriodicTask(enabled=False)` (created but
  paused) and enabled later after a successful `run_dag` test. This requires **no
  new model field** — only the two new view functions/params and a URL route.

- **Option 2 (explicit field):** add a boolean (e.g. `Deployments.schedule_enabled`,
  default `False`) for a clear deployed-but-paused state, plus the same toggle
  endpoint. More explicit but requires a migration.

Recommended: **Option 1** — add a `start_enabled` flag to `deploy_project` and a
new `set_schedule_enabled` view in `deployment_views.py` (+ a route in `urls.py`),
reusing `PeriodicTask.enabled` / `DAG.is_running`. No new model field needed.

---

## Quick reference table

| Endpoint | Method | Path | Body | Auth |
|---|---|---|---|---|
| Login | POST | `/login/` | form | firebase_token |
| CLI status | GET | `/cli_login/session/<session_id>/status` | — | session_id (capability) |
| Create project | POST | `/manage/create_project/` | form | uid + can_create_projects |
| KV write | POST | `/data/set_data_for_key/` | form/json | uid + data-run READ |
| KV read | GET | `/data/fetch_data_for_key/` | query | uid + data-run READ |
| KV read (path) | GET | `/data/fetch_data/<uid>/<project_key>/<data_run_key>/<data_key>/` | path | uid in path |
| Materialize | POST | `/api/v1/wavemaker/materialize_assistant` | json/form | uid (+ owner tag on update) |
| Deploy template | POST | `/template/deploy_template/` | form | uid + can_create_projects |
| Upgrade | POST | `/assistant/upgrade/` | form/json | uid + project ADMIN |
| Check update | POST | `/assistant/check_update/` | form/json | uid + project READ |
| Run DAG (test/real) | POST | `/deploy/run_dag/` | form | uid + project ADMIN + data-run ADMIN |
| Deploy (arm schedule) | POST | `/deploy/deploy_project/` | form | uid + project ADMIN + data-run ADMIN |
| Stop deployment | POST | `/deploy/stop_deployment/` | form | uid + deployment data-run ADMIN |
| Fetch DAG runs | POST | `/runs/fetch_dag_runs/` | form/json | uid + project/data-run READ |
| Fetch node runs | POST | `/runs/fetch_node_runs/` | form | uid + project/data-run READ (needs `dag_run_id`) |

All responses are HTTP 200 with a `{"success": "1"|"0", ...}` JSON envelope unless
noted (the `@require_POST`/`@require_GET` decorators and the `webhook`/`email_webhook`
views are the only places that emit real non-200 HTTP codes).
