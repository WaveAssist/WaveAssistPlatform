from celery_worker import run_dag  # Your DAG celery task

dag_kwargs = {
    'dependencies_dict': {
        'node1': [],
        'node2': ['node1']
    },
    'data_dict': {
        'node1': {
            'node_key': 'node1',
            'project_key': 'proj1',
            'code_to_run': 'def run_task():\n    print("node 1")'
        },
        'node2': {
            'node_key': 'node2',
            'project_key': 'proj1',
            'code_to_run': 'def run_task():\n    print("node 2")'
        }
    },
    'collection_key': 'REMOVED_CREDENTIAL',
    'dag_key': 'DAG_proj1_node1_Deployment_v1_REMOVED_CREDENTIAL',
}

# Trigger the DAG
result = run_dag.apply_async(kwargs=dag_kwargs)
