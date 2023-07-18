from django.shortcuts import render
from .models import *
from .Utils.responseParser import ResponseParser
from WaveAssistApiApp.Utils.MongoManager import MongoManager
# Create your views here.
import pandas as pd
from io import StringIO as StringIO
from .Utils.constants import *
from .Utils.firebase_auth import verify_token

mongo_manager = MongoManager()

def index(request):
    return ResponseParser.getParsedSuccessMessage([],"S01","Hello, world. You're at the WaveAssist index...")


def login(request):
    jwt_token = request.POST.get('jwt_token', '')
    uid = verify_token(jwt_token)
    print(uid)
    if uid == None:
        return ResponseParser.getParsedErrorMessage('Invalid token')

    try:
        client_object = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')

    ##Fetch all projects of the client, as one to many key
    project_array = Project.objects.filter(client=client_object)
    project_dict_array = []
    for project_object in project_array:
        project_dict_array.append(project_object.get_dict())
    output_dictionary = {'project_array': project_dict_array}
    output_dictionary['client_data'] = client_object.get_dict()
    return ResponseParser.getParsedSuccessMessage(output_dictionary, '200', 'Login successful.')


## API to get formatted data of the project
def load_project_data(request):
    uid = request.POST.get('uid', '')
    try:
        client_object = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')


    try:
        project_key = request.POST.get('project_key', '')
        project_object = Project.objects.get(project_key=project_key)
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Project not found.')

    try:
        ##Load IOData with type as 1 and project_key as project_key
        io_data_array = IOData.objects.filter(project__project_key=project_key, output_type__in=[1,2])
        ##Fetch all IO Data from Mongo

        data_dict = {}
        data_format_array = []
        for io_data_object in io_data_array:
            data_array = mongo_manager.fetch_data(io_data_object.key)
            data_array = MongoManager.remove_id_from_array(data_array)
            if io_data_object.output_type == 2:
                data_format_array = data_array
            else:
                data_dict[io_data_object.key] = data_array

        output_dict = {'data_dict': data_dict, 'data_format_array': data_format_array}
        return ResponseParser.getParsedSuccessMessage(output_dict, '200', 'Project data loaded successfully.')

    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Some issue with IOData' + str(e))



def set_data_for_key(request):

    uid = request.POST.get('uid', '')
    try:
        client_object = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')

    io_data_key = request.POST.get('io_data_key', '')
    try:
        io_data_object = IOData.objects.get(key=io_data_key, project__client=client_object)
        if io_data_object is None:
            return ResponseParser.getParsedErrorMessage('IOData not found!')
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('IOData not found!')
    csv_data = str(request.POST.get('csv_data', ''))

    try:
        pd_data = pd.read_csv(StringIO(csv_data))
        ##Save in mongo db
        mongo_manager = MongoManager()
        success = mongo_manager.replace_data_as_dataframe(io_data_key, pd_data)
        mongo_manager.close_connection()
        if not success:
            return ResponseParser.getParsedErrorMessage('Something went wrong with data saving')

        ##Response
        output_dictionary = {'io_data_key': io_data_key}
        return ResponseParser.getParsedSuccessMessage(output_dictionary, '200',
                                                        'Data saved successfully.')
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Something went wrong with data saving: ' + str(e))


