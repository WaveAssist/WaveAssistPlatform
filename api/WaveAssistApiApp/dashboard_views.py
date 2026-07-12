from .models import *
from .Utils.responseParser import ResponseParser
from WaveAssistApiApp.Utils.MongoManager import MongoManager
from .Utils.constants import *
from .Utils.utils import get_repo_parts_from_url
from .Utils.projectSetup import get_config_yaml_from_github, validate_yaml_config
from django.core.cache import cache
import WaveAssistApiApp.Utils.utils as utils
from WaveAssistApiApp.Utils.utils import fetch_credits_from_openrouter
import requests
from firebase_admin import auth as firebase_auth
from .firebase_init import initialize_firebase

initialize_firebase()

mongo_manager = MongoManager()


def index(request):
    return ResponseParser.getParsedSuccessMessage(
        [], "S01", "Hello, world. You're at the WaveAssist index..."
    )


def login(request):  ##TCW
    firebase_token = request.POST.get("firebase_token", "")
    try:
        firebase_uid, _ = get_firebase_uid(firebase_token)
    except Exception as e:
        return ResponseParser.getParsedErrorMessage(f"Failed to login: {str(e)}")
    try:
        user_object = User.objects.get(firebase_uid=firebase_uid)
    except:
        return ResponseParser.getParsedSuccessMessage(
            GET_STARTED_DATA, "S02", "User not found"
        )

    should_get_started = False
    try:
        account_object = Account.objects.get(created_by_user=user_object)
        ##check if account_object has everything.
        if account_object.mongo_db_url == "":
            should_get_started = True
        if account_object.celery_queue == "":
            should_get_started = True
        # Ensure every account has an MCP token — login is the reliable touchpoint since
        # get_started runs only on first setup.
        account_object.ensure_mcp_token()
    except:
        should_get_started = True
    if should_get_started:
        return ResponseParser.getParsedSuccessMessage(
            GET_STARTED_DATA, "S02", "User not found"
        )

    ##Fetch all projects of the User from AccessProvided
    project_array = Project.objects.filter(
        accessprovided__type=0,
        accessprovided__project_access_type__gte=READ_GTE,
        accessprovided__user_object=user_object,
    ).distinct()

    project_dict_array = []
    for project_object in project_array:
        project_dict = project_object.get_dict()
        data_run_array = DataRuns.objects.filter(
            accessprovided__type=1,
            accessprovided__data_run_access_type__gte=READ_GTE,
            accessprovided__user_object=user_object,
            project_object=project_object,
        ).distinct()

        data_run_dict_array = []
        for data_run_object in data_run_array:
            data_run_dict_array.append(data_run_object.get_dict())
        project_dict["data_run_array"] = data_run_dict_array
        project_dict_array.append(project_dict)

    output_dictionary = {"project_array": project_dict_array}
    user_data = user_object.get_dict()
    user_data["mongo_db_url"] = account_object.mongo_db_url
    output_dictionary["user_data"] = user_data

    ##CLI Handling.
    handle_cli_session(request, user_data)

    ##Track PostHog event
    utils.track_posthog(
        uid=str(user_object.uid),
        event="user_login",
        props={
            "user_id": str(user_object.uid),
            "email": user_object.username,
            "name": user_object.name,
        },
    )

    return ResponseParser.getParsedSuccessMessage(
        output_dictionary, "200", "Login successful."
    )


