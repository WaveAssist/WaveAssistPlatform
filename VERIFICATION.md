# Production verification and agent handoff

**Status: Git consolidation is complete. Production readiness is NOT confirmed.**

This document is the handoff for the remaining implementation, review, and integration
work. Use the current source and fresh test results as authority. Earlier conversation
claims about a working Docker stack are not proof that this final repository works.
Nothing has been pushed, published, or deployed to a remote server.

## 1. Scope and constraints

- Work in this independent repository, on `codex/open-source-platform`. The sibling
  repositories are original sources/backups, not the place for further platform fixes.
- Preserve Django, MySQL, MongoDB, Redis, Celery workers, beat, camera, and the existing
  UID-based API contract. Do not introduce a second lightweight backend or rewrite auth.
- One host runs multiple Compose services. This is not a requirement for one container.
- Keep provider integrations available. Internet-connected customer deployments are
  expected; billing, telemetry, catalog, storage, provisioning and login are independent.
- Include the dashboard and optional bundled MCP. The SDK remains separately published.
- Keep customer names, private agent source, infrastructure details and credentials out
  of public documentation, fixtures and Git. Use generic deployment profile names.
- Use the previously agreed Python virtual environment on the existing workstation.
  A fresh machine may install `requirements-dev.txt` in its own isolated environment.
- Test on an isolated Compose project with disposable databases and dedicated test
  credentials. Never source an original production `.env` for a test run.
- Do not push, publish, rotate live credentials, migrate production, or contact customers
  as part of this handoff. Those require separate owner-controlled cutover actions.
  Mock outbound sends first; real email, comments, messages and provider writes require
  explicitly authorized test destinations.
- Commit fixes in small, descriptive commits and update this document with evidence.
  Preserve the sanitized history. Do not re-import original Git objects or fabricate dates.

## 2. What is completed

### Repository and history

- API, worker, dashboard and WaveAgent histories consolidated under `api/`, `worker/`,
  `dashboard/`, and `waveagent/`, with one root `.git` and no nested component repos.
- Genuine development dates retained, contributor aliases normalized, subjects prefixed
  by component, and some vague subjects clarified from changed filenames. Attribution
  reflects imported history; a 30/30/40 contributor split was not manufactured.
- Historical credential literals, private env files, service-account keys, database
  snapshots and selected generated files removed from the imported history.
- `.env` exclusions and reference examples added. Original working environments were
  retained outside the public history. Original repository histories were not rewritten.
- MIT license, repository overview, history provenance and local-import documentation added.
- Five implementation/package commits and a verification commit completed at the initial
  handoff, ending at `5d2bb11`. Later handoff-document commits follow that point.
- No remote publication or push. Working tree was clean at the Git milestone.

### Implementation present, but not fully integration-tested

| Area | Changes already in the source |
| --- | --- |
| Configuration | Independent runtime flags, invalid-mode rejection, Compose env plumbing, removal of several embedded credential defaults. |
| Bootstrap | Fail-fast startup, migrations, explicit `WA_BOOTSTRAP_ADMIN`, identity-conflict checks, no MCP token in startup output. |
| Login | Firebase, automatic local UID entry, and simple environment-configured password login returning the configured admin UID. |
| Billing | Billing-off bypass moved ahead of product-specific credit checks; trial eligibility and repository caps respect the flag. |
| Dashboard | Auth/billing/telemetry build args, analytics guard, billing sidebar guard, configurable Firebase/analytics values and MCP URL. |
| Local import | Preflight source/DAG/schedule validation, admin access check, stopped-deployment requirement, in-place node updates and disabled removed nodes. |
| Configuration UI | `Project.local_configuration` metadata, authenticated local Configure response without GitHub, optional variables and preservation of existing values/types in the node wizard. |
| Variables | Missing-only Mongo seeding, typed defaults, password defaults omitted; errors distinguish SQL import from failed Mongo seeding. |
| Worker | Local source path passed as `__file__`; explicit local `run_task()` entrypoints avoid double wrapping; API base override retained. |
| Logs | Rotating worker JSON files on a shared volume, project/node-scoped API reads, stdout retained. |
| Packaging | Internal monorepo build paths, API readiness probe, shared agent mounts, optional MCP profile and persistent MCP configuration. |

Relevant new migration: `api/WaveAssistApiApp/migrations/0068_project_local_configuration.py`
adds project configuration metadata and node source paths. It has not yet been proven
through a full production-like upgrade and rollback rehearsal.

### Checks actually completed

