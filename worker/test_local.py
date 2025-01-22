import json
import pandas as pd
from celery_worker import run_task



def get_code():
    return """
def run_task():
    import time
    print("Running code!")
    for i in range(0,2):
        time.sleep(1)
    print("Done!")
    """

environment_key = "test_env"

# Prepare the task to publish
task_dict = {
    "node_key": "test_node",
    "project_key": "test_project",
    "code_to_run": get_code(),
}

result = run_task.delay(task_dict=task_dict, environment_key=environment_key)

print("Task ID : ", result.id)
print("Task submitted, result: ", result.get())
