from django.shortcuts import render
from .models import *
from .Utils.responseParser import ResponseParser

# Create your views here.

def index(request):
    return ResponseParser.getParsedSuccessMessage([],"S01","Hello, world. You're at the WaveAssist index...")


#
# ## API to get formatted data of the project
# def load_project_data(request):
#     uid = request.POST.get('uid', '')
#     try:
#         user_profile = Client.objects.get(firebase_uid=uid)
#     except:
#         return ResponseParser.getParsedErrorMessage('User not found')
#
#     try:
#         project_id = request.GET.get('project_id')
#         project_details = Project.objects.filter(id=project_id)
#         project_details_list = []
#         for project_detail in project_details:
#             project_details_list.append(project_detail.to_dict())
#         return ResponseParser.getParsedSuccessMessage(project_details_list, '200',
#                                                         'Project details loaded successfully.')
#     except Exception as e:
#         return ResponseParser.getParsedErrorMessage('Something went wrong: ' + str(e))
#


