import os
import zipfile
import tempfile
import yaml
import boto3
from datetime import datetime
from django.http import FileResponse
from django.views.decorators.csrf import csrf_exempt
from WaveAssistApiApp.models import User, Project, Nodes
from .Utils.constants import AWSS3_ACCESS_KEY_VALUE, AWSS3_SECRET_KEY_VALUE
from .Utils.responseParser import ResponseParser
from .Utils.utils import upload_file_to_s3, zip_directory, user_has_project_access

from django.http import JsonResponse

# ---------- Utility Functions ----------
def get_user_from_token(request):
    uid = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        return User.objects.get(uid=uid)
    except User.DoesNotExist:
        return None

def write_node_files(project, base_dir):
    node_configs = []
    for node in Nodes.objects.filter(project_object=project):
        file_name = f"{node.node_key}.py"
        path = os.path.join(base_dir, file_name)
        with open(path, "w") as f:
            f.write(node.python_code)
        node_configs.append(
            {"key": node.node_key,
                             "name": node.name,
                             "file_name": file_name,
            }
        )

    return node_configs

def create_config_yaml(project_id, node_configs, base_dir):
    config = {"project_key": project_id, "nodes": node_configs}
    with open(os.path.join(base_dir, "config.yaml"), "w") as f:
        yaml.dump(config, f, default_flow_style=False)

# ---------- Views ----------

def pull_bundle(request, project_id):
    user = get_user_from_token(request)
    if not user:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    project = user_has_project_access(user, project_id)
    if not project:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    base_dir = os.path.join(tempfile.gettempdir(), "waveassist", user.uid, project_id)
    os.makedirs(base_dir, exist_ok=True)

    node_configs = write_node_files(project, base_dir)
    create_config_yaml(project_id, node_configs, base_dir)

    zip_path = os.path.join(tempfile.gettempdir(), "waveassist", user.uid, f"{project_id}.zip")
    zip_directory(base_dir, zip_path)

    uid = user.uid
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    s3_file_name = f"{uid}/{project_id}/{timestamp}.zip" if uid and project_id else f"{timestamp}.zip"
    upload_file_to_s3(zip_path, s3_file_name)

    response = FileResponse(open(zip_path, "rb"), as_attachment=True)
    response["Content-Disposition"] = f'attachment; filename="{project_id}.zip"'
    response["Content-Type"] = "application/zip"
    return response


@csrf_exempt
def push_bundle(request, project_id):
    if request.method != "POST":
        return JsonResponse({"error": "Unauthorized"}, status=401)

    user = get_user_from_token(request)
    if not user:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    project = user_has_project_access(user, project_id)
    if not project:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    if "bundle" not in request.FILES:
        return JsonResponse({"error": "No Bundle Found"}, status=401)

    bundle = request.FILES["bundle"]
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "bundle.zip")
        with open(zip_path, "wb") as f:
            for chunk in bundle.chunks():
                f.write(chunk)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(tmpdir)

        config_path = os.path.join(tmpdir, "config.yaml")
        if not os.path.exists(config_path):
            return JsonResponse({"error": "No YAML file found!"}, status=401)

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        for node in config.get("nodes", []):
            name = node.get("name")
            file_name = node.get("file_name")
            key = node.get("key")
            if not key or not file_name:
                continue
            code_path = os.path.join(tmpdir, file_name)
            if not os.path.exists(code_path):
                continue
            with open(code_path, "r") as f:
                code = f.read()
            try:
                node_obj = Nodes.objects.get(node_key=key, project_object=project)
                node_obj.python_code = code
                node_obj.save()
            except Nodes.DoesNotExist:
                print(f"⚠️ Skipping unknown node '{name}' — not found in project {project.project_key}")

    return ResponseParser.getParsedSuccessMessage({}, 200, "Bundle processed successfully")
