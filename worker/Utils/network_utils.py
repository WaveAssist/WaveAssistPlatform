import requests
from Utils.constants import *
from Utils.config import *
import os
import json
import Utils.utils as utils
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)




def call_api(url, data_dict, files_dict=None):
    ##Calling the API here
    # Generate files using = files = {'data_file': open(data_path,'rb')}

    try:
        if files_dict is None:
            response_of_api = requests.post(url,
                                verify=False,
                                data = data_dict,
                                timeout=TIMEOUT_DURATION)
        else:
            response_of_api = requests.post(url,
                                files=files_dict,
                                verify=False,
                                data = data_dict,
                                timeout=TIMEOUT_DURATION)

        response_code = str(response_of_api.status_code)
        if response_code == '200':
            response_json = response_of_api.json()
            if response_code == '200' and response_json['success'] == '1':
                return True, response_json
            else:
                try:
                    error_message = response_json['message']
                except:
                    error_message = ""
                return False,'Error, success-0-main-data, Error: ' + error_message
        else:
            response_message = str(response_of_api.text)
            if len(response_message) > 50:
                response_message = response_message[:50]
            return False,response_message
    except Exception as e:
        response_message = str(e)[:50]
        return False,response_message


def check_network():
    try:
        request = requests.get(BASE_URL, timeout=TIMEOUT_DURATION)
        return True
    except Exception as e:
        utils.logger.error("No internet connection: " + str(e))
        return False
