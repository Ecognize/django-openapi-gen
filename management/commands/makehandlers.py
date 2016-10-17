import os
from django.conf import settings
from django.core.management import BaseCommand

class Command(BaseCommand):
    help = "Generates stub controllers for endpoints specified in API scheme (both YAML and JSON are supported)"

    def handle(self, *args, **options):
        pass

