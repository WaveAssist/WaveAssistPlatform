import json
import os
import uuid
import requests
import hashlib
import time
from datetime import datetime, timedelta
from authlib.integrations.django_client import OAuth
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from authlib.integrations.requests_client import OAuth2Session
from .models import *
from .models import TokenAuthMethod, TokenFetchMethod
from .Utils.responseParser import ResponseParser
from .Utils.constants import *
import WaveAssistApiApp.Utils.utils as utils
import WaveAssistApiApp.Utils.validator as validator
import jwt
from django.test import Client
from django.shortcuts import redirect

oauth = OAuth()
client = Client()


def get_nested(data, path, default=None):
    """
    Safely get a nested value from a dict/list using dot notation.
    Example: get_nested(obj, "properties.email")
    """
    if not path:
        return data

    keys = path.split(".")
    current = data

    for key in keys:
        if isinstance(current, dict):
            if key not in current:
                return default
            current = current.get(key)
        elif isinstance(current, list):
            # Only allow non-negative integer indices (reject "-1", "1.5", etc.)
            if not key.isdigit():
                return default
            index = int(key)
            if index >= len(current):
                return default
            current = current[index]
        else:
            return default

    return current


# Safety cap on paginated provider fetches (e.g. 10 pages x per_page=100 = 1000 items)
MAX_RESOURCE_PAGES = 10


def _extract_items(items_data, resource_config):
    """Extract the list of items from a provider response using items_key (or sane defaults)."""
    items_key = resource_config.get("items_key")
    if items_key:
        items = get_nested(items_data, items_key, [])
    else:
        items = (
            items_data
            if isinstance(items_data, list)
            else get_nested(items_data, "data", [])
        )
    return items if isinstance(items, list) else []


