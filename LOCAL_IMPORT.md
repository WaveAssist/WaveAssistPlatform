# Importing a local agent

Set `AGENTS_DIR` to the host directory containing your agent folders. Compose mounts
that directory read-only at `/agents` in both the API and worker. Keep agent secrets
outside Git. This directory may contain private customer code; it is not part of the
platform source release.

```sh
docker compose exec api python manage.py deploy_local_agent \
  --path /agents/my-agent --project my_agent
```

The command uses `WAVEASSIST_ADMIN_UID`, or accepts `--uid` explicitly. It validates
Python sources, dependency references and cycles, schedules, and variable keys before
changing the project. It stores form metadata in MySQL, so Configure does not require
a GitHub repository. Password defaults and configured values are omitted from this
metadata. Optional variables remain available.

Importing creates default and test environments. Reimporting updates matching nodes
in place and disables removed nodes, preserving historical references. It inserts
only missing Mongo values, retaining existing settings. Stop an active deployment
before importing a new version; enable scheduling after reviewing and testing it.
SQL and Mongo are separate datastores: if Mongo seeding fails after the SQL import,
the command exits with an error and can be safely retried.

Both top-level scripts and files with a `run_task()` entrypoint are supported.
`__file__` points to the source path inside the container. Read adjacent assets using
that path; the worker working directory remains `/app`. Agent-specific Python
packages must be installed in a worker image before running the agent. Import does
not install packages or start schedules automatically.

The Logs view reads project-scoped JSON logs from the shared volume in local log
mode. Each worker process rotates its log at 2 MB with three backups. On process
initialization, log files older than seven days are removed. Container stdout also
remains available through `docker compose logs worker`.
