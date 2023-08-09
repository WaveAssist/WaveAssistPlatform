import threading
import time
from Engine.ProjectManager import ProjectManager
from Utils.network_connect import *
import sys

try:
    project_key = str(sys.argv[1])
except:
    utils.logger.error('Please provide a project key.')
    sys.exit()


## Second: For project, start the project manager.x

utils.logger.info("Starting project manager for project: " + project_key)
project_manager = ProjectManager(project_key)
project_manager.get_started()

if __name__ == '__main__':
    ## Third: Keep printing the status of the project manager.
    while True:
        try:
            project_manager.print_all_nodes_statuses()
            ## Fourth: If the status is not running, then tell the project manager to make changes.
            if not project_manager.is_healthy():
                utils.logger.error(f'Project "{project_manager.project_key}" is not running, fixing things..')
                project_manager.fix_things()
                project_manager.print_all_nodes_statuses()
            time.sleep(60)
        except Exception as e:
            utils.logger.error("Exception in run_engine: " + str(e))
            continue