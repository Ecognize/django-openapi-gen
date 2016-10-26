import os
import six
import codecs

from django_swagger_wrap.tools import Template, Swagger
from django.conf import settings
from django.core.management import BaseCommand

class Command(BaseCommand):
    help = "Generates stub controllers for endpoints specified in API scheme (both YAML and JSON are supported)"

    def add_arguments(self, parser):
        parser.add_argument('filename', nargs = '+', help = 'API scheme file to process')
        parser.add_argument('--name', nargs = '?', default = 'controllers', help = 'Name of module to be created (without extenstion)')
        parser.add_argument('--generate', action = 'store_true', dest = 'generate', help = 'Generate handlers according to spec')

    def handle(self, *args, **options):
        swagger = Swagger(options['filename'][0])
        template = Template()

        eps = {}
        obj = swagger.get_object()

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
