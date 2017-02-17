from jinja2 import Environment, FileSystemLoader
from django_swagger_wrap.router import SwaggerRouter

import codecs
import flex
import six
import os


class Template:
    def __init__(self):
        self.loader = FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates'))
        self.env = Environment(loader = self.loader)

    def render(self, template_name, **kwargs):
        template = self.env.get_template(template_name)
        return template.render(**kwargs)

class Swagger:
    # handle is local filename, file object, string or url
    def __init__(self, handle):
        self.schema = None
        self.loaded = False
        self.handle = handle
        self.models = []
        self.router = None

        # parse
        try:
            self.schema = flex.load(self.handle)
            self.loaded = True
        except:
            ValueError('Cannot process this schema')

        # make models for definitions
        if 'definitions' in self.schema:
            # make external models
            for name, data in six.iteritems(self.schema['definitions']):
                self.models.append()

        # make routes
        if 'paths' in self.schema and 'basePath' in self.schema:
            self.router = SwaggerRouter(self.schema['basePath'], self.schema['paths'])
        else:
            raise ValueError('Schema is missing paths and/or basePath values')
    
    # some advanced parsing techniques to be implemented
    def get_schema(self):
        if self.loaded:
            return self.schema
        else:
            raise ValueError('You should load spec file first')
