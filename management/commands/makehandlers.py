import os

from django_openapi_gen.tools import Template, Swagger
from django.conf import settings
from django.core.management import BaseCommand

class Command(BaseCommand):
    help = "Generates stub controllers for endpoints specified in API scheme (both YAML and JSON are supported)"

    def add_arguments(self, parser):
        parser.add_argument('filename', required = True, help = 'API scheme file to process')
        parser.add_argument('destination', required = False, help = 'Filename of module to be created')
        parser.add_argument('--dryrun', default = True, dest = 'dryrun', help = 'Only lists handlers which will be generated (enabled by default')

    def handle(self, *args, **options):
        swagger = Swagger(args['filename'])
        template = Template()

        eps = []
        obj = swagger.get_object()

        for path in obj['paths']:
            name = None
            child = None
            methods = []

            # poor man's validation
            try:
                child = obj['paths'][path]
                name = child['x-swagger-router-controller']
            except AttributeError:
                raise SyntaxError("Please provide valid Swagger document!")

            # make array of dicts
            eps.append({name : [method for method in child]})

        print(eps)
        #print(template.render('view.ninja', eps))
