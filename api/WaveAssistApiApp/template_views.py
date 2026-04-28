import json
import uuid
from django.shortcuts import render
from .Utils.responseParser import ResponseParser
from .models import *
from .Utils.projectSetup import (
    get_config_yaml_from_github, validate_yaml_config, get_nodes_from_github,
    create_nodes_from_yaml, link_node_dependencies,
    configure_variables, get_latest_commit_sha,
)
from .Utils.constants import *
from .Utils.utils import run_knock_workflow, track_posthog, get_repo_parts_from_url
import base64
import requests
import yaml
from WaveAssistApiApp import manage_views, deployment_views
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.http import HttpResponse
from django.db import transaction
import WaveAssistApiApp.Utils.validator as validator
import WaveAssistApiApp.Utils.utils as utils


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
    should_install_requirements = request.POST.get('should_install_requirements', "0")
    
    if not repo_url:
        return ResponseParser.getParsedErrorMessage("Missing template Repo URL in request")

    timezone = request.POST.get('timezone', 'UTC')


    owner, repo_name = get_repo_parts_from_url(repo_url)
    yaml_config = get_config_yaml_from_github(repo_name, owner)
    is_valid, message =  validate_yaml_config(yaml_config)
    if not is_valid:
        return ResponseParser.getParsedErrorMessage("Error with yaml: " + str(message))

    project_name = yaml_config.get("name", "")
    project_key = f"{project_name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:4]}"
    nodes = yaml_config.get("nodes", [])


    request.POST['project_key'] = project_key
    request.POST['project_name'] = project_name
    request.POST['is_premium'] = False
    create_project_response = manage_views.create_project(request)
    response_data = json.loads(create_project_response.content)
    
    try:
        if response_data.get("success") == "1":
            project_key = response_data["data"]["project_key"]
            project_object = Project.objects.get(project_key=project_key)
        else:
            return ResponseParser.getParsedErrorMessage("Project creation failed: " + response_data.get("message", "Unknown error"))

        if should_install_requirements == "1":
            configure_variables(uid, project_key, yaml_config)

        node_files = get_nodes_from_github(repo_name, owner)
        file_map = {n["node_name"]: n["content"] for n in node_files}
        created_nodes = create_nodes_from_yaml(project_object, nodes, file_map, timezone)
        link_node_dependencies(yaml_config, created_nodes)

        # Persist the source repo URL on the Project so future upgrades
        # (especially for WaveMaker-built projects without a template_key)
        # know where to pull from.
        project_object.github_url = repo_url
        try:
            commit_sha, _ = get_latest_commit_sha(repo_name, owner)
            project_object.deployed_commit_sha = commit_sha
        except Exception:
            pass
        project_object.save()
    except Exception as e:
        print(f"❌ Error creating project or nodes: {str(e)}")
        return ResponseParser.getParsedErrorMessage("Project was not created")


    ##Track PostHog event
    track_posthog(
        uid=str(user_object.uid),
        event='assistant_deployed',
        props={
            'assistant_name': project_name,
            'project_key': project_key,
        }
    )

    return ResponseParser.getParsedSuccessMessage(project_object.get_dict(), '200', 'Project created successfully.')


def check_assistant_update(request):

    success, message, user_object, project_object = validator.validate_user_and_project(
        request, access_level_gte=READ_GTE
    )
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    # Resolve the source repo URL: curated templates use Assistants.github_url
    # (looked up via template_key); WaveMaker-built projects use the URL stored
    # directly on Project.github_url.
    template_key = project_object.template_key
    source_repo_url = ""
    if template_key:
        try:
            assistant = Assistants.objects.get(assistant_key=template_key)
            source_repo_url = assistant.github_url
        except Assistants.DoesNotExist:
            return ResponseParser.getParsedSuccessMessage(
                {"has_update": False}, "200", "Assistant not found for template key."
            )
    elif project_object.github_url:
        source_repo_url = project_object.github_url

    if not source_repo_url:
        return ResponseParser.getParsedSuccessMessage(
            {"has_update": False}, "200", "Project has no upgrade source."
        )

    try:
        owner, repo_name = get_repo_parts_from_url(source_repo_url)
        latest_sha, commit_message = get_latest_commit_sha(repo_name, owner)
    except Exception as e:
        return ResponseParser.getParsedErrorMessage(f"Failed to check for updates: {str(e)}")

    current_sha = project_object.deployed_commit_sha or ""
    has_update = not current_sha or current_sha != latest_sha

    return ResponseParser.getParsedSuccessMessage(
        {
            "has_update": has_update,
            "current_sha": current_sha,
            "latest_sha": latest_sha,
            "latest_commit_message": commit_message,
        },
        "200",
        "Update check complete.",
    )


