# WaveAssistDashboard — Agent Guide

React 18 + Vite + Bootstrap dashboard. **One codebase, two branded builds** — WaveAssist and
GitZoid — deployed to separate domains, sharing one backend (`api.waveassist.io`) and DB.

## Multi-brand architecture

The brand is chosen at **build time** by the `VITE_BRAND` env var (`waveassist` | `gitzoid`),
set per Netlify site. It is **not** a runtime `?brand=` switch (that exists in dev only, for
local preview). Brand = deployment.

- **`src/config/branding.tsx`** — the single source of truth. `getBrand()` resolves the active
  brand (VITE_BRAND → dev localStorage override → default `waveassist`). `BRANDS` holds per-brand
  identity (name, title, accent hex, catalog/template, login copy). `applyBrandToDocument()` (called
  once from `main.tsx`) stamps `<html data-brand="...">`, the tab title, and the favicon.
- **`BrandLogo`** — both brands are **typographic wordmarks**, not raster logos:
  `/waveassist` and `/gitzoid` in JetBrains Mono, with a brand-accent slash. There are no logo
  image assets. `variant="mark"` renders the collapsed form (WaveAssist = bare `/`, GitZoid = `/gz`).

## Theming — how colors work

All brand color lives in **CSS custom properties** in `src/utils/design-system.css`:
`:root` defines the **WaveAssist** token set; `:root[data-brand="gitzoid"]` overrides it. `data-brand`
is set from `VITE_BRAND` at boot (statically in `index.html` via `%VITE_BRAND%`, and by JS as a
safety net) → zero-FOUC.

**Rule: never hardcode a brand color. Use the tokens:**

| Token | WaveAssist | GitZoid | Use |
|---|---|---|---|
| `--color-primary` | `#D8FF00` | `#12C46A` | accent: CTAs, active, links, the slash |
| `--color-primary-rgb` | `216,255,0` | `18,196,106` | for `rgba(var(--color-primary-rgb), α)` tints |
| `--color-primary-hover` | `#C2E600` | `#0E9E55` | hover on filled |
| `--color-bg-main` | `#0B0C0F` | `#0B0E12` | page background |
| `--color-bg-section` | `#0F1114` | `#0E1217` | alt section band |
| `--color-bg-card` | `#14161B` | `#14181F` | cards, nav, panels |
| `--color-border` | `#23262D` | `#232A33` | every 1px hairline |
| `--color-text-primary` | `#ECEEF2` | `#FFFFFF` | primary text |
| `--color-text-secondary` | `#8B909B` | `#9BA4B0` | muted text/labels |
| `--color-text-button` | `#0B0C0F` | `#0B0E12` | text on accent fills — always carbon |

Brand source of truth (mirrored here, not imported):
`WaveAssist/WaveAssistStudio/colors_and_type.css` and
`Gitzoid/GitZoidAgent/GitZoidStudio/colors_and_type.css`. Design language (both): dark carbon,
flat, 1px hairline borders, **no shadows, no gradients as identity**, Inter (UI) + JetBrains Mono
(labels/numbers/mark), one accent used sparingly.

**Inline styles & SVG:** in JSX `style={{}}` objects use `"var(--color-primary)"` etc. (CSS props
resolve `var()`). But SVG **presentation attributes** (`fill="..."`, `stroke="..."`) do NOT resolve
`var()` — use `style={{ fill: "var(--color-primary)" }}` instead, or the JS hex `getBrand().accent`
for things like React Flow `markerEnd.color`.

## Build & env

- Dev: `npm run dev` (WaveAssist) · `npm run dev:gitzoid` (GitZoid). Or `?brand=gitzoid` in dev.
- Build: `npm run build:waveassist` · `npm run build:gitzoid` (both run `scripts/gen-redirects.mjs`
  then `tsc && vite build`).
- Env (set per Netlify site; see `.env.example`): `VITE_BRAND`, `VITE_FIREBASE_*` (falls back to the
  WaveAssist project if unset), `VITE_FIREBASE_AUTH_PROXY` (per-brand Firebase auth-handler proxy for
  `_redirects`), `VITE_DASHBOARD_BASE_URL`.
- **`scripts/gen-redirects.mjs`** generates `public/_redirects` at build time so the Firebase
  auth-handler proxy points at the correct per-brand project (a static file can't read env).
- Firebase config is env-driven in `src/utils/firebase.tsx` (`src/components/firebase.tsx` re-exports it).

## Netlify

Two sites, same repo/branch. Each sets its own `VITE_BRAND` + `VITE_FIREBASE_*` + custom domain
(`app.waveassist.ai`, `app.gitzoid.com`). A single `git push` auto-builds both.

## Backend coupling (Phase 0, already deployed)

`Account.product` drives brand/billing on the backend. WaveAssist = credits (OpenRouter). GitZoid =
free trial → `gitzoid_pro`. All backend behavior is additive and gated on `product == "gitzoid"`.
The "paid" signal is `plan_name`, not `is_premium`.

## `is_super_admin` vs `is_premium` — the node-editing gate

**`is_super_admin` (on `User`) is the single functional gate for the node/DAG builder** — add,
edit, delete, run a node, the Actions column, the deploy button. Frontend reads it via
`hasSuperAdminAccess()` (`src/utils/plan.ts`); backend enforces it via `validate_super_admin`
(`manage_views.py`). Non-admins (including all GitZoid end-users) get a **read-only** DAG.

**`is_premium` is NOT an edit gate and NOT a billing signal** — it is a vestigial legacy
"premium-project" lock (`isProjectPremium && !isUserPremium`). New projects default
`is_premium=false`, billing is `plan_name`, and it gates nothing that `is_super_admin` doesn't
already cover. Don't reintroduce `is_premium` as a capability gate, and don't "consolidate" it
away casually — the leftover lock still touches shared **WaveAssist** paths, so any removal is a
deliberate, separately-tested change, not a drive-by cleanup.

## Deployment lifecycle policy (GitZoid trial)

- **No failure circuit breaker.** A crashing/erroring agent is left to retry every tick — there is
  intentionally no auto-pause on consecutive failures (the `consecutive_failures` column is unused).
- **GitZoid trial exhausted → auto-stop.** When a trial hits 0 credits, the credit-check gate
  (`sdk_views.check_account_credits`) calls `metering.stop_trial_deployments()` to disable the
  celery-beat schedule and free the worker. This is the ONLY automatic deployment stop.
- **Upgrade → auto-resume.** The DoDo webhook (`payment_views`) calls
  `metering.resume_account_deployments()` for a `product == "gitzoid"` account once it's on a paid
  plan (mirror `utils.resume_deployment` / `stop_deployment`).
- **WaveAssist never auto-stops on empty credits** — it's pay-as-you-go: an out-of-credit run just
  can't afford the LLM call and resumes seamlessly on top-up, with no deployment stop. Don't add a
  credit-exhaustion stop to the WaveAssist path.
