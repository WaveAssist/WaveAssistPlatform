import json
import uuid

from .models import *
from .Utils.responseParser import ResponseParser
import pandas as pd
from io import StringIO as StringIO
from .Utils.constants import *
import WaveAssistApiApp.Utils.utils as utils
import WaveAssistApiApp.Utils.validator as validator
from django.db import transaction
from WaveAssistApiApp.Utils.MongoManager import MongoManager
from WaveAssistApiApp.data_views import set_data_for_key
from WaveAssistApiApp.dashboard_views import get_firebase_uid
import WaveAssistApiApp.Utils.AWSManager as aws_manager
from WaveAssistApiApp.dashboard_views import handle_cli_session
from knockapi import Knock
knock_client = Knock(api_key=PROD_KNOCK_KEY)
from django.test import Client
import json
from WaveAssistApiApp.Utils.responseParser import ResponseParser

client = Client()


def get_started(request): #TCW
    firebase_token = request.POST.get('firebase_token', '')
    is_test = int(request.POST.get('is_test', 0)) == 1
    try:
        firebase_uid, decoded_dict = get_firebase_uid(firebase_token)
    except Exception as e:
        return ResponseParser.getParsedErrorMessage(f'Failed to login: {str(e)}')

    ##Create User
    try:
        user_object = User.objects.get(firebase_uid=firebase_uid)
    except:
        user_object = None

    if user_object is None:
        ##Create User
        uid = str(uuid.uuid4())
        name = request.POST.get('name', decoded_dict.get('full_name',''))
        username = request.POST.get('email', decoded_dict.get('email','email'))
        password = request.POST.get('password', 'REMOVED_CREDENTIAL')
        company_name = request.POST.get('company_name', 'Company')
        can_create_projects = True
        ##Check for name, if name not present, create name from email.
        try:
            if name == '':
                name = username.split('@')[0]
        except:
            pass
        try:
            user_object = User.objects.create(uid=uid, name=name, username=username, password=password,
                                              company_name=company_name, can_create_projects=can_create_projects,
                                              firebase_uid=firebase_uid
                                            )
            user_object.save()
        except Exception as e:
            print("User creation failed: " + str(e))
            return ResponseParser.getParsedErrorMessage('User creation failed.')

        ##Register user in Knock
        knock_client.users.update(
          user_id=str(uid),
          name=name,
          email=username
        )

    ##Check for existing Account
    try:
        account_object = Account.objects.filter(created_by_user=user_object)
        if account_object.count() == 0:
            ##Create Account
            account_name = request.POST.get('account_name', user_object.name)
            account_uid = user_object.uid
            celery_queue = 'queue_' + str(account_uid)
            account_object = Account.objects.create(account_name=account_name, account_uid=account_uid, created_by_user=user_object, celery_queue=celery_queue)
            account_object.save()
        else:
            account_object = account_object.first()
    except Exception as e:
        print("Account creation failed: " + str(e))
        return ResponseParser.getParsedErrorMessage('Account creation failed.')

    if account_object.mongo_db_url == '' and not is_test:
        ##Create Mongo url
        try:
            mongo_url,db_name = utils.create_mongo_url(user_object)
            account_object.mongo_db_url = mongo_url
            account_object.db_name = db_name
            account_object.save()
        except Exception as e:
            print("Mongo url creation failed: " + str(e))
            return ResponseParser.getParsedErrorMessage('Mongo url creation failed.' + str(e))

    if account_object.worker_service_arn == '' and not is_test:
        ##Create Worker
        try:
            worker_service_arn = aws_manager.create_worker(user_object.uid)
            account_object.worker_service_arn = worker_service_arn
            account_object.save()
        except Exception as e:
            print("Worker creation failed: " + str(e))
            return ResponseParser.getParsedErrorMessage('Worker creation failed.' + str(e))


    user_dict = user_object.get_dict()
    account_dict = account_object.get_dict()
    user_dict['mongo_db_url'] = account_object.mongo_db_url
    output_dict = {'user_data': user_dict, 'account': account_dict,'project_array':[]}
    utils.run_knock_workflow(str(user_object.uid), 'welcome')
    handle_cli_session(request, user_dict)
    return ResponseParser.getParsedSuccessMessage(output_dict, '200', 'User and Account created successfully.')


