##PYTHON IMPORTS
import glob
import struct
import collections
import datetime
from multiprocessing import Queue, Pool
##Custom
from Utils.constants import *
from Utils.config import *
from time import sleep
from zipfile import ZipFile

import shutil
import os
import json
from Utils.Logger import Logger
##Logger

logger = Logger()

def write_to_file(project_key, project_file_content):
    try:
        logger.info("Writing project file")
        project_file_content_bytes = project_file_content.encode("utf-8")
        ##Join PROJECTS_FOLDER with project_key and a .py extension
        project_file_path = get_project_file_path(project_key)
        with open(project_file_path, 'wb') as f:
            f.write(project_file_content_bytes)
        logger.info("project file written")
        return True
    except Exception as e:
        logger.error("Error in writing project file: " + str(e))
        return False

def get_project_file_path(project_key):
    return os.path.join(PROJECTS_FOLDER, project_key + ".py")

def delete_file(project_key):
    try:
        logger.info("Deleting project file")
        ##Join PROJECTS_FOLDER with project_key and a .py extension
        project_file_path = get_project_file_path(project_key)
        os.remove(project_file_path)
        logger.info("Project file deleted")
        return True
    except Exception as e:
        logger.error("Error in deleting project file: " + str(e))
        return False



def manage_data_update(new_project_data_array, managers_array):
    ##LOOP between managers_array and new_project_data_array, managers_array has manager objects with value project_key,
    ##If project_key is in both, then check if refresh_status is 1, if yes, then call refresh_project
    ##If project_key is in managers_array but not in new_project_data_array, then call delete_project
    ##If project_key is in new_project_data_array but not in managers_array, then call get_started
    from Engine.ProjectManager import ProjectManager

    for new_project_dict in new_project_data_array:
        new_project_key = new_project_dict['project_key']
        did_find = False
        for manager in managers_array:
            if manager.project_key == new_project_key:
                did_find = True
                if str(new_project_dict['refresh_status']) == '1':
                    logger.info(f"Refreshing project {new_project_key}")
                    manager.refresh_project()

        if not did_find:
            new_manager = ProjectManager(new_project_key)
            new_manager.get_started()
            managers_array.append(new_manager)


    ##Delete projects which are not in the new one
    objects_to_remove = []
    for manager_object in managers_array:
        existing_project_key = manager_object.project_key
        if not any(existing_project_key == new_data['project_key'] for new_data in new_project_data_array):
            manager_object.delete_project()
            objects_to_remove.append(manager_object)

    for manager_object in objects_to_remove:
        managers_array.remove(manager_object)
    # return managers_array

