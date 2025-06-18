#!/usr/bin/env python

import json
from django.core.management.base import BaseCommand
from django.utils import timezone
from WaveAssistApi.celery import app
from celery.events import EventReceiver
from celery.events.state import State

from WaveAssistApiApp.models import *
from WaveAssistApiApp.Utils.constants import *
import ast
import re

def extract_value(raw: str, key: str):
    pattern = rf"'{re.escape(key)}'\s*:\s*'(?P<val>[^']*)'"
    m = re.search(pattern, raw)
    return m.group('val') if m else None

def get_parent_dag_run_uuid(task_run):
    current = task_run
    while current.parent is not None:
        current = current.parent
    return current.uuid  # This should be the DAG run


class Command(BaseCommand):
    help = "Consume Celery events and populate DagRuns + NodeRuns."

    def handle(self, *args, **options):
        state = State()
        def recv_event(event):
            state.event(event)
            ev_type = event.get("type")
            task_id = event.get("uuid")
            task = state.tasks.get(task_id)
            if not task:
                return
            name = task.name
            kwargs_string = task.kwargs

            # 1) Root DAG received → create DagRuns + pre-populate NodeRuns
            if ev_type == "task-received" and name == DAG_TASK:
                run_id = task_id
                dag_key = extract_value(kwargs_string, 'dag_key') ##ToDo: Find a better way to extract these values. JSON and AST did not work.
                data_run_key = extract_value(kwargs_string, 'collection_key')
                try:
                    dag = DAG.objects.get(key=dag_key)
                    data_run = DataRuns.objects.get(data_run_key=data_run_key)
                    dag_run = DagRuns.objects.create(
                        run_id=run_id,
                        dag_object=dag,
                        project_object=data_run.project_object,
                        data_run_object=data_run,
                    )
                    dag_run.save()

                except Exception as e:
                    print(self.style.ERROR(f"❌ Error processing DAG Event: {e}"))
                    return

            # 2) Node received → create/update NodeRuns
            if name == RUN_TASK:
                node_key = extract_value(kwargs_string, 'task_key')
                data_run_key = extract_value(kwargs_string, 'collection_key')
                parent_run_id = get_parent_dag_run_uuid(task)  # Get the root DAG run
                if ev_type == "task-received":
                    ##Create nodeRun
                    try:
                        dag_run = DagRuns.objects.get(run_id=parent_run_id)
                        data_run = DataRuns.objects.get(data_run_key=data_run_key)
                        project_object = data_run.project_object
                        node_object = Nodes.objects.get(node_key=node_key, project_object=project_object)
                        NodeRuns.objects.create(
                            dag_run_object=dag_run,
                            node_object=node_object,
                            status="PENDING",  # initial state
                            task_id=task_id
                        )
                    except Exception as e:
                        print(self.style.ERROR(f"❌ Error processing Node Create: {e}"))
                        return
                else:
                    ##Update nodeRun
                    try:
                        node_run = NodeRuns.objects.get(
                            dag_run_object__run_id=parent_run_id,
                            node_object__node_key=node_key
                        )

                        # a) STARTED (task actually began)
                        if ev_type == "task-started":
                            node_run.status = "STARTED"
                            node_run.started_at = timezone.now()
                            node_run.save()

                        # c) SUCCESS
                        elif ev_type == "task-succeeded":
                            result = task.result
                            if result == 'True':
                                node_run.status = "SUCCESS"
                            else:
                                node_run.status = "FAILED"
                            node_run.finished_at = timezone.now()
                            node_run.result = result
                            node_run.save()

                        # d) FAILURE
                        elif ev_type == "task-failed":
                            tb = task.traceback or []
                            node_run.status = "FAILED"
                            node_run.finished_at = timezone.now()
                            node_run.traceback = "\n".join(tb)
                            node_run.save()

                        # e) RETRY
                        elif ev_type == "task-retried":
                            node_run.status = "RETRY"
                            node_run.save()

                    except Exception as e:
                        print("❌ Error updating NodeRun: ", e)

        # Start consuming events
        with app.connection() as conn:
            receiver = EventReceiver(conn, handlers={"*": recv_event}, app=app)
            self.stdout.write(self.style.SUCCESS("⏳ Listening for Celery events…"))
            receiver.capture(limit=None, timeout=None, wakeup=True)
