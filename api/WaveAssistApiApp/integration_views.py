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
import WaveAssistApiApp.Utils.validator as validator
import uuid



##ToDo: Write tests
def zerodha_redirect(request):
    mongo_manager = MongoManager()

    request_token = request.GET.get('request_token', '')
    status = request.GET.get('status', '')
    project_key_csv = request.GET.get('project_key_csv', '')
    uid = request.GET.get('uid', '')
    if status != 'success':
        return ResponseParser.getParsedErrorMessage('Something went wrong')

    try:
        user_object = User.objects.get(uid=uid)
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
        if not validator.does_user_have_access_to_project_key(user_object, project_key):
            response_dict[project_key] = "You do not have access to this project"
            continue

        project_integrations_key = project_key + INTEGRATIONS_SUFFIX_KEY
        mongo_manager.collection = mongo_manager.database[project_key]

        zerodha_api_key = ''
        zerodha_api_secret = ''
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

    mongo_manager.close_connection()
    return ResponseParser.getParsedSuccessMessage(response_dict, '200', 'Zerodha access workflow complete')


def upload_file_to_s3(request):
    success, message, user_object, project_object = validator.validate_user_and_project(request, access_level_gte=READ_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)
    is_public = int(request.POST.get('is_public', '0'))
    should_resize = int(request.POST.get('should_resize', '0'))
    max_dimension = int(request.POST.get('max_dimension', '800'))

    try:
        file = request.FILES['file']
        file_name = file.name
    except:
        return ResponseParser.getParsedErrorMessage('File not found')

    if should_resize == 1:
        file = utils.resize_image(file, max_dimension)

    ##Append UUID4 to file name
    file_name = str(uuid.uuid4()) + '_' + file_name

    ##Upload to s3
    s3_file_name = project_object.project_key + '/' + file_name
    success, s3_file_name  = utils.upload_file_to_s3(file, s3_file_name, is_public)
    if not success:
        return ResponseParser.getParsedErrorMessage('File upload failed.')
    output_data = {
        's3_file_path': s3_file_name,
    }
    return ResponseParser.getParsedSuccessMessage(output_data, '200', 'File uploaded successfully.')



## ------- Functions
def manage_integration_details(integration_object, project_object):
    mongo_manager = MongoManager()
    project_key = project_object.project_key
    project_integrations_key = project_key + INTEGRATIONS_SUFFIX_KEY
    mongo_manager.collection = mongo_manager.database[project_key]
    integrations_data_array = mongo_manager.fetch_data_for_key(project_integrations_key)

    if integration_object.name == "Zerodha":
        ##Create a mongo collection for this project

        did_find_api_key = False
        did_find_secret_key = False
        for data_dict in integrations_data_array:
            if data_dict['name'] == ZERODHA_API_KEY:
                did_find_api_key = True
                data_dict['value'] = ZERODHA_API_KEY_VALUE ##ToDo: Should come from dashboard

            if data_dict['name'] == ZERODHA_API_SECRET_KEY:
                did_find_secret_key = True
                data_dict['value'] = ZERODHA_API_SECRET_KEY_VALUE

        if not did_find_api_key:
            zerodha_key_dict = {}
            zerodha_key_dict['name'] = ZERODHA_API_KEY
            zerodha_key_dict['value'] = ZERODHA_API_KEY_VALUE
            integrations_data_array.append(zerodha_key_dict)

        if not did_find_secret_key:
            zerodha_secret_dict = {}
            zerodha_secret_dict['name'] = ZERODHA_API_SECRET_KEY
            zerodha_secret_dict['value'] = ZERODHA_API_SECRET_KEY_VALUE
            integrations_data_array.append(zerodha_secret_dict)



    if integration_object.name == "AWSS3":
        did_find_access_key = False
        did_find_secret = False

        for data_dict in integrations_data_array:
            if data_dict['name'] == AWSS3_ACCESS_KEY:
                did_find_access_key = True
                data_dict['value'] = AWSS3_ACCESS_KEY_VALUE

            if data_dict['name'] == AWSS3_SECRET:
                did_find_secret = True
                data_dict['value'] = AWSS3_SECRET_KEY_VALUE

        if not did_find_access_key:
            access_key_dict = {}
            access_key_dict['name'] = AWSS3_ACCESS_KEY
            access_key_dict['value'] = AWSS3_ACCESS_KEY_VALUE
            integrations_data_array.append(access_key_dict)

        if not did_find_secret:
            secret_dict = {}
            secret_dict['name'] = AWSS3_SECRET
            secret_dict['value'] = AWSS3_SECRET_KEY_VALUE
            integrations_data_array.append(secret_dict)

    mongo_manager.insert_or_replace_data_for_key(project_integrations_key,integrations_data_array)
    mongo_manager.close_connection()
    return
