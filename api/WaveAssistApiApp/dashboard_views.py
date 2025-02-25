import json

from django.shortcuts import render
from .models import *
from .Utils.responseParser import ResponseParser
from WaveAssistApiApp.Utils.MongoManager import MongoManager
# Create your views here.
import pandas as pd
from io import StringIO as StringIO
from .Utils.constants import *
from WaveAssistApi.celery import app
from celery import chain, group
from kombu.serialization import dumps
from django_celery_beat.models import PeriodicTask, IntervalSchedule
import datetime
from django.contrib.auth.hashers import check_password


import requests
requests.get('https://www.googleapis.com', verify=False)

from firebase_admin import auth as firebase_auth
from .firebase_init import initialize_firebase
initialize_firebase()

mongo_manager = MongoManager()

def index(request):
    return ResponseParser.getParsedSuccessMessage([],"S01","Hello, world. You're at the WaveAssist index...")

def login(request): ##TCW
    firebase_token = request.POST.get('firebase_token', '')
    firebase_uid, _ = get_firebase_uid(firebase_token)
    try:
        user_object = User.objects.get(firebase_uid=firebase_uid)
    except:
        data = {
            'action': 'PERFORM_GET_STARTED'
        }
        return ResponseParser.getParsedSuccessMessage(data, 'S02', 'User not found')

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


def get_firebase_uid(firebase_token):
    if not firebase_token:
        return ResponseParser.getParsedErrorMessage('Firebase token not provided')

    # Verify the Firebase token
    try:
        decoded_token = firebase_auth.verify_id_token(firebase_token)
        print('That')
    except Exception as e:
        return ResponseParser.getParsedErrorMessage(f'Firebase token verification failed: {str(e)}')

    firebase_uid = decoded_token.get('uid')
    print(firebase_uid)
    if not firebase_uid:
        return ResponseParser.getParsedErrorMessage('Firebase UID not found in token')

    return firebase_uid, decoded_token

def firebase_login(request):
    try:
        # Parse the request body
        firebase_token = request.POST.get('firebase_token')

        firebase_uid, _ = get_firebase_uid(firebase_token)
        # Fetch the user object
        try:
            user_object = User.objects.get(firebase_uid=firebase_uid)
        except:
            return ResponseParser.getParsedErrorMessage('User not found')

        # Fetch projects and data runs for the user
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

            data_run_dict_array = [data_run_object.get_dict() for data_run_object in data_run_array]
            project_dict['data_run_array'] = data_run_dict_array
            project_dict_array.append(project_dict)

        output_dictionary = {
            'project_array': project_dict_array,
            'user_data': user_object.get_dict()
        }

        return ResponseParser.getParsedSuccessMessage(output_dictionary, '200', 'Login successful.')

    except Exception as e:
        return ResponseParser.getParsedErrorMessage(f'Failed to login: {str(e)}')