| Check | Result and limitation |
| --- | --- |
| Offline regression suite | **16 passed**, including from an independent fresh clone. Tests cover selected helpers/contracts, not the full Django application. |
| Dashboard build | TypeScript/Vite passed with password auth, billing off, telemetry off, after credential extraction. A large-bundle warning remains. This was a host build of matching dashboard source, not a final fresh Docker web-image test. |
| Real agent validation | The two private target agent configurations passed preflight validation: 15 nodes/7 variables and 17 nodes/44 variables. No production execution was performed. |
| API image | Local image builds succeeded. Subsequent source/credential-extraction edits mean the final committed image still needs rebuilding. |
| Secret checks | Final Git-milestone full-history and release-tree Gitleaks scans passed with zero findings. Known historical literal checks also passed. |
| Private paths | All-ref checks excluded private env files, service-account files and database snapshots. |
| Git integrity | `git fsck --full --no-dangling` passed. Fresh clone and its regression suite passed. |

### Previous Docker state: do not mistake it for completion

An earlier demo used a separate nginx container serving host-built files and partial
MCP checks. It was not a reproducible final Compose deployment. During this audit the
local Colima VM stopped while saving an image and was restarted. Prior demo services
were mostly left stopped afterward. The isolated `wa-audit` project started only
MySQL, MongoDB and Redis; the audit API had not been started at the Git milestone.
Inspect current state before acting; do not assume these containers still exist.

Private temporary backups, scan reports and draft integration fixtures exist on the
original workstation. They may contain raw credentials and private source. Do not copy
them into this repository or treat them as the sole reproducible test suite.

## 3. Deployment profiles that must pass

Use independent test environments and record the exact nonsecret configuration for each.

| Profile | Intended configuration | Required proof |
| --- | --- | --- |
| Consolidated hosted service | Firebase login, billing on, appropriate catalog/integrations, shared worker fleet; bootstrap normally off for migrated data. Telemetry is an explicit choice. | Existing accounts, data, queues, billing, OAuth, schedules and dashboard behavior survive migration to one host. |
| Customer cloud server | Password login, billing off, shared worker and local datastores; integrations and MCP available. | Fresh setup, private repository integration, agent configuration, scheduled execution and logs without a hosted WaveAssist account dependency. |
| Customer connected server | Password or no-login mode, billing off, local datastores, private-network data sources and internet provider access as needed. | Local files, required database drivers, report rendering, internal connectivity, selected delivery channels and backup/restore work. |

Do not describe the third profile as air-gapped. Do not hide integrations simply because
billing or Firebase is disabled. No-login mode is an explicit trusted-access choice,
not a claim that the application has no credentials or needs no network boundary.

## 4. Priority A — reproducible fresh installation

- [ ] Build from a **fresh clone of the final committed revision**, with no sibling repo,
  host `dist/`, local virtualenv, injected source or `docker cp` dependency.
- [ ] Validate Compose with a disposable `.env`; do not print expanded secrets into logs.
  Verify all examples contain usable variable names and intentional defaults.
- [ ] Build API, worker, dashboard and MCP images. Record revision, image IDs, architecture,
  Docker/Compose versions and dependency versions. Resolve any build/install conflicts.
- [ ] API and worker Dockerfiles currently force amd64, while web/MCP do not. Prove the
  actual target architecture; either document amd64-only support or explicitly test/fix
  arm64. Emulated laptop success is not target-server evidence.
- [ ] Resolve unbounded dependency versions and test compatibility of the installed SDK,
  OpenAI client, Celery, Django, MySQL driver and worker packages. MCP's uv lock exists,
  but the Dockerfile currently installs with pip; verify actual reproducibility.
- [ ] Start with empty volumes. Prove migrations, bootstrap, readiness, worker subscription,
  camera and beat startup order. Run Django checks and migration-drift detection.
- [ ] Reboot/restart the stack twice. Prove bootstrap is idempotent and preserves account
  identity, credentials, data and schedules. Conflicting UID/email must fail clearly.
- [ ] Test MCP both enabled and disabled. Core startup must not depend on an omitted MCP.
- [ ] Make persistent data, agent assets and secret mounts usable by the relevant processes.
  Beat/camera receive API env but currently do not mount the API's secret directory;
  check their imports and Firebase initialization requirements.
- [ ] Confirm every browser-visible URL uses the deployed hostname, not container names
  or localhost defaults. Internal worker/MCP calls must use the local API.

## 5. Priority B — core end-to-end behavior

Create a public deterministic fixture that performs no external writes. Do not rely on
the removed legacy `e2e_test.sh`, which could print completion after failures.

- [ ] Import a two-node DAG through the supported command. Trigger it through HTTP.
  Node one stores a value; node two reads/transforms it. Assert the exact final value
  through the SDK/API, not merely the presence of the word SUCCESS in logs.
- [ ] Verify API → Redis → worker → SDK → API → Mongo, plus worker events → camera →
  MySQL → dashboard run/node status. Assert the same run ID across the path.
