import json

from django.shortcuts import render
from .models import *
from .Utils.responseParser import ResponseParser
from WaveAssistApiApp.Utils.MongoManager import MongoManager
# Create your views here.
import pandas as pd
from io import StringIO as StringIO
from .Utils.constants import *
from .Utils.firebase_auth import verify_token
from kiteconnect import KiteConnect
import WaveAssistApiApp.Utils.utils as utils

mongo_manager = MongoManager()


def index(request):
    return ResponseParser.getParsedSuccessMessage([],"S01","Hello, world. You're at the WaveAssist index...")


def login(request):
    jwt_token = request.POST.get('jwt_token', '')
    uid = verify_token(jwt_token)
    print(uid)
    if uid == None:
        return ResponseParser.getParsedErrorMessage('Invalid token')

    try:
        client_object = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')

    ##Fetch all projects of the client, where project's client_array contains client

    project_array = client_object.project_set.filter(running_status=1)

    project_dict_array = []
    for project_object in project_array:
        project_dict_array.append(project_object.get_dict())
    output_dictionary = {'project_array': project_dict_array}
    output_dictionary['client_data'] = client_object.get_dict()
    return ResponseParser.getParsedSuccessMessage(output_dictionary, '200', 'Login successful.')


## API to get formatted data of the project
def load_project_data(request):
    uid = request.POST.get('uid', '')
    try:
        client_object = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')

    try:
        project_key = request.POST.get('project_key', '')
        project_object = Project.objects.get(project_key=project_key)
        mongo_manager.collection = mongo_manager.database[project_object.project_key]
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Project not found.')


    try:
        ##Load IOData with type as 1 and project_key as project_key
        io_data_array = IOData.objects.filter(project__project_key=project_key, output_type__in=[1,2])
        ##Fetch all IO Data from Mongo

        data_dict = {}
        data_format_array = []
        for io_data_object in io_data_array:
            data_array = mongo_manager.fetch_data_for_key(io_data_object.key)
            data_array = MongoManager.add_row_number(data_array)
            data_array = MongoManager.manage_na(data_array)
            if io_data_object.output_type == 2:
                ##Sort data array's by row key in dict and then column key
                data_array = sorted(data_array, key=lambda k: (k['Row'], k['Column']))
                data_format_array = data_array
            data_dict[io_data_object.key] = data_array

        output_dict = {'data_dict': data_dict, 'data_format_array': data_format_array}
        return ResponseParser.getParsedSuccessMessage(output_dict, '200', 'Project data loaded successfully.')
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Something went wrong with data loading: ' + str(e))



def set_data_for_key(request):
    uid = request.POST.get('uid', '')
    try:
        client_object = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')

    io_data_key = request.POST.get('io_data_key', '')
    try:
        io_data_object = IOData.objects.get(key=io_data_key)
        project_key = io_data_object.project.project_key
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('IOData not found!')

    if not utils.has_access(client_object, project_key):
        return ResponseParser.getParsedErrorMessage('You do not have access to this project')

    data_type = request.POST.get('data_type', 'csv')
    if data_type == 'csv':
        csv_data = str(request.POST.get('csv_data', ''))
        pd_data = pd.read_csv(StringIO(csv_data))
    if data_type == 'json':
        json_data = str(request.POST.get('json_data', ''))
        pd_data = pd.read_json(json_data)
    try:
        ##Save in mongo db
        mongo_manager.collection = mongo_manager.database[project_key]

        ##Remove row_number column in pd_data if it exists
        pd_data = pd_data.drop('row_number', axis=1, errors='ignore')

        success = mongo_manager.replace_data_as_dataframe(io_data_key, pd_data)
        if not success:
            return ResponseParser.getParsedErrorMessage('Something went wrong with data saving')
        ##Response
        output_dictionary = {'io_data_key': io_data_key}
        return ResponseParser.getParsedSuccessMessage(output_dictionary, '200',
                                                        'Data saved successfully.')
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Something went wrong with data saving: ' + str(e))



def zerodha_redirect(request):
    request_token = request.GET.get('request_token', '')
    status = request.GET.get('status', '')
    project_key_csv = request.GET.get('project_key_csv', '')
    uid = request.GET.get('uid', '')

    if status != 'success':
        return ResponseParser.getParsedErrorMessage('Something went wrong')

    try:
        client_object = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')


    ##Convert csv to array
    project_key_array = project_key_csv.split(',')
    response_dict = {}
    is_access_token_created = False
    set_access_token = ""

    for project_key in project_key_array:
        if project_key == "" or project_key == " ":
            continue

        if not utils.has_access(client_object, project_key):
            response_dict[project_key] = "You do not have access to this project"
            continue

        project_integrations_key = project_key + INTEGRATIONS_SUFFIX_KEY
        mongo_manager.collection = mongo_manager.database[project_key]

        zerodha_api_key = ''
        zerodha_api_secret = ''
        integrations_data_array = []
        try:
            integrations_data_array = mongo_manager.fetch_data_for_key(project_integrations_key)
            for data_dict in integrations_data_array:
                if data_dict['name'] == ZERODHA_API_KEY:
                    zerodha_api_key = data_dict['value']
                elif data_dict['name'] == ZERODHA_API_SECRET_KEY:
                    zerodha_api_secret = data_dict['value']
        except:
            response_dict[project_key] = "Integrations data not found for this project"
            continue

        try:
            if not is_access_token_created:
                kite = KiteConnect(api_key=zerodha_api_key)
                data = kite.generate_session(request_token, api_secret=zerodha_api_secret)
                access_token = data["access_token"]
                set_access_token = access_token
                is_access_token_created = True
            else:
                access_token = set_access_token
        except Exception as e:
            response_dict[project_key] = "Something went wrong setting token: " + str(e)
            continue


        ##Save access token in mongo
        did_find = False
        for data_dict in integrations_data_array:
            if data_dict['name'] == ZERODHA_ACCESS_TOKEN_KEY:
                data_dict['value'] = access_token
                did_find = True
                break

        if not did_find:
            access_data_dict = {}
            access_data_dict['name'] = ZERODHA_ACCESS_TOKEN_KEY
            access_data_dict['value'] = access_token
            integrations_data_array.append(access_data_dict)

        success = mongo_manager.insert_or_replace_data_for_key(project_integrations_key,integrations_data_array)
        if not success:
            response_dict[project_key] = 'Something went wrong with data saving for this project'
            continue
        else:
            response_dict[project_key] = "Zerodha token successfully set!"


    return ResponseParser.getParsedSuccessMessage(response_dict, '200', 'Zerodha access workflow complete')


