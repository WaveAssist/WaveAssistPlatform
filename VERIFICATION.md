# Verification status

This is a local review candidate. Nothing has been published or deployed remotely.

Completed during consolidation:
- 16 deployment regression tests pass and cover billing bypass, explicit bootstrap, local input
  validation, local entrypoint handling, and project/node-scoped log reading.
- The dashboard TypeScript/Vite build passed after environment-only credential
  extraction, with password auth and billing/telemetry disabled.
- The API Docker image built successfully; an updated build and isolated integration
  stack are in progress.
- Final repository full-history and release-tree secret scans passed with zero findings.
- All-ref checks confirm private environment files, service-account keys and database
  snapshots are excluded. Git object integrity (`git fsck`) passed.
- All 16 regression tests also passed from an independent fresh clone.
- Git consolidation is complete locally; the working tree is clean after commits.

Remaining integration phase:
- Fresh Compose startup, migrations and repeated bootstrap.
- Local import/reimport through real SQL and Mongo databases, preserved values and
  history, Configure UI, and password/no-login/Firebase deployment profiles.
- Actual worker DAG execution, camera statuses, beat scheduling and dashboard logs.
- MCP authoring and run lifecycle against the local API.
- Data migration and external-provider verification for a hosted cutover.

Run the offline regression suite with `python -m pytest tests -q` after installing
`requirements-dev.txt`. These checks do not substitute for the integration phase.
