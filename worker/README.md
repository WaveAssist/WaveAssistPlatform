# WaveAssistWorkerEngine

The WaveAssist Celery worker. It consumes run tasks from Redis and executes each agent
node's Python code, reporting progress back to [`WaveAssistApi`](../WaveAssistApi) and
emitting the events the run-recorder (`camera`) turns into run history.

## How it works

- `celery_app.py` — Celery app; the worker consumes the queue `queue_<ACCOUNT_ID>`
  (`task_default_queue`). For a single-box deployment set `ACCOUNT_ID` to the shared
  operator UUID so it matches the API's dispatch queue.
- `celery_worker.py` — the `run_dag` / `run_task` tasks (schedule a DAG, run one node).
- `Engine/TaskRunner.py` — wraps a node's flat code in `run_task()` and `exec()`s it;
  `print` is redirected to the JSON logger. Node data I/O goes back through the API via
  the `waveassist` SDK, so the worker never talks to Mongo directly.

## Run it

```
pip install -r requirements.txt
celery -A celery_worker worker --loglevel=info --autoscale=8,1 --prefetch-multiplier=1
```

## Configuration (env)

- `REDIS_URL` — broker + result backend (**required**, no baked default).
- `ACCOUNT_ID` — its queue is `queue_<ACCOUNT_ID>`. For the platform box, the bare shared
  operator UUID (see `.env.example`).
- `BASE_URL` / `WAVEASSIST_API_BASE_URL` — the API the SDK calls back into.

## Notes

- The node runtime executes user-authored code in-process — appropriate for a trusted
  single-tenant box, not a hostile multi-tenant environment.
- The Claude Code CLI (for the `claude_cli` LLM provider) is an **optional** build arg
  (`INSTALL_CLAUDE_CLI=1`), off by default; the box uses OpenRouter/Azure.
