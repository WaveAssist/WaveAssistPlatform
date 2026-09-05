"""Regression checks for deployment flags; no network or production credentials."""
import ast
import types
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "api"

@pytest.mark.parametrize("enabled,expected", [(False, False), (True, True)])
def test_customer_billing_disables_trial_gate(enabled, expected):
    tree = ast.parse((API / "WaveAssistApiApp/Utils/metering.py").read_text())
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {"account_is_on_trial", "trial_blocks_run"}]
    ns = {"runtime_flags": types.SimpleNamespace(billing_enabled=enabled), "_FREE_PLANS": {None, "", "starter"}}
    exec(compile(ast.Module(body=functions, type_ignores=[]), "metering", "exec"), ns)
    account = types.SimpleNamespace(product="gitzoid", plan_name="starter", trial_credits_limit=30, trial_credits_used=100)
    assert ns["trial_blocks_run"](account) is expected

def test_credit_bypass_precedes_product_specific_gate():
    source = (API / "WaveAssistApiApp/sdk_views.py").read_text().split("def check_account_credits(request):", 1)[1]
    assert source.index("if not flags.billing_enabled:") < source.index('if account.product == "gitzoid":')

def test_dashboard_docker_accepts_every_runtime_flag():
    source = (ROOT / "dashboard/Dockerfile").read_text()
    for name in ("VITE_AUTH_MODE", "VITE_BILLING", "VITE_TELEMETRY", "VITE_LOCAL_UID", "VITE_MCP_URL"):
        assert "ARG " + name in source
        assert name + "=$" + name in source

def test_bootstrap_is_explicit_and_startup_fails_on_error():
    source = (API / "start.sh").read_text()
    assert "set -eu" in source
    assert "WA_BOOTSTRAP_ADMIN" in source
    assert "|| echo" not in source
    assert "exec gunicorn" in source
