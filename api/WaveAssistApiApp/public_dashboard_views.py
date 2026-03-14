from django.http import HttpResponse, HttpResponseNotFound
from django.views.decorators.http import require_GET, require_POST

from .Utils.responseParser import ResponseParser
from .Utils.constants import READ_GTE
from WaveAssistApiApp.Utils.MongoManager import MongoManager, DashboardTokenManager
from WaveAssistApiApp.Utils.utils import get_param, get_database_name
from .models import User
import WaveAssistApiApp.Utils.validator as validator

dashboard_token_manager = DashboardTokenManager()
mongo_manager = MongoManager()


@require_POST
def generate_dashboard_link(request):
    """Authenticated endpoint — creates a token for a stored HTML dashboard."""
    success, message, user_object, _ = validator.validate_user_and_data_run(request, READ_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    uid = str(user_object.uid)
    project_key = get_param(request, 'project_key', '')
    environment_key = get_param(request, 'data_run_key', None) or get_param(request, 'environment_key', None)
    data_key = get_param(request, 'data_key', '')

    if not data_key:
        return ResponseParser.getParsedErrorMessage("Missing 'data_key' in request.")

    run_based = str(get_param(request, 'run_based', '0'))
    run_id = get_param(request, 'run_id', None)
    if run_based == '1' and run_id:
        data_key = f"{data_key}_{run_id}"

    token = dashboard_token_manager.create_token(uid, project_key, environment_key, data_key)

    return ResponseParser.getParsedSuccessMessage(
        {"token": token},
        "200",
        "Dashboard link created successfully.",
    )


@require_GET
def view_dashboard(request, token):
    """Public endpoint — serves stored HTML for a valid token."""
    token_doc = dashboard_token_manager.get_token(token)
    if not token_doc:
        return HttpResponseNotFound("Dashboard not found.")

    try:
        user_object = User.objects.get(uid=token_doc["uid"])
    except User.DoesNotExist:
        return HttpResponseNotFound("Dashboard not found.")

    db_name = get_database_name(user_object)
    mongo_manager.database = mongo_manager.client[db_name]
    mongo_manager.collection = mongo_manager.database[token_doc["environment_key"]]

    html_data, _ = mongo_manager.fetch_data_for_key(token_doc["data_key"])
    if html_data is None:
        return HttpResponseNotFound("Dashboard content not found.")

    return HttpResponse(html_data, content_type="text/html")
