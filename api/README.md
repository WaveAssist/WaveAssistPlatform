# WaveAssistApi

The WaveAssist backend: a Django REST API that stores agent data, manages projects and
nodes, dispatches runs to the Celery worker, and records run history. It backs both the
hosted product and the self-hosted [`waveassist-platform`](../waveassist-platform) box.

## What it does

- **Projects / nodes / environments** — the agent model (`WaveAssistApiApp/models.py`);
  authoring endpoints under `manage/*`.
- **Data store** — `data/set_data_for_key` / `data/fetch_data_for_key` back the SDK's
  `store_data` / `fetch_data`, persisted in MongoDB per account+environment.
- **Run dispatch** — `deploy/run_dag` sends tasks to the worker over Redis (Celery);
  the `capture_celery_events` command records `DagRuns`/`NodeRuns` from worker events.
- **Auth** — Firebase or, self-hosted, a UID / username-password mode.
- **Integrations, templates, billing** — OAuth providers, template catalog, DoDo billing
  (all gated off in self-hosted mode).

## Run it

Needs MySQL, MongoDB, and Redis. Configure via a `.env` in this directory (see
`.env.example`) — `load_dotenv` reads it. Then:

```
pip install -r requirements.txt
./start.sh          # migrate (+ seed_admin when self-hosted) + gunicorn on :8000
./start_beat.sh     # celery beat (scheduler)
./start_camera.sh   # capture_celery_events (run recorder)
```

The Celery worker lives in [`WaveAssistWorkerEngine`](../WaveAssistWorkerEngine).

## Configuration

All secrets and connection strings come from the environment — **no production values are
baked into the code** (`.env.example` lists every key). Deployment behavior is controlled
by flags read in `WaveAssistApiApp/Utils/runtime_flags.py`:

`WAVEASSIST_SELF_HOSTED`, `WA_WORKER_PROVISIONING`, `WA_DB_PROVISIONING`, `WA_BILLING`,
`WA_STORAGE`, `WA_LOGS`, `WA_CATALOG`, `WA_TELEMETRY`, `WA_AUTH`. With
`WAVEASSIST_SELF_HOSTED=1`, missing DB/Mongo/Redis/secret-key values fail closed instead
of defaulting to cloud infrastructure.

## Self-hosted helpers (management commands)

- `seed_admin` — create/ensure the single admin account (idempotent).
- `deploy_local_agent --path <dir> --uid <uid>` — deploy an agent from a local
  `config.yaml` + node files (no GitHub).
- `password_login` endpoint (`manage/password_login/`) — username/password → admin UID
  when `WA_AUTH=password`.

## Layout

```
WaveAssistApi/         Django project (settings, urls, celery, wsgi)
WaveAssistApiApp/      the app: models, views (manage/data/deploy/run/...), Utils/
  Utils/runtime_flags.py   deployment flags
  Utils/projectSetup.py    build a project from config.yaml + node files
  management/commands/     seed_admin, deploy_local_agent, capture_celery_events, ...
```