- [ ] Assert camera produces complete, correct statuses and error messages. Test camera
  restart/disconnection and missed/duplicate events; document or fix recovery behavior.
- [ ] Prove beat scheduling, timezone handling, stop/disarm/rearm and restart persistence.
  Test multiple disconnected chains, downstream ordering and overlapping schedules.
- [ ] Test failing nodes, blocked downstream nodes, retries, timeout, worker restart and
  Redis interruption. Verify terminal statuses and recovery; do not promise exactly-once
  external side effects without a demonstrated idempotency mechanism.
- [ ] Verify default/test environment isolation and run-scoped data, idle runs, dashboard
  publishing and logs. Test test-mode propagation; a dry-run flag alone does not suppress
  every agent's outbound calls.
- [ ] Test both top-level node scripts and explicit `run_task()` files, adjacent assets,
  nested paths and any local helper-module imports actually required by agents.
- [ ] Ensure tests fail nonzero on bad responses, missing results and polling timeouts.
  Capture machine-readable results and redacted diagnostics. Add the fixture and runner
  to the repository so the next clone can reproduce them.

## 6. Priority C — local import, configuration and dashboard

- [ ] Exercise migration 0068 on empty and existing databases. Confirm data/history retention.
- [ ] Reimport real and fixture agents; prove existing node IDs, run references, configured
  secrets, false/zero values and both environments remain correct.
- [ ] Test unauthorized import, duplicate keys, missing files, symlink/path traversal,
  syntax errors, missing dependencies, cycles, malformed YAML and invalid schedules.
  Errors must occur before mutation where possible and exit nonzero.
- [ ] Test removed/reintroduced nodes and dependency changes. Stopping a deployment may
  leave an in-flight run; define and verify draining before changing its node definitions.
- [ ] Confirm timezone and whitespace handling agree between preflight validation and
  the legacy schedule parser. Validate graph rules used by actual deployment as well.
- [ ] Test partial Mongo-seeding failure and retry. SQL/Mongo are not one transaction;
  ensure no overwritten values, misleading success or concurrent duplicate key records.
- [ ] Configure local projects without any GitHub fetch. Check both node wizard and the
  assistant configuration screen; they are separate UI flows.
- [ ] Exercise password, text, number, boolean, JSON, select/object options, schedules,
  repository groups, GitHub/OAuth resources, optional and dependent fields. Preserve
  existing values and distinguish missing data from a failed network request.
- [ ] Confirm all needed Variables, Nodes, Runs, Logs, Integrations and MCP controls are
  reachable when billing is off. Billing navigation is guarded, but direct routes and
  premium/plan checks require a complete sweep. MCP must not be stranded on Credits.
- [ ] Test browser login/logout/reload, password failure/success, no-login entry and actual
  Firebase login. Verify there is no unexpected Firebase redirect/network access in local
  or password mode. Firebase web configuration was moved to build-time JSON variables.
- [ ] Test deployed branding. `VITE_BRAND` exists in the Dockerfile but is not currently
  exposed in Compose's web args; wire and verify it if selecting another brand is required.

## 7. Priority D — flags, providers, storage and MCP

- [ ] Audit every flag consumer, not just the tested helpers. Defaults must preserve the
  intended hosted behavior; changing one flag must not disable unrelated integrations.
- [ ] Billing off: no trial/repo/run gates, provisioning credit dependency, checkout,
  usage debit or billing emails. Billing on: credits, metering, webhook verification,
  subscription changes and duplicate webhook handling still work in provider test mode.
- [ ] Telemetry off: inspect browser and server outbound traffic, not only UI configuration.
  Telemetry on: confirm explicit keys/hosts and expected events without leaking agent data.
- [ ] Shared queues: migrate existing per-account queue assignments explicitly. A shared
  worker does not automatically consume old account queues. Verify multi-account routing
  and access/data isolation; do not blindly seed over existing accounts.
- [ ] Local Mongo provisioning: prove signup/bootstrap avoids Atlas calls. If external
  MySQL/Mongo/Redis are supported, verify overrides and unnecessary local-service dependencies.
- [ ] Configure and test an LLM provider through stored settings. Confirm SDK calls and
  usage behavior with billing on/off and useful errors for missing credentials.
- [ ] Email: verify explicit SMTP/internal relay configuration and any Postmark path; avoid
  relying on failed cloud calls as the normal routing mechanism. Check CC/BCC and attachments.
- [ ] The earlier SDK suite reported **239 passed, 5 skipped, 4 failures**, all CC/BCC
  normalization tests: `test_send_email_cc_list_joined`, `test_send_email_cc_string_normalized`,
  `test_send_email_bcc_list_joined`, `test_send_email_cc_dedupes_and_drops_blanks`. Reproduce
  against the installed version and determine code defect versus obsolete test expectations.
  The SDK is separate; coordinate a versioned fix if required rather than silently diverging.
