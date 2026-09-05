"""Runtime deployment flags — the single place that decides which control-plane
behaviours are active for this deployment.

Every flag is INDEPENDENT and defaults to the current hosted-cloud behaviour, so:
  * unset everywhere  -> behaves exactly like today's SaaS (cloud untouched);
  * a consolidated primary box can keep billing/auth ON but switch only the fleet
    (WA_WORKER_PROVISIONING=shared_queue);
  * a single-tenant customer box turns the SaaS-only pieces off.

Read these via the helpers (e.g. ``flags.billing_enabled``) rather than re-reading
os.environ at each call site, so behaviour is consistent and testable.
"""
import os


def _mode(name: str, default: str) -> str:
    val = os.getenv(name)
    return (val if val is not None and val.strip() != "" else default).strip().lower()


def _bool(name: str, default: str) -> bool:
    return _mode(name, default) in ("1", "true", "yes", "on")


# Master switch — also drives fail-closed config in settings.py.
SELF_HOSTED = _bool("WAVEASSIST_SELF_HOSTED", "0")

# Each independent; defaults preserve cloud behaviour.
WORKER_PROVISIONING = _mode("WA_WORKER_PROVISIONING", "fargate")     # fargate | shared_queue
DB_PROVISIONING = _mode("WA_DB_PROVISIONING", "atlas")               # atlas | local
BILLING = _mode("WA_BILLING", "on")                                  # on | off
STORAGE = _mode("WA_STORAGE", "s3")                                  # s3 | local
LOGS = _mode("WA_LOGS", "cloudwatch")                                # cloudwatch | local
CATALOG = _mode("WA_CATALOG", "remote")                              # remote | local
TELEMETRY = _mode("WA_TELEMETRY", "on")                              # on | off
AUTH = _mode("WA_AUTH", "firebase")                                  # firebase | local | password

for _name, _value, _allowed in (
    ("WA_WORKER_PROVISIONING", WORKER_PROVISIONING, {"fargate", "shared_queue"}),
    ("WA_DB_PROVISIONING", DB_PROVISIONING, {"atlas", "local"}),
    ("WA_BILLING", BILLING, {"on", "off"}),
    ("WA_STORAGE", STORAGE, {"s3", "local"}),
    ("WA_LOGS", LOGS, {"cloudwatch", "local"}),
    ("WA_CATALOG", CATALOG, {"remote", "local"}),
    ("WA_TELEMETRY", TELEMETRY, {"on", "off"}),
    ("WA_AUTH", AUTH, {"firebase", "local", "password"}),
):
    if _value not in _allowed:
        raise ValueError(f"{_name} must be one of {', '.join(sorted(_allowed))}; got {_value!r}")

# Derived booleans (use these at call sites).
use_fargate = WORKER_PROVISIONING == "fargate"
use_atlas = DB_PROVISIONING == "atlas"
billing_enabled = BILLING == "on"
use_s3 = STORAGE == "s3"
use_cloudwatch = LOGS == "cloudwatch"
use_remote_catalog = CATALOG == "remote"
telemetry_enabled = TELEMETRY == "on"
password_auth = AUTH == "password"


def summary() -> dict:
    """For a health/debug endpoint: what this deployment has enabled."""
    return {
        "self_hosted": SELF_HOSTED,
        "worker_provisioning": WORKER_PROVISIONING,
        "db_provisioning": DB_PROVISIONING,
        "billing": BILLING,
        "storage": STORAGE,
        "logs": LOGS,
        "catalog": CATALOG,
        "telemetry": TELEMETRY,
        "auth": AUTH,
    }
