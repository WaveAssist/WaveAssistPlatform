#!/usr/bin/env python
"""
WaveAssist – Celery event listener (custom events)
--------------------------------------------------
• Handles only our CUSTOM_EVENT_KEY events.
• Lazily creates DagRuns and NodeRuns from these events.
• Idempotently upserts NodeRuns, safe for out-of-order start/complete.
"""

import traceback
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from celery.events import EventReceiver
from WaveAssistApi.celery import app
from WaveAssistApiApp.models import *
from WaveAssistApiApp.Utils.constants import *


class Command(BaseCommand):
    help = "Populate DagRuns + NodeRuns from custom events."

    def _handle_custom_event(self, event):
        # extract required fields
        print(event)
        ev_type        = event.get('event_type')
        run_id         = event.get('uuid')
        node_key       = event.get('node_key')
        project_key    = event.get('project_key')
        collection_key = event.get('collection_key')
        did_succeed    = event.get('did_succeed')
        error_message  = event.get('error_message')
        timestamp      = event.get('timestamp')

        if not all([ev_type, run_id, node_key, project_key, collection_key, timestamp]):
            self.stderr.write(self.style.ERROR(f"❌ Malformed event: {event}"))
            return

        # resolve data_run → project → node
        try:
            data_run = DataRuns.objects.get(data_run_key=collection_key)
            project = Project.objects.get(project_key=project_key)
            node     = Nodes.objects.get(node_key=node_key, project_object=project)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Resolution error: {e}\n{traceback.format_exc()}"))
            return

        # upsert DagRun
        try:
            dag_run, _ = DagRuns.objects.get_or_create(
                run_id=run_id,
                defaults={
                    "project_object": project,
                    "data_run_object": data_run,
                }
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ DagRun creation error: {e}\n{traceback.format_exc()}"))
            return

        # upsert NodeRun
        try:
            node_run, _ = NodeRuns.objects.get_or_create(
                dag_run_object=dag_run,
                node_object=node,
                defaults={
                    "status":  "STARTED",
                }
            )

            # convert float timestamp → aware datetime
            dt = timezone.make_aware(datetime.fromtimestamp(timestamp))

            if ev_type == TASK_STARTED:
                node_run.started_at = dt

            elif ev_type == TASK_COMPLETED:
                node_run.finished_at = dt
                if did_succeed:
                    node_run.status = "SUCCESS"
                else:
                    node_run.status    = "FAILED"
                    node_run.traceback = error_message or ''

            node_run.save(update_fields=['status', 'started_at', 'finished_at', 'traceback'])
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ NodeRun handling error: {e}\n{traceback.format_exc()}"))

    def handle(self, *args, **options):
        """Start listening for our custom events only."""
        def recv(ev):
            # only invoke for the custom event key
            if ev.get('type') == CUSTOM_EVENT_KEY:
                self._handle_custom_event(ev)

        try:
            with app.connection() as conn:
                receiver = EventReceiver(conn, handlers={CUSTOM_EVENT_KEY: recv}, app=app)
                self.stdout.write(self.style.SUCCESS(f"⏳ Listening for '{CUSTOM_EVENT_KEY}'…"))
                receiver.capture(limit=None, timeout=None, wakeup=True)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Connection error: {e}\n{traceback.format_exc()}"))
