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
import re

import boto3
from django.http import JsonResponse
from datetime import datetime, timedelta
import pytz
from urllib.parse import unquote


# Initialize the CloudWatch Logs client
client = boto3.client('logs',
                        aws_access_key_id='REMOVED_CREDENTIAL',
                        aws_secret_access_key='REMOVED_CREDENTIAL',
                      region_name='us-east-1')  # Replace 'your-region' with the appropriate AWS region


def fetch_log_job_names(request): ##Test Case Pending
    options_array = utils.get_all_loki_jobs()
    output_data = { 'job_names': options_array  }
    return ResponseParser.getParsedSuccessMessage(output_data, '200', 'Logs fetched successfully')


def fetch_logs_from_aws(start_datetime, end_datetime, log_group_name, filter_pattern):

    log_array = []
    previous_next_token = ''
    while True:
        # Fetch logs with filter pattern and pagination token
        params = {
            'logGroupName': log_group_name,
            'startTime': start_datetime,
            'endTime': end_datetime,
            'filterPattern': filter_pattern,
        }
        if previous_next_token:
            params['nextToken'] = previous_next_token

        response = client.filter_log_events(**params)
        # Process log events
        events = response['events']
        for event in events:
            log_array.append({
                'timestamp': event['timestamp'],
                'log': event['message']
            })

        # Check if there is a nextToken for pagination
        next_token = response.get('nextToken')
        print(f"Next Token: {next_token}")
        if not next_token or next_token == previous_next_token:
            break  # No more logs to fetch, exit the loop
        else:
            previous_next_token = next_token

    log_array = sorted(log_array, key=lambda x: x['timestamp'], reverse=True)
    return log_array



def fetch_logs(request):
    # Validate user and project
    success, message, user_object, project_object = validator.validate_user_and_project(
        request, access_level_gte=READ_GTE
    )
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    # Parameters
    log_group_name = request.POST.get('log_group_name', '/ecs/WaveAssistWorkerTasks')
    node_key_csv = request.POST.get('node_key_csv')


    # Construct filter_pattern
    if node_key_csv:
        # Split CSV into a list of node keys
        node_key_array = node_key_csv.split(',')
        node_key_array = [node_key.strip() for node_key in node_key_array if node_key]

        # Construct OR conditions for node_key
        node_key_conditions = " || ".join([f'$.extra.node_key = "{node_key}"' for node_key in node_key_array])

        # Combine project_key with OR conditions
        filter_pattern = f'{{ $.extra.project_key = "{project_object.project_key}" && ({node_key_conditions}) }}'
    else:
        filter_pattern = f'{{ $.extra.project_key = "{project_object.project_key}" }}'

    print(f"Filter Pattern: {filter_pattern}")
    next_token = None
    all_logs_array = []
    hours_to_fetch = 1

    try:
        while(True):
            start_datetime = int((datetime.now(pytz.UTC) - timedelta(hours=hours_to_fetch)).timestamp() * 1000)
            end_datetime = int((datetime.now(pytz.UTC) + timedelta(hours=hours_to_fetch)).timestamp() * 1000)
            log_array = fetch_logs_from_aws(start_datetime, end_datetime, log_group_name, filter_pattern)
            all_logs_array.extend(log_array)
            print(len(all_logs_array))
            if len(all_logs_array) <= 10:
                hours_to_fetch += 3
            else:
                break
            if hours_to_fetch >= 24:
                break
        ##Limit return logs to 500
        ##sort all_logs_array
        all_logs_array = sorted(all_logs_array, key=lambda x: x['timestamp'], reverse=True)
        all_logs_array = all_logs_array[:500]
        output_dict = { 'logs': all_logs_array }
        return ResponseParser.getParsedSuccessMessage(output_dict, '200', 'Logs fetched successfully')

    except Exception as e:
        return ResponseParser.getParsedErrorMessage(f"Failed to fetch logs: {str(e)}")

