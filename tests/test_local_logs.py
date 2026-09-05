import importlib.util
import json
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / 'api/WaveAssistApiApp/Utils/local_logs.py'
spec = importlib.util.spec_from_file_location('local_logs', MODULE)
local_logs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local_logs)


def test_logs_are_project_and_node_scoped(tmp_path):
    lines = [
        {'asctime': '2026-01-01 00:00:00', 'message': 'allowed', 'extra': {'project_key': 'a', 'node_key': 'one'}},
        {'asctime': '2026-01-01 00:00:01', 'message': 'other project', 'extra': {'project_key': 'b', 'node_key': 'one'}},
        {'asctime': '2026-01-01 00:00:02', 'message': 'other node', 'extra': {'project_key': 'a', 'node_key': 'two'}},
    ]
    (tmp_path / 'worker-test.log').write_text('\n'.join(map(json.dumps, lines)) + '\npartial JSON')
    assert [x['log'] for x in local_logs.read_logs(tmp_path, 'a', ('one',))] == ['allowed']
    assert [x['log'] for x in local_logs.read_logs(tmp_path, 'a', limit=1)] == ['other node']
