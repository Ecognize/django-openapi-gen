import os
from django.conf import settings
from django.core.management import BaseCommand

class Command(BaseCommand):
    help = "Generates stub controllers for endpoints specified in API scheme (both YAML and JSON are supported)"

    def add_arguments(self, parser):
        parser.add_argument('filename', required = True, help = 'API scheme file to process')
        parser.add_argument('--dryrun', default = True, help = 'Only lists handlers which will be generated (enabled by default')

    def handle(self, *args, **options):
        pass

