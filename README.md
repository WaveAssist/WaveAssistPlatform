<h1 align="center">/waveassist</h1>

<p align="center">
  <b>The deterministic agent runtime, on infrastructure you control.</b><br/>
  <sub>Describe a job in plain English. Your coding agent builds it, WaveAssist runs it on your schedule.</sub>
</p>

<p align="center">
  <a href="https://waveassist.ai"><img src="https://img.shields.io/badge/Website-waveassist.ai-D8FF00" alt="waveassist.ai" /></a>
  <img src="https://img.shields.io/badge/Deterministic-•_Scheduled_•_Self--hosted-0B0C0F" alt="Deterministic, scheduled, self-hosted" />
  <img src="https://img.shields.io/badge/Run_with-Docker_Compose-2496ED" alt="Run with Docker Compose" />
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License" /></a>
</p>

<p align="center">
  <a href="#quickstart">Quickstart</a> ·
  <a href="#deployment-profiles">Deployment profiles</a> ·
  <a href="#configuration-flags">Flags</a> ·
  <a href="#build-agents-from-your-editor-mcp">Build with MCP</a> ·
  <a href="#architecture">Architecture</a>
</p>

---

## What is WaveAssist?

WaveAssist is a runtime for **deterministic AI agents**: recurring jobs that call a model
inside strict guardrails instead of free-form chat. You describe a job in plain English,
your coding agent (Claude Code, Cursor, any MCP host) designs and tests it, and WaveAssist
runs it on a schedule, forever, for pennies a run. Every model call is locked to a JSON
schema, state is persisted between steps, and a run is verified before its schedule goes live.

