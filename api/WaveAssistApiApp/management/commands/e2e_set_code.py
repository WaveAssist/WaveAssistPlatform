"""Test helper: set node code for the e2e project's two sample nodes so a run
exercises the full SDK data round-trip (store_data -> API -> Mongo -> fetch_data).
Not part of the product; used only by the platform E2E test.

    python manage.py e2e_set_code --project e2e
"""
from django.core.management.base import BaseCommand
from WaveAssistApiApp.models import Project, Nodes

NODE1 = (
    "import waveassist\n"
    "waveassist.init()\n"
    "waveassist.store_data('e2e_result', {'ok': True, 'msg': 'hello from worker'}, data_type='json')\n"
)
NODE2 = (
    "import waveassist\n"
    "waveassist.init()\n"
    "r = waveassist.fetch_data('e2e_result', default={})\n"
    "waveassist.store_data('e2e_final', {'received': r, 'stage': 'consume'}, data_type='json')\n"
)


class Command(BaseCommand):
    help = "Set e2e sample node code (store/fetch) for the platform E2E test."

    def add_arguments(self, parser):
        parser.add_argument("--project", default="e2e")

    def handle(self, *args, **opts):
        project = Project.objects.filter(project_key=opts["project"]).first()
        if not project:
            self.stderr.write(f"project '{opts['project']}' not found")
            return
        nodes = {n.node_key: n for n in Nodes.objects.filter(project_object=project)}
        mapping = {"samplenode1": NODE1, "samplenode2": NODE2}
        for key, code in mapping.items():
            n = nodes.get(key)
            if not n:
                self.stderr.write(f"node '{key}' not found (have: {list(nodes)})")
                continue
            n.python_code = code
            n.is_enabled = True
            n.save(update_fields=["python_code", "is_enabled"])
            self.stdout.write(self.style.SUCCESS(f"set code for {key}"))
