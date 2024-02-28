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
from django.utils.text import slugify
from django.http import HttpRequest

mongo_manager = MongoManager()


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



def create_user(request):
    ##Login
    name = models.CharField(max_length=255, default="", null=True)
    username = models.CharField(max_length=255, unique=True)
    password = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255)
    firebase_uid = models.CharField(max_length=100, unique=True)







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

        ##Add flow to project
        flow_object = Flows.objects.create(project=project_object)
        flow_object.client_array.add(client_object)
        flow_object.save()

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
    mongo_manager.collection = mongo_manager.database[project_key]
    dashboard_data_array = mongo_manager.fetch_data_for_key(dashboard_data_key)
    project_dict['dashboard_data_array'] = dashboard_data_array


    ##Get Flows data array
    flow_data_array = project_object.flows_set.all()
    flow_data_dict_array = []
    for flow_data_object in flow_data_array:
        flow_data_dict_array.append(flow_data_object.get_dict())
    project_dict['flow_data_array'] = flow_data_dict_array

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

    project_key = request.POST.get('project_key', '')
    try:
        project_object = Project.objects.get(project_key=project_key)
    except:
        return ResponseParser.getParsedErrorMessage('Project not found')

    uid = request.POST.get('uid', '')
    try:
        client_object = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')

    if not utils.has_access(client_object, project_key):
        return ResponseParser.getParsedErrorMessage('You do not have access to this project')

    uploaded_file = request.FILES['file']
    io_data_key = request.POST.get('io_data_key', '')


    data_type = uploaded_file.name.split('.')[-1].lower()
    csv_data = uploaded_file.read().decode('utf-8')
    if data_type != 'csv':
        return ResponseParser.getParsedErrorMessage('Invalid file type. Only CSV files are allowed.')

    pd_data = pd.read_csv(StringIO(csv_data))

    success = set_pd_data_for_key_for_all(io_data_key, pd_data, is_master_key=False)

    if success:
        return ResponseParser.getParsedSuccessMessage({}, '200', 'IO data updated successfully for all flows.')
    else:
        return ResponseParser.getParsedErrorMessage('Something went wrong while updating io data')


def update_io_data(request):
    uid = request.POST.get('uid', '')
    try:
        client_object = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')

    try:
        io_data_id = int(request.POST.get('io_data_id', ''))
        io_data_object = IOData.objects.get(id=io_data_id)
    except:
        return ResponseParser.getParsedErrorMessage('IO Data not found.')


    if not utils.does_user_have_io_data_access(client_object, io_data_object):
        return ResponseParser.getParsedErrorMessage('You do not have access to this IO Data')

    key = request.POST.get('key', '')
    output_type = str(request.POST.get('output_type', ''))

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

    if not utils.has_access(client_object, project_key):
        return ResponseParser.getParsedErrorMessage('You do not have access to this project')

    key = request.POST.get('key', '')
    output_type = str(request.POST.get('output_type', ''))

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
        key = request.POST.get('key', '')
        io_data_object = IOData.objects.get(key=key)
    except:
        return ResponseParser.getParsedErrorMessage('IO Data not found.')

    if not utils.does_user_have_io_data_access(client_object, io_data_object):
        return ResponseParser.getParsedErrorMessage('You do not have access to this IO Data')

    try:
        io_data_object.delete()
    except:
        return ResponseParser.getParsedErrorMessage('Something went wrong while deleting IO Data')

    return ResponseParser.getParsedSuccessMessage({}, '200', 'IO Data deleted successfully.')



##MONGOCHANGE
def download_io_data(request):
    uid = request.GET.get('uid', '')
    try:
        client_object = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')

    try:
        key = request.GET.get('key', '')
        io_data_object = IOData.objects.get(key=key)
    except:
        return ResponseParser.getParsedErrorMessage('IO Data not found.')

    if not utils.does_user_have_io_data_access(client_object, io_data_object):
        return ResponseParser.getParsedErrorMessage('You do not have access to this IO Data')


    project_object = io_data_object.project

    ##Fetch the first flow for this project
    try:
        flow_object = project_object.flows_set.all()[0]
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('No flows found.')

    collection_key = utils.get_collection_key(flow_object, project_object)
    mongo_manager.collection = mongo_manager.database[collection_key]
    data_df = mongo_manager.fetch_data_as_dataframe(key)
    csv_string = data_df.to_csv(index=False)
    file_name = 'download_' + key

    return ResponseParser.getHTTPResponseForCSV(csv_string, file_name)

