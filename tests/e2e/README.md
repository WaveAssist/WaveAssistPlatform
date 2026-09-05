# Full-stack end-to-end test

`run_e2e.py` proves the real run path on a live Compose deployment:

```
HTTP webhook -> API -> Redis -> worker -> SDK -> API -> Mongo
             -> worker events -> camera -> MySQL -> runs API
```

It imports the committed [`fixtures/two_node_dag`](fixtures/two_node_dag) agent,
triggers it over HTTP, polls the run to completion through the same endpoints the
dashboard uses, and asserts the **exact** final value read back from the data API.
It exits nonzero on any failure and prints a machine-readable JSON report.

## Run it

Bring the stack up with the fixture mounted at `/agents` (the runner imports
`/agents/two_node_dag`), then run the test from the repo root:

```bash
# 1. up (isolated project, disposable volumes, fixture mounted, admin seeded)
AGENTS_DIR=./tests/e2e/fixtures COMPOSE_PROFILES=mcp \
  docker-compose -p wa-verify up -d

# 2. wait for the API to be healthy, then run the test
python tests/e2e/run_e2e.py --report /tmp/e2e_report.json
echo "exit=$?"
```

The fixture DAG: `produce` (starting node) stores `seed_value` from the webhook
body `{"n": N}` (default 21); `consume` (runs after) reads it, computes
`final_result = seed * 2`, and stores it. The runner sends `{"n": 21}` and asserts
`final_result == 42`. `produce` is a top-level script and `consume` uses an explicit
`run_task()`, so both node code styles are exercised.

## Configuration

| Env | Default | Purpose |
|---|---|---|
| `API_BASE` | `http://localhost:8000` | API base URL |
| `WAVEASSIST_ADMIN_UID` | `boxadmin000000000000admin` | admin uid (auth) |
| `E2E_COMPOSE` | `docker-compose -p wa-verify` | compose prefix for the import step |
| `E2E_AGENT_PATH` | `/agents/two_node_dag` | in-container fixture path |
| `E2E_TIMEOUT` | `150` | seconds to wait for a terminal run state |

Pass `--no-import` if the fixture is already imported (e.g. re-running the assertion
only). No external network writes are performed by the fixture.
