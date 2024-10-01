from celery import Celery
import json
from Engine.TaskRunner import TaskRunner
from Engine.MongoManager import MongoManager
import Utils.utils as utils
from celery import chain, group, signature, chord
import os
from celery_singleton import Singleton
import time

BROKER_URL = os.getenv('BROKER_URL', 'redis://localhost:6379/0')
BACKEND_URL = os.getenv('BACKEND_URL', BROKER_URL)

# Setup Celery
app = Celery('waveassist',
             broker=BROKER_URL,
             backend=BACKEND_URL)

# Setup MongoManager
mongo_manager = MongoManager()


##ToDo: Add/Plan timeout
@app.task(base=Singleton, unique_on=['task_key', ], bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 1, 'countdown': 10})
def run_task(*args, task_dict=None, collection_key=None, task_key=None, **kwargs):
    try:
        task_runner = TaskRunner(task_dict, collection_key, mongo_manager)
        task_runner.run()
        return True
    except Exception as e:
        utils.logger.error(f"Error in processing task: {e}")
        raise e


@app.task(base=Singleton, unique_on=['dag_key', ], lock_expiry=600, bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 1, 'countdown': 10})
def run_dag(*args, dependencies_dict=None, data_dict=None, collection_key=None, dag_key=None, **kwargs):
        try:
            ##ToDo: This function can be optimised by using a DFS or similar approach to generate the workflow for the DAG
            ##ToDo: Figure out a way to have celery beat run after previous completion. or limit queue length
            ##ToDo: Write tests

            ##It will mainly optimise the wait time for certain tasks, which need not necessarily wait for others.
            layers_array = utils.generate_flow_layers(dependencies_dict)
            workflow_array = []
            # Iterate over each layer in layers_array
            for layer in layers_array:
                current_layer_tasks_signatures = []
                for task_key in layer:
                    task_dict = data_dict[task_key]
                    task = run_task.si(task_dict=task_dict, collection_key=collection_key, task_key=task_key)
                    current_layer_tasks_signatures.append(task)

                ##Create a group of tasks for the current layer & append
                current_layer_group = group(current_layer_tasks_signatures)
                workflow_array.append(current_layer_group)

            workflow = chain(*workflow_array)
            result = workflow.apply_async()
            return True
        except Exception as e:
            utils.logger.error(f"Error in processing DAG: {e}")
            raise e

