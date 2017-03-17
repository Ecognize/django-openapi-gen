import os
import codecs

from django.utils import six
from django.conf import settings
from django.core.management import BaseCommand
from django.core.exceptions import ImproperlyConfigured

from djsw_wrapper.core import Swagger
from djsw_wrapper.utils import Template
from djsw_wrapper.router import SwaggerRouter

class Command(BaseCommand):
    help = "Generates stub controllers for endpoints specified in API scheme (both YAML and JSON are supported)"

    def add_arguments(self, parser):
        parser.add_argument('--name', nargs = '?', default = 'controllers', help = 'Name of module to be created (without extenstion)')
        parser.add_argument('--generate', action = 'store_true', dest = 'generate', help = 'Generate handlers according to spec')

    def handle(self, *args, **options):
        schema = getattr(settings, 'SWAGGER_SCHEMA', None)
        module = getattr(settings, 'SWAGGER_CONTROLLER', None)

        if not schema:
            raise ImproperlyConfigured('You have to provide SWAGGER_SCHEMA setting pointing to desired schema')
        if not module:
            raise ImproperlyConfigured('You have to specify desired controller module name in SWAGGER_CONTROLLER setting')

        router = SwaggerRouter()

        print('Inspecting available controllers...')

        router.update(True)
        router.process()

        print()
        print('Following classes and methods are going to be generated:')

        enum = router.get_enum()

        for name in enum:
            print("{} : {}".format(name, [x['method'] for x in enum[name]['methods']]))

        if(options['generate']):
            template = Template()
            filename = module.split('.')[-1] + '.py'
            structure = [{ 'name' : name, 'data' : data } for name, data in six.iteritems(enum)]

            print('Generating handlers ({})...'.format(filename))

            with codecs.open(filename, 'w', 'utf-8') as f:
                f.write(template.render(template_name = 'view.jinja', names = structure))

            print('Done.')
        else:
            print()
            print('Use --generate option to create them')