- [ ] GitHub/OAuth: seed required provider/integration records, credentials and callback URLs.
  Verify repository selection, local versus remote catalog, private repo access, template
  deployment and upgrades. Empty databases must not depend on undocumented production rows.
- [ ] Local/S3 storage: verify uploads, bundle import/export, images, generated dashboards,
  download URLs, path handling and restart persistence. Confirm the local files are actually
  served through a supported route; a filesystem path alone is not a usable browser URL.
- [ ] Logs: test real concurrent workers, rotation, retention, restart and project/node
  filtering. The local reader scans bounded file tails; validate completeness for expected
  load and document truncation. No silent successful empty logs for a broken backend.
- [ ] MCP: perform initialize, tools/list, authentication, project listing, deployment,
  configuration, test run, logs, live run and arm/disarm against the local API. A 406 or
  successful HTTP connection is not sufficient. Exercise persistent registry and restart.
- [ ] MCP authoring currently materializes through the backend's GitHub integration.
  Prove that flow with authorized test credentials and document the dependency. Local
  command import does not automatically provide an MCP local-directory import tool.
- [ ] Run the existing MCP tests and verify bundled plugin/server copies, versions and
  references still agree after consolidation.

## 8. Priority E — target workload and operational readiness

- [ ] Private repository-review workload: verify dependencies, OAuth/PAT configuration,
  repository groups, all scheduled chains, incremental state and restart behavior using
  a dedicated test repository. Test writes only where explicitly authorized.
- [ ] Private reporting workload: verify database connectivity/driver, read-only test data,
  schema compatibility, adjacent files, timezone, report generation/PDF system libraries,
  published links, selected delivery channels and duplicate-delivery handling.
- [ ] Hosted workload: rehearse a production-shaped data restore with multiple accounts,
  projects, billing states and schedules. Synthetic happy paths are not enough.
- [ ] Set target CPU/RAM/disk budgets, worker concurrency and timeouts. The worker currently
  autoscales up to eight processes; measure report/LLM workloads before calling it suitable
  for a small box. Test contention, disk pressure and meaningful health alerts.
- [ ] Decide TLS/reverse-proxy, domain, firewall/VPC rules, allowed hosts/CORS and restricted
  admin access. Current Compose publishes API/web/MCP host ports and uses broad application
  defaults. Retain UID auth as requested, but document that a UID grants API access and
  password mode only gates its disclosure; arbitrary node code runs with worker privileges.
- [ ] Remove default production passwords/tokens/UIDs through deployment configuration.
  Check container images and build contexts for env files, databases, credentials and private
  assets. Only public frontend configuration belongs in `VITE_*` variables.
- [ ] Review dependency advisories and licensing/third-party notices; secret-scan success is
  not a dependency security review or proof that all private business data was removed.
- [ ] Document and test backups of MySQL, Mongo, storage, MCP state and deployment config.
  Specify Redis durability/recovery; a mounted Redis volume alone does not establish a
  persistence policy. Restore onto a separate empty host and verify actual values and runs.
- [ ] Rehearse migration: take consistent backups, stop/drain old schedulers and workers,
  restore data, apply migrations, map queues, set provider URLs/keys, validate, then enable
  one scheduler. Avoid duplicate schedules or sends during overlap.
- [ ] Rehearse rollback, including schema/data compatibility and preventing duplicate work.
  Define recovery objectives and the exact conditions for aborting cutover.
- [ ] Owners rotate previously exposed credentials before publication/cutover, confirm
  ownership/license and contributor aliases, then separately authorize the release and
  production changes. Do not push original backup history or private scan artifacts.

## 9. Acceptance evidence and final completion criteria

For each profile, record: tested Git SHA, architecture and image IDs, redacted configuration,
commands, assertions, test report, browser evidence, failures/fixes, external tests skipped
and why, backup/restore outcome, and rollback result. Keep private evidence outside Git.

The next agent should first make one deterministic full-stack test green, then run the
profile matrix and operational checks. Fix concrete failures and rerun affected checks;
avoid spending credits repeatedly rerunning unchanged passing checks.

Do not mark production readiness complete until:

1. A clean clone builds and boots the final images without manual patches or host artifacts.
2. Core DAG, scheduler, camera, storage, configuration and MCP tests pass together.
3. All three deployment profiles and their required external integrations are verified.
4. Data migration, backup/restore and rollback rehearsals pass.
5. Final source/image/history checks pass, documentation matches behavior, changes are
   committed, and every unresolved limitation is explicitly accepted by the owner.

Until those conditions are met, report **which phase passed** and **what remains unverified**.
Do not describe a build, healthcheck, helper test or a historical demo as full production E2E.
