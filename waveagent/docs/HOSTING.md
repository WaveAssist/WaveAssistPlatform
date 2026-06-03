# Hosting the WaveAssist MCP server (the zero-install path)

The simplest experience for end users is a **hosted MCP server** they reach by
URL — no `uv`, no `npx`, no Python to install, exactly like a Slack/GitHub MCP.
This guide is for the **WaveAssist maintainer** who runs that server.

## What it is

The same server (`waveassist_mcp`, the 8 tools) can run over **streamable-HTTP**
instead of stdio. Auth is **per request**: each call carries
`Authorization: Bearer <WaveAssist-UID>`, which the server reads from the request
header (multi-tenant — every user is isolated by their UID). No login tool, no
per-machine config file.

> Verified: with no `WAVEASSIST_UID` env and an empty home dir, a client sending
> `Authorization: Bearer <uid>` is authenticated as that uid; a client with no
> header is unauthenticated. Auth is purely the header.

## Run it

Locally:
```bash
cd mcp && pip install -e .
WAVEASSIST_MCP_PORT=8000 waveassist-mcp-http      # or: python -m waveassist_mcp --http
# endpoint: http://127.0.0.1:8000/mcp
```

Docker (recommended for hosting):
```bash
cd mcp
docker build -t waveassist-mcp .
docker run -p 8000:8000 -v waveassist-data:/data/.waveassist waveassist-mcp
```
Then put it behind TLS at **`https://mcp.waveassist.io/mcp`** (your load balancer /
ingress terminates TLS; the container speaks plain HTTP on `$PORT`). Works on any
container host (Cloud Run, Fly, Render, ECS, …) — they set `$PORT`, which the
server honours.

### Environment
| Var | Default | Purpose |
|---|---|---|
| `PORT` / `WAVEASSIST_MCP_PORT` | `8000` | listen port |
| `WAVEASSIST_MCP_HOST` | `0.0.0.0` | bind host |
| `WAVEASSIST_API_BASE` | `https://api.waveassist.io` | backend the tools call |
| `WAVEASSIST_APP_BASE` | `https://app.waveassist.io` | dashboard/login base |
| `WAVEASSIST_HOME` | `/data/.waveassist` | per-user agent registry dir — **mount a volume** |

## Where to host it (free) + CI/CD

Two free, auto-deploy-on-push options ship in the repo — pick one.

### Quickest (free): Render
`render.yaml` is a Blueprint. Push the repo to GitHub → render.com → **New → Blueprint**
→ pick the repo. Render builds `mcp/Dockerfile`, gives you HTTPS + a custom domain, and
**redeploys on every push**. Caveats: the free web service **sleeps after ~15 min idle
(~1-min cold start)** and has **no disk**.

### Best free (recommended): Google Cloud Run
Perpetual free tier, **true scale-to-zero ($0 when idle)**, **60-min request timeout**
(important for streamable-HTTP/SSE MCP sessions), and a real custom domain. CI/CD is
`.github/workflows/deploy-mcp.yml` (GitHub Actions + Workload Identity Federation — no
JSON keys). One-time setup (replace `waveassist` / `<PROJECT_NUMBER>`):

```bash
export PROJECT_ID=waveassist REGION=us-central1 GH=WaveAssist/WaveAgent
gcloud services enable run.googleapis.com artifactregistry.googleapis.com iamcredentials.googleapis.com --project $PROJECT_ID
gcloud artifacts repositories create mcp --repository-format=docker --location=$REGION --project $PROJECT_ID
gcloud iam service-accounts create gh-deployer --project $PROJECT_ID
SA=gh-deployer@$PROJECT_ID.iam.gserviceaccount.com
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SA" --role=roles/run.admin
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SA" --role=roles/artifactregistry.writer
gcloud iam service-accounts add-iam-policy-binding $SA --member="serviceAccount:$SA" --role=roles/iam.serviceAccountUser --project $PROJECT_ID
gcloud iam workload-identity-pools create github --location=global --project $PROJECT_ID
gcloud iam workload-identity-pools providers create-oidc github --location=global --workload-identity-pool=github \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='${GH}'" --project $PROJECT_ID
PN=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
gcloud iam service-accounts add-iam-policy-binding $SA --project $PROJECT_ID --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/${PN}/locations/global/workloadIdentityPools/github/attribute.repository/${GH}"
echo "Put this PROJECT_NUMBER in deploy-mcp.yml: $PN"
```

