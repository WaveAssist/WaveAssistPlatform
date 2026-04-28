"""
wavemaker_views.py — server-side GitHub push for WaveMaker-built assistants.

WaveMaker (running in the user's worker) POSTs the artifacts produced by
its pipeline (config_yaml + code_files + readme). This endpoint:

  - On create: creates a private repo under the WaveAssist GitHub
    account and pushes all files. Returns the repo_url.
  - On update: pushes new commits to the existing repo. Returns the
    same repo_url.

The WaveMaker worker is responsible for calling /template/deploy_template/
(create) or /template/upgrade_assistant/ (update) afterward. This endpoint
only owns the GitHub side — keeps the WaveAssist GH token off clients.
"""

import base64
import hashlib
import json
import re
import time
import uuid

import requests
import yaml
from django.views.decorators.csrf import csrf_exempt

from .models import Project, AccessProvided, User
from .Utils.responseParser import ResponseParser
from .Utils.constants import GITHUB_TOKEN, GITHUB_USERNAME, ADMIN_GTE


GITHUB_API = "https://api.github.com"
MAX_WAVEMAKER_ASSISTANTS_PER_USER = 25


def _owner_tag(uid: str) -> str:
    """
    Stable per-uid token written into a repo's GitHub description on
    create. On update, the request's uid must hash to the same token —
    that's how we authorize a push without a Project row existing.
    """
    digest = hashlib.sha256(f"wm:{uid}".encode("utf-8")).hexdigest()[:16]
    return f"wm-owner:{digest}"


def _gh(method: str, path: str, body: dict = None) -> requests.Response:
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    url = f"{GITHUB_API}{path}"
    if method == "GET":
        return requests.get(url, headers=headers)
    if method == "POST":
        return requests.post(url, headers=headers, json=body or {})
    if method == "PUT":
        return requests.put(url, headers=headers, json=body or {})
    raise ValueError(f"Unsupported method: {method}")


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower().strip()).strip("-")
    return s[:40] or "assistant"


def _create_repo(repo_name: str, description: str, owner_tag: str) -> str:
    """Create a private repo under the WaveAssist account, embedding the
    owner_tag in the description for later auth on update."""
    existing = _gh("GET", f"/repos/{GITHUB_USERNAME}/{repo_name}")
    if existing.status_code == 200:
        return f"{GITHUB_USERNAME}/{repo_name}"
    desc_user = (description or "")[:300]
    full_description = f"{desc_user} [{owner_tag}]".strip()
    resp = _gh("POST", "/user/repos", {
        "name": repo_name,
        "description": full_description[:350],
        "private": True,
        "auto_init": True,
    })
    if resp.status_code != 201:
        raise Exception(f"GitHub repo creation failed ({resp.status_code}): {resp.text[:200]}")
    full = resp.json().get("full_name", f"{GITHUB_USERNAME}/{repo_name}")
    time.sleep(2)  # GH eventual consistency before pushing files
    return full


def _verify_repo_owner(repo_full_name: str, expected_tag: str) -> bool:
    """Fetch repo, confirm the owner_tag is in its description."""
    resp = _gh("GET", f"/repos/{repo_full_name}")
    if resp.status_code != 200:
        return False
    desc = (resp.json().get("description") or "")
    return expected_tag in desc


def _push_file(repo_full_name: str, file_path: str, content: str, message: str) -> bool:
    existing = _gh("GET", f"/repos/{repo_full_name}/contents/{file_path}")
    sha = existing.json().get("sha") if existing.status_code == 200 else None
    body = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
    }
    if sha:
        body["sha"] = sha
    resp = _gh("PUT", f"/repos/{repo_full_name}/contents/{file_path}", body)
    return resp.status_code in (200, 201)


def _push_all_files(repo_full_name: str, files: dict, commit_msg_prefix: str) -> list[str]:
    failures = []
    for fname, content in files.items():
        if not _push_file(repo_full_name, fname, content, f"{commit_msg_prefix}: {fname}"):
            failures.append(fname)
    return failures


def _build_files_to_push(yaml_config: dict, code_files: dict, readme_md: str) -> dict:
    files = {
        "config.yaml": yaml.dump(yaml_config, default_flow_style=False, sort_keys=False, allow_unicode=True),
    }
    for fname, content in code_files.items():
        files[fname if fname.endswith(".py") else f"{fname}.py"] = content
    if readme_md:
        files["README.md"] = readme_md
    return files


