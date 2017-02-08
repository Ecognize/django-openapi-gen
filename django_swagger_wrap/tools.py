from jinja2 import Environment, FileSystemLoader
import codecs
import flex
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

        self.parse()

    def parse(self):
        try:
            self.schema = flex.load(self.handle)
            self.loaded = True
        except:
            ValueError('Cannot process this schema')
            pass

    def get_cshort(self):
        return 'x-swagger-router-controller'

    # some advanced parsing techniques to be implemented
    def get_schema(self):
        if self.loaded:
            return self.schema
        else:
            raise ValueError('You should load spec file first')
