# Starting node, written as a top-level script (no run_task()): the importer wraps
# this body in run_task() automatically. Exercises the "top-level script" code path.
import waveassist

# The webhook stores its POST body under "<start_node_key>_webhook_data".
payload = waveassist.fetch_data("produce_webhook_data", default={}) or {}
try:
    n = int(payload.get("n", 21))
except (TypeError, ValueError):
    n = 21

waveassist.store_data("seed_value", n)
