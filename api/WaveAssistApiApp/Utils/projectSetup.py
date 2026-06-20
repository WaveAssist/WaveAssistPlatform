import time
import uuid
import base64
import requests
import yaml
from .constants import ADMIN_GTE, GITHUB_USERNAME, GITHUB_TOKEN
from WaveAssistApiApp.models import Project, DataRuns, AccessProvided, Nodes
from django_celery_beat.models import CrontabSchedule, IntervalSchedule
from WaveAssistApiApp import deployment_views
from django.test import Client
import json

client = Client()


def create_nodes_from_yaml(project_object, nodes, file_map, timezone):
    created_nodes = {}

    for node in nodes:
        node_key = node["key"]
        file_name = node["file_name"].replace(".py", "")
        python_code = file_map.get(file_name, "")
        name = node.get("name", node_key)
        schedule_type, cron_obj, interval_obj = parse_schedule(node.get("schedule", {}), timezone)
        node_object = Nodes.objects.create(
            project_object=project_object,
            node_key=node_key,
            name=name,
            python_code=python_code,
            is_starting_node=node.get("starting_node", False),
            is_enabled=True,
            schedule_type=schedule_type,
            crontab_schedule=cron_obj,
            interval_schedule=interval_obj
        )
        created_nodes[node_key] = node_object

    return created_nodes


def parse_schedule(schedule_dict, default_timezone="UTC"):
    if not schedule_dict:
        return "none", None, None
    if "cron" in schedule_dict:
        cron_parts = (schedule_dict["cron"].split(" ") + ["*"] * 5)[:5]
        crontab_obj, _ = CrontabSchedule.objects.get_or_create(
            minute=cron_parts[0],
            hour=cron_parts[1],
            day_of_month=cron_parts[2],
            month_of_year=cron_parts[3],
            day_of_week=cron_parts[4],
            timezone= default_timezone
        )
        return "crontab", crontab_obj, None

    elif "interval" in schedule_dict:
        interval_obj, _ = IntervalSchedule.objects.get_or_create(
            every=schedule_dict["interval"]["every"],
            period=schedule_dict["interval"]["period"]
        )
        return "interval", None, interval_obj

    return "none", None, None


def link_node_dependencies(yaml_config, created_nodes):
    for node_def in yaml_config.get("nodes", []):
        run_after = node_def.get("run_after", [])
        if not run_after:
            continue
        node_object = created_nodes[node_def["key"]]
        node_object.run_after_nodes_array.set([created_nodes[k] for k in run_after if k in created_nodes])
        node_object.save()


def get_wanted_node_files(nodes):
    """Base names (without .py) of the source files referenced by config nodes."""
    return {
        node.get("file_name", "").split("/")[-1].replace(".py", "")
        for node in (nodes or [])
        if node.get("file_name")
    }


def get_nodes_from_github(repo_name, owner='WaveAssist', branch='main', wanted_files=None):
    """Fetch node source files for a repo from GitHub.

    When `wanted_files` is provided (a set/iterable of file base names without the
    ".py" suffix, e.g. the `file_name`s referenced by nodes in config.yaml), only
    those files are fetched. This avoids pulling every .py in the repo (tests,
    helpers, etc.) which both wastes time and burns GitHub rate limit. When it is
    None we fall back to fetching all .py files (legacy behavior).
    """
    repo = f"{owner}/{repo_name}"
    tree_url = f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1"
    wanted = set(wanted_files) if wanted_files is not None else None
    try:
        tree_resp = requests.get(
            tree_url, auth=(GITHUB_USERNAME, GITHUB_TOKEN), timeout=(5, 30)
        )
        tree_data = tree_resp.json()
    except Exception as e:
        print(f"[ERROR] Fetching repo tree failed: {e}")
        return []

    node_files = []
    for item in tree_data.get("tree", []):
        if item["type"] != "blob" or not item["path"].endswith(".py"):
            continue
        node_name = item["path"].split("/")[-1].replace(".py", "")
        if wanted is not None and node_name not in wanted:
            continue
        file_url = f"https://api.github.com/repos/{repo}/contents/{item['path']}?ref={branch}"
        try:
            file_resp = requests.get(
                file_url, auth=(GITHUB_USERNAME, GITHUB_TOKEN), timeout=(5, 30)
            )
            content = file_resp.json().get("content", "")
            if content:
                node_files.append({
                    "node_name": node_name,
                    "content": base64.b64decode(content).decode("utf-8")
                })
        except Exception as e:
            print(f"[SKIP] {item['path']}: {e}")
    return node_files


def get_latest_commit_sha(repo_name, owner='WaveAssist', branch='main'):
    url = f"https://api.github.com/repos/{owner}/{repo_name}/commits/{branch}"
    resp = requests.get(url, auth=(GITHUB_USERNAME, GITHUB_TOKEN), timeout=(5, 30))
    if resp.status_code != 200:
        raise Exception(f"Failed to fetch latest commit: {resp.status_code}")
    data = resp.json()
    return data["sha"], data["commit"]["message"]


def get_config_yaml_from_github(repo_name, owner='WaveAssist', branch='main'):
    url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/config.yaml?ref={branch}"
    # A freshly-created repo's first commit can lag in GitHub's Contents API, so a
    # read-back immediately after the push 404s even though the file is there.
    # Retry on 404 (propagation lag); bail fast on any other status (auth / rate
    # limit are not transient and shouldn't be hammered).
    last_status = None
    for _ in range(5):
        resp = requests.get(url, auth=(GITHUB_USERNAME, GITHUB_TOKEN), timeout=(5, 30))
        last_status = resp.status_code
        if resp.status_code == 200:
            content = resp.json().get("content", "")
            return yaml.safe_load(base64.b64decode(content).decode("utf-8"))
        if resp.status_code != 404:
            break
        time.sleep(2)
    raise Exception(f"Failed to fetch config.yaml (last status {last_status})")



def validate_yaml_config(yaml_config):
    ##Validate that node_keys are all unique and lower case and without spaces
    if not isinstance(yaml_config, dict):
        return False, "YAML config is not a valid dictionary"
    nodes_array = yaml_config.get("nodes", [])
    node_keys = set()
    for node in nodes_array:
        node_key = node.get("key")
        if not node_key:
            return False, "Node key is missing in one of the nodes"
        if not isinstance(node_key, str):
            return False, f"Node key is not a string: {node_key}"
        node_key_expected = node_key.lower().replace(" ", "_")
        if node_key != node_key_expected:
            return False, f"Node key '{node_key}' is not in lower case or contains spaces. Use '{node_key_expected}' instead."
        if node_key in node_keys:
            return False, f"Duplicate node key found: {node_key}"
        node_keys.add(node_key)
    return True, "YAML config is valid"


def configure_variables(uid, project_key, yaml_config):
    default_env_key = f"{project_key}_default"
    test_env_key = f"{project_key}_test"
    all_envs = [default_env_key, test_env_key]
    variables = yaml_config.get("variables", [])
    for env_key in all_envs:
        for variable in variables:
            var_name = variable["name"]
            var_value = variable["value"]
            try:
                payload = {
                    'uid': uid,
                    'project_key': project_key,
                    'data_run_key': env_key,
                    'data': var_value,
                    'data_key': var_name,
                    'data_type': 'string',
                }
                response = client.post('/data/set_data_for_key/', data=json.dumps(payload),
                                       content_type='application/json')
            except Exception as e:
                pass





