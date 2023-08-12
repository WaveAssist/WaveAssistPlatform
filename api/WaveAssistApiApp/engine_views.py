import io

from django.shortcuts import render
from .models import *
from .Utils.responseParser import ResponseParser
from .Utils.constants import WORKER_TOKEN
# Create your views here.
import json
import pandas as pd

## API to load client details
def load_all_projects(request):
    worker_token = request.POST.get('token', '')

    if worker_token != WORKER_TOKEN:
        return ResponseParser.getParsedErrorMessage('No access')

    try:
        project_running_status = int(request.POST.get('project_running_status', '1'))
        project_array = Project.objects.filter(running_status=project_running_status)
        project_dict_array = []
        for project_object in project_array:
            project_dict_array.append(project_object.get_dict())
        output_dictionary = {'project_array': project_dict_array}
        return ResponseParser.getParsedSuccessMessage(output_dictionary, '200', 'Project details loaded successfully.')
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Something went wrong: ' + str(e))


## API to load nodes details
def load_node_data(request):

    worker_token = request.POST.get('token', '')
    if worker_token != WORKER_TOKEN:
        return ResponseParser.getParsedErrorMessage('No access')

    project_key = request.POST.get('project_key', '')
    project_object = None
    try:
        project_object = Project.objects.get(project_key=project_key)
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Project not found!')

    try:
        node_array = project_object.node_array.filter(running_status=1)
        node_dict_array = []
        for node_object in node_array:
            node_dict_array.append(node_object.get_dict())
        output_dictionary = {'node_array': node_dict_array}
        return ResponseParser.getParsedSuccessMessage(output_dictionary, '200', 'Node details loaded successfully.')
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Something went wrong: ' + str(e))



def generate_integrations_code_text(project_object):
    python_code_text = ''
    integration_array = project_object.integration_array.all()
    for integration_object in integration_array:
        python_code_text += integration_object.python_code + '\n'
    return python_code_text


def generate_python_code_text(node_array):
    try:
        python_code_text = ''

        for node_object in node_array:
            python_code = node_object.python_code

            input_data_array = node_object.input_data_array.all()
            ##For each IODataObject in input_data_array, add a parameter to the parameters_string with name as key

            parameters_string = ""
            for input_data_object in input_data_array:
                parameters_string += str(input_data_object.key) + ", "


            python_code_text += "def " + node_object.node_key + "(" + parameters_string +  "):\n"
            python_code_text += "    " + python_code.replace("\n", "\n    ") + "\n\n"

            ##Check if python code has a return statement if output_data_array is not empty

            output_data_array = node_object.output_data_array.all()
            if len(output_data_array) > 0 and python_code.find("return") == -1:
                return False, "Python code does not have a return statement for node: " + node_object.node_key


        #Validate if the entire code is proper python code, if not, return error
        try:
            compile(python_code_text, '<string>', 'exec')
        except Exception as e:
            return False, "Error in compiling code: " + str(e)


        return True, python_code_text

    except Exception as e:
        return False, "Error in generate_python_code_text: " + str(e)

## API to get code of the node
def download_project_file_data(request):
    worker_token = request.POST.get('token', '')
    if worker_token != WORKER_TOKEN:
        return ResponseParser.getParsedErrorMessage('No access')

    project_key = request.POST.get('project_key', '')
    project_object = None
    try:
        project_object = Project.objects.get(project_key=project_key)
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Project not found!')

    try:
        node_array = project_object.node_array.filter(running_status=1)
        success, python_code_text = generate_python_code_text(node_array)
        integrations_code_text = generate_integrations_code_text(project_object)
        final_code_text = integrations_code_text + "\n\n" + python_code_text
        if not success:
            return ResponseParser.getParsedErrorMessage('Something went wrong with python code generation: ' + str(python_code_text))

        output_dictionary = {'file_data': final_code_text}
        return ResponseParser.getParsedSuccessMessage(output_dictionary, '200',
                                                        'Node code loaded successfully.')
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Something went wrong: ' + str(e))



def update_project_refresh_status(request):
    worker_token = request.POST.get('token', '')
    if worker_token != WORKER_TOKEN:
        return ResponseParser.getParsedErrorMessage('No access')

    new_status = int(request.POST.get('new_status', '0'))
    project_key = request.POST.get('project_key', '')

    try:
        project_object = Project.objects.get(project_key=project_key)
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Project not found!')

    try:
        project_object.refresh_status = new_status
        project_object.save()
        output_dictionary = {'new_status': new_status}
        return ResponseParser.getParsedSuccessMessage(output_dictionary, '200',
                                                        'Refresh status updated successfully.')
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Something went wrong with refresh status: ' + str(e))