###Node
def update_node(request):
    uid = request.POST.get('uid', '')
    try:
        client_object = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')

    try:
        node_id = int(request.POST.get('node_id', ''))
        node_object = Nodes.objects.get(id=node_id)
    except:
        return ResponseParser.getParsedErrorMessage('Node not found.')

    project_key = request.POST.get('project_key', '')
    try:
        project_object = Project.objects.get(project_key=project_key)
    except:
        return ResponseParser.getParsedErrorMessage('Project not found')

    if not utils.has_access(client_object, project_key):
        return ResponseParser.getParsedErrorMessage('You do not have access to this project')


    if not utils.does_user_have_node_access(client_object, node_object):
        return ResponseParser.getParsedErrorMessage('You do not have access to this IO Data')

    node_key = request.POST.get('node_key', '')
    name = request.POST.get('name', '')
    running_status = str(request.POST.get('running_status', ''))
    start_frequency_in_seconds = request.POST.get('start_frequency_in_seconds', '')
    input_data_key_csv = request.POST.get('input_data_key_csv', '')
    output_data_key_csv = request.POST.get('output_data_key_csv', '')


    if running_status not in ['0', '1']:
        return ResponseParser.getParsedErrorMessage('Invalid running status.')


    ##Check if key has prefix of project_key + _ - case insensitive
    if not node_key.lower().startswith(project_key.lower() + '_'):
        return ResponseParser.getParsedErrorMessage('Key should start with project key + _')

    ##Process input_data_key_csv. Remove all existing input data and add new ones.
    node_object.input_data_array.clear()
    if input_data_key_csv != '':
        input_data_key_list = input_data_key_csv.split(',')
        for input_data_key in input_data_key_list:
            try:
                io_data_object = IOData.objects.get(key=input_data_key)
                if utils.does_user_have_io_data_access(client_object, io_data_object): ##Can be optimised.
                    node_object.input_data_array.add(io_data_object)
            except:
                pass

    ##Process output_data_key_csv. Remove all existing output data and add new ones.
    node_object.output_data_array.clear()
    if output_data_key_csv != '':
        output_data_key_list = output_data_key_csv.split(',')
        for output_data_key in output_data_key_list:
            try:
                io_data_object = IOData.objects.get(key=output_data_key)
                if utils.does_user_have_io_data_access(client_object, io_data_object): ##Can be optimised.
                    node_object.output_data_array.add(io_data_object)
            except:
                pass

    try:
        node_object.node_key = node_key
        node_object.name = name
        node_object.running_status = running_status
        node_object.start_frequency_in_seconds = start_frequency_in_seconds
        node_object.save()
    except:
        return ResponseParser.getParsedErrorMessage('Something went wrong while updating Node, ensure the key in unique')

    return ResponseParser.getParsedSuccessMessage(node_object.get_dict(), '200', 'Node updated successfully.')




