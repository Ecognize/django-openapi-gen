import os

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

        #print('COM')
        router = SwaggerRouter()

        router.update(True)
        router.process()

        template = Template()

        eps = {}
"""
        for path in obj['paths']:
            name = None
            child = None

            # poor man's validation
            try:
                child = obj['paths'][path]
                name = child[swagger.get_cshort()]
            except AttributeError:
                raise SyntaxError("Please provide valid Swagger document!")

            # make dict
            eps[path] = (name, [method for method in child if method != swagger.get_cshort()])

        if(options['generate']):
            filename = options['name'] + '.py'
            structure = [{ 'name' : data[0], 'methods' : data[1]} for path, data in six.iteritems(eps)]

            print('Generating handlers ({})...'.format(filename))

            with codecs.open(filename, 'w', 'utf-8') as f:
                f.write(template.render(template_name = 'view.jinja', names = structure))

            print('Done.')
        else:
            print('Following handlers are going to be generated:')
            for path, data in six.iteritems(eps):
                print('{} -> {} ({})'.format(path, data[0], ','.join(data[1])))
        #if(options['enumerate']):
        #    print(eps)
        #print(template.render('view.ninja', eps))
"""