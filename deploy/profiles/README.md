# Deployment profiles

Each profile is a complete starting `.env` for one deployment shape. Copy one to the
repo root as `.env`, fill every `__CHANGE_ME__`, then `docker compose build && up -d`.
Rebuild `web` after changing any `VITE_*` / auth / billing / telemetry / URL / brand
value (the dashboard bakes those at build time).

| Profile file | Shape | Login | Billing | Datastores | Notes |
|---|---|---|---|---|---|
| `hosted.env.example` | Consolidated hosted service (multi-tenant product on one host) | Firebase | on | local Mongo/MySQL/Redis, shared queue | migrate existing data in; bootstrap OFF |
| `cloud-customer.env.example` | Single box on a customer cloud (internet) | password | off | local, shared queue | fresh setup; integrations + MCP; brandable |
| `connected-customer.env.example` | Customer hardware reaching private data (internet) | password / no-login | off | local, shared queue | reporting/PDF; own SMTP relay; DB drivers |

Images are arch-neutral: they build natively for the host (arm64 on Apple silicon /
AWS Graviton, amd64 on x86). Build on the target host, or pass `docker build --platform`.

## Per-deployment checklist

1. **Secrets** — set `DB_PASSWORD`, `DJANGO_SECRET_KEY`, `WORKER_TOKEN` to fresh random
   values. With `WAVEASSIST_SELF_HOSTED=1` (compose default) a missing one fails startup.
2. **Admin** — customer profiles seed one admin (`WA_BOOTSTRAP_ADMIN=1`) from
   `WAVEASSIST_ADMIN_UID`/`_EMAIL`. Change `WA_ADMIN_PASSWORD` from `admin` (the dashboard
   warns until you do). The hosted profile keeps `WA_BOOTSTRAP_ADMIN=0` — data is migrated.
3. **Hostnames** — set `PUBLIC_API_URL` / `PUBLIC_APP_URL` / `PUBLIC_MCP_URL` to the real
   URLs the browser and SDK use. These bake into the dashboard, so rebuild `web` if changed.
4. **TLS / reverse proxy** — compose publishes API `:8000`, dashboard `:8080`, MCP `:9000`
   on the host. For an internet box, put a TLS-terminating reverse proxy (nginx / Caddy /
   ALB) in front and restrict the raw ports with the host firewall / security group.
5. **Host / CORS lock-down** — once DNS is final, set `WA_ALLOWED_HOSTS` to your public
   host(s) **plus** the internal names the app calls itself by: `localhost` (health probe),
   `api` (worker/beat/camera/mcp → `http://api:8000`) and `127.0.0.1`. Set `WA_CORS_ORIGINS`
   to the dashboard origin and `WA_CORS_ALLOW_ALL=0`.
6. **Brand** (customer cloud) — `VITE_BRAND=waveassist|gitzoid` selects the dashboard brand;
   for `firebase` auth also supply the matching `VITE_<BRAND>_FIREBASE_CONFIG` JSON.

## LLM provider

`call_llm` reads its provider/credentials from the per-account KV store, not env. It is
**not** gated by billing. Set one provider (easiest: OpenRouter) via the dashboard or:

```
docker compose exec api python manage.py shell -c "..."   # or the data/set_data_for_key API
```

Key `open_router_key` = your OpenRouter key (default provider). For Azure set `llm_provider`
= `azure` and `azure_openai_config` = `{"api_key":"...","endpoint":"..."}`. Agents whose
nodes are fully deterministic need no LLM key.

## Email (reporting / notifications)

Primary transport is Postmark (`POSTMARK_API_TOKEN` + a verified sender domain). The
fallback is SMTP — now configurable for a self-hosted relay via `WA_SMTP_SERVER` /
`WA_SMTP_PORT` + `MAILER_LOGIN_EMAIL` / `MAILER_LOGIN_EMAIL_PASSWORD`. Set `WA_FROM_EMAIL`
to a sender your provider will accept. With neither configured, sends fail loudly (no
silent success). Live send testing is a separate, explicitly-authorized step.

## GitHub / private repositories

Two independent mechanisms:

- **Agent authoring/deploy via MCP** (`waveassist_deploy_agent`) pushes to a GitHub repo
  using the backend's `GITHUB_TOKEN` + `GITHUB_USERNAME`. Without them, MCP deploy fails —
  but agents can be imported from disk with `deploy_local_agent` (no GitHub needed).
- **User repo OAuth** (the in-dashboard repo picker) needs a `WaveAssist_Provider` DB row
  (name, client_id, client_secret, `redirect_uri` pointing at *your* API host, scopes,
  resource_configs) plus `JWT_SECRET`. Seed it via the Django admin / a data migration; an
  empty DB has none. Override `FRONTEND_URL` / `GITZOID_FRONTEND_URL` to your dashboard host.

## Importing an agent

```
docker compose exec api python manage.py deploy_local_agent \
  --path /agents/<dir> --uid <admin-uid> --project <key>
```

Mount the host agent folder by pointing `AGENTS_DIR` at it (it mounts at `/agents`).
Import is idempotent and never overwrites existing variable values; stop a running
deployment before re-importing.

## Backups

State lives in the `mysql_data`, `mongo_data`, `redis_data`, `platform_data` (and
`mcp_data`) volumes. Back up **MySQL** (accounts, projects, run history, beat schedule)
and **Mongo** (variables, published dashboards) together; Redis holds in-flight queue
state. See `deploy/backup_restore.md` for the tested dump/restore procedure.

## Security model (read before exposing to the internet)

- Auth is **UID-based**: a UID grants API access; password mode only gates its disclosure.
- Node code runs **in-process in the worker** with worker privileges. This is a
  single-tenant / trusted-deployment appliance, not a hostile multi-tenant sandbox.
- Remove default passwords/tokens/UIDs. Keep the raw `:8000/:8080/:9000` ports off the
  public internet (proxy + firewall). Set `WA_ALLOWED_HOSTS` / `WA_CORS_ALLOW_ALL=0`.