def create_node(request):
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

    if not utils.has_access(client_object, project_key):
        return ResponseParser.getParsedErrorMessage('You do not have access to this project')


    node_key = request.POST.get('node_key', '')
    name = request.POST.get('name', '')
    running_status = str(request.POST.get('running_status', ''))
    start_frequency_in_seconds = request.POST.get('start_frequency_in_seconds', '')
    input_data_key_csv = request.POST.get('input_data_key_csv', '')
    output_data_key_csv = request.POST.get('output_data_key_csv', '')


    if running_status not in ['0', '1']:
        return ResponseParser.getParsedErrorMessage('Invalid running status.')



    ##Check if key has prefix of project_key + _ - case insensitive
    if not node_key.lower().startswith(project_key.lower() + '_'):
        return ResponseParser.getParsedErrorMessage('Key should start with project key + _')

    try:
        node_object = Nodes(
            project=project_object,
            node_key=node_key,
            name=name,
            description=name,
            running_status=running_status,
            start_frequency_in_seconds=start_frequency_in_seconds
        )
        node_object.save()
    except:
        return ResponseParser.getParsedErrorMessage('Something went wrong while creating Node, ensure the key in unique')



    ##Process input_data_key_csv. Remove all existing input data and add new ones.
    node_object.input_data_array.clear()

    if input_data_key_csv != '':
        input_data_key_list = input_data_key_csv.split(',')
        for input_data_key in input_data_key_list:
            try:
                io_data_object = IOData.objects.get(key=input_data_key)
                if utils.does_user_have_io_data_access(client_object, io_data_object): ##Can be optimised.
                    node_object.input_data_array.add(io_data_object)
            except:
                pass

    ##Process output_data_key_csv. Remove all existing output data and add new ones.
    node_object.output_data_array.clear()
    if output_data_key_csv != '':
        output_data_key_list = output_data_key_csv.split(',')
        for output_data_key in output_data_key_list:
            try:
                io_data_object = IOData.objects.get(key=output_data_key)
                if utils.does_user_have_io_data_access(client_object, io_data_object): ##Can be optimised.
                    node_object.output_data_array.add(io_data_object)
            except:
                pass

    try:
        node_object.save()
    except:
        return ResponseParser.getParsedErrorMessage('Something went wrong while creating node and assigning data.')


    ##Append the node_object to project_object's node_array
    try:
        project_object.node_array.add(node_object)
        project_object.save()
    except:
        return ResponseParser.getParsedErrorMessage('Something went wrong while creating node and assigning project.')


    return ResponseParser.getParsedSuccessMessage(node_object.get_dict(), '200', 'Node updated successfully.')



def delete_node(request):
    uid = request.POST.get('uid', '')
    try:
        client_object = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')

    node_key = request.POST.get('node_key', '')
    try:
        node_object = Nodes.objects.get(node_key=node_key)
    except:
        return ResponseParser.getParsedErrorMessage('Node not found')

    if not utils.does_user_have_node_access(client_object, node_object):
        return ResponseParser.getParsedErrorMessage('You do not have access to this Node')

    try:
        node_object.delete()
    except:
        return ResponseParser.getParsedErrorMessage('Something went wrong while deleting Node')

    return ResponseParser.getParsedSuccessMessage({}, '200', 'Node deleted successfully.')




def update_integrations(request):
    active_integrations_csv = request.POST.get('active_integrations_csv', '')
    project_key = request.POST.get('project_key', '')
    uid = request.POST.get('uid', '')
    try:
        client_object = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')

    try:
        project_object = Project.objects.get(project_key=project_key)
    except:
        return ResponseParser.getParsedErrorMessage('Project not found')

    if not utils.has_access(client_object, project_key):
        return ResponseParser.getParsedErrorMessage('You do not have access to this project')

    active_integrations_list = active_integrations_csv.split(',')
    project_object.integration_array.clear()
    for integration_name in active_integrations_list:
        try:
            integration_object = Integrations.objects.get(name=integration_name)
            utils.manage_integration_details(mongo_manager, integration_object, project_object)
            project_object.integration_array.add(integration_object)
        except:
            pass
    try:
        project_object.save()
    except:
        return ResponseParser.getParsedErrorMessage('Something went wrong while updating integrations')

    return ResponseParser.getParsedSuccessMessage({}, '200', 'Integrations updated successfully.')


def remove_integrations(request):
    integration_name = request.POST.get('integration_name', '')
    project_key = request.POST.get('project_key', '')
    uid = request.POST.get('uid', '')
    try:
        client_object = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')

    try:
        project_object = Project.objects.get(project_key=project_key)
    except:
        return ResponseParser.getParsedErrorMessage('Project not found')

    if not utils.has_access(client_object, project_key):
        return ResponseParser.getParsedErrorMessage('You do not have access to this project')

    try:
        integration_object = Integrations.objects.get(name=integration_name)
    except:
        return ResponseParser.getParsedErrorMessage('Integration not found')

    try:
        project_object.integration_array.remove(integration_object)
        project_object.save()
    except:
        return ResponseParser.getParsedErrorMessage('Something went wrong while removing integration')

    return ResponseParser.getParsedSuccessMessage({}, '200', 'Integration removed successfully.')


