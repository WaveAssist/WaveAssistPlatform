import threading
import time
from Engine.ProjectManager import ProjectManager
from Utils.network_connect import *

## This is the main file that will be run on the server.


## First: Call get_projects API
project_data_array = load_project_array_waiting()

utils.logger.info(str(project_data_array))

## Second: For each project, start the project manager.x
managers_array = []
for project_dict in project_data_array:
    project_key = project_dict['project_key']
    manager = ProjectManager(project_key)
    manager.get_started()



if __name__ == '__main__':
    ## Third: Keep printing the status of the project manager.
    while True:
        try:

            for project_manager in managers_array:
                project_manager.print_all_nodes_statuses()
                ## Fourth: If the status is not running, then tell the project manager to make changes.
                if not project_manager.is_healthy():
                    utils.logger.error(f'Project "{project_manager.project_key}" is not running, fixing things..')
                    project_manager.fix_things()
                    project_manager.print_all_nodes_statuses()

            ## Fifth: Check if the data from the load_project_array_waiting is changed.
            new_project_data_array = load_project_array_waiting()
            utils.manage_data_update(new_project_data_array, managers_array)

            time.sleep(60)

        except Exception as e:
            utils.logger.error("Exception in run_engine: " + str(e))
            continue

