import json
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


def store_in_mongo(uid, project_key, provider_name, access_token, refresh_token):
    try:

        status, _ = utils.set_data_for_key_internal(
            uid, project_key, provider_name + "_access_token", access_token, "string"
        )
        status2, _ = utils.set_data_for_key_internal(
            uid, project_key, provider_name + "_refresh_token", refresh_token, "string"
        )
        if not status or not status2:
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
        failure_redirect_uri = (
            FRONTEND_URL
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

        ##Store in Mongo:
        if not access_token:
            return redirect(failure_redirect_uri)

        success = store_in_mongo(
            uid, project_key, provider_name, access_token, refresh_token
        )
        if not success:
            return redirect(failure_redirect_uri)

        ##Redirect to dashboard.
        success_redirect_uri = (
            FRONTEND_URL
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

        url = single_resource_config_dict.get("endpoint", "")
        headers = {"Authorization": f"Bearer {access_token_data}"}

        # Make API request
        response = requests.request(
            single_resource_config_dict.get("method", "GET"),
            url,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        items_data = response.json()

        # Extract list of items via items_key or default "data"; always normalize to list
        items_key = single_resource_config_dict.get("items_key")
        if items_key:
            items = get_nested(items_data, items_key, [])
        else:
            items = (
                items_data
                if isinstance(items_data, list)
                else get_nested(items_data, "data", [])
            )
        if not isinstance(items, list):
            items = []

        # Extract resource information
        resources = []
        id_field = single_resource_config_dict.get("id_field")
        name_field = single_resource_config_dict.get("name_field")
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
            resources.append(resource)
        return ResponseParser.getParsedSuccessMessage(
            {"resources": resources}, "200", "Resources fetched successfully"
        )

    except Exception as e:
        utils.logger.error(f"Error in fetch_resources: {str(e)}")
        return ResponseParser.getParsedErrorMessage(
            f"Error fetching resources: {str(e)}"
        )
