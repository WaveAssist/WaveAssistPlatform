# WaveAssist Platform

The whole WaveAssist stack on one host, via `docker compose` — API, worker, scheduler,
run-recorder, MCP, dashboard, and the datastores. Same code as the hosted product; a set
of flags turns off the multi-tenant/billing control-plane so it runs self-contained.

```
cp .env.example .env      # fill secrets + choose flags
docker compose build
docker compose up -d
```

Dashboard: `http://<host>:8080` · API: `http://<host>:8000` · MCP: `http://<host>:9000/mcp`

## Services

| Service | Role |
|---|---|
| `mysql` | Django ORM: users, projects, run history, beat schedule |
| `mongo` | KV store behind `fetch_data`/`store_data` |
| `redis` | Celery broker + result backend + camera event bus |
| `api` | Django REST (gunicorn); runs migrations; seeds admin only with `WA_BOOTSTRAP_ADMIN=1` |
| `worker` | Celery worker — executes node code |
| `beat` | Celery beat — fires each agent's schedule |
| `camera` | records DagRuns/NodeRuns for the dashboard's live view |
| `mcp` | in-box MCP endpoint for authoring agents from Claude Code/Cursor |
| `web` | dashboard (nginx serving the built SPA) |

## Configuration flags

Code defaults preserve hosted behavior. Compose and `.env.example` choose box defaults.
Set each flag explicitly for the intended deployment. Frontend flags are build-time settings; rebuild `web` after changing them.

| Flag | Values (default) | Effect |
|---|---|---|
| `WAVEASSIST_SELF_HOSTED` | `0` \| `1` | master; enables fail-closed config |
| `WA_WORKER_PROVISIONING` | `fargate` \| `shared_queue` | skip per-tenant ECS; one shared worker |
| `WA_DB_PROVISIONING` | `atlas` \| `local` | skip Atlas Admin API; use local Mongo |
| `WA_BILLING` | `on` \| `off` | credit gate + DoDo endpoints off |
| `WA_STORAGE` | `s3` \| `local` | published pages/bundles to local disk |
| `WA_LOGS` | `cloudwatch` \| `local` | logs from container instead of CloudWatch |
| `WA_CATALOG` | `remote` \| `local` | disable the remote template catalog |
| `WA_TELEMETRY` | `on` \| `off` | PostHog/GA off |
| `WA_AUTH` | `firebase` \| `local` \| `password` | login mode (see below) |

**Fail-closed:** with `WAVEASSIST_SELF_HOSTED=1`, missing `DB_PASSWORD`/`DB_HOST`/
`MONGODB_CONNECTION_STRING`/`REDIS_URL`/`DJANGO_SECRET_KEY` make the API refuse to start
rather than fall back to a cloud default.

## Auth modes

- **`firebase`** — Google login (real multi-user; needs a Firebase key mounted).
- **`local`** — single-tenant: with `WAVEASSIST_ADMIN_UID` baked into the dashboard build
  (`VITE_LOCAL_UID`), the dashboard auto-enters — no login page.
- **`password`** — username/password login. Env creds `WA_ADMIN_USERNAME` /
  `WA_ADMIN_PASSWORD` (default `admin`/`admin`); the dashboard warns while the default is
  in use. Changing = update the env var and restart.

## Deploying an agent

Set `AGENTS_DIR` to the host folder containing your agents. Compose mounts it at `/agents` in the API and worker. An agent contains `config.yaml` and Python node files. Import it from disk:

```
docker compose exec api python manage.py deploy_local_agent \
  --path /agents/my-agent --uid <admin-uid> --project my_agent
```

This creates the project, its `default`/`test` environments, all nodes (with dependency
order and schedules), grants the admin access, and seeds the `config.yaml` variables.
Secrets (API tokens, DB passwords) seed empty — set them in the dashboard or with
`data/set_data_for_key`. The admin UID is printed by `python manage.py seed_admin`.

## LLM

Node `call_llm` uses the provider configured in the KV store (OpenRouter or Azure).
Set the provider key per deployment; leave unset for agents whose nodes have a
deterministic path.

## Data & backup

State lives in the `mysql_data`, `mongo_data`, `redis_data`, and `platform_data` volumes.
Back up MySQL (metadata, run history) and Mongo (variables, published pages) together;
Redis holds in-flight queue state. `docker compose down` keeps the named volumes;
`down -v` destroys them.

## Repository layout

- `api/`: Django API, migrations, scheduler and camera commands.
- `worker/`: Celery execution engine.
- `dashboard/`: React dashboard and nginx image.
- `waveagent/`: MCP server, skills and editor integration packaging.
- `tests/`: deployment regression checks.

The Python SDK remains independently published as `waveassist`. Configure workers with
`WAVEASSIST_API_BASE_URL` and MCP with `WAVEASSIST_API_BASE` to use this API.

See [local import details](LOCAL_IMPORT.md), [history provenance](HISTORY.md), and
[current verification status](VERIFICATION.md).

## Notes

- Built `--platform=linux/amd64`; on Apple silicon it runs under emulation (dev only).
- This is a single-tenant / trusted-deployment appliance. Auth is UID-based and node code
  runs in-process in the worker — appropriate for a box you control, not a hostile
  multi-tenant environment.

MCP is enabled by `COMPOSE_PROFILES=mcp` in `.env.example`. Leave that value empty
to omit it. For a consolidated multi-user installation, retain Firebase and billing
as required and set `WA_BOOTSTRAP_ADMIN=0`; migrate existing data before cutover.
Firebase dashboard configuration and optional analytics keys are build arguments
listed in `dashboard/.env.example`. Provider integrations remain available.
