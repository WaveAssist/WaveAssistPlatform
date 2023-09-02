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
import WaveAssistApiApp.Utils.utils as utils
import WaveAssistApiApp.views as views
import json
import csv
from django.http import JsonResponse


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


def fetch_project_data(request):
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
    except:
        return ResponseParser.getParsedErrorMessage('Project key not found.')


    #Check for accesss
    if not utils.has_access(client_object, project_key):
        return ResponseParser.getParsedErrorMessage('You do not have access to this project')


    ##Get data for project
    project_dict = project_object.get_dict()

    ##Get IO Data array
    dashboard_data_key = ""
    io_data_array = project_object.iodata_set.filter(output_type__in=[0,1,2])
    io_data_dict_array = []
    for io_data_object in io_data_array:
        if io_data_object.output_type == 2:
            dashboard_data_key = io_data_object.key
            continue
        io_data_dict_array.append(io_data_object.get_dict())
    project_dict['io_data_array'] = io_data_dict_array

    ##Get Node Data array
    node_data_array = project_object.node_array.all()
    node_data_dict_array = []
    for node_data_object in node_data_array:
        node_data_dict_array.append(node_data_object.get_dict())
    project_dict['node_data_array'] = node_data_dict_array

    ##Get Integrations Data array
    integrations_data_array = project_object.integration_array.all()
    integrations_data_dict_array = []
    for integrations_data_object in integrations_data_array:
        integrations_data_dict_array.append(integrations_data_object.get_dict())
    project_dict['integrations_data_array'] = integrations_data_dict_array

    ##Get Clients array
    client_array = project_object.client_array.all()
    client_dict_array = []
    for client_object in client_array:
        client_dict_array.append(client_object.get_dict())
    project_dict['client_array'] = client_dict_array

    ##Get Dashboard data from Mongo

    mongo_manager = MongoManager(collection_name=project_key)
    mongo_manager.collection = mongo_manager.database[project_key]
    integrations_data_array = mongo_manager.fetch_data_for_key(dashboard_data_key)
    project_dict['dashboard_data_array'] = integrations_data_array

    return ResponseParser.getParsedSuccessMessage(project_dict, '200', 'Project data fetched successfully.')



def update_code(request):
    uid = request.POST.get('uid', '')
    try:
        client_object = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')

    node_key = request.POST.get('node_key', '')
    python_code = request.POST.get('python_code', '')

    try:
        node_object = Nodes.objects.get(node_key=node_key)
    except:
        return ResponseParser.getParsedErrorMessage('Node not found')

    if not utils.does_user_have_node_access(client_object, node_object):
        return ResponseParser.getParsedErrorMessage('You do not have access to this node')

    node_object.python_code = python_code
    node_object.save()

    return ResponseParser.getParsedSuccessMessage(node_object.get_dict(), '200', 'Code updated successfully.')




def upload_io_data_file(request):
    try:
        uploaded_file = request.FILES['file']
        # Determine the file type by checking the file extension
        data_type = uploaded_file.name.split('.')[-1].lower()

        content = uploaded_file.read().decode('utf-8')
        request.POST['data_type'] = data_type

        if data_type == 'csv':
            request.POST['csv_data'] = content
        elif data_type == 'json':
            request.POST['json_data'] = content
        else:
            return ResponseParser.getParsedErrorMessage('Invalid file type')

        return views.set_data_for_key(request)

    except:
        return ResponseParser.getParsedErrorMessage('Something went wrong with file extraction')



def update_io_data(request):
    uid = request.POST.get('uid', '')
    try:
        client_object = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')

    try:
        io_data_id = int(request.POST.get('io_data_id', ''))
        io_data_object = IOData.objects.get(id=io_data_id).select_related('project')
    except:
        return ResponseParser.getParsedErrorMessage('IO Data not found.')


    if not utils.does_user_have_io_data_access(client_object, io_data_object):
        return ResponseParser.getParsedErrorMessage('You do not have access to this IO Data')

    key = request.POST.get('key', '')
    output_type = request.POST.get('output_type', '')

    if output_type == '':
        return ResponseParser.getParsedErrorMessage('Output type not found.')

    if output_type not in ['0', '1', '2']:
        return ResponseParser.getParsedErrorMessage('Invalid output type.')

    ##Check if key has prefix of project_key + _ - case insensitive
    project_key = io_data_object.project.project_key
    if not key.lower().startswith(project_key.lower() + '_'):
        return ResponseParser.getParsedErrorMessage('Key should start with project key + _')

    try:
        io_data_object.output_type = output_type
        io_data_object.key = key
        io_data_object.save()
    except:
        return ResponseParser.getParsedErrorMessage('Something went wrong while updating IO Data, ensure the key in unique')

    return ResponseParser.getParsedSuccessMessage(io_data_object.get_dict(), '200', 'IO Data updated successfully.')



def create_io_data(request):
    uid = request.POST.get('uid', '')
    try:
        client_object = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')

    project_key = request.POST.get('project_key', '')
    try:
        project_object = Project.objects.get(project_key=project_key)
    except:
        return ResponseParser.getParsedErrorMessage('Project not found')

    if not utils.has_access(client_object, project_object):
        return ResponseParser.getParsedErrorMessage('You do not have access to this project')

    key = request.POST.get('key', '')
    output_type = request.POST.get('output_type', '')

    if output_type == '':
        return ResponseParser.getParsedErrorMessage('Output type not found.')

    if output_type not in ['0', '1', '2']:
        return ResponseParser.getParsedErrorMessage('Invalid output type.')

    ##Check if key has prefix of project_key + _ - case insensitive
    if not key.lower().startswith(project_key.lower() + '_'):
        return ResponseParser.getParsedErrorMessage('Key should start with project key + _')

    try:
        io_data_object = IOData(
            project=project_object,
            output_type=output_type,
            key=key
        )
        io_data_object.save()
    except:
        return ResponseParser.getParsedErrorMessage('Something went wrong while updating IO Data, ensure the key in unique')

    return ResponseParser.getParsedSuccessMessage(io_data_object.get_dict(), '200', 'IO Data updated successfully.')



def delete_io_data(request):
    uid = request.POST.get('uid', '')
    try:
        client_object = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')

    try:
        key = int(request.POST.get('key', ''))
        io_data_object = IOData.objects.get(key=key).select_related('project')
    except:
        return ResponseParser.getParsedErrorMessage('IO Data not found.')

    if not utils.does_user_have_io_data_access(client_object, io_data_object):
        return ResponseParser.getParsedErrorMessage('You do not have access to this IO Data')

    try:
        io_data_object.delete()
    except:
        return ResponseParser.getParsedErrorMessage('Something went wrong while deleting IO Data')

    return ResponseParser.getParsedSuccessMessage({}, '200', 'IO Data deleted successfully.')

