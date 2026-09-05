"""Read bounded, project-scoped worker logs from the shared box volume."""
import json
from pathlib import Path


def read_logs(directory, project_key, node_keys=(), limit=500):
    logs = []
    paths = sorted(Path(directory).glob('worker-*.log*'), key=lambda p: p.stat().st_mtime, reverse=True)[:64]
    for path in paths:
        with path.open('rb') as stream:
            # Bound each read even if a custom worker does not rotate its log.
            stream.seek(0, 2)
            size = stream.tell()
            stream.seek(max(0, size - 2_000_000))
            if size > 2_000_000:
                stream.readline()
            for line in stream:
                try:
                    record = json.loads(line)
                    context = record.get('extra') or record
                    if context.get('project_key') != project_key:
                        continue
                    if node_keys and context.get('node_key') not in node_keys:
                        continue
                    logs.append({'timestamp': record.get('asctime', ''), 'log': record.get('message', '')})
                except (ValueError, TypeError, AttributeError):
                    continue
    return sorted(logs, key=lambda item: item['timestamp'], reverse=True)[:limit]