The hosted product is at **[waveassist.ai](https://waveassist.ai)**. **This repository is the
same stack, packaged to run entirely on one host you control** with `docker compose`: the API,
worker, scheduler, run-recorder, MCP endpoint, dashboard, and datastores, wired together. A set
of flags turns off the multi-tenant and billing control plane so it runs self-contained, or
keeps them on for a consolidated multi-user deployment on a single box.

### Why self-host it

- **Your data stays yours.** Private repositories, internal databases, and reports never leave
  your network boundary. Provider calls (LLM, email, GitHub) go out only where you configure them.
- **No per-seat billing.** Turn billing off and run as many agents as your box can handle.
- **The same code as hosted.** Not a cut-down fork. A flag flip, not a rewrite.
- **Deterministic and auditable.** Schema-locked model output, recorded runs, and per-node status
  in a dashboard you own.

> Single-tenant, trusted-deployment appliance. Auth is UID-based and node code runs in the
> worker process, so run it on a host you control behind your own TLS and firewall, not as a
> hostile multi-tenant sandbox.

---

## Quickstart

Requires Docker with the Compose plugin. Builds run natively on the host architecture
(arm64 on Apple silicon / AWS Graviton, amd64 on x86 servers).

```bash
cp deploy/profiles/cloud-customer.env.example .env   # pick a profile, fill the __CHANGE_ME__ values
docker compose build
docker compose up -d
```

| Surface | URL |
|---|---|
| Dashboard | `http://<host>:8080` |
| API | `http://<host>:8000` |
| MCP endpoint | `http://<host>:9000/mcp` |

On first boot the API applies migrations and (when `WA_BOOTSTRAP_ADMIN=1`) seeds a single admin
account. Then [deploy an agent](#deploy-an-agent) or [build one from your editor](#build-agents-from-your-editor-mcp).

---

## What you run

One host runs the whole stack as separate Compose services.

| Service | Role |
|---|---|
| `api` | Django REST API (gunicorn). Runs migrations; seeds the admin with `WA_BOOTSTRAP_ADMIN=1`. |
| `worker` | Celery worker. Executes node code. |
| `beat` | Celery beat. Fires each agent's schedule. |
| `camera` | Records DagRuns / NodeRuns for the dashboard's live view. |
| `mcp` | In-box MCP endpoint for authoring agents from Claude Code / Cursor (optional profile). |
| `web` | The React dashboard (nginx serving the built SPA). |
| `mysql` | Django ORM: users, projects, run history, beat schedule. |
| `mongo` | KV store behind `fetch_data` / `store_data` (agent variables, published dashboards). |
| `redis` | Celery broker + result backend + the camera event bus. |

---

## Deterministic agents

An agent is a folder: a `config.yaml` plus flat Python node files. Nodes form a DAG, each on its
own schedule, and pass state through the SDK rather than through function calls.

```python
import waveassist

def run_task():
    prs = waveassist.fetch_data("open_prs")            # read state from the KV store
    review = waveassist.call_llm(                       # schema-locked model call
        model="claude-sonnet-4.6",                      # provider/key configured per deployment
        prompt=f"Review this PR: {prs[0]}",
        response_model=ReviewSchema,                    # output validated against a JSON schema (a pydantic model)
    )
    waveassist.store_data("latest_review", review)      # persist for the next node / run
```

- **`call_llm(..., response_model=...)`** locks every model call to a JSON schema, so a node's
  output is structured and repeatable, not free-form prose.
- **`fetch_data` / `store_data`** persist state to Mongo, scoped per project and environment
  (`default` and `test`), so runs are incremental and idempotent.
- **Nodes and chains** are wired in `config.yaml` with `run_after` dependencies; `beat` runs each
  chain on its own cron or interval, and `camera` records every run.
- The Python SDK is published separately as [`waveassist`](https://pypi.org/project/waveassist/);
  point workers at this box with `WAVEASSIST_API_BASE_URL`.

---

## Deployment profiles

Three ready-to-fill profiles under [`deploy/profiles/`](deploy/profiles) cover the common shapes.
Copy one to `.env` and fill it in. See [`deploy/profiles/README.md`](deploy/profiles/README.md)
for the per-deployment checklist (TLS/proxy, hostnames, LLM/email/GitHub setup, lock-down).

| Profile | Shape | Login | Billing |
|---|---|---|---|
| [`hosted`](deploy/profiles/hosted.env.example) | The multi-tenant product consolidated onto one host | Firebase | on |
| [`cloud-customer`](deploy/profiles/cloud-customer.env.example) | A single box on your cloud, internet-connected | password | off |
| [`connected-customer`](deploy/profiles/connected-customer.env.example) | Your own hardware, reaching private data sources | password / no-login | off |

---

## Configuration flags

Code defaults preserve the hosted behaviour, so an unconfigured build behaves exactly like the
SaaS. Compose and the profiles choose self-hosted defaults. Frontend flags (`VITE_*`) are baked at
build time, so rebuild `web` after changing them.

| Flag | Values (hosted default) | Effect |
|---|---|---|
| `WAVEASSIST_SELF_HOSTED` | `0` \| `1` | Master switch; enables fail-closed config. |
| `WA_AUTH` | `firebase` \| `local` \| `password` | Login mode (see below). |
| `WA_BILLING` | `on` \| `off` | Credit gating and payment endpoints. |
| `WA_WORKER_PROVISIONING` | `fargate` \| `shared_queue` | One shared worker instead of per-tenant ECS. |
| `WA_DB_PROVISIONING` | `atlas` \| `local` | Local Mongo instead of the Atlas Admin API. |
| `WA_STORAGE` | `s3` \| `local` | Published pages / bundles to local disk. |
| `WA_LOGS` | `cloudwatch` \| `local` | Logs from the container instead of CloudWatch. |
| `WA_CATALOG` | `remote` \| `local` | The remote template catalog. |
| `WA_TELEMETRY` | `on` \| `off` | PostHog / Google Analytics (off makes zero external calls). |

**Fail-closed:** with `WAVEASSIST_SELF_HOSTED=1`, missing `DB_PASSWORD` / `DB_HOST` /
`MONGODB_CONNECTION_STRING` / `REDIS_URL` / `DJANGO_SECRET_KEY` make the API refuse to start
rather than fall back to a cloud default.

Host / CORS lock-down and mail relay are configurable too: `WA_ALLOWED_HOSTS`, `WA_CORS_ORIGINS`,
`WA_CORS_ALLOW_ALL`, and `WA_SMTP_SERVER` / `WA_SMTP_PORT` / `WA_FROM_EMAIL`.

### Auth modes

- **`firebase`** Google login for real multi-user deployments (needs a Firebase service-account key mounted).
- **`password`** username / password login. Env credentials `WA_ADMIN_USERNAME` / `WA_ADMIN_PASSWORD`; the dashboard warns while the default is in use.
- **`local`** single-tenant: with the admin UID baked into the dashboard build, it auto-enters with no login page.

---

## Deploy an agent

Point `AGENTS_DIR` at the host folder that holds your agents (it mounts at `/agents`), then import
one from disk:

```bash
docker compose exec api python manage.py deploy_local_agent \
  --path /agents/my-agent --uid <admin-uid> --project my_agent
```

This creates the project, its `default` and `test` environments, all nodes (with dependency order
and schedules), grants the admin access, and seeds `config.yaml` variables. Secrets seed empty; set
them in the dashboard. Import is idempotent and never overwrites an existing value. The admin UID is
printed by `python manage.py seed_admin`.

## Build agents from your editor (MCP)

Enable the bundled MCP service (`COMPOSE_PROFILES=mcp`) and connect your coding agent to
`http://<host>:9000/mcp` with `Authorization: Bearer <your-uid>`. From Claude Code or Cursor you can
then list projects, deploy and configure an agent, run a test, arm the schedule, and read logs, all
against your own box. Authoring via MCP that pushes to GitHub needs `GITHUB_TOKEN` / `GITHUB_USERNAME`
set; local disk import (above) needs neither.

---

## Architecture

```
   Browser                          Coding agent (Claude Code / Cursor)
      │  :8080                                │  :9000/mcp
      ▼                                       ▼
  ┌───────┐        ┌──────────────────────────────────────┐
  │  web  │        │                 api                   │  Django REST, migrations, bootstrap
  └───────┘        │        (gunicorn, :8000)              │
                   └───────┬───────────────┬───────────────┘
                           │               │
              ┌────────────┼───────────────┼─────────────┐
              ▼            ▼               ▼              ▼
          ┌───────┐   ┌───────┐       ┌────────┐    ┌────────┐
          │ mysql │   │ mongo │       │ redis  │◄──►│ worker │  executes node code (SDK)
          └───────┘   └───────┘       └────────┘    └────────┘
          ORM/history  KV store        broker +          ▲
                                       event bus         │ events
                        ┌──────────────┬─────────────────┘
                        ▼              ▼
                    ┌────────┐    ┌────────┐
                    │  beat  │    │ camera │  records runs -> mysql -> dashboard
                    └────────┘    └────────┘
                    fires schedules
```

State lives in the `mysql_data`, `mongo_data`, `redis_data`, and `platform_data` volumes.

## Data and backup

Back up **MySQL** (accounts, projects, run history, beat schedule) and **Mongo** (variables,
published dashboards) together. Redis holds in-flight queue state. Verified dump / restore commands
and a hosted-consolidation migration outline are in
[`deploy/backup_restore.md`](deploy/backup_restore.md). `docker compose down` keeps the named
volumes; `down -v` destroys them.

## Repository layout

- `api/` Django API, migrations, scheduler and camera commands.
- `worker/` Celery execution engine.
- `dashboard/` React dashboard and nginx image.
- `waveagent/` MCP server, skills, and editor integration.
- `deploy/` deployment profiles and the backup / restore runbook.
- `tests/e2e/` a deterministic full-stack test (imports a DAG, triggers it, asserts the exact result).

## Production readiness

The current build state, evidence, and known limitations are tracked in
[`VERIFICATION.md`](VERIFICATION.md). A clean clone builds, boots on empty volumes, and passes the
end-to-end test:

```bash
docker compose up -d
python tests/e2e/run_e2e.py        # exits nonzero on any failure
```

## License

MIT. See [`LICENSE`](LICENSE). Provenance of the imported history is in [`HISTORY.md`](HISTORY.md).

---

<p align="center"><sub>Built by the WaveAssist team. Hosted at <a href="https://waveassist.ai">waveassist.ai</a>.</sub></p>