def set_node_test_status(request):
    project_key = request.POST.get('project_key', '')
    node_key = request.POST.get('node_key', '')
    uid = request.POST.get('uid', '')
    test_status = int(request.POST.get('test_status', '0'))

    try:
        client_object = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')

    try:
        project_object = Project.objects.get(project_key=project_key)
    except:
        return ResponseParser.getParsedErrorMessage('Project not found')

    if not utils.has_access(client_object, project_key):
        return ResponseParser.getParsedErrorMessage('You do not have access to this project')

    try:
        node_object = Nodes.objects.get(node_key=node_key)
    except:
        return ResponseParser.getParsedErrorMessage('Node not found')

    try:
        node_object.test_status = test_status
        node_object.save()
    except:
        return ResponseParser.getParsedErrorMessage('Something went wrong while updating node')

    return ResponseParser.getParsedSuccessMessage({}, '200', 'Node updated successfully.')



def set_restart_status(request):
    project_key = request.POST.get('project_key', '')
    try:
        project_object = Project.objects.get(project_key=project_key)
    except:
        return ResponseParser.getParsedErrorMessage('Project not found')

    new_status = int(request.POST.get('new_status', '1'))

    uid = request.POST.get('uid', '')
    try:
        client_object = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')

    if not utils.has_access(client_object, project_key):
        return ResponseParser.getParsedErrorMessage('You do not have access to this project')

    try:
        project_object.refresh_status = new_status
        project_object.save()
        output_dictionary = {'status': str(new_status)}
        return ResponseParser.getParsedSuccessMessage(output_dictionary, '200',
                                                        'Refresh status updated successfully.')
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Something went wrong with restarting: ' + str(e))



def update_dashboard_data(request):
    project_key = request.POST.get('project_key', '')
    try:
        project_object = Project.objects.get(project_key=project_key)
    except:
        return ResponseParser.getParsedErrorMessage('Project not found')


    uid = request.POST.get('uid', '')
    try:
        client_object = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')


    if not utils.has_access(client_object, project_key):
        return ResponseParser.getParsedErrorMessage('You do not have access to this project')


    try:
        json_string_data = str(request.POST.get('json_data', ''))
        pd_data = pd.read_json(json_string_data)
    except:
        return ResponseParser.getParsedErrorMessage('Invalid json data')


    ##Find the IOData with type 2 for this project and get io_data_key
    try:
        io_data_object = IOData.objects.get(project=project_object, output_type=2)
        io_data_key = io_data_object.key
    except:
        try:
            ##Delete all existing IOData objects with type 2 for this project
            IOData.objects.filter(project=project_object, output_type=2).delete()
        except:
            pass
        try:
            ##Create a new IOData object with type 2 for this project
            io_data_key = project_key + '_dashboard_data'
            io_data_object = IOData.objects.create(key=io_data_key, output_type=2, project=project_object)
            io_data_object.save()
        except Exception as e:
            print("Error with IOData Create: " + str(e))
            return ResponseParser.getParsedErrorMessage('Something went wrong while creating IOData object')

    success = set_pd_data_for_key_for_all(io_data_key, pd_data, is_master_key=True)

    if success:
        return ResponseParser.getParsedSuccessMessage({}, '200', 'Dashboard data updated successfully.')
    else:
        return ResponseParser.getParsedErrorMessage('Something went wrong while updating dashboard data')



def set_pd_data_for_key_for_all(io_data_key, pd_data, is_master_key=False):
    try:
        io_data_object = IOData.objects.get(key=io_data_key)
        project_object = io_data_object.project
        project_key = project_object.project_key
    except Exception as e:
        return False

    try:
        ##Remove row_number column in pd_data if it exists
        pd_data = pd_data.drop('row_number', axis=1, errors='ignore')

        ##Save in mongo db
        if is_master_key:
            mongo_manager.collection = mongo_manager.database[project_key]
            success = mongo_manager.replace_data_as_dataframe(io_data_key, pd_data)
            if not success:
                return False
        else:
            flows_array = project_object.flows_set.all()
            for flow_object in flows_array:
                collection_key = utils.get_collection_key(flow_object, project_object)
                mongo_manager.collection = mongo_manager.database[collection_key]
                success = mongo_manager.replace_data_as_dataframe(io_data_key, pd_data)
                if not success:
                    return False
        return True

    except Exception as e:
        return False