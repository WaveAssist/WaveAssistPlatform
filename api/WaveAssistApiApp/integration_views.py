import json

from django.shortcuts import render
from .models import *
from .Utils.responseParser import ResponseParser
from WaveAssistApiApp.Utils.MongoManager import MongoManager
# Create your views here.
import pandas as pd
from io import StringIO as StringIO
from .Utils.constants import *
import WaveAssistApiApp.Utils.utils as utils
import WaveAssistApiApp.Utils.validator as validator
import uuid


## ------- Functions
def manage_integration_details(integration_object, project_object):
    return
    # mongo_manager = MongoManager()
    # project_key = project_object.project_key
    # project_integrations_key = project_key + INTEGRATIONS_SUFFIX_KEY
    # mongo_manager.collection = mongo_manager.database[project_key]
    # integrations_data_array = mongo_manager.fetch_data_for_key(project_integrations_key)
    #
    # if integration_object.name == "Zerodha":
    #     ##Create a mongo collection for this project
    #
    #     did_find_api_key = False
    #     did_find_secret_key = False
    #     for data_dict in integrations_data_array:
    #         if data_dict['name'] == ZERODHA_API_KEY:
    #             did_find_api_key = True
    #             data_dict['value'] = ZERODHA_API_KEY_VALUE
    #
    #         if data_dict['name'] == ZERODHA_API_SECRET_KEY:
    #             did_find_secret_key = True
    #             data_dict['value'] = ZERODHA_API_SECRET_KEY_VALUE
    #
    #     if not did_find_api_key:
    #         zerodha_key_dict = {}
    #         zerodha_key_dict['name'] = ZERODHA_API_KEY
    #         zerodha_key_dict['value'] = ZERODHA_API_KEY_VALUE
    #         integrations_data_array.append(zerodha_key_dict)
    #
    #     if not did_find_secret_key:
    #         zerodha_secret_dict = {}
    #         zerodha_secret_dict['name'] = ZERODHA_API_SECRET_KEY
    #         zerodha_secret_dict['value'] = ZERODHA_API_SECRET_KEY_VALUE
    #         integrations_data_array.append(zerodha_secret_dict)
    #
    #
    #
    # if integration_object.name == "AWSS3":
    #     did_find_access_key = False
    #     did_find_secret = False
    #
    #     for data_dict in integrations_data_array:
    #         if data_dict['name'] == AWSS3_ACCESS_KEY:
    #             did_find_access_key = True
    #             data_dict['value'] = AWSS3_ACCESS_KEY_VALUE
    #
    #         if data_dict['name'] == AWSS3_SECRET:
    #             did_find_secret = True
    #             data_dict['value'] = AWSS3_SECRET_KEY_VALUE
    #
    #     if not did_find_access_key:
    #         access_key_dict = {}
    #         access_key_dict['name'] = AWSS3_ACCESS_KEY
    #         access_key_dict['value'] = AWSS3_ACCESS_KEY_VALUE
    #         integrations_data_array.append(access_key_dict)
    #
    #     if not did_find_secret:
    #         secret_dict = {}
    #         secret_dict['name'] = AWSS3_SECRET
    #         secret_dict['value'] = AWSS3_SECRET_KEY_VALUE
    #         integrations_data_array.append(secret_dict)
    #
    # mongo_manager.insert_or_replace_data_for_key(project_integrations_key,integrations_data_array)
    # mongo_manager.close_connection()
    # return



def get_integrations_data(project_key, user_object):
    mongo_manager = MongoManager()
    db_name = utils.get_database_name(user_object)
    mongo_manager.database = mongo_manager.client[db_name]
    mongo_manager.collection = mongo_manager.database[project_key]
    project_integrations_key = project_key + INTEGRATIONS_SUFFIX_KEY
    integration_dict = mongo_manager.fetch_data_for_key(project_integrations_key)
    return integration_dict
