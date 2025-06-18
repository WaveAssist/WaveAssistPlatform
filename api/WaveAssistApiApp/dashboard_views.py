from .models import *
from .Utils.responseParser import ResponseParser
from WaveAssistApiApp.Utils.MongoManager import MongoManager
from .Utils.constants import *
from django.core.cache import cache
import WaveAssistApiApp.Utils.utils as utils
import requests
from firebase_admin import auth as firebase_auth
from .firebase_init import initialize_firebase
initialize_firebase()

mongo_manager = MongoManager()

def index(request):
    return ResponseParser.getParsedSuccessMessage([],"S01","Hello, world. You're at the WaveAssist index...")

def login(request): ##TCW
    firebase_token = request.POST.get('firebase_token', '')
    try:
        firebase_uid, _ = get_firebase_uid(firebase_token)
    except Exception as e:
        return ResponseParser.getParsedErrorMessage(f'Failed to login: {str(e)}')
    try:
        user_object = User.objects.get(firebase_uid=firebase_uid)
    except:
        return ResponseParser.getParsedSuccessMessage(GET_STARTED_DATA, 'S02', 'User not found')

    should_get_started = False
    try:
        account_object = Account.objects.get(created_by_user=user_object)
        ##check if account_object has everything.
        if account_object.mongo_db_url == '':
            should_get_started = True
        if account_object.worker_service_arn == '':
            should_get_started = True
    except:
        should_get_started = True
    if should_get_started:
        return ResponseParser.getParsedSuccessMessage(GET_STARTED_DATA, 'S02', 'User not found')


    ##Fetch all projects of the User from AccessProvided
    project_array = Project.objects.filter(
        accessprovided__type=0,
        accessprovided__project_access_type__gte=READ_GTE,
        accessprovided__user_object=user_object
    ).distinct()

    project_dict_array = []
    for project_object in project_array:
        project_dict = project_object.get_dict()
        data_run_array = DataRuns.objects.filter(
            accessprovided__type=1,
            accessprovided__data_run_access_type__gte=READ_GTE,
            accessprovided__user_object=user_object,
            project_object=project_object
        ).distinct()

        data_run_dict_array = []
        for data_run_object in data_run_array:
            data_run_dict_array.append(data_run_object.get_dict())
        project_dict['data_run_array'] = data_run_dict_array
        project_dict_array.append(project_dict)

    output_dictionary = {'project_array': project_dict_array}
    user_data = user_object.get_dict()
    user_data['mongo_db_url'] = account_object.mongo_db_url
    output_dictionary['user_data'] = user_data


    ##CLI Handling.
    handle_cli_session(request,user_data)

    ##Account run handling
    if not account_object.is_working_running:
        utils.run_knock_workflow(str(user_object.uid), 'restart')

    return ResponseParser.getParsedSuccessMessage(output_dictionary, '200', 'Login successful.')




def handle_cli_session(request, user_data):
    try:
        session_id = request.POST.get('session_id', '')
        if session_id:
            uid = str(user_data.get('uid', ''))
            cache.set(f"cli_login_session:{session_id}", uid, timeout=300)
    except Exception as e:
        print("Error handling CLI session:" + str(e))
    return


def get_firebase_uid(firebase_token):
    if not firebase_token:
        raise Exception('Firebase token not found')

    # Verify the Firebase token
    try:
        decoded_token = firebase_auth.verify_id_token(firebase_token)
    except Exception as e:
        raise Exception(f'Failed to verify Firebase token: {str(e)}')

    firebase_uid = decoded_token.get('uid')
    if not firebase_uid:
        raise Exception('Firebase UID not found in the decoded token')
    return firebase_uid, decoded_token


def cli_login_status(request, session_id):
    data = cache.get(f"cli_login_session:{session_id}")
    if data:
        return ResponseParser.getParsedSuccessMessage(data,200, "CLI login status success")
    return ResponseParser.getParsedErrorMessage("Not yet authenticated", 404)