def create_user(request): #TCW
    uid = request.POST.get('uid', '')
    try:
        user_object = User.objects.get(uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not authorized or found.')

    ##Check if user is an admin
    admin_access_count = user_object.accessprovided_set.filter(type=0, project_access_type=3).count()

    if admin_access_count == 0 and not user_object.can_create_projects:
        return ResponseParser.getParsedErrorMessage('You do not have access to create user.')

    ##Creating a new user with default values
    user_default_uuid = str(uuid.uuid4())
    name = request.POST.get('name', user_default_uuid)
    username = request.POST.get('username', user_default_uuid)
    password = request.POST.get('password', user_default_uuid)
    company_name = request.POST.get('company_name', user_default_uuid)

    try:
        user_object = User.objects.create(name=name, username=username, password=password,
                                          company_name=company_name)
        user_object.save()
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('User creation failed: ' + str(e))

    data_dict = {
        "user_object": user_object.get_dict()
    }
    return ResponseParser.getParsedSuccessMessage(data_dict, '200', 'User created successfully.')



def fetch_all_projects(request): #TCW
    uid = request.POST.get('uid', '')
    try:
        user_object = User.objects.get(uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not authorized or found.')
    project_array = Project.objects.filter(
        accessprovided__type=0,
        accessprovided__project_access_type__gte=READ_GTE,
        accessprovided__user_object=user_object
    ).distinct()

    project_dict_array = []
    for project_object in project_array:
        project_dict_array.append(project_object.get_dict())
    output_dictionary = {'project_array': project_dict_array}
    return ResponseParser.getParsedSuccessMessage(output_dictionary, '200', 'Fetch successful.')



def create_project(request): ##TCW ##ToDo: Update test case for name & key
    uid = request.POST.get('uid', '')
    try:
        user_object = User.objects.get(uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')

    try:
        account_object = Account.objects.get(account_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('Account not found')

    if not user_object.can_create_projects:
        return ResponseParser.getParsedErrorMessage('You do not have access to create projects.')

    project_key = request.POST.get('project_key', '')
    project_name = request.POST.get('project_name', '')
    should_create_node = request.POST.get('should_create_node', 'False')
    if project_key == '':
        return ResponseParser.getParsedErrorMessage('Project key not found.')

    if project_name == '':
        return ResponseParser.getParsedErrorMessage('Project name not found.')

    ##Make lower case.
    project_key = project_key.lower()

    ##Check if project_key has any spaces
    if ' ' in project_key:
        return ResponseParser.getParsedErrorMessage('Project key should not contain any spaces.')

    ##Check if project_key already exists
    try:
        if AccessProvided.objects.filter(project_object__project_key=project_key, user_object=user_object).exists():
            return ResponseParser.getParsedErrorMessage('Project key already exists.')
    except:
        pass

    try:
        project_object = Project.objects.create(project_key=project_key, name = project_name)
        project_object.save()

        ##Add a default datarun to project
        data_run_name = 'Default'
        data_run_key = project_key + '_' + data_run_name.lower()
        data_run_object = DataRuns.objects.create(project_object=project_object, data_run_key = data_run_key, name=data_run_name, is_enabled=True)
        data_run_object.save()

        ##Add a test datarun to project
        data_run_name_test = 'Test'
        data_run_key_test = project_key + '_' + data_run_name_test.lower()
        data_run_test_object = DataRuns.objects.create(project_object=project_object, data_run_key = data_run_key_test, name=data_run_name_test, is_enabled=True)
        data_run_test_object.save()


    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Project creation failed: ' + str(e))

    try:
        project_access_object = AccessProvided.objects.create(type=0, project_object=project_object, user_object = user_object, project_access_type=ADMIN_GTE)
        project_access_object.save()

        data_run_access_object = AccessProvided.objects.create(type=1, data_run_object=data_run_object, user_object = user_object, data_run_access_type=ADMIN_GTE)
        data_run_access_object.save()

        ##Same for test
        data_run_access_object_test = AccessProvided.objects.create(type=1, data_run_object=data_run_test_object, user_object = user_object, data_run_access_type=ADMIN_GTE)
        data_run_access_object_test.save()

        # add two key value pair in the variables
        variables = [
            {"name": "uid", "value": str(uid)},
            {"name": "mongo_url", "value": str(account_object.mongo_db_url)},  # or actual URL if available
        ]
        for env_key in [data_run_key, data_run_key_test]:
            for variable in variables:
                var_name = variable["name"]
                var_value = variable["value"]
                try:
                    payload = {
                        'uid': uid,
                        'project_key': project_key,
                        'data_run_key': env_key,
                        'data': var_value,
                        'data_key': var_name,
                        'data_type': 'string',
                    }
                    response = client.post('/data/set_data_for_key/', data=json.dumps(payload),
                                           content_type='application/json')
                except Exception as e:
                    pass
        #create a default node if should_create_node is true

        if should_create_node.lower() == 'true':
            node_array = [{'name':'Node1', 'is_starting_node': '1', 'is_enabled': '1'},
                          {'name':'Node2', 'is_starting_node': '0', 'is_enabled': '1',
                           'run_after_nodes_csv': 'node1'},]
            for node in node_array:
                request.POST = request.POST.copy()
                request.POST['name'] = node['name']
                request.POST['is_starting_node'] = node['is_starting_node']
                request.POST['is_enabled'] = node['is_enabled']
                request.POST['run_after_nodes_csv'] = node.get('run_after_nodes_csv', '')
                create_node(request)

    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Project access creation failed: ' + str(e))

    return ResponseParser.getParsedSuccessMessage(project_object.get_dict(), '200', 'Project created successfully.')


def delete_data_key(request): ##TCW
    success, message, user_object, project_object = validator.validate_user_and_project(request, access_level_gte=ADMIN_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    ##Fetch Values
    data_key = request.POST.get('data_key', '')
    data_run_key = request.POST.get('data_run_key', '')

    ##Remove row from Mongo where IODataKey = key
    try:
        mongo_db_name = utils.get_database_name(user_object)
        mongo_manager = MongoManager()
        mongo_manager.database = mongo_manager.client[mongo_db_name]
        collection = mongo_manager.database[data_run_key]
        collection.delete_many({"IODataKey": data_key})
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Data key deletion failed: ' + str(e))

    return ResponseParser.getParsedSuccessMessage({}, '200', 'Data key deleted successfully.')


def create_data_key(request): ##TCW
    request.POST = request.POST.copy()
    data_type = request.POST.get('data_type', 'string')
    if data_type == 'json' or data_type == 'dataframe':
        data = '[]'
    else:
        data = ''
    request.POST['data_type'] = data_type
    request.POST['data'] = data
    return set_data_for_key(request)


def fetch_project_variables(request): #TCW

    ##Validate Request
    success, message, user_object, project_object = validator.validate_user_and_project(request, access_level_gte=READ_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    all_data_keys = set()

    ##Fetch all MongoKeys for project.
    mongo_db_name = utils.get_database_name(user_object)
    mongo_manager = MongoManager()
    mongo_manager.database = mongo_manager.client[mongo_db_name]


    ##Fetch all environment keys for project
    data_runs_array = DataRuns.objects.filter(project_object=project_object)
    for data_run_object in data_runs_array:
        collection_key = data_run_object.data_run_key
        collection = mongo_manager.database[collection_key]
        unique_iodata_keys = set(collection.distinct("IODataKey"))
        all_data_keys.update(unique_iodata_keys)

    ##Get data for project
    output_dict = {'data_keys': list(all_data_keys)}

    return ResponseParser.getParsedSuccessMessage(output_dict, '200', 'Project Variables fetched successfully.')


def fetch_nodes(request):  # TCW
    ##Validate Request
    success, message, user_object, project_object = validator.validate_user_and_project(request,
                                                                                        access_level_gte=READ_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    ##Nodes
    node_array = project_object.nodes_set.all().order_by(Lower('node_key'))
    node_dict_array = []
    for node_object in node_array:
        node_dict_array.append(node_object.get_dict())
    data_dict = {'node_array': node_dict_array}
    return ResponseParser.getParsedSuccessMessage(data_dict, '200', 'Nodes fetched successfully.')


def fetch_environments(request):  # TCW
    ##Validate Request
    success, message, user_object, project_object = validator.validate_user_and_project(request,
                                                                                        access_level_gte=READ_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    ##Provide data runs which user has access to, and belong to this project.
    data_run_array = DataRuns.objects.filter(accessprovided__type=1,
        accessprovided__data_run_access_type__gte=READ_GTE,
        accessprovided__user_object=user_object,
        project_object=project_object
    ).distinct()
    data_run_dict_array = []
    for data_run_object in data_run_array:
        data_run_dict_array.append(data_run_object.get_dict())

    data_dict = {'environment_array': data_run_dict_array}
    return ResponseParser.getParsedSuccessMessage(data_dict, '200', 'Project Environment fetched successfully.')



def fetch_deployments(request):  # Test cases pending
    ##Validate Request
    success, message, user_object, project_object = validator.validate_user_and_project(request, access_level_gte=READ_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    ##Validate Request
    success, message, user_object, data_run_object = validator.validate_user_and_data_run(request,
                                                                                        access_level_gte=READ_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    deployment_array = Deployments.objects.filter(project_object=project_object, data_run_object=data_run_object).order_by('-version')

    deployment_dict_array = []
    for deployment_object in deployment_array:
        deployment_dict_array.append(deployment_object.get_dict())
    data_dict = {'deployment_array': deployment_dict_array}
    return ResponseParser.getParsedSuccessMessage(data_dict, '200', 'Deployments fetched successfully.')


def delete_project(request): ##ToDo: Write test cases. Check related deleted. Check if DAG Runs are gone.
    ##Validate Request
    success, message, user_object, project_object = validator.validate_user_and_project(request, access_level_gte=ADMIN_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)
    try:
        project_object.delete()
    except:
        return ResponseParser.getParsedErrorMessage('Project deletion failed.')

    return ResponseParser.getParsedSuccessMessage({}, '200', 'Project deleted successfully.')


######## --- CRUD for DataKeys


###Node CRUD
def create_node(request): ##TCW
    success, message, user_object, project_object = validator.validate_user_and_project(request,access_level_gte=ADMIN_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    input_data_key_csv = request.POST.get('input_data_key_csv', '')
    output_data_key_csv = request.POST.get('output_data_key_csv', '')

    ##Validate Keys - Input
    success, message, input_data_keys_array = validator.validate_keys_csv(input_data_key_csv, project_object)
    if not success:
        return ResponseParser.getParsedErrorMessage('Input data keys should belong to this project: ' + message)
    ##Validate Keys - Output
    success, message, output_data_keys_array = validator.validate_keys_csv(output_data_key_csv, project_object)
    if not success:
        return ResponseParser.getParsedErrorMessage('Output data keys should belong to this project: ' + message)

    node_name = request.POST.get('name', '')
    node_key = node_name.lower().replace(' ', '_')
    is_enabled = bool(int(request.POST.get('is_enabled', '0')))

    is_starting_node = bool(int(request.POST.get('is_starting_node', '0')))
    schedule_type = request.POST.get('schedule_type', 'none').lower()
    success, message, interval_object, crontab_object, run_after_nodes_array = validator.validate_and_get_intervals(request, project_object)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    ##Check if node_key already exists
    if Nodes.objects.filter(node_key=node_key, project_object=project_object).exists():
        return ResponseParser.getParsedErrorMessage('Node with this key/name already exists in this project.')

    default_code = """\
    # This is the default node script
    # You can customize this code to define your workflow logic

    import waveassist

    # Initialize WaveAssist
    waveassist.init()

    # Your code starts here...
    """

    try:
        with transaction.atomic():
            node_object = Nodes(
                project_object=project_object,
                node_key=node_key,
                is_enabled=is_enabled,
                name = node_name,
                is_starting_node=is_starting_node,
                schedule_type=schedule_type,
                interval_schedule=interval_object,
                crontab_schedule=crontab_object,
                python_code=default_code
            )
            node_object.save()


            for input_data_key_object in input_data_keys_array:
                node_object.input_data_key_array.add(input_data_key_object)
            for output_data_key_object in output_data_keys_array:
                node_object.output_data_key_array.add(output_data_key_object)

            ##Run after nodes array
            node_object.run_after_nodes_array.set(run_after_nodes_array)

            ##Save Node
            node_object.save()

            ##Check DAG
            success, node_list, message = utils.check_dag(node_object, project_object.nodes_set.filter(is_enabled=True))
            if not success:
                raise Exception("Invalid DAG: " + message)
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Something went wrong while creating Node: ' + str(e))

    return ResponseParser.getParsedSuccessMessage(node_object.get_dict(), '200', 'Node updated successfully.')



def update_node(request): ## TCW
    success, message, user_object, project_object = validator.validate_user_and_project(request, access_level_gte=WRITE_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    node_key = request.POST.get('node_key', '')
    try:
        node_object = Nodes.objects.get(node_key=node_key, project_object=project_object)
    except:
        return ResponseParser.getParsedErrorMessage('Node not found.')

    try:
        with transaction.atomic():
            ##Input keys
            if 'input_data_key_csv' in request.POST:
                input_data_key_csv = request.POST.get('input_data_key_csv', '')
                success, message, input_data_keys_array = validator.validate_keys_csv(input_data_key_csv, project_object)
                if not success:
                    raise Exception('Input data keys should belong to this project: ' + message)
                node_object.input_data_key_array.set(input_data_keys_array)

            ##Output keys
            if 'output_data_key_csv' in request.POST:
                output_data_key_csv = request.POST.get('output_data_key_csv', '')
                success, message, output_data_keys_array = validator.validate_keys_csv(output_data_key_csv, project_object)
                if not success:
                    raise Exception('Output data keys should belong to this project: ' + message)
                node_object.output_data_key_array.set(output_data_keys_array)

            is_enabled = bool(int(request.POST.get('is_enabled', node_object.is_enabled)))
            node_object.is_enabled = is_enabled

            name = request.POST.get('name', node_object.name)
            node_object.name = name


            ##Interval & Schedules
            if 'schedule_type' in request.POST or 'run_after_nodes_csv' in request.POST:
                is_starting_node = bool(int(request.POST.get('is_starting_node', node_object.is_starting_node)))
                schedule_type = request.POST.get('schedule_type', node_object.schedule_type).lower()

                success, message, interval_object, crontab_object, run_after_nodes_array = validator.validate_and_get_intervals(
                    request, project_object, is_starting_node=is_starting_node, schedule_type=schedule_type)
                if not success:
                    raise Exception(message)
                node_object.schedule_type = schedule_type
                node_object.is_starting_node = is_starting_node
                node_object.interval_schedule = interval_object
                node_object.crontab_schedule = crontab_object
                node_object.run_after_nodes_array.set(run_after_nodes_array)

            node_object.save()

            ##Check DAG
            success, node_list, message = utils.check_dag(node_object, project_object.nodes_set.filter(is_enabled=True))
            if not success:
                raise Exception("Invalid DAG: " + message)

    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Something went wrong while updating Node: ' + str(e))

    return ResponseParser.getParsedSuccessMessage(node_object.get_dict(), '200', 'Node updated successfully.')




def delete_node(request): #TWC
    success, message, user_object, project_object = validator.validate_user_and_project(request,access_level_gte=WRITE_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)
    node_key = request.POST.get('node_key', '')
    try:
        node_object = Nodes.objects.get(node_key=node_key, project_object=project_object)
    except:
        return ResponseParser.getParsedErrorMessage('Node not found.')
    try:
        with transaction.atomic():
            node_object.delete()

            ##Fetch the first node of the project for DAG Check by is_starting_node
            starting_node = project_object.nodes_set.filter(is_starting_node=True, is_enabled=True).first()

            ##If no starting node, throw error
            if starting_node is None:
                raise Exception("No starting node found in project, ensure you have at least one starting node.")

            ##Check DAG
            success, node_list, message = utils.check_dag(starting_node, project_object.nodes_set.filter(is_enabled=True))

            if not success:
                raise Exception("Invalid DAG after deletion, ensure you delete the nodes in a fashion that ensures valid DAGS: " + message)
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Something went wrong while deleting Node, error: ' + str(e))

    return ResponseParser.getParsedSuccessMessage({}, '200', 'Node deleted successfully.')


##Node Details
def update_code(request): #TWC
    node_key = request.POST.get('node_key', '')
    python_code = request.POST.get('python_code', '')

    ##Validate request
    success, message, user_object, project_object = validator.validate_user_and_project(request, access_level_gte=WRITE_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    try:
        node_object = Nodes.objects.get(node_key=node_key, project_object = project_object)
    except:
        return ResponseParser.getParsedErrorMessage('Node not found')

    node_object.python_code = python_code
    node_object.save()

    return ResponseParser.getParsedSuccessMessage(node_object.get_dict(), '200', 'Code updated successfully.')



##Integrations CRUD
def activate_integration(request): #TWC without mongo checks(manage_integration_details)
    # success, message, user_object, project_object = validator.validate_user_and_project(request, access_level_gte=WRITE_GTE)
    # if not success:
    #     return ResponseParser.getParsedErrorMessage(message)
    #
    # integration_key = request.POST.get('integration_key', '')
    # if project_object.integration_array.filter(integration_key=integration_key).count() > 0:
    #     return ResponseParser.getParsedErrorMessage('Integration already exist, and is active')
    #
    # try:
    #     integration_object = Integrations.objects.get(integration_key=integration_key)
    # except:
    #     return ResponseParser.getParsedErrorMessage('Integration not found')
    #
    # try:
    #     project_object.integration_array.add(integration_object)
    #     project_object.save()
    # except:
    #     return ResponseParser.getParsedErrorMessage('Something went wrong while adding integration')
    #
    # ##Manage Mongo Data
    # try:
    #     manage_integration_details(integration_object, project_object)
    # except:
    #     return ResponseParser.getParsedErrorMessage('Something went wrong while managing integration details')

    return ResponseParser.getParsedSuccessMessage({}, '200', 'Integration activated successfully.')




def deactivate_integration(request): #TWC
    # success, message, user_object, project_object = validator.validate_user_and_project(request, access_level_gte=WRITE_GTE)
    # if not success:
    #     return ResponseParser.getParsedErrorMessage(message)
    #
    # integration_key = request.POST.get('integration_key', '')
    # if project_object.integration_array.filter(integration_key=integration_key).count() == 0:
    #     return ResponseParser.getParsedErrorMessage('Integration not active for this project')
    #
    # try:
    #     integration_object = Integrations.objects.get(integration_key=integration_key)
    # except:
    #     return ResponseParser.getParsedErrorMessage('Integration not found')
    #
    # try:
    #     project_object.integration_array.remove(integration_object)
    #     project_object.save()
    # except:
    #     return ResponseParser.getParsedErrorMessage('Something went wrong while deactivating integration')

    return ResponseParser.getParsedSuccessMessage({}, '200', 'Integration deactivated successfully.')




##Crud dashboard section

def create_dashboard_section(request): #TCW
    success, message, user_object, project_object = validator.validate_user_and_project(request, access_level_gte=WRITE_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    row = request.POST.get('row', 0)
    column = request.POST.get('column', 0)
    display_type = request.POST.get('display_type', 0)
    data_key = request.POST.get('data_key', '')
    title = request.POST.get('title', '')
    should_display_title = bool(int(request.POST.get('should_display_title', 1)))
    is_editable = bool(int(request.POST.get('is_editable', 0)))
    try:
        data_key_object = DataKey.objects.get(key=data_key)
    except:
        return ResponseParser.getParsedErrorMessage('Data Key not found')

    try:
        dashboard_section_object = DashboardSection.objects.create(row=row, column=column, display_type=display_type, data_key_object=data_key_object,
                                                                   title=title, should_display_title=should_display_title, is_editable=is_editable, project_object=project_object)
        dashboard_section_object.save()
    except:
        return ResponseParser.getParsedErrorMessage('Something went wrong while creating dashboard section')


    return ResponseParser.getParsedSuccessMessage(dashboard_section_object.get_dict(), '200', 'Dashboard section created successfully.')



def update_dashboard_section(request): #TCW
    success, message, user_object, project_object = validator.validate_user_and_project(request, access_level_gte=WRITE_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    dashboard_section_key = request.POST.get('dashboard_section_key', '')
    try:
        dashboard_section_object = DashboardSection.objects.get(dashboard_section_key=dashboard_section_key)
    except:
        return ResponseParser.getParsedErrorMessage('Dashboard Section not found')


    row = request.POST.get('row', dashboard_section_object.row)
    column = request.POST.get('column', dashboard_section_object.column)
    display_type = request.POST.get('display_type', dashboard_section_object.display_type)
    data_key = request.POST.get('data_key', dashboard_section_object.data_key_object.key)
    title = request.POST.get('title', dashboard_section_object.title)
    should_display_title = bool(int(request.POST.get('should_display_title', dashboard_section_object.should_display_title)))
    is_editable = bool(int(request.POST.get('is_editable', dashboard_section_object.is_editable)))

    try:
        data_key_object = DataKey.objects.get(key=data_key)
    except:
        return ResponseParser.getParsedErrorMessage('Data Key not found')

    try:
        dashboard_section_object.row = row
        dashboard_section_object.column = column
        dashboard_section_object.display_type = display_type
        dashboard_section_object.data_key_object = data_key_object
        dashboard_section_object.title = title
        dashboard_section_object.should_display_title = should_display_title
        dashboard_section_object.is_editable = is_editable
        dashboard_section_object.save()
        return ResponseParser.getParsedSuccessMessage(dashboard_section_object.get_dict(), '200', 'Dashboard section updated successfully.')
    except:
        return ResponseParser.getParsedErrorMessage('Something went wrong while updating dashboard section')




def delete_dashboard_section(request): #TCW
    success, message, user_object, project_object = validator.validate_user_and_project(request, access_level_gte=WRITE_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    dashboard_section_key = request.POST.get('dashboard_section_key', '')
    try:
        dashboard_section_object = DashboardSection.objects.get(dashboard_section_key=dashboard_section_key)
    except:
        return ResponseParser.getParsedErrorMessage('Dashboard Section not found')

    try:
        dashboard_section_object.delete()
        return ResponseParser.getParsedSuccessMessage({}, '200', 'Dashboard section deleted successfully.')
    except:
        return ResponseParser.getParsedErrorMessage('Something went wrong while deleting dashboard section')


##CRUD: Data Runs
def create_data_run(request): #TCW
    success, message, user_object, project_object = validator.validate_user_and_project(request, access_level_gte=ADMIN_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    name = request.POST.get('name', '')
    is_enabled = bool(int(request.POST.get('is_enabled', '0')))
    data_run_key = project_object.project_key + '_' + name.lower()

    ##Check if data_run key already exist for project, return if it does.
    try:
        data_run_object = DataRuns.objects.get(data_run_key=data_run_key, project_object=project_object)
        return ResponseParser.getParsedSuccessMessage(data_run_object.get_dict(), '200',
                                                      'Data Run fetched successfully.')
    except:
        pass

    try:
        data_run_object = DataRuns.objects.create(name=name, data_run_key=data_run_key, project_object=project_object, is_enabled=is_enabled)
        data_run_object.save()
    except:
        return ResponseParser.getParsedErrorMessage('Something went wrong while creating Data Run, make sure your data_run name is unique')

    ##Provide access to user for this data run
    try:
        data_run_access_object = AccessProvided.objects.create(type=1, data_run_object=data_run_object, user_object=user_object, data_run_access_type=ADMIN_GTE)
        data_run_access_object.save()
    except:
        return ResponseParser.getParsedErrorMessage('Something went wrong while providing access to Data Run')

    return ResponseParser.getParsedSuccessMessage(data_run_object.get_dict(), '200', 'Data Run created successfully.')


def update_data_run(request): #TCW
    success, message, user_object, project_object = validator.validate_user_and_project(request, access_level_gte=ADMIN_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    ##ToDo: Even the admin to the data run should be able to update it
    data_run_key = request.POST.get('data_run_key', '')
    try:
        data_run_object = DataRuns.objects.get(data_run_key=data_run_key)
    except:
        return ResponseParser.getParsedErrorMessage('Data Run not found')

    name = request.POST.get('name', data_run_object.name)
    is_enabled = bool(int(request.POST.get('is_enabled', data_run_object.is_enabled)))

    try:
        data_run_object.name = name
        data_run_object.is_enabled = is_enabled
        data_run_object.save()
    except:
        return ResponseParser.getParsedErrorMessage('Something went wrong while updating Data Run')

    return ResponseParser.getParsedSuccessMessage(data_run_object.get_dict(), '200', 'Data Run updated successfully.')


def delete_data_run(request): #TCW
    success, message, user_object, project_object = validator.validate_user_and_project(request, access_level_gte=ADMIN_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    data_run_key = request.POST.get('data_run_key', '')
    try:
        data_run_object = DataRuns.objects.get(data_run_key=data_run_key)
    except:
        return ResponseParser.getParsedErrorMessage('Data Run not found')

    try:
        data_run_object.delete()
    except:
        return ResponseParser.getParsedErrorMessage('Something went wrong while deleting Data Run')

    ##ToDo: Delete the related periodic task.
    ##ToDo: Delete mongo data
    ##ToDo: Same in disable, disable periodic tasks.

    return ResponseParser.getParsedSuccessMessage({}, '200', 'Data Run deleted successfully.')