def fetch_openrouter_credits(request, uid):
    try:
        user_object = User.objects.get(uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage("User not found.")

    try:
        account_object = Account.objects.get(created_by_user=user_object)
        open_router_key = account_object.open_router_key
    except Exception:
        return ResponseParser.getParsedErrorMessage("Account not found.")

    if not open_router_key:
        return ResponseParser.getParsedErrorMessage("OpenRouter key not found.")

    try:
        credit_data = fetch_credits_from_openrouter(open_router_key)
    except requests.exceptions.RequestException as e:
        print(f"Network error fetching OpenRouter credits: {str(e)}")
        return ResponseParser.getParsedErrorMessage(f"Network error: {str(e)}")
    except Exception as e:
        print(f"Error fetching OpenRouter credits: {str(e)}")
        return ResponseParser.getParsedErrorMessage(f"Error fetching credits: {str(e)}")

    m = WAVEASSIST_CREDIT_MULTIPLIER

    # limit / limit_remaining are None for uncapped (unlimited) OpenRouter keys.
    def _wa(value):
        return round(value * m, 2) if value is not None else None

    wa_credits = {
        "limit": _wa(credit_data["limit"]),
        "usage": _wa(credit_data["usage"]),
        "limit_remaining": _wa(credit_data["limit_remaining"]),
    }

    return ResponseParser.getParsedSuccessMessage(
        wa_credits, "200", "Credits fetched successfully."
    )


def handle_cli_session(request, user_data):
    try:
        session_id = request.POST.get("session_id", "")
        if session_id:
            uid = str(user_data.get("uid", ""))
            cache.set(f"cli_login_session:{session_id}", uid, timeout=300)
    except Exception as e:
        print("Error handling CLI session:" + str(e))
    return


# Firebase's public signing certs are shared and rotate slowly. Cache them (honoring Google's
# Cache-Control) via a module-level cachecontrol session, so GitZoid token verification doesn't
# re-fetch certs on every login — the same caching firebase_admin does for the default app.
import cachecontrol as _cachecontrol
import requests as _requests_lib
from google.auth.transport import requests as _google_transport
from google.oauth2 import id_token as _google_id_token

_firebase_cert_request = _google_transport.Request(session=_cachecontrol.CacheControl(_requests_lib.session()))


def get_firebase_uid(firebase_token):
    if not firebase_token:
        raise Exception("Firebase token not found")

    # A brand's token is issued by that brand's Firebase project, so we try each brand's verifier.
    last_error = None

    # WaveAssist — the default firebase_admin app (its service account), exactly as before.
    try:
        decoded_token = firebase_auth.verify_id_token(firebase_token)
        firebase_uid = decoded_token.get("uid")
        if firebase_uid:
            return firebase_uid, decoded_token
    except Exception as e:
        last_error = e

    # GitZoid — verified against its project id using Google's public certs (no service-account
    # key needed). A WaveAssist token won't match here (different project), so this runs only for
    # genuine GitZoid tokens.
    try:
        decoded_token = _google_id_token.verify_firebase_token(
            firebase_token, _firebase_cert_request, audience=GITZOID_FIREBASE_PROJECT_ID
        )
        if decoded_token:
            firebase_uid = decoded_token.get("user_id") or decoded_token.get("sub")
            if firebase_uid:
                return firebase_uid, decoded_token
    except Exception as e:
        last_error = e

    raise Exception(f"Failed to verify Firebase token: {last_error}")


def cli_login_status(request, session_id):
    data = cache.get(f"cli_login_session:{session_id}")
    if data:
        return ResponseParser.getParsedSuccessMessage(
            data, 200, "CLI login status success"
        )
    return ResponseParser.getParsedErrorMessage("Not yet authenticated", 404)


def fetch_assistant(request, assistant_key):
    try:
        # Resolve the source repo URL. Two cases:
        #   - Curated assistant: assistant_key matches an Assistants row.
        #     Public — no auth (curated catalog is browsable).
        #   - WaveMaker-built project: assistant_key is the Project.project_key.
        #     Auth-gated — caller must be a user with READ access on the project,
        #     because Project.github_url + variable names are user-private.
        assistant = None
        project = None
        repo_url = ""
        try:
            assistant = Assistants.objects.get(assistant_key=assistant_key)
            repo_url = assistant.github_url or ""
        except Assistants.DoesNotExist:
            try:
                project = Project.objects.get(project_key=assistant_key)
                repo_url = project.github_url or ""
            except Project.DoesNotExist:
                pass

        if not repo_url:
            return ResponseParser.getParsedErrorMessage("Assistant not found.", 404)

        # Auth gate for the WaveMaker (Project) branch only.
        if project is not None:
            uid = (utils.get_param(request, "uid", "") or "").strip()
            if not uid:
                return ResponseParser.getParsedErrorMessage("Missing uid", 401)
            try:
                user_object = User.objects.get(uid=uid)
            except User.DoesNotExist:
                return ResponseParser.getParsedErrorMessage("User not found", 401)
            if not utils.does_user_have_access_to_project(user_object, project, access_gte=READ_GTE):
                return ResponseParser.getParsedErrorMessage("Not authorized for this project", 403)

        owner, repo_name = get_repo_parts_from_url(repo_url)
        yaml_config = get_config_yaml_from_github(repo_name, owner)
        is_valid, message = validate_yaml_config(yaml_config)

        if not is_valid:
            return ResponseParser.getParsedErrorMessage(
                "Error with yaml: " + str(message)
            )
        variables = yaml_config.get("variables", [])
        success_message = yaml_config.get(
            "success_message",
            "Your agent was triggered and will also run on a schedule.",
        )
        ##Show optional variables
        optional_variables = [
            v for v in variables if v.get("is_optional", True) == True
        ]
        variables = [v for v in variables if v.get("is_optional", True) == False]

        # Build the response dict from whichever source we resolved.
        if assistant is not None:
            assistant_dict = assistant.get_dict()
        else:
            # WaveMaker-built project: synthesise the same shape from the Project
            # + yaml_config so the dashboard renders identically.
            assistant_dict = {
                "id": project.id,
                "name": project.name or yaml_config.get("name", ""),
                "assistant_key": project.project_key,
                "github_url": project.github_url or "",
                "credits_needed_per_unit": 0.0,
            }
        assistant_dict["input_array"] = variables
        assistant_dict["optional_input_array"] = optional_variables
        assistant_dict["success_message"] = success_message
        assistant_dict["output_default_message"] = yaml_config.get(
            "output_default_message", ""
        )
        assistant_dict["configuration_helper_message"] = yaml_config.get(
            "configuration_helper_message", ""
        )
        return ResponseParser.getParsedSuccessMessage(
            assistant_dict, "200", "Assistant found successfully."
        )
    except Exception as e:
        return ResponseParser.getParsedErrorMessage(
            f"Error fetching assistant: {str(e)}", 500
        )
