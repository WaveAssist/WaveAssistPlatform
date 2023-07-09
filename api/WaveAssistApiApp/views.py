from django.shortcuts import render
from .models import *
from .Utils.responseParser import ResponseParser

# Create your views here.


## API to load client details
def load_all_clients(request):
    uid = request.POST.get('uid', '')
    try:
        user_profile = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')

    try:
        client_details = Client.objects.all()
        client_details_list = []
        for client_detail in client_details:
            client_details_list.append(client_detail.to_dict())

        output_dictionary = {'client_array': client_details_list}
        return ResponseParser.getParsedSuccessMessage(output_dictionary, '200', 'Client details loaded successfully.')
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Something went wrong: ' + str(e))


## API to load nodes details
def load_node_data(request):
    uid = request.POST.get('uid', '')
    try:
        user_profile = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')

    client_key = request.POST.get('client_key', '')
    try:
        project_objects_list = Project.objects.filter(client__client_key=client_key)
        node_details = project_objects_list.node_list.all()
        node_details_list = []
        for node_detail in node_details:
            node_details_list.append(node_detail.to_dict())

        output_dictionary = {'node_array': node_details_list}
        return ResponseParser.getParsedSuccessMessage(output_dictionary, '200', 'Node details loaded successfully.')
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Something went wrong: ' + str(e))


## API to get code of the node
def get_node_code(request):
    uid = request.POST.get('uid', '')
    try:
        user_profile = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')

    try:
        node_id = request.GET.get('node_id')
        node_object = Nodes.objects.get(id=node_id)
        file_data = node_object.python_code

        output_dictionary = {'file_data': file_data}
        return ResponseParser.getParsedSuccessMessage(output_dictionary, '200',
                                                        'Node code loaded successfully.')
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Something went wrong: ' + str(e))



## API to get formatted data of the project
def load_project_data(request):
    uid = request.POST.get('uid', '')
    try:
        user_profile = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')

    try:
        project_id = request.GET.get('project_id')
        project_details = Project.objects.filter(id=project_id)
        project_details_list = []
        for project_detail in project_details:
            project_details_list.append(project_detail.to_dict())
        return ResponseParser.getParsedSuccessMessage(project_details_list, '200',
                                                        'Project details loaded successfully.')
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Something went wrong: ' + str(e))




