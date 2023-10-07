import time
from Engine.NodeThread import NodeThread
import Utils.utils as utils
import Utils.network_connect as network_connect
from Engine.MongoManager import MongoManager
from Utils.constants import *

# Thread Manager class
class ProjectManager(object):

    def __init__(self, project_key):
        self.project_key = project_key
        self.nodes_dict = {}
        self.mongo_manager = MongoManager(project_key)

    def load_node_array(self):
        node_array = network_connect.load_node_array(self.project_key)
        return node_array


    def setup_project_file(self):
        project_file_content = network_connect.download_project_file_data(self.project_key)
        utils.write_to_file(self.project_key, project_file_content)
        return



    def refresh_project(self):
        ##Refresh project

        self.delete_project()

        self.get_started()

        ##Update backend
        network_connect.update_project_refresh(self.project_key)


    def delete_project(self):
        ##Delete project
        self.stop_and_remove_all_nodes()
        utils.delete_file(self.project_key)



    def get_started(self):
        ##Setup project] file
        self.setup_project_file()

        ##Load node array
        node_array = self.load_node_array()

        ##Create & start nodes
        for node_dict in node_array:
            node_key = node_dict['node_key']
            sleep_duration = float(node_dict['sleep_duration'])
            input_data_array = node_dict['input_data_array']
            output_data_array = node_dict['output_data_array']
            input_data_array.append({"key":self.project_key + INTEGRATIONS_SUFFIX_KEY})

            node = self.create_node(node_key, sleep_duration, input_data_array, output_data_array)
            self.start_node(node)


    def start_node_for_key(self, input_node_key):
        ##Setup project] file
        self.setup_project_file()

        ##Load node array
        node_array = self.load_node_array()

        ##Create & start nodes
        for node_dict in node_array:
            node_key = node_dict['node_key']
            if node_key == input_node_key:
                sleep_duration = float(node_dict['sleep_duration'])
                input_data_array = node_dict['input_data_array']
                output_data_array = node_dict['output_data_array']
                input_data_array.append({"key":self.project_key + INTEGRATIONS_SUFFIX_KEY})
                node = self.create_node(node_key, sleep_duration, input_data_array, output_data_array)
                self.start_node(node)
            else:
                continue

    def create_node(self, node_key, sleep_duration, input_data_array, output_data_array):
        if node_key in self.nodes_dict.keys():
            utils.logger.warning(f'Node "{node_key}" already exists')
            self.stop_and_remove_node(node_key)

        utils.logger.info(f'Creating node "{node_key}"')
        node = NodeThread(self.project_key, node_key, sleep_duration, input_data_array, output_data_array, self.mongo_manager)
        self.nodes_dict[node_key] = node
        utils.logger.info(f'Node "{node_key}" created')
        return node


    def is_healthy(self):
        for node_key, node in self.nodes_dict.items():
            if node.is_alive():
                continue
            else:
                utils.logger.warning(f'Node "{node_key}" is not running')
                return False
        return True


    def fix_things(self):
        network_connect.update_project_refresh(self.project_key, "1")

    def start_node(self,node):
        if node:
            if node.is_alive():
                utils.logger.warning(f'Node "{node.node_key}" is already running')
                return True
            else:
                node.start()
                utils.logger.info(f'Node "{node.node_key}" started')
                return True
        else:
            utils.logger.warning('Node does not exist')
            return False


    def stop_node(self, node_key):
        thread = self.nodes_dict.get(node_key)
        if thread:
            if thread.is_alive():
                thread.stop()
                thread.join()
                utils.logger.info(f'Node "{node_key}" stopped')
            else:
                utils.logger.warning(f'Node "{node_key}" is not running')
        else:
            utils.logger.warning(f'Node "{node_key}" does not exist')



    def stop_and_remove_node(self, node_key):
        thread = self.nodes_dict.get(node_key)
        if thread:
            if thread.is_alive():
                thread.stop()
                thread.join()
                del self.nodes_dict[node_key]
                utils.logger.info(f'Node "{node_key}" stopped')
            else:
                utils.logger.warning(f'Node "{node_key}" is not running')
        else:
            utils.logger.warning(f'Node "{node_key}" does not exist')


    def stop_and_remove_all_nodes(self):
        all_keys = list(self.nodes_dict.keys())
        for node_key in all_keys:
            self.stop_and_remove_node(node_key)
        utils.logger.info('All nodes stopped')


    def print_node_status(self, node_key):
        thread = self.nodes_dict.get(node_key)
        if thread:
            if thread.is_alive():
                utils.logger.info(f'Node "{node_key}" is running')
            else:
                utils.logger.info(f'Node "{node_key}" is stopped')
        else:
            utils.logger.warning(f'Node "{node_key}" does not exist')

    def print_all_nodes_statuses(self):
        utils.logger.info("Printing all nodes statuses for project status...")
        for node_key, thread in self.nodes_dict.items():
            if thread.is_alive():
                utils.logger.info(f'Project Status: Node "{node_key}" is running')
            else:
                utils.logger.info(f'Project Status: Node "{node_key}" is stopped')

