# import the necessary packages
import Utils.utils
from Utils.config import *
from Utils.constants import *
import Utils.utils as utils
import Utils.network_utils as network_utils
from time import sleep


def load_all_projects():
    try:
        utils.logger.info("Loading projects data")
        data = {'token': WORKER_TOKEN}
        success,response_data = network_utils.call_api(LOAD_ALL_PROJECTS_URL,data)
        return success,response_data
    except:
        return False, "Error in loading projects data"


def load_project_array_waiting():
    success,response_data = load_all_projects()
    if not success:
        utils.logger.error("Error in loading projects data")
        while True:
            utils.logger.info("Retrying to load projects data")
            success, response_data = load_all_projects()
            if success:
                break
            sleep(10)
    project_data_array = response_data['data']['project_array']
    return project_data_array


def download_project_file_data(project_key):
    try:
        utils.logger.info("Downloading project file data")
        data = {'token': WORKER_TOKEN}
        data['project_key'] = project_key
        success,response_data = network_utils.call_api(DOWNLOAD_PROJECT_FILE_DATA_URL,data)
        if success:
            file_data = response_data['data']['file_data']
            return file_data
        else:
            utils.logger.error("Error in response of file data: " + str(response_data))
            return ""
    except Exception as e:
        utils.logger.error("Error in downloading file data: " + str(e))
        return ""


def update_project_refresh(project_key, status='0'):
    try:
        utils.logger.info("Updating project refresh")
        data = {'token': WORKER_TOKEN}
        data['project_key'] = project_key
        data['new_status'] = str(status)
        success,response_data = network_utils.call_api(UPDATE_PROJECT_REFRESH_STATUS,data)
        if success:
            return True
        else:
            utils.logger.error("Error in the response of project refresh api: " + str(response_data))
            return False
    except Exception as e:
        utils.logger.error("Error in project refresh api: " + str(e))
        return False



def load_node_array(project_key):
    try:
        utils.logger.info("Loading projects data")
        data = {'token': WORKER_TOKEN}
        data['project_key'] = project_key
        success,response_data = network_utils.call_api(LOAD_NODE_DATA_URL,data)
        if success:
            node_array = response_data['data']['node_array']
            return node_array
        else:
            utils.logger.error("Error in response of nodes data: " + str(response_data))
            return []

    except Exception as e:
        utils.logger.error("Error in loading nodes data: " + str(e))
        return []
