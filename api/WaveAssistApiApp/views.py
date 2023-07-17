from django.shortcuts import render
from .models import *
from .Utils.responseParser import ResponseParser
from WaveAssistApiApp.Utils.MongoManager import MongoManager
# Create your views here.

mongo_manager = MongoManager()

def index(request):
    return ResponseParser.getParsedSuccessMessage([],"S01","Hello, world. You're at the WaveAssist index...")



## API to get formatted data of the project
def load_project_data(request):
    uid = request.GET.get('uid', '')
    try:
        client_object = Client.objects.get(firebase_uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not found')


    try:
        project_key = request.GET.get('project_key', '')
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


