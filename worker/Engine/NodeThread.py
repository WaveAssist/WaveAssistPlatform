import threading
import time
import importlib
import Utils.utils as utils
from Engine.MongoManager import MongoManager

# Custom Thread class
import pandas as pd
from Utils.Timer import Timer


class NodeThread(threading.Thread):
    def __init__(self, project_key, node_key, sleep_duration,  input_data_array, output_data_array, flows_array):
        super(NodeThread, self).__init__()
        self.project_key = project_key
        self.node_key = node_key
        self.sleep_duration = sleep_duration
        self.input_data_array = input_data_array
        self.output_data_array = output_data_array
        self.flows_array = flows_array


    def manage_output(self, output_data, output_dict, mongo_manager):
        try:
            if output_data is None:
                return True
            output_key = str(output_dict['key'])
            action_type = int(output_dict['action_type'])

            if action_type == 0: ##Replace
                return mongo_manager.replace_data_as_dataframe(output_key, output_data)
            return True
        except Exception as e:
            utils.logger.error("Exception in manage_output for: " + str(self.node_key) + " + Error: " + str(e))
            return False


    def get_input(self, mongo_manager):
        ##Get input data from mongo based on keys in input_data_array
        try:
            input_keys_array = [obj['key'] for obj in self.input_data_array]
            input_dict = mongo_manager.fetch_data_as_dataframe_for_array(input_keys_array)
            input_array = [input_dict.get(io_key, pd.DataFrame()) for io_key in input_keys_array]
            return input_array
        except Exception as e:
            utils.logger.error("Exception in get_input for: " + str(self.node_key) + " + Error: " + str(e))
            return []






    def run(self):
        utils.logger.info("Starting Node: " + str(self.node_key))
        timer = Timer(str(self.node_key))
        # Import the module dynamically
        project_module = importlib.import_module(f"Projects.{self.project_key}")
        # Get the function dynamically
        project_function = getattr(project_module, self.node_key)

        while True:
            utils.logger.info(str(self.node_key) + " is running")
            timer.start()
            try:
                ##Run this function for each flow
                for flow_dict in self.flows_array:
                    flow_id = flow_dict['id']
                    try:
                        collection = utils.get_collection_key(flow_id, self.project_key)
                        mongo_manager = MongoManager(collection)

                        input_array = self.get_input(mongo_manager)
                        output = project_function(*input_array)

                        output_array = []
                        if len(self.output_data_array) == 1:
                            output_array = [output]
                        if len(self.output_data_array) > 1:
                            output_array = list(output)

                        ##Manage output here.
                        for i in range(0,len(output_array)):
                            actual_output = output_array[i]
                            output_data = self.output_data_array[i]
                            self.manage_output(actual_output, output_data, mongo_manager)

                        utils.logger.info("Code run completed for node: " + str(self.node_key))
                        timer.print_elapsed()
                    except Exception as e:
                        utils.logger.error("Error occured in flow: " + str(flow_id) + " for node: " + str(self.node_key) + ". Error: " + str(e))

            except Exception as e:
                utils.logger.error("Error occured in thread: " + str(self.node_key) + ". Error: " + str(e))

            utils.logger.info("Node: " + str(self.node_key) + " sleeping for: " + str(self.sleep_duration))
            time.sleep(self.sleep_duration) ##ToDo: Adjust to remove the time it took to run all flows.
            utils.logger.info("Node: " + str(self.node_key) + " back on")