def fetch_provider_items(resource_config, headers):
    """
    Fetch items from a provider's resource endpoint, following pagination when
    resource_config["pagination"] is set. Supported pagination types:
      - {"type": "link_header"}: follow RFC 5988 Link rel="next" (GitHub-style),
        capped at MAX_RESOURCE_PAGES.

    Returns (items, error_message): items is a list on success (error None),
    or None with an error message. Raises on HTTP errors (requests exceptions).
    """
    url = resource_config.get("endpoint", "")

    graphql_query = resource_config.get("graphql_query")
    if graphql_query:
        response = requests.post(
            url,
            json={"query": graphql_query},
            headers={**headers, "Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        items_data = response.json()
        if "errors" in items_data:
            return None, items_data["errors"][0].get("message", "GraphQL error")
        return _extract_items(items_data, resource_config), None

    pagination_type = (resource_config.get("pagination") or {}).get("type")
    items = []
    next_url = url
    pages_fetched = 0
    while next_url and pages_fetched < MAX_RESOURCE_PAGES:
        response = requests.request(
            resource_config.get("method", "GET"),
            next_url,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        items.extend(_extract_items(response.json(), resource_config))
        pages_fetched += 1
        if pagination_type == "link_header":
            next_url = response.links.get("next", {}).get("url")
        else:
            next_url = None
    return items, None


def refresh_access_token(uid, project_key, provider_name):
    """
    Refresh OAuth access token using the stored refresh token.

    Returns (success: bool, access_token: Optional[str], error_message: Optional[str])
    """
    try:
        # Fetch refresh token from Mongo
        success, refresh_token, message = utils.fetch_data_for_key_internal(
            uid, project_key, provider_name + "_refresh_token"
        )
        if not success or not refresh_token:
            utils.logger.error(
                f"Error fetching refresh token for provider '{provider_name}': {message}"
            )
            return False, None, "No refresh capability"

        # Get provider configuration
        try:
            provider = Provider.objects.get(name=provider_name, is_active=True)
        except Provider.DoesNotExist:
            utils.logger.error(
                f"Provider '{provider_name}' not found or inactive while refreshing token"
            )
            return False, None, "No refresh capability"

        if not getattr(provider, "refresh_url", None):
            return False, None, "No refresh capability"

        scopes = provider.default_scopes

        # Create OAuth session using AuthLib
        session = OAuth2Session(
            client_id=provider.client_id,
            client_secret=provider.client_secret,
            scope=scopes,
            token_endpoint_auth_method=(
                provider.token_endpoint_auth_method
                or TokenAuthMethod.CLIENT_SECRET_BASIC
            ),
        )

        try:
            token = session.fetch_token(
                provider.refresh_url,
                grant_type="refresh_token",
                refresh_token=refresh_token,
            )
        except Exception as e:
            utils.logger.error(
                f"Error refreshing access token for provider '{provider_name}': {str(e)}"
            )
            return False, None, str(e)

        new_access_token = token.get("access_token")
        if not new_access_token:
            utils.logger.error(
                f"Refresh response for provider '{provider_name}' did not contain an access_token"
            )
            return False, None, "Failed to refresh access token"

        new_refresh_token = token.get("refresh_token") or refresh_token

        # Determine new expiry
        new_expires_at = token.get("expires_at")
        if new_expires_at is None:
            expires_in = token.get("expires_in")
            if expires_in is not None:
                try:
                    new_expires_at = int(time.time()) + int(expires_in)
                except Exception:
                    new_expires_at = None

        # Persist updated tokens
        store_success = store_in_mongo(
            uid,
            project_key,
            provider_name,
            new_access_token,
            new_refresh_token,
            new_expires_at,
        )
        if not store_success:
            utils.logger.error(
                f"Failed to persist refreshed token for provider '{provider_name}'"
            )
            return False, None, "Failed to persist refreshed token"

        return True, new_access_token, None

    except Exception as e:
        utils.logger.error(
            f"Unexpected error in refresh_access_token for provider '{provider_name}': {str(e)}"
        )
        return False, None, "Internal error during token refresh"


def store_in_mongo(
    uid, project_key, provider_name, access_token, refresh_token, expires_at=None
):
    try:

        status, _ = utils.set_data_for_key_internal(
            uid,
            project_key,
            provider_name + "_access_token",
            access_token,
            "string",
        )
        status2, _ = utils.set_data_for_key_internal(
            uid,
            project_key,
            provider_name + "_refresh_token",
            refresh_token,
            "string",
        )

        status3 = True
        if expires_at is not None:
            # Store token expiry as unix timestamp string
            status3, _ = utils.set_data_for_key_internal(
                uid,
                project_key,
                provider_name + "_token_expires_at",
                str(int(expires_at)),
                "string",
            )

        if not status or not status2 or not status3:
            return False
        return True
    except Exception as e:
        utils.logger.error(f"Error in store_in_mongo: {str(e)}")
        return False


@csrf_exempt
def initiate_oauth(request):
    """POST - Initiate OAuth flow with provider"""
    try:
        success, message, user_object, project_object = (
            validator.validate_user_and_project(request, access_level_gte=READ_GTE)
        )
        if not success:
            return ResponseParser.getParsedErrorMessage(message)

        provider_name = request.POST.get("provider_name", "")
        try:
            provider = Provider.objects.get(name=provider_name, is_active=True)
        except:
            return ResponseParser.getParsedErrorMessage(
                "Provider not found or inactive"
            )
        scopes = provider.default_scopes

        # Create OAuth session using AuthLib
        session = OAuth2Session(
            client_id=provider.client_id,
            client_secret=provider.client_secret,
            scope=scopes,
            redirect_uri=provider.redirect_uri,
            token_endpoint_auth_method=(
                provider.token_endpoint_auth_method or TokenAuthMethod.CLIENT_SECRET_BASIC
            ),
        )

        # Generate state with provider_name, uid, and project_key for security
        state_data = {
            "provider_name": provider_name,
            "uid": user_object.uid,
            "project_key": project_object.project_key,
        }

        ##convert to JWT
        state = jwt.encode(state_data, JWT_SECRET, algorithm="HS256")

        # Generate authorization URL with state and any extra provider-specific params
        extra_auth_params = provider.extra_auth_params or {}
        auth_url, state = session.create_authorization_url(
            provider.auth_url,
            state=state,
            **extra_auth_params,
        )

        return ResponseParser.getParsedSuccessMessage(
            {"auth_url": auth_url},
            "200",
            "OAuth authorization URL generated",
        )

    except Exception as e:
        utils.logger.error(f"Error in initiate_oauth: {str(e)}")
        return ResponseParser.getParsedErrorMessage(f"Error initiating OAuth: {str(e)}")


@csrf_exempt
def oauth_callback(request):
    try:

        state = request.GET.get("state")
        code = request.GET.get("code")

        ##decode state
        state_data = jwt.decode(state, JWT_SECRET, algorithms=["HS256"])
        provider_name = state_data.get("provider_name")
        uid = state_data.get("uid")
        project_key = state_data.get("project_key")

        # Return the user to their own brand's dashboard after OAuth — GitZoid lives on a
        # separate domain (same as the DoDo checkout return). account.product is authoritative.
        _oauth_account = Account.objects.filter(account_uid=uid).first()
        frontend = (
            os.environ.get("GITZOID_FRONTEND_URL", GITZOID_FRONTEND_URL)
            if (_oauth_account and _oauth_account.product == "gitzoid")
            else os.environ.get("FRONTEND_URL", FRONTEND_URL)
        )
        failure_redirect_uri = (
            frontend
            + "/manage/assistant?project_key="
            + project_key
            + "&is_integration_complete=0"
        )

        if not all([provider_name, uid, project_key, code]):
            return redirect(failure_redirect_uri)

        # Validate user
        try:
            user_object = User.objects.get(uid=uid)
        except:
            return redirect(failure_redirect_uri)

        try:
            project_object = Project.objects.get(project_key=project_key)
        except:
            return redirect(failure_redirect_uri)

        if not utils.does_user_have_access_to_project(
            user_object, project_object, access_gte=READ_GTE
        ):
            return redirect(failure_redirect_uri)

        # Get provider configuration
        try:
            provider = Provider.objects.get(name=provider_name, is_active=True)
        except:
            return redirect(failure_redirect_uri)

        # Get scopes from provider defaults
        scopes = provider.default_scopes

        # Create OAuth session using AuthLib
        session = OAuth2Session(
            client_id=provider.client_id,
            client_secret=provider.client_secret,
            scope=scopes,
            redirect_uri=provider.redirect_uri,
            token_endpoint_auth_method=(
                provider.token_endpoint_auth_method or TokenAuthMethod.CLIENT_SECRET_BASIC
            ),
        )

        # Prepare token fetch parameters based on provider configuration
        token_fetch_method = (
            provider.token_fetch_method or TokenFetchMethod.AUTHORIZATION_RESPONSE
        )
        extra_token_params = provider.extra_token_params or {}

        fetch_kwargs = {"state": state, **extra_token_params}

        if token_fetch_method == TokenFetchMethod.CODE:
            fetch_kwargs["code"] = code
            fetch_kwargs.setdefault("redirect_uri", provider.redirect_uri)
        else:
            # Default to using the full authorization response URL
            fetch_kwargs["authorization_response"] = request.build_absolute_uri()

        # Fetch token using AuthLib
        token = session.fetch_token(provider.token_url, **fetch_kwargs)

        access_token = token.get("access_token", "")
        refresh_token = token.get("refresh_token", "")

        # Determine token expiry (unix timestamp)
        expires_at = token.get("expires_at")
        if expires_at is None:
            expires_in = token.get("expires_in")
            if expires_in is not None:
                try:
                    expires_at = int(time.time()) + int(expires_in)
                except Exception:
                    expires_at = None

        # Store in Mongo:
        if not access_token:
            return redirect(failure_redirect_uri)

        success = store_in_mongo(
            uid,
            project_key,
            provider_name,
            access_token,
            refresh_token,
            expires_at,
        )
        if not success:
            return redirect(failure_redirect_uri)

        ##Redirect to dashboard.
        success_redirect_uri = (
            frontend
            + "/manage/assistant?project_key="
            + project_key
            + "&is_integration_complete=1"
        )

        ##Redirect to redirect_uri
        return redirect(success_redirect_uri)

    except Exception as e:
        utils.logger.error(f"Error in oauth_callback: {str(e)}")
        return redirect(failure_redirect_uri)


@csrf_exempt
def fetch_resources(request):
    """POST - Fetch resources from provider"""
    try:
        # Validate user and project access
        success, message, user_object, project_object = (
            validator.validate_user_and_project(request, access_level_gte=READ_GTE)
        )
        if not success:
            return ResponseParser.getParsedErrorMessage(message)

        # Get request parameters
        provider_name = request.POST.get("provider_name", "")
        # Get provider configuration
        try:
            provider = Provider.objects.get(name=provider_name, is_active=True)
        except:
            return ResponseParser.getParsedErrorMessage(
                "Provider not found or inactive"
            )

        # Get stored OAuth data from MongoDB
        access_token_key = f"{provider_name}_access_token"

        success, access_token_data, message = utils.fetch_data_for_key_internal(
            user_object.uid,
            project_object.project_key,
            access_token_key,
            data_run_key=project_object.project_key + "_default",
        )

        if not success or not access_token_data:
            return ResponseParser.getParsedErrorMessage(
                "Error fetching access token: " + str(message)
            )
        single_resource_config_dict = provider.resource_configs
        if not single_resource_config_dict:
            return ResponseParser.getParsedErrorMessage("Resource config not found")

        headers = {"Authorization": f"Bearer {access_token_data}"}

        # Make API request(s) — follows pagination when configured on the provider
        items, error_msg = fetch_provider_items(single_resource_config_dict, headers)
        if error_msg:
            return ResponseParser.getParsedErrorMessage(f"Error fetching resources: {error_msg}")

        # Extract resource information
        resources = []
        id_field = single_resource_config_dict.get("id_field")
        name_field = single_resource_config_dict.get("name_field")
        # Sort/archive metadata for client-side default selection + recent-first ordering.
        # Defaults match GitHub repo fields so it works without a DB resource_configs change.
        sort_field = single_resource_config_dict.get("sort_field", "pushed_at")
        archived_field = single_resource_config_dict.get("archived_field", "archived")
        for item in items:
            resource = {
                "id": get_nested(item, id_field) if id_field else None,
                "name": get_nested(item, name_field) if name_field else None,
                "extra": {},
            }
            # Add other fields as extra data (exclude id/name fields when defined)
            excluded_keys = [k for k in (id_field, name_field) if k is not None]
            for key, value in item.items():
                if key not in excluded_keys:
                    resource["extra"][key] = value
            # Promote sort/archive metadata to top level (kept in extra too for back-compat)
            resource["sort_key"] = get_nested(item, sort_field)
            resource["archived"] = bool(get_nested(item, archived_field, False))
            resources.append(resource)

        # Most-recently-pushed first; None/missing sort_key sorts last. Coerce to str so a provider
        # whose configured sort_field is numeric/bool (not an ISO-8601 timestamp) can never raise a
        # mixed-type comparison and 500 the whole picker. For ISO-8601 UTC strings (GitHub
        # pushed_at/updated_at) lexical order == chronological order; None/falsy -> "" sorts last.
        resources.sort(key=lambda r: str(r.get("sort_key") or ""), reverse=True)

        return ResponseParser.getParsedSuccessMessage(
            {"resources": resources}, "200", "Resources fetched successfully"
        )

    except Exception as e:
        utils.logger.error(f"Error in fetch_resources: {str(e)}")
        return ResponseParser.getParsedErrorMessage(
            f"Error fetching resources: {str(e)}"
        )
