import os

from django_openapi_gen import Generator, Swagger
from django.conf import settings
from django.core.management import BaseCommand

class Command(BaseCommand):
    help = "Generates stub controllers for endpoints specified in API scheme (both YAML and JSON are supported)"

    def add_arguments(self, parser):
        parser.add_argument('filename', required = True, help = 'API scheme file to process')
        parser.add_argument('--dryrun', default = True, dest = 'dryrun', help = 'Only lists handlers which will be generated (enabled by default')

    def handle(self, *args, **options):
        if options['dryrun']:
            pass

        package = package or destination.replace('-', '_')
        data = load(args['filename'])
        swagger = Swagger(data)
        generator = Generator(swagger)
        generator.with_spec = specification
        generator.with_ui = ui
        template = Template()
        if template_dir:
            template.add_searchpath(template_dir)
        env = dict(package=package,
                   module=swagger.module_name)

        if ui:
            ui_dest = join(destination, '%(package)s/static/swagger-ui' % env)
            ui_src = join(dirname(__file__), 'templates/ui')
            status = _copy_ui_dir(ui_dest, ui_src)
            click.secho('%-12s%s' % (status, ui_dest))

        for code in generator.generate():
            source = template.render_code(code)
            dest = join(destination, code.dest(env))
            dest_exists = exists(dest)
            can_override = force or code.override
            statuses = {
                (False, False): 'generate',
                (False, True): 'generate',
                (True, False): 'skip',
                (True, True): 'override'
            }
            status = statuses[(dest_exists, can_override)]
            click.secho('%-12s' % status, nl=False)
            click.secho(dest)

            if status != 'skip':
                write(dest, source)
