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


def fetch_all_project(request):
    uid = request.POST.get('uid', '')
    try:
        client_object = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')

    project_array = client_object.project_set.filter()

    project_dict_array = []
    for project_object in project_array:
        project_dict_array.append(project_object.get_dict())
    output_dictionary = {'project_array': project_dict_array}
    return ResponseParser.getParsedSuccessMessage(output_dictionary, '200', 'Login successful.')


def create_project(request):
    uid = request.POST.get('uid', '')
    try:
        client_object = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')

    project_key = request.POST.get('project_key', '')
    if project_key == '':
        return ResponseParser.getParsedErrorMessage('Project key not found.')

    ##Check if project_key already exists
    try:
        project_object = Project.objects.get(project_key=project_key)
        return ResponseParser.getParsedErrorMessage('Project key already exists.')
    except:
        pass

    try:
        project_object = Project.objects.create(project_key=project_key, running_status=0, payment_status=0, refresh_status=0)
        project_object.client_array.add(client_object)
        project_object.save()
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Project creation failed: ' + str(e))

    return ResponseParser.getParsedSuccessMessage(project_object.get_dict(), '200', 'Project created successfully.')