def upgrade_assistant(request):
    success, message, user_object, project_object = validator.validate_user_and_project(
        request, access_level_gte=ADMIN_GTE
    )
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    # Resolve the source repo URL: curated templates use Assistants.github_url
    # (looked up via template_key); WaveMaker-built projects use the URL stored
    # directly on Project.github_url.
    template_key = project_object.template_key
    source_repo_url = ""
    if template_key:
        try:
            assistant = Assistants.objects.get(assistant_key=template_key)
            source_repo_url = assistant.github_url
        except Assistants.DoesNotExist:
            return ResponseParser.getParsedErrorMessage("Assistant not found.")
    elif project_object.github_url:
        source_repo_url = project_object.github_url

    if not source_repo_url:
        return ResponseParser.getParsedErrorMessage("Project has no upgrade source.")

    owner, repo_name = get_repo_parts_from_url(source_repo_url)

    try:
        latest_sha, commit_message = get_latest_commit_sha(repo_name, owner)
    except Exception as e:
        return ResponseParser.getParsedErrorMessage(f"Failed to fetch latest version: {str(e)}")

    if project_object.deployed_commit_sha == latest_sha:
        return ResponseParser.getParsedErrorMessage("Already on the latest version.")

    try:
        yaml_config = get_config_yaml_from_github(repo_name, owner)
    except Exception as e:
        return ResponseParser.getParsedErrorMessage(f"Failed to fetch config: {str(e)}")

    is_valid, validation_msg = validate_yaml_config(yaml_config)
    if not is_valid:
        return ResponseParser.getParsedErrorMessage("Invalid config in new version: " + str(validation_msg))

    was_running = Deployments.objects.filter(
        project_object=project_object, is_running=True
    ).exists()

    try:
        node_files = get_nodes_from_github(repo_name, owner)
        file_map = {n["node_name"]: n["content"] for n in node_files}
        nodes = yaml_config.get("nodes", [])

        with transaction.atomic():
            Nodes.objects.filter(project_object=project_object).delete()
            timezone = request.POST.get('timezone', 'UTC')
            created_nodes = create_nodes_from_yaml(project_object, nodes, file_map, timezone)
            link_node_dependencies(yaml_config, created_nodes)
            project_object.deployed_commit_sha = latest_sha
            project_object.save()
    except Exception as e:
        return ResponseParser.getParsedErrorMessage(f"Upgrade failed: {str(e)}")

    if was_running:
        data_run_key = utils.get_param(request, "data_run_key", f"{project_object.project_key}_default")
        request.POST = request.POST.copy()
        request.POST["uid"] = str(user_object.uid)
        request.POST["project_key"] = project_object.project_key
        request.POST["data_run_key"] = data_run_key
        request.POST["version"] = f"upgrade_{latest_sha[:8]}_{uuid.uuid4().hex[:6]}"
        deployment_response = deployment_views.deploy_project(request)
        deployment_response_data = json.loads(deployment_response.content)
        if deployment_response_data.get("success") != "1":
            return ResponseParser.getParsedErrorMessage(
                deployment_response_data.get("message", "Upgrade deployed code but failed to start deployment.")
            )

    track_posthog(
        uid=str(user_object.uid),
        event='assistant_upgraded',
        props={
            'project_key': project_object.project_key,
            'template_key': template_key,
            'new_sha': latest_sha,
        }
    )

    return ResponseParser.getParsedSuccessMessage(
        {
            "new_sha": latest_sha,
            "commit_message": commit_message,
        },
        "200",
        "Assistant upgraded successfully.",
    )


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


@cache_page(60 * 60)  # Cache for 1 hr
def list_templates(request):
    # Step 1: Authenticate with Netlify Identity
    identity_url = "https://waveassist.io/.netlify/identity/token"
    payload = {
        "grant_type": "password",
        "username": IDENTITY_USERNAME,  # Changed from "email" to "username" to match curl
        "password": IDENTITY_PASSWORD  # Password should be securely stored/retrieved
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
    }

    auth_resp = requests.post(identity_url, data=payload, headers=headers)
    if auth_resp.status_code != 200:
        return ResponseParser.getParsedErrorMessage("Failed to authenticate with Netlify Identity")
    jwt = auth_resp.json().get("access_token")

    # Step 2: List all template files via Git Gateway
    dir_url = "https://waveassist.io/.netlify/git/github/contents/content/templates"
    headers = {"Authorization": f"Bearer {jwt}"}
    list_resp = requests.get(dir_url, headers=headers)
    if list_resp.status_code != 200:
        return ResponseParser.getParsedErrorMessage("Failed to fetch templates list")

    items = list_resp.json()
    templates = []

    # Step 3: For each markdown file, fetch and parse frontmatter
    for item in items:
        if item.get("type") == "file" and item.get("name", "").endswith(".md"):
            slug = item["name"][:-3]  # remove .md
            file_url = f"https://waveassist.io/.netlify/git/github/contents/content/templates/{slug}.md"
            file_resp = requests.get(file_url, headers=headers)
            if file_resp.status_code != 200:
                continue

            data = file_resp.json()
            raw = base64.b64decode(data.get("content", "")).decode("utf-8")
            parts = raw.split('---', 2)
            if len(parts) < 3:
                continue

            try:
                meta = yaml.safe_load(parts[1].strip()) or {}
            except yaml.YAMLError:
                meta = {}

            # Normalize thumbnail URL
            if "thumbnail" in meta:
                meta["thumbnail"] = meta["thumbnail"].replace(
                    "/images/templates/",
                    "https://waveassist.io/images/templates/"
                )

            meta["slug"] = slug
            templates.append(meta)

    # Step 4: Return list of template metadata
    return ResponseParser.getParsedSuccessMessage(templates, '200', 'Templates fetched successfully.')

