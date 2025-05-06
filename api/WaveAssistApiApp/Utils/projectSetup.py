import uuid
import base64
import requests
import yaml
from .constants import ADMIN_GTE
from WaveAssistApiApp.models import Project, DataRuns, AccessProvided, Nodes
from django_celery_beat.models import CrontabSchedule, IntervalSchedule
from WaveAssistApiApp import deployment_views
from WaveAssistApiApp import debug_views
from django.test import Client
import json

client = Client()

def create_project_object(project_key, project_name, user_object):
    project_object = Project.objects.create(project_key=project_key, name=project_name)

    # Default run
    data_run_object = DataRuns.objects.create(
        project_object=project_object,
        data_run_key=f"{project_key}_default",
        name="Default",
        is_enabled=True
    )

    # Test run
    data_run_test_object = DataRuns.objects.create(
        project_object=project_object,
        data_run_key=f"{project_key}_test",
        name="Test",
        is_enabled=True
    )

    # Grant access
    AccessProvided.objects.create(type=0, project_object=project_object, user_object=user_object, project_access_type=ADMIN_GTE)
    AccessProvided.objects.create(type=1, data_run_object=data_run_object, user_object=user_object, data_run_access_type=ADMIN_GTE)
    AccessProvided.objects.create(type=1, data_run_object=data_run_test_object, user_object=user_object, data_run_access_type=ADMIN_GTE)

    return project_object


def create_nodes_from_yaml(project_object, nodes, file_map):
    created_nodes = {}

    for node in nodes:
        node_key = node["id"]
        entrypoint = node["entrypoint"].replace(".py", "")
        python_code = file_map.get(entrypoint, "")
        schedule_type, cron_obj, interval_obj = parse_schedule(node.get("schedule", {}))

        node_object = Nodes.objects.create(
            project_object=project_object,
            node_key=f"{node_key}_{uuid.uuid4().hex[:4]}",
            name=node["name"],
            python_code=python_code,
            is_starting_node=node.get("starting_node", False),
            is_enabled=True,
            schedule_type=schedule_type,
            crontab_schedule=cron_obj,
            interval_schedule=interval_obj
        )
        created_nodes[node_key] = node_object

    return created_nodes


def parse_schedule(schedule_dict):
    if "cron" in schedule_dict:
        cron_parts = (schedule_dict["cron"].split(" ") + ["*"] * 5)[:5]
        crontab_obj, _ = CrontabSchedule.objects.get_or_create(
            minute=cron_parts[0],
            hour=cron_parts[1],
            day_of_month=cron_parts[2],
            month_of_year=cron_parts[3],
            day_of_week=cron_parts[4],
            timezone=schedule_dict.get("timezone", "UTC")
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
        node_object = created_nodes[node_def["id"]]
        node_object.run_after_nodes_array.set([created_nodes[k] for k in run_after if k in created_nodes])
        node_object.save()


def get_nodes_from_github(repo_name, owner='WaveAssist', branch='main'):
    repo = f"{owner}/{repo_name}"
    tree_url = f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1"
    try:
        tree_data = requests.get(tree_url).json()
    except Exception as e:
        print(f"[ERROR] Fetching repo tree failed: {e}")
        return []

    node_files = []
    for item in tree_data.get("tree", []):
        if item["type"] == "blob" and item["path"].endswith(".py"):
            file_url = f"https://api.github.com/repos/{repo}/contents/{item['path']}"
            try:
                content = requests.get(file_url).json().get("content", "")
                node_files.append({
                    "node_name": item["path"].split("/")[-1].replace(".py", ""),
                    "content": base64.b64decode(content).decode("utf-8")
                })
            except Exception as e:
                print(f"[SKIP] {item['path']}: {e}")
    return node_files


def install_requirements_from_yaml(request, yaml_config, project_key):
    """Install all packages listed in the 'requirements' key of the YAML"""
    packages = yaml_config.get("requirements", [])
    print(f"Installing packages: {packages}")
    for package_name in packages:
        package_version=None
        request.POST = request.POST.copy()
        if '==' in package_name:
            package_name, package_version = package_name.split('==')
        ##Add project_key
        request.POST['project_key'] = project_key
        request.POST['package_name'] = package_name
        if package_version:
            request.POST['package_version'] = package_version
        debug_views.install_package(request)  # Fire and forget — you can handle response if needed


def get_config_yaml_from_github(repo_name, owner='WaveAssist', branch='main'):
    url = f"https://raw.githubusercontent.com/{owner}/{repo_name}/{branch}/config.yaml"
    resp = requests.get(url)
    return yaml.safe_load(resp.text)


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





