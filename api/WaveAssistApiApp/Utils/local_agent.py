"""Read and validate local agents before changing platform state."""
from copy import deepcopy
from pathlib import Path
import re
from zoneinfo import ZoneInfo

import yaml


def load_agent(directory):
    root = Path(directory).resolve()
    with (root / "config.yaml").open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    if not isinstance(config, dict) or not isinstance(config.get("nodes"), list) or not config["nodes"]:
        raise ValueError("config.yaml must contain a nonempty nodes list")
    nodes, sources = {}, {}
    for node in config["nodes"]:
        if not isinstance(node, dict):
            raise ValueError("Each node must be a mapping")
        key = node.get("key", "")
        if not isinstance(key, str) or not re.fullmatch(r"[a-z0-9_\-]+", key) or key in nodes:
            raise ValueError("Node keys must be unique lowercase identifiers")
        filename = node.get("file_name")
        if not isinstance(filename, str):
            raise ValueError(f"Node {key} requires file_name")
        path = (root / filename).resolve()
        if not path.is_relative_to(root) or path.suffix != ".py":
            raise ValueError(f"Node {key} must reference a Python file inside the agent folder")
        source = path.read_text(encoding="utf-8")
        compile(source, filename, "exec")
        sources[key] = source
        nodes[key] = node
        schedule = node.get("schedule") or {}
        if not isinstance(schedule, dict) or set(schedule) - {"cron", "interval", "timezone"}:
            raise ValueError(f"Invalid schedule for {key}")
        if "cron" in schedule and "interval" in schedule:
            raise ValueError(f"Choose one schedule for {key}")
        ZoneInfo(schedule.get("timezone", config.get("timezone", "UTC")))
        if "cron" in schedule:
            from celery.schedules import crontab
            fields = str(schedule["cron"]).split()
            if len(fields) != 5:
                raise ValueError(f"Cron for {key} requires five fields")
            crontab(minute=fields[0], hour=fields[1], day_of_month=fields[2],
                    month_of_year=fields[3], day_of_week=fields[4])
        if "interval" in schedule:
            interval = schedule["interval"]
            if (not isinstance(interval, dict) or type(interval.get("every")) is not int
                    or interval["every"] <= 0 or interval.get("period") not in
                    {"days", "hours", "minutes", "seconds", "microseconds"}):
                raise ValueError(f"Invalid interval for {key}")
    visiting, visited = set(), set()

    def visit(key):
        if key in visiting:
            raise ValueError("Node dependencies contain a cycle")
        if key in visited:
            return
        visiting.add(key)
        dependencies = nodes[key].get("run_after", [])
        if not isinstance(dependencies, list):
            raise ValueError(f"run_after for {key} must be a list")
        for dependency in dependencies:
            if not isinstance(dependency, str) or dependency not in nodes:
                raise ValueError(f"Unknown dependency for {key}")
            visit(dependency)
        visiting.remove(key)
        visited.add(key)

    for key in nodes:
        visit(key)
    variables = config.get("variables") or []
    if not isinstance(variables, list):
        raise ValueError("variables must be a list")
    keys = set()
    for variable in variables:
        if not isinstance(variable, dict):
            raise ValueError("Each variable must be a mapping")
        key = variable.get("key") or variable.get("name")
        if not isinstance(key, str) or not key.strip() or key in keys:
            raise ValueError("Variables require unique keys")
        keys.add(key)
    return config, sources


def configuration_schema(config):
    """Expose form metadata, never configured values or password defaults."""
    schema = {key: deepcopy(config[key]) for key in (
        "name", "description", "success_message", "output_default_message",
        "configuration_helper_message") if key in config}
    schema["nodes"] = []
    schema["variables"] = deepcopy(config.get("variables") or [])
    for variable in schema["variables"]:
        variable.pop("value", None)
        if variable.get("type") in {"password", "secret"} or variable.get("is_secret"):
            variable.pop("default_value", None)
    return schema
