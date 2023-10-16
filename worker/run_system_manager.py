import os
import requests
import subprocess
from Utils.network_connect import *
import time
from Utils.constants import *
import Utils.utils as utils
def fetch_projects_from_api():
    project_data_array = load_project_array_waiting()
    utils.logger.info(f"Fetched {len(project_data_array)} projects.")
    return project_data_array


def get_existing_project_names():
    try:
        with open("existing_projects.txt", "r") as f:
            return f.read().splitlines()
    except FileNotFoundError:
        utils.logger.error("existing_projects.txt file not found. Returning an empty list.")
        return []

def save_existing_projects(project_names_array):
    with open("existing_projects.txt", "w") as f:
        for project_name in project_names_array:
            f.write(f"{project_name}\n")
    utils.logger.info(f"Saved {len(project_names_array)} existing projects to existing_projects.txt.")


def create_service_file(project_name, memory_limit=512, vcpu_allocation=0.5):
    cpu_percent = int(vcpu_allocation * 100 / CURRENT_SERVER_VCPU)
    content = SERVICE_TEMPLATE.format(project_name=project_name, memory_limit=memory_limit, cpu_percent=cpu_percent)
    with open(f"{SERVICE_DIRECTORY}WA{project_name}.service", "w") as f:
        f.write(content)
    utils.logger.info(f"New Service file for {project_name} created.")

def delete_service_file(project_name):
    try:
        os.remove(f"{SERVICE_DIRECTORY}WA{project_name}.service")
        utils.logger.info(f"Service file for {project_name} deleted.")
    except:
        utils.logger.error(f"Error deleting service file for {project_name}.")


def manage_service(action, project_name):
    service_name = project_name + ".service"
    subprocess.run(["sudo", "systemctl", action, service_name])
    utils.logger.info(f"Ran {action} service for {service_name}.")


while True:
    project_data_array = fetch_projects_from_api()
    api_project_names = {project['project_key'] for project in project_data_array}
    existing_projects = set(get_existing_project_names())
    new_projects = api_project_names - existing_projects
    removed_projects = existing_projects - api_project_names

    restart_projects = {project['project_key'] for project in project_data_array if str(project.get('refresh_status')) == "1"}

    for project_name in new_projects:
        ##get project_dict from project_data_array
        try:
            project_dict = [project for project in project_data_array if project['project_key'] == project_name][0]
            memory_allocation = project_dict.get('memory_allocated_in_mb')
            cpu_allocation = project_dict.get('cpu_allocated_in_vcpu')
            create_service_file(project_name, memory_allocation, cpu_allocation)
        except Exception as e:
            print("Error creating service file for project: " + str(e))
            create_service_file(project_name)

    for project in removed_projects:
        delete_service_file(project)

    subprocess.run(["sudo", "systemctl", "daemon-reload"])
    utils.logger.info("systemctl daemon reloaded.")

    for project_key in new_projects:
        manage_service("start", "WA"+project_key)

    for project_key in removed_projects:
        manage_service("stop", "WA"+project_key)

    for project_key in restart_projects:
        manage_service("restart", "WA"+project_key)

        update_project_refresh(project_key)
        utils.logger.info(f"Restart status updated for {project_key}.")

    save_existing_projects(api_project_names)

    time.sleep(30)
