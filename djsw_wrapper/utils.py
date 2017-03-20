import os
import re
from jinja2 import Environment, FileSystemLoader

class _Singleton(type):
    """ A metaclass that creates a Singleton base class when called. """
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class Singleton(_Singleton('SingletonMeta', (object,), {})): pass

# creates class from dict on demand
class LazyClass(object):
    oftype = None

    def __init__(self, name = None, oftype = None):
        if not self.oftype and oftype:
            self.oftype = oftype

        assert name is not None, ('You should provide a name for new class')
        assert self.oftype is not None, ('You should provide a type for new class')

        self.handle = None
        self.attrs = dict()
        self.ready = False
        self.name = name

    def set_attr(self, key, value):
        self.attrs[key] = value

    def as_class(self):
        return type(self.name, (self.oftype,), dict(self.attrs))

class Template():
    def __init__(self):
        self.loader = FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates'))
        self.env = Environment(loader = self.loader)

    def render(self, template_name, **kwargs):
        template = self.env.get_template(template_name)
        return template.render(**kwargs)

# processes $ref links
def Resolver(obj, path, full = False):
    m = re.search('#/(.*)/(.*)', path)
    x = None

    if full:
        b = obj[m.group(1)]
        x = b[m.group(2)]
    else:
        x = m.group(2)

    return x
