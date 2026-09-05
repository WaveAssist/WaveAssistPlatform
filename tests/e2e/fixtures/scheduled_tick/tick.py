import waveassist
from datetime import datetime, timezone


def run_task():
    count = waveassist.fetch_data("tick_count", default=0) or 0
    try:
        count = int(count)
    except (TypeError, ValueError):
        count = 0
    count += 1
    waveassist.store_data("tick_count", count)
    waveassist.store_data("last_tick", datetime.now(timezone.utc).isoformat())
    return count