def _project_count_for_user(user_object) -> int:
    return Project.objects.filter(
        accessprovided__user_object=user_object,
        accessprovided__type=0,
        accessprovided__project_access_type__gte=ADMIN_GTE,
    ).distinct().count()


@csrf_exempt
def materialize_assistant(request):
    """POST /api/v1/wavemaker/materialize_assistant — push artifacts to a WaveAssist-owned GitHub repo."""
    if request.method != "POST":
        return ResponseParser.getParsedErrorMessage("Only POST is supported")

    if request.content_type and "json" in request.content_type:
        try:
            body = json.loads(request.body or b"{}")
        except Exception:
            return ResponseParser.getParsedErrorMessage("Invalid JSON body")
    else:
        body = dict(request.POST.items())

    uid = (body.get("uid") or "").strip()
    assistant_name = (body.get("assistant_name") or "").strip()
    config_yaml_str = body.get("config_yaml") or ""
    code_files = body.get("code_files") or {}
    readme_md = body.get("readme_md") or ""
    existing_project_key = (body.get("existing_project_key") or "").strip() or None
    existing_repo_url = (body.get("existing_repo_url") or "").strip() or None

    if not uid:
        return ResponseParser.getParsedErrorMessage("Missing uid")
    if not assistant_name:
        return ResponseParser.getParsedErrorMessage("Missing assistant_name")
    if not config_yaml_str:
        return ResponseParser.getParsedErrorMessage("Missing config_yaml")
    if not isinstance(code_files, dict) or not code_files:
        return ResponseParser.getParsedErrorMessage("code_files must be a non-empty dict")

    try:
        user_object = User.objects.get(uid=uid)
    except User.DoesNotExist:
        return ResponseParser.getParsedErrorMessage("User not found")

    try:
        yaml_config = yaml.safe_load(config_yaml_str)
    except yaml.YAMLError as e:
        return ResponseParser.getParsedErrorMessage(f"Invalid config_yaml: {e}")

    owner_tag = _owner_tag(uid)
    is_update = bool(existing_repo_url)

    if is_update:
        # Auth: the repo's GitHub description must contain this user's
        # owner_tag. This works whether or not deploy_template ever
        # ran (so orphan repos can still be updated by their creator).
        parts = existing_repo_url.rstrip("/").split("/")
        if len(parts) < 2:
            return ResponseParser.getParsedErrorMessage("Malformed existing_repo_url")
        repo_full_name = f"{parts[-2]}/{parts[-1]}"
        if not repo_full_name.startswith(f"{GITHUB_USERNAME}/"):
            return ResponseParser.getParsedErrorMessage("existing_repo_url must point at the WaveAssist GitHub account")

        if not _verify_repo_owner(repo_full_name, owner_tag):
            return ResponseParser.getParsedErrorMessage("Not authorized to update this repo")

        repo_url = existing_repo_url
        commit_prefix = "Update assistant via WaveMaker"
    else:
        # Per-user assistant cap (creates only). Counts deployed projects
        # via AccessProvided — orphan repos (deploy_template failed) are
        # not counted here, which is acceptable at current scale.
        if _project_count_for_user(user_object) >= MAX_WAVEMAKER_ASSISTANTS_PER_USER:
            return ResponseParser.getParsedErrorMessage(
                f"Project limit reached ({MAX_WAVEMAKER_ASSISTANTS_PER_USER}). Delete unused projects and try again."
            )

        slug = _slugify(assistant_name)
        repo_name = f"wa-{slug}-{uuid.uuid4().hex[:6]}"
        try:
            repo_full_name = _create_repo(repo_name, yaml_config.get("description", ""), owner_tag)
        except Exception as e:
            return ResponseParser.getParsedErrorMessage(str(e))

        repo_url = f"https://github.com/{repo_full_name}"
        commit_prefix = "Initial assistant build via WaveMaker"

    files_to_push = _build_files_to_push(yaml_config, code_files, readme_md)
    failures = _push_all_files(repo_full_name, files_to_push, commit_prefix)
    if failures:
        return ResponseParser.getParsedErrorMessage(f"Failed to push files: {failures}")

    return ResponseParser.getParsedSuccessMessage(
        {
            "repo_url": repo_url,
            "is_update": is_update,
            "files_pushed": len(files_to_push),
        },
        "200",
        "Assistant pushed to GitHub.",
    )
