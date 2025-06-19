#!/usr/bin/env python
"""
WaveAssist – Celery event listener
----------------------------------
• Ignores explicit “dag-received” events.
• Handles only RUN_TASK node events.
• Lazily creates DagRuns, filling project_object,
  and data_run_object from the first node event.
• Idempotently upserts NodeRuns, safe for out-of-order events.
"""

import re
import traceback
from django.core.management.base import BaseCommand
from django.utils import timezone
from celery.events import EventReceiver
from celery.events.state import State
from WaveAssistApi.celery import app
from WaveAssistApiApp.models import *
from WaveAssistApiApp.Utils.constants import RUN_TASK

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def extract_value(raw: str, key: str):
    m = re.search(rf"'{re.escape(key)}'\s*:\s*'(?P<val>[^']*)'", raw or "")
    return m.group("val") if m else None

def root_uuid(task):
    cur = task
    while cur.parent is not None:
        cur = cur.parent
    return cur.uuid

STATE_ORDER = {"PENDING": 1, "RUNNING": 2, "SUCCESS": 3, "FAILED": 3}

# ---------------------------------------------------------------------------
# management command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = "Populate DagRuns + NodeRuns from Celery node events."

    def _handle_node_event(self, task, ev_type):
        """Idempotent upsert of DagRuns / NodeRuns."""
        try:
            kwargs_str = task.kwargs
            dag_run_id = root_uuid(task)
            node_key = extract_value(kwargs_str, "task_key")
            data_key = extract_value(kwargs_str, "collection_key")
            result = task.result
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Event parsing error: {e}\n{traceback.format_exc()}"))
            return

        try:
            data_run = DataRuns.objects.select_related("project_object").get(data_run_key=data_key)
            project = data_run.project_object
            node = Nodes.objects.get(node_key=node_key, project_object=project)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Resolution error: {e}\n{traceback.format_exc()}"))
            return

        try:
            dag_run, _ = DagRuns.objects.get_or_create(
                run_id=dag_run_id,
                defaults={
                    "project_object": project,
                    "data_run_object": data_run,
                }
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ DagRun creation error: {e}\n{traceback.format_exc()}"))
            return

        try:
            node_run, created = NodeRuns.objects.get_or_create(
                dag_run_object=dag_run,
                node_object=node,
                defaults={
                    "status": "PENDING",
                    "task_id": task.uuid,
                }
            )

            now = timezone.now()

            if ev_type == "task-received":
                return

            if ev_type == "task-started":
                if node_run.started_at is None:
                    node_run.started_at = now
                if STATE_ORDER.get(node_run.status, 0) < STATE_ORDER["RUNNING"]:
                    node_run.status = "RUNNING"

            elif ev_type == "task-succeeded":
                final_status = "FAILED" if result == "False" else "SUCCESS"
                if node_run.finished_at is None:
                    node_run.finished_at = now
                if STATE_ORDER[final_status] >= STATE_ORDER.get(node_run.status, 0):
                    node_run.status = final_status
                node_run.result = result

            elif ev_type == "task-failed":
                if node_run.finished_at is None:
                    node_run.finished_at = now
                node_run.status = "FAILED"
                node_run.traceback = "\n".join(task.traceback or [])

            elif ev_type == "task-retried":
                node_run.status = "RETRY"

            node_run.save(update_fields=[
                "status", "started_at", "finished_at", "result", "traceback"
            ])

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ NodeRun handling error: {e}\n{traceback.format_exc()}"))

    def handle(self, *args, **options):
        state = State()

        def recv_event(ev):
            try:
                state.event(ev)
                task = state.tasks.get(ev.get("uuid"))
                if task and task.name == RUN_TASK:
                    self._handle_node_event(task, ev.get("type"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"❌ Event receiver error: {e}\n{traceback.format_exc()}"))

        try:
            with app.connection() as conn:
                receiver = EventReceiver(conn, handlers={"*": recv_event}, app=app)
                self.stdout.write(self.style.SUCCESS("⏳ Listening for node events…"))
                receiver.capture(limit=None, timeout=None, wakeup=True)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Connection or capture error: {e}\n{traceback.format_exc()}"))
