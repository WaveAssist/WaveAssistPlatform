"""Import a local agent without replacing its existing data or run history."""
import os
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from pymongo import MongoClient

from WaveAssistApi.settings import MONGO_CONNECTION_STRING
from WaveAssistApiApp.models import User, Account, Project, DataRuns, Nodes, AccessProvided, Deployments
from WaveAssistApiApp.Utils.constants import ADMIN_GTE, IO_DATA_KEY, DATA_KEY, DATA_TYPE_KEY
from WaveAssistApiApp.Utils import projectSetup, utils
from WaveAssistApiApp.Utils.local_agent import load_agent, configuration_schema


class Command(BaseCommand):
    help = "Import local config.yaml and node files; retain existing variables and node history. Stop schedules before reimporting."

    def add_arguments(self, parser):
        parser.add_argument("--path", required=True)
        parser.add_argument("--uid", default=os.getenv("WAVEASSIST_ADMIN_UID", ""))
        parser.add_argument("--project", default="")

    def handle(self, *args, **opts):
        try:
            config, sources = load_agent(opts["path"])
        except (OSError, ValueError, SyntaxError, TypeError, KeyError) as exc:
            raise CommandError(f"Agent validation failed: {exc}") from exc
        user = User.objects.filter(uid=opts["uid"].strip()).first()
        if not user or not Account.objects.filter(created_by_user=user).exists():
            raise CommandError("User and account must exist; run seed_admin first for a new box.")
        key = opts["project"].strip() or str(config.get("name", "agent")).lower().replace(" ", "_")
        if not re.fullmatch(r"[a-z0-9_\-]{1,200}", key):
            raise CommandError("Project key must be a lowercase identifier (at most 200 characters).")

        with transaction.atomic():
            project = Project.objects.select_for_update().filter(project_key=key).first()
            if project:
                if not utils.does_user_have_access_to_project(user, project, access_gte=ADMIN_GTE):
                    raise CommandError("Admin access to the existing project is required.")
                if Deployments.objects.filter(project_object=project, is_running=True).exists():
                    raise CommandError("Stop the project's deployment before importing changes.")
            else:
                project = Project.objects.create(project_key=key, name=str(config.get("name", key)))
            project.local_configuration = configuration_schema(config)
            project.save(update_fields=["local_configuration"])
            AccessProvided.objects.get_or_create(type=0, project_object=project, user_object=user,
                                                defaults={"project_access_type": ADMIN_GTE})
            AccessProvided.objects.get_or_create(type=2, project_object=project, user_object=user,
                                                defaults={"dashboard_access_type": ADMIN_GTE})
            for env in ("default", "test"):
                data_run, _ = DataRuns.objects.get_or_create(
                    data_run_key=f"{key}_{env}", project_object=project,
                    defaults={"name": env.capitalize(), "is_enabled": True})
                AccessProvided.objects.get_or_create(type=1, data_run_object=data_run, user_object=user,
                                                    defaults={"data_run_access_type": ADMIN_GTE})
            imported = {}
            for definition in config["nodes"]:
                node_key = definition["key"]
                schedule = definition.get("schedule") or {}
                schedule_type, cron, interval = projectSetup.parse_schedule(
                    schedule, schedule.get("timezone", config.get("timezone", "UTC")))
                node, _ = Nodes.objects.update_or_create(project_object=project, node_key=node_key, defaults={
                    "name": definition.get("name", node_key), "python_code": sources[node_key],
                    "local_source_path": str((Path(opts["path"]) / definition["file_name"]).resolve()),
                    "is_starting_node": definition.get("starting_node", False),
                    "chain_label": definition.get("chain_label") or None, "is_enabled": True,
                    "schedule_type": schedule_type, "crontab_schedule": cron, "interval_schedule": interval,
                })
                imported[node_key] = node
            for definition in config["nodes"]:
                imported[definition["key"]].run_after_nodes_array.set(
                    imported[dependency] for dependency in definition.get("run_after", []))
            # Retain removed nodes for historical FK references, but prevent future runs.
            Nodes.objects.filter(project_object=project).exclude(node_key__in=imported).update(
                is_enabled=False, is_starting_node=False)

        # Mongo is not part of the SQL transaction. Inserts are retryable and never
        # overwrite a configured value; report any failure so callers can retry.
        seeded = 0
        try:
            with MongoClient(MONGO_CONNECTION_STRING, serverSelectionTimeoutMS=5000) as client:
                database = client[utils.get_database_name(user)]
                for variable in config.get("variables") or []:
                    variable_key = variable.get("key") or variable["name"]
                    if variable.get("type") in {"password", "secret"} or variable.get("is_secret"):
                        value = ""
                    else:
                        value = variable.get("value", variable.get("default_value"))
                        if value is None:
                            options = variable.get("options") or []
                            value = options[0] if options else ""
                            if isinstance(value, dict):
                                value = value.get("key", "")
                    for env in ("default", "test"):
                        result = database[f"{key}_{env}"].update_one(
                            {IO_DATA_KEY: variable_key}, {"$setOnInsert": {
                                DATA_KEY: value, DATA_TYPE_KEY: "string" if isinstance(value, str) else "json",
                            }}, upsert=True)
                        seeded += int(result.upserted_id is not None)
        except Exception as exc:
            raise CommandError("Nodes imported, but variable seeding failed. Correct Mongo connectivity and rerun; existing values will be retained.") from exc
        self.stdout.write(self.style.SUCCESS(
            f"Imported '{key}': {len(imported)} nodes; {seeded} missing environment values seeded. Scheduling remains stopped."
        ))
