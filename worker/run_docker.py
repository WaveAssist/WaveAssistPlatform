import time
import docker
from time import sleep
WORKER_TOKEN = "REMOVED_CREDENTIAL"
BASE_URL = "https://assistapi.wavepredict.com"
TIMEOUT_DURATION = 300
LOAD_ALL_PROJECTS_URL = BASE_URL + "/load_all_projects/"
import requests


def call_api(url, data_dict):
    ##Calling the API here
    # Generate files using = files = {'data_file': open(data_path,'rb')}

    try:
        response_of_api = requests.post(url,
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


def load_all_projects():
    try:
        print("Loading projects data")
        data = {'token': WORKER_TOKEN}
        success,response_data = call_api(LOAD_ALL_PROJECTS_URL,data)
        return success,response_data
    except:
        return False, "Error in loading projects data"


def load_project_array_waiting():
    success,response_data = load_all_projects()
    if not success:
        print("Error in loading projects data")
        while True:
            print("Retrying to load projects data")
            success, response_data = load_all_projects()
            if success:
                break
            sleep(10)
    project_data_array = response_data['data']['project_array']
    return project_data_array





# Other constants and functions are here

def create_container(project_key):
    docker_image = "waveassistengine"
    cpu_limit = 1
    memory_limit = '0.5g'
    container_name = f"engine-container-{project_key}"

    client = docker.from_env()
    try:
        container = client.containers.run(
            docker_image,
            project_key,
            name=container_name,
            mem_limit=memory_limit,
            detach=True
        )
        print(f"Started container for project {project_key}")
        return container
    except Exception as e:
        print(f"Error starting container for project {project_key}: {e}")
        return None

def delete_container(container_name):
    client = docker.from_env()
    try:
        container = client.containers.get(container_name)
        container.stop()
        container.remove()
        print(f"Removed container {container_name}")
    except Exception as e:
        print(f"Error removing container {container_name}: {e}")

# Main loop
while True:
    try:
        project_array = load_project_array_waiting()

        # Get currently running containers where name starts from "engine-container-"
        client = docker.from_env()
        running_containers = [container.name for container in client.containers.list() if container.name.startswith("engine-container-")]
        for project_dict in project_array:
            project_key = project_dict['project_key']
            container_name = f"engine-container-{project_key}"

            # If container is not running, create it
            if container_name not in running_containers:
                create_container(project_key)

        # Delete containers for projects that are no longer in the array
        for container_name in running_containers:
            project_key = container_name.replace("engine-container-", "")
            if project_key not in [project['project_key'] for project in project_array]:
                delete_container(container_name)

    except Exception as e:
        print(f"An error occurred: {e}")

    # Wait for a specified interval before checking again
    time.sleep(300)  # Wait for 5 minutes before checking again
