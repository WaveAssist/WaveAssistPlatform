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
from WaveAssistApi.celery import app
from celery import chain, group
from kombu.serialization import dumps
from django_celery_beat.models import PeriodicTask, IntervalSchedule
import datetime
from django.contrib.auth.hashers import check_password


mongo_manager = MongoManager()

def index(request):
    return ResponseParser.getParsedSuccessMessage([],"S01","Hello, world. You're at the WaveAssist index...")

def login(request): ##TCW
    username = request.POST.get('username')
    password = request.POST.get('password')
    try:
        user_object = User.objects.get(username=username)
        if not check_password(password, user_object.password):
            raise Exception('Invalid Password')
    except:
        return ResponseParser.getParsedErrorMessage('Username or Password invalid.')

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
    output_dictionary['user_data'] = user_object.get_dict()

    return ResponseParser.getParsedSuccessMessage(output_dictionary, '200', 'Login successful.')

##ToDo: Write tests
def fetch_data_for_data_run(request):
    ##Validate Request
    success, message, user_object , data_run_object = validator.validate_user_and_data_run(request, READ_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)
    data_run_key = data_run_object.data_run_key

    ##Get data for project
    output_dict = {}
    ##Dashboard Sections
    dashboard_section_array = data_run_object.project_object.dashboardsection_set.all().order_by('row', 'column')
    dashboard_section_dict_array = []
    data_keys_array = []
    for dashboard_section_object in dashboard_section_array:
        dashboard_section_dict = dashboard_section_object.get_dict()
        data_key = dashboard_section_object.data_key_object.key
        data_keys_array.append(data_key)
        dashboard_section_dict_array.append(dashboard_section_dict)
    output_dict['dashboard_section_array'] = dashboard_section_dict_array

    ##Fetch data for data keys
    mongo_manager.collection = mongo_manager.database[data_run_key]
    data_dict = mongo_manager.fetch_data_for_keys_array(data_keys_array)
    data_dict = MongoManager.manage_dict_formatting(data_dict)
    output_dict['data_dict'] = data_dict

    return ResponseParser.getParsedSuccessMessage(output_dict, '200', 'Project data fetched successfully.')

