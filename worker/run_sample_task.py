import json
from Engine.MongoManager import MongoManager
import pandas as pd
from celery_worker import run_task


##ToDo: This file does not work.

def get_code():
    return """
def run_task(input_1_df, input_2_df, integrations_df):
    ##Process the data, modify input_1 df
    print("RUNNING TASK!!")
    input_1_df['sum'] = input_1_df['a'] + input_1_df['b']
    input_2_df['sum'] = input_2_df['a'] + input_2_df['b']
    return input_1_df, input_2_df
    """

mongo_manager = MongoManager()

collection_key = "test_project"

##Create input_1_df
input_1_df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
input_2_df = pd.DataFrame({'a': [7, 8, 9], 'b': [10, 11, 12]})
mongo_manager.replace_data_as_dataframe("input_1", input_1_df, collection_key)
mongo_manager.replace_data_as_dataframe("input_2", input_2_df, collection_key)

collection_key = "test_project"

# Prepare the task to publish
task_dict = {
    "node_key": "test_node",
    "project_key": "test_project",
    "input_keys_array": ["input_1", "input_2"],
    "output_keys_array": ["output_1", "output_2"],
    "code_to_run": get_code(),
}

result = run_task.delay(task_dict=task_dict, collection_key=collection_key)

print("Task ID : ", result.id)
print("Task submitted, result: ", result.get())