@cache_page(60 * 60 * 24 * 7)  # Cache for 1 week
def list_assistants(request):
    # Step 1: Authenticate with Netlify Identity
    identity_url = "https://waveassist.io/.netlify/identity/token"
    payload = {
        "grant_type": "password",
        "username": IDENTITY_USERNAME,  # Changed from "email" to "username" to match curl
        "password": IDENTITY_PASSWORD  # Password should be securely stored/retrieved
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
    }

    auth_resp = requests.post(identity_url, data=payload, headers=headers)
    if auth_resp.status_code != 200:
        return ResponseParser.getParsedErrorMessage("Failed to authenticate with Netlify Identity")
    jwt = auth_resp.json().get("access_token")

    # Step 2: List all assistant files via Git Gateway
    dir_url = "https://waveassist.io/.netlify/git/github/contents/content/assistants"
    headers = {"Authorization": f"Bearer {jwt}"}
    list_resp = requests.get(dir_url, headers=headers)
    if list_resp.status_code != 200:
        return ResponseParser.getParsedErrorMessage("Failed to fetch assistants list")

    items = list_resp.json()
    assistants = []

    # Step 3: For each YAML file, fetch and parse content
    for item in items:
        if item.get("type") == "file" and item.get("name", "").endswith(".yml"):
            slug = item["name"][:-4]  # remove .yml
            file_url = f"https://waveassist.io/.netlify/git/github/contents/content/assistants/{slug}.yml"
            file_resp = requests.get(file_url, headers=headers)
            if file_resp.status_code != 200:
                continue

            data = file_resp.json()
            raw = base64.b64decode(data.get("content", "")).decode("utf-8")

            try:
                meta = yaml.safe_load(raw) or {}
            except yaml.YAMLError:
                meta = {}

            # Normalize thumbnail URL
            if "thumbnail" in meta:
                meta["thumbnail"] = meta["thumbnail"].replace(
                    "/images/templates/",
                    "https://waveassist.io/images/templates/"
                )

            # Normalize primary_image URL if it exists
            if "primary_image" in meta:
                meta["primary_image"] = meta["primary_image"].replace(
                    "/images/templates/",
                    "https://waveassist.io/images/templates/"
                )

            meta["slug"] = slug
            assistants.append(meta)

    # Step 4: Return list of assistant metadata
    return ResponseParser.getParsedSuccessMessage(assistants, '200', 'Assistants fetched successfully.')


def refresh_assistants_cache(request, token):
    STATIC_CACHE_TOKEN = "waveassist_cache_reset_token"

    # Check if the provided token matches
    if token != STATIC_CACHE_TOKEN:
        return ResponseParser.getParsedErrorMessage("Unauthorized")

    try:
        # Clear the cache for the list_assistants view
        # The cache key for @cache_page is typically based on the request path
        cache_key = f"views.decorators.cache.cache_page.{request.META['HTTP_HOST']}.GET./assistants/list_assistants/"
        cache.delete(cache_key)

        # Also try to delete with alternative cache key patterns
        cache.delete("views.decorators.cache.cache_page.GET./assistants/list_assistants/")
        cache.delete("cache_page.GET./assistants/list_assistants/")

        # Clear all cache as fallback (more aggressive but ensures cache is cleared)
        cache.clear()

        # Refresh the cache by calling list_assistants
        # Create a mock request object for the list_assistants function
        from django.http import HttpRequest
        mock_request = HttpRequest()
        mock_request.method = 'GET'
        mock_request.META = request.META.copy()

        # Call list_assistants to refresh the cache
        result = list_assistants(mock_request)

        return ResponseParser.getParsedSuccessMessage({}, '200', 'Cache refreshed successfully.')

    except Exception as e:
        return ResponseParser.getParsedErrorMessage(f"Error refreshing cache: {str(e)}")
