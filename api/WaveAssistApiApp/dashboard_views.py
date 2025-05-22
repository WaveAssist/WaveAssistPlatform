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
from django.core.cache import cache


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
    return ResponseParser.getParsedSuccessMessage(output_dictionary, '200', 'Login successful.')


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


def cli_login(request):
    try:
        data = json.loads(request.body.decode())
        session_id = data.get("session_id")
        firebase_token = data.get("id_token")  # sent from frontend

        if not session_id or not firebase_token:
            return ResponseParser.getParsedSuccessMessage({}, 400, "Missing session_id or id_token")

        firebase_uid, _ = get_firebase_uid(firebase_token)
        try:
            user_object = User.objects.get(firebase_uid=firebase_uid)
        except User.DoesNotExist:
            return ResponseParser.getParsedSuccessMessage({}, 404, "User not found")

        # You can use your real API token logic here
        payload = {
            "uid": user_object.uid
        }

        # Store in cache for CLI polling to pick up
        cache.set(f"cli_login_session:{session_id}", payload, timeout=300)

        return ResponseParser.getParsedSuccessMessage(payload, 200, "CLI login success")

    except Exception as e:
        return ResponseParser.getParsedErrorMessage("Internal error: {str(e)}", 500)


def cli_login_status(request, session_id):
    data = cache.get(f"cli_login_session:{session_id}")
    if data:
        return ResponseParser.getParsedSuccessMessage(data,200, "CLI login status success")
    return ResponseParser.getParsedErrorMessage("Not yet authenticated", 404)