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

def fetch_log_job_names(request): ##Test Case Pending
    options_array = utils.get_all_loki_jobs()
    output_data = { 'job_names': options_array  }
    return ResponseParser.getParsedSuccessMessage(output_data, '200', 'Logs fetched successfully')


def fetch_logs(request): ##Test Case Pending
    success, message, user_object, project_object = validator.validate_user_and_project(request, access_level_gte=READ_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    selected_jobs = []
    jobs_array = utils.get_all_loki_jobs()
    job_name = request.POST.get('job_name', 'WaveAssistEC2Tasks')
    node_key_csv = request.POST.get('node_key_csv', '')
    node_key_array = node_key_csv.split(',')
    node_key_array = [node_key.strip() for node_key in node_key_array]

    project_node_keys = list(project_object.nodes_set.filter(is_enabled=True).values_list('node_key', flat=True))
    for node_key in node_key_array:
        if node_key not in project_node_keys:
            return ResponseParser.getParsedErrorMessage('Node Key not found in project')

    for job in jobs_array:
        if job_name.lower() in job.lower():
            selected_jobs.append(job)

    # Handle start_datetime and end_datetime
    start_datetime = request.POST.get('start_datetime')
    end_datetime = request.POST.get('end_datetime')
    if not start_datetime:
        start_datetime = datetime.now() - timedelta(days=3)
    else:
        start_datetime = datetime.fromisoformat(start_datetime)
    if not end_datetime:
        end_datetime = datetime.now() + timedelta(days=3)
    else:
        end_datetime = datetime.fromisoformat(end_datetime)

    # Convert datetime to nanoseconds for Loki API
    start_ts = int(start_datetime.timestamp() * 1e9)
    end_ts = int(end_datetime.timestamp() * 1e9)

    query = utils.build_loki_query(selected_jobs, node_key_array)

    logs = utils.fetch_loki_logs(query, start_ts, end_ts)

    ##Sort by timestamp field in logs
    logs = sorted(logs, key=lambda x: x['timestamp'])

    output_dict = {'logs': logs }

    return ResponseParser.getParsedSuccessMessage(output_dict, '200', 'Logs fetched successfully')
