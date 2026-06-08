# waveassist-mcp

Thin MCP server that lets a coding agent (Claude Code / Cursor) build & deploy
deterministic, recurring **WaveAssist** agents. It wraps the WaveAssist HTTP API
with a set of typed tools and contains **no reasoning** — the WaveAgent SKILL is
the brain. See `../docs/SPEC.md`.

## Tools
- `waveassist_login` — save your WaveAssist UID (pass it directly, or browser login)
- `waveassist_status` — login status + locally-built agents
- `waveassist_list_projects` — list the account's live projects (UID is the token); also a connectivity check
- `waveassist_deploy_agent` — create/update an agent + install nodes (unarmed). Idempotent.
- `waveassist_set_key` — store an integration key in the default + test envs
- `waveassist_test_agent` — dry-run on infra (sets `_is_test_run=true`), returns node statuses
- `waveassist_run_agent` — live one-off run now (sets `_is_test_run=false`, side-effects fire)
- `waveassist_run_logs` — fetch run statuses / tracebacks
- `waveassist_arm_schedule` — arm the recurring schedule (after a green run; fires on next cron tick, not now)
- `waveassist_disarm_schedule` — stop a live agent

## Run
```bash
pip install -e .
WAVEASSIST_UID=<your-uid> python -m waveassist_mcp     # stdio MCP server
```

## Config
- `WAVEASSIST_UID` — your WaveAssist user id (or saved to `~/.waveassist/config.json`)
- `WAVEASSIST_API_BASE` — default `https://api.waveassist.io`
- `WAVEASSIST_APP_BASE` — default `https://app.waveassist.io`
