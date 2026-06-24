import sys
from Engine.TaskRunner import TaskRunner
import Utils.utils as utils
from celery import chain, group
from Utils.constants import *
from celery_singleton import Singleton
from celery.signals import worker_ready
from celery_singleton import clear_locks
import uuid

##Initialize Celery app
utils.start_pre_initialization()
from celery_app import app

@worker_ready.connect
def unlock_all(**kwargs):
    clear_locks(app)

@app.task(base=Singleton,unique_on=['collection_key','task_key'], lock_expiry=2*60*60 + 15*60, bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 1, 'countdown': 10}, acks_late=False)
def run_task(*args, task_dict=None, collection_key=None, task_key=None, run_id=None, **kwargs):
    # Task dict needs node_key, project_key and code_to_run
    try:
        task_runner = TaskRunner(task_dict, collection_key, run_id)
        result = task_runner.run()
        return result
    except Exception as e:
        project_key = task_dict['project_key']
        utils.logger.error(f"Error in processing task: {e}", extra={'task_key': task_key, 'environment_key': collection_key, project_key:project_key, IS_SYSTEM_TASK: True})
        raise e

@app.task(base=Singleton,unique_on=['collection_key','dag_key'], lock_expiry=600, bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 1, 'countdown': 10}, acks_late=False)
def run_dag(*args, dependencies_dict=None, data_dict=None, collection_key=None, dag_key=None, **kwargs):
        try:
            ##ToDo: This function can be optimised by using a DFS or similar approach to generate the workflow for the DAG
            ##ToDo: Figure out a way to have celery beat run after previous completion. or limit queue length
            ##ToDo: Write tests
            run_uuid = str(uuid.uuid4())
            ##It will mainly optimise the wait time for certain tasks, which need not necessarily wait for others.
            layers_array = utils.generate_flow_layers(dependencies_dict)
            workflow_array = []
            # Iterate over each layer in layers_array
            for layer in layers_array:
                current_layer_tasks_signatures = []
                for task_key in layer:
                    task_dict = data_dict[task_key]
                    task = run_task.si(task_dict=task_dict, collection_key=collection_key, task_key=task_key, run_id=run_uuid)
                    current_layer_tasks_signatures.append(task)

                ##Create a group of tasks for the current layer & append
                current_layer_group = group(current_layer_tasks_signatures)
                workflow_array.append(current_layer_group)

            workflow = chain(*workflow_array)
            result = workflow.apply_async()
            return result
        except Exception as e:
            utils.logger.error(f"Error in processing DAG: {e}", extra={'dag_key': dag_key, 'collection_key': collection_key, IS_SYSTEM_TASK: True})
            raise e

