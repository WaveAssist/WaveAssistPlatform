import json
import uuid
from django.shortcuts import render
from .models import *
from .Utils.responseParser import ResponseParser
import pandas as pd
from io import StringIO as StringIO
from .Utils.constants import *
import WaveAssistApiApp.Utils.utils as utils
import WaveAssistApiApp.Utils.validator as validator
from datetime import datetime, timedelta
import requests


def fetch_log_job_names(request): ##Test Case Pending
    response = requests.get(
        LOKI_URL + '/loki/api/v1/label/job/values'
    )
    try:
        response_dict = response.json()
        options_array = response_dict['data']
        output_data = {
            'job_names': options_array
        }
        return ResponseParser.getParsedSuccessMessage(output_data, '200', 'Logs fetched successfully')
    except Exception as e:
        print("Error fetching job names: " + str(e))


def fetch_logs(request): ##Test Case Pending
    success, message, user_object, project_object = validator.validate_user_and_project(request,
                                                                                        access_level_gte=READ_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    node_key = request.POST.get('node_key', '')
    if node_key != '':
        try:
            node_object = Nodes.objects.get(node_key=node_key, project_object=project_object)
        except:
            return ResponseParser.getParsedErrorMessage('Node not found.')

    job_name = request.POST.get('job_name', '')
    if job_name == '':
        return ResponseParser.getParsedErrorMessage('Job name is required.')

    limit = 5000
    # Handle start_datetime and end_datetime
    start_datetime = request.POST.get('start_datetime')
    end_datetime = request.POST.get('end_datetime')

    # If start_datetime is not provided, set it to 1 year ago
    if not start_datetime:
        start_datetime = datetime.now() - timedelta(days=365)
        limit = 100
    else:
        start_datetime = datetime.fromisoformat(start_datetime)

    # If end_datetime is not provided, set it to now
    if not end_datetime:
        end_datetime = datetime.now()
        limit = 100
    else:
        end_datetime = datetime.fromisoformat(end_datetime)

    # Convert datetime to nanoseconds for Loki API
    start_ts = int(start_datetime.timestamp() * 1e9)
    end_ts = int(end_datetime.timestamp() * 1e9)

    query = f'{{job="{job_name}"'
    if node_key:
        query += f', node="{node_key}"'
    query += '}'

    response = requests.get(
        LOKI_URL + '/loki/api/v1/query_range',
        params={
            'query': query,
            'start': start_ts,
            'end': end_ts,
            'limit': limit,
            'direction': 'backward'  # Fetch logs in reverse order (latest logs first)
        }
    )

    try:
        response_dict = response.json()
        result_array = response_dict['data']['result']
    except:
        return ResponseParser.getParsedErrorMessage('Error fetching logs.')

    logs = []
    for result_dict in result_array:
        try:
            all_values = result_dict['values']
            for values_array in all_values:
                try:
                    log_message = values_array[1]
                    if log_message != "":
                        log_dict = {
                            'log': log_message,
                            'timestamp': datetime.fromtimestamp(int(values_array[0])/1000000000).strftime('%Y-%m-%d %H:%M:%S')
                        }
                        logs.append(log_dict)
                except:
                    pass
        except Exception as e:
            print("Error in fetching logs: ", e)

    output_dict = {
        'logs': logs
    }

    return ResponseParser.getParsedSuccessMessage(output_dict, '200', 'Logs fetched successfully')
