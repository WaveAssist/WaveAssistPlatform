# WaveAssistDashboard

React + TypeScript + Vite dashboard for WaveAssist — projects, the node/DAG builder, runs,
environments/variables, and dashboards. One codebase; the backend and auth are chosen at
**build time** via `VITE_*` env, so the same source builds the hosted app and a
self-hosted box build.

## Develop

```
npm install
npm run dev            # WaveAssist brand
npm run dev:gitzoid    # GitZoid brand
```

## Build

```
npm run build          # tsc + vite build -> dist/
```

Served as static files (see `Dockerfile` / `nginx.conf`).

## Build-time config (`VITE_*`, see `.env.example`)

| Var | Purpose |
|---|---|
| `VITE_DASHBOARD_BASE_URL` | API base (e.g. the box's `http://host:8000`) |
| `VITE_AUTH_MODE` | `firebase` (default) · `local` (UID auto-login) · `password` |
| `VITE_LOCAL_UID` | with `local` mode: baked admin UID → auto-enter, no login page |
| `VITE_TELEMETRY` | `on` (default) · `off` (PostHog/GA) |
| `VITE_BILLING` | `on` (default) · `off` (hide upgrade/credits UI) |
| `VITE_MCP_URL` | Connect-MCP endpoint shown in the UI |
| `VITE_BRAND` | `waveassist` · `gitzoid` (see `CLAUDE.md`) |

Because Vite compiles these into the bundle, a **self-hosted build** is produced by
building with the box values; the cloud build (defaults unset) targets the hosted API.

## Auth modes

- **firebase** — Google login (hosted / multi-user).
- **local** — single-tenant box: `VITE_LOCAL_UID` set → auto-login, no page; unset →
  a minimal UID field.
- **password** — username/password form; posts to `manage/password_login/` which returns
  the admin UID (default creds `admin`/`admin`, shown with a change warning).

See `CLAUDE.md` in this folder for brand/theming architecture and the copy rules.
