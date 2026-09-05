"""Local input validation must finish before the importer touches either database."""
import importlib.util
from pathlib import Path

import pytest
import yaml

MODULE = Path(__file__).resolve().parents[1] / "api/WaveAssistApiApp/Utils/local_agent.py"
spec = importlib.util.spec_from_file_location("local_agent", MODULE)
local_agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local_agent)


def agent(tmp_path, nodes, variables=None):
    (tmp_path / "node.py").write_text("def run_task():\n    pass\n")
    (tmp_path / "config.yaml").write_text(yaml.safe_dump({"nodes": nodes, "variables": variables or []}))
    return tmp_path


def test_nested_sources_and_multiple_chains(tmp_path):
    (tmp_path / "steps").mkdir()
    (tmp_path / "steps/node.py").write_text("def run_task():\n    pass\n")
    root = agent(tmp_path, [{"key": "first", "file_name": "steps/node.py", "starting_node": True},
                           {"key": "second", "file_name": "node.py", "starting_node": True}])
    config, sources = local_agent.load_agent(root)
    assert set(sources) == {"first", "second"}


@pytest.mark.parametrize("nodes", [
    [{"key": "a", "file_name": "missing.py"}],
    [{"key": "a", "file_name": "../node.py"}],
    [{"key": "a", "file_name": "node.py", "run_after": ["missing"]}],
    [{"key": "a", "file_name": "node.py", "run_after": ["a"]}],
    [{"key": "a", "file_name": "node.py"}, {"key": "a", "file_name": "node.py"}],
    [{"key": "a", "file_name": "node.py", "schedule": {"cron": "* *"}}],
    [{"key": "a", "file_name": "node.py", "schedule": {"interval": {"every": 0, "period": "minutes"}}}],
])
def test_reject_invalid_agent(tmp_path, nodes):
    with pytest.raises((ValueError, OSError)):
        local_agent.load_agent(agent(tmp_path, nodes))


def test_schema_does_not_expose_configured_values():
    config = {"nodes": [], "variables": [
        {"key": "token", "type": "password", "value": "private", "default_value": "private"},
        {"key": "enabled", "value": False, "default_value": True},
    ]}
    schema = local_agent.configuration_schema(config)
    assert "private" not in str(schema)
    assert "value" not in schema["variables"][1]
    assert schema["variables"][1]["default_value"] is True
    assert config["variables"][0]["value"] == "private"


def test_local_entrypoint_is_not_double_wrapped():
    import ast
    from types import SimpleNamespace
    path = MODULE.with_name('utils.py')
    tree = ast.parse(path.read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'get_code_for_node')
    scope = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), scope)
    for source in ('result = 42', 'def run_task():\n    return 42'):
        node = SimpleNamespace(python_code=source, local_source_path='/agents/demo/node.py')
        code = scope['get_code_for_node'](node, 'demo')
        namespace = {}
        exec(code, namespace)
        result = namespace['run_task']()
        assert result == (42 if source.startswith('def ') else None)
