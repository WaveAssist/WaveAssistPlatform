import json
import uuid

from django.shortcuts import render

from .models import *
from .Utils.responseParser import ResponseParser
from .Utils.projectSetup import *



def deploy_template(request):
    uid = request.POST.get('uid', '')
    try:
        user_object = User.objects.get(uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')

    if not user_object.can_create_projects:
        return ResponseParser.getParsedErrorMessage('You do not have access to create projects.')

    repo_url = request.POST.get('repo_url', '')
    if not repo_url:
        return ResponseParser.getParsedErrorMessage("Missing template Repo URL in request")

    repo_name = repo_url.split("/")[-1].replace(".git", "")
    yaml_config = get_config_yaml_from_github(repo_name)

    project_name = yaml_config.get("name", "")
    project_key = f"{project_name.lower()}_{uuid.uuid4().hex[:4]}"

    nodes = yaml_config.get("nodes", [])

    project_object = create_project_object(project_key, project_name, user_object)
    install_requirements_from_yaml(request, yaml_config)
    node_files = get_nodes_from_github(repo_name)
    file_map = {n["node_name"]: n["content"] for n in node_files}

    created_nodes = create_nodes_from_yaml(project_object, nodes, file_map)
    link_node_dependencies(yaml_config, created_nodes)
    configure_variables(uid, project_key, yaml_config)

    return ResponseParser.getParsedSuccessMessage(project_object.get_dict(), '200', 'Project created successfully.')
