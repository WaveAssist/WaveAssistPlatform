import json
import uuid
from http.client import responses

from django.shortcuts import render
from twisted.spread.pb import respond

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
from WaveAssistApiApp import deployment_views
import waveassist

# Initialize the CloudWatch Logs client
client = boto3.client('logs',
                        aws_access_key_id='REMOVED_CREDENTIAL',
                        aws_secret_access_key='REMOVED_CREDENTIAL',
                      region_name='us-east-1')  # Replace 'your-region' with the appropriate AWS region


def fetch_logs_from_aws(start_datetime, end_datetime, log_group_name, filter_pattern):
    log_array = []
    previous_next_token = ''
    while True:
        params = {
            'logGroupName': log_group_name,
            'startTime': start_datetime,
            'endTime': end_datetime,
            'filterPattern': filter_pattern
        }
        if previous_next_token:
            params['nextToken'] = previous_next_token

        response = client.filter_log_events(**params)
        events = response['events']
        for event in events:
            try:
                log_json = json.loads(event['message'])
                log_array.append({
                    'timestamp': log_json['asctime'],
                    'log': log_json['message']
                })
            except json.JSONDecodeError:
                continue

        next_token = response.get('nextToken')
        if not next_token or next_token == previous_next_token:
            break
        previous_next_token = next_token

    return log_array


def fetch_logs(request):
    success, message, user_object, project_object = validator.validate_user_and_project(
        request, access_level_gte=READ_GTE
    )
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    # Parameters
    log_group_name = request.POST.get('log_group_name', '/ecs/WaveAssistWorkerTasks')
    node_key_csv = request.POST.get('node_key_csv')

    filter_pattern = utils.generate_filter_pattern(node_key_csv, project_object)

    try:
        now_utc = datetime.now(pytz.UTC)
        end_datetime = int(now_utc.timestamp() * 1000)
        current_start_datetime = end_datetime
        all_logs_array = []
        increment_minutes = 15
        max_back_hours = 24
        min_logs = 10
        max_logs = 500

        while len(all_logs_array) < min_logs and (end_datetime - current_start_datetime) < (max_back_hours * 3600 * 1000):
            increment_ms = increment_minutes * 60 * 1000
            new_start_datetime = max(end_datetime - (max_back_hours * 3600 * 1000), current_start_datetime - increment_ms)
            new_logs = fetch_logs_from_aws(new_start_datetime, current_start_datetime, log_group_name, filter_pattern)
            if new_logs:
                all_logs_array.extend(new_logs)
            current_start_datetime = new_start_datetime
            if not new_logs and increment_minutes < 60:
                increment_minutes *= 2

        # Sort and trim to max_logs after all fetching
        all_logs_array = sorted(all_logs_array, key=lambda x: x['timestamp'], reverse=True)[:max_logs]
        output_dict = { 'logs': all_logs_array }
        return ResponseParser.getParsedSuccessMessage(output_dict, '200', 'Logs fetched successfully')

    except Exception as e:
        return ResponseParser.getParsedErrorMessage(f"Failed to fetch logs: {str(e)}")



def fetch_installed_packages(request):
    #TCW
    request.POST = request.POST.copy()
    request.POST['code_to_run'] = FETCH_INSTALL_PACKAGES_CODE
    response = deployment_views.run_code(request)
    try:
        response_str = response.content.decode('utf-8')
        response_dict = json.loads(response_str)
        result = response_dict.get("data", {}).get("result")
    except:
        return ResponseParser.getParsedErrorMessage('Failed to fetch installed packages')

    if result is None:
        return ResponseParser.getParsedErrorMessage('Failed to fetch installed packages')

    waveassist.init(request.POST.get('uid'), request.POST.get('project_key'))
    packages_array = waveassist.fetch_data('installed_packages')

    # STEP 1: Get base package names
    base_packages = utils.get_base_package_names()

    # STEP 2: Filter out base packages
    filtered_packages = [
        pkg for pkg in packages_array
        if pkg["package_name"].lower() not in base_packages
    ]

    try:
        account_object = Account.objects.get(account_uid=request.POST.get('uid'))
        account_object.pip_requirements_array_json = json.dumps(filtered_packages)
        account_object.save()
    except:
        return ResponseParser.getParsedErrorMessage('Account not found or not authorized')

    output_dict = {
        'packages_array': filtered_packages
    }
    return ResponseParser.getParsedSuccessMessage(output_dict, '200', 'Packages fetched successfully')


def code_to_run_uninstall_package(package_to_uninstall):
    code_to_run = '''
def run_task():
    import subprocess
    import sys
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", " ''' + package_to_uninstall + ''' "], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False
    '''
    return code_to_run


def uninstall_package(request): ##TCW
    request.POST = request.POST.copy()
    package_name = request.POST.get('package_name', '')
    package_version = request.POST.get('package_version', None)
    if package_version:
        package_to_uninstall = f"{package_name}=={package_version}"
    else:
        package_to_uninstall = package_name
    code_to_run = code_to_run_uninstall_package(package_to_uninstall)
    request.POST['code_to_run'] = code_to_run
    response = deployment_views.run_code(request)
    return ResponseParser.getParsedSuccessMessage({}, '200', 'Package uninstallation started successfully')


def code_to_run_install_package(package_to_install):
    code_to_run = '''
def run_task():
    import subprocess
    import sys
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", " ''' + package_to_install + ''' "], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False
    '''
    return code_to_run


def install_package(request):
    request.POST = request.POST.copy()
    package_name = request.POST.get('package_name')
    package_version = request.POST.get('package_version', None)
    if package_version:
        package_to_install = f"{package_name}=={package_version}"
    else:
        package_to_install = package_name
    request.POST['code_to_run'] = code_to_run_install_package(package_to_install)
    response = deployment_views.run_code(request)
    return ResponseParser.getParsedSuccessMessage({}, '200', 'Package installation started successfully')

def code_to_run_upgrade_package(package_to_install):
    code_to_run = f'''
def run_task():
    import subprocess
    import sys
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "{package_to_install}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False
    '''
    return code_to_run


def reinstall_package(request):
    request.POST = request.POST.copy()
    package_name = request.POST.get('package_name')
    request.POST['code_to_run'] = code_to_run_upgrade_package(package_name)
    response = deployment_views.run_code(request)
    return ResponseParser.getParsedSuccessMessage({}, '200', 'Package re-installation started successfully')
