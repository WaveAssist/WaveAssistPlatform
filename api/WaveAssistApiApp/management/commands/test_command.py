from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "My test command"

    def handle(self, *args, **options):
        self.stdout.write("Hello from test command!")
