import sys
from datetime import datetime, timezone, timedelta
import waveassist  # Your custom module; ensure it's installed/importable in the container

# Set Django settings if waveassist relies on it (adjust if not needed)
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WaveAssistApi.settings')

waveassist.init("2fec42dd-492b-4294-8154-d33c3ccf", "autotestingproject")

updated_at_str = waveassist.fetch_data("updated_at")

if not updated_at_str:
    sys.exit(1)  # Unhealthy: No data fetched

try:
    updated_at = datetime.fromisoformat(updated_at_str)
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    delta = now - updated_at

    if delta <= timedelta(minutes=15):
        sys.exit(0)  # Healthy: Update is recent (<=15 min old)
    else:
        sys.exit(1)  # Unhealthy: Update is stale (>15 min old)
except Exception as e:
    sys.exit(1)  # Unhealthy: Any error (e.g., invalid format)