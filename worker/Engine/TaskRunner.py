import time
import Utils.utils as utils
from Utils.Timer import Timer
import importlib
from Engine.MongoManager import MongoManager
import pandas as pd
from Utils.constants import *
from Integrations.Mailer import Mailer



class TaskRunner(object):
        def __init__(self, task_dict, collection_key,  mongo_manager):
            self.node_key = task_dict['node_key']
            self.project_key = task_dict['project_key']
            self.code_to_run = task_dict['code_to_run']
            self.input_keys_array = task_dict['input_keys_array']
            self.output_keys_array = task_dict['output_keys_array']
            self.integration_key = self.project_key + INTEGRATION_SUFFIX
            self.integrations_collection_key = self.project_key
            self.collection_key = collection_key
            self.mongo_manager = mongo_manager

        def run_code(self, input_data_array):
            namespace = {}
            try:
                # Try to compile the provided code to check for syntax errors
                compiled_code = compile(self.code_to_run, "<string>", "exec")

                # Execute the compiled code in the given namespace
                exec(compiled_code, namespace)

                # Ensure that the desired function is available in the namespace
                if 'run_task' not in namespace or not callable(namespace['run_task']):
                    raise NameError("'run_task' is not defined or is not callable in the provided code.")

                # Call the function and return the result
                result = namespace['run_task'](*input_data_array)

                if len(self.output_keys_array) == 0:
                    return []
                elif len(self.output_keys_array) == 1:
                    return [result]
                elif len(self.output_keys_array) >= 2:
                    return list(result)
            except SyntaxError as e:
                print("Syntax error in the provided code:", e)
                return []
            except NameError as e:
                print("Name error:", e)
                return []
            except Exception as e:
                print("An error occurred:", e)
                return []

        def save_output(self, output_df, output_key):
            try:
                if output_df is None:
                    return True
                success = self.mongo_manager.replace_data_as_dataframe(output_key, output_df, self.collection_key)
                return success
            except Exception as e:
                utils.logger.error("Exception in manage_output for: " + str(self.node_key) + " + Error: " + str(e))
                return False

        def process_output(self, output_data_array):
            for i in range(0, len(output_data_array)):
                output_data = output_data_array[i]
                output_key = self.output_keys_array[i]
                self.save_output(output_data, output_key)

        def fetch_integrations(self):
            try:
                integrations_df = self.mongo_manager.fetch_data_as_dataframe(self.integration_key, self.integrations_collection_key)
                return integrations_df
            except Exception as e:
                utils.logger.error("Exception in fetch_integrations for node")
                return None


        def get_input(self):
            try:
                input_dict = self.mongo_manager.fetch_data_as_dataframe_for_array(self.input_keys_array, self.collection_key)
                input_dict[self.integration_key] = self.fetch_integrations()
                self.input_keys_array.append(self.integration_key)
                input_array = [input_dict.get(io_key, pd.DataFrame()) for io_key in self.input_keys_array]
                return input_array
            except Exception as e:
                utils.logger.error("Exception in get_input for: " + str(self.node_key) + " + Error: " + str(e))
                return []

        def run(self):
            utils.logger.info("Starting Node: " + str(self.node_key))
            timer = Timer(str(self.node_key))
            timer.start()
            input_data_array = self.get_input()
            output_data_array = self.run_code(input_data_array)
            self.process_output(output_data_array)
            timer.print_elapsed()
            utils.logger.info("Code run completed for node: " + str(self.node_key))




