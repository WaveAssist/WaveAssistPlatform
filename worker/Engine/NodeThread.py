import threading
import time
import importlib
import Utils.utils as utils
# Custom Thread class
import pandas as pd


class NodeThread(threading.Thread):
    def __init__(self, project_key, node_key, sleep_duration,  input_data_array, output_data_array, mongo_manager):
        super(NodeThread, self).__init__()
        self.project_key = project_key
        self.node_key = node_key
        self.sleep_duration = sleep_duration
        self.stop_event = threading.Event()
        self.input_data_array = input_data_array
        self.output_data_array = output_data_array
        self.mongo_manager = mongo_manager


    def manage_output(self,output_data, output_dict):
        try:
            if output_data is None:
                return True
            output_key = str(output_dict['key'])
            action_type = str(output_dict['action_type'])
            if action_type == '0': ##Replace
                return self.mongo_manager.replace_data_as_dataframe(output_key, output_data)
            if action_type == '1': ##Update
                return self.mongo_manager.update_data_as_dataframe(output_key, output_data)
            return True
        except Exception as e:
            utils.logger.error("Exception in manage_output for: " + str(self.node_key) + " + Error: " + str(e))
            return False

    def get_input(self):
        ##Get input data from mongo based on keys in input_data_array
        try:
            input_array = []
            for input_data in self.input_data_array:
                input_key = str(input_data['key'])
                input_data = self.mongo_manager.fetch_data_as_dataframe(input_key)
                if input_data is None:
                    utils.logger.error("Input data is None for key: " + str(input_key))
                    input_data = pd.DataFrame()
                input_array.append(input_data)
            return input_array
        except Exception as e:
            utils.logger.error("Exception in get_input for: " + str(self.node_key) + " + Error: " + str(e))
            return []


    def run(self):
        utils.logger.info("Starting Node: " + str(self.node_key))
        while not self.stop_event.is_set():
            utils.logger.info(str(self.node_key) + " is running")
            try:
                ##Run function here

                ##Manage input here.

                input_data = None
                # Import the module dynamically
                project_module = importlib.import_module(f"Projects.{self.project_key}")

                # importlib.reload(project_module) ##Optimise: only load when refreshed!

                # Get the function dynamically
                project_function = getattr(project_module, self.node_key)
                # Call the function
                ##number of outputs are dynamic

                input_array = self.get_input()


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
                    self.manage_output(actual_output, output_data)

                utils.logger.info("Code run completed for node: " + str(self.node_key))

            except Exception as e:
                utils.logger.error("Error occured in thread: " + str(self.node_key) + ". Error: " + str(e))



            utils.logger.info("Node: " + str(self.node_key) + " sleeping for: " + str(self.sleep_duration))
            time.sleep(self.sleep_duration)
            utils.logger.info("Node: " + str(self.node_key) + " back on")

        utils.logger.warning(str(self.node_key) + " stopped")

    def stop(self):
        self.stop_event.set()

