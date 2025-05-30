import json
import uuid
from django.shortcuts import render
from .Utils.responseParser import ResponseParser
from .models import *
from .Utils.projectSetup import *
from .Utils.constants import *
from .Utils.utils import run_knock_workflow
import base64
from WaveAssistApiApp import manage_views


def deploy_template(request):
    request.POST = request.POST.copy()
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
    is_valid, message =  validate_yaml_config(yaml_config)
    if not is_valid:
        return ResponseParser.getParsedErrorMessage("Error with yaml: " + str(message))

    project_name = yaml_config.get("name", "")
    project_key = f"{project_name.lower()}_{uuid.uuid4().hex[:4]}"
    nodes = yaml_config.get("nodes", [])


    request.POST['project_key'] = project_key
    request.POST['project_name'] = project_name
    create_project_response = manage_views.create_project(request)
    response_data = json.loads(create_project_response.content)
    
    try:
        if response_data.get("success") == "1":
            project_key = response_data["data"]["project_key"]
            project_object = Project.objects.get(project_key=project_key)
        else:
            return ResponseParser.getParsedErrorMessage("Project creation failed: " + response_data.get("message", "Unknown error"))

        install_requirements_from_yaml(request, yaml_config, project_key)
        node_files = get_nodes_from_github(repo_name)
        file_map = {n["node_name"]: n["content"] for n in node_files}

        created_nodes = create_nodes_from_yaml(project_object, nodes, file_map)
        link_node_dependencies(yaml_config, created_nodes)
        configure_variables(uid, project_key, yaml_config)
    except:
        return ResponseParser.getParsedErrorMessage("Project was not created")

    try:
        data = {
            'template_name': str(project_name.lower()),
            'project_key': str(project_key),
        }
        run_knock_workflow(str(uid), 'template', data)
    except:
        pass

    return ResponseParser.getParsedSuccessMessage(project_object.get_dict(), '200', 'Project created successfully.')


def get_template(request, slug):
    # Step 1: Netlify Identity login
    identity_url = "https://waveassist.io/.netlify/identity/token"
    identity_payload = {
        "grant_type": "password",
        "username": IDENTITY_USERNAME,  # Changed from "email" to "username" to match curl
        "password": IDENTITY_PASSWORD  # Password should be securely stored/retrieved
    }
    identity_headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*"
    }

    identity_resp = requests.post(identity_url, data=identity_payload, headers=identity_headers)
    if identity_resp.status_code != 200:
        return ResponseParser.getParsedErrorMessage("Failed to authenticate with Netlify Identity")
    jwt = identity_resp.json().get("access_token")

    # Step 2: Fetch the content from Git Gateway
    git_gateway_url = f"https://waveassist.io/.netlify/git/github/contents/content/templates/{slug}.md"
    headers = {
        "Authorization": f"Bearer {jwt}"
    }
    file_resp = requests.get(git_gateway_url, headers=headers)
    if file_resp.status_code != 200:
        return ResponseParser.getParsedErrorMessage("Failed to fetch template content")

    # Step 3: Return the raw content (optional: decode base64 if needed)
    file_data = file_resp.json()
    print(file_data)
    content = base64.b64decode(file_data['content']).decode('utf-8')
    parts = content.split('---', 2)
    if len(parts) >= 3:
        # Parse the YAML frontmatter (the middle part)
        try:
            output_dict = yaml.safe_load(parts[1].strip())
            markdown_content = parts[2].strip()
            output_dict['markdown'] = markdown_content
            if 'thumbnail' in output_dict:
                output_dict['thumbnail'] = output_dict['thumbnail'].replace("/images/templates/", "https://waveassist.io/images/templates/")
        except Exception as e:
            return ResponseParser.getParsedErrorMessage(f"Failed to parse YAML frontmatter: {str(e)}")
    else:
        return ResponseParser.getParsedErrorMessage("Invalid template format")

    return ResponseParser.getParsedSuccessMessage(output_dict, '200', 'Template fetched successfully.')