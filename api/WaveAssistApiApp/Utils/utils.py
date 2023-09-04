##PYTHON IMPORTS
import glob
import struct
import collections
import datetime
from multiprocessing import Queue, Pool
##Custom
from WaveAssistApiApp.Utils.constants import *

from time import sleep
from zipfile import ZipFile

import shutil
import os
import json
from WaveAssistApiApp.Utils.Logger import Logger
##Logger

logger = Logger()

def has_access(client_object, project_key):
    project_list = client_object.project_set.filter(project_key=project_key)
    if project_list.count() > 0:
        return True
    else:
        return False

def does_user_have_node_access(client_object, node_object):
    # project object has node_array
    node_array = client_object.project_set.all().values_list('node_array', flat=True)
    return node_object.id in node_array

def does_user_have_io_data_access(client_object, io_data_object):
    # project object has node_array
    project_array = client_object.project_set.all()
    return io_data_object.project in project_array


def manage_integration_details(mongo_manager, integration_object, project_object):
    project_key = project_object.project_key

    if integration_object.name == "Zerodha":
        ##Create a mongo collection for this project
        project_integrations_key = project_key + INTEGRATIONS_SUFFIX_KEY
        mongo_manager.collection = mongo_manager.database[project_key]

        integrations_data_array = []


        zerodha_key_dict = {}
        zerodha_key_dict['name'] = ZERODHA_API_KEY
        zerodha_key_dict['value'] = ZERODHA_API_KEY_VALUE
        integrations_data_array.append(zerodha_key_dict)

        zerodha_secret_dict = {}
        zerodha_secret_dict['name'] = ZERODHA_API_SECRET_KEY
        zerodha_secret_dict['value'] = ZERODHA_API_SECRET_KEY_VALUE
        integrations_data_array.append(zerodha_secret_dict)

        mongo_manager.insert_or_replace_data_for_key(project_integrations_key,integrations_data_array)

    return