# Deploy the WaveAssist MCP server to Google Cloud Run — start to finish

Goal: a live `https://mcp.waveassist.ai/mcp` that any host adds with
`Authorization: Bearer <UID>`. Order: push to GitHub → fast first deploy → CI/CD on
push → custom domain → verify.

**Prerequisites (one-time installs):**
- `gcloud` CLI — https://cloud.google.com/sdk/docs/install ; then `gcloud auth login`.
- A GCP project with **billing enabled** (the free tier still requires a billing
  account attached; usage stays $0 at beta volume). Note your **project id**.
- `gh` CLI (or just `git`) for the GitHub push.

> **Phase 0 is already done:** the repo is initialized, secret-swept, and committed
> on `main` (67 files). You just push it.

---

## Phase 1 — Create the GitHub repo and push

From the `WaveAgent/` directory:

```bash
# Option A — GitHub CLI (creates the public repo + pushes in one shot):
gh auth login                      # if not already authenticated
gh repo create WaveAssist/WaveAgent --public --source=. --remote=origin --push

# Option B — web + git: create an EMPTY public repo at github.com/new named
# WaveAssist/WaveAgent (no README/license), then:
git remote add origin https://github.com/WaveAssist/WaveAgent.git
git push -u origin main
```

The root `.claude-plugin/marketplace.json` makes the Claude Code plugin installable
immediately (`/plugin marketplace add WaveAssist/WaveAgent`) — independent of the
hosting below.

---

## Phase 2 — Fast first deploy (live URL in ~2 minutes)

This builds `mcp/Dockerfile` with Cloud Build and deploys — no Artifact Registry or
CI wiring needed yet. Run from `WaveAgent/`:

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud run deploy waveassist-mcp \
  --source mcp \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000 --timeout 3600 \
  --min-instances 0 --max-instances 2 \
  --set-env-vars WAVEASSIST_API_BASE=https://api.waveassist.io,WAVEASSIST_APP_BASE=https://app.waveassist.io,WAVEASSIST_HOME=/data/.waveassist
```

- First run prompts to enable Cloud Build + Run APIs and create a source repo — say yes.
- `--allow-unauthenticated` is correct: MCP clients can't do Google IAM; our own
  `Authorization: Bearer <UID>` header is the tenancy auth.
- It prints a **Service URL** like `https://waveassist-mcp-xxxxx-uc.a.run.app`.
  Your endpoint is that URL + `/mcp`.

**Smoke test it** (add to your own Cursor or Claude Code, using the run.app URL):
```json
"waveassist": {
  "url": "https://waveassist-mcp-xxxxx-uc.a.run.app/mcp",
  "headers": { "Authorization": "Bearer <YOUR_WAVEASSIST_UID>" }
}
```
Then ask the agent: *"check my waveassist status"* — it should report
`uid_present: true, transport: http`.

---

## Phase 3 — CI/CD: auto-deploy on every push (GitHub Actions → Cloud Run)

One-time setup with Workload Identity Federation (no JSON keys). Replace
`YOUR_PROJECT_ID`:

```bash
export PROJECT_ID=YOUR_PROJECT_ID REGION=us-central1 GH=WaveAssist/WaveAgent
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
echo "PROJECT_NUMBER = $PN   (and IMAGE registry = ${REGION}-docker.pkg.dev/${PROJECT_ID}/mcp/waveassist-mcp)"
```

Then edit **`.github/workflows/deploy-mcp.yml`**:
- replace `<PROJECT_NUMBER>` with the printed `PN`,
- if your project id isn't `waveassist`, update `PROJECT_ID`, the `service_account`,
  and the `IMAGE` path to match.

Commit + push → the **Deploy MCP to Cloud Run** action builds, pushes, and deploys on
every push to `main` that touches `mcp/**`.

```bash
git commit -am "wire Cloud Run CI/CD" && git push
```

---

## Phase 4 — Custom domain `mcp.waveassist.ai`

**Quick (beta) — Cloud Run domain mapping:**
```bash
gcloud run domain-mappings create --service waveassist-mcp \
  --domain mcp.waveassist.ai --region us-central1
```
It prints DNS records (a CNAME/A) — add them at your DNS provider. (This path is
Preview-grade; fine for a beta.)

**Production — global external ALB + managed TLS** (lower latency, GA): create a
serverless NEG → backend → URL map → managed cert → HTTPS proxy → forwarding rule,
then point an `A` record at the forwarding-rule IP. Full commands in
`docs/HOSTING.md`.

> If `waveassist.io` DNS is on **Cloudflare**, set the `mcp` record to **DNS-only
> (grey cloud)** so Google's cert validation isn't intercepted.

---

## Phase 5 — Verify + roll out

1. `https://mcp.waveassist.ai/mcp` resolves over HTTPS.
2. Add it to Cursor / Claude Code with your UID header (configs in `docs/USAGE.html`)
   and run *"check my waveassist status"* → `uid_present: true`.
3. Build a real agent end-to-end: *"using waveassist, build an agent that …"*.

## Before public (not needed for the private beta)
- **Stateless registry:** Cloud Run has no disk, so `WAVEASSIST_HOME` resets on
  redeploy (can duplicate projects). Persist per-user agent state via
  `api.waveassist.io` instead of the local file.
- **Scoped credential:** replace the raw-UID Bearer header with a scoped, revocable
  key (or OAuth, so the Claude Code plugin can ship a static URL + browser login).
- **Cold start:** add `--min-instances=1` if the first-call latency bothers users
  (leaves the free tier).
