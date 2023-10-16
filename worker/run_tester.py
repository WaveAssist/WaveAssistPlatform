import os
import requests
import subprocess
from Utils.network_connect import *
import time
from Utils.constants import *
import Utils.utils as utils


##ToDo: Upgrade tester to become a custom project manager.

def upload_test_results(node_key, output_string):
    return update_node_test_results(node_key, output_string, '0')

def fetch_test_nodes():
    success, node_array = load_all_test_nodes()
    utils.logger.info(f"Fetched {len(node_array)} test nodes.")
    return node_array

def run_command(command_array):
    output_string = ""
    timeout = 15
    try:
        # Set timeout to 15 seconds
        completed_process = subprocess.run(command_array, capture_output=True, text=True, timeout=timeout)

        # Access stdout and stderr
        stdout = completed_process.stdout
        stderr = completed_process.stderr

        # Print logs or process them further
        output_string = output_string + "=== STDOUT ===" + '\n'
        output_string = output_string + stdout + '\n'
        output_string = output_string + "=== STDERR ===" + '\n'
        output_string = output_string + stderr + '\n'

    except subprocess.TimeoutExpired as e:
        output_string = output_string + "The function finished within:  " + str(timeout) + ' seconds. ' + '\n'
        output_string = output_string + "=== STDOUT ===" + '\n'
        try:
            output_string = output_string + (e.stdout.decode('utf-8') if e.stderr else "No STDOUT") + '\n'
        except:
            output_string = output_string + "No STDOUT" + '\n'

        output_string = output_string + "=== STDERR ===" + '\n'

        try:
            output_string = output_string + (e.stderr.decode('utf-8') if e.stdout else "No STDERR") + '\n'
        except:
            output_string = output_string + "No STDERR" + '\n'
        
    except Exception as e:
        output_string = output_string + "Error in function: " + str(e) + '\n'

    return output_string

while True:
    try:
        test_nodes_array = fetch_test_nodes()
        for node_dict in test_nodes_array:
            project_key = node_dict['project_key']
            node_key = node_dict['node_key']
            command_array = ["/home/ubuntu/WaveAssistEngine/waveenv/bin/python3", "-u", "run_project.py", project_key, node_key]
            utils.logger.info(f"Running {command_array} for {node_key}.")
            output_string = run_command(command_array)
            upload_test_results(node_key, output_string)
            utils.logger.info(f"Completed {command_array} for {node_key}.")
        time.sleep(5)
    except Exception as e:
        utils.logger.error(f"Error with tester: {e}")
        time.sleep(5)
