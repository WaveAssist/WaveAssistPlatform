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

    ##Track PostHog event
    utils.track_posthog(
        uid=str(user_object.uid),
        event='user_login',
        props={
            'user_id': str(user_object.uid),
            'username': user_object.username,
            'company_name': user_object.company_name,
        }
    )

    return ResponseParser.getParsedSuccessMessage(output_dictionary, '200', 'Login successful.')


def fetch_openrouter_credits(request, uid):
    try:
        user_object = User.objects.get(uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found.')

    try:
        account_object = Account.objects.get(created_by_user=user_object)
        open_router_key = account_object.open_router_key
    except:
        return ResponseParser.getParsedErrorMessage('Account not found.')

    credit_data = {
        'limit': 0,
        'usage': 0,
        'limit_remaining': 0,
    }
    
    if open_router_key:
        try:
            # Fetch credits from OpenRouter
            headers = {
                "Authorization": f"Bearer {open_router_key}",
                "Content-Type": "application/json",
            }
            
            # Get credits information
            credits_url = "https://openrouter.ai/api/v1/key"
            credits_response = requests.get(credits_url, headers=headers, timeout=10)
            if credits_response.status_code == 200:
                credits_info = credits_response.json()
                data = credits_info.get('data', {})
                credit_data['limit'] = data.get('limit', 0)
                credit_data['usage'] = data.get('usage', 0)
                credit_data['limit_remaining'] = data.get('limit_remaining', 0)
            else:
                print(f"OpenRouter credits API returned status {credits_response.status_code}")
            
        except requests.exceptions.RequestException as e:
            print(f"Network error fetching OpenRouter credits: {str(e)}")
            return ResponseParser.getParsedErrorMessage(f'Network error: {str(e)}')
        except Exception as e:
            print(f"Error fetching OpenRouter credits: {str(e)}")
            return ResponseParser.getParsedErrorMessage(f'Error fetching credits: {str(e)}')
    else:
        return ResponseParser.getParsedErrorMessage('OpenRouter key not found.')
    
    return ResponseParser.getParsedSuccessMessage(credit_data, '200', 'OpenRouter credits fetched successfully.')



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


def fetch_assistant(request, assistant_key):
    try:
        assistant = Assistants.objects.get(assistant_key=assistant_key)
        return ResponseParser.getParsedSuccessMessage(assistant.get_dict(), '200', 'Assistant found successfully.')
    except Assistants.DoesNotExist:
        return ResponseParser.getParsedErrorMessage('Assistant not found.', 404)
    except Exception as e:
        return ResponseParser.getParsedErrorMessage(f'Error fetching assistant: {str(e)}', 500)
