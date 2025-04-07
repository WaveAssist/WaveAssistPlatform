##PYTHON IMPORTS
import os
from Utils.Logger import Logger
from Utils.constants import *
import json
import requests
##Logger
logger = Logger(account_key=ACCOUNT_KEY)

BASE_URL = 'https://api.waveassist.io'

##ToDo: Check if this function handles all cases.
def generate_flow_layers(dependencies_dict):
    try:
        layers = []
        initial_layer = [key for key, value in dependencies_dict.items() if not value]
        layers.append(initial_layer)

        # Keep track of processed elements
        processed = set(initial_layer)
        while True:
            next_layer = []
            for key, value in dependencies_dict.items():
                if key not in processed and all(dep in processed for dep in value):
                    next_layer.append(key)

            if not next_layer:
                break
            layers.append(next_layer)
            processed.update(next_layer)
        return layers
    except Exception as e:
        logger.error("Error in generate_flow_layers: " + str(e))
        return []



def start_pre_initialization():
    logger.info("✅ Running start pre initialization... This should run only once!")
    ##Get Data for Key for pip, call api
    try:

        url = f"{BASE_URL}/fetch_config?uid={ACCOUNT_ID}&account_id={ACCOUNT_ID}"
        response_dict = requests.get(url).json()
        config_data = response_dict.get("data", {})
        pip_requirements_array = config_data.get("pip_requirements_array_json", [])
        for pip_requirement in pip_requirements_array:
            try:
                package_name = pip_requirement.get("package_name")
                package_version = pip_requirement.get("package_version")
                if package_version:
                    os.system(f"pip install -U {package_name}=={package_version}")
                else:
                    os.system(f"pip install -U {package_name}")
            except Exception as e:
                logger.error(f"Error in installing package, skipping: {pip_requirement} - {e}")
    except Exception as e:
        logger.error("Error in start_pre_initialization: " + str(e))
        return None
    logger.info("✅ Finished start pre initialization... This should run only once!")