**Custom domain `mcp.waveassist.io`:** map it via a serverless NEG behind a global
external ALB (managed TLS) — the GA path; `gcloud run domain-mappings` is still Preview.
If `waveassist.io` DNS is on Cloudflare, set the `mcp` record to **DNS-only (grey
cloud)** so cert validation isn't intercepted.

### Production (your AWS): ECS Express Mode
⚠️ **AWS App Runner is in maintenance and closed to new customers (Apr 30 2026)** — do
not use it. Use **Amazon ECS Express Mode** (one-shot ALB + TLS + autoscaling, fits your
existing ECS/CloudWatch/IAM, ~$5–10/mo with scale-to-zero, shared ALB so a single small
service stays cheap). Same container; CI/CD = GitHub Actions → ECR → deploy. Run the free
beta on Cloud Run now and move the identical image to ECS Express Mode for prod.

### Gotchas (read before prod)
- **No persistent disk** on Cloud Run / Render-free → `WAVEASSIST_HOME` is ephemeral, so
  the per-user dedup registry resets on redeploy (can create duplicate projects).
  Beta-ok; **before prod, make the registry stateless** — persist per-user agent state
  through `api.waveassist.io` (or GCS) so the MCP container holds no state.
- **Cold start** after idle: the first call eats container boot (sub-s–few-s for the slim
  image). `--min-instances=1` removes it (leaves the free tier; small fixed cost).
- **Streaming timeouts:** Cloud Run `--timeout=3600` (set in the workflow) keeps long
  MCP sessions from being cut at the default; Render/Koyeb idle spin-down will also drop
  an idle-but-open session.

## How end users connect (once it's live at mcp.waveassist.io)

Every host config is just a URL + the user's UID in a Bearer header — the same
shape as their existing Slack/GitHub MCP entries.

**Cursor / Claude Code / any host with native remote-MCP support:**
```json
"waveassist": {
  "url": "https://mcp.waveassist.io/mcp",
  "headers": { "Authorization": "Bearer <YOUR_WAVEASSIST_UID>" }
}
```
Claude Code (CLI) equivalent:
```bash
claude mcp add --transport http waveassist https://mcp.waveassist.io/mcp \
  --header "Authorization: Bearer <YOUR_WAVEASSIST_UID>"
```

**Hosts without native remote MCP (e.g. older Claude Desktop)** — bridge with
`mcp-remote` (the same shim a ClickUp-style entry uses), no Python needed:
```json
"waveassist": {
  "command": "npx",
  "args": ["-y", "mcp-remote", "https://mcp.waveassist.io/mcp",
           "--header", "Authorization: Bearer <YOUR_WAVEASSIST_UID>"]
}
```

The **skill** (the build brain) is still delivered per host: bundled in the Claude
Code plugin, copied into `.cursor/skills/`, or pointed-at on a generic host.

## Open design points (flag before public)

- **Auth = raw UID in a header.** Fine for the private beta (same exposure as a
  PAT in a header). The hardening phase replaces it with a **scoped, revocable API
  key** (or OAuth, so the Claude Code plugin can ship a static URL and trigger a
  browser login instead of a pasted UID).
- **Registry durability.** The per-user create-vs-update registry is a local file
  (`WAVEASSIST_HOME`). A single instance with a mounted volume is fine; for
  multi-instance / autoscaling, move it to server-side storage (a small WaveAssist
  endpoint keyed by uid) so re-deploys still dedup.
- **Claude Code plugin wiring.** Three options for the per-user UID in a *static*
  plugin: (a) ship the bundled local server (needs `uv`); (b) ship a URL with an
  env-expanded header (`Bearer ${WAVEASSIST_UID}`) if the host expands it; (c) ship
  the plugin as skill-only and have users `claude mcp add` the hosted URL. OAuth
  (hardening) removes this choice entirely.
